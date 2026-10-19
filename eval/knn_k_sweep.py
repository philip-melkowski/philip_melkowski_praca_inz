# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

KS = (1, 3, 5, 10, 20, 40, 80, 160)
THR = 0.25
BOOT = 500


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    group = np.array([questions[row[i]]["group"] for i in ids])
    y = np.array([labels[i]["delta"] for i in ids]) > THR
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    rng = np.random.default_rng(SEED)
    boots = [rng.integers(0, len(ids), len(ids)) for _ in range(BOOT)]
    print(f"{len(ids)} pytań, CV po grupach (5), Δ > {THR}; test nie użyty\n{'k':>4s} {'AUROC [95% CI]':>24s} {'APGR [95% CI]':>24s}")
    for k in KS:
        oof = np.zeros(len(ids))
        for tr, te in folds:
            oof[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), min(k, len(tr)))
        a = np.array([(roc_auc_score(y[b], oof[b]), pgr_curve(oof[b], ql[b], qs[b], rng).mean()) for b in boots])
        print(f"{k:4d} {a[:, 0].mean():.3f} [{np.percentile(a[:, 0], 2.5):.3f},{np.percentile(a[:, 0], 97.5):.3f}]   {a[:, 1].mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f},{np.percentile(a[:, 1], 97.5):.3f}]")


if __name__ == "__main__":
    main()
