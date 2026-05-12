from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_current_user
from database.db_engine import get_db
from schemas.user_schema import UserCreate, UserCreateResponse, UserLogin, LoginResponse, LoginConfirm
from services.auth_services import signup as signup_service, login as login_service
from models.user_model import User

router = APIRouter()

@router.post("/signup", response_model=UserCreateResponse)
async def signup(userCreate: UserCreate , db : AsyncSession = Depends(get_db)):
      return await signup_service(userCreate, db)
    

@router.post("/login", response_model=LoginResponse)
async def login(user: UserLogin, db : AsyncSession = Depends(get_db)):
      return await login_service(user, db)

@router.get("/me", response_model=LoginConfirm)
async def read_current_user(current_user: User = Depends(get_current_user)):
      return {"username": current_user.username}
      

@router.post("/logout")
async def logout():
      response = JSONResponse({"msg": "Logged out successfully"})
      response.delete_cookie(key="access_token")
      return response