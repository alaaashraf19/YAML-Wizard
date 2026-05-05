from fastapi import HTTPException
from fastapi.responses import JSONResponse
from schemas.user_schema import UserCreate, UserCreateResponse, UserLogin
from core.security import hash_password, create_access_token, verify_password, get_user
from models.user_model import User as UserModel
from services.github_connect_service import is_github_token_valid

async def signup(user: UserCreate, db):
    username = user.username.lower()
    email = user.email.lower()
    db_user = get_user(db, username)
    email_exists = db.query(UserModel).filter(UserModel.email == email).first()
    
    if db_user:
        raise HTTPException(
            status_code=409,
            detail=[{"loc": ["body", "username"], "msg": "Username already exists"}]
        )
    elif email_exists:
        raise HTTPException(
            status_code=409,
            detail=[{"loc": ["body", "email"], "msg": "Email already exists"}]
        )

    hashed_pw = hash_password(user.password)
    
    new_user = UserModel(
        username=username,
        email=email,
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserCreateResponse(msg = "User created successfully", user_id = str(new_user.id))



async def login(user: UserLogin, db):

    username = user.username
    password = user.password
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    
    db_user = db.query(UserModel).filter(UserModel.username == username.lower()).first()
    hashed_pw = db_user.hashed_password if db_user else None

    if not db_user or not hashed_pw or not verify_password(password, hashed_pw):
        raise HTTPException(status_code=403, detail="Invalid username or password")

    access_token = create_access_token(
            data={"sub": db_user.username, "role": db_user.role}
        )
    
    response = JSONResponse(
        content={
            "username": user.username, 
            "role": db_user.role,
            "msg": "Logged in successfully"
        })
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,        # ===========> MAKE SECURE FOR HTTPS
        samesite="none",
        max_age=60 * 60 * 24 * 7 #7 days
    )

    return response

