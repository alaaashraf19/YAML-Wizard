"""
GitLab REST API Tools — fetches repo files via GitLab API v4.
No git clone needed. Mirrors the interface expected by the repo context agent.

Requires a GitLab personal access token with `read_api` scope.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

GITLAB_API_BASE = "https://gitlab.com/api/v4"


class GitLabAPIClient:
    def __init__(self, token: str, base_url: str = GITLAB_API_BASE):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._headers = {"PRIVATE-TOKEN": token} if token else {}

    # ── internal helpers ──────────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list | None:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = httpx.get(url, headers=self._headers, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                raise PermissionError("GitLab token is invalid or expired.") from exc
            if status == 403:
                raise PermissionError("GitLab token does not have access to this repository.") from exc
            if status == 404:
                raise FileNotFoundError("GitLab repository not found.") from exc
            # Other HTTP errors (5xx etc.) — log and return None so we keep going
            logger.warning("GitLab API %s → %s", url, status)
            return None
        except Exception as exc:
            logger.warning("GitLab API error %s: %s", url, exc)
            return None

    @staticmethod
    def _encode_project(owner: str, repo: str) -> str:
        """URL-encode the namespace/project path for GitLab API."""
        return quote(f"{owner}/{repo}", safe="")

    # ── public API ────────────────────────────────────────────────────────

    def get_default_branch(self, owner: str, repo: str) -> str:
        project_id = self._encode_project(owner, repo)
        data = self._get(f"/projects/{project_id}")
        if data and isinstance(data, dict):
            return data.get("default_branch", "main")
        return "main"

    def list_directory(self, owner: str, repo: str, path: str = "", ref: str = "HEAD") -> list[dict]:
        """
        Returns a list of entries like:
          [{"name": "Dockerfile", "type": "blob"}, {"name": "src", "type": "tree"}]
        """
        project_id = self._encode_project(owner, repo)
        params: dict = {"ref": ref, "per_page": 100}
        if path:
            params["path"] = path
        data = self._get(f"/projects/{project_id}/repository/tree", params=params)
        if not isinstance(data, list):
            return []
        # Normalise to the same shape the GitHub agent expects
        return [
            {
                "name": entry.get("name", ""),
                "type": "dir" if entry.get("type") == "tree" else "file",
            }
            for entry in data
        ]

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> str | None:
        """
        Returns the decoded file content as a plain string, or None on failure.
        """
        project_id = self._encode_project(owner, repo)
        encoded_path = quote(path, safe="")
        data = self._get(
            f"/projects/{project_id}/repository/files/{encoded_path}",
            params={"ref": ref},
        )
        if not isinstance(data, dict):
            return None
        raw = data.get("content", "")
        encoding = data.get("encoding", "base64")
        if encoding == "base64":
            try:
                return base64.b64decode(raw).decode("utf-8", errors="replace")
            except Exception:
                return None
        return raw

    def list_directory_recursive(
        self, owner: str, repo: str, path: str = "", ref: str = "HEAD", max_depth: int = 1
    ) -> list[dict]:
        """List directory and optionally recurse one level (for .gitlab-ci dirs etc.)."""
        entries = self.list_directory(owner, repo, path, ref)
        if max_depth <= 0:
            return entries
        result = list(entries)
        for entry in entries:
            if entry["type"] == "dir":
                sub_path = f"{path}/{entry['name']}" if path else entry["name"]
                sub_entries = self.list_directory(owner, repo, sub_path, ref)
                result.extend(sub_entries)
        return result