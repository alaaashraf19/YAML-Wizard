from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.dry_run_schema import DryRunResponse
from .base import DryRunError


class GitHubDryRunner:
    async def run(
        self, pipeline_id: int, project_id: int, user_id: int, db: AsyncSession
    ) -> DryRunResponse:
        raise DryRunError("not implemented yet.")
