from models.project_model import Project
from models.repo_context_model import RepoContext
from models.repository_model import Repository
from schemas.context_package import ContextPackage
from schemas.project_schema import ProjectSchema
from schemas. repo_schema import RepositorySchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

class ContextResolverResponse(BaseModel):
    project: ProjectSchema
    repo: RepositorySchema
    repo_context: ContextPackage
    project_id: int
    repo_id: int


class ContextResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_context(self, project_id: int):
        
        project = await self.db.scalar(select(Project).where(Project.id == project_id))
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        repo = project.repository
        if not repo:
            raise ValueError(f"Repository not found for project {project_id}")
        
        repo_context = await self.db.scalar(select(RepoContext).where(RepoContext.repo_id == repo.id))

        return ContextResolverResponse(
            project=to_project_schema(project),
            repo=to_repository_schema(repo),
            repo_context=to_context_package(repo_context, repo),
        )
    

def to_project_schema(project: Project) -> ProjectSchema:
    return ProjectSchema(
        id=project.id,
        project_name=project.project_name,

        user_id=project.user_id,
        repo_id=project.repo_id,
    )

def to_repository_schema(repo: Repository) -> RepositorySchema:
    return RepositorySchema(
        id=repo.id,
        full_name=repo.full_name,

        platform=repo.platform,
        gitlab_project_id=repo.gitlab_project_id,

        default_branch=repo.default_branch,
        url=repo.url,
    )


def to_context_package(repo_context: RepoContext) -> ContextPackage:
    return ContextPackage(

        languages=repo_context.languages or [],
        frameworks=repo_context.frameworks or [],
        build_tools=repo_context.build_tools or [],

        has_docker=repo_context.has_docker,
        has_existing_ci=repo_context.has_existing_ci,
        existing_ci_content=repo_context.existing_ci_content,

        test_runners=repo_context.test_runners or [],
        test_runner_details=repo_context.test_runner_details or [],

        has_test_reports=repo_context.has_test_reports,
        report_formats=repo_context.report_formats or [],
        test_reports=repo_context.test_reports or [],

        test_commands=repo_context.test_commands or [],
        build_commands=repo_context.build_commands or [],

        env_vars=repo_context.env_vars or [],
        services=repo_context.services or [],

        directory_tree=repo_context.directory_tree or "",
        key_files=repo_context.key_files or {},

        notes="",
    )