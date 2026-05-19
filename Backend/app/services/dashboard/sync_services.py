from schemas.dashboard import SyncStatus, RepositorySchema, CollectorsRepositoryDetail
from models.dashboard import Repository
from .github_collector_services import GitHubCollector
from .gitlab_collector_services import GitLabCollector
from .ci_collector import CICollector
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple


def get_ci_collector(platform: str) -> CICollector:
    if platform == "github":
        return GitHubCollector()
    elif platform == "gitlab":
        return GitLabCollector()
    else:
        raise ValueError(f"Unsupported platform: {platform}")
    


async def sync_repository(repo_id: int, db: AsyncSession) -> SyncStatus:

    repo_orm = await db.get(Repository, repo_id)
    if not repo_orm:
        raise ValueError("Repository not found")

    repo_schema = RepositorySchema.model_validate(repo_orm)

    owner, repo_name = parse_full_name(repo_orm.full_name)

    ctx = CollectorsRepositoryDetail(
        repo=repo_schema,
        github_owner=owner if repo_orm.platform == "github" else None,
        github_repo=repo_name if repo_orm.platform == "github" else None,
        gitlab_project_id=repo_orm.gitlab_project_id,
    )

    collector = get_ci_collector(repo_orm.platform)

    try:
        return await collector.sync(ctx, db)

    finally:
        await collector.close()

    
    
def parse_full_name(full_name: str) -> Tuple[str, str]:
    """Parse 'owner/repo' from GitHub full name"""
    parts = full_name.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repository full name: {full_name}")
    return parts[0], parts[1]