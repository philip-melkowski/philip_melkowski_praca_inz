# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

K = 20
BOOT = 1000
CS = (0.1, 0.3, 1.0, 3.0, 10.0)
THR = 0.25


def rank01(s: np.ndarray) -> np.ndarray:
    return (rankdata(s) - 1) / (len(s) - 1)


def tfidf_lr(texts: list[str], y: np.ndarray, group: np.ndarray, tr: np.ndarray, te: np.ndarray, **vec_kw) -> np.ndarray:
    def fit_predict(a: np.ndarray, b: np.ndarray, c: float) -> np.ndarray:
        v = TfidfVectorizer(sublinear_tf=True, **vec_kw)
        xa = v.fit_transform([texts[i] for i in a])
        xb = v.transform([texts[i] for i in b])
        return LogisticRegression(C=c, max_iter=3000).fit(xa, y[a]).decision_function(xb)

    inner = list(GroupKFold(n_splits=3).split(tr, groups=group[tr]))
    best = max(CS, key=lambda c: np.mean([roc_auc_score(y[tr][b], fit_predict(tr[a], tr[b], c)) for a, b in inner]))
    return fit_predict(tr, te, best)


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    texts = [questions[row[i]]["prompt"] for i in ids]
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    source = np.array([m["source"] for m in meta])
    y = np.array([m["delta"] for m in meta]) > THR
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    print(f"train+cal: {len(ids)} pytań, CV po grupach (5 części), Δ > {THR}; test nie jest używany\n")

    oof = {name: np.zeros(len(ids)) for name in ("kNN k=20", "słowa tf-idf 1-2gram", "znaki tf-idf 3-5gram", "kNN + słowa", "kNN + słowa + znaki")}
    for tr, te in folds:
        oof["kNN k=20"][te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)
        oof["słowa tf-idf 1-2gram"][te] = tfidf_lr(texts, y, group, tr, te, ngram_range=(1, 2), min_df=3, lowercase=True)
        oof["znaki tf-idf 3-5gram"][te] = tfidf_lr(texts, y, group, tr, te, analyzer="char_wb", ngram_range=(3, 5), min_df=5, lowercase=True)
        a, b, c = (rank01(oof[n][te]) for n in ("kNN k=20", "słowa tf-idf 1-2gram", "znaki tf-idf 3-5gram"))
        oof["kNN + słowa"][te] = a + b
        oof["kNN + słowa + znaki"][te] = a + b + c

    rng = np.random.default_rng(SEED)
    n = len(ids)
    boots = [b for b in (rng.integers(0, n, n) for _ in range(BOOT)) if 0 < y[b].sum() < n]
    res = {name: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots]) for name, s in oof.items()}
    print(f"{'metoda':26s} {'AUROC [95% CI]':26s} {'APGR [95% CI]':26s}")
    for name, a in res.items():
        print(f"{name:26s} {a[:, 0].mean():.3f} [{np.percentile(a[:, 0], 2.5):.3f},{np.percentile(a[:, 0], 97.5):.3f}]      {a[:, 1].mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f},{np.percentile(a[:, 1], 97.5):.3f}]")
    for other in ("słowa tf-idf 1-2gram", "kNN + słowa", "kNN + słowa + znaki"):
        d = res[other] - res["kNN k=20"]
        print(f"  różnica {other} − kNN: AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f},{np.percentile(d[:, 0], 97.5):+.3f}]  APGR {d[:, 1].mean():+.3f} [{np.percentile(d[:, 1], 2.5):+.3f},{np.percentile(d[:, 1], 97.5):+.3f}]")

    print("\nAUROC wewnątrz źródła (czy słowa to nie tylko zastępnik źródła):")
    for src in sorted(set(source)):
        m = source == src
        if 0 < y[m].sum() < m.sum() and m.sum() >= 40:
            print(f"  {src:14s} n={m.sum():4d} COMPLEX {y[m].mean():5.1%}  kNN {roc_auc_score(y[m], oof['kNN k=20'][m]):.3f}  słowa {roc_auc_score(y[m], oof['słowa tf-idf 1-2gram'][m]):.3f}  kNN+słowa {roc_auc_score(y[m], oof['kNN + słowa'][m]):.3f}")

    v = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=5, lowercase=True)
    xa = v.fit_transform(texts)
    w = LogisticRegression(C=1.0, max_iter=3000).fit(xa, y).coef_[0]
    names = np.array(v.get_feature_names_out())
    order = np.argsort(w)
    print("\nnajsilniejsze wyrazy (model na całym train+cal, tylko do opisu):")
    print("  → COMPLEX:", ", ".join(names[order[-25:]][::-1]))
    print("  → SIMPLE: ", ", ".join(names[order[:25]]))


if __name__ == "__main__":
    main()
