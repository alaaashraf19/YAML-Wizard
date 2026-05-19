from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ProjectInfo(BaseModel):
    id:int
    name: str
    target_platform: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatSessionResponse(BaseModel):
    id: int
    session_name: str
    created_at: datetime
    updated_at: datetime
    project_id: Optional[int] = None
    project: Optional[ProjectInfo] = None

class ChatSessionDetailResponse(BaseModel):
    id:int
    session_name: str
    messages: List[ChatMessage]
    project_id: Optional[int] = None
    project: Optional[ProjectInfo] = None
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    project_id: Optional[int] = None

class ChatResponse(BaseModel):
    session_id: Optional[int] = None
    message: ChatMessage
    full_history: List[ChatMessage]