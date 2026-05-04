"""
ContextPackage: the structured output of the RepoContextAgent.
"""
from __future__ import annotations
import json
from typing import Optional
from pydantic import BaseModel, Field


class ContextPackage(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    test_runners: list[str] = Field(default_factory=list)
    has_docker: bool = False
    has_existing_ci: bool = False
    existing_ci_content: Optional[str] = None
    key_files: dict[str, str] = Field(default_factory=dict)
    directory_tree: str = ""
    notes: str = ""

    def to_prompt_string(self) -> str:
        parts: list[str] = []
        parts.append(f"Languages : {', '.join(self.languages) or 'unknown'}")
        parts.append(f"Frameworks: {', '.join(self.frameworks) or 'none detected'}")
        parts.append(f"Build     : {', '.join(self.build_tools) or 'none detected'}")
        parts.append(f"Tests     : {', '.join(self.test_runners) or 'none detected'}")
        parts.append(f"Docker    : {'yes' if self.has_docker else 'no'}")
        parts.append(f"Existing CI: {'yes' if self.has_existing_ci else 'no'}")
        if self.notes:
            parts.append(f"Notes     : {self.notes}")
        parts.append("\n--- Directory tree ---")
        parts.append(self.directory_tree or "(not available)")
        if self.existing_ci_content:
            parts.append("\n--- Existing CI ---")
            parts.append(self.existing_ci_content[:3_000])
        parts.append("\n--- Key files ---")
        for filename, content in self.key_files.items():
            parts.append(f"\n### {filename}\n{content}")
        return "\n".join(parts)

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)