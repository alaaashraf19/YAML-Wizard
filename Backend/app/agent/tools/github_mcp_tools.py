"""
GitHub MCP Tool Wrappers — thin LangChain StructuredTool adapters over
the @modelcontextprotocol/server-github npx server.

No detection logic lives here — all detection is in agent/utils/detection.py.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import re
from typing import Any

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URL & repo validation
# ---------------------------------------------------------------------------

def validate_github_url(repo_url: str) -> tuple[str, str]:
    """
    Validate the GitHub URL format and extract owner/repo.
    Raises ValueError for malformed URLs.
    """
    url_clean = repo_url.strip()

    if not url_clean:
        raise ValueError("Repository URL cannot be empty.")

    if "github.com" not in url_clean:
        raise ValueError(f"Not a GitHub URL: '{repo_url}'")

    pattern = r"github\.com[/:]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
    match = re.search(pattern, url_clean)
    if not match:
        raise ValueError(f"Cannot parse owner/repo from URL: '{repo_url}'")

    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")

    if not owner or not repo:
        raise ValueError(f"Invalid owner or repo name in URL: '{repo_url}'")

    return owner, repo


def validate_repo_exists(owner: str, repo: str, token: str) -> None:
    """
    Check the repo actually exists on GitHub and the token has access.
    Raises:
        ValueError       — malformed owner/repo
        FileNotFoundError — repo not found (404)
        PermissionError  — bad token or no access (401/403)
        RuntimeError     — unexpected API error
    """
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=10,
        )

        if resp.status_code == 200:
            return  # all good

        if resp.status_code == 404:
            raise FileNotFoundError(
                f"Repository '{owner}/{repo}' was not found. "
                "Check the URL or make sure the repo is public / accessible."
            )
        if resp.status_code == 401:
            raise PermissionError(
                "GitHub token is invalid or expired. Please reconnect your GitHub account."
            )
        if resp.status_code == 403:
            raise PermissionError(
                f"Access denied to '{owner}/{repo}'. "
                "Make sure your token has the required permissions."
            )

        # Any other non-2xx
        raise RuntimeError(
            f"GitHub API returned unexpected status {resp.status_code} "
            f"for '{owner}/{repo}'."
        )

    except (FileNotFoundError, PermissionError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to reach GitHub API: {exc}") from exc


# ---------------------------------------------------------------------------
# MCP Session Manager
# ---------------------------------------------------------------------------

class MCPSessionManager:
    def __init__(self, github_token: str):
        self.github_token = github_token

    def _get_server_params(self) -> StdioServerParameters:
        return StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
                "PATH": os.environ.get("PATH", ""),
            },
        )

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        # asyncio.run() fails if there's already a running event loop (e.g. inside FastAPI/uvicorn).
        # Solution: always run in a fresh thread with its own event loop.
        def _run_in_new_loop():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._async_call(tool_name, arguments))
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_in_new_loop)
            return future.result()

    async def _async_call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        params = self._get_server_params()
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                parts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                    else:
                        parts.append(str(block))
                return "\n".join(parts)


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class GetFileContentsInput(BaseModel):
    owner: str = Field(description="Repository owner")
    repo:  str = Field(description="Repository name")
    path:  str = Field(description="File path; use '.' for root listing")
    ref:   str = Field(default="HEAD", description="Git ref")


class ListDirectoryInput(BaseModel):
    owner: str = Field(description="Repository owner")
    repo:  str = Field(description="Repository name")
    path:  str = Field(default=".", description="Directory path; use '.' for root")
    ref:   str = Field(default="HEAD", description="Git ref")


class SearchCodeInput(BaseModel):
    query: str = Field(description="Search query")
    owner: str = Field(description="Repository owner")
    repo:  str = Field(description="Repository name")


# ---------------------------------------------------------------------------
# Tool builder
# ---------------------------------------------------------------------------

def build_github_tools(manager: MCPSessionManager) -> list[StructuredTool]:

    def get_file_contents(owner: str, repo: str, path: str, ref: str = "HEAD") -> str:
        try:
            return manager.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo, "path": path, "ref": ref},
            )
        except Exception as exc:
            return f"[ERROR] Could not fetch {path}: {exc}"

    def list_directory(owner: str, repo: str, path: str = ".", ref: str = "HEAD") -> str:
        # GitHub MCP server does not accept path="" — use "." for root listing.
        # We also omit `ref` to avoid "Not Found" errors on some repos.
        resolved_path = path if path else "."
        try:
            return manager.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo, "path": resolved_path},
            )
        except* Exception as eg:
            # Python 3.11+: MCP errors arrive wrapped in an ExceptionGroup
            for exc in eg.exceptions:
                msg = str(exc).lower()
                if "401" in msg or "unauthorized" in msg or "bad credentials" in msg:
                    raise PermissionError("GitHub token is invalid or expired.") from exc
                if "403" in msg or "forbidden" in msg:
                    raise PermissionError("GitHub token does not have access to this repository.") from exc
                if "404" in msg or "not found" in msg:
                    raise FileNotFoundError("GitHub repository not found.") from exc
            raise

    def search_code(query: str, owner: str, repo: str) -> str:
        try:
            return manager.call_tool("search_code", {"query": f"{query} repo:{owner}/{repo}"})
        except Exception as exc:
            return f"[ERROR] Search failed: {exc}"

    return [
        StructuredTool.from_function(
            func=list_directory,
            name="list_directory",
            description="List files/folders in a GitHub repo directory. Use path='.' for root.",
            args_schema=ListDirectoryInput,
        ),
        StructuredTool.from_function(
            func=get_file_contents,
            name="get_file_contents",
            description=(
                "Get a file's content from a GitHub repo. "
                "Use for Dockerfile, requirements.txt, package.json, go.mod, pom.xml, etc. "
                "SKIP lock files and binaries."
            ),
            args_schema=GetFileContentsInput,
        ),
        StructuredTool.from_function(
            func=search_code,
            name="search_code",
            description="Search for code patterns inside a GitHub repository.",
            args_schema=SearchCodeInput,
        ),
    ]