from .github_connect import GithubConnector
from .gitlab_connect import GitLabConnector
from schemas.repo_schema import Platform


def get_connector(platform: Platform):
    if platform == Platform.GITHUB:
        return GithubConnector()
    elif platform == Platform.GITLAB:
        return GitLabConnector()
    else:
        raise ValueError("Unsupported platform")