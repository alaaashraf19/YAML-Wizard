from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from schemas.dashboard import RepoCreate, RepoOut, SyncStatus
from database.db_engine import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from services.dashboard.repos_services import add_repo_service
from services.dashboard.sync_services import sync_repository
from models.user_model import User
from sqlalchemy import select
from models.dashboard import Repository

router = APIRouter()


@router.post("/add", response_model=RepoOut, status_code=201)
async def add_repo(body: RepoCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),):
    return add_repo_service(body, db, current_user)


@router.get("/list", response_model=list[RepoOut])
async def list_repos(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Repository).where(Repository.user_id == current_user.id).order_by(Repository.created_at.desc()))
    return result.scalars().all()


@router.get("/get_repo/{repo_id}", response_model=RepoOut)
async def get_repo(repo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Repository).where(Repository.id == repo_id and Repository.user_id == current_user.id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/delete/{repo_id}", status_code=204)
async def delete_repo(repo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Repository).where(Repository.id == repo_id and Repository.user_id == current_user.id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    await db.delete(repo)
    await db.commit()



@router.post("/sync/{repo_id}", response_model=SyncStatus)
async def sync_repo(repo_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    """Trigger an on-demand sync for a repository."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id and Repository.user_id == current_user.id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return await sync_repository(repo, db)