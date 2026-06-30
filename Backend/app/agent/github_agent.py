"""
GitHub Repo Context Agent
=========================
Deterministic repo scanner using the @modelcontextprotocol/server-github MCP server.

Steps:
  1. Validate URL format and repo existence via GitHub API
  2. List repo root via MCP
  3. Fetch key config / dependency files
  4. Fetch default branch from GitHub API
  5. Delegate all detection to agent/utils/detection.py
  6. Return a ContextPackage

Detection logic lives exclusively in agent/utils/detection.py — nothing is
duplicated here.
"""
from __future__ import annotations

import json
import logging
import os

from agent.tools.github_mcp_tools import (
    MCPSessionManager,
    build_github_tools,
    validate_github_url,
    validate_repo_exists,
)
from agent.utils.detection import build_context_package, truncate
from schemas.context_package import ContextPackage

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 20  # raised from 15 to handle larger repos

# Files always fetched if present at root
ROOT_FILES_TO_FETCH = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "package.json",
    "tsconfig.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Makefile",
    ".gitlab-ci.yml",
    ".travis.yml",
    "Gemfile",
    "karma.conf.js",
    "jest.config.js",
    "jest.config.ts",
    "playwright.config.js",
    "playwright.config.ts",
    ".rspec",
    "pytest.ini",
    "tox.ini",
    # env examples for secret detection
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env",
    "example.env",
}

# Subdirectories to scan for config files
SUBDIRS_TO_SCAN = {"backend", "frontend", "src", "app", "api", "server", "web", "packages"}

# Directories to recurse into
DIRS_TO_EXPLORE = {".github"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_directory_listing(raw: str) -> tuple[str, list[dict]]:
    try:
        entries = json.loads(raw)
        if not isinstance(entries, list):
            return raw, []
        lines = []
        for entry in entries:
            name = entry.get("name", "")
            kind = entry.get("type", "")
            lines.append(f"{name}/" if kind == "dir" else name)
        return "\n".join(lines), entries
    except (json.JSONDecodeError, AttributeError):
        return raw, []


def _extract_file_content(raw: str) -> str:
    """
    GitHub MCP wraps file responses:
      {"name": "pyproject.toml", "content": "actual text", ...}
    Extract the plain content field, falling back to raw string.
    """
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "content" in parsed and isinstance(parsed["content"], str):
            return parsed["content"]
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


def _select_files_to_fetch(entries: list[dict]) -> list[str]:
    paths: list[str] = []
    dir_names: list[str] = []
    for entry in entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind == "file" and name in ROOT_FILES_TO_FETCH:
            paths.append(name)
        elif kind == "dir" and name in DIRS_TO_EXPLORE:
            dir_names.append(name)
    if ".github" in dir_names:
        paths.append(".github/workflows")
    return paths


def _get_default_branch_via_api(owner: str, repo: str, github_token: str) -> str:
    """Fetch default branch directly from GitHub REST API."""
    try:
        import httpx
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("default_branch", "main")
    except Exception as exc:
        logger.warning("Could not fetch default branch from GitHub API: %s", exc)
        return "main"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_github_agent(
    repo_url: str,
    github_token: str,
) -> ContextPackage:
    """
    Scan a GitHub repository and return a ContextPackage.

    Args:
        repo_url:     Full GitHub URL (any format).
        github_token: Personal access token with repo read access.

    Raises:
        ValueError        — malformed / non-GitHub URL
        FileNotFoundError — repo does not exist or is not accessible
        PermissionError   — bad token or insufficient permissions
        RuntimeError      — unexpected GitHub API or MCP error
    """
    # ── Step 0: validate URL format ───────────────────────────────────────
    try:
        owner, repo = validate_github_url(repo_url)
    except ValueError as exc:
        logger.error("Invalid GitHub URL '%s': %s", repo_url, exc)
        raise

    logger.info("GitHubAgent starting: %s/%s", owner, repo)

    # ── Step 0b: validate repo exists on GitHub ───────────────────────────
    # This gives a clear, fast error before spending time on MCP calls.
    try:
        validate_repo_exists(owner, repo, github_token)
    except (FileNotFoundError, PermissionError, RuntimeError) as exc:
        logger.error("Repo validation failed for %s/%s: %s", owner, repo, exc)
        raise

    logger.info("Repo validated: %s/%s", owner, repo)

    # ── Build MCP tools ───────────────────────────────────────────────────
    manager  = MCPSessionManager(github_token=github_token)
    tools    = build_github_tools(manager)
    tool_map = {t.name: t for t in tools}

    def call(tool_name: str, **kwargs) -> str:
        result = tool_map[tool_name].invoke(kwargs)
        return result if isinstance(result, str) else str(result)

    # ── Step 1: list root ─────────────────────────────────────────────────
    # Use path="." — the GitHub MCP server does not accept path=""
    raw_root = call("list_directory", owner=owner, repo=repo, path=".")
    plain_tree, root_entries = _parse_directory_listing(raw_root)
    logger.info("Root listing: %d entries", len(root_entries))

    all_paths = [e.get("name", "") for e in root_entries if e.get("type") == "file"]

    # ── Step 2: fetch key files ───────────────────────────────────────────
    paths_to_fetch = _select_files_to_fetch(root_entries)
    logger.info("Files selected: %s", paths_to_fetch)

    key_files: dict[str, str] = {}
    fetch_count = 0

    for path in paths_to_fetch:
        if fetch_count >= MAX_TOOL_CALLS:
            logger.warning("MAX_TOOL_CALLS (%d) reached", MAX_TOOL_CALLS)
            break

        raw = call("get_file_contents", owner=owner, repo=repo, path=path)
        fetch_count += 1

        if raw.startswith("[ERROR]"):
            logger.warning("Skipping %s: %s", path, raw)
            continue

        _, sub_entries = _parse_directory_listing(raw)
        if sub_entries:
            # It's a directory (e.g. .github/workflows) → fetch yml files inside
            for entry in sub_entries:
                sub_name = entry.get("name", "")
                sub_kind = entry.get("type", "")
                if sub_kind == "file" and sub_name.endswith((".yml", ".yaml")):
                    sub_path = f"{path}/{sub_name}"
                    if fetch_count >= MAX_TOOL_CALLS:
                        break
                    sub_raw = call("get_file_contents", owner=owner, repo=repo, path=sub_path)
                    fetch_count += 1
                    if not sub_raw.startswith("[ERROR]"):
                        key_files[sub_path] = truncate(_extract_file_content(sub_raw))
                        all_paths.append(sub_path)
                        logger.info("Fetched: %s", sub_path)
        else:
            key_files[path] = truncate(_extract_file_content(raw))
            logger.info("Fetched: %s", path)

    # ── Step 2b: scan known subdirs ───────────────────────────────────────
    SUBDIR_FILES = (
        "pyproject.toml", "requirements.txt", "package.json",
        "jest.config.js", "jest.config.ts",
        "playwright.config.js", "playwright.config.ts",
        "pytest.ini", "setup.cfg",
        ".env.example", ".env.sample",
    )
    for entry in root_entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind != "dir" or name not in SUBDIRS_TO_SCAN:
            continue
        for sub_file in SUBDIR_FILES:
            sub_path = f"{name}/{sub_file}"
            if sub_path in key_files or fetch_count >= MAX_TOOL_CALLS:
                continue
            sub_raw = call("get_file_contents", owner=owner, repo=repo, path=sub_path)
            fetch_count += 1
            if not sub_raw.startswith("[ERROR]"):
                key_files[sub_path] = truncate(_extract_file_content(sub_raw))
                logger.info("Fetched subdir file: %s", sub_path)

    # ── Step 3: fetch default branch ──────────────────────────────────────
    default_branch = _get_default_branch_via_api(owner, repo, github_token)
    logger.info("Default branch: %s", default_branch)

    # ── Step 4: build ContextPackage via shared detection utils ──────────
    package = build_context_package(
        key_files=key_files,
        all_paths=all_paths,
        directory_tree=plain_tree,
        default_branch=default_branch,
        notes=f"GitHub: fetched {fetch_count} files from {owner}/{repo}",
    )
    logger.info(
        "Done — languages=%s runners=%s env_vars=%d services=%s",
        package.languages, package.test_runners, len(package.env_vars), package.services,
    )
    return package