from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ProjectBase(BaseModel):
    project_name: str
    url: str

class ProjectCreate(ProjectBase):
    install_id: int | None = None
    github_repo_id: int | None = None
    pass

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    repo_url: Optional[str] = None

class ProjectSchema(BaseModel):
    id: int
    user_id: int
    project_name: str
    repo_id: int

class ProjectSessionResponse(ProjectSchema):
    created_at: datetime
    updated_at: datetime
    
class ProjectResponse(ProjectSessionResponse):
    platform: str
    repo_url: str
    branch : str
    class Config:
        from_attributes =True

class ProjectSession(BaseModel):
    id: int
    session_name: str
    updated_at: datetime
