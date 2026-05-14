from fastapi import HTTPException
from fastapi.responses import JSONResponse
from schemas.user_schema import UserCreate, UserCreateResponse, UserLogin,UserUpdate
from core.security import hash_password, create_access_token, verify_password, get_user
from models.user_model import User as UserModel


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
        samesite="Lax",
        max_age=60 * 60 * 24 * 7 #7 days
    )

    return response

async def update_user_profile(user_id:int, user_update: UserUpdate, db):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_update.username:
        new_username = user_update.username.lower()
        existing_user = db.query(UserModel).filter(
            UserModel.username == new_username,
            UserModel.id != user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="Username already exists")
        user.username = new_username
    if user_update.email:
        new_email = user_update.email.lower()
        existing_user = db.query(UserModel).filter(
            UserModel.email == new_email,
            UserModel.id != user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = new_email
    if user_update.new_password:
        if not user_update.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(user_update.current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        user.hashed_password = hash_password(user_update.new_password)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "msg" : "User updated successfully"
    }


async def get_user_profile(user_id: int, db):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }