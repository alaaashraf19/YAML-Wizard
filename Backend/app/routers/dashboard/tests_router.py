from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from schemas.dashboard import TestHistoryPoint
from database.db_engine import get_db
from models.user_model import User
from models.dashboard import PipelineRun, TestRun
from services.dashboard.repos_services import get_repo_or_404

router = APIRouter()

@router.get("/repos/{repo_id}/tests/{test_name}/history", response_model=list[TestHistoryPoint])
async def get_test_history( repo_id: int, test_name: str, limit: int = Query(default=20, le=100), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    """Get historical performance data for a specific test across multiple commits."""

    await get_repo_or_404(repo_id, db, current_user)

    query = (
        select(
            TestRun.status,
            TestRun.duration_ms,
            TestRun.avg_duration_ms,
            TestRun.diff_from_avg_pct,
            TestRun.color,
            PipelineRun.commit_hash,
            PipelineRun.commit_message,
            PipelineRun.started_at,
        )
        .join(PipelineRun, TestRun.run_id == PipelineRun.id)
        .where(PipelineRun.repo_id == repo_id, TestRun.test_name == test_name)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        TestHistoryPoint(
            status=row.status,
            duration_ms=row.duration_ms,
            avg_duration_ms=row.avg_duration_ms,
            diff_from_avg_pct=row.diff_from_avg_pct,
            color=row.color,
            commit_hash=row.commit_hash,
            commit_message=row.commit_message,
            timestamp=row.started_at,
        )
        for row in rows
    ]


@router.get("/repos/{repo_id}/tests/summary")
async def get_tests_summary( repo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    """Get a summary of all tests and their latest status based on latest run only, so mainly one commit"""
    
    await get_repo_or_404(repo_id, db, current_user)

    latest_run = await db.execute(
        select(PipelineRun.id)
        .where(PipelineRun.repo_id == repo_id)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    run_id = latest_run.scalar_one_or_none()
    if not run_id:
        return []

    result = await db.execute(
        select(TestRun).where(TestRun.run_id == run_id).order_by(TestRun.test_name)
    )
    return result.scalars().all()
