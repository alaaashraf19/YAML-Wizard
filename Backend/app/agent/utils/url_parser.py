"""
url_parser.py — validates and normalises GitHub / GitLab repo URLs.
Handles:
  - https://github.com/owner/repo
  - https://github.com/owner/repo.git
  - https://github.com/owner/repo/tree/branch/subfolder
  - https://github.com/owner/repo/blob/main/file.py
  - https://gitlab.com/owner/repo
  - https://gitlab.com/owner/group/repo  (nested namespace)
  - https://gitlab.com/owner/repo/-/tree/branch
  - git@github.com:owner/repo.git        (SSH)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Platform(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"


@dataclass
class ParsedRepoURL:
    platform: Platform
    owner: str
    repo: str
    branch: str | None      # None = use default branch from API
    canonical_url: str      # clean https URL, no trailing path


# Markers that indicate a sub-path, not part of owner/repo
_GITHUB_SUB_MARKERS  = ("/tree/", "/blob/", "/commit/", "/releases", "/issues", "/pulls", "/actions")
_GITLAB_SUB_MARKERS  = ("/-/tree/", "/-/blob/", "/-/commit/", "/-/releases", "/-/issues", "/-/merge_requests")

_SSH_RE = re.compile(r'^git@(?P<host>[^:]+):(?P<path>.+?)(?:\.git)?$')


def parse_repo_url(url: str) -> ParsedRepoURL:
    """
    Parse and validate a GitHub or GitLab repo URL.
    Raises ValueError with a human-readable message on failure.
    """
    url = url.strip()

    # ── SSH → HTTPS conversion ────────────────────────────────────────────
    m = _SSH_RE.match(url)
    if m:
        url = f"https://{m.group('host')}/{m.group('path')}"

    # ── Must start with https:// ──────────────────────────────────────────
    if not url.startswith("https://"):
        raise ValueError(
            f"Invalid URL: '{url}'. Must be a full https:// GitHub or GitLab URL."
        )

    # ── Detect platform ───────────────────────────────────────────────────
    lower = url.lower()
    if "github.com" in lower:
        platform = Platform.GITHUB
        sub_markers = _GITHUB_SUB_MARKERS
        host = "github.com"
    elif "gitlab.com" in lower:
        platform = Platform.GITLAB
        sub_markers = _GITLAB_SUB_MARKERS
        host = "gitlab.com"
    else:
        raise ValueError(
            f"Unsupported host in URL: '{url}'. Only github.com and gitlab.com are supported."
        )

    # ── Extract branch from sub-path (before stripping) ──────────────────
    branch: str | None = None
    for marker in ("/tree/", "/-/tree/"):
        if marker in url:
            after = url[url.index(marker) + len(marker):]
            # branch is the first path component after /tree/
            branch = after.split("/")[0] or None
            break

    # ── Strip sub-paths ───────────────────────────────────────────────────
    clean = url.rstrip("/")
    for marker in sub_markers:
        if marker in clean:
            clean = clean[:clean.index(marker)]
    clean = clean.rstrip("/")

    # ── Extract owner + repo from path ────────────────────────────────────
    # Remove https://github.com/ or https://gitlab.com/
    try:
        path = clean.split(f"{host}/", 1)[1]
    except IndexError:
        raise ValueError(f"Cannot extract repository path from URL: '{url}'")

    path = path.removesuffix(".git").strip("/")
    parts = [p for p in path.split("/") if p]

    if len(parts) < 2:
        raise ValueError(
            f"URL does not contain owner/repo: '{url}'. "
            f"Expected format: https://{host}/owner/repo"
        )

    # GitLab supports nested namespaces: owner/group/subgroup/repo
    # The repo is always the last segment; owner is everything before it.
    if platform == Platform.GITLAB:
        owner = "/".join(parts[:-1])
        repo  = parts[-1]
    else:
        owner = parts[0]
        repo  = parts[1]

    # ── Basic sanity checks ───────────────────────────────────────────────
    _validate_segment("owner", owner)
    _validate_segment("repo",  repo)

    canonical = f"https://{host}/{owner}/{repo}"
    return ParsedRepoURL(
        platform=platform,
        owner=owner,
        repo=repo,
        branch=branch,
        canonical_url=canonical,
    )


def _validate_segment(name: str, value: str) -> None:
    # Allow letters, digits, hyphens, underscores, dots, and slash (for GitLab namespaces)
    if not re.match(r'^[\w\-./]+$', value):
        raise ValueError(f"Invalid {name} in URL: '{value}'")
    if len(value) > 200:
        raise ValueError(f"{name} is too long: '{value[:40]}...'")
