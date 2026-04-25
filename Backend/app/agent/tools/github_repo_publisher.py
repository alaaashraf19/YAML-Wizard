import base64
from os import name
import httpx
from Backend.app.agent.utils.github_auth import get_installation_token


#to be updated to take yaml file as parameter
#if branch is not main we should ask user to specify he mustt speicfy
async def push_yaml_file(yaml_content: str, platform: str, commit_message: str, create_pr: bool, pr_branch: str = "yaml-wizard/ci-pipeline", owner: str, repo_name: str, branch: str, installation_id: int):
    token = get_installation_token(installation_id)

    url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/.github/workflows/ci.yml"



    encoded_content = base64.b64encode(yaml_content.encode()).decode()

    data = {
        "message": "Add CI workflow via YAML Wizard",
        "content": encoded_content,
        "branch": branch
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
    return response.json()

def get_platform():
     
# if __name__ == "__main__":
#     push_yaml_file("alaaashraf19", "YAML-Wizard", "feature/Backend/Repo-Publisher", 125924739)



# from github import Github

# g = Github(installation_token)
# repo = g.get_repo("owner/repo")

# repo.create_file(
#     path="generated.yaml",
#     message="Add generated YAML",
#     content="your content here",
#     branch="main"
# )
if name == "__main__":
        yaml_content = """
name: CI

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Hello from YAML Wizard"
"""
async def test_push_yaml_file():
    response = await push_yaml_file(yaml_content, "platform", "commit_message", True, "pr_branch", "owner", "repo_name", "branch", 123456)
    print(response)