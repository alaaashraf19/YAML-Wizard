from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import yaml


class PipelineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    path: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    content: str
    is_generated_by_wizard: bool = True

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    path: Optional[str] = Field(None, min_length=1)
    branch: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = None

class PipelineResponse(PipelineBase):
    id: int
    is_active: bool = False
    activated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    project_id: int

    class Config:
        from_attributes = True


class PipelineSummary(BaseModel):
    id: int
    name: str
    path: str
    branch: str
    is_active: bool = False
    created_at: datetime

    class Config:
        from_attributes = True