from __future__ import annotations

import asyncio
import time
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.pipeline_model import Pipeline
from models.platforms_model import GitLabConnection
from models.project_model import Project
from models.repository_model import Repository
from schemas.dry_run_schema import DryRunJob, DryRunResponse
from services.platform_connectors.gitlab_connect import GitLabConnector
from .base import DryRunError, DryRunInProgress

GITLAB_API = "https://gitlab.com/api/v4"

# pipeline statuses that mean the run is over
TERMINAL = {"success", "failed", "canceled", "skipped", "manual"}
POLL_INTERVAL_SEC = 3
POLL_TIMEOUT_SEC = 300
HTTP_TIMEOUT = 30.0

#blocks duplicate concurrent dry runs of the same pipeline
active_pipelines: set[int] = set()
active_lock = asyncio.Lock()


class GitLabDryRunner:
    async def run(self, pipeline_id: int, project_id: int, user_id: int, db: AsyncSession) -> DryRunResponse:
        # reject a second run for the same pipeline while one is already active (refreshing mid runs)
        async with active_lock:
            if pipeline_id in active_pipelines:
                raise DryRunInProgress("A dry run is already in progress for this pipeline.")
            active_pipelines.add(pipeline_id)
        try:
            return await self.execute(pipeline_id, project_id, user_id, db)
        finally:
            async with active_lock:
                active_pipelines.discard(pipeline_id)

    async def execute(self, pipeline_id: int, project_id: int, user_id: int, db: AsyncSession) -> DryRunResponse:
        pipeline, repo = await self.load_info(pipeline_id, project_id, user_id, db)
        gl_project_id = repo.gitlab_project_id
        if not gl_project_id:
            raise DryRunError("Repository has no gitlab_project_id; cannot run a GitLab dry run.")

        token = await self.get_token(user_id, db)
        ref = repo.default_branch or "main" #the branch/tag name a pipeline runs against
        path = (pipeline.path or ".gitlab-ci.yml").lstrip("/")
        temp_branch = f"yaml-wizard/dry-run-{pipeline_id}"

        headers = {"Authorization": f"Bearer {token}"}
        ext_pipeline_id: int | None = None
        branch_created = False
        response: DryRunResponse | None = None
        async with httpx.AsyncClient(base_url=GITLAB_API, headers=headers, timeout=HTTP_TIMEOUT) as client:
            try:
                await self.create_branch(client, gl_project_id, temp_branch, ref)
                branch_created = True
                await self.commit_file(client, gl_project_id, temp_branch, path, pipeline.content)
                gl = await self.trigger(client, gl_project_id, temp_branch)
                ext_pipeline_id = gl["id"] #The real GitLab pipeline ID returned when a run is triggered
                final = await self.poll(client, gl_project_id, ext_pipeline_id)
                jobs = await self.jobs_results(client, gl_project_id, ext_pipeline_id)
                status = final.get("status", "unknown")
                response = DryRunResponse(
                    pipeline_id=pipeline.id,
                    platform="gitlab",
                    status=status,
                    valid=status == "success",
                    external_pipeline_id=ext_pipeline_id,
                    ref=temp_branch,
                    web_url=final.get("web_url"),
                    duration_s=final.get("duration"),
                    jobs=jobs,
                    cleaned_up=False,
                    message=f"Dry run finished with status '{status}'",
                )
            finally:
                cleaned = await self.cleanup(client, gl_project_id, ext_pipeline_id, temp_branch, branch_created)
                if response is not None:
                    response.cleaned_up = cleaned
        return response

    async def load_info(self, pipeline_id, project_id, user_id, db) -> tuple[Pipeline, Repository]:
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
            raise DryRunError("Pipeline not found for this user/project.")
        pipeline, repo = row
        if (repo.platform or "").lower() != "gitlab":
            raise DryRunError("Pipeline is not a GitLab pipeline.")
        return pipeline, repo

    async def get_token(self, user_id, db) -> str:
        result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user_id))
        connection = result.scalar_one_or_none()
        if not connection:
            raise DryRunError("No connected GitLab account for this user.")
        token = await GitLabConnector().get_valid_token(connection, db)
        if not token:
            raise DryRunError("Could not obtain a valid GitLab token.")
        return token

    #gitlab api
    async def create_branch(self, client, pid, branch, ref) -> None:
        resp = await client.post(
            f"/projects/{pid}/repository/branches",
            params={"branch": branch, "ref": ref},
        )
        # delete a leftover branch from a previously crashed run.
        if resp.status_code == 400 and "already exists" in resp.text.lower():
            await client.delete(f"/projects/{pid}/repository/branches/{quote(branch, safe='')}")
            resp = await client.post(
                f"/projects/{pid}/repository/branches",
                params={"branch": branch, "ref": ref},
            )
        if resp.status_code >= 400:
            raise DryRunError(f"create branch failed: HTTP {resp.status_code} {resp.text[:200]}")

    async def commit_file(self, client, pid, branch, path, content) -> None:
        encoded = quote(path, safe="") #URL-encodes the entire path, including slashes. GitLab's Files API requires the file path as a single encoded URL segment, safe=""  means escape everything, even  / .
        payload = {"branch": branch, "content": content, "commit_message": "ci: yaml-wizard dry run"}
        get = await client.get(f"/projects/{pid}/repository/files/{encoded}", params={"ref": branch})
        method = client.put if get.status_code == 200 else client.post
        resp = await method(f"/projects/{pid}/repository/files/{encoded}", json=payload)
        if resp.status_code >= 400:
            raise DryRunError(f"commit file failed: HTTP {resp.status_code} {resp.text[:200]}")

    async def trigger(self, client, pid, ref) -> dict:
        resp = await client.post(f"/projects/{pid}/pipeline", json={"ref": ref})
        if resp.status_code >= 400:
            raise DryRunError(f"trigger pipeline failed: HTTP {resp.status_code} {resp.text[:200]}")
        return resp.json()

    async def poll(self, client, pid, ext_id) -> dict:
        deadline = time.monotonic() + POLL_TIMEOUT_SEC
        last: dict = {"status": "unknown"}
        while time.monotonic() < deadline:
            resp = await client.get(f"/projects/{pid}/pipelines/{ext_id}")
            if resp.status_code < 400:
                last = resp.json()
                if last.get("status") in TERMINAL:
                    return last
            await asyncio.sleep(POLL_INTERVAL_SEC)
        last.setdefault("status", "running")
        return last

    async def jobs_results(self, client, pid, ext_id) -> list[DryRunJob]:
        resp = await client.get(f"/projects/{pid}/pipelines/{ext_id}/jobs", params={"per_page": 100})
        if resp.status_code >= 400:
            return []
        return [
            DryRunJob(
                name=j.get("name", "unknown"),
                stage=j.get("stage"),
                status=j.get("status", "unknown"),
                duration_s=j.get("duration"),
                allow_failure=j.get("allow_failure", False),
                web_url=j.get("web_url"),
            )
            for j in resp.json()
        ]

    async def cleanup(self, client, pid, ext_id, branch, branch_created) -> bool:
        ok = True
        if ext_id:
            try:
                await client.delete(f"/projects/{pid}/pipelines/{ext_id}")
            except httpx.HTTPError:
                ok = False
        if branch_created:
            try:
                await client.delete(f"/projects/{pid}/repository/branches/{quote(branch, safe='')}")
            except httpx.HTTPError:
                ok = False
        return ok
