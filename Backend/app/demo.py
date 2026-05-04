#!/usr/bin/env python3
"""
demo.py — YAML Wizard: RepoContextAgent demo

Shows the agent successfully identifying requirements.txt and Dockerfile
for a public Python repository.

Usage:
    export GITHUB_TOKEN="ghp_..."
    python demo.py

    # Override repo / prompt:
    python demo.py --repo https://github.com/tiangolo/fastapi --prompt "GitLab CI for this FastAPI app"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

# Make sure the app package is importable when running from project root
sys.path.insert(0, ".")

from app.agent.repo_context_agent import run_repo_context_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("demo")

# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

DEMOS = [
    {
        "name": "Python FastAPI — GitHub Actions",
        "repo_url": "https://github.com/tiangolo/fastapi",
        "prompt": "Create a GitHub Actions CI/CD pipeline for this Python FastAPI application.",
    },
    {
        "name": "Node.js Express — Docker + CI",
        "repo_url": "https://github.com/expressjs/express",
        "prompt": "Set up a CI pipeline that builds and tests this Node.js Express app.",
    },
    {
        "name": "Go — GitLab CI",
        "repo_url": "https://github.com/gin-gonic/gin",
        "prompt": "Generate a GitLab CI pipeline with build, test, and lint stages for this Go project.",
    },
]


def run_demo(repo_url: str, prompt: str, name: str, token: str, model: str) -> None:
    print("\n" + "=" * 70)
    print(f"  DEMO: {name}")
    print(f"  Repo: {repo_url}")
    print(f"  Prompt: {prompt}")
    print("=" * 70)

    try:
        package = run_repo_context_agent(
            user_prompt=prompt,
            repo_url=repo_url,
            github_token=token,
            model=model,
        )
    except Exception as exc:
        logger.error("Agent failed: %s", exc)
        return

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n✅  Context Package collected successfully")
    print(f"   Languages : {', '.join(package.languages) or 'N/A'}")
    print(f"   Frameworks: {', '.join(package.frameworks) or 'N/A'}")
    print(f"   Build tools: {', '.join(package.build_tools) or 'N/A'}")
    print(f"   Test runners: {', '.join(package.test_runners) or 'N/A'}")
    print(f"   Has Docker: {package.has_docker}")
    print(f"   Has existing CI: {package.has_existing_ci}")
    print(f"   Files fetched: {list(package.key_files.keys())}")
    print(f"   Notes: {package.notes}")

    print("\n--- Prompt-ready string (first 600 chars) ---")
    print(package.to_prompt_string()[:600])

    # ── Save JSON ─────────────────────────────────────────────────────────
    safe_name = name.lower().replace(" ", "_").replace("/", "-")
    out_path = f"demo_output_{safe_name}.json"
    with open(out_path, "w") as fh:
        json.dump(json.loads(package.to_json()), fh, indent=2)
    print(f"\n📄  Full JSON saved to: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="YAML Wizard Agent demo")
    parser.add_argument("--repo", default=None, help="GitHub repo URL")
    parser.add_argument("--prompt", default=None, help="User DevOps prompt")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model")
    parser.add_argument("--all", action="store_true", help="Run all preset demos")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        logger.warning(
            "GITHUB_TOKEN not set. Unauthenticated requests are rate-limited to 60/hr."
        )

    if args.all:
        for demo in DEMOS:
            run_demo(**demo, token=token, model=args.model)
    elif args.repo and args.prompt:
        run_demo(
            repo_url=args.repo,
            prompt=args.prompt,
            name="custom",
            token=token,
            model=args.model,
        )
    else:
        # Default: Python demo
        demo = DEMOS[0]
        run_demo(**demo, token=token, model=args.model)


if __name__ == "__main__":
    main()