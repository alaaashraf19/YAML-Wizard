from typing import Optional

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    project_name: str
    repo_url: str
    target_platform: str

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    repo_url: Optional[str] = None
    target_platform: Optional[str] = None
class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    user_id: int
    class Config:
        from_attributes =True
