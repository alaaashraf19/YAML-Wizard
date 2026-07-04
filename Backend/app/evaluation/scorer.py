"""Scoring rubric engine for evaluating generated CI/CD YAML quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

import yaml
from agent.tools.validators import parse_yaml
from agent.tools.validators import validate_github          
from agent.tools.validators import validate_gitlab
from schemas.context_package import ContextPackage

@dataclass
class ScoreBreakdown:
    """Detailed score breakdown across all dimensions."""

    correctness: float = 0.0
    completeness: float = 0.0
    best_practices: float = 0.0
    project_fit: float = 0.0

    correctness_details: List[str] = field(default_factory=list)
    completeness_details: List[str] = field(default_factory=list)
    best_practices_details: List[str] = field(default_factory=list)
    project_fit_details: List[str] = field(default_factory=list)

    weights: Dict[str, float] = field(default_factory=lambda: {
        "correctness": 0.30,
        "completeness": 0.30,
        "best_practices": 0.20,
        "project_fit": 0.20,
    })


    @property
    def overall(self) -> float:
        """Weighted overall score (0-100)."""
        raw = (
            self.correctness * self.weights["correctness"]
            + self.completeness * self.weights["completeness"]
            + self.best_practices * self.weights["best_practices"]
            + self.project_fit * self.weights["project_fit"]
        )
        return round(raw * 100, 1)

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Overall Score: {self.overall}/100",
            f"  Correctness:    {self.correctness:.0%} (weight {self.weights['correctness']:.0%})",
            f"  Completeness:   {self.completeness:.0%} (weight {self.weights['completeness']:.0%})",
            f"  Best Practices: {self.best_practices:.0%} (weight {self.weights['best_practices']:.0%})",
            f"  Project Fit:    {self.project_fit:.0%} (weight {self.weights['project_fit']:.0%})",
        ]
        return "\n".join(lines)


async def score_yaml(
    yaml_content: str,
    platform: str,
    repo_context: ContextPackage,
) -> ScoreBreakdown:
    """Score a generated YAML across all evaluation dimensions."""
    breakdown = ScoreBreakdown()

    try:
        data = yaml.safe_load((yaml_content))
    except yaml.YAMLError:
        data = None

    await _score_correctness(yaml_content, platform, breakdown)
    if data and isinstance(data, dict):
        _score_completeness(data, platform, repo_context, breakdown)
        _score_best_practices(data, platform, breakdown)
        _score_project_fit(data, repo_context, breakdown)

    return breakdown


# ── Correctness ─────────────────────────────────────────────────────────────
import re
def sanitize_github_expressions(yaml_content: str) -> str:
    """Replace ${{ ... }} GitHub Actions expressions with safe placeholder strings.

    PyYAML cannot parse GitHub's template syntax, so we substitute them
    before validation and restore context-awareness afterward.
    """
    return re.sub(r'\$\{\{.*?\}\}', '__GHA_EXPR__', yaml_content)

async def _score_correctness(yaml_content: str, platform: str, bd: ScoreBreakdown) -> None:
    """Score based on passing all 3 validation stages."""
    checks = 3
    passed = 0

    doc, syntax_errors = parse_yaml(sanitize_github_expressions(yaml_content))
    if not syntax_errors:
        passed += 1
        bd.correctness_details.append("✓ Syntax valid")
    else:
        bd.correctness_details.append(f"✗ Syntax errors: {'; '.join(syntax_errors)}")


    semantic_valid = False
    if platform == "github":
        result = validate_github(yaml_content, doc if doc is not None else {})
        semantic_valid = result.get("valid", False)
        if semantic_valid:
            passed += 1
            bd.correctness_details.append("✓ Semantic valid (actionlint + schema)")
        else:
            errors = [e.get("message", "") for e in result.get("errors", [])]
            bd.correctness_details.append(f"✗ Semantic errors: {'; '.join(errors)}")



        try:
            result = await validate_gitlab(yaml_content, doc if doc is not None else {})
        except Exception as e:
            result = {"valid": False, "errors": [{"message": str(e)}]}
        semantic_valid = result.get("valid", False)
        if semantic_valid:
            passed += 1
            bd.correctness_details.append("✓ Semantic valid (GitLab CI lint)")
        else:
            errors = [e.get("message", "") for e in result.get("errors", [])]
        bd.correctness_details.append(f"✗ Semantic errors: {'; '.join(errors)}")

    bd.correctness = passed / checks


# ── Completeness ────────────────────────────────────────────────────────────


def _extract_stages_from_yaml(data: dict) -> List[str]:
    """Dynamically extract all stages / jobs / steps from the YAML."""
    stages = set()

    # GitHub Actions
    if "jobs" in data:
        for job in data["jobs"].values():
            if isinstance(job, dict):
                for step in job.get("steps", []):
                    if isinstance(step, dict):
                        if "uses" in step:
                            stages.add(step["uses"].split("@")[0])
                        if "run" in step:
                            stages.add(step["run"].split()[0] if step["run"] else "")

    # GitLab CI
    for key, value in data.items():
        if isinstance(value, dict) and "script" in value:
            script = value["script"]
            if isinstance(script, list):
                for cmd in script:
                    stages.add(str(cmd).split()[0])
            else:
                stages.add(str(script).split()[0])

    return [s for s in stages if s]



def _score_completeness(data: dict, platform: str, ctx: Any, bd: ScoreBreakdown) -> None:
    """
    Dynamically evaluates how complete the generated pipeline is
    based on the project's ContextPackage.
    """
    yaml_text = yaml.dump(data).lower()
    yaml_stages = _extract_stages_from_yaml(data)

    expected: list[str] = []

    # 1. Core pipeline stages that almost every project should have
    core_stages = ["checkout", "setup", "install"]
    expected.extend(core_stages)

    # 2. Language-specific setup (from ContextPackage)
    for lang in ctx.languages:
        expected.append(f"setup-{lang}")
        expected.append(f"setup_{lang}")

    # 3. Build tools / commands
    for tool in ctx.build_tools:
        expected.append(tool.lower().split()[0])

    for cmd in ctx.build_commands:
        expected.append(cmd.split()[0].lower())

    # 4. Test runners
    for runner in ctx.test_runners:
        expected.append(runner.lower())

    for cmd in ctx.test_commands:
        expected.append(cmd.split()[0].lower())

    # 5. Docker
    if ctx.has_docker:
        expected.extend(["docker", "dockerfile", "build", "push"])

    # 6. Frameworks / services (optional but useful)
    for fw in ctx.frameworks:
        expected.append(fw.lower())
    for svc in ctx.services:
        expected.append(svc.lower())

    # Remove duplicates while preserving order
    seen = set()
    expected = [x for x in expected if not (x in seen or seen.add(x))]

    # Now check presence
    found = 0
    for item in expected:
        if any(item in stage for stage in yaml_stages) or item in yaml_text:
            found += 1
            bd.completeness_details.append(f"✓ Found: {item}")
        else:
            bd.completeness_details.append(f"✗ Missing: {item}")

    bd.completeness = found / len(expected) if expected else 1.0


# ── Best Practices ──────────────────────────────────────────────────────────


def _score_best_practices(data: dict, platform: str, bd: ScoreBreakdown) -> None:
    """Score based on CI/CD best practices."""
    checks = []

    if platform == "github":
        checks = _check_github_best_practices(data, bd)
    elif platform == "gitlab":
        checks = _check_gitlab_best_practices(data, bd)

    passed = sum(checks)
    bd.best_practices = passed / len(checks) if checks else 1.0


def _check_github_best_practices(data: dict, bd: ScoreBreakdown) -> list[bool]:
    """Check GitHub Actions best practices."""
    checks: list[bool] = []
    yaml_text = yaml.dump(data)

    # 1. Pinned action versions (uses @vN or @sha)
    steps = _extract_all_steps(data)
    uses_refs = [s.get("uses", "") for s in steps if s.get("uses")]
    if uses_refs:
        pinned = sum(1 for u in uses_refs if "@" in u)
        ratio = pinned / len(uses_refs)
        ok = ratio >= 0.8
        checks.append(ok)
        bd.best_practices_details.append(
            f"{'✓' if ok else '✗'} Pinned action versions: {pinned}/{len(uses_refs)} ({ratio:.0%})"
        )

    # 3. Has permissions defined
    has_perms = "permissions" in data
    checks.append(has_perms)
    bd.best_practices_details.append(
        f"{'✓' if has_perms else '✗'} Explicit permissions (least-privilege)"
    )

    # 4. Triggers scoped to specific branches
    trigger = data.get("on") or data.get(True, {})
    scoped = False
    if isinstance(trigger, dict):
        for event_config in trigger.values():
            if isinstance(event_config, dict) and "branches" in event_config:
                scoped = True
                break
    checks.append(scoped)
    bd.best_practices_details.append(
        f"{'✓' if scoped else '✗'} Triggers scoped to branches"
    )

    # 5. Job dependency chain (uses 'needs')
    jobs = data.get("jobs", {})
    has_needs = any(
        "needs" in jdef for jdef in jobs.values() if isinstance(jdef, dict)
    )
    if len(jobs) > 1:
        checks.append(has_needs)
        bd.best_practices_details.append(
            f"{'✓' if has_needs else '✗'} Job dependency ordering (needs)"
        )

    # 6. Caching configured
    has_cache = "cache" in yaml_text.lower()
    checks.append(has_cache)
    bd.best_practices_details.append(
        f"{'✓' if has_cache else '✗'} Dependency caching configured"
    )

    # 7. PR trigger present
    trigger_keys = set()
    if isinstance(trigger, dict):
        trigger_keys = set(trigger.keys())
    elif isinstance(trigger, list):
        trigger_keys = set(trigger)
    has_pr = "pull_request" in trigger_keys or "pull_request_target" in trigger_keys
    checks.append(has_pr)
    bd.best_practices_details.append(
        f"{'✓' if has_pr else '✗'} Pull request trigger"
    )

    return checks


def _check_gitlab_best_practices(data: dict, bd: ScoreBreakdown) -> list[bool]:
    """Check GitLab CI best practices."""
    checks: list[bool] = []
    yaml_text = yaml.dump(data)

    # 1. Has stages defined
    has_stages = "stages" in data
    checks.append(has_stages)
    bd.best_practices_details.append(
        f"{'✓' if has_stages else '✗'} Explicit stages defined"
    )

    # 2. Caching configured
    has_cache = "cache" in yaml_text.lower()
    checks.append(has_cache)
    bd.best_practices_details.append(
        f"{'✓' if has_cache else '✗'} Dependency caching"
    )

    # 3. Uses 'rules' instead of deprecated 'only/except'
    jobs = {k: v for k, v in data.items() if isinstance(v, dict) and not k.startswith(".")}
    uses_rules = any("rules" in jdef for jdef in jobs.values() if isinstance(jdef, dict))
    uses_only = any("only" in jdef or "except" in jdef for jdef in jobs.values() if isinstance(jdef, dict))
    ok = uses_rules or not uses_only
    checks.append(ok)
    bd.best_practices_details.append(
        f"{'✓' if ok else '✗'} Uses 'rules' (not deprecated only/except)"
    )

    # 4. Has artifacts for inter-job data
    jobs = {
        k: v for k, v in data.items()
        if isinstance(v, dict) and not k.startswith(".")
    }

    if len(jobs) > 1: #A single-job pipeline doesn't need artifacts or needs
        has_artifacts = "artifacts" in yaml_text.lower()
        checks.append(has_artifacts)
        bd.best_practices_details.append(
            f"{'✓' if has_artifacts else '✗'} Artifacts configured"
        )

    # 5. Uses 'needs' for DAG
    if len(jobs) > 1:
        has_needs = any(
            "needs" in job
            for job in jobs.values()
        )

        checks.append(has_needs)
        bd.best_practices_details.append(
            f"{'✓' if has_needs else '✗'} DAG execution (needs)"
        )

    return checks


# ── Project Fit ─────────────────────────────────────────────────────────────

def _score_project_fit(data: dict, ctx: Any, bd: ScoreBreakdown) -> None:
    """Score how well the generated pipeline matches the detected project."""
    checks: List[bool] = []
    yaml_text = yaml.dump(data).lower()

    def command_present(command: str) -> bool:
        command = command.lower().strip()
        return (
            command in yaml_text or
            " ".join(command.split()[:2]) in yaml_text or
            command.split()[0] in yaml_text
        )

    # 1. Languages
    for lang in ctx.languages:
        found = lang.lower() in yaml_text
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Language: {lang}"
        )

    # 2. Test runners
    for runner in ctx.test_runners:
        found = runner.lower() in yaml_text
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Test runner: {runner}"
        )

    # 3. Docker
    if ctx.has_docker:
        found = "docker" in yaml_text
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Docker support"
        )

    # 4. Build tools / package managers
    for tool in ctx.build_tools:
        normalized = tool.lower().split("/")[0].split()[0]
        found = normalized in yaml_text
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Build tool: {tool}"
        )

    # 5. Frameworks
    for framework in ctx.frameworks:
        found = framework.lower() in yaml_text
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Framework: {framework}"
        )

    # 6. Build commands
    for cmd in ctx.build_commands:
        found = command_present(cmd)
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Build command: {cmd}"
        )

    # 7. Test commands
    for cmd in ctx.test_commands:
        found = command_present(cmd)
        checks.append(found)
        bd.project_fit_details.append(
            f"{'✓' if found else '✗'} Test command: {cmd}"
        )

    bd.project_fit = sum(checks) / len(checks) if checks else 1.0


# ── Helpers ─────────────────────────────────────────────────────────────────


def _extract_all_steps(data: dict) -> list[dict]:
    """Extract all steps from all jobs in a GitHub Actions workflow."""
    steps = []
    for job_def in data.get("jobs", {}).values():
        if isinstance(job_def, dict):
            for step in job_def.get("steps", []):
                if isinstance(step, dict):
                    steps.append(step)
    return steps
