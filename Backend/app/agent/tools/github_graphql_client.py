from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# A GraphQL alias must match /[_A-Za-z][_0-9A-Za-z]*/ — file paths contain
# slashes and dots, so every candidate path gets a sanitized alias and we
# keep a reverse map back to the real path.
_ALIAS_SAFE_RE = re.compile(r"[^0-9A-Za-z_]")


def _make_alias(path: str, index: int) -> str:
    safe = _ALIAS_SAFE_RE.sub("_", path)
    return f"f{index}_{safe}"[:64]  # GraphQL alias length is generous, but keep it sane


class GitHubGraphQLError(Exception):
    """Non-auth, non-retryable GraphQL error (bad query, schema mismatch, etc.)."""


class _CircuitBreaker:
    """
    Minimal circuit breaker, scoped to one client instance (i.e. one repo
    scan). Not meant to be a distributed/shared breaker — its job is to
    stop a single agent run from retrying into a dead endpoint for the
    full duration of a large scan.
    """

    def __init__(self, failure_threshold: int = 4, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.cooldown_seconds:
            # Cooldown elapsed — allow a trial request through (half-open).
            return False
        return True

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._opened_at = time.monotonic()
            logger.warning(
                "GitHubGraphQLClient circuit breaker OPEN after %d consecutive failures; "
                "cooling down for %.0fs",
                self._consecutive_failures, self.cooldown_seconds,
            )

    def assert_closed(self) -> None:
        if self.is_open:
            raise GitHubGraphQLError(
                "GitHub GraphQL circuit breaker is open (too many recent failures); "
                "skipping call until cooldown elapses."
            )


def _is_retryable_http_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException) or isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        # 401/403 are auth/permission problems — never retryable.
        # 404 means "not found" — also not retryable.
        # 429/5xx are transient — retry with backoff.
        return status == 429 or status >= 500
    return False


@dataclass
class GraphQLFileResult:
    path: str
    content: str | None       # None if file does not exist / not a blob
    is_binary: bool = False


@dataclass
class GraphQLRootListing:
    default_branch: str
    entries: list[dict]                       # [{"name": ..., "type": "file"|"dir"}, ...]
    files: dict[str, GraphQLFileResult] = field(default_factory=dict)


class GitHubGraphQLClient:
    """
    Thin wrapper around the GitHub GraphQL v4 API, scoped to read-only
    repo-content scanning. Holds a short-lived httpx client and a
    per-instance circuit breaker.
    """

    def __init__(self, token: str, timeout: float = 15.0):
        if not token:
            raise PermissionError("GitHub token is required for GraphQL access.")
        self._token = token
        self._timeout = timeout
        self._breaker = _CircuitBreaker()

    # ── low-level transport ────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential_jitter(initial=0.5, max=8.0),
        reraise=True,
    )
    def _post(self, query: str, variables: dict[str, Any]) -> dict:
        self._breaker.assert_closed()
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    GITHUB_GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "yaml-wizard-repo-fetcher",
                    },
                )
            if resp.status_code in (401, 403):
                # Don't let tenacity retry auth failures.
                self._breaker.record_failure()
                raise PermissionError(
                    "GitHub token is invalid, expired, or lacks access to this repository."
                )
            resp.raise_for_status()
            payload = resp.json()
        except PermissionError:
            raise
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
            if not _is_retryable_http_error(exc) and isinstance(exc, httpx.HTTPStatusError):
                self._breaker.record_failure()
                if exc.response.status_code == 404:
                    raise FileNotFoundError("GitHub repository not found.") from exc
                raise
            # Retryable — let tenacity handle backoff; record failure for the breaker
            # on the final exhausted attempt via the caller's except block below.
            raise

        if "errors" in payload and not payload.get("data"):
            self._breaker.record_failure()
            messages = "; ".join(e.get("message", "unknown") for e in payload["errors"])
            raise GitHubGraphQLError(f"GitHub GraphQL error: {messages}")

        self._breaker.record_success()
        return payload.get("data", {})

    def _post_with_breaker_accounting(self, query: str, variables: dict[str, Any]) -> dict:
        """Wraps _post so retry exhaustion still trips the breaker exactly once."""
        try:
            return self._post(query, variables)
        except PermissionError:
            raise
        except FileNotFoundError:
            raise
        except Exception:
            self._breaker.record_failure()
            raise

    # ── public API ──────────────────────────────────────────────────────────

    def fetch_root_and_files(
        self,
        owner: str,
        repo: str,
        candidate_paths: list[str],
    ) -> GraphQLRootListing:
        """
        ONE GraphQL request that returns:
          - the repository's default branch
          - the root directory listing
          - the content of every path in `candidate_paths` that exists as a
            blob on the default branch (aliased fields, batched)

        Non-existent paths simply come back null — no error, no extra
        round-trip needed to "check if it exists first".
        """
        aliases: dict[str, str] = {_make_alias(p, i): p for i, p in enumerate(candidate_paths)}

        file_fragments = "\n".join(
            f'{alias}: object(expression: "HEAD:{_escape(path)}") {{ '
            f'... on Blob {{ text isBinary }} }}'
            for alias, path in aliases.items()
        )

        query = f"""
        query($owner: String!, $repo: String!) {{
          repository(owner: $owner, name: $repo) {{
            defaultBranchRef {{ name }}
            rootTree: object(expression: "HEAD:") {{
              ... on Tree {{
                entries {{
                  name
                  type
                }}
              }}
            }}
            {file_fragments}
          }}
        }}
        """

        data = self._post_with_breaker_accounting(query, {"owner": owner, "repo": repo})
        repository = data.get("repository")
        if repository is None:
            raise FileNotFoundError(f"GitHub repository not found: {owner}/{repo}")

        default_branch = (repository.get("defaultBranchRef") or {}).get("name") or "main"

        root_tree = repository.get("rootTree") or {}
        raw_entries = root_tree.get("entries") or []
        entries = [
            {"name": e.get("name", ""), "type": "dir" if e.get("type") == "tree" else "file"}
            for e in raw_entries
        ]

        files: dict[str, GraphQLFileResult] = {}
        for alias, path in aliases.items():
            blob = repository.get(alias)
            if not blob:
                files[path] = GraphQLFileResult(path=path, content=None)
                continue
            files[path] = GraphQLFileResult(
                path=path,
                content=blob.get("text"),
                is_binary=bool(blob.get("isBinary")),
            )

        return GraphQLRootListing(default_branch=default_branch, entries=entries, files=files)

    def fetch_files(self, owner: str, repo: str, paths: list[str]) -> dict[str, GraphQLFileResult]:
        """
        Fetch an arbitrary batch of file paths in ONE request (e.g. files
        discovered inside .github/workflows/ or backend/ after the first
        call revealed their names). Returns only paths that resolved to
        a blob with text content.
        """
        if not paths:
            return {}

        aliases: dict[str, str] = {_make_alias(p, i): p for i, p in enumerate(paths)}
        file_fragments = "\n".join(
            f'{alias}: object(expression: "HEAD:{_escape(path)}") {{ '
            f'... on Blob {{ text isBinary }} }}'
            for alias, path in aliases.items()
        )
        query = f"""
        query($owner: String!, $repo: String!) {{
          repository(owner: $owner, name: $repo) {{
            {file_fragments}
          }}
        }}
        """
        data = self._post_with_breaker_accounting(query, {"owner": owner, "repo": repo})
        repository = data.get("repository") or {}

        results: dict[str, GraphQLFileResult] = {}
        for alias, path in aliases.items():
            blob = repository.get(alias)
            if blob and blob.get("text") is not None:
                results[path] = GraphQLFileResult(
                    path=path, content=blob.get("text"), is_binary=bool(blob.get("isBinary"))
                )
        return results

    def list_directory(self, owner: str, repo: str, path: str, ref: str = "HEAD") -> list[dict]:
        """Single-directory listing (used for discovering subdir contents, e.g. .github/workflows)."""
        query = """
        query($owner: String!, $repo: String!, $expr: String!) {
          repository(owner: $owner, name: $repo) {
            object(expression: $expr) {
              ... on Tree {
                entries { name type }
              }
            }
          }
        }
        """
        expr = f"{ref}:{path}" if ref != "HEAD" else f"HEAD:{path}"
        data = self._post_with_breaker_accounting(query, {"owner": owner, "repo": repo, "expr": expr})
        repository = data.get("repository") or {}
        obj = repository.get("object") or {}
        raw_entries = obj.get("entries") or []
        return [
            {"name": e.get("name", ""), "type": "dir" if e.get("type") == "tree" else "file"}
            for e in raw_entries
        ]


def _escape(path: str) -> str:
    """Escape characters that would break the GraphQL expression string literal."""
    return path.replace("\\", "\\\\").replace('"', '\\"')
