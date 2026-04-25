from fastapi import  Request
from fastapi.responses import RedirectResponse
from schemas.github_installation_schema import GitHubInstallation



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

#try also first url 
#this redirects user to installation page and github handles installation ui and then github calls the webhook automatically 
# when the app is installed and we can specify the events we want to listen to in the app settings in github developer settings
async def install_app_services():
    #url ="https://github.com/apps/yaml-wizard"
    url = "https://github.com/apps/yaml-wizard/installations/new"
    return RedirectResponse(url)

async def github_webhook(request: Request, db):
    payload = await request.json()
    if payload.get("action") == "created" and "installation" in payload:
        installation_id = payload["installation"]["id"]
        account_login = payload["installation"]["account"]["login"]
        account_id = payload["installation"]["account"]["id"]#better to use id than login because login can change but id is fixed
        #account_type = payload["installation"]["account"]["type"] # User | Organization
        print(f"App installed: {installation_id} by {account_login}")


        db.add(GitHubInstallation(
            installation_id=installation_id,
            account_login=account_login,
            account_id=account_id
        ))
        db.commit()
    
    # repo = payload.get("repository", {})

    # repo_id = repo.get("id")
    # full_name = repo.get("full_name")
    # default_branch = repo.get("default_branch")
    # private = repo.get("private")

    return {"ok": True}


async def setup_github_url_services(installation_id:int,current_user,db):
    #we will link the installation to the user
    installation = db.query(GitHubInstallation).filter(GitHubInstallation.installation_id == installation_id).first()
    if installation:
        installation.user_id = current_user.id
        db.commit()
        return {"message": "GitHub app setup successful"} #make him a page where he can return to user profile page or home page
    else:
        return {"message": "Installation not found"}, 404

