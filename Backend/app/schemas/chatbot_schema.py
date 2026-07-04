from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from schemas.project_schema import ProjectResponse
class ProjectInfo(BaseModel):
    id:int
    name: str

class PipelineInfo(BaseModel):
    id: int
    name: str
    content: str
    path: str
    branch: str
    is_generated_by_wizard: bool
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    committed_at: Optional[datetime] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatSessionResponse(BaseModel):
    id: int
    session_name: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessage]] = None
    project_id: Optional[int] = None
    project: Optional[ProjectResponse] = None
    pipeline: Optional[PipelineInfo] = None


class ChatSessionDetailResponse(BaseModel):
    id:int
    session_name: str
    messages: List[ChatMessage]
    project_id: Optional[int] = None
    project: Optional[ProjectInfo] = None
    pipeline: Optional[PipelineInfo] = None
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    project_id: Optional[int] = None
    pipeline_id: Optional[int] = None

class ChatResponse(BaseModel):
    session_id: Optional[int] = None
    session_name: str
    message: ChatMessage
    full_history: List[ChatMessage]


# ---- Guest (unauthenticated) chat ----
# Guests have no account, no persisted session, and no linked project/pipeline,
# so the request/response shapes are intentionally minimal: the frontend keeps
# the conversation in memory and resends it as `chat_history` each turn.
class GuestChatRequest(BaseModel):
    message: str
    chat_history: List[ChatMessage] = []


class GuestChatResponse(BaseModel):
    message: ChatMessage