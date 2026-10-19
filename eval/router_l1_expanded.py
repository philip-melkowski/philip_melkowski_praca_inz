# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402
from router_layers import l1_features  # noqa: E402

K = 20
BOOT = 1000
THR = 0.25
SIZES = (10, 30, 100)
MIN_DF = 8


def rank01(s: np.ndarray) -> np.ndarray:
    return (rankdata(s) - 1) / (len(s) - 1)


def pick_terms(texts: list[str], y: np.ndarray, n: int) -> tuple[list[str], list[str]]:
    vec = CountVectorizer(binary=True, ngram_range=(1, 2), min_df=MIN_DF, lowercase=True)
    x = vec.fit_transform(texts)
    names = np.array(vec.get_feature_names_out())
    pos = np.asarray(x[y].sum(axis=0)).ravel() + 0.5
    neg = np.asarray(x[~y].sum(axis=0)).ravel() + 0.5
    lo = np.log(pos / (y.sum() + 1)) - np.log(neg / ((~y).sum() + 1))
    z = lo / np.sqrt(1 / pos + 1 / neg)
    order = np.argsort(z)
    return list(names[order[-n:]]), list(names[order[:n]])


def counts(texts: list[str], terms: list[str]) -> np.ndarray:
    vec = CountVectorizer(binary=True, ngram_range=(1, 2), lowercase=True, vocabulary=terms)
    return np.asarray(vec.transform(texts).sum(axis=1)).ravel().astype(float)


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
    y = np.array([m["delta"] for m in meta]) > THR
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    print(f"train+cal: {len(ids)} pytań, CV po grupach (5), Δ > {THR}; listy słów wybierane WEWNĄTRZ każdej części wyłącznie z jej części uczącej; test nie użyty\n")

    names = ["kNN k=20", "L1 (obecna: 10 cech)", *[f"L1 + lista słów N={n}" for n in SIZES], "L1 + kNN", *[f"L1(N={n}) + kNN" for n in SIZES]]
    oof = {k: np.zeros(len(ids)) for k in names}
    for tr, te in folds:
        knn = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)
        oof["kNN k=20"][te] = knn
        sc = StandardScaler().fit(F[tr])
        base = LogisticRegression(C=0.1, max_iter=3000).fit(sc.transform(F[tr]), y[tr]).decision_function(sc.transform(F[te]))
        oof["L1 (obecna: 10 cech)"][te] = base
        oof["L1 + kNN"][te] = rank01(knn) + rank01(base)
        for n in SIZES:
            cx, sx = pick_terms([texts[i] for i in tr], y[tr], n)
            ftr = np.column_stack([F[tr], counts([texts[i] for i in tr], cx), counts([texts[i] for i in tr], sx)])
            fte = np.column_stack([F[te], counts([texts[i] for i in te], cx), counts([texts[i] for i in te], sx)])
            sc2 = StandardScaler().fit(ftr)
            s = LogisticRegression(C=0.1, max_iter=3000).fit(sc2.transform(ftr), y[tr]).decision_function(sc2.transform(fte))
            oof[f"L1 + lista słów N={n}"][te] = s
            oof[f"L1(N={n}) + kNN"][te] = rank01(knn) + rank01(s)

    rng = np.random.default_rng(SEED)
    n_all = len(ids)
    boots = [b for b in (rng.integers(0, n_all, n_all) for _ in range(BOOT)) if 0 < y[b].sum() < n_all]
    res = {k: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots]) for k, s in oof.items()}
    print(f"{'metoda':28s} {'AUROC [95% CI]':26s} {'APGR [95% CI]':26s}")
    for k, a in res.items():
        print(f"{k:28s} {a[:, 0].mean():.3f} [{np.percentile(a[:, 0], 2.5):.3f},{np.percentile(a[:, 0], 97.5):.3f}]      {a[:, 1].mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f},{np.percentile(a[:, 1], 97.5):.3f}]")
    print()
    for a_, b_ in [(f"L1 + lista słów N={n}", "L1 (obecna: 10 cech)") for n in SIZES] + [(f"L1(N={n}) + kNN", "kNN k=20") for n in SIZES] + [(f"L1(N={n}) + kNN", "L1 + kNN") for n in SIZES]:
        d = res[a_] - res[b_]
        print(f"  {a_} − {b_}: AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f},{np.percentile(d[:, 0], 97.5):+.3f}]  APGR {d[:, 1].mean():+.3f} [{np.percentile(d[:, 1], 2.5):+.3f},{np.percentile(d[:, 1], 97.5):+.3f}]")

    tr = np.arange(len(ids))
    for n in (30,):
        cx, sx = pick_terms(texts, y, n)
        print(f"\nlista N={n} z całego train+cal (tylko opis, nie do oceny):\n  COMPLEX: {', '.join(cx[::-1])}\n  SIMPLE: {', '.join(sx)}")


if __name__ == "__main__":
    main()
