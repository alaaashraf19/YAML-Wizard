from __future__ import annotations
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db_engine import get_db
from models.repo_model import RepoContext as RepoContextModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


class FetchContextRequest(BaseModel):
    prompt:   str = Field(examples=["Create a GitHub Actions CI/CD pipeline for this Python FastAPI app."])
    repo_url: str = Field(examples=["https://github.com/tiangolo/fastapi"])
    model:    str = Field(default="qwen2.5:3b")


class FetchContextResponse(BaseModel):
    id:                  int
    url:                 str
    languages:           list[str]
    frameworks:          list[str]
    build_tools:         list[str]
    test_runners:        list[str]
    has_docker:          bool
    has_existing_ci:     bool
    has_test_reports:    bool
    report_formats:      list[str]
    key_files:           dict[str, str]
    directory_tree:      str
    notes:               str


@router.post("/fetch-context", response_model=FetchContextResponse)
def fetch_context(body: FetchContextRequest, db: Session = Depends(get_db)):
    github_token = os.getenv("GITHUB_TOKEN", "")

    # 1. run agent
    try:
        from agent.repo_context_agent import run_repo_context_agent
        pkg = run_repo_context_agent(
            user_prompt=body.prompt,
            repo_url=body.repo_url,
            github_token=github_token,
            model=body.model,
        )
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    # 2. parse platform from URL
    from schemas.repo_schema import Platform
    platform = Platform.GITHUB if "github.com" in body.repo_url else Platform.GITLAB
    # 3. save to DB
    try:
        record = RepoContextModel(
            url                 = body.repo_url,
            platform            = platform,
            default_branch      = "main",
            languages           = pkg.languages,
            frameworks          = pkg.frameworks,
            build_tools         = pkg.build_tools,
            test_runners        = pkg.test_runners,
            has_docker          = pkg.has_docker,
            has_existing_ci     = pkg.has_existing_ci,
            existing_ci_content = pkg.existing_ci_content,
            has_test_reports    = pkg.has_test_reports,
            report_formats      = pkg.report_formats,
            key_files           = pkg.key_files,
            directory_tree      = pkg.directory_tree,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as exc:
        db.rollback()
        logger.error("DB error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    # 4. return
    return FetchContextResponse(
        id               = record.id,
        url              = record.url,
        languages        = record.languages or [],
        frameworks       = record.frameworks or [],
        build_tools      = record.build_tools or [],
        test_runners     = record.test_runners or [],
        has_docker       = record.has_docker,
        has_existing_ci  = record.has_existing_ci,
        has_test_reports = record.has_test_reports,
        report_formats   = record.report_formats or [],
        key_files        = record.key_files or {},
        directory_tree   = record.directory_tree or "",
        notes            = pkg.notes,
    )