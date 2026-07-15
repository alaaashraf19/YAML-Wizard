from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from models.pipeline_model import Pipeline
from models.project_model import Project
from schemas.pipeline_schema import PipelineCreate, PipelineUpdate
from services.project_service import get_projectModel_by_id


async def create_pipeline(
        pipeline: PipelineCreate,
        project_id: int,
        user_id: int,
        db: AsyncSession
) -> Pipeline:

    await get_projectModel_by_id(project_id, user_id, db)

    pipeline_data = pipeline.model_dump()

    if pipeline_data.get('is_active'):
        pipeline_data['committed_at'] = datetime.utcnow()

    new_pipeline = Pipeline(
        **pipeline_data,
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

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
) -> List[Pipeline]:
    await get_projectModel_by_id(project_id, user_id, db)

    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.project_id == project_id)
        .order_by(Pipeline.created_at.desc())
    )
    pipelines = result.scalars().all()

    return pipelines


async def get_active_pipelines(
        project_id: int,
        user_id: int,
        db: AsyncSession
) -> List[Pipeline]:

    await get_projectModel_by_id(project_id, user_id, db)

    result = await db.execute(
        select(Pipeline)
        .where(
            Pipeline.project_id == project_id,
            Pipeline.is_active == True
        )
        .order_by(Pipeline.committed_at.desc())
    )
    pipelines = result.scalars().all()

    return pipelines


async def set_active_pipeline(
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
) -> Pipeline:
    """Set a specific pipeline as active (does not deactivate others)."""
    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)

    pipeline.is_active = True
    pipeline.committed_at = datetime.utcnow()
    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)

    return pipeline


async def deactivate_pipeline(
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
) -> Pipeline:

    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)

    pipeline.is_active = False
    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)

    return pipeline


async def update_pipeline(
        pipeline_id: int,
        project_id: int,
        pipeline_update: PipelineUpdate,
        user_id: int,
        db: AsyncSession
) -> Pipeline:
    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)
    project = await get_projectModel_by_id(project_id, user_id, db)
    update_data = pipeline_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(pipeline, key, value)

    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)
    return pipeline


async def delete_pipeline(
        pipeline_id: int,
        user_id: int,
        db: AsyncSession
) -> dict:
    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)

    await db.delete(pipeline)
    await db.commit()

    return {"message": "Pipeline deleted successfully", "id": pipeline_id}


async def mark_pipeline_committed(
        pipeline_id: int,
        user_id: int,
        commit_hash: str,
        commit_author: str,
        db: AsyncSession,
        commit_message: Optional[str] = None,
) -> Pipeline:

    pipeline = await get_pipeline_by_id(pipeline_id, user_id, db)

    pipeline.commit_hash = commit_hash
    pipeline.commit_author = commit_author
    pipeline.commit_message = commit_message
    pipeline.committed_at = datetime.utcnow()
    pipeline.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(pipeline)

    return pipeline