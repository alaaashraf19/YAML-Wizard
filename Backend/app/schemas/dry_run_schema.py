from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DryRunJob(BaseModel):
    name: str
    stage: str | None = None
    status: str
    duration_s: float | None = None
    allow_failure: bool = False
    web_url: str | None = None


class DryRunResponse(BaseModel):
    pipeline_id: int # our internal Pipeline.id
    platform: str
    status: str  # success, failed, error, canceled, skipped ...
    valid: bool  # True when the pipeline reached a successful terminal state
    external_pipeline_id: int | None = None   # GitLab pipeline id (the real triggered one)
    ref: str | None = None  # temp branch the dry run executed on
    web_url: str | None = None
    duration_s: float | None = None
    jobs: list[DryRunJob] = Field(default_factory=list)
    cleaned_up: bool = False
    message: str | None = None


class DryRunHistoryItem(BaseModel):
    id: int
    pipeline_id: int
    project_id: int
    platform: str
    status: str
    valid: bool
    external_pipeline_id: int | None = None
    ref: str | None = None
    web_url: str | None = None
    duration_s: float | None = None
    jobs: list[DryRunJob] = Field(default_factory=list)
    cleaned_up: bool = False
    message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
