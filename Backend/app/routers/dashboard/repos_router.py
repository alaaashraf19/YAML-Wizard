from fastapi import APIRouter, Depends
from core.security import get_current_user
from schemas.dashboard import RepoCreate, RepoOut
from database.db_engine import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from services.dashboard.repos_services import add_repo_service
from models.user_model import User

router = APIRouter()


@router.post("/repos", response_model=RepoOut, status_code=201)
async def add_repo(body: RepoCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),):
    return add_repo_service(body, db, current_user)
