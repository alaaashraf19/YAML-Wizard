from __future__ import annotations

import logging

from agent.tools.github_graphql_client import GitHubGraphQLClient, GitHubGraphQLError
# from agent.tools.github_mcp_tools import MCPSessionManager, build_github_tools
from agent.utils.detection import build_context_package, truncate
from agent.utils.url_parser import parse_repo_url
from schemas.context_package import ContextPackage

logger = logging.getLogger(__name__)

MAX_FILES_PER_REQUEST = 60  # GitHub GraphQL caps total aliased fields per query; stay well under it

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

SUBDIR_FILES = (
    "pyproject.toml", "requirements.txt", "package.json",
    "jest.config.js", "jest.config.ts",
    "playwright.config.js", "playwright.config.ts",
    "pytest.ini", "setup.cfg",
    ".env.example", ".env.sample",
)

# Directories to recurse into
DIRS_TO_EXPLORE = {".github"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_directory_tree(entries: list[dict]) -> str:
    return "\n".join(f"{e['name']}/" if e["type"] == "dir" else e["name"] for e in entries)


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
        github_token: Token with repo read access (OAuth token or GitHub App
                       installation token — see core/github_auth.py).
    """
    parsed = parse_repo_url(repo_url)
    owner, repo = parsed.owner, parsed.repo

    logger.info("GitHubAgent starting: %s/%s", owner, repo)

    client = GitHubGraphQLClient(token=github_token)

    # ── Call 1: root listing + default branch + every root-candidate file ──
    # in a single batched request.
    candidate_root_paths = sorted(ROOT_FILES_TO_FETCH)
    try:
        result = client.fetch_root_and_files(owner, repo, candidate_root_paths)
    except GitHubGraphQLError as exc:
        logger.warning("GraphQL batch error, repo may have an empty/unusual root: %s", exc)
        raise

    default_branch = result.default_branch
    root_entries = result.entries
    plain_tree = _build_directory_tree(root_entries)
    all_paths = [e["name"] for e in root_entries if e["type"] == "file"]

    key_files: dict[str, str] = {}
    fetched = 0
    for path, file_result in result.files.items():
        if file_result.content is None or file_result.is_binary:
            continue
        key_files[path] = truncate(file_result.content)
        fetched += 1
    logger.info("Call 1: root listing (%d entries) + %d root files fetched in 1 round-trip",
                len(root_entries), fetched)

    # ── Call 2 (conditional): subdir candidate files + .github/workflows ───
    # We don't know workflow filenames yet, so list that directory first —
    # this is the only place we may need a small extra round-trip, and only
    # if the repo actually has a .github directory.
    second_batch_paths: list[str] = []

    for entry in root_entries:
        if entry["type"] == "dir" and entry["name"] in SUBDIRS_TO_SCAN:
            for sub_file in SUBDIR_FILES:
                second_batch_paths.append(f"{entry['name']}/{sub_file}")

    has_github_dir = any(e["type"] == "dir" and e["name"] == ".github" for e in root_entries)
    workflow_paths: list[str] = []
    if has_github_dir:
        try:
            workflow_entries = client.list_directory(owner, repo, ".github/workflows", ref=default_branch)
            workflow_paths = [
                f".github/workflows/{e['name']}"
                for e in workflow_entries
                if e["type"] == "file" and e["name"].endswith((".yml", ".yaml"))
            ]
            all_paths.extend(workflow_paths)
        except (FileNotFoundError, GitHubGraphQLError) as exc:
            logger.info("No .github/workflows directory or could not list it: %s", exc)

    second_batch_paths.extend(workflow_paths)
    second_batch_paths = second_batch_paths[:MAX_FILES_PER_REQUEST]

    if second_batch_paths:
        try:
            batch2 = client.fetch_files(owner, repo, second_batch_paths)
            for path, file_result in batch2.items():
                if file_result.content is None or file_result.is_binary:
                    continue
                key_files[path] = truncate(file_result.content)
                fetched += 1
            logger.info("Call 2: %d subdir/workflow files fetched in 1 round-trip", len(batch2))
        except GitHubGraphQLError as exc:
            logger.warning("Subdir/workflow batch fetch failed, continuing with what we have: %s", exc)

    logger.info("Total files fetched: %d (in at most 3 GraphQL round-trips)", fetched)

    # ── Build ContextPackage via shared detection utils ────────────────────
    package = build_context_package(
        key_files=key_files,
        all_paths=all_paths,
        directory_tree=plain_tree,
        default_branch=default_branch,
        notes=f"GitHub: fetched {fetched} files from {owner}/{repo} via GraphQL",
    )
    logger.info(
        "Done — languages=%s runners=%s env_vars=%d services=%s",
        package.languages, package.test_runners, len(package.env_vars), package.services,
    )
    return package