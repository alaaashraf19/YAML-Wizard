from fastapi import APIRouter, Depends
from core.security import get_current_user


router = APIRouter()

#to be updated
@router.get("/profile")
def get_profile(current_user = Depends(get_current_user)):
    return {"username": current_user.username, "email": current_user.email}