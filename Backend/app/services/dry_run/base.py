from __future__ import annotations
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.dry_run_schema import DryRunResponse

#Raised when a dry run cannot be executed (config, auth, or remote error)
class DryRunError(Exception):
    pass

#Raised when a dry run is already running for the same pipeline
class DryRunInProgress(DryRunError):
    pass

#Interface for platform dry-run services (GitLab, GitHub).
class DryRunner(Protocol):

    async def run(self, pipeline_id: int, project_id: int, user_id: int, db: AsyncSession) -> DryRunResponse:
        pass
