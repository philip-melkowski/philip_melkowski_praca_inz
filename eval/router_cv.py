# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402
from router_layers import l1_features  # noqa: E402

K = 20
BOOT = 1000
THRESHOLDS = (0.15, 0.25, 0.35)


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    F = np.array([l1_features(questions[row[i]]["prompt"], questions[row[i]]["tokens"]) for i in ids])
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    source = np.array([m["source"] for m in meta])
    delta = np.array([m["delta"] for m in meta])
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    tokens = np.array([questions[row[i]]["tokens"] for i in ids], dtype=float)
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    rng = np.random.default_rng(SEED)
    print(f"train+cal: {len(ids)} pytań, walidacja krzyżowa po grupach (5 części); test nie jest używany\n")

    for thr in THRESHOLDS:
        y = delta > thr
        oof = {name: np.zeros(len(ids)) for name in ("sama długość", "samo źródło", "L1 reguły", "L2 kNN k=20", "L1+L2 LR")}
        for tr, te in folds:
            oof["sama długość"][te] = np.log(tokens[te])
            prior = {s: y[tr][source[tr] == s].mean() for s in set(source[tr])}
            oof["samo źródło"][te] = [prior.get(s, y[tr].mean()) for s in source[te]]
            sc = StandardScaler().fit(F[tr])
            Ftr, Fte = sc.transform(F[tr]), sc.transform(F[te])
            oof["L1 reguły"][te] = LogisticRegression(C=0.1, max_iter=3000).fit(Ftr, y[tr]).decision_function(Fte)
            oof["L2 kNN k=20"][te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)
            oof["L1+L2 LR"][te] = LogisticRegression(C=1.0, max_iter=3000).fit(np.hstack([X[tr], Ftr]), y[tr]).decision_function(np.hstack([X[te], Fte]))
        n = len(ids)
        boots = [b for b in (rng.integers(0, n, n) for _ in range(BOOT)) if 0 < y[b].sum() < n]
        res: dict[str, np.ndarray] = {
            name: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots]) for name, s in oof.items()
        }
        print(f"=== próg Δ > {thr} (COMPLEX {y.mean():.1%}) ===")
        print(f"{'metoda':16s} {'AUROC [95% CI]':26s} {'APGR [95% CI]':26s}")
        for name, a in res.items():
            print(f"{name:16s} {a[:, 0].mean():.3f} [{np.percentile(a[:, 0], 2.5):.3f},{np.percentile(a[:, 0], 97.5):.3f}]      {a[:, 1].mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f},{np.percentile(a[:, 1], 97.5):.3f}]")
        for a_, b_ in (("L2 kNN k=20", "samo źródło"), ("L2 kNN k=20", "sama długość"), ("L1+L2 LR", "L2 kNN k=20"), ("L2 kNN k=20", "L1 reguły")):
            d = res[a_] - res[b_]
            print(f"  różnica {a_} − {b_}: AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f},{np.percentile(d[:, 0], 97.5):+.3f}]  APGR {d[:, 1].mean():+.3f} [{np.percentile(d[:, 1], 2.5):+.3f},{np.percentile(d[:, 1], 97.5):+.3f}]")
        print()


if __name__ == "__main__":
    main()
