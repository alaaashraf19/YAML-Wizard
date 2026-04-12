from fastapi import APIRouter
from app.schemas.user_schema import UserCreate, UserLogin, UserLoginResponse
from app.services.auth_services import signup as signup_service, login as login_service


router = APIRouter()

@router.post("/signup", response_model=str)
def signup(user: UserCreate):
        return signup_service(user)
    

@router.post("/login", response_model=UserLoginResponse)
async def login(user: UserLogin):
    await login_service(user)