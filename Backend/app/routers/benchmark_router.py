from fastapi import APIRouter

from evaluation.benchmark import run_benchmark
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db

from core.security import get_current_user
from models.user_model import User
from services.project_service import _resolve_token
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


@router.post("/run")
async def benchmark(
    model_name: str = "gemini-2.5-flash",
    user_prompt: str = "Set up a complete CI/CD pipeline with linting, testing, and building",
    current_user:User = Depends(get_current_user) ,db: AsyncSession = Depends(get_db)
):
    report = await run_benchmark(
        model_name=model_name,
        user_prompt=user_prompt,
    )

    return {
        "summary": report.summary(),
        "results": report.results,
    }