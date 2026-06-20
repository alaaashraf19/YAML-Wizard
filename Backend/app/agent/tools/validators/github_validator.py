from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
GITHUB_SCHEMA_PATH = SCHEMAS_DIR / "github-workflow.json"

ACTIONLINT_BINARY = (Path(__file__).resolve().parents[1]/ "bin"/ ("actionlint.exe" if os.name == "nt" else "actionlint"))
ACTIONLINT_TIMEOUT_SEC = 20


# Validates GitHub Actions YAML via actionlint, falling back to the JSON schema. returns a report dict (primary_source, fallback_used/reason, errors).
def validate_github(yaml_content: str, doc: Any) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []

    primary = "actionlint"
    fallback_used = False
    fallback_reason: Optional[str] = None

    if ACTIONLINT_BINARY.is_file():
        al_errors, run_error = run_actionlint(str(ACTIONLINT_BINARY), yaml_content)
        if run_error is None:
            errors.extend(al_errors)
        else:
            primary = "json-schema"
            fallback_used = True
            fallback_reason = f"actionlint invocation failed: {run_error}. used JSON schema instead"
            errors.extend(run_schema(doc))
    else:
        primary = "json-schema"
        fallback_used = True
        fallback_reason = (f"actionlint binary not found. used JSON schema instead")
        errors.extend(run_schema(doc))

    return {
        "primary_source": primary,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "errors": errors,
    }

# Runs the actionlint binary on the YAML and parses its JSON output. returns (error list, run-error message | None).
def run_actionlint(binary: str, yaml_content: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    tmp_path: Optional[str] = None
    try:
        #action lint reads from files, so we create a temp file that we handle its deletion manually as the behaviour of tempfiles differs from an Os to another
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False, encoding="utf-8", newline="") as tmp:
            tmp.write(yaml_content)
            tmp_path = tmp.name

        proc = subprocess.run(
            [binary, "-format", "{{json .}}", "-no-color", tmp_path],
            capture_output=True,
            text=True,
            timeout=ACTIONLINT_TIMEOUT_SEC,
            check=False,
        )
    
    except FileNotFoundError as exc:
        return [], f"binary not executable: {exc}"
    except subprocess.TimeoutExpired:
        return [], f"timed out after {ACTIONLINT_TIMEOUT_SEC}s"
    except OSError as exc:
        return [], f"OS error: {exc}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    # or "" => in case python failed to capture the json output of the linter correctly
    raw = (proc.stdout or "").strip()
    if not raw: #output is empty and linter passed successfully
        if proc.returncode == 0:
            return [], None
        return [], f"non-zero exit ({proc.returncode}) with no JSON output: {proc.stderr.strip()[:200]}"

    items = json.loads(raw)
    errors: List[Dict[str, Any]] = []
    for it in items if isinstance(items, list) else []:
        errors.append(
            {
                "source": "actionlint",
                "level": "semantic",
                "line": it.get("line"),
                "col": it.get("column"),
                "rule": it.get("kind"),
                "message": it.get("message", "").strip(),
                "snippet": (it.get("snippet") or "").strip() or None,
            }
        )
    return errors, None


def run_schema(doc: Any) -> List[Dict[str, Any]]:
    if not GITHUB_SCHEMA_PATH.is_file():
        return [
            {
                "source": "json-schema",
                "level": "semantic",
                "message": f"schema not available at {GITHUB_SCHEMA_PATH}",
            }
        ]
    try:
        with open(GITHUB_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        return [
            {
                "source": "json-schema",
                "level": "semantic",
                "message": f"could not load schema at {GITHUB_SCHEMA_PATH}: {exc}",
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
        for p in err.absolute_path: #err.absolute_path = deque(['jobs', 'build', 'steps', 1, 'run'])
            path += f"[{p}]" if isinstance(p, int) else f".{p}" # converted to readable json line => $.jobs.build.steps[1].run starting from the json root
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
