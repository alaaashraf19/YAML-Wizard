from __future__ import annotations

from datetime import datetime

import yaml as pyyaml
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pipeline_model import Pipeline
from models.project_model import Project
from models.repository_model import Repository
from schemas.pipeline_jobs_schema import JobView
from .base import InvalidJobOrder, JobsNotFound
from .factory import get_pipeline_editor


#fetch the pipeline together with its repo platform
async def load_pipeline_with_platform(
    pipeline_id: int, project_id: int, user_id: int, db: AsyncSession) -> tuple[Pipeline, str]:
    result = await db.execute(
        select(Pipeline, Repository.platform)
        .join(Project, Pipeline.project_id == Project.id)
        .join(Repository, Project.repo_id == Repository.id)
        .where(Pipeline.id == pipeline_id, Project.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipeline, platform = row
    if pipeline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found in this project")
    return pipeline, platform


def editor_for(platform: str):
    try:
        return get_pipeline_editor(platform)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


async def list_pipeline_jobs(
    pipeline_id: int, project_id: int, user_id: int, db: AsyncSession
) -> tuple[str, list[JobView]]:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)
    try:
        jobs = editor.list_jobs(pipeline.content)
    except JobsNotFound as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return platform, jobs


async def set_pipeline_job_order(
    pipeline_id: int, project_id: int, user_id: int, new_order: list[str], db: AsyncSession) -> tuple[str, list[JobView], str]:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)

    try:
        new_content = editor.reorder(pipeline.content, new_order)
    except InvalidJobOrder as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except JobsNotFound as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    #reorder must still parse as valid YAML.
    try:
        pyyaml.safe_load(new_content)
    except pyyaml.YAMLError as exc:
        raise HTTPException(status_code=500, detail=f"Reorder produced invalid YAML: {exc}")

    # Skip the write when nothing actually changed (for example the submitted order matches the current one) so we don't reformat.
    if new_content != pipeline.content:
        pipeline.content = new_content
        pipeline.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(pipeline)

    jobs = editor.list_jobs(pipeline.content)
    return platform, jobs, pipeline.content
