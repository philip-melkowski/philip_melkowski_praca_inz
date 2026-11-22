# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import argparse
import json
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
    p.add_argument("--labels", default=str(DATASETS_DIR / "labels.jsonl"), help="etykiety pomiaru głównego (v3: data/labels/labels_v3.jsonl)")
    p.add_argument("--extra-splits", nargs="*", default=[], choices=["extra_train", "extra_val"], help="dodatkowe pytania (wpis 118, D21)")
    args = p.parse_args()

    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    with Path(args.labels).open(encoding="utf-8") as f:
        labels = [r for r in map(json.loads, f) if r["split"] in args.splits]
    vectors = emb[[row[r["id"]] for r in labels]].astype(np.float32)
    if args.extra_splits:
        xq = read("questions_extra_split.jsonl")
        xrow = {q["id"]: i for i, q in enumerate(xq)}
        xsplit = {q["id"]: q["split"] for q in xq}
        xlabels = [r for r in read("labels_extra.jsonl") if xsplit[r["id"]] in args.extra_splits]
        xemb = np.load(DATASETS_DIR / "embeddings_extra_nomic.npy")
        vectors = np.vstack([vectors, xemb[[xrow[r["id"]] for r in xlabels]].astype(np.float32)])
        labels = labels + xlabels
    y = np.array([r["delta"] > args.threshold for r in labels], dtype=np.float32)
    np.savez(args.output, vectors=vectors, labels=y)
    print(f"{args.output}: {len(y)} wektorów ×{vectors.shape[1]}, podziały {args.splits + args.extra_splits}, COMPLEX {y.mean():.1%} (Δ > {args.threshold})")


if __name__ == "__main__":
    main()
