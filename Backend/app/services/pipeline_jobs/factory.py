from .base import PipelineEditor
from .github_editor import GitHubPipelineEditor
from .gitlab_editor import GitLabPipelineEditor


def get_pipeline_editor(platform: str) -> PipelineEditor:
    normalized = (platform or "").lower()
    if normalized == "github":
        return GitHubPipelineEditor()
    if normalized == "gitlab":
        return GitLabPipelineEditor()
    raise ValueError(f"Unsupported platform for job editing: {platform!r}")
