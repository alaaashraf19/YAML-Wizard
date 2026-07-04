"""
GitLab Repo Context Agent
=========================
Deterministic repo scanner using the GitLab REST API v4.
No git clone. No MCP server needed for GitLab.
Steps:
  1. List repo root via GitLab API
  2. Fetch key config / dependency files
  3. Fetch default branch from GitLab API
  4. Delegate all detection to agent/utils/detection.py
  5. Return a ContextPackage
Detection logic lives exclusively in agent/utils/detection.py — nothing is
duplicated here.
"""
from __future__ import annotations

import logging

from agent.tools.gitlab_api_tools import GitLabAPIClient
from agent.utils.detection import build_context_package, truncate
from schemas.context_package import ContextPackage

logger = logging.getLogger(__name__)

MAX_FILE_FETCHES = 20

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
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env",
    "example.env",
}

SUBDIRS_TO_SCAN    = {"backend", "frontend", "src", "app", "api", "server", "web", "packages"}
SUBDIR_FILES       = (
    "pyproject.toml", "requirements.txt", "package.json",
    "jest.config.js", "jest.config.ts",
    "playwright.config.js", "playwright.config.ts",
    "pytest.ini", "setup.cfg",
    ".env.example", ".env.sample",
)
CI_DIRS_TO_EXPLORE = {".gitlab-ci"}  # some repos split CI into a folder


def _build_directory_tree(entries: list[dict]) -> str:
    lines = []
    for entry in entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        lines.append(f"{name}/" if kind == "dir" else name)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_gitlab_agent(
    repo_url: str,
    gitlab_token: str,
) -> ContextPackage:
    """
    Scan a GitLab repository and return a ContextPackage.

    Args:
        repo_url:      Full GitLab URL (any format).
        gitlab_token:  Personal access token with read_api scope.
    """
    # ── Parse owner/repo from URL ─────────────────────────────────────────
    url_clean = repo_url.rstrip("/")
    for marker in ("/-/tree/", "/-/blob/", "/-/commit/", "/-/releases", "/-/issues"):
        if marker in url_clean:
            url_clean = url_clean[:url_clean.index(marker)]
    parts = url_clean.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {repo_url}")
    owner, repo_name = parts[-2], parts[-1]
    repo_name = repo_name.removesuffix(".git")

    logger.info("GitLabAgent starting: %s/%s", owner, repo_name)

    client = GitLabAPIClient(token=gitlab_token)

    # ── Step 1: fetch default branch ──────────────────────────────────────
    default_branch = client.get_default_branch(owner, repo_name)
    logger.info("Default branch: %s", default_branch)

    # ── Step 2: list root ─────────────────────────────────────────────────
    root_entries = client.list_directory(owner, repo_name, path="", ref=default_branch)
    logger.info("Root listing: %d entries", len(root_entries))

    plain_tree = _build_directory_tree(root_entries)
    all_paths  = [e["name"] for e in root_entries if e["type"] == "file"]

    # ── Step 3: fetch key files ───────────────────────────────────────────
    key_files: dict[str, str] = {}
    fetch_count = 0

    # Root files
    for entry in root_entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind != "file" or name not in ROOT_FILES_TO_FETCH:
            continue
        if fetch_count >= MAX_FILE_FETCHES:
            logger.warning("MAX_FILE_FETCHES (%d) reached at root scan", MAX_FILE_FETCHES)
            break
        content = client.get_file_content(owner, repo_name, name, ref=default_branch)
        fetch_count += 1
        if content is not None:
            key_files[name] = truncate(content)
            logger.info("Fetched: %s", name)

    # .gitlab-ci.yml sub-files (some projects include additional CI files)
    for entry in root_entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind != "dir" or name not in CI_DIRS_TO_EXPLORE:
            continue
        sub_entries = client.list_directory(owner, repo_name, path=name, ref=default_branch)
        for sub in sub_entries:
            sub_name = sub.get("name", "")
            sub_kind = sub.get("type", "")
            if sub_kind == "file" and sub_name.endswith((".yml", ".yaml")):
                sub_path = f"{name}/{sub_name}"
                if fetch_count >= MAX_FILE_FETCHES:
                    break
                content = client.get_file_content(owner, repo_name, sub_path, ref=default_branch)
                fetch_count += 1
                if content is not None:
                    key_files[sub_path] = truncate(content)
                    all_paths.append(sub_path)
                    logger.info("Fetched CI sub-file: %s", sub_path)

    # Subdir files (backend/pyproject.toml etc.)
    for entry in root_entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind != "dir" or name not in SUBDIRS_TO_SCAN:
            continue
        for sub_file in SUBDIR_FILES:
            sub_path = f"{name}/{sub_file}"
            if sub_path in key_files or fetch_count >= MAX_FILE_FETCHES:
                continue
            content = client.get_file_content(owner, repo_name, sub_path, ref=default_branch)
            fetch_count += 1
            if content is not None:
                key_files[sub_path] = truncate(content)
                logger.info("Fetched subdir file: %s", sub_path)

    logger.info("Total files fetched: %d", fetch_count)

    # ── Step 4: build ContextPackage via shared detection utils ──────────
    package = build_context_package(
        key_files=key_files,
        all_paths=all_paths,
        directory_tree=plain_tree,
        default_branch=default_branch,
        notes=f"GitLab: fetched {fetch_count} files from {owner}/{repo_name}",
    )
    logger.info(
        "Done — languages=%s runners=%s env_vars=%d services=%s",
        package.languages, package.test_runners, len(package.env_vars), package.services,
    )
    return package
