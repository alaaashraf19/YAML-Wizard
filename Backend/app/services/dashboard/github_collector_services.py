import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import httpx
from schemas.dashboard import CIArtifact, CollectorsRepositoryDetail, SyncStatus, TestResult
from .ci_collector import CICollector
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .processor_services import compute_job_comparison, compute_run_comparison, compute_test_avg_and_color
from models.dashboard import JobTiming, PipelineRun, Repository, TestRun
from .test_parsers.ParserRegistry import ParserRegistry
from typing import Tuple
from io import BytesIO
import zipfile

load_dotenv()

class GitHubCollector(CICollector):
    
    """Fetches CI/CD data from the GitHub Actions API"""

    BASE_URL = "https://api.github.com"

    def __init__(self ,token: str | None = None) -> None:
        
        self.token = token or os.getenv("GITHUB_ACCESS_TOKEN") # to be changed not get it from env 
        
        if not self.token:
            raise ValueError("GitHub access token not provided. Set GITHUB_ACCESS_TOKEN in environment variables.")
        
        auth_prefix = "Bearer" if self.token.startswith("github_pat_") else "token"
        self.headers = {
            "Authorization": f"{auth_prefix} {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._client = httpx.AsyncClient(headers=self.headers, timeout=30.0)


    def repo_info(ctx: CollectorsRepositoryDetail):
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
        
        owner, repo_name = self.repo_info(ctx)

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
                external_id = raw_run["id"] # GitHub's unique run ID

                #Skip if already synced
                #so do not insert the workflow run again if it already exists in the db
                existing = await db.execute(select(PipelineRun).where(PipelineRun.external_id == external_id))

                if existing.scalar_one_or_none():
                    continue

                if raw_run.get("status") != "completed":
                    continue

                duration = self.parse_duration(raw_run.get("run_started_at"), raw_run.get("updated_at"),)
                
                pipeline_run = PipelineRun(
                    repo_id=ctx.repo.id,  
                    external_id=external_id,
                    commit_hash=raw_run.get("head_sha", ""),
                    commit_message=raw_run.get("head_commit", {}).get("message") if raw_run.get("head_commit") else raw_run.get("display_title"),
                    branch=raw_run.get("head_branch"),
                    status=raw_run.get("status", "unknown"), #queued, in_progress, completed
                    conclusion=raw_run.get("conclusion"),#status == "completed"
                    total_duration_s=duration,
                    started_at=self._parse_ts(raw_run.get("run_started_at")),
                    completed_at = self._parse_ts(raw_run.get("updated_at")) if raw_run.get("status") == "completed" else None,
                )

                db.add(pipeline_run)
                await db.flush() # flush to get pipeline_run.id for jobs, commit later#

                #compare to previous run
                pipeline_run.compared_to_prev_pct = await compute_run_comparison(pipeline_run, ctx.repo.id, db,)
                
                print(f"Run {pipeline_run.id} compared to previous run: {pipeline_run.compared_to_prev_pct}%")
                
                tests_parsed += await self.get_artifacts_for_run(ctx.repo, external_id, db)

                #fetch jobs for the pipeline run
                raw_jobs = await self.get_jobs(ctx, external_id)
                for raw_job in raw_jobs:
                    job_duration = self.parse_duration(raw_job.get("started_at"), raw_job.get("completed_at"),)
                    job = JobTiming(
                        run_id=pipeline_run.id,
                        external_id=raw_job["id"],
                        job_name=raw_job.get("name", "unknown"),
                        status=raw_job.get("conclusion", raw_job.get("status", "unknown")),
                        duration_s=job_duration,
                        started_at=self._parse_ts(raw_job.get("started_at")),
                        completed_at=self._parse_ts(raw_job.get("completed_at")),
                    )

                    if job_duration is not None:
                        job.compared_to_prev_pct = await compute_job_comparison(job.job_name, job_duration, ctx.repo.id, pipeline_run.id, db,)
                    db.add(job)
                    await db.flush()  #to get job.id before syncing tests#

                    if tests_parsed == 0:
                        tests_parsed += await self.sync_job_tests(job, raw_job, db, owner, repo_name, ctx.repo)
                    
                    print(f"[Final] Synced job {job.job_name} with {tests_parsed} tests parsed so far")
                    if tests_parsed > 0:
                        print(f"Job {job.job_name}: Parsed {tests_parsed} tests")
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
                    message=f"Sync error: {e}",
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

    async def get_artifacts_for_run(self, repo: Repository, run_id: int, db: AsyncSession):
        
        parser_registry = ParserRegistry()

        parts = repo.full_name.split("/")
        owner, repo_name = parts
        repo_id = repo.id

        try:
            print(f"[sync-tests] Fetching artifacts for (owner={owner}, repo={repo_name}, run_id={run_id})", flush=True)
            artifacts = await self.get_artifacts(owner, repo_name, run_id)
            
            print(f"[sync-tests] Found {len(artifacts)} total artifacts", flush=True)
            
            for artifact in artifacts:
                artifact_name = artifact["name"]
                print(f"[sync-tests] Checking artifact: {artifact_name}", flush=True)
                
                if any(name in artifact["name"].lower() for name in ["test", "report", "result", "junit", "coverage"]):
                    
                    try:
                        print(f"[sync-tests] Downloading artifact: {artifact_name}", flush=True)

                        zip_data = await self.download_artifact(artifact["archive_download_url"])

                        print(f"[sync-tests] Downloaded artifact {artifact_name}", flush=True)
                        
                        reports = extract_test_reports_from_zip(zip_data)

                        print(f"[sync-tests] Extracted {len(reports)} report files from {artifact_name}", flush=True)
                        
                        for filename, content, ext in reports:
                            print(f"[sync-tests] Processing report file: {filename} (type: {ext}, size: {len(content)} bytes)", flush=True)
                            
                            try:
                                parsed_tests = parser_registry.parse(content, filename)

                                print(f"[sync-tests] Parsed {len(parsed_tests)} tests from {filename}", flush=True)
                                
                                tests_found += await self.process_test_batch(parsed_tests, run_id, repo_id, db, job = None)
                                
                                print(f"[sync-tests] Added test to DB. Total tests found: {tests_found}", flush=True)
                            except Exception as e:
                                print(f"[sync-tests] ERROR parsing {filename}: while snying job tests function: {str(e)}", flush=True)
                    
                    except Exception as e:
                        print(f"[sync-tests] ERROR downloading/extract artifact {artifact_name}:  while snying job tests function:: {str(e)}", flush=True)
                else:
                    print(f"[sync-tests] Skipping non-test artifact: {artifact_name}", flush=True)
        
        except Exception as e:
            print(f"[sync-tests] ERROR fetching artifacts: {str(e)}", flush=True)
        
        #Parse logs if no test reports found
        print(f"[sync-tests] Tests found in artifacts: {tests_found}. Will {'skip logs' if tests_found > 0 else 'parse logs'}", flush=True)
        

    async def sync_job_tests(self, repo: Repository, job: JobTiming, raw_job: dict, db: AsyncSession):
        
        """Collect test results for a job"""
        
        parts = repo.full_name.split("/")
        owner, repo_name = parts
        repo_id = repo.id

        job_id = raw_job["id"] #for test logs
            
        parser_registry = ParserRegistry()
        
        try:
            log_content = await self.get_logs(owner, repo_name, job_id)

            try:
                parsed_tests = parser_registry.parse(log_content, "job.log")
                
                print(f"[sync-tests] Parsed {len(parsed_tests)} tests from logs", flush=True)

                tests_found += await self.process_test_batch(parsed_tests, job.run_id, repo_id, db,  job,)

            except Exception as e:
                print(f"[sync-tests] ERROR parsing logs: {str(e)}", flush=True)
            
        except Exception as e:
            print(f"[sync-tests] ERROR fetching logs: {str(e)}", flush=True)
        
        print(f"[sync-tests] Completed sync_job_tests from logs for {job.job_name}: {tests_found} tests found", flush=True)
        
        return tests_found



    async def process_test_batch(self, parsed_tests: list[TestResult], run_id:int, repo_id:int, db: AsyncSession, job : JobTiming | None,):

        for test in parsed_tests:

            avg, diff, color = await compute_test_avg_and_color(test.test_name,  test.duration_ms, test.status, repo_id,db,)
            db.add(TestRun(
                run_id=run_id,
                job_id=job.id if job else None,
                test_name=test.test_name,
                status=test.status,
                duration_ms=test.duration_ms,
                avg_duration_ms=avg,
                diff_from_avg_pct=diff,
                color=color,
                error_message=test.error,
                framework=test.framework,
                source_format=test.source,
            ))
            tests_found += 1

        return tests_found


    def parse_duration(self, started_at: str | None, completed_at: str | None) -> int | None:
            
        """Calculate duration in seconds from ISO timestamps"""
        #github timings are like: "2026-05-10T12:00:00Z"
        # we convert to "2026-05-10T12:00:00+00:00"
        if not started_at or not completed_at:
            return None
        try:
            #this creates an object like: datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            return max(0, int((end - start).total_seconds()))
        except (ValueError, TypeError):
            return None
        

    def _parse_ts(self, time: str | None) -> datetime | None:
        if not time:
            return None
        try:
            return datetime.fromisoformat(time.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        


    def extract_test_reports_from_zip(zip_data: bytes) -> list[Tuple[str, str, str]]:
        
        """
        Extract structured test report files from CI artifact ZIPs.

        Returns:
            [(filename, content, extension), ...]
        """

        reports = []

        VALID_EXTENSIONS = {".xml", ".json"}

        COMMON_REPORT_PATTERNS = [
            "test",
            "tests",
            "report",
            "reports",
            "result",
            "results",
            "junit",
            "surefire",
            "failsafe",
            "pytest",
            "nunit",
            "trx",
            "jest",
            "playwright",
            "mocha",
            "rspec",
        ]

        try:
            with zipfile.ZipFile(BytesIO(zip_data)) as z:

                for file_info in z.filelist:

                    fname = file_info.filename
                    lower_name = fname.lower()

                    # skip directories
                    if file_info.is_dir():
                        continue

                    ext = os.path.splitext(lower_name)[1]

                    # skip unsupported file types
                    if ext not in VALID_EXTENSIONS:
                        continue

                    # heuristic filter
                    if not any(p in lower_name for p in COMMON_REPORT_PATTERNS):
                        continue

                    try:
                        content = z.read(fname).decode(
                            "utf-8",
                            errors="ignore"
                        )

                        reports.append(
                            (fname, content, ext.lstrip("."))
                        )

                    except Exception as e:
                        print(f"Failed reading report file {fname}: {e}", flush=True)

        except Exception as e:
            print(f"Failed to extract artifact zip: {e}", flush=True)

        return reports