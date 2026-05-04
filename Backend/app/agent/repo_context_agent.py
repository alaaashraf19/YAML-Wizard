from __future__ import annotations

import json
import logging
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent.tools.github_mcp_tools import MCPSessionManager, build_github_tools
from schemas.context_package import ContextPackage

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 15
MAX_FILE_CONTENT_CHARS = 8_000

# Files we always fetch if present at root
ROOT_FILES_TO_FETCH = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "Pipfile",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Makefile",
    ".gitlab-ci.yml",
}

# Directories we always recurse into if present
DIRS_TO_EXPLORE = {".github"}


# ── State ─────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: list[BaseMessage]
    tool_call_count: int
    # Injected programmatically after the first list_directory call
    files_to_fetch: list[str]
    fetch_index: int


# ── Directory parsing ──────────────────────────────────────────────────────

def _parse_directory_listing(raw: str) -> tuple[str, list[dict]]:
    """
    Parse the GitHub API JSON array into:
      - a human-readable plain-text tree string
      - the raw list of entry dicts for programmatic use
    Falls back gracefully if the response is not valid JSON.
    """
    try:
        entries = json.loads(raw)
        if not isinstance(entries, list):
            return raw, []
        lines = []
        for entry in entries:
            name = entry.get("name", "")
            kind = entry.get("type", "")
            lines.append(f"{name}/" if kind == "dir" else name)
        return "\n".join(lines), entries
    except (json.JSONDecodeError, AttributeError):
        return raw, []


def _select_files_to_fetch(entries: list[dict], owner: str, repo: str) -> list[str]:
    """
    Programmatically decide which paths to fetch based on the root listing.
    No LLM involvement — deterministic.
    """
    paths: list[str] = []
    dir_names: list[str] = []

    for entry in entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind == "file" and name in ROOT_FILES_TO_FETCH:
            paths.append(name)
        elif kind == "dir" and name in DIRS_TO_EXPLORE:
            dir_names.append(name)

    # For .github, we need to list workflows/ and pick ci ymls
    if ".github" in dir_names:
        paths.append(".github/workflows")   # signals: list this dir next

    return paths


# ── Helpers ───────────────────────────────────────────────────────────────

def _truncate(content: str, max_chars: int = MAX_FILE_CONTENT_CHARS) -> str:
    if len(content) <= max_chars:
        return content
    half = max_chars // 2
    return content[:half] + "\n...[truncated]...\n" + content[-half:]


def _extract_file_path(messages: list[BaseMessage], tool_call_id: str) -> str | None:
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        for tc in getattr(msg, "tool_calls", []):
            if tc.get("id") == tool_call_id:
                path = tc.get("args", {}).get("path", "")
                return path if path else None
    return None


def _build_context_from_tool_results(
    messages: list[BaseMessage],
    owner: str,
    repo: str,
) -> ContextPackage:
    key_files: dict[str, str] = {}
    directory_tree: str = ""

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content if isinstance(msg.content, str) else ""
        tool_name = getattr(msg, "name", "") or ""

        if tool_name == "list_directory" and not directory_tree:
            plain, _ = _parse_directory_listing(content)
            directory_tree = plain

        elif tool_name == "get_file_contents":
            file_path = _extract_file_path(messages, msg.tool_call_id)
            if file_path and content and not content.startswith("[ERROR]"):
                # If this was a directory listing (e.g. .github/workflows), expand it
                _, sub_entries = _parse_directory_listing(content)
                if sub_entries:
                    # It's a directory — we'll handle sub-files via fetch queue
                    pass
                else:
                    key_files[file_path] = _truncate(content)

    return ContextPackage(
        languages=_detect_languages(key_files),
        frameworks=_detect_frameworks(key_files),
        build_tools=_detect_build_tools(key_files),
        test_runners=_detect_test_runners(key_files),
        has_docker="Dockerfile" in key_files or "docker-compose.yml" in key_files,
        has_existing_ci=any(
            k.startswith(".github/workflows") or k == ".gitlab-ci.yml"
            for k in key_files
        ),
        existing_ci_content=next(
            (v for k, v in key_files.items() if k.startswith(".github/workflows") or k == ".gitlab-ci.yml"),
            None,
        ),
        key_files=key_files,
        directory_tree=directory_tree,
        notes=f"Fetched {len(key_files)} files from {owner}/{repo}",
    )


# ── Detection helpers ─────────────────────────────────────────────────────

def _detect_languages(key_files: dict) -> list[str]:
    langs = []
    if any(f in key_files for f in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile")):
        langs.append("python")
    if "package.json" in key_files:
        pkg = key_files["package.json"]
        langs.append("typescript" if "tsconfig" in str(key_files) or '"typescript"' in pkg else "javascript")
    if "go.mod" in key_files:
        langs.append("go")
    if "Cargo.toml" in key_files:
        langs.append("rust")
    if "pom.xml" in key_files or "build.gradle" in key_files:
        langs.append("java")
    if "Gemfile" in key_files:
        langs.append("ruby")
    return langs


def _detect_frameworks(key_files: dict) -> list[str]:
    all_content = " ".join(key_files.values()).lower()
    return [
        fw for fw in ("fastapi", "django", "flask", "express", "react", "vue", "next", "spring", "rails")
        if fw in all_content
    ]


def _detect_build_tools(key_files: dict) -> list[str]:
    tools = []
    if "requirements.txt" in key_files or "pyproject.toml" in key_files:
        tools.append("pip")
    if "package.json" in key_files:
        tools.append("npm")
    if "pom.xml" in key_files:
        tools.append("maven")
    if "Makefile" in key_files:
        tools.append("make")
    if "Cargo.toml" in key_files:
        tools.append("cargo")
    return tools


def _detect_test_runners(key_files: dict) -> list[str]:
    all_content = " ".join(key_files.values()).lower()
    runners = [r for r in ("pytest", "unittest", "jest", "mocha") if r in all_content]
    if "go.mod" in key_files:
        runners.append("go test")
    return runners


# ── Programmatic orchestration (bypasses LLM for file selection) ──────────

def run_repo_context_agent(
    user_prompt: str,
    repo_url: str,
    github_token: str,
    model: str = "qwen2.5:3b",
) -> ContextPackage:
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {repo_url}")
    owner, repo = parts[-2], parts[-1]

    manager = MCPSessionManager(github_token=github_token)
    tools = build_github_tools(manager)

    # Build a tool lookup by name for direct calls
    tool_map = {t.name: t for t in tools}

    def call(tool_name: str, **kwargs) -> str:
        result = tool_map[tool_name].invoke(kwargs)
        return result if isinstance(result, str) else str(result)

    logger.info("RepoContextAgent starting: %s/%s", owner, repo)

    # ── Step 1: list root ──────────────────────────────────────────────────
    raw_root = call("list_directory", owner=owner, repo=repo, path="")
    plain_tree, root_entries = _parse_directory_listing(raw_root)
    logger.info("Root listing done — %d entries", len(root_entries))

    # ── Step 2: select files deterministically ────────────────────────────
    paths_to_fetch = _select_files_to_fetch(root_entries, owner, repo)
    logger.info("Files selected: %s", paths_to_fetch)

    # ── Step 3: fetch each path; expand directories one level ─────────────
    key_files: dict[str, str] = {}

    for path in paths_to_fetch:
        if len(key_files) >= MAX_TOOL_CALLS:
            break
        raw = call("get_file_contents", owner=owner, repo=repo, path=path)

        if raw.startswith("[ERROR]"):
            logger.warning("Skipping %s: %s", path, raw)
            continue

        # Check if the response is a directory listing (e.g. .github/workflows)
        plain_sub, sub_entries = _parse_directory_listing(raw)
        if sub_entries:
            # It's a directory — fetch each yml/yaml file inside
            for entry in sub_entries:
                sub_name = entry.get("name", "")
                sub_kind = entry.get("type", "")
                if sub_kind == "file" and sub_name.endswith((".yml", ".yaml")):
                    sub_path = f"{path}/{sub_name}"
                    sub_raw = call("get_file_contents", owner=owner, repo=repo, path=sub_path)
                    if not sub_raw.startswith("[ERROR]"):
                        key_files[sub_path] = _truncate(sub_raw)
                        logger.info("Fetched: %s", sub_path)
        else:
            key_files[path] = _truncate(raw)
            logger.info("Fetched: %s", path)

    # ── Step 4: build and return package ──────────────────────────────────
    has_ci = any(
        k.startswith(".github/workflows") or k == ".gitlab-ci.yml"
        for k in key_files
    )
    package = ContextPackage(
        languages=_detect_languages(key_files),
        frameworks=_detect_frameworks(key_files),
        build_tools=_detect_build_tools(key_files),
        test_runners=_detect_test_runners(key_files),
        has_docker="Dockerfile" in key_files or "docker-compose.yml" in key_files,
        has_existing_ci=has_ci,
        existing_ci_content=next(
            (v for k, v in key_files.items() if k.startswith(".github/workflows") or k == ".gitlab-ci.yml"),
            None,
        ),
        key_files=key_files,
        directory_tree=plain_tree,
        notes=f"Fetched {len(key_files)} files from {owner}/{repo}",
    )

    logger.info("Done — languages=%s, files=%s", package.languages, list(key_files.keys()))
    return package