from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_current_user
from database.db_engine import get_db
from models.user_model import User
from services.user_service import upload_avatar as upload_avatar_service
from schemas.user_schema import UserResponse, UserUpdate
from services.user_service import update_user_profile,get_user_profile

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user:User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
      return await get_user_profile(current_user.id, db)

@router.put("/profile", response_model=UserResponse)
async def update_profile(user_update: UserUpdate,
                         current_user:User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
      return await update_user_profile(current_user.id,user_update, db)

@router.post("/upload/avatar")
async def upload_avatar(file: UploadFile = File(...),db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user),):
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    avatar_url = await upload_avatar_service(file.file, current_user.id)

    current_user.avatar_url = avatar_url
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return {"message": "Avatar uploaded successfully","avatar_url": avatar_url}

@router.get("/avatar")
async def get_avatar(db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user),):

    await db.refresh(current_user)

    if current_user.avatar_url:
        return {"avatar_url": current_user.avatar_url}
    else:
        return {"message": "No avatar uploaded yet."}

