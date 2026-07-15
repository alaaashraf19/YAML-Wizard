from pydantic import BaseModel

from schemas.dashboard import RepoCreate
from schemas.context_package import ContextPackage


class BenchmarkContext(BaseModel):
    repo: RepoCreate
    repo_context: ContextPackage