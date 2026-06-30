from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dry_run_model import DryRunHistory
from models.project_model import Project
from schemas.dry_run_schema import DryRunResponse


async def save_dry_run(
    db: AsyncSession, user_id: int, project_id: int, result: DryRunResponse
) -> DryRunHistory:
    row = DryRunHistory(
        pipeline_id=result.pipeline_id,
        project_id=project_id,
        user_id=user_id,
        platform=result.platform,
        status=result.status,
        valid=result.valid,
        external_pipeline_id=result.external_pipeline_id,
        ref=result.ref,
        web_url=result.web_url,
        duration_s=result.duration_s,
        jobs=[j.model_dump() for j in result.jobs],
        cleaned_up=result.cleaned_up,
        message=result.message,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_dry_runs(
    db: AsyncSession, user_id: int, project_id: int, pipeline_id: int,
    limit: int = 20, offset: int = 0,
) -> list[DryRunHistory] | None:
    owns = await db.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user_id)
    )
    if owns.scalar_one_or_none() is None:
        return None

    result = await db.execute(
        select(DryRunHistory)
        .where(
            DryRunHistory.project_id == project_id,
            DryRunHistory.pipeline_id == pipeline_id,
        )
        .order_by(DryRunHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
