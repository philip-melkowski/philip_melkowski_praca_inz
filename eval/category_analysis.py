# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    pool = [r for r in read("labels.jsonl") if r["split"] in ("train", "cal")]
    X = emb[[row[r["id"]] for r in pool]]
    delta = np.array([r["delta"] for r in pool])
    y = (delta > 0.25).astype(float)
    group = np.array([questions[row[r["id"]]]["group"] for r in pool])
    cat = np.array([questions[row[r["id"]]]["category"] or "" for r in pool])
    score = np.zeros(len(pool))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        score[te] = knn_score(X[te] @ X[tr].T, y[tr], 20)

    print("pytania z kategorią (Arena i pytania Gemini), train+cal, kNN poza próbką\n")
    print(f"{'kategoria':26s} {'n':>5s} {'COMPLEX':>8s} {'śr.Δ':>6s} {'śr. wynik routera':>18s} {'AUROC wewn.':>12s}")
    stats = defaultdict(list)
    for c in sorted(set(cat) - {""}):
        m = cat == c
        stats[c] = [int(m.sum()), y[m].mean(), delta[m].mean(), score[m].mean(), roc_auc_score(y[m], score[m]) if 0 < y[m].sum() < m.sum() and m.sum() >= 30 else float("nan")]
    for c, (n, comp, d, sc, auc) in sorted(stats.items(), key=lambda kv: -kv[1][1]):
        print(f"{c:26s} {n:5d} {comp:8.1%} {d:+6.2f} {sc:18.2f} {auc:12.3f}")


if __name__ == "__main__":
    main()
