from pathlib import Path
from typing import Literal

import chromadb
import torch
from langchain_core.tools import tool
from sentence_transformers import SentenceTransformer


DATASETS_DIR = Path(__file__).resolve().parents[4] / "datasets"
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

EMBED_MODEL = "BAAI/bge-m3"
EMBED_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
EMBED_DTYPE = torch.float16 if EMBED_DEVICE == "cuda" else torch.float32

DEFAULT_K = 2
SEPARATOR = "\n" + "=" * 80 + "\n"


embed_model = None
chroma_client = None
collections: dict[str, object] = {}


def get_embedding_model():
    global embed_model
    if embed_model is None:
        embed_model = SentenceTransformer(
            EMBED_MODEL,
            device=EMBED_DEVICE,
            model_kwargs={"dtype": EMBED_DTYPE},
        )
    return embed_model


def get_chroma_client():
    global chroma_client
    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return chroma_client


def get_collection(target: str):
    if target not in TARGETS:
        raise ValueError(
            f"Unknown target: {target!r}. Expected one of {list(TARGETS)}."
        )
    if target not in collections:
        collections[target] = get_chroma_client().get_collection(
            name=TARGETS[target]["collection_name"]
        )
    return collections[target]


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()
    vec = model.encode(
        [text],
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vec[0].tolist()


def retrieve(user_prompt: str, target: str, k: int) -> list[dict]:
    cfg = TARGETS[target]
    coll = get_collection(target)
    qvec = embed_query(user_prompt)
    res = coll.query(
        query_embeddings=[qvec],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    ids = res.get("ids", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    out = []
    for sha, meta, dist in zip(ids, metas, dists):
        yaml_path = meta.get("yaml_path") or str(cfg["raw_dir"] / (sha + ".yml"))
        try:
            with open(yaml_path, "r", encoding="utf-8", errors="replace") as f:
                yaml_text = f.read()
        except Exception as e:
            yaml_text = f"# could not read {yaml_path}: {e}"
        out.append({"similarity": 1.0 - float(dist), "yaml_text": yaml_text})
    return out


def format_examples(examples: list[dict]) -> str:
    if not examples:
        return "No relevant examples were found in the dataset."

    blocks = [
        f"similarity: {ex['similarity']:.3f}\n{ex['yaml_text'].rstrip()}"
        for ex in examples
    ]
    print(SEPARATOR.join(blocks))
    return SEPARATOR.join(blocks)


@tool
def retrieve_examples_tool(description: str, target: Literal["github", "gitlab"]) -> str:
    """
    Retrieve the top 2 real-world CI/CD pipeline YAML examples from the dataset
    that are semantically closest to the user's described requirements.

    Call this tool whenever the user describes a CI/CD pipeline they want to
    create, modify, or understand for either GitHub Actions or GitLab CI.

    IMPORTANT — how to interpret the returned examples:
    - They are NOT the final answer. Do not copy them verbatim and return them
      to the user unless the user asked for examples only.
      They are reference material for YOU, the assistant, to draw
      on while composing your own pipeline.
    - They are not guaranteed to match the user's intent end-to-end. Each
      example was selected by semantic similarity, which means usually only
      SOME parts of the YAML are relevant — a job, a step, a trigger pattern,
      a deployment strategy — while the rest may be unrelated. Cherry-pick the
      relevant parts and discard the rest.
    - The similarity score tells you how loosely or tightly the example matches
      the request. Lower scores mean only small fragments are likely useful.
    - The YAML may use OUTDATED or DEPRECATED versions of actions, images, or
      syntax (e.g. `actions/checkout@v2`, deprecated runners, old GitLab
      keywords). Treat versions and image tags with skepticism and upgrade them
      to current best-practice versions in your final answer.
    - On the upside, the examples are almost always SYNTACTICALLY CORRECT real
      pipelines from production repositories, so they are a reliable guide for
      structure, indentation, key names, and overall pipeline shape.

    In short: use these examples to inform structure and patterns, not as a
    drop-in solution. Synthesize a fresh, modern, intent-matching pipeline from
    the relevant fragments.

    Args:
        description: A natural-language description of what the user wants the
            pipeline to do (jobs, triggers, deploy targets, etc.).
        target: Which platform to search examples for. Must be 'github' for
            (GitHub Actions) or 'gitlab' for (GitLab CI).

    Returns:
        A string with the 2 most similar YAML examples, each prefixed with its
        similarity score and separated by a divider line.
    """
    examples = retrieve(description, target=target, k=DEFAULT_K)
    return format_examples(examples)


# if __name__ == "__main__":
#     import sys

#     if len(sys.argv) >= 3:
#         target_arg = sys.argv[1].lower()
#         query_arg = " ".join(sys.argv[2:])
#     else:
#         target_arg = input("target ('github' or 'gitlab'): ").strip().lower()
#         query_arg = input("describe the pipeline: ").strip()

#     if target_arg not in TARGETS:
#         print(f"ERROR: target must be one of {list(TARGETS)}, got {target_arg!r}")
#         sys.exit(1)
#     if not query_arg:
#         print("ERROR: empty query")
#         sys.exit(1)

#     print(f"\nQuery:  {query_arg}")
#     print(f"Target: {target_arg}\n")
#     print("Loading embedding model and Chroma collection (first run is slow)...\n")

#     print(format_examples(retrieve(query_arg, target=target_arg, k=DEFAULT_K)))
