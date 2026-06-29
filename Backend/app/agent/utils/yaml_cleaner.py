
from __future__ import annotations

import logging
import re
from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import FoldedScalarString, LiteralScalarString

logger = logging.getLogger(__name__)


REDACTED = "<REDACTED>"

# Keys whose *exact* name (or name fragment between word boundaries /
# underscores / hyphens) indicates the value is a secret.
SENSITIVE_KEY_PATTERNS: list[re.Pattern] = [
    re.compile(r"(^|[_\-])password($|[_\-])", re.I),
    re.compile(r"(^|[_\-])secret($|[_\-])", re.I),
    re.compile(r"(^|[_\-])token($|[_\-])", re.I),
    re.compile(r"(^|[_\-])api[_\-]?key$", re.I),
    re.compile(r"(^|[_\-])private[_\-]?key$", re.I),
    re.compile(r"(^|[_\-])client[_\-]?secret$", re.I),
    re.compile(r"(^|[_\-])auth($|[_\-])", re.I),
    re.compile(r"(^|[_\-])credential", re.I),
    re.compile(r"(^|[_\-])pat$", re.I),
    re.compile(r"[_\-]key$", re.I),
    re.compile(r"(^|[_\-])pass($|[_\-])", re.I),       # docker_pass, db_pass, redis_pass
    re.compile(r"(^|[_\-])passwd($|[_\-])", re.I),     # db_passwd
    re.compile(r"(^|[_\-])passphrase($|[_\-])", re.I), # ssh_passphrase
]

# Well-known token formats — matched with .search() so they're found
# anywhere inside a longer string (e.g. "Bearer <token>").
TOKEN_PATTERNS: list[re.Pattern] = [
    # JWT:  xxxxx.yyyyy.zzzzz
    re.compile(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
    # GitHub classic PAT (36 chars historically, but length can vary)
    re.compile(r"ghp_[a-zA-Z0-9]{32,}"),
    # GitHub fine-grained PAT
    re.compile(r"github_pat_[a-zA-Z0-9_]{82}"),
    # GitLab PAT
    re.compile(r"glpat-[a-zA-Z0-9_-]{20}"),
    # AWS Access Key ID
    re.compile(r"AKIA[0-9A-Z]{16}"),
    # Google API key
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    # Anthropic / Claude key
    re.compile(r"sk-ant-[a-zA-Z0-9_\-]{40,}"),
    # OpenAI key
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),
    # Slack tokens  (xoxb-, xoxp-, xoxa-, xoxr-, xoxs-)
    re.compile(r"xox[baprs]-[a-zA-Z0-9\-]{10,}"),
    # Generic high-entropy base64 (40+ chars)
    re.compile(r"[a-zA-Z0-9+/]{40,}={0,2}"),
]

# Strings that look like secrets but are actually *references* — keep them.
SAFE_REFERENCE_RE = re.compile(
    r"\$\{\{\s*secrets\.\w+\s*\}\}"    # ${{ secrets.X }}
    r"|\$\{\{\s*github\.token\s*\}\}"  # ${{ github.token }}
    r"|\$\{[A-Z_][A-Z0-9_]*\}"         # ${VAR}
    r"|\$[A-Z_][A-Z0-9_]*$"            # $VAR  (whole string)
    r"|\$CI_[A-Z_]+"                   # $CI_JOB_TOKEN etc.
)

# "Authorization: Bearer <token>" / "Basic <b64>" embedded in strings.
AUTH_HEADER_RE = re.compile(
    r"(?i)(Bearer\s+)([A-Za-z0-9\-_\.]+)"
    r"|(Basic\s+)([A-Za-z0-9+/=]+)"
)

# Shell variable assignments inside multiline blocks.
# Matches both "export KEY=value" and bare "KEY=value" at the start of a line.
# The "export" keyword is optional — shell scripts frequently assign without it.
SHELL_ASSIGNMENT_RE = re.compile(
    r"(?im)"                                               # multiline + ignorecase
    r"^(\s*(?:export\s+)?)"                               # optional indent + "export"
    r"(\w*(?:TOKEN|SECRET|KEY|PASSWORD|AUTH|CRED|PAT|ACCESS)\w*)"  # sensitive var name
    r"(\s*=\s*)"                                           # equals sign
    r"(['\"]?)(\S+?)(\4)"                                 # optional quotes + value
    r"(?=\s*$|\s*[;#])"                                   # end of line, ; or # comment
)

# Line pattern for .env / shell-export files (KEY=VALUE format).
# KEY=value or KEY = value patterns inside flat/collapsed strings that have
# no newlines (e.g. when ruamel folds a multi-line env block into one string).
# Unlike SHELL_ASSIGNMENT_RE this does NOT use ^ / multiline anchors.
FLAT_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b\w*(?:TOKEN|SECRET|KEY|PASSWORD|AUTH|CRED|PAT|ACCESS)\w*"
    r"\s*=\s*)(\S+)"
)

ENV_LINE_RE = re.compile(
    r"^(\s*(?:export\s+)?)?"                             # optional indent + "export"
    r"([A-Za-z_][A-Za-z0-9_]*)"                         # variable name
    r"(\s*=\s*)"                                         # equals sign
    r"(.*?)(\s*)$"                                       # value + trailing whitespace
)

# YAML keys that introduce a flat name→value mapping where every child
# key name is itself a secret identifier. Each child is inspected by
# _is_sensitive_key() individually so non-secret siblings are kept.
ENV_SECTION_KEYS = {"env", "variables", "environment", "secrets"}

# Sibling keys that carry the actual secret value in name/value pair lists.
# Pattern:  - name: SECRET_KEY      ← identifier in 'name'
#             value: actual-secret  ← secret in 'value' / 'defaultValue' etc.
# Used by Kubernetes manifests, Docker Compose env lists, CircleCI, Jenkins.
NAME_VALUE_SIBLINGS = {"value", "defaultValue", "default", "val"}


def _redact_env_file(content: str) -> str:
    """
    Redact a .env / dotenv file line by line.

    Called when ruamel parses the content as a plain scalar string rather
    than a structured mapping — which happens with KEY=VALUE files because
    that format is technically valid YAML bare scalar syntax.
    Comments and blank lines are preserved unchanged.
    """
    lines = content.splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n")
        # Preserve blank lines and comments
        if not stripped.strip() or stripped.strip().startswith("#"):
            out.append(line)
            continue
        m = ENV_LINE_RE.match(stripped)
        if m:
            prefix, key, eq, value, trail = m.groups()
            prefix = prefix or ""
            if _is_sensitive_key(key) or _contains_known_token(value):
                out.append(f"{prefix}{key}{eq}{REDACTED}{trail}\n")
            else:
                out.append(line)
        else:
            out.append(line)
    return "".join(out)





def redact_secrets(content: str) -> str:
    """
    Redact sensitive values from a CI/CD pipeline YAML string.

    Returns a YAML string with secrets replaced by ``<REDACTED>``.
    All comments, key order, indentation, quotes, multiline blocks,
    and anchors are preserved.

    Also handles .env / dotenv files (KEY=VALUE format) correctly —
    ruamel parses these as plain scalar strings rather than mappings,
    so the function detects this and falls through to a line-by-line
    redactor instead.

    Falls back to ``_redact_env_file`` if ruamel raises any exception
    (e.g. unresolved templating syntax).
    """
    yaml = _make_yaml_parser(content)  # pass content for sequence-indent detection
    try:
        data = yaml.load(content)
        if data is None:
            return content
        # .env and shell-export files parse as a plain str in YAML
        # (KEY=VALUE is a valid bare scalar). Route to the line-by-line redactor.
        if not isinstance(data, (CommentedMap, CommentedSeq)):
            return _redact_env_file(content)
        _recursive_clean(data)
        buf = StringIO()
        yaml.dump(data, buf)
        return buf.getvalue()
    except Exception as exc:
        logger.warning(
            "ruamel.yaml could not parse content — falling back to "
            "regex-based redaction. Reason: %s",
            exc,
        )
        # Content is genuinely malformed YAML (tab indentation, duplicate keys,
        # etc.). _regex_fallback scans arbitrary text by pattern, which is more
        # appropriate here than the line-by-line KEY=VALUE logic of _redact_env_file.
        return _regex_fallback(content)


# ---------------------------------------------------------------------------
# Internal helpers — detection
# ---------------------------------------------------------------------------


def _is_sensitive_key(key: str) -> bool:
    """Return True when *key* indicates its value is a secret."""
    return any(p.search(key) for p in SENSITIVE_KEY_PATTERNS)


def _is_safe_reference(value: str) -> bool:
    """Return True when *value* is a variable reference, not a real secret."""
    return bool(SAFE_REFERENCE_RE.search(value.strip()))


def _contains_known_token(value: str) -> bool:
    """Return True when *value* contains a recognisable token format."""
    return any(p.search(value) for p in TOKEN_PATTERNS)


# ---------------------------------------------------------------------------
# Internal helpers — redaction
# ---------------------------------------------------------------------------


def _redact_scalar(value: str) -> str:
    """
    Redact secret content embedded inside an otherwise plain string.

    Safe references and non-secret strings are returned unchanged.
    Known token patterns are replaced in-place (the surrounding text
    is preserved), then auth-header patterns are applied.
    """
    if _is_safe_reference(value):
        return value

    result = value

    # Replace only the token portion, keeping surrounding text intact.
    if _contains_known_token(result):
        for pattern in TOKEN_PATTERNS:
            result = pattern.sub(REDACTED, result)

    # "Bearer <token>" / "Basic <b64>" anywhere in the string.
    result = AUTH_HEADER_RE.sub(
        lambda m: (m.group(1) or m.group(3)) + REDACTED,
        result,
    )

    # KEY=value assignments in flat/collapsed strings (no newlines).
    # Catches cases where ruamel folds an indented continuation block into
    # a single string: "GITHUB_TOKEN = abc DOCKER_PASSWORD = xyz".
    def _flat_replace(m: re.Match) -> str:
        val = m.group(2)
        if val.startswith("$") or _is_safe_reference(val):
            return m.group(0)
        return m.group(1) + REDACTED

    result = FLAT_ASSIGNMENT_RE.sub(_flat_replace, result)

    return result


def _redact_multiline(value: str) -> str:
    """
    Redact secrets inside a shell-script-like multiline block.

    Handles both ``export KEY=value`` and bare ``KEY=value`` assignments,
    plus Authorization headers. Safe references like ``${{ secrets.X }}``
    and ``$VAR`` are preserved even when the key name matches.
    """
    def _replace(m: re.Match) -> str:
        lead, name, eq, q1, val, q2 = m.groups()
        # Preserve variable references — these are not real credentials
        if SAFE_REFERENCE_RE.fullmatch(val.strip()):
            return m.group(0)
        return f"{lead}{name}{eq}{q1}{REDACTED}{q2}"

    value = SHELL_ASSIGNMENT_RE.sub(_replace, value)
    value = AUTH_HEADER_RE.sub(
        lambda m: (m.group(1) or m.group(3)) + REDACTED,
        value,
    )
    return value


def _redact_env_section(mapping: CommentedMap) -> None:
    """
    Inspect every variable inside an env / variables / environment block.

    Variables whose *name* matches a sensitive pattern are redacted
    entirely; others are passed through ``_redact_scalar`` so that
    hardcoded tokens embedded in non-sensitive variables are still caught.
    """
    for var_name in mapping:
        var_val = mapping[var_name]
        if not isinstance(var_val, str):
            continue
        if _is_safe_reference(var_val):
            continue
        if _is_sensitive_key(str(var_name)):
            mapping[var_name] = REDACTED
        else:
            mapping[var_name] = _redact_scalar(var_val)


# ---------------------------------------------------------------------------
# Recursive traversal
# ---------------------------------------------------------------------------


def _handle_name_value_item(item: CommentedMap) -> None:
    """
    Redact the value in a name/value pair list item when the name is sensitive.

    Handles the pattern used by Kubernetes Secret manifests, Docker Compose
    environment lists, CircleCI, and Jenkins::

        - name: SECRET_ONE          # ← sensitive identifier
          value: "actual-secret"   # ← this gets redacted

    ``valueFrom`` and other structured references (``secretKeyRef`` etc.)
    are left untouched because they are already indirection, not raw secrets.
    Safe references like ``${{ secrets.X }}`` in the value are also preserved.
    """
    name_val = str(item.get("name", ""))
    if not _is_sensitive_key(name_val):
        return
    for sibling in NAME_VALUE_SIBLINGS:
        if sibling in item:
            v = item[sibling]
            if isinstance(v, str) and not _is_safe_reference(v):
                item[sibling] = REDACTED


def _recursive_clean(obj: Any) -> None:
    """
    Walk the ruamel.yaml object tree in-place, redacting secrets.

    ruamel.yaml represents YAML mappings as ``CommentedMap`` and sequences
    as ``CommentedSeq``; both carry inline comments so they survive.
    Multiline scalars are ``LiteralScalarString`` (``|``) or
    ``FoldedScalarString`` (``>``); their type is preserved so the YAML
    block style is retained on serialisation.
    """
    if isinstance(obj, CommentedMap):
        for key in obj:
            value = obj[key]
            key_str = str(key)

            # ── env / variables / environment sections ───────────────────
            if key_str.lower() in ENV_SECTION_KEYS and isinstance(value, CommentedMap):
                _redact_env_section(value)
                continue

            # ── sensitive key → redact value if it's a leaf string ───────
            if _is_sensitive_key(key_str):
                if isinstance(value, str):
                    if not _is_safe_reference(value):
                        obj[key] = REDACTED
                    continue  # string is a leaf — nothing deeper to visit
                # value is a dict or list (e.g. a "credentials:" block) —
                # do NOT stop here; fall through to recurse into it so that
                # sensitive leaf keys inside it are still redacted.

            # ── multiline block scalars ───────────────────────────────────
            if isinstance(value, (LiteralScalarString, FoldedScalarString)):
                cleaned = _redact_multiline(str(value))
                # Re-wrap in the same type so ruamel.yaml emits "|" or ">"
                obj[key] = type(value)(cleaned)
                continue

            # ── plain strings ─────────────────────────────────────────────
            if isinstance(value, str):
                obj[key] = _redact_scalar(value)
                continue

            # ── nested structures ─────────────────────────────────────────
            _recursive_clean(value)

    elif isinstance(obj, (CommentedSeq, list)):
        for item in obj:
            # ── name/value pair pattern ───────────────────────────────────
            # Check before recursing: if this list item is a dict with a
            # 'name' key, it may use the name/value pattern where the secret
            # identifier is in 'name' and the value is in a sibling key.
            if isinstance(item, CommentedMap) and "name" in item:
                _handle_name_value_item(item)
            _recursive_clean(item)


# ---------------------------------------------------------------------------
# Regex fallback (used only when YAML parsing fails)
# ---------------------------------------------------------------------------


def _regex_fallback(content: str) -> str:
    """
    Pattern-based redaction for genuinely malformed YAML.

    Called only when ruamel raises a parse exception (e.g. tab indentation,
    duplicate keys). Works on raw text without structural assumptions, so it
    catches secrets regardless of surrounding syntax.

    Safe references (``${{ secrets.X }}``, ``$VAR``) are preserved.
    Key names are always kept — only values are replaced.
    """

    def _guard(m: re.Match, value_group: int, repl_fn) -> str:
        """Apply repl_fn only if the matched value is not a safe reference."""
        value = m.group(value_group) if len(m.groups()) >= value_group else m.group(0)
        # Values starting with $ are variable references — never real secrets
        if value.startswith("$"):
            return m.group(0)
        if SAFE_REFERENCE_RE.search(m.group(0)):
            return m.group(0)
        return repl_fn(m)

    # ── Pattern 1: full key name contains a sensitive word ────────────────
    # Matches: SECRET_TOKEN: value, API_KEY=value, DOCKER_PASSWORD: 'value'
    # Preserves the full key name; replaces only the value.
    p_key_contains = re.compile(
        r"(?i)([A-Za-z_][A-Za-z0-9_]*"
        r"(?:token|secret|key|password|auth|credential|pat|pass)[A-Za-z0-9_]*"
        r"\s*[:=]\s*)"
        r"(['\"]?)([^\s'\"#\n]+)(\2)"
    )
    content = p_key_contains.sub(
        lambda m: _guard(m, 3, lambda m: m.group(1) + REDACTED),
        content,
    )

    # ── Pattern 2: key IS a sensitive word ───────────────────────────────
    # Matches: password: value, secret: value, token: value
    p_key_is = re.compile(
        r"(?im)((?:^|\s)"
        r"(?:password|secret|token|api_key|auth|credential|private_key|passphrase)"
        r"\s*[:=]\s*)"
        r"(['\"]?)([^\s'\"#\n]+)(\2)"
    )
    content = p_key_is.sub(
        lambda m: _guard(m, 3, lambda m: m.group(1) + REDACTED),
        content,
    )

    # ── Pattern 3: Bearer / Basic auth headers ────────────────────────────
    p_bearer = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9\-_\.]+)")
    p_basic  = re.compile(r"(?i)(Basic\s+)([A-Za-z0-9+/=]+)")
    content = p_bearer.sub(lambda m: _guard(m, 2, lambda m: m.group(1) + REDACTED), content)
    content = p_basic.sub( lambda m: _guard(m, 2, lambda m: m.group(1) + REDACTED), content)

    # ── Pattern 4: named token formats anywhere in the text ───────────────
    p_named_tokens = re.compile(
        r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"   # JWT
        r"|ghp_[a-zA-Z0-9]{36}"                                  # GitHub classic PAT
        r"|glpat-[a-zA-Z0-9_\-]{20}"                             # GitLab PAT
        r"|AKIA[0-9A-Z]{16}"                                      # AWS key ID
        r"|AIza[0-9A-Za-z_\-]{35}"                               # Google API key
        r"|sk-ant-[a-zA-Z0-9_\-]{40,}"                           # Anthropic key
        r"|sk-[a-zA-Z0-9]{32,}"                                   # OpenAI key
    )
    content = p_named_tokens.sub(
        lambda m: m.group(0) if SAFE_REFERENCE_RE.search(m.group(0)) else REDACTED,
        content,
    )

    # ── Pattern 5: bare shell assignments (KEY=value, export KEY=value) ───
    content = SHELL_ASSIGNMENT_RE.sub(
        lambda m: (
            m.group(0) if m.group(5).startswith("$")
            else f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{REDACTED}{m.group(6)}"
        ),
        content,
    )

    # ── Pattern 6: name/value pair lists ─────────────────────────────────
    # Handles:
    #   - name: SECRET_ONE        ← sensitive identifier in name field
    #     value: "actual-secret"  ← this gets redacted
    # Used by Kubernetes manifests, Docker Compose env lists, CircleCI.
    name_value_re = re.compile(
        r"(?im)"
        r"(name:\s*['\"]?\w*"
        r"(?:TOKEN|SECRET|KEY|PASSWORD|AUTH|CRED|PAT|ACCESS|PASS)\w*['\"]?"
        r"\s*\n\s*)"
        r"(value:\s*)"
        r"(['\"]?)([^\n#]+?)(\3)"
        r"(?=\s*$|\s*#)"
    )
    content = name_value_re.sub(
        lambda m: (
            m.group(0) if (
                m.group(4).strip().startswith("$") or
                _is_safe_reference(m.group(4))
            ) else m.group(1) + m.group(2) + m.group(3) + REDACTED + m.group(5)
        ),
        content,
    )
    return content


# ---------------------------------------------------------------------------
# YAML parser factory
# ---------------------------------------------------------------------------


def _detect_sequence_indent(content: str) -> tuple:
    """
    Detect the sequence indentation style used in *content*.

    Looks for the first key:\n  - item pattern and measures how many
    spaces precede the dash relative to its parent key. Returns
    (sequence_indent, dash_offset) so ruamel reproduces the same style
    on serialisation, or (None, None) when no indented list items are found.

    Examples::

        stages:        sequence_indent=2, dash_offset=2  ->  "  - item"
          - test
        stages:        sequence_indent=4, dash_offset=4  ->  "    - item"
            - test
        stages:        (None, None) - dash at key level, ruamel default is fine
        - test
    """
    lines = content.splitlines()
    for i, line in enumerate(lines[:-1]):
        if not re.match(r"^(\s*)\S+.*:\s*$", line):
            continue
        key_indent = len(line) - len(line.lstrip())
        for j in range(i + 1, min(i + 5, len(lines))):
            next_line = lines[j]
            if not next_line.strip():
                continue
            m = re.match(r"^(\s*)-\s", next_line)
            if m:
                item_indent = len(m.group(1))
                relative = item_indent - key_indent
                if relative > 0:
                    return item_indent, relative
            break
    return None, None


def _make_yaml_parser(content: str = "") -> YAML:
    """
    Return a ruamel.yaml instance configured for maximum fidelity.

    When *content* is provided the sequence indentation style is detected
    from it and applied to the parser so that yaml.dump reproduces the
    original "  - item" vs "- item" style faithfully.
    """
    yaml = YAML()
    yaml.preserve_quotes = True   # keeps 'single' and "double" quotes as-is
    yaml.width = 4096             # prevents unwanted line wrapping
    seq_indent, dash_offset = _detect_sequence_indent(content)
    if seq_indent is not None:
        yaml.sequence_indent = seq_indent
        yaml.sequence_dash_offset = dash_offset
    return yaml