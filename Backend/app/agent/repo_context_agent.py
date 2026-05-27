"""
RepoContextAgent — deterministic GitHub repo scanner.

Uses @modelcontextprotocol/server-github (via npx) to:
  1. List the repo root
  2. Fetch key config/dependency files
  3. Detect languages, frameworks, build tools
  4. Detect test runners (expanded: pytest, jest, mocha, playwright,
     rspec, go test, junit/surefire, nunit, xunit, karma, vitest)
  5. Detect test report formats (JUnit XML, TRX, NUnit XML,
     Jest JSON, Mocha JSON, Playwright JSON)
  6. Return a ContextPackage ready for YAML generation & dashboard
"""
from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agent.tools.github_mcp_tools import MCPSessionManager, build_github_tools
from schemas.context_package import ContextPackage, TestReportInfo, TestRunnerInfo

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 15
MAX_FILE_CONTENT_CHARS = 20_000   # raised: tool sections (pytest, coverage) appear late in pyproject.toml

# ── Files always fetched if present at root ───────────────────────────────
ROOT_FILES_TO_FETCH = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",           # modern Docker Compose filename
    "compose.yaml",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Makefile",
    ".gitlab-ci.yml",
    ".travis.yml",
    "Gemfile",
    "karma.conf.js",
    "jest.config.js",
    "jest.config.ts",
    "playwright.config.js",
    "playwright.config.ts",
    ".rspec",
    "pytest.ini",
    "tox.ini",
    "tsconfig.json",
}

# Subdirectories to recurse into for key files (backend/pyproject.toml etc.)
SUBDIRS_TO_SCAN = {"backend", "frontend", "src", "app"}

DIRS_TO_EXPLORE = {".github"}

# ── Report directories heuristic ─────────────────────────────────────────
REPORT_DIR_HINTS = [
    "test-results", "test_results", "reports", "junit",
    "allure-results", "coverage", "artifacts", "output",
]


# ═══════════════════════════════════════════════════════════════════════════
# Detection helpers
# ═══════════════════════════════════════════════════════════════════════════

def _detect_languages(key_files: dict[str, str]) -> list[str]:
    langs: list[str] = []
    if any(f in key_files for f in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile")):
        langs.append("python")
    # Check root package.json AND any subdir package.json (frontend/package.json etc.)
    pkg_keys = [k for k in key_files if k == "package.json" or k.endswith("/package.json")]
    if pkg_keys:
        all_pkg_content = " ".join(key_files[k] for k in pkg_keys)
        is_ts = (
            '"typescript"' in all_pkg_content
            or '"@types/' in all_pkg_content
            or "tsconfig" in str(list(key_files.keys()))
            or "tsconfig.json" in key_files
            or any(k.endswith("/tsconfig.json") for k in key_files)
        )
        langs.append("typescript" if is_ts else "javascript")
    if "go.mod" in key_files:
        langs.append("go")
    if "Cargo.toml" in key_files:
        langs.append("rust")
    if "pom.xml" in key_files or "build.gradle" in key_files or "build.gradle.kts" in key_files:
        langs.append("java")
    if "Gemfile" in key_files:
        langs.append("ruby")
    return langs


# Files that reliably indicate a framework (dependency/config files only)
# Intentionally excludes CI workflow files to avoid false positives
FRAMEWORK_SOURCE_FILES = {
    "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
    "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "go.mod", "Gemfile", "Cargo.toml", "composer.json",
}

# (framework_name, keyword_that_must_appear_in_a_dependency_file)
FRAMEWORK_SIGNATURES: list[tuple[str, str]] = [
    ("fastapi",   "fastapi"),
    ("django",    "django"),
    ("flask",     "flask"),
    ("express",   '"express"'),
    ("react",     '"react"'),
    ("vue",       '"vue"'),
    ("nextjs",    '"next"'),
    ("nuxt",      '"nuxt"'),
    ("svelte",    '"svelte"'),
    ("angular",   "@angular/core"),
    ("spring",    "spring-boot"),
    ("rails",     "rails"),
    ("nestjs",    "@nestjs/core"),
    ("gin",       "gin-gonic/gin"),
    ("fiber",     "gofiber/fiber"),
    ("echo",      "labstack/echo"),
    ("quarkus",   "quarkus"),
]


def _detect_frameworks(key_files: dict[str, str]) -> list[str]:
    # Only scan dependency/config files — never CI workflows
    dep_content = " ".join(
        v for k, v in key_files.items()
        if any(k.endswith(src) or k == src for src in FRAMEWORK_SOURCE_FILES)
    ).lower()

    return [fw for fw, keyword in FRAMEWORK_SIGNATURES if keyword.lower() in dep_content]


def _detect_build_tools(key_files: dict[str, str]) -> list[str]:
    tools: list[str] = []
    if "requirements.txt" in key_files or "pyproject.toml" in key_files:
        tools.append("pip")
        if "poetry" in key_files.get("pyproject.toml", ""):
            tools.append("poetry")
    if "package.json" in key_files:
        pkg = key_files["package.json"]
        tools.append("npm")
        if "webpack" in pkg:
            tools.append("webpack")
        if "vite" in pkg:
            tools.append("vite")
    if "pom.xml" in key_files:
        tools.append("maven")
    if "build.gradle" in key_files or "build.gradle.kts" in key_files:
        tools.append("gradle")
    if "Makefile" in key_files:
        tools.append("make")
    if "Cargo.toml" in key_files:
        tools.append("cargo")
    return tools


# ── Expanded test runner detection ────────────────────────────────────────

# (runner_name, ecosystem, file_key, content_keyword_or_None)
RUNNER_SIGNATURES: list[tuple[str, str, str, str | None]] = [
    # Python
    ("pytest",          "python",   "pytest.ini",       None),
    ("pytest",          "python",   "pyproject.toml",   "pytest"),
    ("pytest",          "python",   "setup.cfg",        "pytest"),
    ("pytest",          "python",   "requirements.txt", "pytest"),
    ("pytest",          "python",   "tox.ini",          "pytest"),
    ("unittest",        "python",   "pyproject.toml",   "unittest"),
    # JavaScript / TypeScript
    ("jest",            "javascript", "jest.config.js",  None),
    ("jest",            "javascript", "jest.config.ts",  None),
    ("jest",            "javascript", "package.json",    '"jest"'),
    ("mocha",           "javascript", "package.json",    '"mocha"'),
    ("vitest",          "javascript", "package.json",    '"vitest"'),
    ("karma",           "javascript", "karma.conf.js",   None),
    ("karma",           "javascript", "package.json",    '"karma"'),
    # End-to-End
    ("playwright",      "e2e",  "playwright.config.js",  None),
    ("playwright",      "e2e",  "playwright.config.ts",  None),
    ("playwright",      "e2e",  "package.json",          '"playwright"'),
    # Ruby
    ("rspec",           "ruby", ".rspec",                None),
    ("rspec",           "ruby", "Gemfile",               "rspec"),
    # Go
    ("go test",         "go",   "go.mod",                None),
    # Java
    ("junit/surefire",  "java", "pom.xml",               "junit"),
    ("junit/surefire",  "java", "build.gradle",          "junit"),
    ("junit/surefire",  "java", "build.gradle.kts",      "junit"),
    # .NET
    ("nunit",           "dotnet", "package.json",        "nunit"),   # placeholder — .csproj not fetched by default
    ("xunit",           "dotnet", "package.json",        "xunit"),
]


def _detect_test_runners(key_files: dict[str, str]) -> tuple[list[str], list[TestRunnerInfo]]:
    """
    Returns:
      - flat list[str]          (backward-compatible, stored in DB)
      - list[TestRunnerInfo]    (rich info for dashboard & YAML gen)
    """
    seen: set[str] = set()
    details: list[TestRunnerInfo] = []

    for runner, ecosystem, file_key, keyword in RUNNER_SIGNATURES:
        if runner in seen:
            continue
        # Match exact filename OR any subdir variant (e.g. backend/pyproject.toml)
        matching_keys = [k for k in key_files if k == file_key or k.endswith("/" + file_key)]
        if not matching_keys:
            continue
        # Check ALL matching files — the root pyproject.toml may lack pytest
        # while backend/pyproject.toml has it
        matched_path = None
        for candidate_key in matching_keys:
            file_content = key_files[candidate_key]
            if keyword is None or keyword in file_content:
                matched_path = candidate_key
                break
        if matched_path is None:
            continue
        seen.add(runner)
        details.append(TestRunnerInfo(
            runner=runner,
            ecosystem=ecosystem,
            detected_via=matched_path + (f" (contains '{keyword}')" if keyword else ""),
        ))

    return sorted(seen), details


# ── Test report format detection ──────────────────────────────────────────

REPORT_SIGNATURES: list[tuple[str, str, str | None]] = [
    # (format_name, file_extension, content_discriminator)
    ("junit_xml",       ".xml",  "testsuites"),
    ("junit_xml",       ".xml",  "testsuite"),
    ("nunit_xml",       ".xml",  "test-run"),
    ("nunit_xml",       ".xml",  "TestResult"),
    ("trx",             ".trx",  None),
    ("jest_json",       ".json", '"numPassedTests"'),
    ("mocha_json",      ".json", '"passes"'),
    ("playwright_json", ".json", '"suites"'),
]


def _xml_root_tag(content: str) -> str | None:
    try:
        return ET.fromstring(content[:4096]).tag.lower()
    except ET.ParseError:
        return None


def _detect_report_format(path: str, content: str | None) -> str | None:
    lower = path.lower()
    for fmt, ext, discriminator in REPORT_SIGNATURES:
        if ext not in lower:
            continue
        if discriminator is None:
            return fmt
        if content is None:
            continue
        if ext == ".xml":
            tag = _xml_root_tag(content)
            if tag and discriminator.lower() in tag:
                return fmt
        else:
            if discriminator in content:
                return fmt
    return None


def _detect_reports(
    all_paths: list[str],
    key_files: dict[str, str],
) -> tuple[bool, list[TestReportInfo]]:
    """
    Scan known paths for test report files.
    `all_paths` = every file path seen in the directory listing (if available).
    `key_files` = already-fetched file contents.
    """
    found: list[TestReportInfo] = []
    seen_formats: set[str] = set()

    # Check already-fetched files first
    for path, content in key_files.items():
        lower = path.lower()
        if not any(lower.endswith(ext) for ext in (".xml", ".trx", ".json")):
            continue
        if not any(hint in lower for hint in REPORT_DIR_HINTS):
            continue
        fmt = _detect_report_format(path, content)
        if fmt and fmt not in seen_formats:
            seen_formats.add(fmt)
            found.append(TestReportInfo(format=fmt, path=path))

    # Also check directory listing paths (no content available)
    for path in all_paths:
        lower = path.lower()
        if not any(lower.endswith(ext) for ext in (".xml", ".trx", ".json")):
            continue
        if not any(hint in lower for hint in REPORT_DIR_HINTS):
            continue
        fmt = _detect_report_format(path, None)
        if fmt and fmt not in seen_formats:
            seen_formats.add(fmt)
            found.append(TestReportInfo(format=fmt, path=path))

    return len(found) > 0, found


# ═══════════════════════════════════════════════════════════════════════════
# Directory parsing helpers (unchanged from original)
# ═══════════════════════════════════════════════════════════════════════════

def _parse_directory_listing(raw: str) -> tuple[str, list[dict]]:
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
    paths: list[str] = []
    dir_names: list[str] = []
    for entry in entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind == "file" and name in ROOT_FILES_TO_FETCH:
            paths.append(name)
        elif kind == "dir" and name in DIRS_TO_EXPLORE:
            dir_names.append(name)
    if ".github" in dir_names:
        paths.append(".github/workflows")
    return paths


def _extract_file_content(raw: str) -> str:
    """
    The GitHub MCP server wraps each file response as a JSON object:
      {"name": "pyproject.toml", "content": "actual text ...", ...}

    Extract the plain `content` field so all detection logic runs
    on the real file text, not the wrapper JSON.
    Falls back to `raw` if it is not a single-file object.
    """
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "content" in parsed and isinstance(parsed["content"], str):
            return parsed["content"]
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


def _truncate(content: str, max_chars: int = MAX_FILE_CONTENT_CHARS) -> str:
    """
    Keep the beginning AND the end of the file.
    Tool/test sections (e.g. [tool.pytest.ini_options]) often appear at
    the end of pyproject.toml, so we must preserve the tail.
    """
    if len(content) <= max_chars:
        return content
    # Keep 60 % from the start (imports, dependencies) and 40 % from the end
    # (tool sections, test config) — this catches pytest/coverage/ruff config
    head = int(max_chars * 0.6)
    tail = max_chars - head
    return content[:head] + "\n...[truncated]...\n" + content[-tail:]


# ═══════════════════════════════════════════════════════════════════════════
# Main agent entry point
# ═══════════════════════════════════════════════════════════════════════════

def run_repo_context_agent(
    user_prompt: str,
    repo_url: str,
    github_token: str,
    model: str = "qwen2.5:3b",
) -> ContextPackage:
    """
    Deterministic repo scanner — no LLM involved in file selection.

    Steps:
      1. List repo root via MCP github server
      2. Fetch key config/dependency files
      3. Detect languages, frameworks, build tools
      4. Detect test runners (expanded set)
      5. Detect test report formats
      6. Return ContextPackage
    """
    # Strip trailing slash and any subfolder/tree path
    # Handles:
    #   https://github.com/owner/repo
    #   https://github.com/owner/repo/tree/branch/subfolder
    #   https://github.com/owner/repo/blob/main/file.py
    url_clean = repo_url.rstrip("/")
    for marker in ("/tree/", "/blob/", "/commit/", "/releases", "/issues", "/pulls"):
        if marker in url_clean:
            url_clean = url_clean[:url_clean.index(marker)]

    parts = url_clean.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {repo_url}")
    owner, repo = parts[-2], parts[-1]
    repo = repo.removesuffix(".git")

    manager = MCPSessionManager(github_token=github_token)
    tools = build_github_tools(manager)
    tool_map = {t.name: t for t in tools}

    def call(tool_name: str, **kwargs) -> str:
        result = tool_map[tool_name].invoke(kwargs)
        return result if isinstance(result, str) else str(result)

    logger.info("RepoContextAgent starting: %s/%s", owner, repo)

    # ── Step 1: list root ─────────────────────────────────────────────────
    raw_root = call("list_directory", owner=owner, repo=repo, path="")
    plain_tree, root_entries = _parse_directory_listing(raw_root)
    logger.info("Root listing done — %d entries", len(root_entries))

    # Build a flat path list from root entries (for report detection)
    all_paths = [e.get("name", "") for e in root_entries if e.get("type") == "file"]

    # ── Step 2: select & fetch files ──────────────────────────────────────
    paths_to_fetch = _select_files_to_fetch(root_entries, owner, repo)
    logger.info("Files selected: %s", paths_to_fetch)

    key_files: dict[str, str] = {}

    for path in paths_to_fetch:
        if len(key_files) >= MAX_TOOL_CALLS:
            break
        raw = call("get_file_contents", owner=owner, repo=repo, path=path)
        if raw.startswith("[ERROR]"):
            logger.warning("Skipping %s: %s", path, raw)
            continue

        plain_sub, sub_entries = _parse_directory_listing(raw)
        if sub_entries:
            # It's a directory (e.g. .github/workflows) — fetch yml files inside
            for entry in sub_entries:
                sub_name = entry.get("name", "")
                sub_kind = entry.get("type", "")
                if sub_kind == "file" and sub_name.endswith((".yml", ".yaml")):
                    sub_path = f"{path}/{sub_name}"
                    sub_raw = call("get_file_contents", owner=owner, repo=repo, path=sub_path)
                    if not sub_raw.startswith("[ERROR]"):
                        key_files[sub_path] = _truncate(_extract_file_content(sub_raw))
                        all_paths.append(sub_path)
                        logger.info("Fetched: %s", sub_path)
        else:
            key_files[path] = _truncate(_extract_file_content(raw))
            logger.info("Fetched: %s", path)

    # ── Step 2b: scan known subdirs for backend/frontend config files ────────
    for entry in root_entries:
        name = entry.get("name", "")
        kind = entry.get("type", "")
        if kind != "dir" or name not in SUBDIRS_TO_SCAN:
            continue
        for sub_file in ("pyproject.toml", "requirements.txt", "package.json",
                         "jest.config.js", "jest.config.ts",
                         "playwright.config.js", "playwright.config.ts",
                         "pytest.ini", "setup.cfg"):
            sub_path = f"{name}/{sub_file}"
            if sub_path in key_files:
                continue
            sub_raw = call("get_file_contents", owner=owner, repo=repo, path=sub_path)
            if not sub_raw.startswith("[ERROR]"):
                extracted = _extract_file_content(sub_raw)
                key_files[sub_path] = _truncate(extracted)
                logger.info("Fetched subdir file: %s", sub_path)

    # ── Step 3: detect everything ─────────────────────────────────────────
    languages  = _detect_languages(key_files)
    frameworks = _detect_frameworks(key_files)
    build_tools = _detect_build_tools(key_files)
    test_runners_flat, test_runner_details = _detect_test_runners(key_files)
    has_reports, test_reports = _detect_reports(all_paths, key_files)

    has_ci = any(
        k.startswith(".github/workflows") or k == ".gitlab-ci.yml"
        for k in key_files
    )
    existing_ci_content = next(
        (v for k, v in key_files.items()
         if k.startswith(".github/workflows") or k == ".gitlab-ci.yml"),
        None,
    )

    package = ContextPackage(
        languages=languages,
        frameworks=frameworks,
        build_tools=build_tools,
        test_runners=test_runners_flat,
        test_runner_details=test_runner_details,
        has_test_reports=has_reports,
        test_reports=test_reports,
        has_docker=any(f in key_files for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")),
        has_existing_ci=has_ci,
        existing_ci_content=existing_ci_content,
        key_files=key_files,
        directory_tree=plain_tree,
        notes=f"Fetched {len(key_files)} files from {owner}/{repo}",
    )

    logger.info(
        "Done — languages=%s runners=%s has_test_reports=%s",
        package.languages, package.test_runners, package.has_test_reports,
    )
    return package