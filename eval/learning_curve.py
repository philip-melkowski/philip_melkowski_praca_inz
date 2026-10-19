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

FRACTIONS = (0.1, 0.25, 0.5, 0.75, 1.0)
REPEATS = 5


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    pool = [r for r in read("labels.jsonl") if r["split"] in ("train", "cal")]
    X = emb[[row[r["id"]] for r in pool]]
    delta = np.array([r["delta"] for r in pool])
    y = (delta > 0.25).astype(float)
    ql = np.array([r["q_large"] for r in pool])
    qs = np.array([r["q_small"] for r in pool])
    group = np.array([questions[row[r["id"]]]["group"] for r in pool])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    rng = np.random.default_rng(SEED)
    print(f"krzywa uczenia: kNN k=20, train+cal ({len(pool)} pytań), walidacja krzyżowa po grupach; indeks = część części uczącej (średnia z {REPEATS} losowań)\n")
    print(f"{'udział indeksu':>14s} {'pytań w indeksie (śr.)':>23s} {'AUROC':>7s} {'APGR':>7s}")
    for frac in FRACTIONS:
        aucs, apgrs, sizes = [], [], []
        for _ in range(REPEATS):
            s = np.zeros(len(pool))
            n_used = 0
            for tr, te in folds:
                sub = rng.choice(tr, size=max(25, int(len(tr) * frac)), replace=False)
                n_used += len(sub)
                s[te] = knn_score(X[te] @ X[sub].T, y[sub], min(20, len(sub)))
            aucs.append(roc_auc_score(y > 0.5, s))
            apgrs.append(pgr_curve(s, ql, qs, rng).mean())
            sizes.append(n_used / len(folds))
        print(f"{frac:14.0%} {np.mean(sizes):23.0f} {np.mean(aucs):7.3f} {np.mean(apgrs):7.3f}")


if __name__ == "__main__":
    main()
