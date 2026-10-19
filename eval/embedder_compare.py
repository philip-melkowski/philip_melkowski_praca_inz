# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

BOOT = 1000
KS = (10, 20, 40)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("embeddings", nargs="+", help="pliki .npy w data/datasets (pierwszy = odniesienie, nomic)")
    args = p.parse_args()

    questions = read("questions_v2_split.jsonl")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    idx = [row[i] for i in ids]
    meta = [labels[i] for i in ids]
    group = np.array([questions[i]["group"] for i in idx])
    y = np.array([m["delta"] > 0.25 for m in meta])
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    folds = list(GroupKFold(n_splits=5).split(np.zeros(len(ids)), groups=group))
    rng = np.random.default_rng(SEED)
    n = len(ids)
    boots = [b for b in (rng.integers(0, n, n) for _ in range(BOOT)) if 0 < y[b].sum() < n]

    results: dict[str, np.ndarray] = {}
    print(f"train+cal {n} pytań, walidacja krzyżowa po grupach; kNN, Δ > 0,25\n")
    print(f"{'embedder':28s} {'wymiar':>6s} {'k':>3s} {'AUROC':>6s} {'APGR':>6s}")
    for name in args.embeddings:
        X = np.load(DATASETS_DIR / name)[idx]
        best_k, best_auc, best_s = 0, -1.0, np.zeros(n)
        for k in KS:
            s = np.zeros(n)
            for tr, te in folds:
                s[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), k)
            auc = roc_auc_score(y, s)
            print(f"{name:28s} {X.shape[1]:6d} {k:3d} {auc:6.3f} {pgr_curve(s, ql, qs, rng).mean():6.3f}")
            if auc > best_auc:
                best_k, best_auc, best_s = k, auc, s
        results[name] = np.array([(roc_auc_score(y[b], best_s[b]), pgr_curve(best_s[b], ql[b], qs[b], rng).mean()) for b in boots])
        print(f"  → najlepsze k={best_k} (wybrane na tych samych danych, więc lekko optymistyczne)")
    ref = args.embeddings[0]
    print(f"\nróżnice parowane względem {ref} (95% CI):")
    for name in args.embeddings[1:]:
        d = results[name] - results[ref]
        print(f"  {name}: AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f},{np.percentile(d[:, 0], 97.5):+.3f}]  APGR {d[:, 1].mean():+.3f} [{np.percentile(d[:, 1], 2.5):+.3f},{np.percentile(d[:, 1], 97.5):+.3f}]")


if __name__ == "__main__":
    main()
