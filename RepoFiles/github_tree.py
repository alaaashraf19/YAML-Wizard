import requests
import argparse
import sys

target_files = [
    # JavaScript / Node.js
    "package.json","package-lock.json","yarn.lock",
    "pnpm-lock.yaml","next.config.js","angular.json",
    "tsconfig.json",

    # Python
    "requirements.txt","pyproject.toml","Pipfile",
    "Pipfile.lock","poetry.lock","setup.py","manage.py",

    # Java / JVM
    "pom.xml","build.gradle","build.gradle.kts","settings.gradle",

    # Infrastructure & Containers
    "Dockerfile","docker-compose.yml","docker-compose.yaml","Containerfile",
    "Procfile","kubernetes.yaml","deployment.yaml","values.yaml","main.tf",

    # Other Languages (Go, Ruby, PHP, Rust, C++)
    "go.mod","go.sum","Gemfile","Gemfile.lock","composer.json",
    "composer.lock","Cargo.toml","Cargo.lock","Makefile","CMakeLists.txt",

    # General Configuration
    ".env.example",".gitignore",".editorconfig",".eslintrc.js",
    ".eslintrc.json",".prettierrc","sonar-project.properties"
]

def get_repo_tree(owner, repo, token=None, branch="main"):
    
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    # print(url)
    
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
        
    return data.get('tree', [])



def find_target_files_paths(tree_data, target_files):
    with open("target_files.txt", "w",encoding="utf-8") as f:
        for item in tree_data:
            path = item['path']
            file_name = path.split('/')[-1]
            if file_name in target_files:
                f.write(f"{path}\n")
           



def group(tree_data):
    hierarchy = {}
    for item in tree_data:
        path = item['path']
        parts = path.split('/')       
        
        current_level = hierarchy
        
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]          
    return hierarchy




def print_tree(structure, prefix=""):
    keys = sorted(structure.keys())
    count = len(keys)
    
    for i, key in enumerate(keys):
        is_last = (i == count - 1)
        
        connector = "└── " if is_last else "├── "
        
        print(f"{prefix}{connector}{key}")
        
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        if structure[key]:
            print_tree(structure[key], new_prefix)




# owner = input()
# repo = input()
# branch = input()
# token = input()

parser = argparse.ArgumentParser()
parser.add_argument("owner")
parser.add_argument("repo")
parser.add_argument("--branch", default="main")
parser.add_argument("--token")
args = parser.parse_args()


# tree_data = get_repo_tree(owner, repo, token, branch)
tree_data = get_repo_tree(args.owner, args.repo, args.token, args.branch)

# print(tree_data)

hierarchy = group(tree_data)

print_tree(hierarchy)

find_target_files_paths(tree_data, target_files)
