from pydantic import BaseModel, Field


class JobView(BaseModel):
    id: str
    display_index: int
    stage: str | None = None  #GitLab stage (None for GitHub)
    needs: list[str] = Field(default_factory=list)
    content: str | None = None  # the full job block (key + spec) as YAML


#Desired final order of job ids
class JobOrderUpdate(BaseModel):
    order: list[str] = Field(..., min_length=1)


class JobOrderResponse(BaseModel):
    pipeline_id: int
    platform: str
    jobs: list[JobView]
    content: str | None = None  # full pipeline YAML