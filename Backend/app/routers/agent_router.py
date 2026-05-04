from __future__ import annotations
import logging
import os

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


class FetchContextRequest(BaseModel):
    prompt: str = Field(examples=["Create a GitHub Actions CI/CD pipeline for this Python FastAPI app."])
    repo_url: str = Field(examples=["https://github.com/tiangolo/fastapi"])
    model: str = Field(default="qwen2.5:3b")


@router.post("/fetch-context")
def fetch_context(body: FetchContextRequest):
    github_token = os.getenv("GITHUB_TOKEN", "")
    try:
        from agent.repo_context_agent import run_repo_context_agent
        package = run_repo_context_agent(
            user_prompt=body.prompt,
            repo_url=body.repo_url,
            github_token=github_token,
            model=body.model,
        )
        return package.model_dump()
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))