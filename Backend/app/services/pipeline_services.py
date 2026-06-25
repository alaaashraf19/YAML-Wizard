from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from models.pipeline_model import Pipeline
from models.project_model import Project
from schemas.pipeline_schema import PipelineCreate, PipelineUpdate,PipelineSummary,PipelineResponse
from services.project_service import get_projectModel_by_id


async def create_pipeline(
        pipeline: PipelineCreate,
        project_id: int,
        user_id: int,
        db: AsyncSession
) -> Pipeline:

    await get_projectModel_by_id(project_id, user_id, db)

    new_pipeline = Pipeline(
        **pipeline.model_dump(),
        project_id=project_id,
    )
    new_pipeline.created_at = datetime.utcnow()
    new_pipeline.updated_at = datetime.utcnow()
    db.add(new_pipeline)
    await db.commit()
    await db.refresh(new_pipeline)

    return new_pipeline


async def get_pipeline_by_id(
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
) -> Pipeline:
    result = await db.execute(
        select(Pipeline)
        .join(Project, Pipeline.project_id == Project.id)
        .where(
            Pipeline.id == pipeline_id,
            Project.user_id == user_id
        )
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


async def get_project_pipelines(
        project_id: int,
        user_id: int,
        db: AsyncSession
) -> List[PipelineSummary]:

    project = await get_projectModel_by_id(project_id, user_id, db)
    active_pipeline_id = project.active_pipeline_id

    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.project_id == project_id)
        .order_by(Pipeline.created_at.desc())
    )
    pipelines = result.scalars().all()
    if not pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    response = []
    for pipeline in pipelines:
        p = PipelineSummary.model_validate(pipeline)
        p.is_active = (pipeline.id == active_pipeline_id)
        response.append(p)
    return response


async def get_active_pipeline(
        project_id: int,
        user_id: int,
        db: AsyncSession
) -> Optional[PipelineResponse]:

    project = await get_projectModel_by_id(project_id, user_id, db)

    if not project.active_pipeline_id:
        raise HTTPException(
            status_code=404,
            detail="No active pipeline found for this project"
        )

    result = await db.execute(
        select(Pipeline).where(Pipeline.id == project.active_pipeline_id)
    )
    pipeline = result.scalar_one_or_none()
    project = await get_projectModel_by_id(pipeline.project_id, user_id, db)
    p = PipelineResponse.model_validate(pipeline)
    p.is_active = (pipeline.id == project.active_pipeline_id)

    return p


async def set_active_pipeline(
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
) -> PipelineResponse:

    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)

    await db.execute(
        update(Project)
        .where(Project.id == pipeline.project_id)
        .values(active_pipeline_id=pipeline_id)
    )

    pipeline.activated_at = datetime.utcnow()
    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)
    p = PipelineResponse.model_validate(pipeline)
    p.is_active = True
    return p


async def update_pipeline(
        pipeline_id: int,
        project_id: int,
        pipeline_update: PipelineUpdate,
        user_id: int,
        db: AsyncSession
) -> PipelineResponse:

    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)
    project = await get_projectModel_by_id(project_id, user_id, db)
    update_data = pipeline_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(pipeline, key, value)

    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)
    p = PipelineResponse.model_validate(pipeline)
    p.is_active = (pipeline.id == project.active_pipeline_id)
    return p

async def delete_pipeline(
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
) -> dict:

    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)


    project = await get_projectModel_by_id(pipeline.project_id, user_id, db)

    if project.active_pipeline_id == pipeline_id:
        await db.execute(
            update(Project)
            .where(Project.id == project.id)
            .values(active_pipeline_id=None)
        )

    await db.delete(pipeline)
    await db.commit()

    return {"message": "Pipeline deleted successfully", "id": pipeline_id}


