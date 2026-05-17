import os
from dotenv import load_dotenv
import httpx
from io import BytesIO
import zipfile
from typing import Tuple

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

    #if branch is not specified github api returns runs from all branches
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

    async def get_job_logs(self, owner: str, repo: str, job_id: int) -> str:
        
        """Fetch raw job logs from GitHub API"""
        
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    async def get_job_artifacts(self, owner: str, repo: str, run_id: int) -> list[dict]:
        
        """Fetch artifact metadata for a run"""
        
        resp = await self._client.get(
            f"{self.BASE_URL}/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        )
        resp.raise_for_status()
        return resp.json().get("artifacts", [])


    async def download_artifact(self, artifact_url: str) -> bytes:
        
        """Download artifact zip file"""
        
        resp = await self._client.get(artifact_url, follow_redirects=True)#downloads the file into memory as an HTTP response.
        resp.raise_for_status()
        return resp.content
    
    def extract_test_reports_from_zip(self, zip_data: bytes) -> list[Tuple[str, str, str]]:
        """Extract test report files from artifact zip
        
        Returns: [(filename, content, framework_hint), ...]
        """
        reports = []
        try:
            with zipfile.ZipFile(BytesIO(zip_data)) as z:
                for file_info in z.filelist:
                    fname = file_info.filename
                    
                    # Look for common test report patterns
                    if any(pattern in fname.lower() for pattern in 
                           ['test', 'report', 'result', 'junit', 'jest', 'coverage']):
                        
                        if fname.endswith(('.xml', '.json')):
                            content = z.read(fname).decode('utf-8', errors='ignore')
                            reports.append((fname, content, fname.split('.')[-1]))
        except Exception as e:
            logger.warning(f"Failed to extract artifacts: {e}")
        
        return reports
