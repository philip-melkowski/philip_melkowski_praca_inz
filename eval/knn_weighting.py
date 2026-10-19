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
from router_baselines import DATASETS_DIR, SEED, pgr_curve, read  # noqa: E402

THR = 0.25
BOOT = 500
KS = (1, 5, 10, 20, 40, 80)
SCHEMES = {
    "równe wagi": lambda s: np.ones_like(s),
    "waga = podobieństwo (obecna)": lambda s: np.clip(s, 1e-6, None),
    "waga = podobieństwo^4": lambda s: np.clip(s, 1e-6, None) ** 4,
    "waga = podobieństwo^10": lambda s: np.clip(s, 1e-6, None) ** 10,
    "waga = exp(podobieństwo / 0,05)": lambda s: np.exp((s - s.max(axis=1, keepdims=True)) / 0.05),
}


def knn(sim: np.ndarray, target: np.ndarray, k: int, scheme) -> np.ndarray:
    idx = np.argpartition(-sim, k - 1, axis=1)[:, :k] if k < sim.shape[1] else np.tile(np.arange(sim.shape[1]), (len(sim), 1))
    s = np.take_along_axis(sim, idx, axis=1)
    w = scheme(s)
    return (w * target[idx]).sum(1) / w.sum(1)


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

    def evaluate(s: np.ndarray) -> np.ndarray:
        return np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots])

    scores = {}
    for name, scheme in SCHEMES.items():
        for k in KS:
            oof = np.zeros(len(ids))
            for tr, te in folds:
                oof[te] = knn(X[te] @ X[tr].T, y[tr].astype(float), k, scheme)
            scores[(name, k)] = evaluate(oof)
    base = scores[("waga = podobieństwo (obecna)", 20)]
    print(f"{len(ids)} pytań, CV po grupach; AUROC / APGR (średnia z bootstrapu), różnica APGR względem obecnej (k=20) [95% CI]\n")
    print(f"{'schemat wag':34s} " + " ".join(f"{'k=' + str(k):>22s}" for k in KS))
    for name in SCHEMES:
        cells = []
        for k in KS:
            a = scores[(name, k)]
            d = a[:, 1] - base[:, 1]
            cells.append(f"{a[:, 0].mean():.3f}/{a[:, 1].mean():.3f} ({d.mean():+.3f})")
        print(f"{name:34s} " + " ".join(f"{c:>22s}" for c in cells))
    best = max(scores, key=lambda key: scores[key][:, 1].mean())
    d = scores[best][:, 1] - base[:, 1]
    print(f"\nnajlepszy wariant wg APGR: {best}: {scores[best][:, 1].mean():.3f}; różnica względem obecnej {d.mean():+.3f} [{np.percentile(d, 2.5):+.3f}; {np.percentile(d, 97.5):+.3f}]")


if __name__ == "__main__":
    main()
