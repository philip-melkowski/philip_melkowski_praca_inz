# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from l1_heuristics import FEATURE_NAMES, export_spec, features  # noqa: E402
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

THR = 0.25
C = 0.1
ALPHAS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0)
BOOT = 1000


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    F = np.array([features(questions[row[i]]["prompt"]) for i in ids])
    group = np.array([questions[row[i]]["group"] for i in ids])
    y = np.array([labels[i]["delta"] for i in ids]) > THR
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    knn = np.zeros(len(ids))
    p1 = np.zeros(len(ids))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        knn[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), 20)
        sc = StandardScaler().fit(F[tr])
        p1[te] = LogisticRegression(C=C, max_iter=3000).fit(sc.transform(F[tr]), y[tr]).predict_proba(sc.transform(F[te]))[:, 1]
    rng = np.random.default_rng(SEED)
    n = len(ids)
    boots = [b for b in (rng.integers(0, n, n) for _ in range(BOOT)) if 0 < y[b].sum() < n]
    print(f"{n} pytań, CV po grupach (5); cechy ({len(FEATURE_NAMES)}): {', '.join(FEATURE_NAMES)}\n")
    print(f"{'waga heurystyk α':>17s} {'AUROC [95% CI]':>24s} {'APGR [95% CI]':>24s}   różnica APGR vs kNN [95% CI]")
    base = None
    res = {}
    for a in ALPHAS:
        s = (1 - a) * knn + a * p1
        arr = np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots])
        res[a] = arr
    for a in ALPHAS:
        arr = res[a]
        d = arr[:, 1] - res[0.0][:, 1]
        print(f"{a:17.1f} {arr[:, 0].mean():.3f} [{np.percentile(arr[:, 0], 2.5):.3f},{np.percentile(arr[:, 0], 97.5):.3f}]   {arr[:, 1].mean():.3f} [{np.percentile(arr[:, 1], 2.5):.3f},{np.percentile(arr[:, 1], 97.5):.3f}]   {d.mean():+.3f} [{np.percentile(d, 2.5):+.3f};{np.percentile(d, 97.5):+.3f}]")
    sc = StandardScaler().fit(F)
    lr = LogisticRegression(C=C, max_iter=3000).fit(sc.transform(F), y)
    spec = export_spec(sc.mean_, sc.scale_, lr.coef_[0], float(lr.intercept_[0]), {"trained_on": "train+cal", "n": n, "C": C, "label": f"delta>{THR}"})
    out = Path(__file__).parent.parent / "data" / "router_l1_logistic.json"
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nzapisano {out}; wagi (po standaryzacji):")
    for name, w in sorted(zip(FEATURE_NAMES, lr.coef_[0], strict=True), key=lambda x: -abs(x[1])):
        print(f"  {name:14s} {w:+.3f}")
    print(f"liczba fraz: COMPLEX {len(spec['complex_phrases'])}, SIMPLE {len(spec['simple_phrases'])}")


if __name__ == "__main__":
    main()
