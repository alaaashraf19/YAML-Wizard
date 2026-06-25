from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from schemas.chatbot_schema import (
    ChatRequest, ChatResponse, ChatSessionResponse,
    ChatSessionDetailResponse, ChatMessage
)
from schemas.project_schema import ProjectResponse
from services.chatbot_service import ChatbotService
from database.db_engine import get_db
from core.security import get_current_user
from models.user_model import User
from models.repository_model import Repository

router = APIRouter()

chatbot_service = ChatbotService()


@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
        request: ChatRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    result = await chatbot_service.process_chat_message(
        user_id=current_user.id,
        message=request.message,
        session_id=request.session_id,
        project_id = request.project_id,
        db=db
    )

    return ChatResponse(
        session_id=result["session_id"],
        session_name=result["session_name"],
        message=ChatMessage(
            role="assistant",
            content=result["bot_response"],
            timestamp=result["bot_timestamp"]
        ),
        full_history=[
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in result["full_history"]
        ]
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    sessions = await chatbot_service.get_user_sessions(
        user_id=current_user.id,
        db=db
    )
    return [
        ChatSessionResponse(
            id=session.id,
            session_name=session.session_name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            project_id=session.project_id,
            project= {
                "id" : session.project_id,
                "project_name" : session.project.project_name,
                "user_id" :  current_user.id,
                "repo_id" : session.project.repo_id,
                "created_at": session.project.created_at,
                "updated_at": session.project.updated_at
            } if session.project else None,
        )
        for session in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_details(
        session_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    session_data = await chatbot_service.get_session_with_messages(
        user_id=current_user.id,
        session_id=session_id,
        db=db
    )

    return ChatSessionDetailResponse(
        id=session_data["session_id"],
        session_name=session_data["session_name"],
        project_id=session_data["project_id"],
        project=session_data["project"],
        messages=[
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"]
            )
            for msg in session_data["messages"]
        ]
    )

@router.delete("/sessions/{session_id}")
async def delete_session(
        session_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    await chatbot_service.delete_session(
        user_id=current_user.id,
        session_id=session_id,
        db=db
    )

    return {"message": "Session deleted successfully"}

@router.post("/sessions/{session_id}/projects/{project_id}", response_model=ProjectResponse)
async def link_session_to_project(
        session_id: int,
        project_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    project = await chatbot_service.link_session_to_project(user_id=current_user.id,session_id=session_id, project_id=project_id, db=db)
    return ProjectResponse(
        id=project.id,
        user_id=current_user.id,
        project_name=project.project_name,
        repo_id=project.repo_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        platform = project.platform,
        repo_url=project.repo_url,
        
    )