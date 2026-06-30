from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx


SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
GITLAB_SCHEMA_PATH = SCHEMAS_DIR / "gitlab-ci.json"

CI_LINT_TIMEOUT_SEC = 20


# call_gitlab_ci_lint or the schema , returns a report dict (primary_source, fallback_used/reason, api_endpoint, jobs, errors, warnings).
async def validate_gitlab(yaml_content: str, doc: Any, connection: Any = None, db: Any = None, project_id: Any = None) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    primary = "gitlab-ci-lint"
    fallback_used = False
    fallback_reason: Optional[str] = None
    endpoint_used: Optional[str] = None
    jobs_summary: List[Dict[str, Any]] = []

    api_result, api_error, endpoint_used = await call_gitlab_ci_lint(yaml_content, connection, db, project_id)

    if api_error is None and api_result is not None:
        for msg in api_result.get("errors", []) or []:
            errors.append(apiError(msg, level="semantic"))
        for msg in api_result.get("warnings", []) or []:
            warnings.append(apiError(msg, level="warning"))
        jobs_summary, job_warnings = summarize_jobs(api_result.get("jobs"))
        warnings.extend(job_warnings)
    else:
        primary = "json-schema"
        fallback_used = True
        attempted = f" (attempted {endpoint_used})" if endpoint_used else ""
        fallback_reason = f"GitLab CI lint unavailable{attempted}: {api_error}; used JSON schema instead"
        errors.extend(run_schema(doc))

    return {
        "primary_source": primary,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "api_endpoint": endpoint_used,
        "jobs": jobs_summary,
        "errors": errors,
        "warnings": warnings,
    }


# Sends the YAML to GitLab's project/ci/lint endpoint. it returns result,execution error,used URL.
async def call_gitlab_ci_lint(yaml_content: str, connection: Any = None, db: Any = None, project_id: Any = None) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:

    token, auth_headers, token_error = await retrieve_gitlab_token(connection, db)
    if token_error is not None:
        return None, token_error, None

    if not project_id:
        return None, "no GitLab project id available for this repository", None

    url = f"https://gitlab.com/api/v4/projects/{project_id}/ci/lint"
    payload = {"content": yaml_content, "include_jobs": True}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=auth_headers, timeout=CI_LINT_TIMEOUT_SEC)
    except httpx.TimeoutException:
        return None, f"timed out after {CI_LINT_TIMEOUT_SEC}s", url
    except httpx.HTTPError as exc:
        return None, f"HTTP error: {exc}", url

    if resp.status_code >= 400:
        return None, f"HTTP {resp.status_code}: {resp.text.strip()[:200]}", url

    try:
        body = resp.json()
    except ValueError as exc:
        return None, f"non-JSON response: {exc}", url

    return body, None, url


# gets the user's GitLab token. returns (token, auth-header error message).
async def retrieve_gitlab_token(connection: Any, db: Any,) -> Tuple[Optional[str], Optional[Dict[str, str]], Optional[str]]:
    if connection is None or db is None:
        return None, None, "no connected GitLab account available to obtain a token"

    try:
        from services.platform_connectors.gitlab_connect import GitLabConnector

        token = await GitLabConnector().get_valid_token(connection, db)
    except Exception as exc: #db error
        return None, None, f"could not obtain GitLab token from connection: {exc}"

    if not token: 
        return None, None, "no GitLab token available from the connected account"

    return token, {"Authorization": f"Bearer {token}"}, None



def apiError(message: str, level: str) -> Dict[str, Any]:
    return {
        "source": "gitlab-ci-lint",
        "level": level,
        "message": message,
    }


# Builds a job-check warning. returns a dict with source, level, and message.
def jobWarning(message: str) -> Dict[str, Any]:
    return {
        "source": "gitlab-jobs-check",
        "level": "warning",
        "message": message,
    }


# collects GitLab lint jobs array and gets warnings for empty jobs. i returns (job list, warning list).
def summarize_jobs(jobs: Optional[List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    summary: List[Dict[str, Any]] = [
        {
            "name": job.get("name"),
            "stage": job.get("stage"),
            "when": job.get("when"),
            "allow_failure": job.get("allow_failure"), #if ture the job failing doesn't stop the whole pipeline
        }
        for job in (jobs or [])
    ]

    warnings: List[Dict[str, Any]] = []
    if not summary:
        warnings.append(jobWarning("pipeline produces no jobs"))
    return summary, warnings


def run_schema(doc: Any) -> List[Dict[str, Any]]:
    if not GITLAB_SCHEMA_PATH.is_file():
        return [
            {
                "source": "json-schema",
                "level": "semantic",
                "message": f"schema not available at {GITLAB_SCHEMA_PATH}",
            }
        ]
    try:
        with open(GITLAB_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return [
            {
                "source": "json-schema",
                "level": "semantic",
                "message": f"could not load schema at {GITLAB_SCHEMA_PATH}: {exc}",
            }
        ]

    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        return [
            {
                "source": "json-schema",
                "level": "semantic",
                "message": f"jsonschema not installed: {exc}",
            }
        ]

    validator = Draft7Validator(schema)
    errors: List[Dict[str, Any]] = []
    for err in validator.iter_errors(doc):
        path = "$"
        for p in err.absolute_path:
            path += f"[{p}]" if isinstance(p, int) else f".{p}"
        errors.append(
            {
                "source": "json-schema",
                "level": "semantic",
                "path": path,
                "message": err.message,
                "validator": err.validator,
            }
        )
    return errors