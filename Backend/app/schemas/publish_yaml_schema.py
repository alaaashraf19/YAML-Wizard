from pydantic import BaseModel

class PublishResult(BaseModel):
    """Result of publishing a YAML file to a remote repository."""
    success: bool
    message: str
    url: str | None = None  # link to the committed file or PR



class PublishRequest(BaseModel):
    filepath: str | None = None  
    commit_message: str | None = None
    create_pr: bool = True
    pr_branch: str | None
