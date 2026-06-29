"""Ground truth comparator — structurally compare generated YAML against a reference."""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml



@dataclass
class ComparisonResult:
    """Result of comparing generated YAML against ground truth."""

    # Scores (0.0 - 1.0)
    job_coverage: float = 0.0
    step_coverage: float = 0.0
    trigger_coverage: float = 0.0
    structural_similarity: float = 0.0

    details: list[str] = field(default_factory=list)

    # Jobs/steps only in generated (additions)
    additions: list[str] = field(default_factory=list)
    # Jobs/steps only in ground truth (missing)
    missing: list[str] = field(default_factory=list)

    @property
    def overall(self) -> float:
        """Overall similarity score (0-100)."""
        raw = (
            self.job_coverage * 0.35
            + self.step_coverage * 0.30
            + self.trigger_coverage * 0.15
            + self.structural_similarity * 0.20
        )
        return round(raw * 100, 1)

    def summary(self) -> str:
        lines = [
            f"Ground Truth Comparison: {self.overall}/100",
            f"  Job Coverage:       {self.job_coverage:.0%}",
            f"  Step Coverage:      {self.step_coverage:.0%}",
            f"  Trigger Coverage:   {self.trigger_coverage:.0%}",
            f"  Structural Sim.:    {self.structural_similarity:.0%}",
        ]
        if self.additions:
            lines.append(f"  Additions (ours):   {', '.join(self.additions)}")
        if self.missing:
            lines.append(f"  Missing (vs ref):   {', '.join(self.missing)}")
        return "\n".join(lines)
import re 

def sanitize_github_expressions(yaml_content: str) -> str:
    """Replace ${{ ... }} GitHub Actions expressions with safe placeholder strings.

    PyYAML cannot parse GitHub's template syntax, so we substitute them
    before validation and restore context-awareness afterward.
    """
    return re.sub(r'\$\{\{.*?\}\}', '__GHA_EXPR__', yaml_content)

def compare_yaml(
    generated: str,
    ground_truth: str,
    platform: str,
) -> ComparisonResult:
    """Compare generated YAML structurally against a ground-truth reference."""
    result = ComparisonResult()

    try:
        gen_data = yaml.safe_load(sanitize_github_expressions(generated))
        ref_data = yaml.safe_load(sanitize_github_expressions(ground_truth))
    except yaml.YAMLError:
        result.details.append("✗ Failed to parse one or both YAML files")
        return result

    if not isinstance(gen_data, dict) or not isinstance(ref_data, dict):
        result.details.append("✗ One or both YAML files are not valid mappings")
        return result

    if platform == "github":
        _compare_github(gen_data, ref_data, result)
    elif platform == "gitlab":
        _compare_gitlab(gen_data, ref_data, result)

    return result


# ── GitHub Actions comparison ───────────────────────────────────────────────


def _compare_github(gen: dict, ref: dict, result: ComparisonResult) -> None:
    """Compare two GitHub Actions workflows."""
    _compare_triggers(gen, ref, result)
    _compare_github_jobs(gen, ref, result)
    _compare_structural(gen, ref, result)


def _compare_triggers(gen: dict, ref: dict, result: ComparisonResult) -> None:
    """Compare trigger configurations."""
    gen_triggers = _extract_triggers(gen)
    ref_triggers = _extract_triggers(ref)

    if not ref_triggers:
        result.trigger_coverage = 1.0
        result.details.append("⚠ Reference has no triggers to compare")
        return

    covered = gen_triggers & ref_triggers
    result.trigger_coverage = len(covered) / len(ref_triggers) if ref_triggers else 1.0

    extra = gen_triggers - ref_triggers
    missing = ref_triggers - gen_triggers

    for t in covered:
        result.details.append(f"✓ Trigger '{t}' present in both")
    for t in extra:
        result.details.append(f"+ Trigger '{t}' added (not in reference)")
        result.additions.append(f"trigger:{t}")
    for t in missing:
        result.details.append(f"✗ Trigger '{t}' missing (in reference)")
        result.missing.append(f"trigger:{t}")


def _extract_triggers(data: dict) -> set[str]:
    """Extract trigger event names from a workflow."""
    trigger = data.get("on") or data.get(True, {})
    if isinstance(trigger, str):
        return {trigger}
    elif isinstance(trigger, list):
        return set(trigger)
    elif isinstance(trigger, dict):
        return set(trigger.keys())
    return set()


def _compare_github_jobs(gen: dict, ref: dict, result: ComparisonResult) -> None:
    """Compare jobs between generated and reference."""
    gen_jobs = gen.get("jobs", {})
    ref_jobs = ref.get("jobs", {})

    if not isinstance(gen_jobs, dict) or not isinstance(ref_jobs, dict):
        return

    # Normalize job names for fuzzy matching (lowercase)
    gen_names = set(j.lower() for j in gen_jobs)
    ref_names = set(j.lower() for j in ref_jobs)

    # Also match by job 'name' field
    gen_labels = set()
    ref_labels = set()
    for jdef in gen_jobs.values():
        if isinstance(jdef, dict) and "name" in jdef:
            gen_labels.add(jdef["name"].lower())
    for jdef in ref_jobs.values():
        if isinstance(jdef, dict) and "name" in jdef:
            ref_labels.add(jdef["name"].lower())

    # Combine keys and labels for matching
    gen_all = gen_names | gen_labels
    ref_all = ref_names | ref_labels

    covered = ref_all & gen_all
    extra = gen_all - ref_all
    missing_set = ref_all - gen_all

    result.job_coverage = len(covered) / len(ref_all) if ref_all else 1.0

    for j in covered:
        result.details.append(f"✓ Job '{j}' present in both")
    for j in extra:
        result.details.append(f"+ Job '{j}' added (not in reference)")
        result.additions.append(f"job:{j}")
    for j in missing_set:
        result.details.append(f"✗ Job '{j}' missing (in reference)")
        result.missing.append(f"job:{j}")

    # Step-level comparison for matching jobs
    _compare_steps_across_jobs(gen_jobs, ref_jobs, result)


def _compare_steps_across_jobs(gen_jobs: dict, ref_jobs: dict, result: ComparisonResult) -> None:
    """Compare steps between matching jobs."""
    gen_actions = _extract_all_actions(gen_jobs)
    ref_actions = _extract_all_actions(ref_jobs)

    gen_commands = _extract_all_commands(gen_jobs)
    ref_commands = _extract_all_commands(ref_jobs)

    # Action coverage
    if ref_actions:
        covered = ref_actions & gen_actions
        action_coverage = len(covered) / len(ref_actions)
    else:
        action_coverage = 1.0

    # Command keyword coverage
    if ref_commands:
        covered_cmds = ref_commands & gen_commands
        cmd_coverage = len(covered_cmds) / len(ref_commands)
    else:
        cmd_coverage = 1.0

    result.step_coverage = (action_coverage + cmd_coverage) / 2

    result.details.append(f"  Action coverage: {action_coverage:.0%} (actions used in both)")
    result.details.append(f"  Command coverage: {cmd_coverage:.0%} (command keywords in both)")


def _extract_all_actions(jobs: dict) -> set[str]:
    """Extract all 'uses' action references from jobs."""
    actions = set()
    for jdef in jobs.values():
        if not isinstance(jdef, dict):
            continue
        for step in jdef.get("steps", []):
            if isinstance(step, dict) and "uses" in step:
                # Normalize: strip version
                action = step["uses"].split("@")[0].lower()
                actions.add(action)
    return actions


def _extract_all_commands(jobs: dict) -> set[str]:
    """Extract command keywords from 'run' steps."""
    keywords = set()
    for jdef in jobs.values():
        if not isinstance(jdef, dict):
            continue
        for step in jdef.get("steps", []):
            if isinstance(step, dict) and "run" in step:
                run = str(step["run"]).lower()
                # Extract meaningful command keywords
                for word in run.split():
                    word = word.strip("|-;\"'")
                    if len(word) > 2 and not word.startswith("#") and not word.startswith("$"):
                        keywords.add(word)
    return keywords


# ── GitLab CI comparison ───────────────────────────────────────────────────


def _compare_gitlab(gen: dict, ref: dict, result: ComparisonResult) -> None:
    """Compare two GitLab CI pipelines."""
    reserved = {"stages", "variables", "default", "include", "image", "services",
                "before_script", "after_script", "cache", "workflow", "pages"}

    gen_jobs = {k: v for k, v in gen.items() if k not in reserved and isinstance(v, dict) and not k.startswith(".")}
    ref_jobs = {k: v for k, v in ref.items() if k not in reserved and isinstance(v, dict) and not k.startswith(".")}

    gen_names = set(j.lower() for j in gen_jobs)
    ref_names = set(j.lower() for j in ref_jobs)

    covered = ref_names & gen_names
    result.job_coverage = len(covered) / len(ref_names) if ref_names else 1.0

    for j in covered:
        result.details.append(f"✓ Job '{j}' present in both")
    for j in gen_names - ref_names:
        result.details.append(f"+ Job '{j}' added")
        result.additions.append(f"job:{j}")
    for j in ref_names - gen_names:
        result.details.append(f"✗ Job '{j}' missing")
        result.missing.append(f"job:{j}")

    # Compare stages
    gen_stages = set(gen.get("stages", []))
    ref_stages = set(ref.get("stages", []))
    if ref_stages:
        stage_covered = ref_stages & gen_stages
        result.trigger_coverage = len(stage_covered) / len(ref_stages)
    else:
        result.trigger_coverage = 1.0

    # Script keyword comparison
    gen_scripts = _extract_gitlab_scripts(gen_jobs)
    ref_scripts = _extract_gitlab_scripts(ref_jobs)
    if ref_scripts:
        script_covered = ref_scripts & gen_scripts
        result.step_coverage = len(script_covered) / len(ref_scripts)
    else:
        result.step_coverage = 1.0

    _compare_structural(gen, ref, result)


def _extract_gitlab_scripts(jobs: dict) -> set[str]:
    """Extract script command keywords from GitLab CI jobs."""
    keywords = set()
    for jdef in jobs.values():
        if not isinstance(jdef, dict):
            continue
        scripts = jdef.get("script", [])
        if isinstance(scripts, str):
            scripts = [scripts]
        for cmd in scripts:
            for word in str(cmd).lower().split():
                word = word.strip("|-;\"'")
                if len(word) > 2 and not word.startswith("#"):
                    keywords.add(word)
    return keywords


# ── Structural similarity ──────────────────────────────────────────────────


def _compare_structural(gen: dict, ref: dict, result: ComparisonResult) -> None:
    """Compare top-level structure similarity."""
    gen_keys = set(str(k).lower() for k in gen.keys())
    ref_keys = set(str(k).lower() for k in ref.keys())

    all_keys = gen_keys | ref_keys
    common = gen_keys & ref_keys

    result.structural_similarity = len(common) / len(all_keys) if all_keys else 1.0
    result.details.append(
        f"  Structural: {len(common)}/{len(all_keys)} top-level keys in common"
    )
