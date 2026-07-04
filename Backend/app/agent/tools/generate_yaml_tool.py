from agent.prompts import GENERATE_PROMPT

from langchain_core.tools import tool
from schemas.context_package import ContextPackage
from langchain_core.runnables import RunnableConfig

@tool
async def generate_yaml_tool(user_prompt: str, previous_yaml: str | None = None,
                            config: RunnableConfig = None) -> str:
    """
    Call this to generate a NEW pipeline from scratch or to add NEW features 
    to an existing pipeline. 
    Do NOT call this to fix errors in existing code; use validate_pipeline_tool first for that.
    """
    try:
        previous_section = ""
        if previous_yaml:
            previous_section = f"\n\nExisting YAML to modify:\n```yaml\n{previous_yaml}\n```"

        return (
            f"REPO_CONTEXT_ALREADY_LOADED\n"
            f"User request: {user_prompt}"
            f"{previous_section}\n\n"
            f"Now generate/modify the pipeline. Follow the OUTPUT STRUCTURE: "
            f"Provide a brief description, then the YAML inside a ```yaml block."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
