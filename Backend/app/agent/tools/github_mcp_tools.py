"""
GitHub MCP Tool Wrappers for LangChain.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
import os

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
        return asyncio.run(self._async_call(tool_name, arguments))

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


class GetFileContentsInput(BaseModel):
    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")
    path: str = Field(description="File path within the repository; use '' for root listing")
    ref: str = Field(default="HEAD", description="Git ref")


class ListDirectoryInput(BaseModel):
    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")
    path: str = Field(default="", description="Directory path; empty string for root")
    ref: str = Field(default="HEAD", description="Git ref")


class SearchCodeInput(BaseModel):
    query: str = Field(description="Search query")
    owner: str = Field(description="Repository owner")
    repo: str = Field(description="Repository name")


def build_github_tools(manager: MCPSessionManager) -> list[StructuredTool]:

    def get_file_contents(owner: str, repo: str, path: str, ref: str = "HEAD") -> str:
        """Fetch raw content of a file OR list a directory from a GitHub repository."""
        try:
            return manager.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo, "path": path, "ref": ref},
            )
        except Exception as exc:
            return f"[ERROR] Could not fetch {path}: {exc}"

    def list_directory(owner: str, repo: str, path: str = "", ref: str = "HEAD") -> str:
        """List files and folders in a GitHub repository directory. Use path='' for root."""
        try:
            return manager.call_tool(
                "get_file_contents",
                {"owner": owner, "repo": repo, "path": path, "ref": ref},
            )
        except Exception as exc:
            return f"[ERROR] Could not list directory {path}: {exc}"

    def search_code(query: str, owner: str, repo: str) -> str:
        """Search for code patterns within a GitHub repository."""
        try:
            scoped_query = f"{query} repo:{owner}/{repo}"
            return manager.call_tool("search_code", {"query": scoped_query})
        except Exception as exc:
            return f"[ERROR] Search failed: {exc}"

    return [
        StructuredTool.from_function(
            func=list_directory,
            name="list_directory",
            description=(
                "List files and folders in a GitHub repository directory. "
                "ALWAYS call this first with path='' to see the root. "
                "Then decide which files to fetch."
            ),
            args_schema=ListDirectoryInput,
        ),
        StructuredTool.from_function(
            func=get_file_contents,
            name="get_file_contents",
            description=(
                "Get a specific file's content from a GitHub repo. "
                "Use for Dockerfile, requirements.txt, package.json, pyproject.toml, go.mod, pom.xml, etc. "
                "SKIP lock files (package-lock.json, poetry.lock, Pipfile.lock) and binaries."
            ),
            args_schema=GetFileContentsInput,
        ),
        StructuredTool.from_function(
            func=search_code,
            name="search_code",
            description=(
                "Search for code patterns inside a GitHub repository. "
                "Useful to find environment variables, script sections, or configurations."
            ),
            args_schema=SearchCodeInput,
        ),
    ]