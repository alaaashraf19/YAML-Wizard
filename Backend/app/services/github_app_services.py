from fastapi import  HTTPException
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy import select
from agent.utils.github_auth import generate_jwt, get_installation_token
from core.security import get_current_user
from models.platforms_model import GitHubInstallation as GitHubInstallationModel, GitHubInstallationRepo
from schemas.github_app_schema import GitHubInstallationRepoSchema
import os
from dotenv import load_dotenv
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
frontend_url = os.getenv("Frontend_Base_URL")
async def install_app_services():
    url = "https://github.com/apps/yaml-wizard/installations/new"
    return RedirectResponse(url, status_code=302)

async def github_webhook(request, db):
    payload = await request.json()
    event = request.headers.get("X-GitHub-Event")

    if event == "installation":

        installation_data = payload.get("installation", {})
        action = payload.get("action")

        installation_id = installation_data.get("id")
        account = installation_data.get("account", {})

        account_login = account.get("login")
        account_id = account.get("id")
        repo_selection = installation_data.get("repository_selection")

        print(
            f"App installed: {installation_id} by {account_login}, "
            f"repos selection: {repo_selection}"
        )

        result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.installation_id == installation_id))
        installation = result.scalar_one_or_none()

        if action == "created":

            if not installation:
                installation = GitHubInstallationModel(
                    installation_id=installation_id,
                    account_login=account_login,
                    account_id=account_id,
                    repos_selection=repo_selection or "all",
                )
                db.add(installation)

            else:
                installation.account_login = account_login
                installation.account_id = account_id

                if repo_selection is not None:
                    installation.repos_selection = repo_selection

        elif action == "deleted":

            if installation:
                await db.delete(installation)
                installation = None

        await db.commit()
    # repo = payload.get("repository", {})

    return {"ok": True}
            


    # The webhook may not have been received yet, or the user may have installed
    # the app previously but never linked it to their account.
    #
    # So:
    # - If the installation does not exist, we create a placeholder record.
    # - Then we ensure we have the account_id (via webhook data or GitHub API).
    # - We verify that the installation belongs to the currently authenticated GitHub user.
    # - If it is already linked to another user, we reject the request.
    # - Otherwise, we safely link this installation to the current user.


async def setup_github_url_services(installation_id, request, db):
    token = request.cookies.get("access_token")
    if not token:
        # raise HTTPException(status_code=401, detail="Unauthorized")
        return RedirectResponse(f"{frontend_url}/login")
    
    user = await get_current_user(db, token)

    result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.installation_id == installation_id))
    installation = result.scalar_one_or_none()

    if(installation 
    and installation.user_id 
    and installation.user_id != user.id
    ):
        return RedirectResponse(f"{frontend_url}/profile")
        # raise HTTPException(status_code=400, detail="Installation already linked to a different user")
    
    if installation and installation.user_id == user.id:
        return RedirectResponse(f"{frontend_url}/profile")
    
    if not installation:
        account_id = await fetch_installation_account_id(installation_id)
        installation = GitHubInstallationModel(
            installation_id=installation_id,
            account_id=account_id,
            user_id=user.id,
            repos_selection=None,  # webhook will fill this
        )
        db.add(installation)
    else:
        installation.user_id = user.id
    
    await db.commit()
    return RedirectResponse(f"{frontend_url}/profile")


async def fetch_installation_account_id(installation_id: int) -> int:
    
    """     Fetch installation account info from GitHub using app auth at any time
            This is useful when webhook might be delayed or missing, or installation created before account info update
            If webhook hasn’t arrived → fetch from GitHub directly """

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
                raise HTTPException(
            status_code=404,
            detail=response.text
        )

    elif response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail=response.text
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub API error: {response.status_code}"
        )
    


async def fetch_installation_repos(current_user, db) -> list[GitHubInstallationRepoSchema]:

    # Fetch the installation linked to the current user
    result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.user_id == current_user.id))
    installation = result.scalar_one_or_none()
    if not installation:
        return []
    installation_token = get_installation_token(installation.installation_id)

    url = "https://api.github.com/installation/repositories"

    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    #fetch existing repos once
    existing = await db.execute(
        select(GitHubInstallationRepo.repo_id).where(
            GitHubInstallationRepo.installation_id == installation.installation_id
        )
    )
    existing_ids = set(existing.scalars().all())

    repos = []
    for repo in data.get("repositories", []):
        repo_id = repo.get("id")
        repo_full_name = repo.get("full_name")
        repos.append(GitHubInstallationRepoSchema(repo_id=repo_id, repo_full_name=repo_full_name))

        if repo_id not in existing_ids:
            db.add(
                GitHubInstallationRepo(
                    installation_id=installation.installation_id,
                    repo_id=repo_id,
                    repo_full_name=repo_full_name
                )
            )

    await db.commit()

    return repos