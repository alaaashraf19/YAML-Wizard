import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from tqdm.auto import tqdm

DATASETS_DIR = Path("../../../datasets")
load_dotenv("../../.env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

PROVIDER = "groq"
MAX_YAML_CHARS = 12000
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
LIMIT = None



GITHUB_SYSTEM_INSTRUCTION = (
    "You are an expert DevOps engineer who reverse-engineers GitHub Actions "
    "workflows into the natural-language requests that would produce them. "
    "Given a YAML workflow, write a concise English description in the form "
    "of a user request to an LLM, so that the description can later be used "
    "as a few-shot example to regenerate a similar workflow. "
    "Return STRICT JSON with two fields and nothing else."
)

GITHUB_OUTPUT_SCHEMA_HINT = (
    'Return ONLY a JSON object of the form: '
    '{"description": "<imperative user-style request, 2-5 sentences>", '
    '"tags": ["<short kebab-case tag>", ...]}'
)

GITHUB_FEW_SHOT_EXAMPLES = [
    {
        "yaml": (
            "name: CI\n"
            "on:\n"
            "  push:\n"
            "    branches: [main]\n"
            "  pull_request:\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-node@v4\n"
            "        with: { node-version: '20' }\n"
            "      - run: npm ci\n"
            "      - run: npm test\n"
        ),
        "json": (
            '{"description": "Create a GitHub Actions workflow named CI that '
            'runs on every push to main and on pull requests. Use a single '
            'ubuntu-latest job that checks out the repository, sets up Node.js '
            '20, installs dependencies with npm ci, and runs npm test.", '
            '"tags": ["nodejs", "npm", "ci", "ubuntu", "tests"]}'
        ),
    },
    {
        "yaml": (
            "name: Release\n"
            "on:\n"
            "  push:\n"
            "    tags: ['v*']\n"
            "jobs:\n"
            "  publish:\n"
            "    runs-on: ubuntu-latest\n"
            "    permissions: { contents: write }\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with: { python-version: '3.11' }\n"
            "      - run: pip install build twine\n"
            "      - run: python -m build\n"
            "      - run: twine upload dist/*\n"
            "        env: { TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }} }\n"
        ),
        "json": (
            '{"description": "Create a GitHub Actions release workflow that '
            'triggers when a tag matching v* is pushed. In a single '
            'ubuntu-latest job with write permission to repository contents, '
            'check out the code, set up Python 3.11, install build and twine, '
            'build the package with python -m build, and upload the resulting '
            'distributions to PyPI using twine with PYPI_TOKEN from secrets.", '
            '"tags": ["python", "release", "pypi", "twine", "tags"]}'
        ),
    },
]


GITLAB_SYSTEM_INSTRUCTION = (
    "You are an expert DevOps engineer who reverse-engineers GitLab CI/CD "
    "pipelines (.gitlab-ci.yml files) into the natural-language requests "
    "that would produce them. Given a YAML pipeline, write a concise English "
    "description in the form of a user request to an LLM, so that the "
    "description can later be used as a few-shot example to regenerate a "
    "similar pipeline. "
    "Be highly specific about the INTERNAL COMMANDS so that similar "
    "pipelines embed close together: enumerate the concrete shell commands "
    "run in each job (e.g. 'pip install -r requirements.txt', "
    "'pytest --cov', 'docker build -t app .', 'mvn -B package', "
    "'cargo build --release'), name the package managers and build tools "
    "used (pip, pipenv, poetry, npm, yarn, pnpm, maven, gradle, cargo, "
    "go build, make, cmake, bundler, composer, dotnet), the Docker image "
    "and services (e.g. 'python:3.11', 'node:alpine', 'postgres:14'), the "
    "stages, artifacts, caches, rules/only/except triggers, deployment "
    "targets (GitLab Pages, Docker registry, S3, Kubernetes, Heroku, npm, "
    "PyPI), and any environment variables or secrets that are referenced. "
    "Return STRICT JSON with two fields and nothing else."
)

GITLAB_OUTPUT_SCHEMA_HINT = (
    'Return ONLY a JSON object of the form: '
    '{"description": "<imperative user-style request, 3-6 sentences, '
    'mentioning each job by name, the stage it runs in, the exact shell '
    'commands it executes, the docker image / services used, caches, '
    'artifacts, triggers (rules/only/except) and deployment targets>", '
    '"tags": ["<short kebab-case tag>", ...]}'
)

GITLAB_FEW_SHOT_EXAMPLES = [
    {
        "yaml": (
            "image: python:3.11\n"
            "services:\n"
            "  - postgres:14\n"
            "variables:\n"
            "  POSTGRES_DB: app_test\n"
            "  POSTGRES_USER: runner\n"
            "  POSTGRES_PASSWORD: ''\n"
            "stages:\n"
            "  - test\n"
            "  - deploy\n"
            "cache:\n"
            "  paths:\n"
            "    - .cache/pip\n"
            "pytest:\n"
            "  stage: test\n"
            "  script:\n"
            "    - pip install -r requirements.txt\n"
            "    - pytest --cov=app --junitxml=report.xml\n"
            "  artifacts:\n"
            "    when: always\n"
            "    reports:\n"
            "      junit: report.xml\n"
            "pages:\n"
            "  stage: deploy\n"
            "  script:\n"
            "    - mkdocs build -d public\n"
            "  artifacts:\n"
            "    paths:\n"
            "      - public\n"
            "  only:\n"
            "    - main\n"
        ),
        "json": (
            '{"description": "Create a GitLab CI pipeline that uses the '
            'python:3.11 Docker image with a postgres:14 service and a pip '
            'cache on .cache/pip. Define two stages: test and deploy, plus '
            'POSTGRES_DB, POSTGRES_USER and POSTGRES_PASSWORD variables for '
            'the database service. In the test stage add a pytest job that '
            'runs pip install -r requirements.txt then pytest --cov=app '
            '--junitxml=report.xml and always uploads report.xml as a JUnit '
            'artifact. In the deploy stage add a GitLab Pages job that runs '
            'mkdocs build -d public, publishes the public/ directory as the '
            'pages artifact, and only runs on the main branch.", '
            '"tags": ["python", "pytest", "postgres", "coverage", '
            '"gitlab-pages", "mkdocs"]}'
        ),
    },
    {
        "yaml": (
            "image: docker:24\n"
            "services:\n"
            "  - docker:24-dind\n"
            "variables:\n"
            "  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA\n"
            "stages:\n"
            "  - build\n"
            "  - release\n"
            "build_image:\n"
            "  stage: build\n"
            "  before_script:\n"
            "    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY\n"
            "  script:\n"
            "    - docker build -t $IMAGE_TAG .\n"
            "    - docker push $IMAGE_TAG\n"
            "  rules:\n"
            "    - if: '$CI_COMMIT_BRANCH == \"main\"'\n"
            "release_tag:\n"
            "  stage: release\n"
            "  script:\n"
            "    - docker pull $IMAGE_TAG\n"
            "    - docker tag $IMAGE_TAG $CI_REGISTRY_IMAGE:latest\n"
            "    - docker push $CI_REGISTRY_IMAGE:latest\n"
            "  rules:\n"
            "    - if: '$CI_COMMIT_TAG'\n"
        ),
        "json": (
            '{"description": "Create a GitLab CI pipeline that builds and '
            'publishes a Docker image to the GitLab Container Registry using '
            'the docker:24 image with the docker:24-dind service. Define an '
            'IMAGE_TAG variable as $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA '
            'and two stages: build and release. In the build stage add a '
            'build_image job that logs in to $CI_REGISTRY with '
            '$CI_REGISTRY_USER / $CI_REGISTRY_PASSWORD, runs '
            'docker build -t $IMAGE_TAG . and docker push $IMAGE_TAG, and '
            'only runs when the commit branch is main. In the release stage '
            'add a release_tag job that runs docker pull $IMAGE_TAG, '
            'docker tag $IMAGE_TAG $CI_REGISTRY_IMAGE:latest and '
            'docker push $CI_REGISTRY_IMAGE:latest, and only runs when a '
            'git tag is pushed.", '
            '"tags": ["docker", "dind", "container-registry", "release", '
            '"tags", "ci-registry"]}'
        ),
    },
]

TARGET_CONFIGS = {
    "github": {
        "raw_dir": DATASETS_DIR / "Valid_Raw_GithubActions",
        "descriptions_dir": DATASETS_DIR / "GithubActions_Descriptions",
        "groq_model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "groq_min_seconds_between_calls": 2.5,
        "system_instruction": GITHUB_SYSTEM_INSTRUCTION,
        "output_schema_hint": GITHUB_OUTPUT_SCHEMA_HINT,
        "few_shot_examples": GITHUB_FEW_SHOT_EXAMPLES,
    },
    "gitlab": {
        "raw_dir": DATASETS_DIR / "Valid_Raw_GitlabCI",
        "descriptions_dir": DATASETS_DIR / "GitlabCI_Descriptions",
        "groq_model": "openai/gpt-oss-120b",
        "groq_min_seconds_between_calls": 4.0,
        "system_instruction": GITLAB_SYSTEM_INSTRUCTION,
        "output_schema_hint": GITLAB_OUTPUT_SCHEMA_HINT,
        "few_shot_examples": GITLAB_FEW_SHOT_EXAMPLES,
    },
}


def build_user_prompt(yaml_text, cfg):
    parts = []
    parts.append(cfg["output_schema_hint"])
    parts.append("")
    parts.append("Here are two examples of the expected output:")
    for ex in cfg["few_shot_examples"]:
        parts.append("")
        parts.append("YAML:")
        parts.append("```yaml")
        parts.append(ex["yaml"].rstrip())
        parts.append("```")
        parts.append("Output:")
        parts.append(ex["json"])
    parts.append("")
    parts.append("Now do the same for this YAML:")
    parts.append("```yaml")
    parts.append(yaml_text.rstrip())
    parts.append("```")
    parts.append("Output:")
    return "\n".join(parts)


groq_client = None


def parse_provider_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    obj = json.loads(text)
    desc = obj.get("description", "")
    tags = obj.get("tags", [])
    if not isinstance(desc, str) or not desc.strip():
        raise ValueError("Provider returned empty description")
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip() for t in tags if str(t).strip()]
    return {"description": desc.strip(), "tags": tags}


def describe_with_groq(yaml_text, cfg):
    global groq_client
    if groq_client is None:
        from groq import Groq
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to .env")
        groq_client = Groq(api_key=GROQ_API_KEY)

    completion = groq_client.chat.completions.create(
        model=cfg["groq_model"],
        messages=[
            {"role": "system", "content": cfg["system_instruction"]},
            {"role": "user", "content": build_user_prompt(yaml_text, cfg)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    text = completion.choices[0].message.content or ""
    return parse_provider_json(text)


def write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def truncate_yaml(text, max_chars, cfg):
    if len(text) <= max_chars:
        return text
    head = text[: max_chars - 200]
    return head + f"\n[truncated, original length: {len(text)} chars]\n"


def call_with_retry(describe_fn, yaml_text):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return describe_fn(yaml_text)
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise last_err


def describe_target(target, provider=PROVIDER, limit=LIMIT):
    if target not in TARGET_CONFIGS:
        raise ValueError(f"Unknown target: {target}")
    cfg = TARGET_CONFIGS[target]
    out_dir = cfg["descriptions_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Target: {target} ===")
    print(f"Raw YAMLs: {cfg['raw_dir']}")
    print(f"Model:     {cfg['groq_model']}")

    if provider == "groq":
        def describe_fn(yt):
            return describe_with_groq(yt, cfg)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    sleep_seconds = cfg["groq_min_seconds_between_calls"]
    model_name = cfg["groq_model"]
    failed_log = out_dir / "_failed.txt"

    files = sorted(p for p in cfg["raw_dir"].iterdir() if p.suffix == ".yml")
    if limit is not None:
        files = files[:limit]

    n_done = n_skipped = n_failed = 0
    failed_records = []

    pbar = tqdm(files, desc=f"describe[{target}/{provider}]", unit="file")
    for path in pbar:
        sha = path.stem
        out_path = out_dir / (sha + ".json")
        if out_path.exists():
            n_skipped += 1
            pbar.set_postfix(done=n_done, skip=n_skipped, fail=n_failed)
            continue

        try:
            yaml_text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            n_failed += 1
            failed_records.append(f"{sha}\tread_error\t{e}")
            pbar.set_postfix(done=n_done, skip=n_skipped, fail=n_failed)
            continue

        truncated = truncate_yaml(yaml_text, MAX_YAML_CHARS, cfg)

        try:
            result = call_with_retry(describe_fn, truncated)
        except Exception as e:
            n_failed += 1
            failed_records.append(f"{sha}\t{type(e).__name__}\t{str(e)[:200]}")
            pbar.set_postfix(done=n_done, skip=n_skipped, fail=n_failed)
            continue

        record = {
            "sha": sha,
            "provider": provider,
            "model": model_name,
            "yaml_bytes": len(yaml_text),
            "description": result["description"],
            "tags": result["tags"]
        }
        write_json(out_path, record)
        n_done += 1
        pbar.set_postfix(done=n_done, skip=n_skipped, fail=n_failed)

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if failed_records:
        with open(failed_log, "a", encoding="utf-8") as f:
            for line in failed_records:
                f.write(line + "\n")

    print("--- describe summary ---")
    print(f"target:   {target}")
    print(f"provider: {provider}")
    print(f"model:    {model_name}")
    print(f"done:     {n_done}")
    print(f"skipped:  {n_skipped}")
    print(f"failed:   {n_failed}")
    if failed_records:
        print(f"failures appended to: {failed_log}")


def run_describe(targets=None, provider=PROVIDER, limit=LIMIT):
    if targets is None:
        names = list(TARGET_CONFIGS.keys())
    elif isinstance(targets, str):
        names = [targets]
    else:
        names = list(targets)
    for name in names:
        describe_target(name, provider=provider, limit=limit)


if __name__ == "__main__":
    print("Provider:", PROVIDER)
    print("Targets: ", list(TARGET_CONFIGS.keys()))
    run_describe()
