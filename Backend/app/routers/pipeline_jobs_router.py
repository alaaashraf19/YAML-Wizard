from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_current_user
from database.db_engine import get_db
from models.user_model import User
from schemas.pipeline_jobs_schema import (
    JobOrderResponse,
    PipelineJobsEdit,
    PipelineVersionsResponse,
    PublishVersionRequest,
    PushVersionResponse,
    ApproveVersionResponse,
    DeleteVersionResponse,
)
from services.pipeline_jobs.service import (
    list_pipeline_jobs,
    review_pipeline_jobs,
    commit_pipeline_jobs,
    list_pipeline_versions,
    push_pipeline_version,
    approve_pipeline_version,
    delete_pipeline_version,
)

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


#get all saved edit versions of a pipeline
@router.get("/{project_id}/pipelines/{pipeline_id}/versions", response_model=PipelineVersionsResponse,)
async def get_pipeline_versions(
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    platform, versions = await list_pipeline_versions(pipeline_id, project_id, current_user.id, db)
    return PipelineVersionsResponse(
        pipeline_id=pipeline_id,
        platform=platform,
        count=len(versions),
        versions=versions,
    )


#delete a single saved edit version of a pipeline
@router.delete(
    "/{project_id}/pipelines/{pipeline_id}/versions/{version_id}",
    response_model=DeleteVersionResponse,
)
async def delete_pipeline_version_endpoint(
    project_id: int,
    pipeline_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await delete_pipeline_version(pipeline_id, project_id, version_id, current_user.id, db)
    return DeleteVersionResponse(**result)


#step 1 review: full job edit (reorder + change text + add + delete) is assembled and validated, then ai agent shows advisory warnings. nothing gets saved to DB here.
@router.put("/{project_id}/pipelines/{pipeline_id}/jobs", response_model=JobOrderResponse,)
async def review_pipeline_jobs_endpoint(
    project_id: int,
    pipeline_id: int,
    body: PipelineJobsEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await review_pipeline_jobs(
        pipeline_id, project_id, current_user.id, body.jobs, db
    )
    return JobOrderResponse(pipeline_id=pipeline_id, **result)


#step 2 commit The same edited jobs are after they are re-assembled and re-validated.
@router.post("/{project_id}/pipelines/{pipeline_id}/jobs/commit", response_model=JobOrderResponse,)
async def commit_pipeline_jobs_endpoint(
    project_id: int,
    pipeline_id: int,
    body: PipelineJobsEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await commit_pipeline_jobs(
        pipeline_id, project_id, current_user.id, body.jobs, db
    )
    return JobOrderResponse(pipeline_id=pipeline_id, **result)


#approve a saved edit version: swap it in as the main pipeline
@router.post(
    "/{project_id}/pipelines/{pipeline_id}/versions/{version_id}/approve",
    response_model=ApproveVersionResponse,
)
async def approve_pipeline_version_endpoint(
    project_id: int,
    pipeline_id: int,
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await approve_pipeline_version(pipeline_id, project_id, version_id, current_user.id, db)
    return ApproveVersionResponse(**result)


#push a saved edit version's YAML to the repo
@router.post(
    "/{project_id}/pipelines/{pipeline_id}/versions/{version_id}/push",
    response_model=PushVersionResponse,
)
async def push_pipeline_version_endpoint(
    project_id: int,
    pipeline_id: int,
    version_id: int,
    body: PublishVersionRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await push_pipeline_version(
        pipeline_id,
        project_id,
        version_id,
        current_user.id,
        db,
        commit_message=(body.commit_message if body else None),
    )
    return PushVersionResponse(**result)
