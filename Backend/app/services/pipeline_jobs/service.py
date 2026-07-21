from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.pipeline_model import Pipeline
from models.pipeline_version_model import PipelineVersion
from models.platforms_model import GitLabConnection, GitHubInstallation, GitHubInstallationRepo
from models.project_model import Project
from models.repository_model import Repository
from schemas.pipeline_jobs_schema import JobView, JobEdit
from .base import InvalidJobOrder, JobsNotFound
from .factory import get_pipeline_editor


#fetch the pipeline together with its repo platform
async def load_pipeline_with_platform(
    pipeline_id: int, project_id: int, user_id: int, db: AsyncSession) -> tuple[Pipeline, str]:
    result = await db.execute(
        select(Pipeline, Repository.platform)
        .join(Project, Pipeline.project_id == Project.id)
        .join(Repository, Project.repo_id == Repository.id)
        .where(Pipeline.id == pipeline_id, Project.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    pipeline, platform = row
    if pipeline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Pipeline not found in this project")
    return pipeline, platform


def editor_for(platform: str):
    try:
        return get_pipeline_editor(platform)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


async def list_pipeline_jobs(
    pipeline_id: int, project_id: int, user_id: int, db: AsyncSession
) -> tuple[str, list[JobView], str]:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)
    try:
        jobs = editor.list_jobs(pipeline.content)
    except JobsNotFound as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return platform, jobs, pipeline.content


#return every saved edit version of a pipeline
async def list_pipeline_versions(
    pipeline_id: int, project_id: int, user_id: int, db: AsyncSession
) -> tuple[str, list[PipelineVersion]]:
    _, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    result = await db.execute(
        select(PipelineVersion)
        .where(PipelineVersion.pipeline_id == pipeline_id)
        .order_by(PipelineVersion.id)
    )
    versions = result.scalars().all()
    return platform, list(versions)


#returns the jobs list and full YAML of a single saved edit version of a pipeline
async def list_pipeline_version_jobs(
    pipeline_id: int, project_id: int, version_id: int, user_id: int, db: AsyncSession
) -> tuple[str, PipelineVersion, list[JobView]]:
    _, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    version = await load_version_for_pipeline(pipeline_id, version_id, db)
    editor = editor_for(platform)
    try:
        jobs = editor.list_jobs(version.content)
    except JobsNotFound as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return platform, version, jobs


#delete one saved edit version of a pipeline
async def delete_pipeline_version(
    pipeline_id: int, project_id: int, version_id: int, user_id: int, db: AsyncSession
) -> dict:
    await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    result = await db.execute(
        select(PipelineVersion).where(
            PipelineVersion.id == version_id,
            PipelineVersion.pipeline_id == pipeline_id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found for this pipeline")

    name = version.name
    await db.delete(version)
    await db.commit()
    return {
        "pipeline_id": pipeline_id,
        "version_id": version_id,
        "name": name,
        "deleted": True,
        "message": f"Version '{name}' deleted",
    }



async def _assemble_and_validate(
    pipeline: Pipeline, platform: str, editor, job_edits: list[JobEdit],
    user_id: int, db: AsyncSession, project_id: int,
) -> tuple[str, dict]:
    #parse each submitted block. The block's top-level key is the job id, so renaming a job is just editing that key. id is only an optional label for error messages.
    parsed: list[tuple[str, object]] = []
    seen: set[str] = set()
    for index, edit in enumerate(job_edits):
        label = edit.id or f"#{index + 1}" #numbering the jobs in case of id is not set, the error shows job number instead of id
        try:
            key, spec = editor.parse_job_block(edit.content)
        except (InvalidJobOrder, JobsNotFound) as exc:
            raise HTTPException(status_code=400, detail=f"job {label}: {exc}")
        except Exception as exc:  # malformed YAML in the submitted block
            raise HTTPException(status_code=400, detail=f"job {label}: invalid YAML ({exc})")
        if not editor.is_valid_job_id(key):
            raise HTTPException(status_code=400, detail=f"'{key}' is not a valid job id for {platform}")
        if key in seen:
            raise HTTPException(status_code=400, detail=f"duplicate job id '{key}'")
        seen.add(key)
        parsed.append((key, spec))

    #assemble the new pipeline, preserving globals/formatting
    try:
        new_content = editor.assemble(pipeline.content, parsed)
    except (InvalidJobOrder, JobsNotFound) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    #validate the assembled pipeline through the agent's validation system
    report = await validate_assembled_pipeline(new_content, platform, user_id, db, project_id)
    return new_content, report


#return [] instead of raising, so a rejected pipeline can still send a response
def safe_list_jobs(editor, content: str) -> list[JobView]:
    try:
        return editor.list_jobs(content)
    except Exception:
        return []


async def review_pipeline_jobs(
    pipeline_id: int, project_id: int, user_id: int, job_edits: list[JobEdit], db: AsyncSession
) -> dict:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)

    new_content, report = await _assemble_and_validate(
        pipeline, platform, editor, job_edits, user_id, db, project_id
    )

    #if the linter says the assembled pipeline is invalid, return the errors without running AI review
    if not report.get("valid", False):
        return {
            "platform": platform,
            "jobs": safe_list_jobs(editor, new_content),
            "content": new_content,
            "valid": False,
            "errors": report.get("errors", []),
            "warnings": report.get("warnings", []),
            "report": report,
            "ai_warnings": [],
            "ai_review": {
                "available": False,
                "model": None,
                "error": "Skipped because pipeline validation failed",
            },
            "committed": False,
        }

    #ai review (it doesn't block any processes from happening, the edited code can still be submitted)
    from agent.pipeline_edit_ai_review import review_pipeline
    ai = await review_pipeline(new_content, platform)

    jobs = editor.list_jobs(new_content)
    return {
        "platform": platform,
        "jobs": jobs,
        "content": new_content,
        "valid": True,
        "warnings": report.get("warnings", []),
        "ai_warnings": ai.get("warnings", []),
        "ai_review": {
            "available": ai.get("available", False),
            "model": ai.get("model"),
            "error": ai.get("error"),
        },
        "committed": False,
    }

#save a freshly edited version in the versions table
async def save_pipeline_version(pipeline: Pipeline, content: str, db: AsyncSession) -> PipelineVersion:
    result = await db.execute(
        select(func.count())
        .select_from(PipelineVersion)
        .where(PipelineVersion.pipeline_id == pipeline.id)
    )
    edit_number = (result.scalar_one() or 0) + 1

    version = PipelineVersion(
        name=f"edit_{edit_number}_pipeline_{pipeline.name}",
        content=content,
        path=pipeline.path,
        branch=pipeline.branch,
        is_generated_by_wizard=False,
        description=pipeline.description,
        is_active=False, 
        commit_hash=None,
        commit_author=None,
        commit_message=None,
        committed_at=None,
        project_id=pipeline.project_id,
        pipeline_id=pipeline.id,
    )
    db.add(version)
    return version

#starting point of saving the edited version in the new table
async def commit_pipeline_jobs(
    pipeline_id: int, project_id: int, user_id: int, job_edits: list[JobEdit], db: AsyncSession
) -> dict:
    pipeline, platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    editor = editor_for(platform)

    new_content, report = await _assemble_and_validate(
        pipeline, platform, editor, job_edits, user_id, db, project_id
    )

    #if the linter says the assembled pipeline is invalid, return the errors and don't save version
    if not report.get("valid", False):
        return {
            "platform": platform,
            "jobs": safe_list_jobs(editor, new_content),
            "content": new_content,
            "valid": False,
            "errors": report.get("errors", []),
            "warnings": report.get("warnings", []),
            "report": report,
            "committed": False,
            "version": None,
            "version_id": None,
        }

    #keep the original pipeline and store the edit as a new numbered version
    version = None
    if new_content != pipeline.content:
        version = await save_pipeline_version(pipeline, new_content, db)
        await db.commit()
        await db.refresh(version)

    jobs = editor.list_jobs(new_content)
    return {
        "platform": platform,
        "jobs": jobs,
        "content": new_content,
        "valid": True,
        "warnings": report.get("warnings", []),
        "committed": True,
        "version": version.name if version is not None else None,
        "version_id": version.id if version is not None else None,
    }


async def validate_assembled_pipeline(content: str, platform: str, user_id: int, db: AsyncSession, project_id: int | None = None) -> dict:
    from agent.tools.validate_pipeline_tool import build_report

    target = (platform or "").lower()
    connection = None
    gitlab_project_id = None
    if target == "gitlab":
        result = await db.execute(
            select(GitLabConnection).where(GitLabConnection.user_id == user_id)
        )
        connection = result.scalar_one_or_none()
        if project_id is not None:
            repo_row = await db.execute(
                select(Repository.gitlab_project_id)
                .join(Project, Project.repo_id == Repository.id)
                .where(Project.id == project_id, Project.user_id == user_id)
            )
            gitlab_project_id = repo_row.scalar_one_or_none()
    return await build_report(content, target, connection=connection, db=db, project_id=gitlab_project_id)


#load a pipeline together with its repository (url/full_name/platform/installation), scoped to the user+project
async def load_pipeline_and_repo(
    pipeline_id: int, project_id: int, user_id: int, db: AsyncSession
) -> tuple[Pipeline, Repository]:
    result = await db.execute(
        select(Pipeline, Repository)
        .join(Project, Pipeline.project_id == Project.id)
        .join(Repository, Project.repo_id == Repository.id)
        .where(
            Pipeline.id == pipeline_id,
            Project.id == project_id,
            Project.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return row  # (pipeline, repo)


#resolve the GitHub App installation id for a repo: by the repo's full_name first, then any installation of the user
async def github_installation_id(repo: Repository, user_id: int, db: AsyncSession) -> int | None:
    by_repo = await db.execute(
        select(GitHubInstallationRepo.installation_id)
        .where(GitHubInstallationRepo.repo_url == repo.url)
    )
    installation_id = by_repo.scalars().first()
    if installation_id:
        return installation_id
    by_user = await db.execute(
        select(GitHubInstallation.installation_id).where(GitHubInstallation.user_id == user_id)
    )
    return by_user.scalars().first()


#get a write-capable token for the repo's platform (GitHub installation token / GitLab OAuth token)
async def resolve_publish_token(platform: str, repo: Repository, user_id: int, db: AsyncSession) -> str:
    if platform == "github":
        installation_id = await github_installation_id(repo, user_id, db)
        if installation_id is None:
            raise HTTPException(status_code=400, detail="No GitHub App installation found for this repository")
        from core.github_auth import get_installation_token
        try:
            return await asyncio.to_thread(get_installation_token, installation_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Could not obtain GitHub installation token: {exc}")

    if platform == "gitlab":
        from services.platform_connectors.gitlab_connect import GitLabConnector
        result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user_id))
        connection = result.scalar_one_or_none()
        if connection is None:
            raise HTTPException(status_code=400, detail="GitLab account not linked")
        return await GitLabConnector().get_valid_token(connection, db)

    raise HTTPException(status_code=422, detail=f"Unsupported platform for publishing: {platform!r}")


#load a version that must belong to the given pipeline (404 otherwise)
async def load_version_for_pipeline(pipeline_id: int, version_id: int, db: AsyncSession) -> PipelineVersion:
    result = await db.execute(
        select(PipelineVersion).where(
            PipelineVersion.id == version_id,
            PipelineVersion.pipeline_id == pipeline_id,
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found for this pipeline")
    return version


#push a version's YAML to the repo direct commit.
async def push_version_to_repo(
    pipeline: Pipeline, repo: Repository, version: PipelineVersion,
    user_id: int, db: AsyncSession, commit_message: str | None,
) -> tuple[object, str]:
    platform = (repo.platform or "").lower()
    from ..project_service import _resolve_token
    token, _ = await _resolve_token(user_id, platform, repo.url, db)
    if token is None:
        raise HTTPException(status_code=401, detail="No authentication token available.")
    # token = await resolve_publish_token(platform, repo, user_id, db)

    file_path = (pipeline.path or "").lstrip("/")
    branch = pipeline.branch or repo.default_branch or "main"
    message = commit_message or f"ci: publish {version.name} via YAML Wizard"

    from ..repo_publish_service import publish_to_repo_tool
    result = publish_to_repo_tool(
        yaml_content=version.content,
        repo_url=repo.url,
        platform=platform,
        token=token,
        file_path=file_path,
        branch=branch,
        commit_message=message,
        create_pr=False,
    )
    return result, message


#fields carried between the pipelines row and a version row on a swap. id, name, pipeline_id, project_id and updated_at are intentionally not swapped.
SWAPPED_VERSION_FIELDS = (
    "name", "content", "path", "branch", "is_generated_by_wizard", "description",
    "is_active", "commit_hash", "commit_author", "commit_message",
    "committed_at", "created_at",
)


#swap a version in as the main pipeline: the version's state moves into the pipelines row and the old main moves back into the version row.
def swap_version_into_pipeline(pipeline: Pipeline, version: PipelineVersion) -> None:
    for field in SWAPPED_VERSION_FIELDS:
        pipeline_value = getattr(pipeline, field)
        setattr(pipeline, field, getattr(version, field))
        setattr(version, field, pipeline_value)
    pipeline.updated_at = datetime.utcnow()


#push a saved edit version's YAML to the repo, then approve it and make sure there is one active version for the pipeline
async def push_pipeline_version(
    pipeline_id: int, project_id: int, version_id: int, user_id: int, db: AsyncSession,
    commit_message: str | None = None,
) -> dict:
    pipeline, repo = await load_pipeline_and_repo(pipeline_id, project_id, user_id, db)
    version = await load_version_for_pipeline(pipeline_id, version_id, db)

    result, message = await push_version_to_repo(pipeline, repo, version, user_id, db, commit_message)

    if not getattr(result, "success", False):
        raise HTTPException(status_code=502, detail=f"Publish failed: {getattr(result, 'message', 'unknown error')}")

    #if the push succeeded we approve it, swap the pushed version into the pipelines row and old main into the version row
    #I didn't use approve because of redundant db queries
    swap_version_into_pipeline(pipeline, version)

    #the pipelines row now holds the pushed content and is the single live/active one
    now = datetime.utcnow()
    pipeline.is_active = True
    pipeline.commit_message = message
    pipeline.committed_at = now
    pipeline.commit_hash = None
    pipeline.commit_author = None
    version.is_active = False  # the demoted old main (now in the version row) is not active

    #enforce exactly one active version per pipeline across both tables, deactivate every other version
    await db.execute(
        update(PipelineVersion)
        .where(
            PipelineVersion.pipeline_id == pipeline_id,
            PipelineVersion.id != version_id,
        )
        .values(is_active=False)
        .execution_options(synchronize_session=False)
    )

    await db.commit()
    await db.refresh(pipeline)
    await db.refresh(version)

    return {
        "pipeline_id": pipeline_id,
        "version_id": version_id,
        "platform": (repo.platform or "").lower(),
        "pushed": True,
        "message": result.message,
        "url": result.url,
    }


#approve a saved edit version. swap it in as the main pipeline (old main goes to version row). No repo push.
async def approve_pipeline_version(
    pipeline_id: int, project_id: int, version_id: int, user_id: int, db: AsyncSession,
) -> dict:
    pipeline, _platform = await load_pipeline_with_platform(pipeline_id, project_id, user_id, db)
    version = await load_version_for_pipeline(pipeline_id, version_id, db)

    swap_version_into_pipeline(pipeline, version)

    await db.commit()
    await db.refresh(pipeline)
    await db.refresh(version)

    return {
        "pipeline_id": pipeline_id,
        "version_id": version_id,
        "approved": True,
        "message": f"Version '{version.name}' approved as the main pipeline",
        "pipeline_content": pipeline.content,
        "version_content": version.content,
    }
