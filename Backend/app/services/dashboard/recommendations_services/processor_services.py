from models.repository_model import JobTiming, PipelineRun, TestRun
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


ORANGE_THRESHOLD = 0.15  # >15% slower
RED_THRESHOLD = 0.50     # >50% slower or failed

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


async def compute_test_avg_and_color(test_name: str, current_duration: int | None, status: str,repo_id: int, db: AsyncSession,) -> tuple[float | None, float | None, str]:
    """Calculate rolling average, diff, and color for a test.

    Returns (avg_duration_ms, diff_from_avg_pct, color).
    """
    if status in ("fail", "error"):
        return None, None, "red"

    #last 10 runs for this test to get its avg data
    result = await db.execute(select(TestRun.duration_ms).join(PipelineRun, TestRun.run_id == PipelineRun.id)
        .where(
            PipelineRun.repo_id == repo_id,
            TestRun.test_name == test_name,
            TestRun.duration_ms.isnot(None),
            TestRun.status == "pass",
        )
        .order_by(PipelineRun.started_at.desc())
        .limit(10)
    )
    durations = [row[0] for row in result.all()]

    if not durations or current_duration is None:
        return None, None, "green"

    avg = sum(durations) / len(durations)
    if avg == 0:
        return avg, 0.0, "green"

    diff_pct = ((current_duration - avg) / avg) * 100

    if diff_pct > RED_THRESHOLD * 100:
        color = "red"
    elif diff_pct > ORANGE_THRESHOLD * 100:
        color = "orange"
    else:
        color = "green"

    return avg, diff_pct, color
