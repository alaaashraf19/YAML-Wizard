from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request
from services.github_connect_service import github_callback_service, github_connect_service
from database.db_engine import get_db
from requests import Request, Session
from fastapi import APIRouter, Request

router = APIRouter()



@router.get("/connect")
async def github_connect(
    request: Request,
    db: Session = Depends(get_db)
):
    return await github_connect_service(request, db)


@router.get("/callback")
async def github_callback(
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    return await github_callback_service(code, request, db)