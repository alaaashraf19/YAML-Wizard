from pydantic import BaseModel, Field


class JobView(BaseModel):
    id: str
    display_index: int
    stage: str | None = None  #GitLab stage (None for GitHub)
    needs: list[str] = Field(default_factory=list)
    content: str | None = None  # the full job block (key + spec) as YAML


#One job in a full edit. The job's identity is the content block's top-level key
#id is an optionall and ignored except in errors.
class JobEdit(BaseModel):
    id: str | None = None
    content: str = Field(..., min_length=1)  # full job block (key + spec) its top-level key is the job id


#Full list of edited set of jobs, in order. jobs can be deleted, new jobs can be added.
class PipelineJobsEdit(BaseModel):
    jobs: list[JobEdit] = Field(..., min_length=1)


class JobOrderResponse(BaseModel):
    pipeline_id: int
    platform: str
    jobs: list[JobView]
    content: str | None = None  # full pipeline YAML
    warnings: list | None = None 