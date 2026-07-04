#open an integrated terminal in preprocess folder and run pipeline through CLI (stage 1 to stage 3 will be run only once)
#descriptions and embedding will be skipped because they are ready at datasets folder
#chroma_db vectore stores will be populated and will be inside datasets

import stage1_generate_descriptions as s1
import stage2_embed as s2
import stage3_ingest as s3


def main():

    print("Stage 1: generating descriptions")
    s1.run_describe()

    print("Stage 2: embedding descriptions")
    s2.run_embed()

    print("Stage 3: ingesting embeddings into Chroma")
    s3.run_ingest()


if __name__ == "__main__":
    main()
