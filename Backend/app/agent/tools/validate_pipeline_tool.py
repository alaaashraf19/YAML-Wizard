from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from agent.tools.validators import parse_yaml, validate_github, validate_gitlab


@tool
async def validate_pipeline_tool(
    yaml_content: str, target: Literal["github", "gitlab"], config: RunnableConfig = None) -> str:
    """Validate a CI/CD pipeline YAML both syntactically and semantically. Call this on
    every pipeline YAML you produce before returning it to the user.

    Two layers:
    - Syntactic: PyYAML parses the content (errors tagged source="pyyaml" with line/col).
      If syntax fails, semantic checks are skipped.
    - Semantic, per target: target="github" -> actionlint (primary) else JSON-Schema fallback;
      target="gitlab" -> GitLab /api/v4/ci/lint (primary) else JSON-Schema fallback.

    Every error has a "source" (pyyaml | actionlint | gitlab-ci-lint | json-schema) plus the
    best locator for it (line/col for pyyaml/actionlint, JSON-pointer path for schema).

    Args:
        yaml_content: The full YAML text of the pipeline to validate.
        target: "github" (GitHub Actions) or "gitlab" (GitLab CI).

    Returns a JSON string of shape:
        {"valid": bool, "target": "github"|"gitlab",
         "primary_source": "actionlint"|"gitlab-ci-lint"|"json-schema"|"pyyaml",
         "fallback_used": bool, "fallback_reason": str|null,
         "summary": "<n> error(s), <m> warning(s)",
         "errors": [{"source":..., "level":..., ...}], "warnings": [ ... ]}
    If "valid" is false, read the errors, fix the YAML, and call again; if true, return it to the user.
    """
    print("i am inside validate")
    configurable = (config or {}).get("configurable", {})
    report = await build_report(
        yaml_content,
        target,
        connection=configurable.get("gitlab_connection"),
        db=configurable.get("db"),
        project_id=configurable.get("gitlab_project_id"),
    )
    log_validation_report(report, target)
    return json.dumps(report, indent=2, ensure_ascii=False)


async def build_report(yaml_content: str, target: str, connection: Any = None, db: Any = None, project_id: Any = None,) -> Dict[str, Any]:
    if target not in ("github", "gitlab"):
        return {
            "valid": False,
            "target": target,
            "primary_source": None,
            "fallback_used": False,
            "fallback_reason": None,
            "summary": "1 error(s), 0 warning(s)",
            "errors": [
                {
                    "source": "validate_pipeline_tool",
                    "level": "input",
                    "message": f"unknown target {target}; expected 'github' or 'gitlab'",
                }
            ],
            "warnings": [],
        }

    doc, syntax_errors = parse_yaml(yaml_content)
    if syntax_errors:
        return {
            "valid": False,
            "target": target,
            "primary_source": "pyyaml",
            "fallback_used": False,
            "fallback_reason": None,
            "summary": f"{len(syntax_errors)} error(s), 0 warning(s)",
            "errors": syntax_errors,
            "warnings": [],
            "note": "Semantic validation is skipped because YAML was not parsed correctly.",
        }

    if doc is None:
        return {
            "valid": False,
            "target": target,
            "primary_source": "pyyaml",
            "fallback_used": False,
            "fallback_reason": None,
            "summary": "1 error(s), 0 warning(s)",
            "errors": [
                {
                    "source": "pyyaml",
                    "level": "syntax",
                    "message": "YAML parsed to an empty document",
                }
            ],
            "warnings": [],
        }

    if target == "github":
        result = validate_github(yaml_content, doc)
    else:
        result = await validate_gitlab(yaml_content, doc, connection, db, project_id)

    errors: List[Dict[str, Any]] = result.get("errors", [])
    warnings: List[Dict[str, Any]] = result.get("warnings", [])

    report: Dict[str, Any] = {
        "valid": len(errors) == 0,
        "target": target,
        "primary_source": result.get("primary_source"),
        "fallback_used": result.get("fallback_used", False),
        "fallback_reason": result.get("fallback_reason"),
        "summary": f"{len(errors)} error(s), {len(warnings)} warning(s)",
        "errors": errors,
        "warnings": warnings,
    }
    if target == "gitlab":
        report["api_endpoint"] = result.get("api_endpoint")
        report["jobs"] = result.get("jobs", [])
        # print(report)
    
    print("report in validate", report)
    return report


REPORT_LOG_PATH = Path(__file__).resolve().parents[3] / "logs" / "validation_reports.jsonl"


def log_validation_report(report: Dict[str, Any], target: str) -> None:
    path = REPORT_LOG_PATH
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": target,
        **report,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"could not write report to {path}: {exc}")
