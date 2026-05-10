from schemas.dashboard import RepoCreate
from sqlalchemy import select
from models.dashboard import Repository
from urllib.parse import urlparse
from fastapi import HTTPException



async def add_repo_service(body: RepoCreate, db, current_user):
    
    full_name, detected_platform = _parse_repo_info(body.url)
    platform = body.platform or detected_platform

    existing = await db.execute(select(Repository).where(Repository.full_name == full_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Repository '{full_name}' already tracked")

    repo = Repository(
        full_name=full_name,
        platform=platform,
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