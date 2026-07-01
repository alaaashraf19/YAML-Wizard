from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Platform(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"


class RepositorySchema(BaseModel):

    id: int
    full_name: str

    platform: str = "github"
    gitlab_project_id: Optional[int] = None

    default_branch: str = "main"
    url: str

    class Config:
        from_attributes = True