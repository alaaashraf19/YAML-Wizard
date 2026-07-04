import datetime
from fastapi import APIRouter, Depends, HTTPException
from models.project_model import Project
from models.pipeline_model import Pipeline
from models.repository_model import Repository
from services.project_service import _resolve_token
from database.db_engine import get_db
from core.security import get_current_user
from models.user_model import User
from models.platforms_model import GitHubInstallation,GitLabConnection, GitHubConnection
from services.repo_publish_service import publish_to_repo_tool
from core.github_auth import get_installation_token
from services.platform_connectors.gitlab_connect import GitLabConnector
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas.publish_yaml_schema import PublishResult, PublishRequest
router = APIRouter()

@router.post("/yaml/{platform}/{project_id}/{pipeline_id}", response_model=PublishResult)
async def publish_yaml(platform: str,project_id: int, pipeline_id:int, publishrequest: PublishRequest
                    ,current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    

    #here is for button publish in chat where the project is already there 
    #and the pipeline is already approved
    if platform.lower() not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Supported: github, gitlab")
    
    user_id = current_user.id
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    
    project_result = await db.execute(select(Project).where(Project.id == project_id))
    project = project_result.scalar_one_or_none()
    if not project: 
        raise HTTPException(status_code=404, detail="Project not found")
    
    repo_result = await db.execute(select(Repository).where(Repository.id == project.repo_id))
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    branch = repo.default_branch

    pipeline_result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = pipeline_result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    yaml_content = pipeline.content

    token, source = await _resolve_token(user_id, platform.lower() , repo.url,db)
    if not token:
        raise HTTPException(status_code=401, detail="No authentication token available.")
    
    commit_message = publishrequest.commit_message if publishrequest.commit_message else f"ci: add CI/CD pipeline via YAML Wizard"
    result = publish_to_repo_tool(yaml_content=yaml_content, repo_url=repo.url, platform=platform, token=token, 
                                  file_path=pipeline.path, branch=branch,
                                  commit_message= commit_message, 
                                  create_pr= publishrequest.create_pr, pr_branch= publishrequest.pr_branch)
    if not result.success:
        raise HTTPException(status_code=500, detail=f"Failed to publish YAML: {result.message}")
    
    author = None
    if source == "installation":
        inst = await db.execute(select(GitHubInstallation).where(GitHubInstallation.user_id == user_id))
        inst = inst.scalar_one_or_none()
        author = inst.account_login if inst else None
    
    elif source == "connection":
        if platform.lower() == "github":

            conn = await db.execute(select(GitHubConnection).where(GitHubConnection.user_id == user_id))
            conn = conn.scalar_one_or_none()
            author = conn.github_username if conn else None
        
        else:
            conn =await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user_id))
            conn = conn.scalar_one_or_none()
            author = conn.gitlab_username if conn else None
    pipeline.commit_author = author
    pipeline.committed_at = datetime.datetime.utcnow()
    pipeline.activated_at = datetime.datetime.utcnow()
    pipeline.is_active = True
    pipeline.is_generated_by_wizard = True
    pipeline.commit_message = commit_message
    await db.commit()
    return result
    print(result.success)


    

