import json
from pathlib import Path

import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm

# Paths
DATASETS_DIR = Path("../../../datasets")

TARGETS = {
    "github": {
        "descriptions_dir":    DATASETS_DIR / "GithubActions_Descriptions",
        "embeddings_parquet":  DATASETS_DIR / "embeddings_github.parquet",
    },
    "gitlab": {
        "descriptions_dir":    DATASETS_DIR / "GitlabCI_Descriptions",
        "embeddings_parquet":  DATASETS_DIR / "embeddings_gitlab.parquet",
    },
}

# Embedding
#cuda is much faster than cpu when having a suitable gpu
#python -m pip uninstall -y torch torchvision torchaudio
#python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
#python -c "import torch; print(torch.__version__, '| cuda:', torch.version.cuda, '| available:', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
EMBED_MODEL = "BAAI/bge-m3"
EMBED_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBED_DTYPE = "float16" if EMBED_DEVICE == "cuda" else "float32"
EMBED_BATCH_SIZE = 16

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
        print(f"Loading embedding model: {EMBED_MODEL} device={EMBED_DEVICE} dtype={EMBED_DTYPE}")
        embed_model = SentenceTransformer(
            EMBED_MODEL,
            device=EMBED_DEVICE,
            model_kwargs={"torch_dtype": dtype},
        )
    return embed_model


def load_descriptions(descriptions_dir):
    if not descriptions_dir.exists():
        return []
    files = sorted(
        p for p in descriptions_dir.iterdir()
        if p.suffix == ".json" and not p.name.startswith("_")
    )
    items = []
    for p in files:
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
        items.append((obj["sha"], obj["description"]))
    return items


def embed_target(target_name, cfg):
    if cfg["embeddings_parquet"].exists():
        print(f"{cfg['embeddings_parquet']} already exists - skipping {target_name}")
        return

    items = load_descriptions(cfg["descriptions_dir"])
    if not items:
        print(f"No descriptions in {cfg['descriptions_dir']} - skipping {target_name}")
        return

    model = get_embedding_model()
    shas = [s for s, _ in items]
    texts = [t for _, t in items]

    vectors = []
    for i in tqdm(range(0, len(texts), EMBED_BATCH_SIZE), desc=f"embed[{target_name}]", unit="batch"):
        chunk = texts[i:i + EMBED_BATCH_SIZE]
        vecs = model.encode(
            chunk,
            batch_size=EMBED_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        for v in vecs:
            vectors.append(v.tolist())

    df_new = pd.DataFrame({
        "sha": shas,
        "vector": vectors,
    })
    df_new.to_parquet(cfg["embeddings_parquet"], index=False)
    print(f"Wrote {len(df_new)} rows to {cfg['embeddings_parquet']}")


def run_embed(targets=None):
    if targets is None:
        names = list(TARGETS.keys())
    elif isinstance(targets, str):
        names = [targets]
    else:
        names = list(targets)
    for name in names:
        if name not in TARGETS:
            raise ValueError(f"Unknown target: {name}")
        embed_target(name, TARGETS[name])


if __name__ == "__main__":
    run_embed()
