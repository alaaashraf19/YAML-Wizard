from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PipelineBase(BaseModel):
    name: Optional[str] = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    path: Optional[str] = Field(None, min_length=1)
    branch: str = Field(..., min_length=1)
    content: str
    is_generated_by_wizard: bool = True


class PipelineCreate(PipelineBase):
    is_active: bool = False
    committed_at: Optional[datetime] = None


class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    path: Optional[str] = Field(None, min_length=1)
    branch: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = None
    is_active: Optional[bool] = None


class PipelineResponse(PipelineBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    project_id: int
    # Commit info
    commit_hash: Optional[str] = None
    commit_author: Optional[str] = None
    commit_message: Optional[str] = None
    committed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PipelineSummary(BaseModel):
    id: int
    name: str
    path: str
    branch: str
    is_active: bool
    created_at: datetime
    commit_hash: Optional[str] = None
    commit_author: Optional[str] = None

    class Config:
        from_attributes = True