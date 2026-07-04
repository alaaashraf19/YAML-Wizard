import os
import httpx
from dotenv import load_dotenv
from .ci_collector import CICollector
from urllib.parse import quote
from schemas.dashboard import CollectorsRepositoryDetail, CIArtifact, SyncStatus
from sqlalchemy.ext.asyncio import AsyncSession
from models.repository_model import JobTiming, PipelineRun
from sqlalchemy import select
from datetime import datetime, timezone
from ..recommendations_services.processor_services import compute_job_comparison, compute_run_comparison
from ..test_parsers.ParserRegistry import ParserRegistry
from .collectors_utils import parse_duration, _parse_ts, process_test_batch, extract_test_reports_from_zip

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
        