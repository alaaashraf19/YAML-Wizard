import base64
import time
import httpx
from urllib.parse import urlparse, quote
from typing import Optional, Literal
from schemas.publish_yaml_schema import PublishResult
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from services.project_service import _resolve_token
from services.dashboard.repos_services import _parse_repo_info,_parse_branch, get_github_default_branch, get_gitlab_default_branch, parse_github_repo, _get_gitlab_proj_id
from sqlalchemy import select
from models.project_model import Project
from models.repository_model import Repository
from typing import Optional


_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 2  #seconds


@tool
async def publish_to_repo_tool(yaml_content: str, repo_url: Optional[str] = None,
    file_path: str | None = None,
    branch: str | None = None, commit_message: str | None = None, 
    publish_mode: Literal["pr", "direct"] = "pr", pr_branch: str = "yaml-wizard/ci-pipeline",
    config: RunnableConfig = None) -> PublishResult:
    
    """
    Tool: publish_to_repo

    Publishes a YAML file to a remote Git repository (GitHub or GitLab).
    Use this when the user explicitly asks to 'push', 'publish', or 'deploy' the generated pipeline.

    Behavior Notes:

        - This tool performs an external side effect (modifies remote repositories).
        - It should only be called when the user explicitly requests publishing, deploying, or pushing a file.
        - Prefer creating a pull request (create_pr=True) when safety is desired.
        - The YAML content should already be fully generated before calling this tool.

    """
    create_pr = publish_mode == "pr"
    configurable = config.get("configurable", {})
    
    db = configurable.get("db")
    user_id = configurable.get("user_id")
    project_id = configurable.get("project_id")
    gitlab_project_id = configurable.get("gitlab_project_id")

    if project_id:
        repo = await db.scalar(
            select(Repository)
            .join(Project, Repository.id == Project.repo_id)
            .where(Project.id == project_id)
        )
        
        if not repo:
            print("[publish_to_repo_tool] no repository found for project_id:", project_id)
            raise ValueError(f"No Repository found for this project (project_id={project_id})")
        repo_url = repo.url

    print("[publish_to_repo_tool] repo_url:", repo_url)

    
    try:
        parsed_full_name, parsed_platform = _parse_repo_info(repo_url)

        # Use the parsed_platform to override/verify the LLM's platform choice
        target_platform = parsed_platform.lower()
    except Exception as e:
        print("[publish_to_repo_tool] invalid repository URL:", str(e))
        return PublishResult(success=False, message=f"Invalid Repository URL: {str(e)}")
    token, _ = await _resolve_token(user_id, target_platform , repo_url,db)
    if not token:
        print("[publish_to_repo_tool] no authentication token found")
        return PublishResult(success=False, message="No authentication token found for the platform.")
    
    parsed_branch = await _parse_branch(repo_url, parsed_platform, parsed_full_name, token)
    if parsed_branch is None:
        return PublishResult(success=False, message=f"Could not resolve default branch: {str(e)}")
        
    if target_platform == "github":
        return _publish_github(
            yaml_content, repo_url, token, file_path, parsed_branch,
            commit_message, create_pr, pr_branch,
        )
    elif target_platform == "gitlab":
        print("[publish_to_repo_tool] entering gitlab publish flow")
        if gitlab_project_id is None:
            print("[publish_to_repo_tool] gitlab_project_id missing, resolving from repo URL")
            # Attempt to parse the GitLab project ID from the repo URL if not provided
            gitlab_project_id = await _get_gitlab_proj_id(parsed_full_name, token)
            print("[publish_to_repo_tool] parsed gitlab_project_id:", gitlab_project_id)
        else:
            print("[publish_to_repo_tool] using provided gitlab_project_id:", gitlab_project_id)
        return _publish_gitlab(
            yaml_content, repo_url, token, file_path, branch or parsed_branch,
            commit_message, create_pr, pr_branch,
            gitlab_project_id
        )
    else:
        return PublishResult(success=False, message=f"Unknown platform: {target_platform}")



def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:

    """Make an HTTP request with automatic retry on transient server errors."""

    last_exc: httpx.HTTPStatusError | None = None
    for attempt in range(_MAX_RETRIES + 1):
        resp = httpx.request(method, url, **kwargs)
        if resp.status_code not in _RETRYABLE_STATUS_CODES:
            resp.raise_for_status()
            return resp
        if attempt < _MAX_RETRIES:
            wait = _BACKOFF_BASE ** attempt  # 1s, 2s, 4s
            time.sleep(wait)
        else:
            resp.raise_for_status()  #raise on final attempt
    raise httpx.HTTPError(f"Request failed after {_MAX_RETRIES + 1} attempts")


# ── GITHUB ──────────────────────────────────────────────────────────────────


def _publish_github(yaml_content: str,repo_url: str,token: str,file_path: str | None,
    branch: str,commit_message: str | None,create_pr: bool,pr_branch: str,) -> PublishResult:
    
    """Publish YAML to a GitHub repository via the Contents API."""
    """directly to a branch or via pull request"""

    print("[_publish_github] starting GitHub publish")
    print("[_publish_github] repo_url:", repo_url)
    print("[_publish_github] branch:", branch)
    print("[_publish_github] create_pr:", create_pr)
    print("[_publish_github] pr_branch:", pr_branch)

    owner, repo = parse_github_repo(repo_url)
    print("[_publish_github] owner:", owner)
    print("[_publish_github] repo:", repo)
    api_base = "https://api.github.com"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if file_path is None:
        file_path = ".github/workflows/ci.yml"
    print("[_publish_github] file_path:", file_path)

    if commit_message is None:
        commit_message = f"ci: add {file_path} via YAML Wizard"
    print("[_publish_github] commit_message:", commit_message)

    target_branch = pr_branch if create_pr else branch
    print("[_publish_github] target_branch:", target_branch)

    try:
        # If creating a PR, first create the branch from the base
        if create_pr:
            print("[_publish_github] creating branch from", branch, "to", pr_branch)
            _github_create_branch(api_base, headers, owner, repo, branch, pr_branch)

        # Check if file already exists (to get its SHA for updates)
        print("[_publish_github] checking existing file sha")
        existing_sha = _github_get_file_sha(
            api_base, headers, owner, repo, file_path, target_branch,
        )

        # Create or update the file
        print("[_publish_github] encoding YAML content")
        content_b64 = base64.b64encode(yaml_content.encode()).decode()
        payload: dict = {
            "message": commit_message,
            "content": content_b64,
            "branch": target_branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha
            print("[_publish_github] existing_sha found:", existing_sha)
        else:
            print("[_publish_github] no existing_sha found, creating new file")

        print("[_publish_github] sending GitHub contents API request")
        resp = _request_with_retry(
            "PUT",
            f"{api_base}/repos/{owner}/{repo}/contents/{file_path}",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        file_url = resp.json().get("content", {}).get("html_url", "")
        print("[_publish_github] response file_url:", file_url)

        # Create PR if requested
        if create_pr:
            print("[_publish_github] creating pull request")
            pr_result = _github_create_pr(
                api_base, headers, owner, repo,
                head=pr_branch, base=branch,
                title=f"ci: add CI/CD pipeline via YAML Wizard",
                body=(
                    f"This PR adds a CI/CD pipeline generated by YAML Wizard.\n\n"
                    f"**File:** `{file_path}`\n\n"
                    f"Please review the workflow before merging."
                ),
            )
            return PublishResult(
                success=True,
                message=f"Pull request created: {pr_result}",
                url=pr_result,
            )

        return PublishResult(
            success=True,
            message=f"File committed to {target_branch}: {file_path}",
            url=file_url,
        )
    
    except httpx.HTTPStatusError as e:
        error_body = e.response.text

        status = e.response.status_code
        if status == 401:
            return PublishResult(success=False, message="Authentication failed — check your token")
        elif status == 403:
            return PublishResult(success=False, message="Permission denied — missing required scopes")
        elif status == 404:
            return PublishResult(success=False, message=f"Repository not found: {owner}/{repo}")
        elif status == 409:
            return PublishResult(success=False, message=f"Conflict — file may have changed. {error_body}")
        elif status == 422:
            return PublishResult(success=False, message=f"Validation error: {error_body}")
        elif status == 500:
            return PublishResult(success=False, message="GitHub server error (500)")
        elif status in (502, 503, 504):
            return PublishResult(success=False, message=f"GitHub unavailable ({status}) — retry later")
        else:
            return PublishResult(success=False, message=f"HTTP error {status}: {error_body}")

    except httpx.RequestError as e:
        return PublishResult(success=False, message=f"Network error: {str(e)}")

    except ValueError as e:
        return PublishResult(success=False, message=str(e))
    
    except Exception as e:
        print(f"DEBUG: Caught custom exception: {str(e)}") 
        return PublishResult(success=False, message=str(e))



def _github_create_branch(
    api_base: str, headers: dict, owner: str, repo: str,
    source_branch: str, new_branch: str,) -> None:
    
    """Create a new branch from a source branch."""

    print("[_github_create_branch] starting branch creation")
    print("[_github_create_branch] source_branch:", source_branch)
    print("[_github_create_branch] new_branch:", new_branch)

    # Get the SHA of the source branch
    try:
        resp = httpx.get(f"{api_base}/repos/{owner}/{repo}/git/ref/heads/{source_branch}", headers=headers)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise Exception(f"Source branch '{source_branch}' not found in '{owner}/{repo}'. (Note: Check if the branch is 'main' or 'master')")
        raise e

    sha = resp.json()["object"]["sha"]
    print("[_github_create_branch] source sha:", sha)

    # Create the new branch
    print("[_github_create_branch] creating new branch ref")
    try:
        resp = _request_with_retry(
            "POST",
            f"{api_base}/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{new_branch}", "sha": sha},
            headers=headers,
            timeout=15.0,
        )
        print("[_github_create_branch] branch creation succeeded or already existed")


    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            # We treat 404 on a POST as a permission issue if we know the repo exists
            raise Exception("PERMISSION_DENIED: You do not have write access to this repository. Please provide a repository where you have owner or collaborator permissions.")



def _github_get_file_sha(
    api_base: str, headers: dict, owner: str, repo: str, path: str, branch: str,) -> str | None:

    """Get the SHA of an existing file (needed for updates)."""

    try:
        resp = httpx.get(
            f"{api_base}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch},
            headers=headers,
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json().get("sha")
    except httpx.HTTPError:
        pass
    return None


def _github_create_pr(
    api_base: str, headers: dict, owner: str, repo: str,
    head: str, base: str, title: str, body: str,) -> str:

    """Create a pull request and return its URL."""

    resp = _request_with_retry(
        "POST",
        f"{api_base}/repos/{owner}/{repo}/pulls",
        json={"title": title, "body": body, "head": head, "base": base},
        headers=headers,
        timeout=15.0,
    )
    return resp.json().get("html_url", "")




# ── GITLAB ──────────────────────────────────────────────────────────────────


def _publish_gitlab(
    yaml_content: str,
    repo_url: str,
    token: str,
    file_path: str | None,
    branch: str,
    commit_message: str | None,
    create_pr: bool,
    pr_branch: str,
    gitlab_project_id = int | None) -> PublishResult:

    """Publish YAML to a GitLab repository via the Repository Files API."""
    """directly to a branch or via merge request"""

    parsed = urlparse(repo_url)
    #https://gitlab.com/group/project
    #becomes: scheme: https + hostname: gitlab.com + path: /group/project
    #GitLab has multiple hosts so we extract it from repos, companies can have diff host than the public one
    gitlab_host = f"{parsed.scheme}://{parsed.hostname}"
    
    api_base = f"{gitlab_host}/api/v4" #GitLab API version 4 is the standard REST API base.
    headers = {"Authorization": f"Bearer {token}"}
    
    if file_path is None:
        file_path = ".gitlab-ci.yml"

    if commit_message is None:
        commit_message = f"ci: add {file_path} via YAML Wizard"

    target_branch = pr_branch if create_pr else branch
    print("PROJECT ID:", gitlab_project_id)
    #print("TARGET BRANCH:", target_branch)
    try:
        # Create branch if making merge request
        if create_pr:
            httpx.post(
                f"{api_base}/projects/{gitlab_project_id}/repository/branches",
                params={"branch": pr_branch, "ref": branch},
                headers=headers,
                timeout=15.0,
            )
        print(" before FILE EXISTS:")


        # Check if file exists
        file_exists = _gitlab_file_exists(api_base, headers, gitlab_project_id, file_path, target_branch)
        print("FILE EXISTS:", file_exists)
        # Create or update file
        encoded_path = file_path.replace("/", "%2F")
        payload = {
            "branch": target_branch,
            "content": yaml_content,
            "commit_message": commit_message,
        }

        if file_exists:
            resp = httpx.put(
                f"{api_base}/projects/{gitlab_project_id}/repository/files/{encoded_path}",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
        else:
            resp = httpx.post(
                f"{api_base}/projects/{gitlab_project_id}/repository/files/{encoded_path}",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
        resp.raise_for_status()

        # Create merge request if requested
        if create_pr:
            mr_resp = httpx.post(
                f"{api_base}/projects/{gitlab_project_id}/merge_requests",
                json={
                    "source_branch": pr_branch,
                    "target_branch": branch,
                    "title": "ci: add CI/CD pipeline via YAML Wizard",
                    "description": (
                        f"This MR adds a CI/CD pipeline generated by YAML Wizard.\n\n"
                        f"**File:** `{file_path}`\n\n"
                        f"Please review the pipeline before merging."
                    ),
                },
                headers=headers,
                timeout=15.0,
            )
            mr_resp.raise_for_status()
            mr_url = mr_resp.json().get("web_url", "")
            return PublishResult(
                success=True,
                message=f"Merge request created: {mr_url}",
                url=mr_url,
            )

        file_url = f"{gitlab_host}/{repo_url.split(gitlab_host)[-1].strip('/')}/blob/{target_branch}/{file_path}"
        return PublishResult(
            success=True,
            message=f"File committed to {target_branch}: {file_path}",
            url=file_url,
        )
    except httpx.HTTPStatusError as e:
        status = e.response.status_code

        if status == 401:
            return PublishResult(success=False, message="Authentication failed — check your token")
        elif status == 403:
            return PublishResult(success=False, message="Permission denied — token may lack write access")
        elif status == 404:
            return PublishResult(success=False, message="Repository not found")
        elif status == 409:
            return PublishResult(success=False, message="Conflict — resource already exists or was modified")
        elif status == 422:
            return PublishResult(success=False, message="Validation error — check request payload")
        elif status == 429:
            return PublishResult(success=False, message="Rate limit exceeded — try again later")
        elif status >= 500:
            return PublishResult(success=False, message="GitLab server error — try again later")

        return PublishResult(
            success=False,
            message=f"GitLab API error (HTTP {status})"
        )
    except httpx.HTTPError as e:
        return PublishResult(
            success=False,
            message="Network error while contacting GitLab"
        )
    except ValueError as e:
        return PublishResult(success=False, message=str(e))



def _gitlab_file_exists(api_base: str, headers: dict, project_id: str, path: str, branch: str) -> bool:
    encoded_path = quote(path, safe="") #encodes ALL unsafe URL characters, not just /, whitespaces, # 

    url = f"{api_base}/projects/{project_id}/repository/files/{encoded_path}"

    resp = httpx.get(
        url,
        params={"ref": branch},
        headers=headers,
        timeout=15.0,
    )

    print("FILE CHECK:", resp.status_code, resp.text)

    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise Exception(f"GitLab file check failed: {resp.status_code} - {resp.text}")
    