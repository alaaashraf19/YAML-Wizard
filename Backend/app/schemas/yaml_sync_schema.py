from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class YamlSyncResult(BaseModel):
    """Result of a YAML sync operation for one repository."""
    model_config = ConfigDict(from_attributes=True)

    repo_id: int
    repo_name: str
    platform: str
    files_found: int = 0
    files_synced: int = 0          # newly created pipelines
    files_updated: int = 0         # updated existing pipelines
    errors: list[str] = []
    success: bool = True
    message: str = ""


class PipelineSyncResult(BaseModel):
    """Result of syncing a single pipeline."""
    pipeline_id: int
    project_id: int
    name: str
    path: str
    branch: str
    is_active: bool
    commit_hash: Optional[str] = None
    commit_author: Optional[str] = None
    commit_message: Optional[str] = None
    committed_at: Optional[datetime] = None
    success: bool
    message: str