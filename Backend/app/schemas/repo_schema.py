from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Platform(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"


class RepoContext(BaseModel):
    """Extracted context from a repository."""
    url: str
    platform: Platform
    default_branch: str = "main"
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    test_runners: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    build_commands: list[str] = Field(default_factory=list)
    env_vars: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    has_docker: bool = False
    has_existing_ci: bool = False
    existing_ci_content: Optional[str] = None
    directory_tree: str = ""
    key_files: dict[str, str] = Field(default_factory=dict)
