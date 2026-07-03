from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent.finetuning.model_client import is_configured
from core.security import get_current_user
from database.db_engine import get_db
from models.user_model import User
from schemas.chatbot_schema import ChatMessage
from schemas.finetuned_schema import (
    GenerateRequest,
    GenerateResponse,
    ModelEngine,
    ModelsResponse,
)
from services.finetuned_generation_service import FinetunedGenerationService

router = APIRouter()

generation_service = FinetunedGenerationService()


#List the chat models the user can choose from.
@router.get("/models", response_model=ModelsResponse)
async def list_models(current_user: User = Depends(get_current_user)):
    return ModelsResponse(engines=[
        ModelEngine(id="agent", label="Agent (Gemini)", available=True),
        ModelEngine(id="finetuned", label="Finetuned (Qwen CI)", available=is_configured()),
    ])


#Single-shot CI/CD YAML generation via the finetuned model
@router.post("/generate", response_model=GenerateResponse)
async def generate_pipeline(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await generation_service.process(
        user_id=current_user.id,
        message=request.message,
        session_id=request.session_id,
        project_id=request.project_id,
        pipeline_id=request.pipeline_id,
        platform_override=request.platform,
        db=db,
    )
    return GenerateResponse(
        session_id=result["session_id"],
        session_name=result["session_name"],
        platform=result["platform"],
        valid=result["valid"],
        yaml=result["yaml"],
        message=ChatMessage(
            role="assistant",
            content=result["message_content"],
            timestamp=result["bot_timestamp"],
        ),
        report=result["report"],
        full_history=[
            ChatMessage(role=m["role"], content=m["content"], timestamp=m["timestamp"])
            for m in result["full_history"]
        ],
    )
