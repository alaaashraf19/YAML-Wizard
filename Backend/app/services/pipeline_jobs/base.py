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

    def reorder(self, content: str, new_order: list[str]) -> str:
        data = self.load(content)
        container, all_keys, job_keys = self.container_and_keys(data)
        self.validate_permutation(job_keys, new_order)
        if [str(k) for k in job_keys] == list(new_order):
            return content  # no-op. keep the original text exactly
        for key in self.target_sequence(all_keys, job_keys, new_order):
            container.move_to_end(key)
        return self.dump(data)

    @staticmethod
    def validate_permutation(job_keys: list, new_order: list[str]) -> None:
        if len(new_order) != len(set(new_order)):
            raise InvalidJobOrder("order contains duplicate job ids")
        current = {str(k) for k in job_keys}
        requested = set(new_order)
        if current != requested:
            missing = sorted(current - requested)
            unknown = sorted(requested - current)
            raise InvalidJobOrder(
                "order must be a permutation of the existing jobs "
                f"(missing={missing}, unknown={unknown})"
            )

    #full target key order: job slots are filled from new_order while every otherkey (globals, hidden templates) keeps its original position
    @staticmethod
    def target_sequence(all_keys: list, job_keys: list, new_order: list[str]) -> list:
        job_set = {str(k) for k in job_keys}
        nxt = iter(new_order)
        return [next(nxt) if str(key) in job_set else key for key in all_keys]
