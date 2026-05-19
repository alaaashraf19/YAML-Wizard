import httpx

from schemas.dashboard import RepoCreate
from sqlalchemy import select
from urllib.parse import urlparse
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from models.user_model import User
from models.dashboard import Repository, PipelineRun
from services.dashboard.gitlab_collector_services import GitLabCollector

#this is for adding a repo in dashboard by pasting the url, if it's not added in our user profile aka projects field
# will be saved in db, need to make it appear in user projects to fetch all projects from db and show them this included
async def add_repo_service(body: RepoCreate, db, current_user):
    
    full_name, detected_platform = _parse_repo_info(body.url)
    platform = body.platform or detected_platform
    
    if platform not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Unsupported platform. Only 'github' and 'gitlab' are supported.")
    if platform == "gitlab":
        gitLabCollector = GitLabCollector()
        try:
            gitlab_project_id = await gitLabCollector.get_project_id(full_name)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(404, "GitLab project not found")
            if e.response.status_code == 403:
                raise HTTPException(403, "Can't access GitLab project with provided token")
        finally:
            await gitLabCollector.close()

    existing = await db.execute(select(Repository).where(Repository.full_name == full_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Repository '{full_name}' already tracked")

    repo = Repository(
        full_name=full_name,
        platform=platform,
        gitlab_project_id=gitlab_project_id if platform == "gitlab" else None,
        default_branch=body.default_branch,
        url=body.url.rstrip("/"),
        user_id=current_user.id

    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo

def _parse_repo_info(url: str) -> tuple[str, str]:
    
    """Extract full_name and platform from a repo URL."""
    
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]

    if "github" in host:
        platform = "github"
    elif "gitlab" in host:
        platform = "gitlab"
    else:
        platform = "github"

    return path, platform


async def get_repo_or_404(repo_id: int, db: AsyncSession, current_user: User):
    result = await db.execute(
        select(Repository).where(
            Repository.id == repo_id,
            Repository.user_id == current_user.id
        )
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

async def get_run_or_404(run_id: int, repo_id: int, db: AsyncSession):
    result = await db.execute(
        select(PipelineRun).where(
            PipelineRun.id == run_id,
            PipelineRun.repo_id == repo_id
        )
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run