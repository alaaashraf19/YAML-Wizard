from datetime import datetime
from schemas.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from models.project_model import Project
from models.repository_model import Repository
from fastapi import HTTPException
from sqlalchemy import select,update,delete
from sqlalchemy.ext.asyncio import AsyncSession
from .dashboard.repos_services import _parse_repo_info, _parse_branch, _get_gitlab_proj_id
from sqlalchemy.exc import IntegrityError


async def get_user_projects(user_id: int, db: AsyncSession):
    result = await db.execute(
    select(Project, Repository)
    .join(Repository, Project.repo_id == Repository.id)
    .where(Project.user_id == user_id))

    rows = result.all()
    return [
    ProjectResponse(
        id=project.id,
        user_id=project.user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        project_name=project.project_name,
        repo_id=repo.id,
        platform=repo.platform,
        repo_url=repo.url,
    )
    for project, repo in rows
]



async def create_project(project: ProjectCreate,user_id:int, db: AsyncSession):
    project_data = project.model_dump()
    project_data['user_id'] = user_id

    repo_url=project_data['url'].rstrip("/")
    full_name, detected_platform = _parse_repo_info(repo_url)
    default_branch = _parse_branch(repo_url)
    if default_branch is None:
        default_branch = "main"

    if detected_platform not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Unsupported platform. Only 'github' and 'gitlab' are supported.")
    if detected_platform == "gitlab":
        gitlab_project_id = await _get_gitlab_proj_id(full_name)

    repo = Repository(
        full_name=full_name,
        platform=detected_platform,
        gitlab_project_id= gitlab_project_id if detected_platform == "gitlab" else None,
        default_branch=default_branch,
        url=repo_url,
        user_id=user_id
    )

    try:
        db.add(repo)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409,detail="Repository URL already exists")
    await db.refresh(repo)
    new_project = Project(
        project_name=project_data['project_name'],
        user_id=user_id,
        repo_id=repo.id
    )

    new_project.created_at = datetime.utcnow()
    new_project.updated_at = datetime.utcnow()
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return ProjectResponse(
        id=new_project.id,
        user_id=user_id,
        created_at=new_project.created_at,
        updated_at=new_project.updated_at,
        project_name=new_project.project_name,
        repo_id=repo.id,
        platform=repo.platform,
        repo_url=repo.url,
        )

async def update_project(project_id: int, user_id:int, project_update: ProjectUpdate, db: AsyncSession):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    repo_result = await db.execute(select(Repository).where(Repository.id == project.repo_id))
    repo = repo_result.scalars().one_or_none()
    
    if project_update.project_name is not None:
        project.project_name = project_update.project_name
    
    if project_update.repo_url is not None:
        repo.url = project_update.repo_url
        repo.full_name, detected_platform = _parse_repo_info(repo.url)
        default_branch = _parse_branch(repo.url)
        if default_branch is None:
            default_branch = "main"
        repo.default_branch =default_branch

        if detected_platform not in ["github", "gitlab"]:
            raise HTTPException(status_code=400, detail="Unsupported platform. Only 'github' and 'gitlab' are supported.")
        repo.platform = detected_platform
        if detected_platform == "gitlab":
            repo.gitlab_project_id = await _get_gitlab_proj_id(repo.full_name)
        else:
            repo.gitlab_project_id = None

    
    project.updated_at = datetime.utcnow()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Repository URL already exists"
        )
    await db.refresh(project)
    await db.refresh(repo)

    return ProjectResponse(
        id=project_id,
        user_id=user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        project_name=project.project_name,
        repo_id=repo.id,
        platform=repo.platform,
        repo_url=repo.url,
        )

async def delete_project(project_id: int,user_id: int, db: AsyncSession) ->str:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return {"project deleted successfully"}

async def get_project_by_id(project_id: int,user_id:int, db: AsyncSession)-> ProjectResponse:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    repo_result = await db.execute(select(Repository).where(Repository.id == project.repo_id))
    repo = repo_result.scalars().one_or_none()

    return ProjectResponse(
        id=project_id,
        user_id=user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        project_name=project.project_name,
        repo_id=repo.id,
        platform=repo.platform,
        repo_url=repo.url,
        )

async def get_projectModel_by_id(project_id: int,user_id: int, db: AsyncSession)-> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

async def _check_url_duplicates(repo_url:str, db: AsyncSession, ) :
    result = await db.execute(select(Repository).where(Repository.url == repo_url))
    existing_repo = result.scalar_one_or_none()

    if existing_repo:
        raise HTTPException( status_code=409,detail="Repository URL already exists")