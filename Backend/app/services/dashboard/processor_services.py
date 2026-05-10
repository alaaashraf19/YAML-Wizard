from models.dashboard import JobTiming, Repository, PipelineRun
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func


async def compute_run_comparison(run: PipelineRun, repo_id: int, db: AsyncSession,) -> float | None:
    
    """Compare a run's duration to the very previous run on the same branch"""
    
    prev = await db.execute(select(PipelineRun)
        .where(
            PipelineRun.repo_id == repo_id,
            PipelineRun.branch == run.branch,
            PipelineRun.started_at < run.started_at,
            PipelineRun.total_duration_s.isnot(None),
        )
        .order_by(PipelineRun.started_at.desc())
        .limit(1)#return first result only
    )
    prev_run = prev.scalar_one_or_none()
    if not prev_run or not prev_run.total_duration_s or not run.total_duration_s or prev_run.total_duration_s == 0:
        return None
    
    return ((run.total_duration_s-prev_run.total_duration_s)/prev_run.total_duration_s) *100

async def compute_job_comparison(job_name: str, current_duration: int, repo_id: int, run_id: int, db: AsyncSession,) -> float | None:
    
    """Compare a job's duration to the same job in the previous run."""
    
    prev_job = await db.execute(
        select(JobTiming.duration_s)
        .join(PipelineRun, JobTiming.run_id == PipelineRun.id)#this connects JobTiming.run_id → PipelineRun.id
        .where(
            PipelineRun.repo_id == repo_id,
            PipelineRun.id < run_id,#run_id of the current job
            JobTiming.job_name == job_name,
            JobTiming.duration_s.isnot(None),
        )
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    prev_dur = prev_job.scalar_one_or_none()
    if not prev_dur or not current_duration or prev_dur == 0:
        return None
    return ((current_duration-prev_dur)/prev_dur) *100

