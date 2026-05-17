from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from .processor_services import compute_job_comparison, compute_run_comparison, compute_test_avg_and_color
from schemas.dashboard import SyncStatus
from models.dashboard import JobTiming, PipelineRun, Repository, TestRun
from services.dashboard.github_collector_services import GitHubCollector
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .test_parsers.ParserRegistry import ParserRegistry
from .test_parsers.BaseTestParser import BaseTestParser

load_dotenv()

async def sync_repository(repo_id: int, db: AsyncSession) -> SyncStatus:
    
    """Sync pipeline data for a repository from the platform API."""
    
    repo = await db.get(Repository, repo_id)

    if not repo:
        raise ValueError("Repository not found")

    if repo.platform == "github":
        return await sync_github_actions(repo, db)
    else:
        return SyncStatus(  
            repo_id=repo.id,
            runs_synced=0,
            jobs_synced=0,
            tests_parsed=0,
            message=f"Platform '{repo.platform}' sync not yet implemented",
        )
    
#here framework will be replaced with fetching it from repocontext model when repo fetcher is done
async def sync_github_actions(repo: Repository, db: AsyncSession, framework: str | None = None) -> SyncStatus:
    
    """Fetch runs, jobs, and test results from GitHub Actions."""
    
    parts = repo.full_name.split("/")
    owner, repo_name = parts
    
    collector = GitHubCollector()
    runs_synced = 0
    jobs_synced = 0
    tests_parsed = 0

    try:
        #Fetch recent workflow runs

        ##update the max runs logic
        max_runs = os.getenv("MAX_RUNS_PER_SYNC")
        if max_runs is None:
            raise ValueError("MAX_RUNS_PER_SYNC not found as env variable or invalid. Please set it to a positive integer.")
        raw_runs = await collector.get_workflow_runs(owner, repo_name, per_page=int(max_runs))

        for raw_run in raw_runs:
            external_id = raw_run["id"] # GitHub's unique run ID

            # Skip if already synced
            #do not insert the workflow run again if it already exists in the db
            existing = await db.execute(select(PipelineRun).where(PipelineRun.external_id == external_id))
            # execute() returns a result object, not the actual row,
            # so scalar_one_or_none() extracts the matching PipelineRun or None
            if existing.scalar_one_or_none():
                continue

            if raw_run.get("status") != "completed":
                continue

            duration = parse_duration(raw_run.get("run_started_at"), raw_run.get("updated_at"),)
            pipeline_run = PipelineRun(
                repo_id=repo.id,  external_id=external_id,
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
            pipeline_run.compared_to_prev_pct = await compute_run_comparison(pipeline_run, repo.id, db,)
            print(f"Run {pipeline_run.id} compared to previous run: {pipeline_run.compared_to_prev_pct}%")
            
            #fetch jobs for the pipeline run
            raw_jobs = await collector.get_run_jobs(owner, repo_name, external_id)
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
                    job.compared_to_prev_pct = await compute_job_comparison(job.job_name, job_duration, repo.id, pipeline_run.id, db,)
                db.add(job)
                await db.flush()  #to get job.id before syncing tests

                tests_parsed += await sync_job_tests(job, raw_job, collector, db, owner, repo_name, repo)
                print(f"Synced job {job.job_name} with {tests_parsed} tests parsed so far")
                if tests_parsed > 0:
                    print(f"Job {job.job_name}: Parsed {tests_parsed} tests")
                jobs_synced += 1
            
            runs_synced += 1
            repo.last_synced_at = datetime.now(timezone.utc)
            await db.commit()

                
    except Exception as e:
            await db.rollback()
            return SyncStatus(
                repo_id=repo.id,
                runs_synced=runs_synced,
                jobs_synced=jobs_synced,
                tests_parsed=tests_parsed,
                message=f"Sync error: {e}",
            )
    finally:
        await collector.close()

    return SyncStatus(
            repo_id=repo.id,
            runs_synced=runs_synced,
            jobs_synced=jobs_synced,
            tests_parsed=tests_parsed,
            message=f"Synced {runs_synced} runs, {jobs_synced} jobs, {tests_parsed} tests",
        )             


def _parse_ts(time: str | None) -> datetime | None:
    if not time:
        return None
    try:
        return datetime.fromisoformat(time.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None



async def sync_job_tests(job: JobTiming, raw_job, collector: GitHubCollector, db: AsyncSession, owner: str, repo_name: str, repo:Repository):
    
    """Collect test results for a job"""
    
    job_id = raw_job["id"]
    run_id = raw_job["run_id"]
    
    print(f"[sync-tests] Starting sync_job_tests for job {job.job_name} (id={job_id}, run_id={run_id})", flush=True)
    
    parser_registry = ParserRegistry()
    tests_found = 0
    artifacts_errors = []
    logs_errors = []
    
    #Check for test report artifacts
    try:
        print(f"[sync-tests] Fetching artifacts for job {job.job_name} (owner={owner}, repo={repo_name}, run_id={run_id})", flush=True)
        artifacts = await collector.get_job_artifacts(owner, repo_name, run_id)
        print(f"[sync-tests] Found {len(artifacts)} total artifacts", flush=True)
        
        for artifact in artifacts:
            artifact_name = artifact["name"]
            print(f"[sync-tests] Checking artifact: {artifact_name}", flush=True)
            
            if any(name in artifact["name"].lower() for name in 
                   ["test", "report", "result", "junit", "coverage"]):
                
                
                try:
                    print(f"[sync-tests] Downloading artifact: {artifact_name}", flush=True)

                    zip_data = await collector.download_artifact(artifact["archive_download_url"])

                    print(f"[sync-tests] Downloaded {len(zip_data)} bytes for artifact {artifact_name}", flush=True)
                    
                    reports = collector.extract_test_reports_from_zip(zip_data)

                    print(f"[sync-tests] Extracted {len(reports)} report files from {artifact_name}", flush=True)
                    
                    for filename, content, ext in reports:
                        print(f"[sync-tests] Processing report file: {filename} (type: {ext}, size: {len(content)} bytes)", flush=True)
                        
                        try:
                            parser = parser_registry.detect(content, filename)

                            if parser:
                                parsed_tests = parser.parse(content)
                            else:
                                parsed_tests = []

                            print(f"[sync-tests] Parsed {len(parsed_tests)} tests from {filename}", flush=True)
                            
                            tests_found += await process_test_batch(parsed_tests,job,repo,db)
                            
                            print(f"[sync-tests] Added test to DB. Total tests found: {tests_found}", flush=True)
                        except Exception as e:
                            error_msg = f"Failed to parse {filename}, while snying job tests function: {str(e)}"
                            print(f"[sync-tests] ERROR parsing {filename}: {error_msg}", flush=True)
                            artifacts_errors.append(Exception(error_msg))
                
                except Exception as e:
                    error_msg = f"Failed to download/extract artifact {artifact['name']}, while snying job tests function:: {str(e)}"
                    print(f"[sync-tests] ERROR downloading {artifact_name}: {error_msg}", flush=True)
                    artifacts_errors.append(Exception(error_msg))
            else:
                print(f"[sync-tests] Skipping non-test artifact: {artifact_name}", flush=True)
    
    except Exception as e:
        error_msg = f"Failed to fetch artifacts: {str(e)}"
        print(f"[sync-tests] ERROR fetching artifacts: {error_msg}", flush=True)
        artifacts_errors.append(Exception(error_msg))
    
    #Parse logs if no test reports found
    print(f"[sync-tests] Tests found in artifacts: {tests_found}. Will {'skip logs' if tests_found > 0 else 'parse logs'}", flush=True)
    
    if tests_found == 0:
        try:
            log_content = await collector.get_job_logs(owner, repo_name, job_id)
            log_content = BaseTestParser.normalize_github_logs(log_content)

            try:
                print(f"[sync-tests] Parsing job logs as test report", flush=True)
                parser = parser_registry.detect(log_content, "job.log")

                if parser:
                    print(f"[sync-tests] Detected parser: {parser.parser_name}", flush=True)
                    parsed_tests = parser.parse(log_content)
                else:
                    print("[sync-tests] No parser detected", flush=True)
                    parsed_tests = []
                

                print(f"[sync-tests] Parsed {len(parsed_tests)} tests from logs", flush=True)
                tests_found += await process_test_batch(
                                parsed_tests,
                                job,
                                repo,
                                db)
                print(f"[sync-tests] Added test from logs. Total tests found: {tests_found}", flush=True)      
            except Exception as e:
                error_msg = f"while snying job tests function:, Failed to parse job logs: {str(e)}"
                print(f"[sync-tests] ERROR parsing logs: {error_msg}", flush=True)
                logs_errors.append(Exception(error_msg))
        
        except Exception as e:
            error_msg = f"while snying job tests function:, Failed to fetch job logs: {str(e)}"
            print(f"[sync-tests] ERROR fetching logs: {error_msg}", flush=True)
            logs_errors.append(Exception(error_msg))
    
    print(f"[sync-tests] Completed sync_job_tests for {job.job_name}: {tests_found} tests found, {len(artifacts_errors)} artifact errors, {len(logs_errors)} log errors", flush=True)
    
    return tests_found



async def process_test_batch(
    parsed_tests,
    job,
    repo,
    db
):
    tests_found = 0

    for test in parsed_tests:

        avg, diff, color = await compute_test_avg_and_color(
            test.test_name,
            test.duration_ms,
            test.status,
            repo.id,
            db,
        )

        db.add(TestRun(
            run_id=job.run_id,
            job_id=job.id,
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


def parse_duration(started_at: str | None, completed_at: str | None) -> int | None:
        
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