from agent.prompts import RECTIFY_PROMPT

from langchain_core.tools import tool

@tool
async def rectify_yaml_tool(yaml_content: str,validation_report: str,) -> str:
    """
    Prepare YAML validation errors for correction.

    Args:
        yaml_content: Current YAML.
        validation_report: JSON output from validate_pipeline_tool.

    Returns:
        Prompt containing YAML and validation errors that should be fixed.
    """

    return RECTIFY_PROMPT.format(
        yaml_content=yaml_content,
        validation_report=validation_report,
    )