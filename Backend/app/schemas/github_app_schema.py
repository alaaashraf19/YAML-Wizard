from pydantic import BaseModel, ConfigDict

class GitHubInstallationRepoSchema(BaseModel):
    repo_id: int
    repo_full_name: str
    repo_url: str
    model_config = ConfigDict(from_attributes=True)#bcz we use this class as a response model and we are fetching data from the database using sqlalchemy models which return objects with attributes not dicts, we need to tell pydantic to read data from attributes not dict keys