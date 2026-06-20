from core.security import get_current_user
from schemas.dashboard import PipelineRunOut, PipelineRunDetail, JobTimingOut, TestRunOut
from database.db_engine import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from models.user_model import User
from models.repository_model import PipelineRun, JobTiming, TestRun
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from services.dashboard.repos_services import get_repo_or_404, get_run_or_404

router = APIRouter()



@router.get("/repos/{repo_id}/runs", response_model=list[PipelineRunOut])
async def list_runs(repo_id: int, branch: str | None = None, status: str | None = None, limit: int = Query(default=20, le=100), 
                    offset: int = 0,db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    await get_repo_or_404(repo_id, db, current_user)
    query = select(PipelineRun).where(PipelineRun.repo_id == repo_id)
    if branch:
        query = query.where(PipelineRun.branch == branch)
    if status:
        query = query.where(PipelineRun.conclusion == status)
    query = query.order_by(PipelineRun.started_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/repos/{repo_id}/runs/{run_id}", response_model=PipelineRunDetail)
async def get_run(repo_id: int, run_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    await get_repo_or_404(repo_id, db, current_user)
    
    query = (
        select(PipelineRun)
        .where(PipelineRun.id == run_id, PipelineRun.repo_id == repo_id)
        .options(selectinload(PipelineRun.jobs), selectinload(PipelineRun.tests))
    )

    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/repos/{repo_id}/runs/latest", response_model=PipelineRunDetail | None)
async def get_latest_run(repo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    await get_repo_or_404(repo_id, db, current_user)
    
    query = (select(PipelineRun).where(PipelineRun.repo_id == repo_id)
        .options(selectinload(PipelineRun.jobs), selectinload(PipelineRun.tests))
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )

    result = await db.execute(query)
    run = result.scalar_one_or_none()

    if not run:
        return None
    return run



@router.get("/repos/{repo_id}/runs/{run_id}/jobs", response_model=list[JobTimingOut])
async def get_run_jobs(repo_id: int, run_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    await get_repo_or_404(repo_id, db, current_user)

    await get_run_or_404(run_id, repo_id, db)

    result = await db.execute(
        select(JobTiming).where(JobTiming.run_id == run_id).order_by(JobTiming.started_at)
    )
    return result.scalars().all()



@router.get("/repos/{repo_id}/runs/{run_id}/tests", response_model=list[TestRunOut])
async def get_run_tests(repo_id: int, run_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    await get_repo_or_404(repo_id, db, current_user)

    await get_run_or_404(run_id, repo_id, db)

    result = await db.execute(
        select(TestRun).where(TestRun.run_id == run_id).order_by(TestRun.test_name)
    )
    return result.scalars().all()