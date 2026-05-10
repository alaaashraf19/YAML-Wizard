from pydantic import BaseModel, ConfigDict
from datetime import datetime

# ── Repository ──────────────────────────────────────────────────────────────

class RepoCreate(BaseModel):
    url: str
    platform: str | None = None  # auto-detected if omitted
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