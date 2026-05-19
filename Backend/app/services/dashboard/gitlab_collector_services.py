import os
import httpx
from dotenv import load_dotenv
from .ci_collector import CICollector
from urllib.parse import quote
from schemas.dashboard import CollectorsRepositoryDetail, CIArtifact

load_dotenv()

class GitLabCollector(CICollector):
    
    """Fetches CI/CD data from the GitLab Pipelines API"""

    BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, token: str | None = None) -> None:
        
        self.token = token or os.getenv("GITLAB_ACCESS_TOKEN")

        if not self.token:
            raise ValueError("GitLab access token not provided.")

        self.headers = {
            "PRIVATE-TOKEN": self.token,
        }

        self._client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()


    async def get_project_id(self, full_name: str) -> int:

        encoded = quote(full_name, safe="")

        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{encoded}"
        )

        resp.raise_for_status()

        data = resp.json()

        return data["id"]
    
    async def get_runs(self, ctx: CollectorsRepositoryDetail, per_page: int = 30, page: int = 1, branch: str | None = None,) -> list[dict]:
        
        """Fetch CI/CD pipelines for a project"""

        project_id = ctx.gitlab_project_id
        params = {"per_page": per_page, "page": page}
        if branch:
            params["ref"] = branch

        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{project_id}/pipelines",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


    async def get_jobs(self, ctx: CollectorsRepositoryDetail, run_id: int) -> list[dict]:
        
        """Fetch jobs for a pipeline"""

        project_id = ctx.gitlab_project_id
        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{project_id}/pipelines/{run_id}/jobs",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        return resp.json()


    async def get_logs(self, ctx: CollectorsRepositoryDetail, job_id: int) -> str:
        """Fetch raw job trace/logs"""

        project_id = ctx.gitlab_project_id
        resp = await self._client.get(
            f"{self.BASE_URL}/projects/{project_id}/jobs/{job_id}/trace",
        )
        resp.raise_for_status()
        return resp.text


    #here artifacts are related to jobs not runs diff from github actions
    async def get_artifacts(self, ctx: CollectorsRepositoryDetail, job_id: int) -> list[dict]:
        
        """GitLab does not expose artifacts exactly like GitHub runs;
        artifacts are usually tied to jobs."""

        project_id = ctx.gitlab_project_id
        return [
            CIArtifact(
                id=str(job_id),
                name="job_artifact",
                download_url=f"{self.BASE_URL}/projects/{project_id}/jobs/{job_id}/artifacts",
                provider="gitlab",
            )
        ]


    async def download_artifact(self, artifact: CIArtifact) -> bytes:

        resp = await self._client.get(artifact.download_url,follow_redirects=True)
        resp.raise_for_status()
        return resp.content
