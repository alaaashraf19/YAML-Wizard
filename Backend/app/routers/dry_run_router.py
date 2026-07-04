from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.db_engine import get_db
from models.user_model import User
from schemas.dry_run_schema import DryRunHistoryItem, DryRunResponse
from services.dry_run.base import DryRunError, DryRunInProgress
from services.dry_run.factory import get_dry_runner
from services.dry_run.history import list_dry_runs, save_dry_run

router = APIRouter()


#triggers a real pipeline, polls it, returns the result, then cleans up the temp branch + pipeline.
@router.post("/{platform}/{project_id}/{pipeline_id}", response_model=DryRunResponse)
async def dry_run_pipeline(
    platform: str,
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        runner = get_dry_runner(platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        result = await runner.run(pipeline_id, project_id, current_user.id, db)
    except DryRunInProgress as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DryRunError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))

    await save_dry_run(db, current_user.id, project_id, result)
    return result


#returns the saved dry-run history for a pipeline, newest first.
@router.get("/history/{project_id}/{pipeline_id}", response_model=list[DryRunHistoryItem])
async def get_dry_run_history(
    project_id: int,
    pipeline_id: int,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_dry_runs(db, current_user.id, project_id, pipeline_id, limit, offset)
    if rows is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return rows
