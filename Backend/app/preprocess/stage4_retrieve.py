#should be moved to tools later on
from pathlib import Path
import chromadb
import torch
from sentence_transformers import SentenceTransformer


DATASETS_DIR = Path("../../../datasets")
CHROMA_DIR = DATASETS_DIR / "chroma_db"

TARGETS = {
    "github": {
        "raw_dir": DATASETS_DIR / "Valid_Raw_GithubActions",
        "collection_name": "github_actions",
    },
    "gitlab": {
        "raw_dir": DATASETS_DIR / "Valid_Raw_GitlabCI",
        "collection_name": "gitlab_ci",
    },
}

# Embedding
EMBED_MODEL = "BAAI/bge-m3"
EMBED_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBED_DTYPE = "float16" if EMBED_DEVICE == "cuda" else "float32"

# Retrieval
DEFAULT_K = 5


# Embedding model
DTYPE_MAP = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}

embed_model = None


def get_embedding_model():
    global embed_model
    if embed_model is None:
        dtype = DTYPE_MAP.get(EMBED_DTYPE, torch.float32)
        print(f"Loading embedding model: {EMBED_MODEL}     device={EMBED_DEVICE}      dtype={EMBED_DTYPE}")
        embed_model = SentenceTransformer(
            EMBED_MODEL,
            device=EMBED_DEVICE,
            model_kwargs={"torch_dtype": dtype},
        )
    return embed_model


chroma_client = None


def get_chroma_client():
    global chroma_client
    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return chroma_client


data_collections = {}


def get_collection(target):
    if target not in TARGETS:
        raise ValueError(
            f"Unknown target: {target!r}. Expected one of {list(TARGETS)}.")
    if target not in data_collections:
        data_collections[target] = get_chroma_client().get_collection(name=TARGETS[target]["collection_name"],)
    return data_collections[target]


def embed_query(text):
    model = get_embedding_model()
    vec = model.encode(
        [text],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vec[0].tolist()



def retrieve_examples(user_prompt, target, k=DEFAULT_K):
    cfg = TARGETS.get(target)
    if cfg is None:
        raise ValueError(
            f"Unknown target: {target!r}. Expected one of {list(TARGETS)}.")

    coll = get_collection(target)
    qvec = embed_query(user_prompt)
    res = coll.query(
        query_embeddings=[qvec],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    out = []
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for sha, doc, meta, dist in zip(ids, docs, metas, dists):
        similarity = 1.0 - float(dist)
        yaml_path = meta.get("yaml_path") or str(cfg["raw_dir"] / (sha + ".yml"))
        try:
            with open(yaml_path, "r", encoding="utf-8", errors="replace") as f:
                yaml_text = f.read()
        except Exception as e:
            yaml_text = f"# could not read {yaml_path}: {e}"
        out.append({
            "sha": sha,
            "description": doc,
            "similarity": similarity,
            "tags": [t for t in (meta.get("tags") or "").split(",") if t],
            "yaml_text": yaml_text,
        })
    return out


if __name__ == "__main__":
    queries = [
        ("github", "Write a robust GitHub Actions CI/CD workflow that triggers on pull requests and main branch updates to run code linting, unit tests, and security scans. Upon success, the pipeline must build and push a Docker image, deploy to a staging environment for E2E testing, require manual approval for final production deployment, and send automated status notifications to the team"),
        ("gitlab", "GitLab CI pipeline that runs tests, builds a Docker image, and deploys to staging with a manual approval gate before production"),
    ]

    for target, q in queries:
        print(f"TARGET: {target}\n")
        print("QUERY:", q, "\n")
        results = retrieve_examples(q, target=target, k=3)
        for i, r in enumerate(results, 1):
            print(f"\n[{i}]\nsim={r['similarity']:.3f}\nsha={r['sha']}\ntags={','.join(r['tags'])}\n")
            print(f"{r['description']}\n")
            print("************YAML ACTUAL CODE**************")
            for line in r["yaml_text"].splitlines():
                print(f"{line}")
            print("\n================================================================================================")
