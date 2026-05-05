from fastapi import  HTTPException, Request
from fastapi.responses import RedirectResponse
import httpx
from models.user_model import User
from agent.utils.github_auth import generate_jwt
from core.security import get_current_user
from models.github_installation_model import GitHubInstallation as GitHubInstallationModel
from models.user_model import User as UserModel
from dotenv import load_dotenv
import os
load_dotenv()


# User clicks button
#         ↓
# Redirect to GitHub
#         ↓
# User installs app
#         ↓
# GitHub sends webhook
#         ↓
# github_webhook() runs and we listen to evennts

# User installs your GitHub App

# GitHub sends a webhook:

# {
#   "action": "created",
#   "installation": {
#     "id": 123456
#   }
# }
# GitHub redirects browser:
#    https://yourapp.com/setup?installation_id=123
#    ↓
# Your /setup endpoint runs
#    ↓
# You link:
#    installation_id ↔ current_user.id
#    ↓
# Done

async def install_app_services():
    url = "https://github.com/apps/yaml-wizard/installations/new"
    return RedirectResponse(url, status_code=302)

async def github_webhook(request, db):
    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")

    if event == "installation" and payload.get("action") == "created":

        installation_data = payload.get("installation", {})
        account = installation_data.get("account", {})

        installation_id = installation_data.get("id")
        account_login = account.get("login")
        account_id = account.get("id")

        #account_type = payload["installation"]["account"]["type"] # User | Organization
        print(f"App installed: {installation_id} by {account_login}")
        
        installation = db.query(GitHubInstallationModel).filter(GitHubInstallationModel.installation_id == installation_id).first()

        if not installation:
            installation = GitHubInstallationModel(
                installation_id=installation_id,
                account_login=account_login,
                account_id=account_id
            )
            db.add(installation)

        else:
            # update info if already exists
            installation.account_login = account_login
            installation.account_id = account_id
        db.commit()


    elif event == "installation" and payload.get("action") == "deleted":
        installation_id = payload["installation"]["id"]

        installation = db.query(GitHubInstallationModel).filter(GitHubInstallationModel.installation_id == installation_id).first()
        if installation:
            # either delete OR unlink
            db.delete(installation)
            db.commit()
            
    # repo = payload.get("repository", {})

    # repo_id = repo.get("id")
    # full_name = repo.get("full_name")
    # default_branch = repo.get("default_branch")
    # private = repo.get("private")
    
    return {"ok": True}



async def setup_github_url_services(installation_id, request, db):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = get_current_user(db, token)

    if user.github_id is None:
        raise HTTPException(
            status_code=400, 
            detail="Please connect your GitHub account first"
        )
    
    # The webhook may not have been received yet, or the user may have installed
    # the app previously but never linked it to their account.
    #
    # So:
    # - If the installation does not exist, we create a placeholder record.
    # - Then we ensure we have the account_id (via webhook data or GitHub API).
    # - We verify that the installation belongs to the currently authenticated GitHub user.
    # - If it is already linked to another user, we reject the request.
    # - Otherwise, we safely link this installation to the current user.

    installation = db.query(GitHubInstallationModel).filter(GitHubInstallationModel.installation_id == installation_id).first()

    if not installation:
        installation = GitHubInstallationModel(installation_id=installation_id)
        db.add(installation)
        db.flush() # Get the installation in DB without committing
    

    account_id = installation.account_id
    if account_id is None:
        account_id = await fetch_installation_account_id(installation_id)
        installation.account_id = account_id
        db.flush() #If an exception happens after this → transaction is rolled back
    
    if account_id != user.github_id:
        raise HTTPException(
            status_code=403, 
            detail="This installation belongs to a different GitHub account"
        )
    
    user_id = installation.user_id
    if user_id is not None and user_id != user.id:
        raise HTTPException(
            status_code=400, 
            detail="This GitHub installation is already linked to another user"
        )
        
    installation.user_id = user.id
    db.commit()

    return {"message": "GitHub app setup successful"} #link to a page where he can return to user profile page or home page


async def fetch_installation_account_id(installation_id: int) -> int:
    """Fetch installation account info from GitHub using app auth at any time
    This is useful when webhook might be delayed or missing, or installation created before account info update
    """
    """If webhook hasn’t arrived → fetch from GitHub directly"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {generate_jwt()}",
                "Accept": "application/vnd.github+json"
            }
        )
    
    if response.status_code == 200:
        data = response.json()
        account_id: int = data["account"]["id"] 
        return account_id
    elif response.status_code == 404:
        raise HTTPException(status_code=404, detail="Installation not found")

    elif response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid GitHub App JWT")

    else:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub API error: {response.status_code}"
        )