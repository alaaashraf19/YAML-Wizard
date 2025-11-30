import requests
import argparse
import sys

def get_file_content(owner, repo, token=None):
    file = open("target_files.txt","r")
    for line in file:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{line.strip()}?recursive=1"
        # print(url)
        
        headers = {
            "Accept": "application/vnd.github.raw+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        with open("contents.txt", "a", encoding="utf-8") as f:
            if token:
                headers["Authorization"] = f"Bearer {token}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            f.write(response.text)
            f.write('=========================================================================================================\n')
        
    
        
# owner = input()
# repo = input()
# branch = input()
# token = input()

parser = argparse.ArgumentParser()
parser.add_argument("owner")
parser.add_argument("repo")
parser.add_argument("--token")
args = parser.parse_args()


# content = get_repo_tree(owner, repo, token, branch)
content = get_file_content(args.owner, args.repo,args.token)




