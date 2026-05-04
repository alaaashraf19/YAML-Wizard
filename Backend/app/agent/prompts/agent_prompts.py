"""
Prompts for the GitHub Repo Context Agent.
Optimised for small models (qwen2.5:2b / 3b).
"""
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = """You are RepoContextAgent, part of YAML Wizard.
Goal: collect ONLY the files needed to generate a CI/CD YAML for the user's request.

Rules:
1. ALWAYS call list_directory with path="" first to see the repo root.
2. Look at file names; pick only files that hold config or dependency info.
3. SKIP: lock files (*.lock, package-lock.json), binaries, large assets, test fixtures.
4. Call get_file_contents for each relevant file (max 8 files total).
5. Use search_code if you need to find a specific pattern (e.g. "scripts" in package.json).
6. After collecting files, output a JSON block exactly like this:

```json
{
  "languages": ["python"],
  "frameworks": ["fastapi"],
  "build_tools": ["pip"],
  "test_runners": ["pytest"],
  "has_docker": true,
  "key_files": {
    "Dockerfile": "<content>",
    "requirements.txt": "<content>"
  },
  "directory_tree": "<root listing>",
  "notes": "FastAPI app with Docker. No existing CI found."
}
```

Output ONLY the JSON block after you are done calling tools. No extra text."""


FEW_SHOT_EXAMPLES = """
--- EXAMPLE 1 ---
User request: "Create a GitHub Actions CI/CD pipeline for this Python app."
Repo: https://github.com/example/my-python-app

Step 1 → list_directory(owner="example", repo="my-python-app", path="")
Result: README.md, requirements.txt, Dockerfile, src/, tests/, .github/

Step 2 → get_file_contents(owner="example", repo="my-python-app", path="requirements.txt")
Step 3 → get_file_contents(owner="example", repo="my-python-app", path="Dockerfile")

Output:
```json
{
  "languages": ["python"],
  "frameworks": [],
  "build_tools": ["pip"],
  "test_runners": ["pytest"],
  "has_docker": true,
  "key_files": {
    "requirements.txt": "fastapi\npytest\nuvicorn",
    "Dockerfile": "FROM python:3.11\nCOPY . .\nRUN pip install -r requirements.txt"
  },
  "directory_tree": "README.md\nrequirements.txt\nDockerfile\nsrc/\ntests/",
  "notes": "Python app with Docker. No existing GitHub Actions found."
}
```

--- EXAMPLE 2 ---
User request: "Jenkins pipeline for my Node.js app."
Repo: https://github.com/example/node-api

Step 1 → list_directory(owner="example", repo="node-api", path="")
Result: package.json, tsconfig.json, Dockerfile, src/, Jenkinsfile

Step 2 → get_file_contents(owner="example", repo="node-api", path="package.json")
Step 3 → get_file_contents(owner="example", repo="node-api", path="Dockerfile")

Output:
```json
{
  "languages": ["typescript"],
  "frameworks": ["express"],
  "build_tools": ["npm/yarn build"],
  "test_runners": ["jest"],
  "has_docker": true,
  "key_files": {
    "package.json": "{...}",
    "Dockerfile": "FROM node:20-alpine\n..."
  },
  "directory_tree": "package.json\ntsconfig.json\nDockerfile\nsrc/\nJenkinsfile",
  "notes": "TypeScript/Express app. Existing Jenkinsfile found."
}
```
--- END EXAMPLES ---

Now handle the real request below.
"""


def build_initial_message(user_prompt: str, repo_url: str, owner: str, repo: str) -> list:
    human_content = (
        f"{FEW_SHOT_EXAMPLES}\n\n"
        f"User request: \"{user_prompt}\"\n"
        f"Repo URL: {repo_url}\n"
        f"Owner: {owner}  |  Repo: {repo}\n\n"
        "Begin by listing the repository root."
    )
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]