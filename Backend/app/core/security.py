import os
from dotenv import load_dotenv
from datetime import timedelta,datetime,timezone
from fastapi import Cookie, HTTPException, Depends, status
from passlib.context import CryptContext
from fastapi.security import  OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db
from models.user_model import User
from sqlalchemy import select

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
SECRET_KEY =os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES",30)
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def create_access_token(data: dict):

    if SECRET_KEY is None:
        raise ValueError("SECRET_KEY environment variable is not set")
    
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password,hashed_password)


async def get_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()

async def get_current_user(db: AsyncSession = Depends(get_db),token: str | None = Cookie(None, alias="access_token")):
    if SECRET_KEY is None:
        raise ValueError("SECRET_KEY environment variable is not set")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        #print("COOKIE TOKEN:", token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        role = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception 
    
    user = await get_user(db, username=username.lower())
    if user is None:
        raise credentials_exception
    return user