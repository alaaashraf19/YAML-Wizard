from fastapi import APIRouter,Depends, Request
from services.gitlab_connect_service import gitlab_connect_service, gitlab_callback_service
from services.github_connect_service import github_callback_service, github_connect_service
from requests import Session
from database.db_engine import get_db


router = APIRouter()



@router.get("/github/connect")
def github_connect(
    request: Request,
    db: Session = Depends(get_db)
):
    return github_connect_service(request, db)


@router.get("/github/callback")
async def github_callback(
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    return await github_callback_service(code, request, db)


@router.get("/gitlab/connect")
def gitlab_connect(request: Request,
    db: Session = Depends(get_db)):
    return gitlab_connect_service(request,db)


@router.get("/gitlab/callback")
async def gitlab_callback( code: str,
    request: Request,
    db: Session = Depends(get_db)):
    return await gitlab_callback_service(code,request,db)
    