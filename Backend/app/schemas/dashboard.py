from typing import Optional

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from enum import Enum
# Repository 

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

class TestResult(BaseModel):
        test_name : str
        status : TestStatus
        duration_ms : Optional[int] = None
        error : Optional[str] = None
        source : str = "unknown"
        framework : str = "unknown"

