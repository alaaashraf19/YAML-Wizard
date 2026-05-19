import json
import sys
from pathlib import Path
import chromadb
import pandas as pd
from tqdm.auto import tqdm


DATASETS_DIR = Path("../../../datasets")
CHROMA_DIR = DATASETS_DIR / "chroma_db"

TARGETS = {
    "github": {
        "raw_dir": DATASETS_DIR / "Valid_Raw_GithubActions",
        "descriptions_dir": DATASETS_DIR / "GithubActions_Descriptions",
        "embeddings_parquet": DATASETS_DIR / "embeddings_github.parquet",
        "collection_name": "github_actions",
    },
    "gitlab": {
        "raw_dir": DATASETS_DIR / "Valid_Raw_GitlabCI",
        "descriptions_dir": DATASETS_DIR / "GitlabCI_Descriptions",
        "embeddings_parquet": DATASETS_DIR / "embeddings_gitlab.parquet",
        "collection_name": "gitlab_ci",
    },
}

INGEST_BATCH_SIZE = 1000

chroma_client = None


def get_chroma_client():
    global chroma_client
    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return chroma_client


def get_or_create_collection(name):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def load_description_record(descriptions_dir, sha):
    p = descriptions_dir / (sha + ".json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_target(target_name, cfg):
    parquet = cfg["embeddings_parquet"]
    if not parquet.exists():
        print(f"Embeddings parquet not found at {parquet} - run Stage 2 first.", file=sys.stderr)
        return

    df = pd.read_parquet(parquet)
    if len(df) == 0:
        print(f"No embeddings in {parquet} - skipping {target_name}")
        return

    coll = get_or_create_collection(cfg["collection_name"])
    if coll.count() > 0:
        print(f"Collection {coll.name} already has {coll.count()} items - skipping {target_name}")
        return
    ids_all = df["sha"].tolist()
    vecs_all = df["vector"].tolist()
    n = len(ids_all)

    for i in tqdm(range(0, n, INGEST_BATCH_SIZE), desc=f"ingest[{target_name}]", unit="batch"):
        ids = ids_all[i:i + INGEST_BATCH_SIZE]
        vecs = vecs_all[i:i + INGEST_BATCH_SIZE]
        documents = []
        metadatas = []
        for sha in ids:
            rec = load_description_record(cfg["descriptions_dir"], sha)
            tags_csv = ",".join(rec.get("tags", []))
            yaml_path = str(cfg["raw_dir"] / (sha + ".yml"))
            documents.append(rec["description"])
            metadatas.append({
                "target": target_name,
                "yaml_path": yaml_path,
                "yaml_bytes": rec.get("yaml_bytes", 0),
                "tags": tags_csv,
                "model": rec.get("model", ""),
            })
        coll.upsert(ids=ids, embeddings=vecs, documents=documents, metadatas=metadatas)

    print(f"Collection {coll.name} now contains {coll.count()} items")


def run_ingest(targets=None):
    if targets is None:
        names = list(TARGETS.keys())
    elif isinstance(targets, str):
        names = [targets]
    else:
        names = list(targets)
    for name in names:
        if name not in TARGETS:
            raise ValueError(f"Unknown target: {name}")
        ingest_target(name, TARGETS[name])


if __name__ == "__main__":
    run_ingest()
