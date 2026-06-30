from __future__ import annotations

from .base import DryRunner
from .github_dry_run import GitHubDryRunner
from .gitlab_dry_run import GitLabDryRunner


def get_dry_runner(platform: str) -> DryRunner:
    normalized = (platform or "").lower()
    if normalized == "gitlab":
        return GitLabDryRunner()
    if normalized == "github":
        return GitHubDryRunner()
    raise ValueError(f"Unsupported platform for dry run: {platform!r}")
