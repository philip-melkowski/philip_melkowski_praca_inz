# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

THRESHOLD = 0.25
BOOT = 500


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    group = np.array([questions[row[i]]["group"] for i in ids])
    meta = [labels[i] for i in ids]
    delta = np.array([m["delta"] for m in meta])
    y = delta > THRESHOLD
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    rng = np.random.default_rng(SEED)

    def oof(fit_predict: Any) -> np.ndarray:
        out = np.zeros(len(ids))
        for tr, te in folds:
            out[te] = fit_predict(X[tr], y[tr], delta[tr], X[te])
        return out

    models = {
        "kNN k=20 (odniesienie)": lambda a, b, d, c: knn_score(c @ a.T, b.astype(float), 20),
        "kNN k=40": lambda a, b, d, c: knn_score(c @ a.T, b.astype(float), 40),
        "regresja logistyczna C=1": lambda a, b, d, c: LogisticRegression(C=1.0, max_iter=3000).fit(a, b).decision_function(c),
        "regresja logistyczna C=0,1": lambda a, b, d, c: LogisticRegression(C=0.1, max_iter=3000).fit(a, b).decision_function(c),
        "SVM RBF C=1": lambda a, b, d, c: SVC(C=1.0, kernel="rbf").fit(a, b).decision_function(c),
        "SVM RBF C=10": lambda a, b, d, c: SVC(C=10.0, kernel="rbf").fit(a, b).decision_function(c),
        "regresja grzbietowa na ciągłym Δ": lambda a, b, d, c: Ridge(alpha=10.0).fit(a, d).predict(c),
        "MLP (1 warstwa 128)": lambda a, b, d, c: MLPClassifier((128,), alpha=1e-2, early_stopping=True, random_state=SEED, max_iter=300).fit(a, b).predict_proba(c)[:, 1],
        "boosting drzew na PCA(64)": lambda a, b, d, c: _hgb(a, b, c),
    }
    scores = {name: oof(fn) for name, fn in models.items()}
    n = len(ids)
    boots = [b for b in (rng.integers(0, n, n) for _ in range(BOOT)) if 0 < y[b].sum() < n]
    base = scores["kNN k=20 (odniesienie)"]
    base_boot = np.array([pgr_curve(base[b], ql[b], qs[b], rng).mean() for b in boots])
    print(f"train+cal {n} pytań, walidacja krzyżowa po grupach (5 części), Δ > {THRESHOLD}; test nie jest używany\n")
    print(f"{'model':36s} {'AUROC':>6s} {'APGR':>6s} {'różnica APGR vs kNN k=20 [95% CI]':>36s}")
    for name, s in scores.items():
        apgr = pgr_curve(s, ql, qs, rng).mean()
        sb = np.array([pgr_curve(s[b], ql[b], qs[b], rng).mean() for b in boots])
        d = sb - base_boot
        print(f"{name:36s} {roc_auc_score(y, s):6.3f} {apgr:6.3f} {d.mean():+.3f} [{np.percentile(d, 2.5):+.3f},{np.percentile(d, 97.5):+.3f}]")


def _hgb(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    pca = PCA(n_components=64, random_state=SEED).fit(a)
    model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=SEED).fit(pca.transform(a), b)
    return model.predict_proba(pca.transform(c))[:, 1]


if __name__ == "__main__":
    main()
