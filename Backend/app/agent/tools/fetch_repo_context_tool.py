from langchain_core.tools import tool
from ..utils.url_parser import parse_repo_url
from fastapi.concurrency import run_in_threadpool
from services.project_service import _resolve_token
from langchain_core.runnables import RunnableConfig
from ..utils.context_resolver import build_context_summary

@tool
async def fetch_repo_context_tool(repo_url: str, config: RunnableConfig = None) -> str:
    """
    Call this tool when a user provides a repository URL (GitHub or GitLab) 
    and wants to start a new project, generate a pipeline, or analyze that repo, 
    or maybe firther questions and validations or fixing.
    It fetches the languages, frameworks, and existing CI setup.
    """
    print("[fetch_repo_context_tool] called — fetching repo context")
    
    configurable = (config or {}).get("configurable", {})
    db = configurable.get("db")
    user_id = configurable.get("user_id")
    
    parsed_repo_url= parse_repo_url(repo_url)
    token, _  = await _resolve_token(user_id, parsed_repo_url.platform , repo_url,db)

    if parsed_repo_url.platform == "github":
        from agent.github_agent import run_github_agent
        pkg = await run_in_threadpool(run_github_agent, repo_url=repo_url, github_token=token)
    else:
        from agent.gitlab_agent import run_gitlab_agent
        pkg = await run_in_threadpool(run_gitlab_agent, repo_url=repo_url, gitlab_token=token)

    context_summary = build_context_summary(pkg) #str
    return (
        f"SUCCESS: Context fetched for {repo_url}\n\n"
        f"REPO_CONTEXT_LOADED:\n{context_summary}\n\n"
        "You now have the repository details. You can now answer questions about it "
    )