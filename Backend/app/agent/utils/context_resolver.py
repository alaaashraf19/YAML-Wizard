from models.project_model import Project
from models.repo_context_model import RepoContext
from models.repository_model import Repository
from schemas.context_package import ContextPackage
from schemas.project_schema import ProjectSchema
from schemas. repo_schema import RepositorySchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from sqlalchemy.orm import joinedload

class ContextResolverResponse(BaseModel):
    project: ProjectSchema
    repo: RepositorySchema
    repo_context: ContextPackage
    project_id: int
    repo_id: int


class ContextResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_context(self, project_id: int) -> ContextResolverResponse:
        


        project = await self.db.scalar(
            select(Project)
            .options(
                joinedload(Project.repository)
                .joinedload(Repository.context)
            )
            .where(Project.id == project_id)
        )
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        repo = project.repository
        if not repo:
            raise ValueError(f"Repository not found for project {project_id}")
        
        repo_context = repo.context

        return ContextResolverResponse(
            project=to_project_schema(project),
            repo=to_repository_schema(repo),
            repo_context=to_context_package(repo_context),
            project_id=project.id,
            repo_id=repo.id,
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


def build_context_summary(ctx: ContextPackage) -> str:
    """
    Builds a token-efficient summary of the repository context.
    Prioritizes core stack info and truncates large blobs.
    """
    lines = []

    # 1. Core Stack - (High Priority, keep clear)
    lines.append(f"### CORE STACK")
    lines.append(f"- Languages: {', '.join(ctx.languages) if ctx.languages else 'Unknown'}")
    lines.append(f"- Frameworks: {', '.join(ctx.frameworks) if ctx.frameworks else 'None'}")
    lines.append(f"- Build Tools: {', '.join(ctx.build_tools) if ctx.build_tools else 'None'}")
    lines.append(f"- Default Branch: {ctx.default_branch}")

    # 2. Commands & Env - (High Priority for YAML accuracy)
    lines.append(f"\n### COMMANDS")
    lines.append(f"- Build: {', '.join(ctx.build_commands) if ctx.build_commands else 'None'}")
    lines.append(f"- Test: {', '.join(ctx.test_commands) if ctx.test_commands else 'None'}")
    lines.append(f"- Env Vars Needed: {', '.join(ctx.env_vars) if ctx.env_vars else 'None'}")
    
    if ctx.services:
        lines.append(f"- Required Services: {', '.join(ctx.services)}")

    # 3. Existing CI - (Medium Priority, heavily truncated)
    if ctx.has_existing_ci and ctx.existing_ci_content:
        # We only need the first 1000 chars to see the structure
        truncated_ci = ctx.existing_ci_content[:1000].strip()
        lines.append(f"\n### EXISTING CI (TRUNCATED)\n```yaml\n{truncated_ci}\n```")

    # 4. Directory Structure - (Aggressively truncated)
    if ctx.directory_tree:
        # The first 1000 chars usually cover the root and first-level folders
        lines.append(f"\n### DIRECTORY STRUCTURE (ROOT)\n{ctx.directory_tree[:1000]}")

    # 5. Key Configuration Files - (The "Token Killer", now optimized)
    if ctx.key_files:
        lines.append("\n### KEY FILE SNIPPETS")
        # We only look at the first 5 files to prevent overflow
        for i, (filename, content) in enumerate(ctx.key_files.items()):
            if i >= 5: break # Limit number of files
            
            if content and content != "[empty]":
                # We skip lock files as they are huge and useless for the LLM
                if any(ext in filename for ext in ["lock", "sum", "bin"]):
                    continue
                
                # Take only the first 600 characters of each config file
                # This is usually enough for package.json or requirements.txt
                snippet = content[:600].strip().replace("\n", " ")
                lines.append(f"- {filename}: {snippet}...")

    return "\n".join(lines)