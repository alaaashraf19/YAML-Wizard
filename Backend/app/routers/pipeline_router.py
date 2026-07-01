from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db, async_session
from models.pipeline_model import Pipeline
from schemas.project_schema import ProjectCreate,ProjectResponse, ProjectSession,ProjectUpdate
from schemas.pipeline_schema import PipelineCreate,PipelineResponse,PipelineUpdate,PipelineSummary

from services.project_service import get_project_by_id,get_projectModel_by_id
from services.pipeline_services import(
    create_pipeline,get_pipeline_by_id,get_project_pipelines
    ,get_active_pipelines,set_active_pipeline,
    update_pipeline,delete_pipeline,deactivate_pipeline, mark_pipeline_committed)
from core.security import get_current_user
from models.user_model import User
from typing import List, Optional
from services.dashboard.yaml_sync_service import yaml_sync_service
from schemas.yaml_sync_schema import YamlSyncResult, PipelineSyncResult

router = APIRouter()


@router.post("/{project_id}", response_model=PipelineResponse)
async def create_project_pipeline(
    project_id: int,
    pipeline: PipelineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await create_pipeline(pipeline, project_id, current_user.id, db)
    return PipelineResponse.model_validate(pipeline)


@router.get("/project/{project_id}", response_model=List[PipelineResponse])
async def get_project_pipelines_list(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipelines =  await get_project_pipelines(project_id, current_user.id, db)
    return [PipelineResponse.model_validate(p) for p in pipelines]


@router.get("/{project_id}/active", response_model=List[PipelineResponse])
async def get_project_active_pipelines(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipelines = await get_active_pipelines(project_id, current_user.id, db)
    return [PipelineResponse.model_validate(p) for p in pipelines]


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_project_pipeline_by_id(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await get_pipeline_by_id(pipeline_id, current_user.id, db)
    return PipelineResponse.model_validate(pipeline)



@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_project_pipeline(
    project_id: int,
    pipeline_id: int,
    pipeline_update: PipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await update_pipeline(pipeline_id,project_id, pipeline_update, current_user.id, db)
    return PipelineResponse.model_validate(pipeline)


@router.delete("/{pipeline_id}", response_model=dict)
async def delete_project_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await delete_pipeline(pipeline_id,current_user.id,db)


@router.post("/{pipeline_id}/activate", response_model=PipelineResponse)
async def activate_project_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await set_active_pipeline(pipeline_id, current_user.id, db)
    return PipelineResponse.model_validate(pipeline)

@router.post("/{pipeline_id}/deactivate", response_model=PipelineResponse)
async def deactivate_project_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await deactivate_pipeline(pipeline_id, current_user.id, db)
    return PipelineResponse.model_validate(pipeline)

@router.post("/{pipeline_id}/commit", response_model=PipelineResponse)
async def commit_project_pipeline(
    pipeline_id: int,
    commit_hash: str,
    commit_author: str,
    commit_message: Optional[str] = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await mark_pipeline_committed(
        pipeline_id, current_user.id, commit_hash,
        commit_author, db, commit_message)
    return PipelineResponse.model_validate(pipeline)


@router.post("/{project_id}/sync", response_model=List[PipelineResponse])
async def sync_project_pipelines(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync all YAML pipelines for a project from its repository."""
    project = await get_projectModel_by_id(project_id, current_user.id, db)
    if not project.repo_id:
        raise HTTPException(400, "Project has no connected repository")
    # Run sync for that repo
    result = await yaml_sync_service.sync_repository_yaml_files(project.repo_id, db)
    if not result.success:
        raise HTTPException(500, detail=result.message)
    # Return updated list
    return await get_project_pipelines(project_id, current_user.id, db)


@router.post("/sync-all", response_model=list[YamlSyncResult])
async def sync_all_user_repositories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync YAML files for all repositories belonging to the current user."""
    # get all repos for user
    from models.repository_model import Repository
    repos = (await db.execute(select(Repository).where(Repository.user_id == current_user.id))).scalars().all()
    results = []
    for repo in repos:
        # use fresh session per repo to avoid cross-commit issues
        async with async_session() as repo_db:
            res = await yaml_sync_service.sync_repository_yaml_files(repo.id, repo_db)
            results.append(res)
    return results


@router.post("/{project_id}/{pipeline_id}/sync", response_model=PipelineResponse)
async def sync_single_pipeline_manual(
    project_id: int,
    pipeline_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync a single pipeline with the latest file from the repository."""
    # verify project ownership
    await get_projectModel_by_id(project_id, current_user.id, db)
    # verify pipeline belongs to project
    pipeline = await get_pipeline_by_id(pipeline_id, current_user.id, db)
    if pipeline.project_id != project_id:
        raise HTTPException(404, "Pipeline not in this project")
    # call service
    updated_data = await yaml_sync_service.sync_single_pipeline(pipeline_id, current_user.id, db)
    return PipelineResponse(**updated_data)