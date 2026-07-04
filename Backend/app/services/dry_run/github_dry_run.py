#Install Docker Desktop
#docker pull catthehacker/ubuntu:act-latest
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import time

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.github_auth import get_installation_token
from models.pipeline_model import Pipeline
from models.platforms_model import GitHubInstallation, GitHubInstallationRepo
from models.project_model import Project
from models.repository_model import Repository
from schemas.dry_run_schema import DryRunJob, DryRunResponse
from .base import DryRunError, DryRunInProgress


ACT_BINARY = os.getenv("ACT_BINARY", "act") #path of the  act  executable
ACT_IMAGE = os.getenv("ACT_DEFAULT_IMAGE", "catthehacker/ubuntu:act-latest") #The Docker image  act  uses to emulate an Ubuntu runner
ACT_EVENT = os.getenv("ACT_EVENT", "push") #default event to simulate when the workflow's triggers can't be determined
ACT_ARCH = os.getenv("ACT_CONTAINER_ARCH", "")  # e.g. "linux/amd64" on Apple silicon
ACT_TIMEOUT_SEC = int(os.getenv("ACT_TIMEOUT_SEC", "600"))
CLONE_TIMEOUT_SEC = int(os.getenv("DRY_RUN_CLONE_TIMEOUT_SEC", "120"))
DOCKER_INFO_TIMEOUT_SEC = 15
GIT_BINARY = "git"

# failure act results that should mark a job as failed
FAIL_RESULTS = {"failure", "failed", "cancelled", "canceled"}

# blocks duplicate concurrent dry runs of the same pipeline
active_pipelines: set[int] = set()
active_lock = asyncio.Lock()


class GitHubDryRunner:
    async def run(self, pipeline_id: int, project_id: int, user_id: int, db: AsyncSession) -> DryRunResponse:
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
        owner, repo_name = self.owner_repo(repo)
        branch = repo.default_branch or "main"
        wf_path = (pipeline.path or ".github/workflows/ci.yml").lstrip("/")

        await self.precheck() #Fail fast Verify act and Docker are installed and the daemon is reachable before clone.
        token = await self.get_token(repo, user_id, db)

        workdir = tempfile.mkdtemp(prefix=f"ghdryrun-{pipeline_id}-")
        response: DryRunResponse | None = None
        try:
            await self.clone(owner, repo_name, branch, token, workdir)
            self.write_workflow(workdir, wf_path, pipeline.content)

            event = self.pick_event(pipeline.content)
            rc, out, err, duration = await self.run_act(workdir, wf_path, event) #exit code, stdout, stderr, and elapsed seconds.


            jobs = parse_act_json(out)
            status = "success" if rc == 0 else "failed"
            response = DryRunResponse(
                pipeline_id=pipeline.id,
                platform="github",
                status=status,
                valid=rc == 0,
                external_pipeline_id=None,   # local run, no remote pipeline
                ref=branch,
                web_url=None,                # local run, no URL
                duration_s=round(duration, 2),
                jobs=jobs,
                cleaned_up=False,
                message=self.summary(rc, jobs, err),
            )
        finally:
            cleaned = self.cleanup(workdir)
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
        if (repo.platform or "").lower() != "github":
            raise DryRunError("Pipeline is not a GitHub pipeline.")
        return pipeline, repo

    def owner_repo(self, repo: Repository) -> tuple[str, str]:
        parts = (repo.full_name or "").split("/")
        if len(parts) < 2:
            raise DryRunError("repository full_name must be 'owner/repo'.")
        return parts[0], parts[1]

    async def get_token(self, repo: Repository, user_id: int, db) -> str | None:
        installation_id = await self.find_installation(repo, user_id, db)
        if installation_id is None:
            return None  # try an unauthenticated clone (works for public repos)
        try:
            return await asyncio.to_thread(get_installation_token, installation_id)
        except Exception as exc:
            raise DryRunError(f"could not obtain GitHub installation token: {exc}")

    async def find_installation(self, repo: Repository, user_id: int, db) -> int | None:
        by_repo = await db.execute(
            select(GitHubInstallationRepo.installation_id).where(
                GitHubInstallationRepo.repo_full_name == repo.full_name
            )
        )
        installation_id = by_repo.scalars().first()
        if installation_id:
            return installation_id
        by_user = await db.execute(
            select(GitHubInstallation.installation_id).where(GitHubInstallation.user_id == user_id)
        )
        return by_user.scalars().first()

    async def precheck(self) -> None:
        if shutil.which(ACT_BINARY) is None:
            raise DryRunError("`act` is not installed on the server; cannot run GitHub dry runs.")
        if shutil.which("docker") is None:
            raise DryRunError("Docker is not installed on the server; `act` requires Docker.")
        rc, _, _ = await self.exec(["docker", "info"], cwd=None, timeout=DOCKER_INFO_TIMEOUT_SEC)
        if rc != 0:
            raise DryRunError("Docker daemon is not reachable; cannot run GitHub dry runs.")

    async def clone(self, owner, repo_name, branch, token, workdir) -> None:
        if token:
            url = f"https://x-access-token:{token}@github.com/{owner}/{repo_name}.git"
        else:
            url = f"https://github.com/{owner}/{repo_name}.git"
        args = [GIT_BINARY, "clone", "--depth", "1", "--branch", branch, url, workdir]
        rc, _, err = await self.exec(args, cwd=None, timeout=CLONE_TIMEOUT_SEC)
        if rc != 0:
            safe = err.replace(token, "***") if token else err # On failure, redact the token from the error
            raise DryRunError(f"git clone failed: {safe.strip()[:200]}")

    def write_workflow(self, workdir, wf_path, content) -> None:
        full = os.path.join(workdir, *wf_path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    async def run_act(self, workdir, wf_path, event) -> tuple[int, str, str, float]:
        args = [
            ACT_BINARY, event,
            "-W", wf_path,
            "--json",
            "-P", f"ubuntu-latest={ACT_IMAGE}", #map each Ubuntu runner label to the chosen Docker image, so  runs-on: ubuntu-latest/22.04/20.04  all resolve
            "-P", f"ubuntu-22.04={ACT_IMAGE}",
            "-P", f"ubuntu-20.04={ACT_IMAGE}",
            "--rm", #remove the container after it finishes
        ]
        if ACT_ARCH:
            args += ["--container-architecture", ACT_ARCH]
        start = time.monotonic()
        rc, out, err = await self.exec(args, cwd=workdir, timeout=ACT_TIMEOUT_SEC)
        return rc, out, err, time.monotonic() - start

    def pick_event(self, content: str) -> str:
        try:
            doc = yaml.safe_load(content) or {}
        except yaml.YAMLError:
            return ACT_EVENT
        if not isinstance(doc, dict):
            return ACT_EVENT
        # YAML 1.1 parses the on: key as the boolean True — check both.
        raw = doc.get("on", doc.get(True))
        if isinstance(raw, dict):
            events = [str(k) for k in raw.keys()]
        elif isinstance(raw, list):
            events = [str(e) for e in raw]
        elif isinstance(raw, str):
            events = [raw]
        else:
            events = []
        if not events or ACT_EVENT in events:
            return ACT_EVENT
        return events[0] #run the first declared event.


    async def exec(self, args, cwd, timeout) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *args, cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return 124, "", f"timed out after {timeout}s"
        return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")

    def summary(self, rc, jobs, err) -> str:
        if rc == 0:
            return f"act completed successfully ({len(jobs)} job(s))"
        tail = " ".join((err or "").strip().splitlines()[-3:])
        return f"act failed (exit {rc}). {tail}"[:300]

    def cleanup(self, workdir) -> bool:
        try:
            shutil.rmtree(workdir, ignore_errors=True)
            return True
        except OSError:
            return False


def parse_act_json(stdout: str) -> list[DryRunJob]:
    jobs: dict[str, dict] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        job_id = rec.get("jobID") or rec.get("job")
        if not job_id:
            continue
        entry = jobs.setdefault(
            job_id,
            {"name": rec.get("jobName") or job_id, "stage": rec.get("stage"), "status": "success"},
        )
        result = rec.get("jobResult") or rec.get("stepResult") or rec.get("result")
        if result:
            r = str(result).lower()
            if r in FAIL_RESULTS:
                entry["status"] = "failed"
            elif r == "skipped" and entry["status"] == "success":
                entry["status"] = "skipped"

    return [
        DryRunJob(
            name=j["name"],
            stage=(str(j["stage"]) if j["stage"] is not None else None),
            status=j["status"],
            duration_s=None,
            allow_failure=False,
            web_url=None,
        )
        for j in jobs.values()
    ]
