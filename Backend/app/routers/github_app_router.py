from fastapi import APIRouter, Depends
from core.security import get_current_user
from services.github_app_services import github_webhook as github_webhook_services, install_app_services, setup_github_url_services
from database.db_engine import get_db
from requests import Session
from models.user_model import User
router = APIRouter()

#may be moved to projects service
#this is for adding a project but without the url
#using the github app installation we can get the repos of the user and then we can ask the user to select the repo
@router.post("/install_app",)
async def install_app():
    #redirect user to github app installation page
    return await install_app_services()

@router.get("/setup")
async def setup_github_url(installation_id:int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await setup_github_url_services(installation_id,current_user,db)