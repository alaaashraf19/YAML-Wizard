from agent.prompts import GENERATE_PROMPT

from langchain_core.tools import tool
from schemas.context_package import ContextPackage
from langchain_core.runnables import RunnableConfig

@tool
async def generate_yaml_tool(repo_context: ContextPackage,user_prompt: str, previous_yaml: str | None = None,
                            config: RunnableConfig = None) -> str:
    """
    Generate a GitHub Actions or GitLab CI YAML pipeline
    based on repository context and user requirements.

    Args:
        repo_context: Structured information about the repository (languages, frameworks, existing CI, etc.).
        user_prompt: The user's natural language description of their CI/CD needs.
        previous_yaml: Optional existing YAML content to use as a starting point or reference.
    Returns:
        Tuple of (yaml_content, description)
    """
    configurable = (config or {}).get("configurable", {})
    context = configurable.get("context")
    repo_context = context.repo_context if context else None
    repo = context.repo if context else None
    print(repo_context)
    context_summary = build_context_summary(repo_context)

    previous_yaml_section = ""
    if previous_yaml:
        previous_yaml_section = (
            f"The user already has the following YAML that should be used as a starting point "
            f"or edited according to their request:\n```yaml\n{previous_yaml}\n```"
        )

    return GENERATE_PROMPT.format(
        platform=repo.platform,
        repo_url=repo.url,
        repo_context=context_summary,
        user_prompt=user_prompt,
        previous_yaml_section=previous_yaml_section,
    )


def build_context_summary(ctx: ContextPackage) -> str:
    """Build a human-readable summary of the repo context."""

    lines = []

    # ── Core stack ─────────────────────────────────────────────
    lines.append(f"Languages: {', '.join(ctx.languages) if ctx.languages else 'unknown'}")

    lines.append(f"Frameworks: {', '.join(ctx.frameworks) if ctx.frameworks else 'none detected'}")

    lines.append( f"Build tools: {', '.join(ctx.build_tools) if ctx.build_tools else 'none detected'}")

    # ── Testing ────────────────────────────────────────────────
    lines.append( f"Test runners: {', '.join(ctx.test_runners) if ctx.test_runners else 'none detected'}")
    
    if ctx.test_runner_details:
        runner_details = ", ".join(
            f"{r.runner} ({r.ecosystem}, detected via {r.detected_via})"
            for r in ctx.test_runner_details
        )
        lines.append(f"Test runner details: {runner_details}")
    else:
        lines.append("Test runner details: none")

    lines.append(f"Test commands: {', '.join(ctx.test_commands) if ctx.test_commands else 'none'}")

    # ── Build / Runtime ────────────────────────────────────────
    lines.append(f"Build commands: {', '.join(ctx.build_commands) if ctx.build_commands else 'none'}")

    lines.append(f"Environment variables: {', '.join(ctx.env_vars) if ctx.env_vars else 'none'}")

    lines.append(f"Services: {', '.join(ctx.services) if ctx.services else 'none'}")

    # ── CI / Docker ────────────────────────────────────────────
    lines.append(f"Has Docker: {'yes' if ctx.has_docker else 'no'}")
    lines.append(f"Has existing CI: {'yes' if ctx.has_existing_ci else 'no'}")

    if ctx.existing_ci_content:
        truncated_ci = (
            ctx.existing_ci_content[:5000] + "..."
            if len(ctx.existing_ci_content) > 5000
            else ctx.existing_ci_content
        )
        lines.append(f"\nExisting CI configuration:\n{truncated_ci}")

    # ── Reports ────────────────────────────────────────────────
    lines.append(f"Has test reports: {'yes' if ctx.has_test_reports else 'no'}")

    lines.append(f"Report formats: {', '.join(ctx.report_formats) if ctx.report_formats else 'none'}")

    # ── Structure ──────────────────────────────────────────────
    lines.append(f"\nDirectory structure:\n{ctx.directory_tree}")

    if ctx.key_files:
        lines.append("\nKey configuration files:")
        for filename, content in ctx.key_files.items():
            if content and content != "[empty]":
                truncated = (
                    content[:3000] + "..."
                    if len(content) > 3000
                    else content
                )
                lines.append(f"\n--- {filename} ---\n{truncated}")

    return "\n".join(lines)

import json
def parse_response(content: str) -> tuple[str, str]:
    data = json.loads(content)

    return data["yaml"].strip(), data["description"].strip()