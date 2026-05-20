from schemas.dashboard import SyncStatus, RepositorySchema, CollectorsRepositoryDetail
from models.dashboard import Repository
from .platform_collectors.github_collector_services import GitHubCollector
from .platform_collectors.gitlab_collector_services import GitLabCollector
from .platform_collectors.ci_collector import CICollector
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Tuple


async def sync_repository(repo_id: int, db: AsyncSession) -> SyncStatus:

    repo_orm = await db.get(Repository, repo_id)
    if not repo_orm:
        raise ValueError("Repository not found")
    
    repo_schema = RepositorySchema.model_validate(repo_orm)

    if repo_orm.platform not in ["github", "gitlab"]:
        raise ValueError(f"Unsupported platform: {repo_orm.platform}")

    collector = get_ci_collector(repo_orm.platform)
    print(f"[sync-repo] Starting sync for repo {repo_schema.full_name} (ID: {repo_id}) on platform {repo_orm.platform}", flush=True)
    print(f"[sync-repo] using collector: {collector.__class__.__name__}", flush=True)
    ctx = build_ctx(repo_orm, repo_schema)
    try:
        return await collector.sync(ctx, db)

    finally:
        await collector.close()

    

def get_ci_collector(platform: str) -> CICollector:
    if platform == "github":
        return GitHubCollector()
    elif platform == "gitlab":
        return GitLabCollector()
    else:
        raise ValueError(f"Unsupported platform: {platform}")

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
    parts = full_name.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid repository full name: {full_name}")
    return parts[0], parts[1]

