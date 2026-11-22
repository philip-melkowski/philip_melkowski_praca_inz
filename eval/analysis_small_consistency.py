# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""Sygnał po wygenerowaniu odpowiedzi (PRZEMYSLENIA pkt 5.3): czy zgodność próbek małego modelu przewiduje trudność.

Bez przecieku: predyktory liczone z próbek 0 i 1 małego modelu, etykieta z próbki 2 (Δ₂ = jakość dużego − jakość
próbki 2 > 0,25). Tylko train, etykiety v3 (`data/labels/`). To górna granica dla kaskady: wymaga wygenerowania
dwóch odpowiedzi małego modelu i ich oceny, więc nie jest dostępna przy routingu przed odpowiedzią."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, group_bootstrap, knn_score, read  # noqa: E402

ROOT = Path(__file__).parent.parent
THR = 0.25
K = 20


def main() -> None:
    rng = np.random.default_rng(SEED)
    with (ROOT / "data" / "labels" / "labels_v3.jsonl").open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in map(json.loads, f) if r["split"] == "train"}
    small: dict[str, dict[int, float]] = defaultdict(dict)
    large: dict[str, float] = {}
    with (ROOT / "data" / "labels" / "sample_scores_v3.jsonl").open(encoding="utf-8") as f:
        for s in map(json.loads, f):
            if s["id"] not in labels:
                continue
            if s["model"].startswith("Qwen/"):
                large[s["id"]] = s["quality"]
            else:
                small[s["id"]][s["sample"]] = s["quality"]
    ids = [i for i in labels if i in large and set(small[i]) >= {0, 1, 2}]
    q = {q["id"]: q for q in read("questions_v2_split.jsonl")}
    q0 = np.array([small[i][0] for i in ids])
    q1 = np.array([small[i][1] for i in ids])
    q2 = np.array([small[i][2] for i in ids])
    ql = np.array([large[i] for i in ids])
    y = (ql - q2) > THR
    g = np.array([str(q[i]["group"]) for i in ids])
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {qq["id"]: n for n, qq in enumerate(read("questions_v2_split.jsonl"))}
    X = emb[[row[i] for i in ids]]
    from sklearn.model_selection import GroupKFold

    knn = np.zeros(len(ids))
    for a, b in GroupKFold(n_splits=5).split(X, groups=g):
        knn[b] = knn_score(X[b] @ X[a].T, y[a].astype(float), K)

    preds = {
        "kNN (przed odpowiedzią)": knn,
        "niezgodność próbek 0 i 1 (|q0 − q1|)": np.abs(q0 - q1),
        "niska jakość małego (1 − średnia q0, q1)": 1 - (q0 + q1) / 2,
    }
    print(f"train: {len(ids)} pytań, etykieta z próbki 2: COMPLEX {y.mean():.1%}\n")
    boots = [group_bootstrap(g, rng) for _ in range(1000)]
    for name, s in preds.items():
        vals = [roc_auc_score(y[b], s[b]) for b in boots if 0 < y[b].sum() < len(b)]
        print(f"  {name:42s} AUROC {roc_auc_score(y, s):.3f} [{np.percentile(vals, 2.5):.3f}; {np.percentile(vals, 97.5):.3f}]")
    agree = q0 == q1
    print(f"\n  próbki 0 i 1 z tą samą oceną: {agree.mean():.1%} pytań; COMPLEX wśród zgodnych {y[agree].mean():.1%}, wśród niezgodnych {y[~agree].mean():.1%}")


if __name__ == "__main__":
    main()
