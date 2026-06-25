from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy import select
from core.github_auth import get_installation_token, generate_jwt
from core.security import get_current_user
from models.platforms_model import GitHubInstallation as GitHubInstallationModel, GitHubInstallationRepo
from schemas.github_app_schema import GitHubInstallationRepoSchema
from schemas.project_schema import ProjectCreate
from services.project_service import create_project
import os
from dotenv import load_dotenv
import asyncio

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
    # print(payload)

    selection= payload.get("repository_selection")
    print("selection",selection)
    event = request.headers.get("X-GitHub-Event")

    if event == "installation":

        installation_data = payload.get("installation", {})
        action = payload.get("action")

        installation_id = installation_data.get("id")
        account = installation_data.get("account", {})

        account_login = account.get("login")
        account_id = account.get("id")
        account_type = account.get("type")
        repo_selection = installation_data.get("repository_selection")

        result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.installation_id == installation_id))
        installation = result.scalar_one_or_none()

        if action == "created":
            print(
                f"App installed: {installation_id} by {account_login}, "
                f"repos selection: {repo_selection}",  f"account_type: {account_type}"
            )

            if not installation:
                installation = GitHubInstallationModel(
                    installation_id=installation_id,
                    account_login=account_login,
                    account_id=account_id,
                    account_type=account_type,
                    repos_selection=repo_selection,
                    user_id=None,  # will be linked later in /setup
                )
                print("WEBHOOK creating install model", installation_id)
                db.add(installation)

            else:
                installation.account_login = account_login
                installation.account_id = account_id
                installation.account_type = account_type

                if repo_selection is not None:
                    installation.repos_selection = repo_selection

        elif action == "deleted":

            if installation:
                print(
                f"App uninstalled: {installation_id} by {account_login}, "
                f"repos selection: {repo_selection}",  f"account_type: {account_type}")
                await db.delete(installation)

        await db.commit()


    elif event == "installation_repositories":
        print("here 1")
        installation_data = payload.get("installation", {})
        print(installation_data)
        print("repository_selection =", installation_data.get("repository_selection"))
        installation_id = installation_data.get("id")
        repo_selection_value = installation_data.get("repository_selection")

        result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.installation_id == installation_id))
        installation = result.scalar_one_or_none()

        account = installation_data.get("account", {})

        account_login = account.get("login")
        account_id = account.get("id")
        account_type = account.get("type")
        if not installation:
            installation = GitHubInstallationModel(
                installation_id=installation_id,
                account_login=account_login,
                account_id=account_id,
                account_type=account_type,
                repos_selection=repo_selection_value,
                user_id=None,  # will be linked later in /setup
            )
            db.add(installation)
        else:
            if repo_selection_value:
                installation.repos_selection=repo_selection_value
        await db.commit()

        repositories_added = payload.get("repositories_added", [])
        repositories_removed = payload.get("repositories_removed", [])

        #add repos
        for repo in repositories_added:

            repo_id = repo.get("id")
            if not repo_id:
                continue #since our db logic depend on repo id if we didnt receive it we discard 

            existing = await db.execute(
                select(GitHubInstallationRepo).where(
                    GitHubInstallationRepo.installation_id == installation_id,
                    GitHubInstallationRepo.repo_id == repo_id,)
            )

            if existing.scalar_one_or_none():
                continue
            print("WEBHOOK creating repo", installation_id)
            db.add(
                GitHubInstallationRepo(
                    installation_id=installation_id,
                    repo_id=repo_id,
                    repo_full_name=repo.get("full_name"),
                    repo_url=repo.get("html_url"),#we create it since it doesnt return from payload
                )
            )

        #remove repos
        for repo in repositories_removed:
            print("here 2")

            repo_id = repo.get("id")
            if not repo_id:
                continue 

            result = await db.execute(
                select(GitHubInstallationRepo).where(
                    GitHubInstallationRepo.installation_id == installation_id,
                    GitHubInstallationRepo.repo_id == repo_id,)
            )

            repo_record = result.scalar_one_or_none()

            if repo_record:
                await db.delete(repo_record)

        await db.commit()
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
        return RedirectResponse(f"{frontend_url}/login")

    user = await get_current_user(db, token)

    installation = None

    # Wait up to 10 seconds for webhook to create installation
    for _ in range(10):
        result = await db.execute(
            select(GitHubInstallationModel).where(
                GitHubInstallationModel.installation_id == installation_id
            )
        )
        installation = result.scalar_one_or_none()

        if installation:
            break

        await asyncio.sleep(1)

    if not installation:
        print(f"Installation {installation_id} not found after waiting")
        return RedirectResponse(
            f"{frontend_url}/profile?status=installation_not_ready"
        )

    # Installation belongs to another user
    if (
        installation.user_id is not None
        and installation.user_id != user.id
    ):
        return RedirectResponse(f"{frontend_url}/profile")

    # Already linked to this user
    if installation.user_id == user.id:
        await create_proj_after_install(user, db, installation_id)
        return RedirectResponse(f"{frontend_url}/profile")

    # Link installation to user
    installation.user_id = user.id

    # Fill missing account info if needed
    if (
        installation.account_id is None
        or installation.account_login is None
        or installation.account_type is None
    ):
        account_data = await fetch_installation_account_data(
            installation_id
        )

        installation.account_id = account_data.get("id")
        installation.account_login = account_data.get("login")
        installation.account_type = account_data.get("type")
        installation.repos_selection = account_data.get("repository_selection") 

    await db.commit()

    await create_proj_after_install(user, db, installation_id)

    return RedirectResponse(f"{frontend_url}/profile")

async def create_proj_after_install(user,db, installation_id):

    repos = await fetch_installation_repos(user, db)#will save newly installed repos in db of type githubinstallationrepo and model
    #for each repo we create a project by sending repo url and repo fullname added to it _proj as project name
    for repo in repos:
        project_name = repo.repo_full_name.split("/")[-1] + "_project"
        create_request = ProjectCreate(
                project_name=project_name,
                url= repo.repo_url,
                install_id=installation_id,
        )
        print("here 4")
        await create_project(create_request, user.id,db)

    


async def fetch_installation_account_data(installation_id: int) -> dict:
    
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
    
    response.raise_for_status()
    data = response.json()

    account = data.get("account", {})

    return {
        "id": account.get("id"),
        "login": account.get("login"),
        "type": account.get("type"),  #"User" or "Organization"
    }
    


async def fetch_installation_repos(current_user, db) -> list[GitHubInstallationRepoSchema]:

    # Fetch the installation linked to the current user
    result = await db.execute(select(GitHubInstallationModel).where(GitHubInstallationModel.user_id == current_user.id))
    installations = result.scalars().all()

    if not installations:
        return []
    
    repos = []

    for installation in installations:
        installation_token = get_installation_token(
            installation.installation_id
        )

        headers = {
            "Authorization": f"Bearer {installation_token}",
            "Accept": "application/vnd.github+json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/installation/repositories",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

        existing = await db.execute(
            select(GitHubInstallationRepo.repo_id).where(
                GitHubInstallationRepo.installation_id
                == installation.installation_id
            )
        )

        existing_ids = set(existing.scalars().all())

        for repo in data.get("repositories", []):
            repo_id = repo["id"]
            repo_full_name = repo["full_name"]
            repo_url = repo["html_url"]

            repos.append(
                GitHubInstallationRepoSchema(
                    repo_id=repo_id,
                    repo_full_name=repo_full_name,
                    repo_url=repo_url
                )
            )

            if repo_id not in existing_ids:
                db.add(
                    GitHubInstallationRepo(
                        installation_id=installation.installation_id,
                        repo_id=repo_id,
                        repo_full_name=repo_full_name,
                        repo_url=repo_url,
                    )
                )

    await db.commit()
    return repos