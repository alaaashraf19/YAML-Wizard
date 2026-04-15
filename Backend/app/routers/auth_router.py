from fastapi import APIRouter, Depends
from requests import Session
from database.db_engine import get_db
from schemas.user_schema import UserCreate, UserCreateResponse, UserLogin, UserLoginResponse
from services.auth_services import signup as signup_service, login as login_service


router = APIRouter()

@router.post("/signup", response_model=UserCreateResponse)
async def signup(userCreate: UserCreate , db : Session = Depends(get_db)):
      return await signup_service(userCreate, db)
    

@router.post("/login", response_model=UserLoginResponse)
async def login(user: UserLogin, db : Session = Depends(get_db)):
       return await login_service(user, db)