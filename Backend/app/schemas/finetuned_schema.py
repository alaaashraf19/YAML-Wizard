from typing import List, Optional

from pydantic import BaseModel

from schemas.chatbot_schema import ChatMessage


class GenerateRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    project_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    platform: Optional[str] = None


class GenerateResponse(BaseModel):
    session_id: Optional[int] = None
    session_name: str
    platform: str
    valid: bool
    yaml: str  # the generated YAML
    message: ChatMessage  # assistant message (content == the YAML)
    report: Optional[dict] = None # validation report (errors / warnings)
    full_history: List[ChatMessage]


class ModelEngine(BaseModel):
    id: str  # "agent" or "finetuned"
    label: str
    available: bool


class ModelsResponse(BaseModel):
    engines: List[ModelEngine]
