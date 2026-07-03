#Fine-tuned-model YAML generation workflow.Single-shot: prompt + repo context -> raw CI/CD YAML. 

from __future__ import annotations

from agent.finetuning.model_client import chat_completion

FINETUNED_SYSTEM_PROMPT = (
    "You are an expert CI/CD engineer. Given a plain-English description of a "
    "pipeline, output ONLY the complete, valid YAML for the requested platform "
    "(GitHub Actions or GitLab CI). Do not add explanations or markdown fences."
)

RECTIFY_INSTRUCTION = (
    "The YAML you produced failed validation. Fix ALL of the reported errors and "
    "output ONLY the corrected, complete YAML. Do not add explanations or markdown fences."
)


def platform_label(platform: str) -> str:
    return "GitHub Actions" if (platform or "").lower() == "github" else "GitLab CI"

#Remove leading and trailing yaml fences the model may add despite the instruction
def strip_code_fences(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


#Assemble the user turn: target platform + (optional) repo context + description.
def build_user_message(description: str, platform: str, context_summary: str | None) -> str:
    parts = [f"Target platform: {platform_label(platform)}"]
    if context_summary:
        parts.append("\nRepository context:\n" + context_summary)
    parts.append("\nPipeline description:\n" + (description or "").strip())
    return "\n".join(parts)


async def generate_yaml(
    description: str,
    platform: str,
    context_summary: str | None = None,
    temperature: float = 0.2,
) -> str:
    messages = [
        {"role": "system", "content": FINETUNED_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(description, platform, context_summary)},
    ]
    raw = await chat_completion(messages, temperature=temperature)
    return strip_code_fences(raw)


async def rectify_yaml(
    description: str,
    platform: str,
    context_summary: str | None,
    broken_yaml: str,
    validation_report: str,
    temperature: float = 0.1,
) -> str:
    messages = [
        {"role": "system", "content": FINETUNED_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(description, platform, context_summary)},
        {"role": "assistant", "content": broken_yaml},
        {"role": "user", "content": f"{RECTIFY_INSTRUCTION}\n\nValidation report:\n{validation_report}"},
    ]
    raw = await chat_completion(messages, temperature=temperature)
    return strip_code_fences(raw)
