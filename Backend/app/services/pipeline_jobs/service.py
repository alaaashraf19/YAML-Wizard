from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pipeline_model import Pipeline
from models.platforms_model import GitLabConnection
from models.project_model import Project
from models.repository_model import Repository
from schemas.pipeline_jobs_schema import JobView, JobEdit
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
) -> tuple[str, list[JobView], str]:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)
    try:
        jobs = editor.list_jobs(pipeline.content)
    except JobsNotFound as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return platform, jobs, pipeline.content



async def edit_pipeline_jobs(
    pipeline_id: int, project_id: int, user_id: int, job_edits: list[JobEdit], db: AsyncSession
) -> tuple[str, list[JobView], str, list]:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)

    #parse each submitted block. The block's top-level key is the job id, so renaming a job is just editing that key. id is only an optional label for error messages.
    parsed: list[tuple[str, object]] = []
    seen: set[str] = set()
    for index, edit in enumerate(job_edits):
        label = edit.id or f"#{index + 1}" #numbering the jobs in case of id is not set, the error shows job number instead of id
        try:
            key, spec = editor.parse_job_block(edit.content)
        except (InvalidJobOrder, JobsNotFound) as exc:
            raise HTTPException(status_code=400, detail=f"job {label}: {exc}")
        except Exception as exc:  # malformed YAML in the submitted block
            raise HTTPException(status_code=400, detail=f"job {label}: invalid YAML ({exc})")
        if not editor.is_valid_job_id(key):
            raise HTTPException(status_code=400, detail=f"'{key}' is not a valid job id for {platform}")
        if key in seen:
            raise HTTPException(status_code=400, detail=f"duplicate job id '{key}'")
        seen.add(key)
        parsed.append((key, spec))

    #assemble the new pipeline, preserving globals/formatting
    try:
        new_content = editor.assemble(pipeline.content, parsed)
    except (InvalidJobOrder, JobsNotFound) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    #validate the assembled pipeline through the agent's validation system
    report = await validate_assembled_pipeline(new_content, platform, user_id, db, project_id)
    if not report.get("valid", False):
        raise HTTPException(
            status_code=422,
            detail={"message": "Pipeline validation failed", "report": report},
        )

    #persist only if valid and actually changed
    if new_content != pipeline.content:
        pipeline.content = new_content
        pipeline.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(pipeline)

    jobs = editor.list_jobs(pipeline.content)
    return platform, jobs, pipeline.content, report.get("warnings", [])


async def validate_assembled_pipeline(content: str, platform: str, user_id: int, db: AsyncSession, project_id: int | None = None) -> dict:
    from agent.tools.validate_pipeline_tool import build_report

    target = (platform or "").lower()
    connection = None
    gitlab_project_id = None
    if target == "gitlab":
        result = await db.execute(
            select(GitLabConnection).where(GitLabConnection.user_id == user_id)
        )
        connection = result.scalar_one_or_none()
        if project_id is not None:
            repo_row = await db.execute(
                select(Repository.gitlab_project_id)
                .join(Project, Project.repo_id == Repository.id)
                .where(Project.id == project_id, Project.user_id == user_id)
            )
            gitlab_project_id = repo_row.scalar_one_or_none()
    return await build_report(content, target, connection=connection, db=db, project_id=gitlab_project_id)
