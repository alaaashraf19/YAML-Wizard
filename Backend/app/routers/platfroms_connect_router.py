from fastapi import APIRouter,Depends, Request, HTTPException
from services.platform_connectors.factory import get_connector
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db
from models.platforms_model import GitHubConnection, GitLabConnection
from core.security import get_current_user
from sqlalchemy import select

router = APIRouter()



@router.get("/{platform}/connect")
async def connect(platform: str, request: Request, db: AsyncSession = Depends(get_db)):
    connector = get_connector(platform)
    return await connector.connect(request, db)


@router.get("/{platform}/callback")
async def callback(platform: str, code: str, state: str, request: Request, db: AsyncSession = Depends(get_db)):
    connector = get_connector(platform)
    return await connector.callback(code, state, request, db)
    

@router.get("/integration/status")
async def integration_status(request: Request, db: AsyncSession = Depends(get_db)):

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Not authenticated")

    user = await get_current_user(db, token)

    github = await db.execute(
        select(GitHubConnection).where(GitHubConnection.user_id == user.id)
    )
    github_conn = github.scalar_one_or_none()

    gitlab = await db.execute(
        select(GitLabConnection).where(GitLabConnection.user_id == user.id)
    )
    gitlab_conn = gitlab.scalar_one_or_none()

    return {
        "github": {
            "connected": github_conn is not None,
            "username": github_conn.github_username if github_conn else None
        },
        "gitlab": {
            "connected": gitlab_conn is not None,
            "username": gitlab_conn.gitlab_username if gitlab_conn else None
        }
    }