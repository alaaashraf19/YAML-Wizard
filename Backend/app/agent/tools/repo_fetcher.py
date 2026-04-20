from __future__ import annotations

import shutil
from pathlib import Path

from git import Repo
from app.schemas.repo_schema import Platform, RepoContext
from utils.helpers import get_temp_dir, build_directory_tree, read_file_safe


# Files that reveal project structure and dependencies
KEY_FILES = {
    # Python
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Pipfile", "poetry.lock", "tox.ini", ".flake8", "mypy.ini",
    # JavaScript / TypeScript
    "package.json", "tsconfig.json", ".eslintrc.json", ".eslintrc.js",
    "webpack.config.js", "vite.config.ts", "vite.config.js",
    "next.config.js", "next.config.mjs",
    # Java / Kotlin
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    # Go
    "go.mod", "go.sum",
    # Rust
    "Cargo.toml",
    # Ruby
    "Gemfile", "Rakefile",
    # Docker
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    # CI existing
    ".github/workflows", ".gitlab-ci.yml",
    # General
    "Makefile", ".env.example",
}

LANGUAGE_INDICATORS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "*.py"],
    "javascript": ["package.json", "*.js", "*.jsx"],
    "typescript": ["tsconfig.json", "*.ts", "*.tsx"],
    "java": ["pom.xml", "build.gradle", "*.java"],
    "go": ["go.mod", "*.go"],
    "rust": ["Cargo.toml", "*.rs"],
    "ruby": ["Gemfile", "*.rb"],
    "csharp": ["*.csproj", "*.sln"],
}


FRAMEWORK_INDICATORS: dict[str, list[str]] = {
    "react": ["react", "react-dom"],
    "next.js": ["next"],
    "vue": ["vue"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "spring": ["spring-boot", "spring-web"],
    "express": ["express"],
    "rails": ["rails"],
}

def fetch_repo(repo_url: str, platform: str) -> RepoContext:
    """Clone a public repo and extract context for YAML generation."""
    tmp_dir = get_temp_dir()
    try:
        repo = Repo.clone_from(repo_url, tmp_dir, depth=1)#shallow clone only latest commit which is faster and we only need current state of repo for context extraction
        default_branch = _get_default_branch(repo)

        root = Path(tmp_dir)
        tree = build_directory_tree(root, max_depth=3)

        # Read key files
        key_files: dict[str, str] = {}
        for kf in KEY_FILES:
            path = root / kf
            if path.is_file():
                key_files[kf] = read_file_safe(path)
            elif path.is_dir():
                # e.g. .github/workflows — list contents
                if path.exists():
                    contents = [f.name for f in path.iterdir() if f.is_file()]
                    key_files[kf] = ", ".join(contents) if contents else "[empty]"

        # Also read existing CI files
        existing_ci = _read_existing_ci(root, platform)

        languages = _detect_languages(root, key_files)
        frameworks = _detect_frameworks(key_files)
        build_tools = _detect_build_tools(key_files)
        test_runners = _detect_test_runners(key_files)
        has_docker = (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists()

        return RepoContext(
            url=repo_url,
            platform=Platform(platform),
            default_branch=default_branch,
            languages=languages,
            frameworks=frameworks,
            build_tools=build_tools,
            test_runners=test_runners,
            has_docker=has_docker,
            has_existing_ci=existing_ci is not None,
            existing_ci_content=existing_ci,
            directory_tree=tree,
            key_files=key_files,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


        
def _get_default_branch(repo: Repo) -> str:
    """Get the default branch name."""
    try:
        return str(repo.active_branch)
    except TypeError:
        return "main"
    
def _read_existing_ci(root: Path, platform: str) -> str | None:
    """Read existing CI configuration if present."""
    if platform == "github":
        workflows_dir = root / ".github" / "workflows"
        if workflows_dir.is_dir():
            parts = []
            for f in workflows_dir.iterdir():
                if f.suffix in (".yml", ".yaml"):
                    parts.append(f"# --- {f.name} ---\n{read_file_safe(f)}")
            return "\n\n".join(parts) if parts else None
    elif platform == "gitlab":
        ci_file = root / ".gitlab-ci.yml"
        if ci_file.is_file():
            return read_file_safe(ci_file)
    return None

def _detect_languages(root: Path, key_files: dict[str, str]) -> list[str]:
    """Detect programming languages used in the project."""
    detected = []
    file_extensions = set()
    for p in root.rglob("*"):
        if p.is_file() and p.suffix:
            file_extensions.add(p.suffix.lower())

    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript",
        ".java": "java", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".cs": "csharp", ".php": "php",
    }
    for ext, lang in ext_map.items():
        if ext in file_extensions and lang not in detected:
            detected.append(lang)

    # Also check key files
    if "pyproject.toml" in key_files or "requirements.txt" in key_files:
        if "python" not in detected:
            detected.append("python")
    if "package.json" in key_files:
        if "javascript" not in detected:
            detected.append("javascript")
    if "go.mod" in key_files:
        if "go" not in detected:
            detected.append("go")

    return detected


def _detect_frameworks(key_files: dict[str, str]) -> list[str]:
    """Detect frameworks from dependency files."""
    detected = []
    # Check package.json
    pkg_json = key_files.get("package.json", "")
    for framework, indicators in FRAMEWORK_INDICATORS.items():
        for indicator in indicators:
            if indicator in pkg_json:
                detected.append(framework)
                break

    # Check Python deps
    for pyfile in ("pyproject.toml", "requirements.txt", "Pipfile"):
        content = key_files.get(pyfile, "")
        for framework, indicators in FRAMEWORK_INDICATORS.items():
            if framework not in detected:
                for indicator in indicators:
                    if indicator in content:
                        detected.append(framework)
                        break

    return detected

def _detect_build_tools(key_files: dict[str, str]) -> list[str]:
    """Detect build tools from key files."""
    tools = []
    if "package.json" in key_files:
        pkg = key_files["package.json"]
        if '"build"' in pkg:
            tools.append("npm/yarn build")
        if "webpack" in pkg:
            tools.append("webpack")
        if "vite" in pkg:
            tools.append("vite")
    if "Makefile" in key_files:
        tools.append("make")
    if "pom.xml" in key_files:
        tools.append("maven")
    if "build.gradle" in key_files or "build.gradle.kts" in key_files:
        tools.append("gradle")
    if "Cargo.toml" in key_files:
        tools.append("cargo")
    if "pyproject.toml" in key_files:
        content = key_files.get("pyproject.toml", "")
        if "poetry" in content:
            tools.append("poetry")
        elif "setuptools" in content:
            tools.append("setuptools")
    return tools

def _detect_test_runners(key_files: dict[str, str]) -> list[str]:
    """Detect test runners from key files."""
    runners = []
    # Python
    for pyfile in ("pyproject.toml", "setup.cfg", "tox.ini"):
        content = key_files.get(pyfile, "")
        if "pytest" in content:
            runners.append("pytest")
            break
        if "unittest" in content:
            runners.append("unittest")
            break

    # JS/TS
    pkg = key_files.get("package.json", "")
    if "jest" in pkg:
        runners.append("jest")
    if "mocha" in pkg:
        runners.append("mocha")
    if "vitest" in pkg:
        runners.append("vitest")

    # Java
    if "pom.xml" in key_files:
        pom = key_files["pom.xml"]
        if "junit" in pom.lower():
            runners.append("junit")
        if "surefire" in pom:
            runners.append("maven-surefire")

    # Go (built-in)
    if "go.mod" in key_files:
        runners.append("go test")

    return runners

    
