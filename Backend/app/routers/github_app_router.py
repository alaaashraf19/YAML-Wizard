from typing import List
from fastapi import APIRouter, Depends, Request, HTTPException
from services.github_app_services import  github_webhook as github_webhook_services, install_app_services, setup_github_url_services, fetch_installation_repos
from database.db_engine import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_current_user
from models.user_model import User
from schemas.github_app_schema import GitHubInstallationRepoSchema
from models.platforms_model import GitHubInstallation as GitHubInstallationModel
from sqlalchemy import select

router = APIRouter()

#may be moved to projects service
#this is for adding a project but without the url
#using the github app installation we can get the repos of the user and then we can ask the user to select the repo
@router.get("/install_app")
async def install_app():
    #redirect user to github app installation page
    return await install_app_services()

@router.post("/webhook")
async def github_webhook(request: Request, db: AsyncSession  = Depends(get_db)):
    return await github_webhook_services(request, db)

@router.get("/setup")
async def setup_github_url(installation_id:int, request: Request , db: AsyncSession  = Depends(get_db)):
    return await setup_github_url_services(installation_id, request, db)


@router.get("/installations/repos", response_model=List[GitHubInstallationRepoSchema])
async def get_repos(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repos_data = await fetch_installation_repos(current_user, db)
    return repos_data


@router.get("/installations")
async def get_user_installations(request: Request, db: AsyncSession  = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user = await get_current_user(db, token)

    result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.user_id == user.id))
    installations = result.scalars().all()
    return [
        {
            "installation_id": i.installation_id,
            "account_login": i.account_login,
            "account_id": i.account_id,
            "account_type": i.account_type,
            "repos_selection": i.repos_selection,
        }
        for i in installations
    ]

@router.post("/disconnect/{installation_id}")
async def disconnect_one(installation_id: int, request: Request, db: AsyncSession  = Depends(get_db)):
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = await get_current_user(db, token)

    result = await db.execute(
        select(GitHubInstallationModel).where(
            GitHubInstallationModel.installation_id == installation_id,
            GitHubInstallationModel.user_id == user.id
        )
    )
    installation = result.scalar_one_or_none()

    if not installation:
        raise HTTPException(status_code=404, detail="Installation not found")

    await db.delete(installation)

    await db.commit()

    return {"message": "Disconnected"}

@router.post("/disconnect")
async def disconnect_all(request: Request, db: AsyncSession = Depends(get_db)):
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = await get_current_user(db, token)

    result = await db.execute(
        select(GitHubInstallationModel).where(GitHubInstallationModel.user_id == user.id))
    installations = result.scalars().all()

    for inst in installations:
        await db.delete(inst)

    await db.commit()

    return {"message": "All GitHub apps disconnected"}