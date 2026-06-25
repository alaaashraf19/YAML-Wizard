from __future__ import annotations

from schemas.pipeline_jobs_schema import JobView
from .base import JobsNotFound, PipelineEditor

# Top-level GitLab CI keywords that are NOT jobs.
GITLAB_GLOBAL_KEYS = {
    "default", "include", "stages", "variables", "workflow",
    "image", "services", "before_script", "after_script", "cache",
}


#GitLab needs may be a string, a list of strings, or a list of {job: name, ...} mappings
def normalize_needs(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict) and "job" in item:
                out.append(str(item["job"]))
        return out
    return []


#GitLab ci jobs are top-level keys that are not reserved globals or hidden (.xxxx) templates; globals keep their position, only jobs reorder
class GitLabPipelineEditor(PipelineEditor):
    def is_job(self, key, value) -> bool:
        return (
            isinstance(key, str)
            and not key.startswith(".")
            and key not in GITLAB_GLOBAL_KEYS
            and isinstance(value, dict)
        )

    def container_and_keys(self, data):
        if not isinstance(data, dict):
            raise JobsNotFound("Invalid GitLab CI file: expected a top-level mapping")
        all_keys = list(data.keys())
        job_keys = [k for k in all_keys if self.is_job(k, data[k])]
        if not job_keys:
            raise JobsNotFound("No jobs found in the GitLab CI file")
        return data, all_keys, job_keys

    def list_jobs(self, content: str) -> list[JobView]:
        data = self.load(content)
        _, _, job_keys = self.container_and_keys(data)
        out: list[JobView] = []
        for index, key in enumerate(job_keys):
            spec = data.get(key)
            stage = spec.get("stage") if isinstance(spec, dict) else None
            needs = normalize_needs(spec.get("needs")) if isinstance(spec, dict) else []
            out.append(JobView(
                id=str(key),
                display_index=index,
                stage=str(stage) if stage is not None else None,
                needs=needs,
            ))
        return out
