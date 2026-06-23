from typing import Protocol

from schemas.dashboard import CIArtifact, CollectorsRepositoryDetail, SyncStatus


class CICollector(Protocol):
    """interface for CI data collection services (GitHub, GitLab, etc.)"""
    
    async def sync(self, ctx, db) -> SyncStatus: 
        ...

    async def close(self) -> None: 
        ...

    async def get_runs(self, ctx: CollectorsRepositoryDetail, per_page: int = 30, page: int = 1, ref: str | None = None) -> list[dict]:
        ...

    async def get_jobs(self, ctx: CollectorsRepositoryDetail, run_id: int) -> list[dict]:
        ...

    async def get_logs(self, ctx: CollectorsRepositoryDetail, job_id: int) -> str:#project is repo url = repo+owner
        ...

    async def get_artifacts(self, ctx: CollectorsRepositoryDetail, job_id: int) -> list[dict]:
        ...
    
    async def download_artifact(self, artifact: CIArtifact) -> bytes:
        ...