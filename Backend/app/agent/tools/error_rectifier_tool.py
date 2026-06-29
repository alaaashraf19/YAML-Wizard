from agent.prompts import RECTIFY_PROMPT

from langchain_core.tools import tool

@tool
async def rectify_yaml_tool(
    yaml_content: str,
    validation_report: str,
) -> str:
    """
    Call this tool when `validate_pipeline_tool` returns errors.
    It tells the LLM to fix the YAML using the validation report.

    Args:
        yaml_content: The current (invalid) YAML.
        validation_report: The JSON/string output from validate_pipeline_tool.
    """
    print("[rectify_yaml_tool] called — validation errors received")

    # Keep it short and clear
    return (
        f"VALIDATION_FAILED\n"
        f"Current YAML:\n```yaml\n{yaml_content}\n```\n\n"
        f"Validation Report:\n{validation_report}\n\n"
        f"Fix ALL errors and return ONLY the corrected JSON in this format:\n"
        f'{{"yaml": "<fixed YAML>", "description": "<what was fixed>"}}'
    )