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
    lines = []

    # 1. Core Stack
    lines.append(f"### CORE STACK")
    lines.append(f"- Languages: {', '.join(ctx.languages) or 'Unknown'}")
    lines.append(f"- Frameworks: {', '.join(ctx.frameworks) or 'None'}")
    lines.append(f"- Build Tools: {', '.join(ctx.build_tools) or 'None'}")

    # 2. Commands (Critical for YAML)
    lines.append(f"\n### COMMANDS")
    if ctx.build_commands: lines.append(f"- Build: {', '.join(ctx.build_commands)}")
    if ctx.test_commands: lines.append(f"- Test: {', '.join(ctx.test_commands)}")
    if ctx.env_vars: lines.append(f"- Env: {', '.join(ctx.env_vars)}")

    # 3. Existing CI (Redundancy Check)
    if ctx.has_existing_ci and ctx.existing_ci_content:
        # Only include if it's short; if it's long, the LLM will see it in active_pipeline_msg anyway
        ci_snippet = ctx.existing_ci_content[:500].strip()
        lines.append(f"\n### EXISTING CI SNIPPET\n```yaml\n{ci_snippet}\n```")

    # 4. Directory Structure (Tightened)
    if ctx.directory_tree:
        # 800 chars is usually plenty for the root structure
        lines.append(f"\n### DIR TREE\n{ctx.directory_tree[:800]}")

    # 5. Key Configuration Files (Aggressively cleaned)
    if ctx.key_files:
        lines.append("\n### CONFIG FILES")
        count = 0
        for filename, content in ctx.key_files.items():
            if count >= 4: break # Limit to top 4 files
            if not content or content == "[empty]": continue
            
            # Skip massive or binary-adjacent files
            if any(x in filename.lower() for x in ["lock", "sum", "license", "xlsx", "csv"]):
                continue
            
            # Take only 400 chars and strip newlines to save vertical space/tokens
            snippet = content[:400].replace("\n", " ").strip()
            lines.append(f"- {filename}: {snippet}...")
            count += 1

    return "\n".join(lines)