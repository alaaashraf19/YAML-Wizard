from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.db_engine import get_db
from models.user_model import User
from schemas.pipeline_jobs_schema import JobOrderResponse, JobOrderUpdate
from services.pipeline_jobs.service import list_pipeline_jobs, set_pipeline_job_order

router = APIRouter()

#extract the jobs of a certain pipeline
@router.get("/{project_id}/pipelines/{pipeline_id}/jobs", response_model=JobOrderResponse,)
async def get_pipeline_jobs(
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    
    platform, jobs = await list_pipeline_jobs(pipeline_id, project_id, current_user.id, db)
    return JobOrderResponse(pipeline_id=pipeline_id, platform=platform, jobs=jobs)


#persist a new job order;
@router.put("/{project_id}/pipelines/{pipeline_id}/jobs/order",response_model=JobOrderResponse,)
async def update_pipeline_job_order(
    project_id: int,
    pipeline_id: int,
    body: JobOrderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    platform, jobs, content = await set_pipeline_job_order(
        pipeline_id, project_id, current_user.id, body.order, db
    )
    return JobOrderResponse(pipeline_id=pipeline_id, platform=platform, jobs=jobs, content=content)
