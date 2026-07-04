from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

GROQ_REVIEW_MODEL = os.getenv("GROQ_REVIEW_MODEL", "openai/gpt-oss-120b")
MAX_YAML_CHARS = 16000

ALLOWED_LEVELS = {"info", "warning", "critical"}
ALLOWED_CATEGORIES = {
    "security",
    "performance",
    "reliability",
    "best-practice",
    "maintainability",
    "correctness",
    "other",
}

SYSTEM_PROMPT = """You are a senior DevOps / CI-CD security reviewer. You are given a CI/CD pipeline YAML that has ALREADY passed syntactic and schema validation (pyyaml, actionlint, gitlab-ci-lint, json-schema). Your job is to find higher-level problems those linters do NOT catch and report them as actionable warnings.

Look in particular for:
- Security: unpinned/floating action or image versions (use a commit SHA or pinned tag), secrets hard-coded in plaintext, overly broad token permissions (missing least-privilege `permissions:`), dangerous triggers (e.g. pull_request_target combined with checkout of untrusted code), script injection from untrusted ${{ github.event.* }} / variable input, use of curl|bash, missing `--frozen`/lockfile installs.
- Reliability: missing job/step timeouts, no concurrency/cancel-in-progress control, no retry on flaky network steps, jobs that swallow failures.
- Performance: missing dependency caching, no shallow clone where helpful, redundant or duplicated steps, unnecessary matrix expansion.
- Maintainability: duplicated config that should be factored out, unclear stage/needs wiring, missing names on steps.

Rules:
- Only report genuine, concrete issues. If the pipeline is clean, return an empty list. Do NOT invent problems and do NOT repeat pure syntax/schema errors a linter already reports.
- Be specific: reference the affected job and what to change.
- Return STRICT JSON only, no markdown, no prose outside the JSON."""


OUTPUT_SCHEMA_HINT = """Return ONLY a JSON object of this exact shape:
{"warnings": [
  {"level": "info|warning|critical",
   "category": "security|performance|reliability|best-practice|maintainability|correctness|other",
   "job": "<affected job id, or \"workflow\" for pipeline-wide issues>",
   "title": "<short title>",
   "message": "<what is wrong and why it matters>",
   "suggestion": "<concrete fix>"}
]}
If there is nothing worth flagging, return {"warnings": []}."""


def truncate_yaml(text: str) -> str:
    if len(text) <= MAX_YAML_CHARS:
        return text
    head = text[: MAX_YAML_CHARS - 200]
    return head + f"\n[truncated, original length: {len(text)} chars]\n"


def build_user_prompt(content: str, platform: str) -> str:
    target = "GitHub Actions" if platform == "github" else "GitLab CI/CD"
    return (
        f"Platform: {target}\n\n"
        f"{OUTPUT_SCHEMA_HINT}\n\n"
        "Review this pipeline YAML:\n"
        "```yaml\n"
        f"{truncate_yaml(content.rstrip())}\n"
        "```\n"
        "Output:"
    )


def normalize_warning(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    message = str(raw.get("message") or raw.get("title") or "").strip()
    if not message:
        return None

    level = str(raw.get("level") or "warning").strip().lower()
    if level not in ALLOWED_LEVELS:
        level = "warning"

    category = str(raw.get("category") or "best-practice").strip().lower()
    if category not in ALLOWED_CATEGORIES:
        category = "other"

    job = raw.get("job")
    job = str(job).strip() if job not in (None, "", "null") else "workflow"

    title = str(raw.get("title") or "").strip() or None
    suggestion = str(raw.get("suggestion") or "").strip() or None

    return {
        "source": "groq-ai-review",
        "level": level,
        "category": category,
        "job": job,
        "title": title,
        "message": message,
        "suggestion": suggestion,
    }


def parse_warnings(text: str) -> list[dict[str, Any]]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    if not text:
        return []

    obj = json.loads(text)
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict):
        items = obj.get("warnings", [])
    else:
        items = []
    if not isinstance(items, list):
        return []

    out: list[dict[str, Any]] = []
    for item in items:
        normalized = normalize_warning(item)
        if normalized is not None:
            out.append(normalized)
    return out


async def review_pipeline(content: str, platform: str) -> dict[str, Any]:
    target = (platform or "").lower()
    result: dict[str, Any] = {
        "available": False,
        "model": GROQ_REVIEW_MODEL,
        "warnings": [],
        "error": None,
    }

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        result["error"] = "GROQ_API_KEY is not set; AI review was skipped."
        return result

    if not content or not content.strip():
        result["error"] = "Empty pipeline content; AI review was skipped."
        return result

    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=api_key)
        completion = await client.chat.completions.create(
            model=GROQ_REVIEW_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(content, target)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw_text = completion.choices[0].message.content or ""
        result["warnings"] = parse_warnings(raw_text)
        result["available"] = True
    except Exception as exc:  # network / auth / model / parse failures
        result["error"] = f"AI review failed: {exc}"

    return result
