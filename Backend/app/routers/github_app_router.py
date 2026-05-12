from fastapi import APIRouter, Depends, Request
from services.github_app_services import  github_webhook as github_webhook_services, install_app_services, setup_github_url_services
from database.db_engine import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

#may be moved to projects service
#this is for adding a project but without the url
#using the github app installation we can get the repos of the user and then we can ask the user to select the repo
@router.get("/install_app")
async def install_app():
    #redirect user to github app installation page
    return await install_app_services()

@router.post("/webhook")
async def github_webhook(request: Request, db: AsyncSession  = Depends(get_db)):
    return await github_webhook_services(request, db)

@router.get("/setup")
async def setup_github_url(installation_id:int, request: Request , db: AsyncSession  = Depends(get_db)):
    return await setup_github_url_services(installation_id,request,db)
