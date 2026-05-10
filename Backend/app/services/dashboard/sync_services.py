from datetime import datetime
import os
from dotenv import load_dotenv
from processor_services import compute_job_comparison, compute_run_comparison
from schemas.dashboard import SyncStatus
from models.dashboard import JobTiming, PipelineRun, Repository
from services.dashboard.github_collector_services import GitHubCollector
from sqlalchemy import select

load_dotenv()

async def sync_repository(repo: Repository, db) -> SyncStatus:
    
    """Sync pipeline data for a repository from the platform API."""
    
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
    
async def sync_github_actions(repo: Repository, db):
    
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

            duration = GitHubCollector.parse_duration(raw_run.get("run_started_at"), raw_run.get("updated_at"),)
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
            
            #fetch jobs for the pipeline run
            raw_jobs = await collector.get_run_jobs(owner, repo_name, external_id)
            for raw_job in raw_jobs:
                job_duration = GitHubCollector.parse_duration(raw_job.get("started_at"), raw_job.get("completed_at"),)
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
                jobs_synced += 1


            ##still logic for tests to be addec
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

