from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db_engine import get_db
from models.dashboard import PipelineRun, TestRun, JobTiming
from schemas.dashboard import Insight, TrendPoint
from services.dashboard.insights_services import generate_insights
from services.dashboard.repos_services import get_repo_or_404
from core.security import get_current_user

router = APIRouter(tags=["insights"])


@router.get("/repos/{repo_id}/insights", response_model=list[Insight])
async def get_insights(repo_id: int,run_id: int | None = Query(default=None),limit: int = Query(default=10, le=50),db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Generate smart insights. If run_id is provided, insights are scoped to that run"""
    await get_repo_or_404(repo_id, db, current_user)  # Ensure repo exists and belongs to user
    return await generate_insights(repo_id, db, run_id=run_id, limit=limit)


@router.get("/repos/{repo_id}/trends", response_model=list[TrendPoint])
async def get_trends(repo_id: int, limit: int = Query(default=20, le=100), db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    """Get trend data for pipeline runs (for charts)."""
    await get_repo_or_404(repo_id, db, current_user)  # Ensure repo exists and belongs to user
    
    query = (select(PipelineRun).where(PipelineRun.repo_id == repo_id).order_by(PipelineRun.started_at.desc()).limit(limit))
    result = await db.execute(query)
    runs = result.scalars().all()

    points = []
    for run in reversed(runs):
        # Count tests for this run
        test_result = await db.execute(select(TestRun).where(TestRun.run_id == run.id))
        tests = test_result.scalars().all()
        points.append(TrendPoint(
            commit_hash=run.commit_hash,
            timestamp=run.started_at,
            total_duration_s=run.total_duration_s,
            status=run.conclusion or run.status,
            test_count=len(tests),
            test_pass_count=sum(1 for t in tests if t.status == "pass"),
            test_fail_count=sum(1 for t in tests if t.status in ("fail", "error")),
        ))
    return points