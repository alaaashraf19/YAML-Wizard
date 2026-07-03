import os
import base64
from dotenv import load_dotenv
from datetime import datetime, timezone
import httpx
import yaml
from schemas.dashboard import CIArtifact, CollectorsRepositoryDetail, SyncStatus
from .ci_collector import CICollector
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..recommendations_services.processor_services import compute_job_comparison, compute_run_comparison
from models.repository_model import JobTiming, PipelineRun, Repository
from models.pipeline_model import Pipeline
from models.project_model import Project
from models.pipeline_version_model import PipelineVersion
from ..test_parsers.ParserRegistry import ParserRegistry
from .collectors_utils import parse_duration, _parse_ts, process_test_batch, extract_test_reports_from_zip
import asyncio

load_dotenv()

class GitHubCollector(CICollector):
    
    """Fetches CI/CD data from the GitHub Actions API"""

    BASE_URL = "https://api.github.com"

    def __init__(self ,token: str) -> None:
        
        self.token = token
        
        if not self.token:
            raise ValueError("GitHub access token not provided. Set GITHUB_ACCESS_TOKEN in environment variables.")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        self._client = httpx.AsyncClient(headers=self.headers, timeout=30.0)


    def repo_info(self,ctx: CollectorsRepositoryDetail):
        return ctx.github_owner, ctx.github_repo
    
    async def close(self) -> None:
        await self._client.aclose()

    #if branch is not specified github api returns runs from all branches
    async def get_runs(self, ctx: CollectorsRepositoryDetail, per_page: int = 30, page: int = 1, branch: str | None = None,) -> list[dict]:
        
        """Fetch workflow runs for a repository"""
        owner, repo_name = self.repo_info(ctx)
        params: dict = {"per_page": per_page, "page": page}
        if branch:
            params["branch"] = branch
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo_name}/actions/runs",
            params=params,
            )
        resp.raise_for_status()
        return resp.json().get("workflow_runs", [])
    

    async def get_jobs(self, ctx: CollectorsRepositoryDetail, run_id: int) -> list[dict]:
        
        """Fetch jobs for a specific workflow run"""
        owner, repo_name = self.repo_info(ctx)
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo_name}/actions/runs/{run_id}/jobs",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        return resp.json().get("jobs", [])

    async def get_logs(self, ctx: CollectorsRepositoryDetail, job_id: int) -> str:
        
        """Fetch raw job logs from GitHub API"""
        owner, repo_name = self.repo_info(ctx)
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo_name}/actions/jobs/{job_id}/logs",
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    async def get_artifacts(self, ctx, run_id: int) -> list[CIArtifact]:

        owner, repo = self.repo_info(ctx)

        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        )
        resp.raise_for_status()

        data = resp.json().get("artifacts", [])

        return [
            CIArtifact(
                id=str(a["id"]),
                name=a["name"],
                download_url=a["archive_download_url"],
                provider="github",
            )
            for a in data
        ]


    async def download_artifact(self, artifact: CIArtifact) -> bytes:

        """Download artifact zip file"""

        resp = await self._client.get(artifact.download_url, follow_redirects=True)#downloads the file into memory as an HTTP response.
        resp.raise_for_status()
        return resp.content
    

    async def sync(self,ctx: CollectorsRepositoryDetail, db: AsyncSession) -> SyncStatus:
        
        """Fetch runs, jobs, and test results from GitHub Actions."""
        
        runs_synced = 0
        jobs_synced = 0
        tests_parsed = 0

        try:
            #Fetch recent workflow runs

            ##update the max runs logic
            max_runs = os.getenv("MAX_RUNS_PER_SYNC")
            if max_runs is None:
                raise ValueError("MAX_RUNS_PER_SYNC not found as env variable or invalid. Please set it to a positive integer.")
            raw_runs = await self.get_runs(ctx, per_page=int(max_runs))

            for raw_run in raw_runs:
                run_tests = 0
                external_id = raw_run["id"] # GitHub's unique run ID

                #Skip if already synced
                #so do not insert the workflow run again if it already exists in the db
                existing = await db.execute(select(PipelineRun).where(PipelineRun.external_id == external_id, PipelineRun.repo_id == ctx.repo.id))

                if existing.scalar_one_or_none():
                    continue

                if raw_run.get("status") != "completed":
                    continue

                duration = parse_duration(raw_run.get("run_started_at"), raw_run.get("updated_at"),)
                
                pipeline_run = PipelineRun(
                    repo_id=ctx.repo.id,  
                    external_id=external_id,
                    commit_hash=raw_run.get("head_sha", ""),
                    commit_message=raw_run.get("head_commit", {}).get("message") if raw_run.get("head_commit") else raw_run.get("display_title"),
                    branch=raw_run.get("head_branch"),
                    status=raw_run.get("status", "unknown"), #queued, in_progress, completed
                    conclusion=raw_run.get("conclusion"),#status == "completed"
                    total_duration_s=duration,
                    started_at=_parse_ts(raw_run.get("run_started_at")),
                    completed_at = _parse_ts(raw_run.get("updated_at")) if raw_run.get("status") == "completed" else None,
                )

                db.add(pipeline_run)
                await db.flush() # flush to get pipeline_run.id for jobs, commit later#

                #compare to previous run
                pipeline_run.compared_to_prev_pct = await compute_run_comparison(pipeline_run, ctx.repo.id, db,)
                
                # print(f"Run {pipeline_run.id} compared to previous run: {pipeline_run.compared_to_prev_pct}%")

                #fetch jobs for the pipeline run
                raw_jobs = await self.get_jobs(ctx, external_id)
                for raw_job in raw_jobs:
                    job_duration = parse_duration(raw_job.get("started_at"), raw_job.get("completed_at"),)
                    job = JobTiming(
                        run_id=pipeline_run.id,
                        external_id=raw_job["id"],
                        job_name=raw_job.get("name", "unknown"),
                        status=raw_job.get("conclusion", raw_job.get("status", "unknown")),
                        duration_s=job_duration,
                        started_at=_parse_ts(raw_job.get("started_at")),
                        completed_at=_parse_ts(raw_job.get("completed_at")),
                    )

                    if job_duration is not None:
                        job.compared_to_prev_pct = await compute_job_comparison(job.job_name, job_duration, ctx.repo.id, pipeline_run.id, db,)
                    db.add(job)
                    await db.flush()  #to get job.id before syncing tests

                    job_tests = await self.get_artifacts_for_run(ctx,pipeline_run.id,db)

                    if job_tests == 0:
                        job_tests = await self.sync_job_tests(ctx, job, db)
                    
                    tests_parsed += job_tests
                    
                    # print(f"[Final] Synced job {job.job_name} with {tests_parsed} tests parsed so far")
                    if tests_parsed > 0:
                        # print(f"Job {job.job_name}: Parsed {tests_parsed} tests")
                        pass
                    jobs_synced += 1
                
                runs_synced += 1
            ctx.repo.last_synced_at = datetime.now(timezone.utc)
            await db.commit()

                    
        except Exception as e:
                await db.rollback()
                return SyncStatus(
                    repo_id=ctx.repo.id,
                    runs_synced=runs_synced,
                    jobs_synced=jobs_synced,
                    tests_parsed=tests_parsed,
                    message=f"Github Sync error: {e}",
                )
        finally:
            await self.close()

        return SyncStatus(
                repo_id=ctx.repo.id,
                runs_synced=runs_synced,
                jobs_synced=jobs_synced,
                tests_parsed=tests_parsed,
                message=f"Synced {runs_synced} runs, {jobs_synced} jobs, {tests_parsed} tests",
            )             

    async def get_artifacts_for_run(self, ctx: CollectorsRepositoryDetail, run_id: int, db: AsyncSession) -> int:
        
        parser_registry = ParserRegistry()
        tests_found = 0

        parts = ctx.repo.full_name.split("/")
        owner, repo_name = parts
        repo_id = ctx.repo.id

        try:
            # print(f"[sync-tests] Fetching artifacts for (owner={owner}, repo={repo_name}, run_id={run_id})", flush=True)
            artifacts = await self.get_artifacts(ctx, run_id)
            
            # print(f"[sync-tests] Found {len(artifacts)} total artifacts", flush=True)
            
            for artifact in artifacts:
                artifact_name = artifact.name
                # print(f"[sync-tests] Checking artifact: {artifact_name}", flush=True)
                
                if any(name in artifact_name.lower() for name in ["test", "report", "result", "junit", "coverage"]):
                    
                    try:
                        # print(f"[sync-tests] Downloading artifact: {artifact_name}", flush=True)

                        zip_data = await self.download_artifact(artifact)

                        # print(f"[sync-tests] Downloaded artifact {artifact_name}", flush=True)
                        
                        reports = extract_test_reports_from_zip(zip_data)

                        # print(f"[sync-tests] Extracted {len(reports)} report files from {artifact_name}", flush=True)
                        
                        for filename, content, ext in reports:
                            # print(f"[sync-tests] Processing report file: {filename} (type: {ext}, size: {len(content)} bytes)", flush=True)
                            
                            try:
                                parsed_tests = parser_registry.parse(content, filename)

                                # print(f"[sync-tests] Parsed {len(parsed_tests)} tests from {filename}", flush=True)
                                
                                tests_found += await process_test_batch(parsed_tests, run_id, repo_id, db, job = None)
                                
                                # print(f"[sync-tests] Added test to DB. Total tests found: {tests_found}", flush=True)

                            except Exception as e:
                                # print(f"[sync-tests] ERROR parsing {filename}: while snying job tests function: {str(e)}", flush=True)
                                pass
                    
                    except Exception as e:
                        # print(f"[sync-tests] ERROR downloading/extract artifact {artifact_name}:  while snying job tests function:: {str(e)}", flush=True)
                        pass
                else:
                    # print(f"[sync-tests] Skipping non-test artifact: {artifact_name}", flush=True)
                    pass
        
        except Exception as e:
            # print(f"[sync-tests] ERROR fetching artifacts: {str(e)}", flush=True)
            pass
        
        #Parse logs if no test reports found
        # print(f"[sync-tests] Tests found in artifacts: {tests_found}. Will {'skip logs' if tests_found > 0 else 'parse logs'}", flush=True)
        return tests_found



    async def sync_job_tests(self, ctx: CollectorsRepositoryDetail, job: JobTiming, db: AsyncSession):
        
        """Collect test results for a job"""
        
        repo_id = ctx.repo.id
            
        parser_registry = ParserRegistry()
        tests_found=0
        try:
            log_content = await self.get_logs(ctx, job.external_id)

            try:
                parsed_tests = parser_registry.parse(log_content, "job.log")
                
                # print(f"[sync-tests] Parsed {len(parsed_tests)} tests from logs", flush=True)

                tests_found += await process_test_batch(parsed_tests, job.run_id, repo_id, db,  job,)

            except Exception as e:
                # print(f"[sync-tests] ERROR parsing logs: {str(e)}", flush=True)
                pass
            
        except Exception as e:
            # print(f"[sync-tests] ERROR fetching logs: {str(e)}", flush=True)
            pass
        
        # print(f"[sync-tests] Completed sync_job_tests from logs for {job.job_name}: {tests_found} tests found", flush=True)
        
        return tests_found


    async def get_repository_contents(
            self,
            ctx: CollectorsRepositoryDetail,
            path: str = ".github/workflows",
    ) -> list[dict]:
        """Fetch repository contents from GitHub API."""
        owner, repo_name = self.repo_info(ctx)

        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/contents/{path}"

        resp = await self._client.get(url)

        if resp.status_code == 404:
            return []

        resp.raise_for_status()
        return resp.json()

    async def get_file_content(
            self,
            ctx: CollectorsRepositoryDetail,
            file_path: str,
            branch: str = "main"
    ) -> str | None:
        """Fetch the content of a specific file from the repository."""
        owner, repo_name = self.repo_info(ctx)

        import urllib.parse
        encoded_path = urllib.parse.quote(file_path)

        url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/contents/{encoded_path}"

        try:
            resp = await self._client.get(url, params={"ref": branch})

            if resp.status_code == 404:
                return None

            resp.raise_for_status()

            data = resp.json()

            if "content" in data:
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content

            return None

        except Exception as e:
            # print(f"[GitHubCollector] Error fetching file {file_path}: {e}")
            return None

    async def find_yaml_files(
            self,
            ctx: CollectorsRepositoryDetail,
    ) -> list[dict]:
        """Find all YAML files in common CI/CD directories."""
        yaml_files = []

        paths_to_check = [
            ".github/workflows",
            ".github/actions",
            ".github/ci",
            ".github",
        ]

        for path in paths_to_check:
            try:
                contents = await self.get_repository_contents(ctx, path)

                if not contents:
                    continue

                if isinstance(contents, dict):
                    contents = [contents]

                for item in contents:
                    if item.get("type") == "file":
                        filename = item.get("name", "")
                        if filename.endswith((".yml", ".yaml")):
                            if self._is_ci_file(filename, path):
                                content = await self.get_file_content(
                                    ctx,
                                    item.get("path"),
                                    branch=ctx.repo.default_branch or "main"
                                )
                                if content:
                                    yaml_files.append({
                                        "path": item.get("path"),
                                        "name": filename,
                                        "content": content,
                                        "sha": item.get("sha"),
                                        "branch": ctx.repo.default_branch or "main",
                                    })
            except Exception as e:
                # print(f"[GitHubCollector] Error finding YAML files in {path}: {e}")
                continue

        return yaml_files

    def _is_ci_file(self, filename: str, path: str) -> bool:
        """Check if a file is a CI/CD configuration file."""
        ci_patterns = [
            "workflow", "ci", "cd", "deploy", "build",
            "test", "release", "pipeline", "actions"
        ]

        name_lower = filename.lower()
        path_lower = path.lower()

        if any(p in path_lower for p in ["workflow", "ci", "actions", "pipeline"]):
            return True

        if any(p in name_lower for p in ci_patterns):
            return True

        return False

    def _extract_description(self, content: str) -> str | None:
        """Extract description from YAML content."""
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                if "description" in data:
                    return data["description"]
                if "name" in data:
                    return data["name"]
            return None
        except:
            return None

    async def save_yaml_files(
            self,
            ctx: CollectorsRepositoryDetail,
            db: AsyncSession
    ) -> tuple[int, int]:
        """
        Fetch YAML files and save them as Pipeline records with commit info.
        Returns (saved_count, updated_count)
        """
        saved = 0
        updated = 0
        yaml_files = await self.find_yaml_files(ctx)
        project = await self._get_project_for_repo(ctx.repo.id, db)
        if not project:
            return 0, 0

        for yf in yaml_files:
            branch = yf.get("branch", ctx.repo.default_branch or "main")
            # get latest commit info
            commit_info = await self.get_file_with_commit_info(ctx, yf["path"], branch=branch)

            existing = await db.execute(
                select(Pipeline).where(
                    Pipeline.project_id == project.id,
                    Pipeline.path == yf["path"],
                    Pipeline.branch == branch
                )
            )
            existing_version = await db.execute(
                select(PipelineVersion).where(
                    PipelineVersion.project_id == project.id,
                    PipelineVersion.path == yf["path"],
                    PipelineVersion.branch == branch,
                    PipelineVersion.is_active == True
                )
            )
            pipeline = existing.scalar_one_or_none()
            active_version = existing_version.scalar_one_or_none()
            if pipeline:
                if active_version:
                    continue
                else:
                    # update if content changed or commit hash changed
                    if (pipeline.content != yf["content"]) or (
                            commit_info and pipeline.commit_hash != commit_info.get("commit_hash")):
                        pipeline.content = yf["content"]
                        pipeline.updated_at = datetime.utcnow()
                        pipeline.name = yf["name"]
                        pipeline.description = self._extract_description(yf["content"])
                        if commit_info:
                            pipeline.commit_hash = commit_info.get("commit_hash")
                            pipeline.commit_author = commit_info.get("commit_author")
                            pipeline.commit_message = commit_info.get("commit_message")
                            if commit_info and commit_info.get("committed_at"):
                                committed_at = commit_info["committed_at"]
                                if isinstance(committed_at, str):
                                    # Convert to naive UTC
                                    aware = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
                                    naive = aware.replace(tzinfo=None)
                                    pipeline.committed_at = naive
                                else:
                                    # If it's already a datetime, ensure it's naive
                                    if committed_at.tzinfo is not None:
                                        pipeline.committed_at = committed_at.replace(tzinfo=None)
                                    else:
                                        pipeline.committed_at = committed_at
                        pipeline.is_active = True

                        await db.commit()
                        await db.refresh(pipeline)
                        updated += 1
            else:
                new_pipe = Pipeline(
                    name=yf["name"],
                    content=yf["content"],
                    path=yf["path"],
                    branch=branch,
                    is_generated_by_wizard=False,
                    is_active=True,
                    description=self._extract_description(yf["content"]),
                    project_id=project.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                if commit_info:
                    new_pipe.commit_hash = commit_info.get("commit_hash")
                    new_pipe.commit_author = commit_info.get("commit_author")
                    new_pipe.commit_message = commit_info.get("commit_message")
                    if commit_info and commit_info.get("committed_at"):
                        committed_at = commit_info["committed_at"]
                        if isinstance(committed_at, str):
                            # Convert to naive UTC
                            aware = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
                            naive = aware.replace(tzinfo=None)
                            new_pipe.committed_at = naive
                        else:
                            # If it's already a datetime, ensure it's naive
                            if committed_at.tzinfo is not None:
                                new_pipe.committed_at = committed_at.replace(tzinfo=None)
                            else:
                                new_pipe.committed_at = committed_at
                db.add(new_pipe)
                await db.commit()
                await db.refresh(new_pipe)
                saved += 1

        return saved, updated

    async def _get_project_for_repo(
            self,
            repo_id: int,
            db: AsyncSession
    ) -> Project | None:
        """Get the project associated with a repository."""
        result = await db.execute(
            select(Project).where(Project.repo_id == repo_id)
        )
        return result.scalar_one_or_none()

    async def get_file_with_commit_info(
            self,
            ctx: CollectorsRepositoryDetail,
            file_path: str,
            branch: str = "main"
    ) -> dict | None:
        """
        Fetch file content AND the latest commit info for that file.
        Returns dict with content, commit_hash, commit_author, commit_message, committed_at.
        """
        owner, repo_name = self.repo_info(ctx)
        import urllib.parse
        encoded_path = urllib.parse.quote(file_path)

        try:
            # 1) Get file content
            url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/contents/{encoded_path}"
            resp = await self._client.get(url, params={"ref": branch})
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if "content" not in data:
                return None

            content = base64.b64decode(data["content"]).decode("utf-8")

            # 2) Get latest commit for this file
            commits_url = f"{self.BASE_URL}/repos/{owner}/{repo_name}/commits"
            params = {"path": file_path, "sha": branch, "per_page": 1}
            commits_resp = await self._client.get(commits_url, params=params)
            commits_resp.raise_for_status()
            commits = commits_resp.json()

            result = {
                "content": content,
                "branch": branch,
                "file_sha": data.get("sha"),
            }

            if commits and len(commits) > 0:
                latest = commits[0]
                result["commit_hash"] = latest.get("sha")
                result["commit_author"] = latest.get("commit", {}).get("author", {}).get("name")
                result["commit_email"] = latest.get("commit", {}).get("author", {}).get("email")
                result["commit_message"] = latest.get("commit", {}).get("message", "")
                result["committed_at"] = latest.get("commit", {}).get("author", {}).get("date")
            else:
                result["commit_hash"] = None
                result["commit_author"] = None
                result["commit_message"] = None
                result["committed_at"] = None

            return result

        except Exception as e:
            # print(f"[GitHubCollector] Error fetching file with commit info {file_path}: {e}")
            return None