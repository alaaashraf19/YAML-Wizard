from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db_engine import get_db
from schemas.user_schema import UserCreate, UserCreateResponse, UserLogin, UserLoginResponse
from services.auth_services import signup, login

router = APIRouter()


@router.post("/signup", response_model=UserCreateResponse)
async def signup_route(user: UserCreate, db: Session = Depends(get_db)):
    return await signup(user, db)


@router.post("/login", response_model=UserLoginResponse)
async def login_route(user: UserLogin, db: Session = Depends(get_db)):
    return await login(user, db)
