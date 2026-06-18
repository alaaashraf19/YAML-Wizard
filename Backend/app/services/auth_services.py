from fastapi import HTTPException
from schemas.user_schema import UserCreate, UserCreateResponse, UserLogin, UserLoginResponse
from core.security import hash_password, create_access_token, verify_password
from models.user_model import User as UserModel


async def signup(user: UserCreate, db):
    db_user = db.query(UserModel).filter(UserModel.username == user.username.lower()).first()
    email_exists = db.query(UserModel).filter(UserModel.email == user.email.lower()).first()

    if db_user:
        raise HTTPException(
            status_code=409,
            detail=[{"loc": ["body", "username"], "msg": "Username already exists"}],
        )
    elif email_exists:
        raise HTTPException(
            status_code=409,
            detail=[{"loc": ["body", "email"], "msg": "Email already exists"}],
        )

    hashed_pw = hash_password(user.password)
    new_user = UserModel(
        username=user.username.lower(),
        email=user.email.lower(),
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserCreateResponse(message="User created successfully", user_id=str(new_user.id))


async def login(user: UserLogin, db):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    db_user = db.query(UserModel).filter(UserModel.username == user.username.lower()).first()
    hashed_pw = db_user.hashed_password if db_user else None

    if not db_user or not hashed_pw or not verify_password(user.password, hashed_pw):
        raise HTTPException(status_code=403, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": db_user.username, "role": db_user.role})
    return UserLoginResponse(access_token=access_token, token_type="bearer")
