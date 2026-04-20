
from pathlib import Path
import tempfile


#creates a temp dir for cloning repos, ensures cleanup after use
def get_temp_dir(prefix: str = "yaml-wizard-") -> Path:
    """Create and return a temporary directory."""
    return Path(tempfile.mkdtemp(prefix=prefix))


#build dir tree helps in understanding the project layout 
#useful in AI/YAML generation to know where to place files and how to reference them in CI config
#example of directory tree output:
# repo/
# ├── README.md
# ├── src/
# │   ├── main.py
# │   ├── api/
# │   │   ├── routes.py
# │   │   ├── v1/  -> depth 3 included but contents not explored further
# │   │   │   ├── users.py
# │   │   │   └── auth/
# │   │   │       └── login.py
# ├── tests/
# │   └── test_main.py
def build_directory_tree(root: Path, max_depth: int = 3, prefix: str = "") -> str:
    """Build a string representation of a directory tree."""
    if max_depth < 0:
        return ""

    lines: list[str] = []
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name)) #dirs come first then files
    except PermissionError:
        return ""

    # Filter out hidden dirs and common noise
    skip = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".mypy_cache"}
    entries = [e for e in entries if e.name not in skip]

    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}") #prefix is identation for nested levels
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            subtree = build_directory_tree(entry, max_depth - 1, prefix + extension)
            if subtree:
                lines.append(subtree)

    return "\n".join(lines)


def read_file_safe(path: Path, max_bytes: int = 50_000) -> str:
    """Read a file, returning empty string on failure or if too large."""
    try:
        if path.stat().st_size > max_bytes:
            return f"[file too large: {path.stat().st_size} bytes]"
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""