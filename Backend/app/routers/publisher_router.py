from fastapi import APIRouter, Depends, HTTPException
from database.db_engine import get_db
from core.security import get_current_user
from models.user_model import User
from models.platforms_model import GitHubInstallation,GitLabConnection, GitHubConnection
from agent.tools.repo_publisher import publish_to_repo
from agent.utils.github_auth import get_installation_token
from services.gitlab_connect_service import get_valid_gitlab_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
router = APIRouter()

@router.post("/yaml/{platform}")
async def publish_yaml(platform: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    
    if platform.lower() not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Supported: github, gitlab")
    if(platform.lower()=="github"):
        yaml_content = """
        name: CI Pipeline

        on:
        push:
            branches: [ main ]
        jobs:
        build:
            runs-on: ubuntu-latest
            steps:
            - uses: actions/checkout@v2
            - name: Set up Python
                uses: actions/setup-python@v2
                with:
                python-version: '3.x'
            - name: Install dependencies
                run: |
                python -m pip install --upgrade pip
                pip install -r requirements.txt
        """
        #will be replaced with repo model after repo fetching data
        repo_url = "https://github.com/alaaashraf19/YAML-Wizard.git"
        user_id = current_user.id
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        

        result = await db.execute(select(GitHubConnection).where(GitHubConnection.user_id == user.id))
        github_connection = result.scalar_one_or_none()

        if not github_connection:
            raise HTTPException(status_code=404, detail="GitHub account not linked")
        #rememeber to check if it is isntallation for user or org this query will change!
        installation = await db.execute(select(GitHubInstallation).where(GitHubInstallation.account_id == github_connection.github_user_id))
        installation = installation.scalar_one_or_none()

        if not installation:
            raise HTTPException(status_code=404, detail="installation not found")

        token = get_installation_token(installation.installation_id)
    else:
        yaml_content="""
        stages:
        - lint

        lint-job:
        stage: lint
        image: python:3.11

        before_script:
            - pip install ruff

        script:
            - echo "Running ruff lint..."
            - ruff check .

        rules:
            - if: '$CI_COMMIT_BRANCH == "main"'
        """
        repo_url="https://gitlab.com/alaaashraf19-group/alaaashraf19-project.git"
        user_id = current_user.id
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user_id))
        gitlab_connection = result.scalar_one_or_none()
        if gitlab_connection is None:
            raise HTTPException(status_code=404, detail="Gitlab Account not linked")
        token = await get_valid_gitlab_token(gitlab_connection, db)

    result = publish_to_repo(yaml_content=yaml_content, repo_url=repo_url, platform=platform, token=token, file_path=None, branch= "main",commit_message= "test commit message",create_pr= True, pr_branch= "test")
    print(result.success)
    