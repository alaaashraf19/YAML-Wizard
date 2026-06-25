from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ProjectBase(BaseModel):
    project_name: str
    url: str

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    repo_url: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    project_name: str
    repo_id: int
    platform: str
    repo_url: str
    class Config:
        from_attributes =True
