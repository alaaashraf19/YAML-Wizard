from __future__ import annotations

from schemas.pipeline_jobs_schema import JobView
from .base import JobsNotFound, PipelineEditor


#GitHub needs may be a single job id or a list of job ids
def normalize_needs(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


#GitHub Actions: jobs are the keys of the top-level jobs: mapping
class GitHubPipelineEditor(PipelineEditor):
    def container_and_keys(self, data):
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, dict) or not jobs:
            raise JobsNotFound("No 'jobs:' mapping found in the GitHub Actions workflow")
        keys = list(jobs.keys())
        return jobs, keys, keys

    def list_jobs(self, content: str) -> list[JobView]:
        data = self.load(content)
        jobs, _, _ = self.container_and_keys(data)
        out: list[JobView] = []
        for index, (key, spec) in enumerate(jobs.items()):
            needs = normalize_needs(spec.get("needs")) if isinstance(spec, dict) else []
            out.append(JobView(id=str(key), display_index=index, stage=None, needs=needs))
        return out
