from schemas.dashboard import SyncStatus, RepositorySchema, CollectorsRepositoryDetail
from models.repository_model import Repository
from .platform_collectors.github_collector_services import GitHubCollector
from .platform_collectors.gitlab_collector_services import GitLabCollector
from .platform_collectors.ci_collector import CICollector
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple
from ..project_service import _resolve_token
from models.repository_model import Repository
from fastapi import HTTPException
from datetime import datetime, timezone

async def sync_repository(user_id :int,repo: Repository, db: AsyncSession) -> SyncStatus:
    
    repo_schema = RepositorySchema.model_validate(repo)

    token, _ = await _resolve_token(user_id, repo.platform, repo.url, db)
    if token is None:
        raise HTTPException(status_code=401, detail="No authentication token available.")

    collector = get_ci_collector(repo.platform, token)
    ctx = build_ctx(repo, repo_schema)
    try:
        status = await collector.sync(ctx, db)
        repo.last_synced_at = datetime.now(timezone.utc)
        await db.commit()
        return status

    finally:
        await collector.close()

    

def get_ci_collector(platform: str, token:str) -> CICollector:
    if platform == "github":
        return GitHubCollector(token)
    elif platform == "gitlab":
        return GitLabCollector(token)

def build_ctx(repo_orm, repo_schema):

    owner = None
    repo_name = None
    if repo_orm.platform == "github":
        owner, repo_name = parse_full_name(repo_orm.full_name)

    return CollectorsRepositoryDetail(
        repo=repo_schema,
        github_owner=owner,
        github_repo=repo_name,
        gitlab_project_id=repo_orm.gitlab_project_id,
    )

def parse_full_name(full_name: str) -> Tuple[str, str]:
    """Parse 'owner/repo' from GitHub full name"""
    parts = full_name.strip("/").split("/")

    if len(parts) < 2:
        raise ValueError(f"Invalid repository full name: {full_name}")

    owner = parts[0]
    repo = parts[1]

    return owner, repo

