from datetime import datetime
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
    valid: bool = True  # False when the linter/semantic validation failed
    errors: list | None = None  # linter errors
    report: dict | None = None  # full validation report 
    warnings: list | None = None  # linter warnings (actionlint / gitlab-ci-lint / json-schema)
    ai_warnings: list | None = None  # advisory warnings from ai
    ai_review: dict | None = None  # ai review process status: {available, model, error}
    committed: bool = False  # True only after the change has been saved to the db
    version: str | None = None  # name of the saved pipeline version (edit_x_pipeline_y)
    version_id: int | None = None  # id of the saved pipeline version, if one was created


#one saved edit for a pipeline
class PipelineVersionView(BaseModel):
    id: int
    pipeline_id: int
    project_id: int
    name: str
    content: str  
    path: str
    branch: str
    description: str | None = None
    is_generated_by_wizard: bool
    is_active: bool
    commit_hash: str | None = None
    commit_author: str | None = None
    commit_message: str | None = None
    committed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


#All edit versions of a single pipeline, oldest first
class PipelineVersionsResponse(BaseModel):
    pipeline_id: int
    platform: str
    count: int
    versions: list[PipelineVersionView]


#Jobs list and full YAML of a single saved edit version
class VersionJobsResponse(BaseModel):
    pipeline_id: int
    version_id: int
    name: str
    platform: str
    jobs: list[JobView]
    content: str | None = None  # full YAML of this version


#Optional body for publishing a version (custom commit message)
class PublishVersionRequest(BaseModel):
    commit_message: str | None = None


#Result of pushing a version's YAML to the repo
class PushVersionResponse(BaseModel):
    pipeline_id: int
    version_id: int
    platform: str
    pushed: bool  # whether the push to the repo succeeded
    message: str  # message from the publish tool
    url: str | None = None  # link to the committed file


#Result of approving a version
class ApproveVersionResponse(BaseModel):
    pipeline_id: int
    version_id: int
    approved: bool
    message: str
    pipeline_content: str  #the approved edit
    version_content: str  # the former main


#Result of deleting a single edit version
class DeleteVersionResponse(BaseModel):
    pipeline_id: int
    version_id: int
    name: str
    deleted: bool
    message: str