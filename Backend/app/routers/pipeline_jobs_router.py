from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.db_engine import get_db
from models.user_model import User
from schemas.pipeline_jobs_schema import JobOrderResponse, PipelineJobsEdit
from services.pipeline_jobs.service import list_pipeline_jobs, edit_pipeline_jobs

router = APIRouter()

#extract the jobs of a certain pipeline
@router.get("/{project_id}/pipelines/{pipeline_id}/jobs", response_model=JobOrderResponse,)
async def get_pipeline_jobs(
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    
    platform, jobs, content = await list_pipeline_jobs(pipeline_id, project_id, current_user.id, db)
    return JobOrderResponse(pipeline_id=pipeline_id, platform=platform, jobs=jobs, content=content)


#full job edit: reorder + change text + add + delete, validated before it is saved
@router.put("/{project_id}/pipelines/{pipeline_id}/jobs", response_model=JobOrderResponse,)
async def edit_pipeline_jobs_endpoint(
    project_id: int,
    pipeline_id: int,
    body: PipelineJobsEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    platform, jobs, content, warnings = await edit_pipeline_jobs(
        pipeline_id, project_id, current_user.id, body.jobs, db
    )
    return JobOrderResponse(
        pipeline_id=pipeline_id, platform=platform, jobs=jobs, content=content, warnings=warnings
    )
