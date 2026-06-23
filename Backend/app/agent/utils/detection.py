"""
detection.py — shared detection helpers for all repo context agents.
All detection functions are pure: they take `key_files: dict[str, str]`
(path → content) and return structured results.  Neither GitHub nor GitLab
agent should duplicate this logic.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Optional

from schemas.context_package import ContextPackage, TestReportInfo, TestRunnerInfo

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_CONTENT_CHARS = 20_000

FRAMEWORK_SOURCE_FILES = {
    "requirements.txt", "pyproject.toml", "setup.py", "Pipfile",
    "package.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "go.mod", "Gemfile", "Cargo.toml", "composer.json",
}

FRAMEWORK_SIGNATURES: list[tuple[str, str]] = [
    ("fastapi",  "fastapi"),
    ("django",   "django"),
    ("flask",    "flask"),
    ("express",  '"express"'),
    ("react",    '"react"'),
    ("vue",      '"vue"'),
    ("nextjs",   '"next"'),
    ("nuxt",     '"nuxt"'),
    ("svelte",   '"svelte"'),
    ("angular",  "@angular/core"),
    ("spring",   "spring-boot"),
    ("rails",    "rails"),
    ("nestjs",   "@nestjs/core"),
    ("gin",      "gin-gonic/gin"),
    ("fiber",    "gofiber/fiber"),
    ("echo",     "labstack/echo"),
    ("quarkus",  "quarkus"),
]

# (runner, ecosystem, file_key, content_keyword_or_None)
RUNNER_SIGNATURES: list[tuple[str, str, str, str | None]] = [
    # Python
    ("pytest",         "python",     "pytest.ini",            None),
    ("pytest",         "python",     "pyproject.toml",        "pytest"),
    ("pytest",         "python",     "setup.cfg",             "pytest"),
    ("pytest",         "python",     "requirements.txt",      "pytest"),
    ("pytest",         "python",     "tox.ini",               "pytest"),
    ("unittest",       "python",     "pyproject.toml",        "unittest"),
    # JavaScript / TypeScript
    ("jest",           "javascript", "jest.config.js",        None),
    ("jest",           "javascript", "jest.config.ts",        None),
    ("jest",           "javascript", "package.json",          '"jest"'),
    ("mocha",          "javascript", "package.json",          '"mocha"'),
    ("vitest",         "javascript", "package.json",          '"vitest"'),
    ("karma",          "javascript", "karma.conf.js",         None),
    ("karma",          "javascript", "package.json",          '"karma"'),
    # E2E
    ("playwright",     "e2e",        "playwright.config.js",  None),
    ("playwright",     "e2e",        "playwright.config.ts",  None),
    ("playwright",     "e2e",        "package.json",          '"playwright"'),
    # Ruby
    ("rspec",          "ruby",       ".rspec",                None),
    ("rspec",          "ruby",       "Gemfile",               "rspec"),
    # Go
    ("go test",        "go",         "go.mod",                None),
    # Java
    ("junit/surefire", "java",       "pom.xml",               "junit"),
    ("junit/surefire", "java",       "build.gradle",          "junit"),
    ("junit/surefire", "java",       "build.gradle.kts",      "junit"),
    # .NET
    ("nunit",          "dotnet",     "*.csproj",              "nunit"),
    ("xunit",          "dotnet",     "*.csproj",              "xunit"),
]

REPORT_DIR_HINTS = [
    "test-results", "test_results", "reports", "junit",
    "allure-results", "coverage", "artifacts", "output",
]

REPORT_SIGNATURES: list[tuple[str, str, str | None]] = [
    ("junit_xml",       ".xml",  "testsuites"),
    ("junit_xml",       ".xml",  "testsuite"),
    ("nunit_xml",       ".xml",  "test-run"),
    ("nunit_xml",       ".xml",  "TestResult"),
    ("trx",             ".trx",  None),
    ("jest_json",       ".json", '"numPassedTests"'),
    ("mocha_json",      ".json", '"passes"'),
    ("playwright_json", ".json", '"suites"'),
]

# Common env-var getter patterns
ENV_VAR_PATTERNS = [
    re.compile(r'os\.getenv\(["\']([A-Z_][A-Z0-9_]+)["\']'),
    re.compile(r'os\.environ(?:\.get)?\(["\']([A-Z_][A-Z0-9_]+)["\']'),
    re.compile(r'process\.env\.([A-Z_][A-Z0-9_]+)'),
    re.compile(r'ENV\[["\']([\w]+)["\']\]'),                  # Ruby
    re.compile(r'System\.getenv\(["\']([A-Z_][A-Z0-9_]+)["\']'),  # Java
    re.compile(r'\$\{?([A-Z_][A-Z0-9_]+)\}?'),               # shell / docker-compose
]

# Docker service image → service name mapping
DOCKER_SERVICE_IMAGES = {
    "postgres": "postgres",
    "mysql": "mysql",
    "mariadb": "mariadb",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "redis": "redis",
    "rabbitmq": "rabbitmq",
    "elasticsearch": "elasticsearch",
    "kafka": "kafka",
    "zookeeper": "zookeeper",
    "minio": "minio",
    "memcached": "memcached",
}

# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

def truncate(content: str, max_chars: int = MAX_FILE_CONTENT_CHARS) -> str:
    """Keep head (60 %) + tail (40 %) so tool/test config at EOF is preserved."""
    if len(content) <= max_chars:
        return content
    head = int(max_chars * 0.6)
    tail = max_chars - head
    return content[:head] + "\n...[truncated]...\n" + content[-tail:]


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_languages(key_files: dict[str, str]) -> list[str]:
    langs: list[str] = []
    if any(f in key_files for f in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile")):
        langs.append("python")

    pkg_keys = [k for k in key_files if k == "package.json" or k.endswith("/package.json")]
    if pkg_keys:
        all_pkg = " ".join(key_files[k] for k in pkg_keys)
        is_ts = (
            '"typescript"' in all_pkg
            or '"@types/' in all_pkg
            or "tsconfig" in " ".join(key_files.keys())
        )
        langs.append("typescript" if is_ts else "javascript")

    if "go.mod" in key_files:
        langs.append("go")
    if "Cargo.toml" in key_files:
        langs.append("rust")
    if any(f in key_files for f in ("pom.xml", "build.gradle", "build.gradle.kts")):
        langs.append("java")
    if "Gemfile" in key_files:
        langs.append("ruby")
    # .NET detection via csproj files
    if any(k.endswith(".csproj") for k in key_files):
        langs.append("csharp")
    return langs


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

def detect_frameworks(key_files: dict[str, str]) -> list[str]:
    dep_content = " ".join(
        v for k, v in key_files.items()
        if any(k.endswith(src) or k == src for src in FRAMEWORK_SOURCE_FILES)
    ).lower()
    return [fw for fw, kw in FRAMEWORK_SIGNATURES if kw.lower() in dep_content]


# ---------------------------------------------------------------------------
# Build tool detection
# ---------------------------------------------------------------------------

def detect_build_tools(key_files: dict[str, str]) -> list[str]:
    tools: list[str] = []
    if "requirements.txt" in key_files or "pyproject.toml" in key_files:
        tools.append("pip")
        if "poetry" in key_files.get("pyproject.toml", ""):
            tools.append("poetry")
    pkg_keys = [k for k in key_files if k == "package.json" or k.endswith("/package.json")]
    if pkg_keys:
        pkg_content = " ".join(key_files[k] for k in pkg_keys)
        tools.append("npm")
        if "webpack" in pkg_content:
            tools.append("webpack")
        if "vite" in pkg_content:
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


# ---------------------------------------------------------------------------
# Test runner detection
# ---------------------------------------------------------------------------

def detect_test_runners(
    key_files: dict[str, str],
) -> tuple[list[str], list[TestRunnerInfo]]:
    seen: set[str] = set()
    details: list[TestRunnerInfo] = []
    for runner, ecosystem, file_key, keyword in RUNNER_SIGNATURES:
        if runner in seen:
            continue
        # Support glob-like *.csproj
        if file_key.startswith("*"):
            ext = file_key[1:]  # e.g. ".csproj"
            matching_keys = [k for k in key_files if k.endswith(ext)]
        else:
            matching_keys = [k for k in key_files if k == file_key or k.endswith("/" + file_key)]
        if not matching_keys:
            continue
        matched_path = None
        for candidate in matching_keys:
            if keyword is None or keyword in key_files[candidate]:
                matched_path = candidate
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


# ---------------------------------------------------------------------------
# Test commands extraction
# ---------------------------------------------------------------------------

def extract_test_commands(key_files: dict[str, str]) -> list[str]:
    """
    Try to extract the actual test command(s) from package.json scripts,
    Makefile, or pyproject.toml.
    """
    commands: list[str] = []

    # package.json → scripts.test / scripts.test:*
    for k in key_files:
        if k == "package.json" or k.endswith("/package.json"):
            try:
                pkg = json.loads(key_files[k])
                scripts = pkg.get("scripts", {})
                for name, cmd in scripts.items():
                    if name == "test" or name.startswith("test"):
                        commands.append(f"npm run {name}  # → {cmd}")
            except (json.JSONDecodeError, AttributeError):
                pass

    # Makefile → targets named test / tests / check
    if "Makefile" in key_files:
        for line in key_files["Makefile"].splitlines():
            if re.match(r'^(test|tests|check)\s*:', line):
                commands.append(f"make {line.split(':')[0].strip()}")

    # pyproject.toml → [tool.pytest.ini_options] addopts
    if "pyproject.toml" in key_files:
        content = key_files["pyproject.toml"]
        m = re.search(r'\[tool\.pytest\.ini_options\](.*?)(?=\n\[|\Z)', content, re.DOTALL)
        if m:
            addopts = re.search(r'addopts\s*=\s*["\']([^"\']+)["\']', m.group(1))
            if addopts:
                commands.append(f"pytest {addopts.group(1)}")
            else:
                commands.append("pytest")
        elif "pytest" in content:
            commands.append("pytest")

    return commands


# ---------------------------------------------------------------------------
# Build commands extraction
# ---------------------------------------------------------------------------

def extract_build_commands(key_files: dict[str, str]) -> list[str]:
    """
    Extract build commands from package.json scripts, Makefile, pyproject.toml, or Dockerfile.
    """
    commands: list[str] = []

    # package.json → build/compile/dist scripts
    for k in key_files:
        if k == "package.json" or k.endswith("/package.json"):
            try:
                pkg = json.loads(key_files[k])
                scripts = pkg.get("scripts", {})
                for name, cmd in scripts.items():
                    if name in ("build", "compile", "dist"):
                        commands.append(f"npm run {name}  # → {cmd}")
            except (json.JSONDecodeError, AttributeError):
                pass

    # Makefile → build/compile/dist targets
    if "Makefile" in key_files:
        for line in key_files["Makefile"].splitlines():
            if re.match(r'^(build|compile|dist)\s*:', line):
                commands.append(f"make {line.split(':')[0].strip()}")

    # Python build tools — detect which one is configured
    if "pyproject.toml" in key_files:
        content = key_files["pyproject.toml"]
        if "pdm-backend" in content or "[tool.pdm]" in content:
            commands.append("pdm build")
        elif "hatchling" in content or "[tool.hatch" in content:
            commands.append("hatch build")
        elif "flit" in content:
            commands.append("flit build")
        elif "poetry" in content:
            commands.append("poetry build")
        else:
            # uv / pip fallback — uv is now common
            commands.append("uv build")

    elif "setup.py" in key_files or "setup.cfg" in key_files:
        commands.append("pip install -e .")

    # Go
    if "go.mod" in key_files:
        commands.append("go build ./...")

    # Rust
    if "Cargo.toml" in key_files:
        commands.append("cargo build --release")

    # Java
    if "pom.xml" in key_files:
        commands.append("mvn package -DskipTests")
    elif "build.gradle" in key_files or "build.gradle.kts" in key_files:
        commands.append("./gradlew build -x test")

    # Docker (only if Dockerfile exists)
    if any(f in key_files for f in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                                     "compose.yml", "compose.yaml")):
        commands.append("docker build -t app .")

    return commands


# ---------------------------------------------------------------------------
# Environment variable detection
# ---------------------------------------------------------------------------

def detect_env_vars(key_files: dict[str, str]) -> list[str]:
    """
    Collect env var names from:
      - .env.example / .env.sample
      - os.getenv / process.env / ENV[] patterns in source files
      - env: sections in GitHub Actions / GitLab CI YAML files
      - ${{ secrets.X }} / ${{ vars.X }} references in workflows
    Returns a deduplicated sorted list.
    """
    found: set[str] = set()
    SKIP_NOISE = {
        "PATH", "HOME", "USER", "SHELL", "PWD", "TERM", "LANG", "LC_ALL",
        "GITHUB_TOKEN", "GITHUB_CONTEXT", "GITHUB_OUTPUT", "GITHUB_ENV",
        "GITHUB_REF", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
        "GITHUB_BASE_REF", "GITHUB_HEAD_REF", "GITHUB_EVENT_NAME",
        "GITHUB_REPOSITORY", "GITHUB_WORKSPACE", "GITHUB_ACTOR",
        "CI", "DEBUG", "NODE_ENV", "CONTEXT",
    }

    # .env.example / .env.sample
    for k in key_files:
        if k in (".env.example", ".env.sample", ".env.template", "example.env"):
            for line in key_files[k].splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    var = line.split("=")[0].strip()
                    if var and re.match(r'^[A-Z_][A-Z0-9_]+$', var) and var not in SKIP_NOISE:
                        found.add(var)

    # Source files: os.getenv / process.env / etc.
    SOURCE_EXTENSIONS = (".py", ".js", ".ts", ".go", ".rb", ".java")
    for k, content in key_files.items():
        if not any(k.endswith(ext) for ext in SOURCE_EXTENSIONS):
            continue
        for pattern in ENV_VAR_PATTERNS:
            for match in pattern.finditer(content):
                var = match.group(1)
                if var and re.match(r'^[A-Z_][A-Z0-9_]+$', var) and var not in SKIP_NOISE:
                    found.add(var)

    # CI YAML files: ${{ secrets.X }} / ${{ vars.X }} references
    secrets_pattern = re.compile(r'\$\{\{\s*(?:secrets|vars)\.([A-Z_][A-Z0-9_]+)\s*\}\}')
    env_key_pattern = re.compile(r'^\s{6,12}([A-Z_][A-Z0-9_]+)\s*:\s*\S', re.MULTILINE)

    for k, content in key_files.items():
        if not (k.endswith(".yml") or k.endswith(".yaml")):
            continue
        for match in secrets_pattern.finditer(content):
            var = match.group(1)
            if var not in SKIP_NOISE:
                found.add(var)
        for match in env_key_pattern.finditer(content):
            var = match.group(1)
            if var not in SKIP_NOISE and re.match(r'^[A-Z_][A-Z0-9_]+$', var):
                found.add(var)

    return sorted(found)


# ---------------------------------------------------------------------------
# Service / dependency detection from docker-compose
# ---------------------------------------------------------------------------

def detect_services(key_files: dict[str, str]) -> list[str]:
    """
    Parse docker-compose.yml to find backing services (postgres, redis, etc.).
    Returns a list of service names the CI pipeline should spin up.
    """
    compose_content = None
    for k in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        if k in key_files:
            compose_content = key_files[k]
            break
    if not compose_content:
        return []

    services: set[str] = set()
    for image_hint, service_name in DOCKER_SERVICE_IMAGES.items():
        if image_hint in compose_content.lower():
            services.add(service_name)
    return sorted(services)


# ---------------------------------------------------------------------------
# Test report detection
# ---------------------------------------------------------------------------

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


def detect_reports(
    all_paths: list[str],
    key_files: dict[str, str],
) -> tuple[bool, list[TestReportInfo]]:
    found: list[TestReportInfo] = []
    seen_formats: set[str] = set()

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


# ---------------------------------------------------------------------------
# Build full ContextPackage from already-fetched key_files + metadata
# ---------------------------------------------------------------------------

def build_context_package(
    key_files: dict[str, str],
    all_paths: list[str],
    directory_tree: str,
    default_branch: str,
    notes: str = "",
) -> ContextPackage:
    languages   = detect_languages(key_files)
    frameworks  = detect_frameworks(key_files)
    build_tools = detect_build_tools(key_files)
    test_runners_flat, test_runner_details = detect_test_runners(key_files)
    has_reports, test_reports              = detect_reports(all_paths, key_files)
    env_vars       = detect_env_vars(key_files)
    services       = detect_services(key_files)
    test_commands  = extract_test_commands(key_files)
    build_commands = extract_build_commands(key_files)

    has_ci = any(
        k.startswith(".github/workflows") or k == ".gitlab-ci.yml" or k == ".travis.yml"
        for k in key_files
    )
    existing_ci_content = next(
        (v for k, v in key_files.items()
         if k.startswith(".github/workflows") or k == ".gitlab-ci.yml"),
        None,
    )

    return ContextPackage(
        languages=languages,
        frameworks=frameworks,
        build_tools=build_tools,
        test_runners=test_runners_flat,
        test_runner_details=test_runner_details,
        has_test_reports=has_reports,
        test_reports=test_reports,
        has_docker=any(f in key_files for f in (
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            "compose.yml", "compose.yaml",
        )),
        has_existing_ci=has_ci,
        existing_ci_content=existing_ci_content,
        key_files=key_files,
        directory_tree=directory_tree,
        default_branch=default_branch,
        env_vars=env_vars,
        services=services,
        test_commands=test_commands,
        build_commands=build_commands,
        notes=notes,
    )
