import os
import base64
import httpx
from dotenv import load_dotenv

from models import PipelineVersion
from .ci_collector import CICollector
from urllib.parse import quote
from schemas.dashboard import CollectorsRepositoryDetail, CIArtifact, SyncStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from ..recommendations_services.processor_services import compute_job_comparison, compute_run_comparison
from models.repository_model import JobTiming, PipelineRun
from models.pipeline_model import Pipeline
from models.project_model import Project
from ..test_parsers.ParserRegistry import ParserRegistry
from .collectors_utils import parse_duration, _parse_ts, process_test_batch, extract_test_reports_from_zip
import yaml

load_dotenv()

class GitLabCollector(CICollector): 
    """Fetches CI/CD data from the GitLab Pipelines API"""

    BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, token: str | None = None) -> None:
        
        self.token = token or os.getenv("GITLAB_ACCESS_TOKEN")

        if not self.token:
            raise ValueError("GitLab access token not provided.")

        self.headers = {
            "PRIVATE-TOKEN": self.token,
        }

        self._client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()


    async def get_project_id(self, full_name: str) -> int:

        encoded = quote(full_name, safe="")

        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{encoded}"
        )

        resp.raise_for_status()

        data = resp.json()

        return data["id"]
    
    def _proj_id(self, ctx: CollectorsRepositoryDetail) -> int:
        """Helper to get project ID from context or GitLab API"""

        project_id = ctx.gitlab_project_id
        if not project_id:
            raise ValueError("Missing GitLab project_id in context")
        return project_id
        
    async def get_runs(self, ctx: CollectorsRepositoryDetail, per_page: int = 30, page: int = 1, branch: str | None = None,) -> list[dict]:
        """Fetch CI/CD pipelines for a project"""

        project_id = self._proj_id(ctx)
        params = {"per_page": per_page, "page": page}
        if branch:
            params["ref"] = branch

        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{project_id}/pipelines",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


    async def get_jobs(self, ctx: CollectorsRepositoryDetail, run_id: int) -> list[dict]:       
        """Fetch jobs for a pipeline"""

        project_id = self._proj_id(ctx)
        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{project_id}/pipelines/{run_id}/jobs",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        return resp.json()


        
    async def get_logs(self, ctx: CollectorsRepositoryDetail, job_id: int) -> str:
        """Fetch raw job trace/logs"""

        project_id = self._proj_id(ctx)
        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{project_id}/jobs/{job_id}/trace",
        )
        resp.raise_for_status()
        return resp.text


    #here artifacts are related to jobs not runs diff from github actions
    async def get_artifacts(self, ctx: CollectorsRepositoryDetail, job_id: int) -> list[CIArtifact]:  
        """GitLab does not expose artifacts exactly like GitHub runs;
        artifacts are usually tied to jobs."""

        project_id = self._proj_id(ctx)
        return [
            CIArtifact(
                id=str(job_id),
                name="job_artifact",
                download_url=f"{self.BASE_URL}/projects/{project_id}/jobs/{job_id}/artifacts",
                provider="gitlab",
            )
        ]


    async def download_artifact(self, artifact: CIArtifact) -> bytes:

        resp = await self._client.get(artifact.download_url,follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    

    async def sync(self, ctx: CollectorsRepositoryDetail, db: AsyncSession) -> SyncStatus:
        
        """Fetch runs, jobs, and test results from Gitlab Actions."""
        
        runs_synced = 0
        jobs_synced = 0
        tests_parsed = 0

        try:
            #Fetch recent workflow runs

            ##update the max runs logic
            max_runs = os.getenv("MAX_RUNS_PER_SYNC")
            if max_runs is None:
                raise ValueError("MAX_RUNS_PER_SYNC not found as env variable or invalid. Please set it to a positive integer.")
            pipelines  = await self.get_runs(ctx, per_page=int(max_runs))

            for pipeline in pipelines:
                external_id = pipeline["id"] # GitLab's unique pipeline ID

                existing = await db.execute(select(PipelineRun).where(PipelineRun.external_id == external_id,PipelineRun.repo_id == ctx.repo.id))

                if existing.scalar_one_or_none():
                    continue

                if pipeline.get("status") not in {"success", "failed"}:
                    continue

                duration = parse_duration(pipeline.get("created_at"), pipeline.get("finished_at"),)
                
                run = PipelineRun(
                    repo_id=ctx.repo.id,
                    external_id=external_id,
                    commit_hash=pipeline.get("sha", ""),
                    branch=pipeline.get("ref"),
                    status=pipeline.get("status"),
                    conclusion=pipeline.get("status"),
                    total_duration_s=duration,
                    started_at=_parse_ts(pipeline.get("created_at")),
                    completed_at=_parse_ts(pipeline.get("finished_at")),
                )

                db.add(run)
                await db.flush() # flush to get pipeline_run.id for jobs, commit later#

                #compare to previous run
                run.compared_to_prev_pct = await compute_run_comparison(run, ctx.repo.id, db,)
                
                # print(f"Run {run.id} compared to previous run: {run.compared_to_prev_pct}%")
                
                #fetch jobs for the pipeline run
                raw_jobs = await self.get_jobs(ctx, external_id)

                for raw_job in raw_jobs:
                    job_tests=0

                    job_duration = parse_duration(raw_job.get("started_at"), raw_job.get("finished_at"),)

                    job = JobTiming(
                        run_id=run.id,
                        external_id=raw_job["id"],
                        job_name=raw_job.get("name", "unknown"),
                        status=raw_job.get("status"),
                        duration_s=job_duration,
                        started_at=_parse_ts(raw_job.get("started_at")),
                        completed_at=_parse_ts(raw_job.get("finished_at")),
                    )
                    if job_duration is not None:
                        job.compared_to_prev_pct = await compute_job_comparison(job.job_name, job_duration, ctx.repo.id, run.id, db,)
                    db.add(job)
                    await db.flush()  #to get job.id before syncing tests#


                    has_artifacts = (raw_job.get("artifacts_file")
                        and raw_job["artifacts_file"].get("filename")
                    )
                    if has_artifacts:
                        job_tests = await self.get_artifacts_for_job(run, ctx, job, db)
                    else:
                        # print(f"[sync-tests] No artifacts for job {job.job_name}")
                        pass

                    if job_tests == 0:
                        job_tests = await self.sync_job_tests(run,ctx,job, db,)
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
                    message=f"GitLab Sync error: {e}",
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
    
    async def get_artifacts_for_job(self, run: PipelineRun, ctx: CollectorsRepositoryDetail, job: JobTiming, db: AsyncSession) -> int:
        
        parser_registry = ParserRegistry()
        tests_found = 0
        
        try:
            # print(f"[sync-tests] Fetching artifacts for (repo={ctx.repo.full_name}, job_id={job.external_id})", flush=True)
            artifacts = await self.get_artifacts(ctx, job.external_id)
            
            # print(f"[sync-tests] Found {len(artifacts)} total artifacts", flush=True)
            
            for artifact in artifacts:

                artifact_name = artifact.name
                                    
                try:
                    # print(f"[sync-tests] Downloading artifact: {artifact_name}", flush=True)
                    pass

                    zip_data = await self.download_artifact(artifact)

                    # print(f"[sync-tests] Downloaded artifact {artifact_name}", flush=True)
                    
                    reports = extract_test_reports_from_zip(zip_data)

                    # print(f"[sync-tests] Extracted {len(reports)} report files from {artifact_name}", flush=True)
                    
                    for filename, content, ext in reports:
                        # print(f"[sync-tests] Processing report file: {filename} (type: {ext}, size: {len(content)} bytes)", flush=True)

                        try:
                            parsed_tests = parser_registry.parse(content, filename)

                            # print(f"[sync-tests] Parsed {len(parsed_tests)} tests from {filename}", flush=True)
                            
                            tests_found += await process_test_batch(parsed_tests, run.id, ctx.repo.id, db, job)
                            
                            # print(f"[sync-tests] Added test to DB. Total tests found: {tests_found}", flush=True)

                        
                        except Exception as e:
                            # print(f"[sync-tests] ERROR parsing {filename}: while snying job tests function: {str(e)}", flush=True)
                            pass
                
                except Exception as e:
                    # print(f"[sync-tests] ERROR downloading/extract artifact {artifact_name}:  while snying job tests function:: {str(e)}", flush=True)
                    pass
    
        except Exception as e:
            # print(f"[sync-tests] ERROR fetching artifacts: {str(e)}", flush=True)
            pass
        
        #Parse logs if no test reports found
        # print(f"[sync-tests] Tests found in artifacts: {tests_found}. Will {'skip logs' if tests_found > 0 else 'parse logs'}", flush=True)
        return tests_found
        

    async def sync_job_tests(self, run: PipelineRun,ctx: CollectorsRepositoryDetail, job: JobTiming, db: AsyncSession):
        
        """Collect test results for a job"""
            
        parser_registry = ParserRegistry()
        tests_found=0
        
        try:
            log_content = await self.get_logs(ctx, job.external_id)

            try:
                parsed_tests = parser_registry.parse(log_content, "job.log")
                
                # print(f"[sync-tests] Parsed {len(parsed_tests)} tests from logs", flush=True)

                tests_found = await process_test_batch(parsed_tests, run.id, ctx.repo.id, db,  job)
    
            except Exception as e:
                # print(f"[sync-tests] ERROR parsing logs: {str(e)}", flush=True)
                pass
            
        except Exception as e:
            # print(f"[sync-tests] ERROR fetching logs: {str(e)}", flush=True)
            return tests_found
        
        # print(f"[sync-tests] Completed sync_job_tests from logs for {job.job_name}: {tests_found} tests found", flush=True)
        return tests_found

    async def get_repository_files(
            self,
            ctx: CollectorsRepositoryDetail,
            path: str = "",
            ref: str = "main",
            recursive: bool = False,
    ) -> list[dict]:
        """Fetch repository files from GitLab API."""
        project_id = self._proj_id(ctx)

        url = f"{self.BASE_URL}/projects/{project_id}/repository/tree"
        params = {
            "path": path,
            "ref": ref,
            "recursive": "true" if recursive else "false",
            "per_page": 100,
        }

        all_items = []
        page = 1

        while True:
            params["page"] = page
            resp = await self._client.get(url, params=params)

            if resp.status_code == 404:
                return []

            resp.raise_for_status()
            items = resp.json()

            if not items:
                break

            all_items.extend(items)
            page += 1

            if len(items) < 100:
                break

        return all_items

    async def get_file_content(
            self,
            ctx: CollectorsRepositoryDetail,
            file_path: str,
            ref: str = "main"
    ) -> str | None:
        """Fetch the content of a specific file."""
        project_id = self._proj_id(ctx)
        encoded_path = quote(file_path, safe="")

        url = f"{self.BASE_URL}/projects/{project_id}/repository/files/{encoded_path}"
        params = {"ref": ref}

        try:
            resp = await self._client.get(url, params=params)

            if resp.status_code == 404:
                return None

            resp.raise_for_status()

            data = resp.json()

            if "content" in data:
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content

            return None

        except Exception as e:
            print(f"[GitLabCollector] Error fetching file {file_path}: {e}")
            return None

    async def find_yaml_files(
            self,
            ctx: CollectorsRepositoryDetail,
            ref: str = "main"
    ) -> list[dict]:
        """Find all YAML files in the repository."""
        yaml_files = []

        try:
            all_files = await self.get_repository_files(ctx, ref=ref,recursive=True)

            for file in all_files:
                if file.get("type") == "blob":
                    filename = file.get("name", "")
                    file_path = file.get("path", "")

                    if filename.endswith((".yml", ".yaml")):
                        if self._is_ci_file(filename, file_path):
                            content = await self.get_file_content(
                                ctx,
                                file_path,
                                ref=ref
                            )
                            if content:
                                yaml_files.append({
                                    "path": file_path,
                                    "name": filename,
                                    "content": content,
                                    "ref": ref,
                                })

        except Exception as e:
            print(f"[GitLabCollector] Error finding YAML files: {e}")

        return yaml_files

    def _is_ci_file(self, filename: str, path: str) -> bool:
        """Check if a file is a CI/CD configuration file."""
        ci_patterns = [
            "gitlab-ci", "ci", "cd", "deploy", "build",
            "test", "release", "pipeline", "actions", "workflow"
        ]

        name_lower = filename.lower()
        path_lower = path.lower()

        if filename == ".gitlab-ci.yml":
            return True

        if any(p in path_lower for p in ["ci", "pipeline", ".gitlab"]):
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

    async def save_yaml_files(
            self,
            ctx: CollectorsRepositoryDetail,
            db: AsyncSession
    ) -> tuple[int, int]:
        """Fetch YAML files and save them as Pipeline records with commit info.
        Returns (saved_count, updated_count).
        """
        saved = 0
        updated = 0
        ref = ctx.repo.default_branch or "main"
        yaml_files = await self.find_yaml_files(ctx, ref=ref)

        project = await self._get_project_for_repo(ctx.repo.id, db)
        if not project:
            return 0, 0

        for yf in yaml_files:
            # Get commit info for this file
            commit_info = await self.get_file_with_commit_info(
                ctx, yf["path"], ref=ref
            )

            existing = await db.execute(
                select(Pipeline).where(
                    Pipeline.project_id == project.id,
                    Pipeline.path == yf["path"],
                    Pipeline.branch == yf.get("ref", ref)
                )
            )
            existing_version = await db.execute(
                select(PipelineVersion).where(
                    PipelineVersion.project_id == project.id,
                    PipelineVersion.path == yf["path"],
                    PipelineVersion.branch == yf.get("ref", ref),
                    PipelineVersion.is_active == True
                )
            )
            pipeline = existing.scalar_one_or_none()
            active_version = existing_version.scalar_one_or_none()
            if pipeline:
                if active_version:
                    continue
                else:
                    # Update if content changed or commit hash changed
                    if (pipeline.content != yf["content"]) or (
                            commit_info and pipeline.commit_hash != commit_info.get("commit_hash")
                    ):
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
                    branch=yf.get("ref", ref),
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

    async def get_file_with_commit_info(
            self,
            ctx: CollectorsRepositoryDetail,
            file_path: str,
            ref: str = "main"
    ) -> dict | None:
        """
        Fetch file content AND the latest commit info for that file from GitLab.
        """
        project_id = self._proj_id(ctx)
        encoded_path = quote(file_path, safe="")

        try:
            # 1) File content
            url = f"{self.BASE_URL}/projects/{project_id}/repository/files/{encoded_path}"
            resp = await self._client.get(url, params={"ref": ref})
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
            if "content" not in data:
                return None

            content = base64.b64decode(data["content"]).decode("utf-8")

            # 2) Latest commit for file
            commits_url = f"{self.BASE_URL}/projects/{project_id}/repository/commits"
            params = {"path": file_path, "ref_name": ref, "per_page": 1}
            commits_resp = await self._client.get(commits_url, params=params)
            commits_resp.raise_for_status()
            commits = commits_resp.json()

            result = {
                "content": content,
                "branch": ref,
                "file_sha": data.get("last_commit_id"),
            }

            if commits and len(commits) > 0:
                latest = commits[0]
                result["commit_hash"] = latest.get("id")
                result["commit_author"] = latest.get("author_name")
                result["commit_email"] = latest.get("author_email")
                result["commit_message"] = latest.get("message", "")
                result["committed_at"] = latest.get("created_at")
            else:
                result["commit_hash"] = None
                result["commit_author"] = None
                result["commit_message"] = None
                result["committed_at"] = None

            return result

        except Exception as e:
            print(f"[GitLabCollector] Error fetching file with commit info {file_path}: {e}")
            return None