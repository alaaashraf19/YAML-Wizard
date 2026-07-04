from agent.prompts import RECTIFY_PROMPT

from langchain_core.tools import tool

@tool
async def rectify_yaml_tool(
    yaml_content: str,
    validation_report: str,
) -> str:
    """
    Call this tool ONLY when `validate_pipeline_tool` returns errors.
    It provides the context needed for the RECTIFY_PROMPT.
    """
    print("[rectify_yaml_tool] called — validation errors received")

    # Keep it short and clear
    return (
        f"VALIDATION_FAILED\n"
        f"Current YAML:\n```yaml\n{yaml_content}\n```\n\n"
        f"The YAML failed validation. Here are the errors:\n{validation_report}\n\n"
        f"Please apply the RECTIFY_PROMPT rules now: "
        f"Explain the fix, then provide the corrected ```yaml block."
    )