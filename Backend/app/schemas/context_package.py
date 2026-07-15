"""
ContextPackage — structured output of any repo context agent (GitHub or GitLab).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, model_validator


class TestRunnerInfo(BaseModel):
    runner: str
    ecosystem: str
    detected_via: str


class TestReportInfo(BaseModel):
    format: str
    path: str


class ContextPackage(BaseModel):
    # ── core detections ────────────────────────────────────────────────────
    languages:           list[str]          = Field(default_factory=list)
    frameworks:          list[str]          = Field(default_factory=list)
    build_tools:         list[str]          = Field(default_factory=list)

    # ── test runners ───────────────────────────────────────────────────────
    test_runners:        list[str]          = Field(default_factory=list)
    test_runner_details: list[TestRunnerInfo] = Field(default_factory=list)

    # ── test reports ───────────────────────────────────────────────────────
    has_test_reports:    bool               = False
    report_formats:      list[str]          = Field(default_factory=list)
    test_reports:        list[TestReportInfo] = Field(default_factory=list)

    # ── CI / Docker ────────────────────────────────────────────────────────
    has_docker:          bool               = False
    has_existing_ci:     bool               = False
    existing_ci_content: Optional[str]      = None

    # ── repo structure ─────────────────────────────────────────────────────
    key_files:           dict[str, str]     = Field(default_factory=dict)
    directory_tree:      str                = ""

    # ── NEW: branch + commands + env ───────────────────────────────────────
    default_branch:      str                = "main"
    env_vars:            list[str]          = Field(default_factory=list)
    services:            list[str]          = Field(default_factory=list)
    test_commands:       list[str]          = Field(default_factory=list)
    build_commands:      list[str]          = Field(default_factory=list)

    notes:               str                = ""

    # ── validators ─────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def _sync_report_formats(self) -> "ContextPackage":
        if self.test_reports and not self.report_formats:
            self.report_formats = [r.format for r in self.test_reports]
        if self.test_reports:
            self.has_test_reports = True
        return self

    # ── helpers ────────────────────────────────────────────────────────────
    def to_prompt_string(self) -> str:
        parts: list[str] = []
        parts.append(f"Languages     : {', '.join(self.languages) or 'unknown'}")
        parts.append(f"Frameworks    : {', '.join(self.frameworks) or 'none detected'}")
        parts.append(f"Build tools   : {', '.join(self.build_tools) or 'none detected'}")
        parts.append(f"Test runners  : {', '.join(self.test_runners) or 'none detected'}")
        parts.append(f"Test commands : {'; '.join(self.test_commands) or 'not found'}")
        parts.append(f"Build commands: {'; '.join(self.build_commands) or 'not found'}")
        parts.append(f"Reports       : {'yes — ' + ', '.join(self.report_formats) if self.has_test_reports else 'no'}")
        parts.append(f"Docker        : {'yes' if self.has_docker else 'no'}")
        parts.append(f"Services      : {', '.join(self.services) or 'none'}")
        parts.append(f"Env vars      : {', '.join(self.env_vars) or 'none detected'}")
        parts.append(f"Default branch: {self.default_branch}")
        parts.append(f"Existing CI   : {'yes' if self.has_existing_ci else 'no'}")
        if self.notes:
            parts.append(f"Notes         : {self.notes}")
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
