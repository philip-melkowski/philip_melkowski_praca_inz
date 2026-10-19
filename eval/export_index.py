# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, read  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--splits", nargs="+", default=["train"], choices=["train", "cal", "test"])
    p.add_argument("--output", default=str(DATASETS_DIR / "router_index.npz"))
    p.add_argument("--threshold", type=float, default=0.25)
    args = p.parse_args()

    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = [r for r in read("labels.jsonl") if r["split"] in args.splits]
    vectors = emb[[row[r["id"]] for r in labels]].astype(np.float32)
    y = np.array([r["delta"] > args.threshold for r in labels], dtype=np.float32)
    np.savez(args.output, vectors=vectors, labels=y)
    print(f"{args.output}: {len(y)} wektorów ×{vectors.shape[1]}, podziały {args.splits}, COMPLEX {y.mean():.1%} (Δ > {args.threshold})")


if __name__ == "__main__":
    main()
