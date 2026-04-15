import os
from dotenv import load_dotenv
from datetime import timedelta,datetime,timezone
from fastapi import HTTPException, Depends
from passlib.context import CryptContext
from fastapi.security import  OAuth2PasswordBearer
from jose import JWTError, jwt

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


#to be updated 
def get_current_user(token: str = Depends(oauth2_scheme)):
    if SECRET_KEY is None:
        raise ValueError("SECRET_KEY environment variable is not set")
    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials") #401->Unauthorized
        
        return {"username": username,"role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")