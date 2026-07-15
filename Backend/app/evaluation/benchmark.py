"""Benchmark runner — evaluate YAML generation across multiple repos."""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.dashboard import RepoCreate
from agent.chatbot_agent import ChatbotAgent
from .comparator import ComparisonResult, compare_yaml
from .scorer import ScoreBreakdown, score_yaml
from schemas.benchmark_schema import BenchmarkContext
from agent.utils.context_resolver import build_context_summary

import os
from dotenv import load_dotenv
load_dotenv()


@dataclass
class EvalResult:
    """Evaluation result for a single repository."""

    repo_url: str
    platform: str
    score: ScoreBreakdown
    comparison: ComparisonResult | None  # None if no ground truth
    generated_yaml: str
    ground_truth_yaml: str | None
    error: str | None = None

    @property
    def overall_score(self) -> float:
        return self.score.overall

    @property
    def comparison_score(self) -> float | None:
        return self.comparison.overall if self.comparison else None


@dataclass
class BenchmarkReport:
    """Aggregate benchmark report across all repos."""

    results: list[EvalResult] = field(default_factory=list)

    @property
    def avg_score(self) -> float:
        scores = [r.overall_score for r in self.results if r.error is None]
        return round(sum(scores) / len(scores), 1) if scores else 0.0

    @property
    def avg_comparison(self) -> float | None:
        scores = [r.comparison_score for r in self.results if r.comparison_score is not None]
        return round(sum(scores) / len(scores), 1) if scores else None

    @property
    def pass_rate(self) -> float:
        """Fraction of repos where correctness is 100%."""
        if not self.results:
            return 0.0
        passed = sum(1 for r in self.results if r.error is None and r.score.correctness == 1.0)
        return passed / len(self.results)

    def summary(self) -> str:
        lines = [
            f"Benchmark Report ({len(self.results)} repos)",
            f"{'=' * 50}",
            f"Average Quality Score: {self.avg_score}/100",
        ]
        if self.avg_comparison is not None:
            lines.append(f"Average Ground Truth Similarity: {self.avg_comparison}/100")
        lines.append(f"Validation Pass Rate: {self.pass_rate:.0%}")
        lines.append(f"{'=' * 50}")

        for r in self.results:
            status = "✓" if r.error is None else "✗"
            comp = f" | GT: {r.comparison_score}" if r.comparison_score is not None else ""
            lines.append(f"  {status} {r.repo_url}")
            lines.append(f"    Score: {r.overall_score}/100{comp}")
            if r.error:
                lines.append(f"    Error: {r.error}")

        return "\n".join(lines)


# ── Default benchmark repos ────────────────────────────────────────────────

DEFAULT_BENCHMARK_REPOS: list[dict[str, str]] = [
    {"url": "https://github.com/alaaashraf19/YAML-Wizard", "platform": "github"},
    {"url": "https://github.com/psf/requests.git", "platform": "github"},
    {"url": "https://github.com/pallets/flask.git", "platform": "github"},
    {"url": "https://github.com/expressjs/express.git", "platform": "github"},
    {"url": "https://github.com/spring-projects/spring-petclinic.git", "platform": "github"},
]


# ── Core functions ──────────────────────────────────────────────────────────

from urllib.parse import urlparse
from fastapi.concurrency import run_in_threadpool

def extract_platform(repo_url: str) -> str:
    hostname = urlparse(repo_url).hostname or ""

    if "github" in hostname:
        return "github"
    elif "gitlab" in hostname:
        return "gitlab"
    elif "bitbucket" in hostname:
        return "bitbucket"

    return "unknown"

async def evaluate_repo(
    repo_url: str,
    model_name: str,
    platform: str = "github",
    user_prompt: str = "Set up a complete CI/CD pipeline with linting, testing, and building",
) -> EvalResult:
    """Evaluate YAML generation quality for a single repo."""
    try:
        # Fetch repo context (includes existing CI)
        try:
            if platform == "github":
                from agent.github_agent import run_github_agent
                pkg = await run_in_threadpool(run_github_agent, repo_url=repo_url, github_token= os.getenv("GITHUB_ACCESS_TOKEN"))
            else:
                from agent.gitlab_agent import run_gitlab_agent
                pkg = await run_in_threadpool(run_gitlab_agent, repo_url=repo_url, gitlab_token= os.getenv("GITLAB_ACCESS_TOKEN"))
        except Exception as exc:
            print("Agent failed for repo", repo_url, "exception ",exc)
            return EvalResult(
                repo_url=repo_url,
                platform=platform,
                score=ScoreBreakdown(),
                comparison=None,
                generated_yaml="",
                ground_truth_yaml=None,
                error=f"Agent failed: {exc}",
            )
        
        full_context = pkg

        # Extract ground truth before hiding it
        ground_truth = full_context.existing_ci_content

        # Create a context with existing CI hidden (to test generation from scratch)
        hidden_context = full_context.model_copy(update={
            "has_existing_ci": False,
            "existing_ci_content": None,
        })
        # Also remove CI files from key_files
        cleaned_keys = {
            k: v for k, v in hidden_context.key_files.items()
            if ".github/workflows" not in k and ".gitlab-ci" not in k
        }
        hidden_context.key_files = cleaned_keys


        # 3. Build a minimal ContextResolverResponse wrapper for the agent

        context_wrapper = BenchmarkContext(
            repo=RepoCreate(
                platform=platform,
                default_branch="main",
                url=repo_url,
            ),
            repo_context=hidden_context,
        )
        context_summary = build_context_summary(hidden_context)
        # 4. Use the new ChatbotAgent to generate the YAML
        agent = ChatbotAgent(model=model_name)

        generated_response = await agent.invoke(
            message=user_prompt,
            session_id=0,
            context=context_wrapper,
            context_summary=context_summary,
        )

        generated_yaml = ""

        if isinstance(generated_response, list):
            for segment in generated_response:
                if (
                    segment.get("type") == "code"
                    and segment.get("language", "").lower() in {"yaml", "yml"}
                ):
                    generated_yaml = segment["content"]
                    break

            # Fallback: first code block if no yaml language specified
            if not generated_yaml:
                for segment in generated_response:
                    if segment.get("type") == "code":
                        generated_yaml = segment["content"]
                        break
        else:
            generated_yaml = generated_response

        print("i am before score yaml")
        print(generated_yaml)
        # Score the generated YAML
        score = await score_yaml(generated_yaml, platform, full_context)

        # Compare against ground truth if available
        comparison = None
        if ground_truth:
            comparison = compare_yaml(generated_yaml, ground_truth, platform)

        return EvalResult(
            repo_url=repo_url,
            platform=platform,
            score=score,
            comparison=comparison,
            generated_yaml=generated_yaml,
            ground_truth_yaml=ground_truth,
        )

    except Exception as e:
        return EvalResult(
            repo_url=repo_url,
            platform=platform,
            score=ScoreBreakdown(),
            comparison=None,
            generated_yaml="",
            ground_truth_yaml=None,
            error=str(e),
        )


async def run_benchmark(
    model_name: str,
    repos: list[dict[str, str]] | None = None,
    user_prompt: str = "Set up a complete CI/CD pipeline with linting, testing, and building",
) -> BenchmarkReport:
    """Run evaluation across a set of benchmark repos."""
    if repos is None:
        repos = DEFAULT_BENCHMARK_REPOS

    report = BenchmarkReport()

    for repo_info in repos:
        result = await evaluate_repo(
            repo_url=repo_info["url"],
            platform=repo_info.get("platform", "github"),
            model_name=model_name,
            user_prompt=user_prompt,
        )
        report.results.append(result)

    return report



if __name__ == "__main__":
    report = run_benchmark()
    print(report.summary())