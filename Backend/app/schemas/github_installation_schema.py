from pydantic import BaseModel

class GitHubInstallation(BaseModel):
    installation_id: int
    account_login: str
    account_id: int
