from __future__ import annotations
import io
from abc import ABC, abstractmethod
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from schemas.pipeline_jobs_schema import JobView


#Raised when a requested order is not a permutation of the existing jobs
class InvalidJobOrder(ValueError):
    pass

#Raised when the pipeline YAML has no reorderable jobs for the platform.
class JobsNotFound(ValueError):
    pass


class PipelineEditor(ABC):
    def __init__(self) -> None:
        self._yaml = YAML(typ="rt")
        self._yaml.preserve_quotes = True
        self._yaml.width = 4096
        self._yaml.indent(mapping=2, sequence=4, offset=2)

    def load(self, content: str):
        data = self._yaml.load(content)
        if data is None:
            raise JobsNotFound("Pipeline YAML is empty")
        return data

    def dump(self, data) -> str:
        buf = io.StringIO()
        self._yaml.dump(data, buf)
        return buf.getvalue()

    #truns a single job (its key + spec) into a YAML block, commentedMap is the ruamel data structure that keeps the comments .
    def job_block(self, key, spec) -> str:
        block = CommentedMap()
        block[key] = spec
        return self.dump(block)

    #Parse a single job block ("<id>:\n  <spec>") into (id, spec). spec must be a mapping.
    def parse_job_block(self, content: str) -> tuple[str, object]:
        data = self.load(content)
        if not isinstance(data, dict):
            raise InvalidJobOrder("job content must be a YAML mapping")
        keys = list(data.keys())
        if len(keys) != 1:
            raise InvalidJobOrder(
                f"a job block must have exactly one top-level key, found {len(keys)}: {[str(k) for k in keys]}"
            )
        key = keys[0]
        spec = data[key]
        if not isinstance(spec, dict):
            raise InvalidJobOrder(f"job '{key}' body must be a mapping")
        return str(key), spec

    #Whether a job id is a legal job key for this platform (overridden for GitLab).
    def is_valid_job_id(self, job_id: str) -> bool:
        return isinstance(job_id, str) and bool(job_id.strip()) # string and not empty


    #Returns (container, all_keys_in_container, reorderable_job_keys)
    @abstractmethod
    def container_and_keys(self, data) -> tuple[CommentedMap, list, list]:
        pass

    #Return the ordered, read-only view of the pipeline's jobs.
    @abstractmethod
    def list_jobs(self, content: str) -> list[JobView]:
        pass


    def job_ids(self, content: str) -> list[str]:
        _, _, job_keys = self.container_and_keys(self.load(content))
        return [str(k) for k in job_keys]

    #Rebuild the pipeline from the desired ordered jobs, preserving every non-job key (globals, hidden templates) and the original formatting/comments.
    #jobs is an ordered list of (job_id, spec). omitted original jobs are deleted, new ids are added, and matching ids have their spec replaced.
    def assemble(self, content: str, jobs: list[tuple[str, object]]) -> str:
        data = self.load(content)
        container, _all_keys, job_keys = self.container_and_keys(data)
        desired_ids = [jid for jid, _ in jobs]
        keep = set(desired_ids)
        #delete jobs the user removed
        for key in list(job_keys):
            if str(key) not in keep:
                del container[key]
        #replace existing specs / add new jobs
        for jid, spec in jobs:
            container[jid] = spec
        #apply the requested order (non-job keys keep their relative position)
        for jid in desired_ids:
            container.move_to_end(jid)
        return self.dump(data)
