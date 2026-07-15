import cloudinary.uploader
from fastapi import HTTPException
from schemas.user_schema import UserUpdate
from core.security import hash_password, verify_password
from models.user_model import User as UserModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def update_user_profile(user_id: int, user_update: UserUpdate, db: AsyncSession):

    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.username:
        new_username = user_update.username.lower()

        result = await db.execute(
            select(UserModel).where(
                UserModel.username == new_username,
                UserModel.id != user.id
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=409, detail="Username already exists")
        user.username = new_username

    if user_update.email:
        new_email = user_update.email.lower()

        result = await db.execute(
            select(UserModel).where(
                UserModel.email == new_email,
                UserModel.id != user.id
            )
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = new_email

    if user_update.new_password:
        if not user_update.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")

        if not verify_password(user_update.current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        user.hashed_password = hash_password(user_update.new_password)

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "msg": "User updated successfully"
    }


async def get_user_profile(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }


async def upload_avatar(file, user_id: int) -> str:

    """Upload image to Cloudinary and return secure URL"""

    result = cloudinary.uploader.upload(
        file,
        folder="avatars",
        public_id=f"user_{user_id}",
        overwrite=True,
        resource_type="image",
        transformation=[
        {"width": 512, "height": 512, "crop": "limit"},  # resize
        {"quality": "auto:good"},  # auto compression
        {"fetch_format": "auto"} ]  # converts to webp if better
    )

    return result["secure_url"]