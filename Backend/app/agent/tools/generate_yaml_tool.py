from agent.prompts import GENERATE_PROMPT

from langchain_core.tools import tool
from schemas.context_package import ContextPackage
from langchain_core.runnables import RunnableConfig

@tool
async def generate_yaml_tool(user_prompt: str, previous_yaml: str | None = None,
                            config: RunnableConfig = None) -> str:
    """
    Call this tool FIRST whenever the user asks to generate, modify, or explain
    a CI/CD pipeline / YAML workflow.

    The full repository context has already been injected into the conversation
    as a system message. This tool simply confirms that you should now generate
    the pipeline using that context + the GENERATE_PROMPT rules.
    """
    try:

        print("[generate_yaml_tool] called - context already available in system message")

        previous_section = ""
        if previous_yaml:
            previous_section = f"\n\nExisting YAML to base changes on:\n```yaml\n{previous_yaml}\n```"

        return (
            f"REPO_CONTEXT_ALREADY_LOADED\n"
            f"User request: {user_prompt}"
            f"{previous_section}\n\n"
            f"Now generate the pipeline following the GENERATE_PROMPT rules. "
            f"Return ONLY the required JSON object."
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise




import json
import re
def parse_response(content: str) -> tuple[str, str]:
    # Remove markdown code blocks if the LLM accidentally included them
    clean_content = re.sub(r"```json\s?|```", "", content).strip()
    data = json.loads(clean_content)
    return data["yaml"].strip(), data["description"].strip()