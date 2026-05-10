
from datetime import datetime
import os
from dotenv import load_dotenv
import httpx
load_dotenv()

class GitHubCollector:
    
    """Fetches CI/CD data from the GitHub Actions API"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None) -> None:
        
        self.token = token or os.getenv("GITHUB_ACCESS_TOKEN") # to be changed not get it from env 
        
        if not self.token:
            raise ValueError("GitHub access token not provided. Set GITHUB_ACCESS_TOKEN in environment variables.")
        
        auth_prefix = "Bearer" if self.token.startswith("github_pat_") else "token"
        self.headers = {
            "Authorization": f"{auth_prefix} {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    
    async def close(self) -> None:
        await self._client.aclose()

    
    async def get_workflow_runs(self, owner: str, repo: str, per_page: int = 30, page: int = 1, branch: str | None = None,) -> list[dict]:
        
        """Fetch workflow runs for a repository"""
        
        params: dict = {"per_page": per_page, "page": page}
        if branch:
            params["branch"] = branch
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/actions/runs",
            params=params,
            )
        resp.raise_for_status()
        return resp.json().get("workflow_runs", [])
    

    async def get_run_jobs(self, owner: str, repo: str, run_id: int) -> list[dict]:
        
        """Fetch jobs for a specific workflow run"""
        
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        return resp.json().get("jobs", [])



    async def get_job_log(self, owner: str, repo: str, job_id: int) -> str:
        
        """Fetch raw log text for a specific job"""
        
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
                follow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.text
        except httpx.HTTPError:
            pass
        return ""
    

    @staticmethod
    def parse_duration(started_at: str | None, completed_at: str | None) -> int | None:
        
        """Calculate duration in seconds from ISO timestamps"""
        #github timings are like: "2026-05-10T12:00:00Z"
        # we convert to "2026-05-10T12:00:00+00:00"
        if not started_at or not completed_at:
            return None
        try:
            #this creates an object like: datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            return max(0, int((end - start).total_seconds()))
        except (ValueError, TypeError):
            return None
    


