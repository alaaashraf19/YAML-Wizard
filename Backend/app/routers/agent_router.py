"""
Agent Router — /agent/fetch-context

Supports both GitHub and GitLab repositories.
Detects platform from the URL and routes to the correct agent.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import get_current_user
from database.db_engine import get_db
from models.repo_context_model import RepoContext as RepoContextModel
from models.repository_model import Repository as RepositoryModel
from models.user_model import User as UserModel
from schemas.repo_schema import Platform

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class FetchContextRequest(BaseModel):
    repo_url:      str  = Field(examples=["https://github.com/tiangolo/fastapi"])
    github_token:  str  = Field(default="", description="Override GitHub token (optional)")
    gitlab_token:  str  = Field(default="", description="GitLab personal access token (optional)")


class FetchContextResponse(BaseModel):
    id:                  int
    url:                 str
    platform:            str
    default_branch:      str
    languages:           list[str]
    frameworks:          list[str]
    build_tools:         list[str]
    test_runners:        list[str]
    test_commands:       list[str]
    build_commands:      list[str]
    env_vars:            list[str]
    services:            list[str]
    has_docker:          bool
    has_existing_ci:     bool
    has_test_reports:    bool
    report_formats:      list[str]
    key_files:           dict[str, str]
    directory_tree:      str
    notes:               str


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/fetch-context", response_model=FetchContextResponse)
async def fetch_context(
    body: FetchContextRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    # ── Detect platform ───────────────────────────────────────────────────
    url_lower = body.repo_url.lower()
    if "gitlab.com" in url_lower:
        platform = Platform.GITLAB
    elif "github.com" in url_lower:
        platform = Platform.GITHUB
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="repo_url must be a github.com or gitlab.com URL.",
        )

    # ── Resolve tokens ────────────────────────────────────────────────────
    github_token = body.github_token or settings.github_token
    gitlab_token = body.gitlab_token or settings.gitlab_token

    if platform == Platform.GITHUB and not github_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub token is required. Set GITHUB_TOKEN in .env or pass github_token in the request.",
        )
    if platform == Platform.GITLAB and not gitlab_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitLab token is required. Set GITLAB_TOKEN in .env or pass gitlab_token in the request.",
        )

    # ── Run agent ─────────────────────────────────────────────────────────
    # run_github_agent / run_gitlab_agent are sync functions that internally
    # call asyncio.run() (for the MCP client). Calling them directly here
    # would crash with "asyncio.run() cannot be called from a running event
    # loop" since this route itself runs inside FastAPI's event loop.
    # run_in_threadpool executes them in a worker thread, which has no
    # running loop of its own, so their internal asyncio.run() works fine.
    try:
        if platform == Platform.GITHUB:
            from agent.github_agent import run_github_agent
            pkg = await run_in_threadpool(run_github_agent, repo_url=body.repo_url, github_token=github_token)
        else:
            from agent.gitlab_agent import run_gitlab_agent
            pkg = await run_in_threadpool(run_gitlab_agent, repo_url=body.repo_url, gitlab_token=gitlab_token)
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    # ── Persist to DB ─────────────────────────────────────────────────────
    # url/platform/default_branch live on Repository, not RepoContext.
    # RepoContext is linked to a Repository via repo_id (1-to-1).
    try:
        result = await db.execute(
            select(RepositoryModel).where(RepositoryModel.url == body.repo_url)
        )
        repository = result.scalar_one_or_none()

        if repository is None:
            repository = RepositoryModel(
                user_id=current_user.id,
                full_name=body.repo_url.rstrip("/").split("/")[-2:][0] + "/" + body.repo_url.rstrip("/").split("/")[-1],
                platform=platform.value,
                default_branch=pkg.default_branch,
                url=body.repo_url,
            )
            db.add(repository)
            await db.flush()  # assigns repository.id without committing yet
        else:
            repository.default_branch = pkg.default_branch

        result = await db.execute(
            select(RepoContextModel).where(RepoContextModel.repo_id == repository.id)
        )
        record = result.scalar_one_or_none()

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

        if record is None:
            record = RepoContextModel(repo_id=repository.id, **context_fields)
            db.add(record)
        else:
            for field_name, value in context_fields.items():
                setattr(record, field_name, value)

        await db.commit()
        await db.refresh(repository)
        await db.refresh(record)
    except Exception as exc:
        await db.rollback()
        logger.error("DB error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    # ── Return ────────────────────────────────────────────────────────────
    return FetchContextResponse(
        id               = record.id,
        url              = repository.url,
        platform         = repository.platform,
        default_branch   = repository.default_branch,
        languages        = record.languages        or [],
        frameworks       = record.frameworks       or [],
        build_tools      = record.build_tools      or [],
        test_runners     = record.test_runners     or [],
        test_commands    = record.test_commands    or [],
        build_commands   = record.build_commands   or [],
        env_vars         = record.env_vars         or [],
        services         = record.services         or [],
        has_docker       = record.has_docker,
        has_existing_ci  = record.has_existing_ci,
        has_test_reports = record.has_test_reports,
        report_formats   = record.report_formats   or [],
        key_files        = record.key_files        or {},
        directory_tree   = record.directory_tree   or "",
        notes            = pkg.notes,
    )