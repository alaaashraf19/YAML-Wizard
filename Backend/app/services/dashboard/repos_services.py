import httpx

from schemas.dashboard import RepoCreate
from sqlalchemy import select
from urllib.parse import urlparse, quote
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from models.user_model import User
from models.repository_model import Repository, PipelineRun
from services.dashboard.platform_collectors.gitlab_collector_services import GitLabCollector


#this is for adding a repo in dashboard by pasting the url, if it's not added in our user profile aka projects field
async def add_repo_service(body: RepoCreate, db, current_user):
    
    try:
        full_name, detected_platform, parsed_branch = _parse_repo_info(body.url)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Entered URL is invalid"
        )
    platform = body.platform or detected_platform
    
    if platform not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Unsupported platform. Only 'github' and 'gitlab' are supported.")
    
    from services.project_service import _resolve_token
    token, _ = await _resolve_token(user_id=current_user.id, platform=platform, repo_url=body.url, db=db)
    if not token:
            raise HTTPException(status_code=401, detail=f"Connect your {platform} account first ")
    
    if platform == "gitlab":
        gitlab_project_id = await _get_gitlab_proj_id(full_name, token)
        
    existing = await db.execute(select(Repository).where(Repository.full_name == full_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Repository '{full_name}' already tracked")

    repo = Repository(
        full_name=full_name,
        platform=platform,
        gitlab_project_id=gitlab_project_id if platform == "gitlab" else None,
        default_branch=body.default_branch,
        url=body.url.rstrip("/"),
        user_id=current_user.id

    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo
    


def _parse_repo_info(url: str) -> tuple[str, str, str | None]:
    """
    Returns: (full_name, platform, branch)
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    # Strip query string first (everything after ?)
    path = parsed.path
    parts = path.strip("/").split("/")

    branch = None
    full_name = None

    if "github" in host:
        platform = "github"

        if "tree" in parts:
            tree_idx = parts.index("tree")
            if len(parts) > tree_idx + 1:
                branch = parts[tree_idx + 1]
            parts = parts[:tree_idx]

        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")

        full_name = "/".join(parts[:2])

    elif "gitlab" in host:
        platform = "gitlab"

        if "tree" in parts:
            tree_idx = parts.index("tree")
            if len(parts) > tree_idx + 1:
                branch = parts[tree_idx + 1]
            parts = parts[:tree_idx]

        # Remove the "-" separator on GitLab
        if "-" in parts:
            dash_idx = parts.index("-")
            parts = parts[:dash_idx]

        if len(parts) < 2:
            raise ValueError("Invalid GitLab repository URL")

        full_name = "/".join(parts)

    else:
        raise ValueError("Unsupported repository host")

    if full_name and full_name.endswith(".git"):
        full_name = full_name[:-4]

    return full_name, platform, branch


async def get_repo_or_404(repo_id: int, db: AsyncSession, current_user: User):
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.user_id == current_user.id
        )
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

async def get_run_or_404(run_id: int, repo_id: int, db: AsyncSession):
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id,
            PipelineRun.repo_id == repo_id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

def parse_github_repo(url: str):
    parts = urlparse(url).path.strip("/").split("/")

    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL")

    owner = parts[0]
    repo = parts[1].removesuffix(".git")

    return owner, repo

async def get_github_default_branch(repo_url: str, token: str | None = None) -> str:
    
    owner, repo = parse_github_repo(repo_url)
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
        )
        response.raise_for_status()
    return response.json()["default_branch"]

def parse_gitlab_repo(url: str) -> str:
    
    parts = urlparse(url).path.strip("/").split("/")
    if "-" in parts:
        parts = parts[:parts.index("-")]
    elif "tree" in parts:
        parts = parts[:parts.index("tree")]

    if len(parts) < 2:
        raise ValueError("Invalid GitLab repository URL")

    return "/".join(parts).removesuffix(".git")

async def get_gitlab_default_branch(repo_url: str, token: str | None = None):
    repo_path = parse_gitlab_repo(repo_url)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    encoded = quote(repo_path, safe="")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gitlab.com/api/v4/projects/{encoded}",
            headers=headers
        )
        response.raise_for_status()
    return response.json()["default_branch"]


async def _get_gitlab_proj_id(full_name: str,token:str) -> int:
    gitLabCollector = GitLabCollector(token = token)
    try:
        gitlab_project_id = await gitLabCollector.get_project_id(full_name)
        return gitlab_project_id
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(404, "GitLab project not found")
        if e.response.status_code == 403:
            raise HTTPException(403, "Can't access GitLab project with provided token")
    finally:
        await gitLabCollector.close()