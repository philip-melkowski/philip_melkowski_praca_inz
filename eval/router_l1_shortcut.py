# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402
from router_l1_expanded import counts, pick_terms  # noqa: E402
from router_layers import l1_features  # noqa: E402

THR = 0.25
COVERAGE = (0.05, 0.10, 0.20, 0.30)


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    texts = [questions[row[i]]["prompt"] for i in ids]
    F = np.array([l1_features(questions[row[i]]["prompt"], questions[row[i]]["tokens"]) for i in ids])
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    delta = np.array([m["delta"] for m in meta])
    y = delta > THR
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    s = {k: np.zeros(len(ids)) for k in ("L1 obecna", "L1 + lista słów (N=100)", "kNN (L2)")}
    for tr, te in folds:
        s["kNN (L2)"][te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), 20)
        sc = StandardScaler().fit(F[tr])
        s["L1 obecna"][te] = LogisticRegression(C=0.1, max_iter=3000).fit(sc.transform(F[tr]), y[tr]).predict_proba(sc.transform(F[te]))[:, 1]
        cx, sx = pick_terms([texts[i] for i in tr], y[tr], 100)
        ftr = np.column_stack([F[tr], counts([texts[i] for i in tr], cx), counts([texts[i] for i in tr], sx)])
        fte = np.column_stack([F[te], counts([texts[i] for i in te], cx), counts([texts[i] for i in te], sx)])
        sc2 = StandardScaler().fit(ftr)
        s["L1 + lista słów (N=100)"][te] = LogisticRegression(C=0.1, max_iter=3000).fit(sc2.transform(ftr), y[tr]).predict_proba(sc2.transform(fte))[:, 1]

    print(f"{len(ids)} pytań (CV po grupach); bazowo COMPLEX {y.mean():.1%}, średnie Δ {delta.mean():+.3f}\n")
    print("Skrót SIMPLE: warstwa wybiera X% pytań, które uważa za najłatwiejsze (kierowane do małego bez warstwy 2).")
    print(f"{'pokrycie':>9s} {'metoda':26s} {'% COMPLEX w tej grupie':>24s} {'średnie Δ':>10s}")
    for c in COVERAGE:
        for name, sc_ in s.items():
            idx = np.argsort(sc_)[: int(c * len(ids))]
            print(f"{c:9.0%} {name:26s} {y[idx].mean():24.1%} {delta[idx].mean():+10.3f}")
        print()
    print("Skrót COMPLEX: X% pytań uważanych za najtrudniejsze (kierowane do dużego bez warstwy 2).")
    print(f"{'pokrycie':>9s} {'metoda':26s} {'% COMPLEX w tej grupie':>24s} {'średnie Δ':>10s}")
    for c in COVERAGE:
        for name, sc_ in s.items():
            idx = np.argsort(sc_)[::-1][: int(c * len(ids))]
            print(f"{c:9.0%} {name:26s} {y[idx].mean():24.1%} {delta[idx].mean():+10.3f}")
        print()


if __name__ == "__main__":
    main()
