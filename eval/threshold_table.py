# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402

K = 20
THRESHOLD = 0.25


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    group = np.array([questions[row[i]]["group"] for i in ids])
    meta = [labels[i] for i in ids]
    y = np.array([m["delta"] > THRESHOLD for m in meta], dtype=float)
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    score = np.zeros(len(ids))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        score[te] = knn_score(X[te] @ X[tr].T, y[tr], K)
    print(f"Router kNN k={K}, przewidywania poza próbką na train+cal (n={len(ids)}); Δ > {THRESHOLD}")
    print(f"jakość: znormalizowana 0–1; zawsze mały {qs.mean():.3f}, zawsze duży {ql.mean():.3f}, różnica {ql.mean() - qs.mean():.3f}\n")
    print(f"{'próg wyniku':>12s} {'do dużego':>10s} {'jakość':>8s} {'PGR':>6s} {'utrata vs duży':>15s}")
    for t in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.01):
        big = score >= t
        q = np.where(big, ql, qs).mean()
        print(f"{t:12.2f} {big.mean():10.1%} {q:8.3f} {(q - qs.mean()) / (ql.mean() - qs.mean()):6.2f} {ql.mean() - q:15.3f}")
    print("\nrozkład wyniku routera (kwantyle):", ", ".join(f"{p}%: {np.percentile(score, p):.2f}" for p in (10, 25, 50, 75, 90)))


if __name__ == "__main__":
    main()
