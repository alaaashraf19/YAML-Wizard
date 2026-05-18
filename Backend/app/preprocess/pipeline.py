#open an integrated terminal in preprocess folder and run pipeline through CLI (stage 1 to stage 3 will be run only once)
#descriptions and embedding will be skipped because they are ready at datasets folder
#chroma_db vectore stores will be populated and will be inside datasets
#a test sample will run (stage 4 returns the actual yaml and will be used as a tool for the agent later)

import stage1_generate_descriptions as s1
import stage2_embed as s2
import stage3_ingest as s3
import stage4_retrieve as s4


queries = {
    "github": "build and test a python package on push to main, then publish a Docker image",
    "gitlab": "GitLab CI pipeline that runs tests, builds a Docker image, and deploys to staging",
}


def main():

    print("Stage 1: generating descriptions")
    s1.run_describe()

    print("Stage 2: embedding descriptions")
    s2.run_embed()

    print("Stage 3: ingesting embeddings into Chroma")
    s3.run_ingest()

    print("Stage 4: retrieval")
    for target, q in queries.items():
        print(f"\n{target}:\t{q}")
        results = s4.retrieve_examples(q, target=target, k=3)
        for i, r in enumerate(results, 1):
            print(f"[{i}]\tsim={r['similarity']:.3f}\tsha={r['sha']}\ttags={','.join(r['tags'])}")


if __name__ == "__main__":
    main()
