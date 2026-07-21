from datetime import datetime
from services.platform_connectors.gitlab_connect import GitLabConnector
from models.user_model import User
from schemas.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from models.project_model import Project
from models.repository_model import Repository
from models.repo_context_model import RepoContext as RepoContextModel
from models.platforms_model import GitHubConnection, GitHubInstallation, GitLabConnection, GitHubInstallationRepo
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .dashboard.repos_services import _parse_repo_info,_parse_branch, _get_gitlab_proj_id, get_github_default_branch,get_gitlab_default_branch
from .platform_connectors.oauth_utils import decrypt_token
from sqlalchemy.exc import IntegrityError
from fastapi.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)


async def get_user_projects(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Project, Repository)
        .join(Repository, Project.repo_id == Repository.id)
        .where(Project.user_id == user_id)
    )
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
            branch=repo.default_branch
        )
        for project, repo in rows
    ]


async def _resolve_token(user_id: int, platform: str, repo_url: str, db: AsyncSession) -> tuple[str | None, str | None]:
    if platform == "github":
        inst_result = await db.execute(
            select(GitHubInstallation).where(GitHubInstallation.user_id == user_id).limit(1)
        )
        installation = inst_result.scalar_one_or_none()
        if installation:

            result = await db.execute(
                select(GitHubInstallationRepo)
                .join(
                    GitHubInstallation,
                    GitHubInstallation.installation_id
                    == GitHubInstallationRepo.installation_id,
                )
                .where(
                    GitHubInstallation.user_id == user_id,
                    GitHubInstallationRepo.repo_url == repo_url,
                )
            )
            authorized_repo = result.scalar_one_or_none()
            if authorized_repo:
                try:
                    from core.github_auth import get_installation_token
                    token = await run_in_threadpool(get_installation_token, authorized_repo.installation_id)
                    
                    logger.info("Using GitHub installation token for user_id=%s", user_id)
                    return token, "installation"
                except Exception as exc:
                    logger.warning("Installation token failed: %s", exc)

        conn_result = await db.execute(
            select(GitHubConnection).where(GitHubConnection.user_id == user_id))
        connection = conn_result.scalar_one_or_none()
        if connection and connection.access_token:
            try:
                return decrypt_token(connection.access_token), "connection"
            except Exception as exc:
                logger.warning("Decrypt GitHub token failed: %s", exc)

    elif platform == "gitlab":
        conn_result = await db.execute(
            select(GitLabConnection).where(GitLabConnection.user_id == user_id)
        )
        connection = conn_result.scalar_one_or_none()
        if connection and connection.access_token:
            try:
                gitlab_connector = GitLabConnector()
                return await gitlab_connector.get_valid_token(connection, db), "connection"
            except Exception as exc:
                logger.warning("Decrypt GitLab token failed: %s", exc)

    return None, None


async def create_project(project: ProjectCreate, user_id: int, db: AsyncSession):

    project_data = project.model_dump()

    repo_url = project_data['url'].rstrip("/")

    #does this user already have this url or this github ID?
    existing_stmt = select(Repository).where(
        Repository.user_id == user_id,
        (Repository.url == repo_url) | 
        (Repository.github_repo_id == project.github_repo_id if project.github_repo_id else False)
    )
    result = await db.execute(existing_stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already added this repository.")
        
    try:
        full_name, detected_platform = _parse_repo_info(repo_url)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Entered URL is invalid"
        )
    
    gitlab_project_id = None
    installation_id = None
    github_repo_id = None

    if detected_platform not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    token, _ = await _resolve_token(user_id=user_id, platform=detected_platform, repo_url=repo_url, db=db)
    if not token:
        raise HTTPException(status_code=401, detail="No authentication token available.")

    if detected_platform == "github":
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        from services.github_app_services import fetch_installation_repos
        await fetch_installation_repos(current_user=user, db=db)

        result = await db.execute(
            select(GitHubInstallationRepo)
            .join(
                GitHubInstallation,
                GitHubInstallation.installation_id
                == GitHubInstallationRepo.installation_id,
            )
            .where(
                GitHubInstallation.user_id == user_id,
                GitHubInstallationRepo.repo_url == repo_url,
            )
        )
        authorized_repo = result.scalar_one_or_none()

        if authorized_repo is not None:
            installation_id = authorized_repo.installation_id
            github_repo_id = authorized_repo.repo_id
        else:
            result = await db.execute(
                select(GitHubConnection).where(
                    GitHubConnection.user_id == user_id
                )
            )
            github_connection = result.scalar_one_or_none()
            if github_connection is None:
                raise HTTPException(
                    status_code=403,
                    detail=f"{detected_platform.upper()} account is required"
                )

    elif detected_platform == "gitlab":
        result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user_id))
        connection = result.scalar_one_or_none()

        if connection is None:
            raise HTTPException(
                status_code=403,
                detail=f"{detected_platform.upper()} account is required"
            )
        gitlab_project_id = await _get_gitlab_proj_id(full_name,token)

    if project.github_repo_id is not None:
        github_repo_id = project.github_repo_id

    repo = Repository(
        full_name=full_name,
        platform=detected_platform,
        gitlab_project_id=gitlab_project_id,
        default_branch=None,
        url=repo_url,
        user_id=user_id,
        github_repo_id=github_repo_id,
        installation_id=installation_id,
    )
    try:
        db.add(repo)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Repository URL already exists")
    await db.refresh(repo)


    #### get branch fron url and if no branch specified then turn to get default branch of the repo
    default_branch = await _parse_branch(repo.url, repo.platform, repo.full_name, token)
    repo.default_branch = default_branch

    try:
        await _fetch_and_save_repo_context(
            repo_id=repo.id,
            repo_url=repo_url,
            platform=detected_platform,
            token=token,
        )
    except* PermissionError as eg:
        await db.delete(repo)
        await db.commit()
        logger.exception("Failed to fetch repository context for repo_id=%s", repo.id)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch repository context. Check the URL and your access permissions.",
        )

    new_project = Project(
        project_name=project_data['project_name'],
        user_id=user_id,
        repo_id=repo.id,
        github_installation_id=installation_id,
    )

    if project.install_id is not None:
        new_project.github_installation_id = project.install_id
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
        branch=repo.default_branch,
    )


async def _fetch_and_save_repo_context(repo_id: int, repo_url: str, platform: str, token: str):
    """Fetch repo context and persist it.  Raises on fatal errors so the
    caller can roll back the repo row and surface a proper HTTP error."""
    from database.db_engine import async_session

    # Fatal errors (bad URL, bad token, repo not found, network failure)
    # are allowed to propagate — the caller handles cleanup.
    # Non-fatal gaps (e.g. missing optional files) are already handled
    # gracefully inside the agents themselves.
    if platform == "github":
        from agent.github_agent import run_github_agent
        pkg = await run_in_threadpool(run_github_agent, repo_url=repo_url, github_token=token)
    else:
        from agent.gitlab_agent import run_gitlab_agent
        pkg = await run_in_threadpool(run_gitlab_agent, repo_url=repo_url, gitlab_token=token)

    context_fields = dict(
        languages           = pkg.languages,
        frameworks          = pkg.frameworks,
        build_tools         = pkg.build_tools,
        test_runners        = pkg.test_runners,
        test_commands       = pkg.test_commands,
        build_commands      = pkg.build_commands,
        env_vars            = pkg.env_vars,
        services            = pkg.services,
        has_docker          = pkg.has_docker,
        has_existing_ci     = pkg.has_existing_ci,
        existing_ci_content = pkg.existing_ci_content,
        has_test_reports    = pkg.has_test_reports,
        report_formats      = pkg.report_formats,
        key_files           = pkg.key_files,
        directory_tree      = pkg.directory_tree,
    )

    async with async_session() as db:
        try:
            result = await db.execute(
                select(RepoContextModel).where(RepoContextModel.repo_id == repo_id)
            )
            record = result.scalar_one_or_none()

            if record is None:
                record = RepoContextModel(repo_id=repo_id, **context_fields)
                db.add(record)
            else:
                for k, v in context_fields.items():
                    setattr(record, k, v)

            await db.commit()
            logger.info("RepoContext saved for repo_id=%s", repo_id)

        except Exception as exc:
            await db.rollback()
            logger.error("Failed to save RepoContext for repo_id=%s: %s", repo_id, exc, exc_info=True)


async def update_project(project_id: int, user_id: int, project_update: ProjectUpdate, db: AsyncSession):
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

        full_name, detected_platform = _parse_repo_info(repo.url)
        repo.full_name=full_name
        if detected_platform not in ["github", "gitlab"]:
            raise HTTPException(status_code=400, detail="Unsupported platform.")
        
        repo.platform = detected_platform

        token, _ = await _resolve_token(user_id=user_id, platform=detected_platform, repo_url=repo.url, db=db)
        if not token:
            await db.delete(repo)
            await db.commit()
            raise HTTPException(status_code=401,detail="No authentication token available.")
        
        default_branch = await _parse_branch(repo.url, repo.platform, repo.full_name, token)
        repo.default_branch = default_branch
       
        print(default_branch)
        repo.gitlab_project_id = await _get_gitlab_proj_id(repo.full_name,token) if detected_platform == "gitlab" else None

    project.updated_at = datetime.utcnow()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Repository URL already exists")
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
        branch=repo.default_branch
    )


async def delete_project(project_id: int, user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return {"project deleted successfully"}


async def get_project_by_id(project_id: int, user_id: int, db: AsyncSession) -> ProjectResponse:
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
        branch=repo.default_branch
        )

async def get_projectModel_by_id(project_id: int,user_id: int, db: AsyncSession)-> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project