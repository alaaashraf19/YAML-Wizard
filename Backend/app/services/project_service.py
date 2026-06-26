from datetime import datetime
from schemas.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from models.project_model import Project
from models.repository_model import Repository
from models.repo_context_model import RepoContext as RepoContextModel
from models.platforms_model import GitHubConnection, GitHubInstallation, GitLabConnection
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .dashboard.repos_services import _parse_repo_info, _parse_branch, _get_gitlab_proj_id
from .platform_connectors.oauth_utils import decrypt_token
from sqlalchemy.exc import IntegrityError
from fastapi.concurrency import run_in_threadpool
import asyncio
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
        )
        for project, repo in rows
    ]


async def _resolve_token(user_id: int, platform: str, db: AsyncSession) -> str | None:
    if platform == "github":
        inst_result = await db.execute(
            select(GitHubInstallation).where(GitHubInstallation.user_id == user_id).limit(1)
        )
        installation = inst_result.scalar_one_or_none()
        if installation:
            try:
                from core.github_auth import get_installation_token
                token = await run_in_threadpool(get_installation_token, installation.installation_id)
                logger.info("Using GitHub installation token for user_id=%s", user_id)
                return token
            except Exception as exc:
                logger.warning("Installation token failed: %s", exc)

        conn_result = await db.execute(
            select(GitHubConnection).where(GitHubConnection.user_id == user_id)
        )
        connection = conn_result.scalar_one_or_none()
        if connection and connection.access_token:
            try:
                return decrypt_token(connection.access_token)
            except Exception as exc:
                logger.warning("Decrypt GitHub token failed: %s", exc)

    elif platform == "gitlab":
        conn_result = await db.execute(
            select(GitLabConnection).where(GitLabConnection.user_id == user_id)
        )
        connection = conn_result.scalar_one_or_none()
        if connection and connection.access_token:
            try:
                return decrypt_token(connection.access_token)
            except Exception as exc:
                logger.warning("Decrypt GitLab token failed: %s", exc)

    return None


async def create_project(project: ProjectCreate, user_id: int, db: AsyncSession):
    project_data = project.model_dump()

    repo_url = project_data['url'].rstrip("/")
    full_name, detected_platform = _parse_repo_info(repo_url)
    default_branch = _parse_branch(repo_url)
    if default_branch is None:
        default_branch = "main"

    if detected_platform not in ["github", "gitlab"]:
        raise HTTPException(status_code=400, detail="Unsupported platform.")

    gitlab_project_id = None
    if detected_platform == "gitlab":
        gitlab_project_id = await _get_gitlab_proj_id(full_name)

    repo = Repository(
        full_name=full_name,
        platform=detected_platform,
        gitlab_project_id=gitlab_project_id,
        default_branch=default_branch,
        url=repo_url,
        user_id=user_id
    )

    try:
        db.add(repo)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Repository URL already exists")
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

    # ── Fire-and-forget: fetch repo context in background ─────────────────
    token = await _resolve_token(user_id=user_id, platform=detected_platform, db=db)
    if token:
        asyncio.create_task(
            _fetch_and_save_repo_context(
                repo_id=repo.id,
                repo_url=repo_url,
                platform=detected_platform,
                token=token,
            )
        )
    else:
        logger.warning("No token for user_id=%s platform=%s — skipping context fetch.", user_id, detected_platform)

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


async def _fetch_and_save_repo_context(repo_id: int, repo_url: str, platform: str, token: str):
    """Background task — opens its own DB session."""
    from database.db_engine import async_session

    try:
        if platform == "github":
            from agent.github_agent import run_github_agent
            pkg = await run_in_threadpool(run_github_agent, repo_url=repo_url, github_token=token)
        else:
            from agent.gitlab_agent import run_gitlab_agent
            pkg = await run_in_threadpool(run_gitlab_agent, repo_url=repo_url, gitlab_token=token)
    except Exception as exc:
        logger.error("Agent failed for repo_id=%s: %s", repo_id, exc, exc_info=True)
        return

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
        repo.full_name, detected_platform = _parse_repo_info(repo.url)
        repo.default_branch = _parse_branch(repo.url) or "main"
        if detected_platform not in ["github", "gitlab"]:
            raise HTTPException(status_code=400, detail="Unsupported platform.")
        repo.platform = detected_platform
        repo.gitlab_project_id = await _get_gitlab_proj_id(repo.full_name) if detected_platform == "gitlab" else None

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
    )