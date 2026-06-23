from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum

class RepoCreate(BaseModel):
    url: str
    platform: str | None = None
    default_branch: str = "main"


class RepoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    platform: str
    default_branch: str
    url: str
    last_synced_at: datetime | None
    created_at: datetime


##pipeline run

class PipelineRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repo_id: int
    external_id: int
    commit_hash: str
    commit_message: str | None
    branch: str | None
    status: str
    conclusion: str | None
    total_duration_s: int | None
    started_at: datetime | None
    completed_at: datetime | None
    compared_to_prev_pct: float | None
    created_at: datetime


class JobTimingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    external_id: int
    job_name: str
    status: str
    duration_s: int | None
    started_at: datetime | None
    completed_at: datetime | None
    compared_to_prev_pct: float | None


class TestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    test_name: str
    status: str
    duration_ms: int | None
    avg_duration_ms: float | None
    diff_from_avg_pct: float | None
    color: str
    created_at: datetime


class PipelineRunDetail(PipelineRunOut):
    """Run with nested jobs and tests."""
    jobs: list[JobTimingOut] = []
    tests: list[TestRunOut] = []



class TestHistoryPoint(BaseModel):
    commit_hash: str
    commit_message: str | None
    status: str
    duration_ms: int | None
    avg_duration_ms: float | None
    diff_from_avg_pct: float | None
    color: str
    timestamp: datetime | None
    
#  Sync 

class SyncStatus(BaseModel):
    repo_id: int
    runs_synced: int
    jobs_synced: int
    tests_parsed: int
    message: str

##tests per workflow run
class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"

# class TestResult(BaseModel):
#         test_name : str
#         status : str
#         duration_ms : Optional[int] = None
#         error : Optional[str] = None
#         source : str = "unknown"
#         framework : str = "unknown"

class Insight(BaseModel):
    level: str  # "warning", "info", "success", "error"
    icon: str  # emoji
    title: str
    detail: str
    commit_hash: str | None = None
    test_name: str | None = None



class TrendPoint(BaseModel):
    commit_hash: str
    timestamp: datetime | None
    total_duration_s: int | None
    status: str
    test_count: int = 0
    test_pass_count: int = 0
    test_fail_count: int = 0


class TestResult(BaseModel):
    test_name: str
    status: str

    duration_ms: Optional[int] = None
    error: Optional[str] = None

    source: str = "unknown"
    framework: str = "unknown"

    #hierarchy
    file: Optional[str] = None
    parent_test: Optional[str] = None
    is_subtest: Optional[bool] = None

    #aggregated/summaries
    is_aggregated: Optional[bool] = None
    passed_count: Optional[int] = None
    failed_count: Optional[int] = None
    skipped_count: Optional[int] = None
    total_count: Optional[int] = None


class RepositorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    full_name: str
    platform: str
    gitlab_project_id: int | None
    default_branch: str
    url: str
    last_synced_at: datetime | None = None
    created_at: datetime

class CollectorsRepositoryDetail(BaseModel):
    repo: RepositorySchema
    gitlab_project_id: int | None
    github_owner: str | None
    github_repo: str | None


class CIArtifact(BaseModel):
    id: str | None = None
    name: str | None = None
    download_url: str
    provider: str  # github | gitlab