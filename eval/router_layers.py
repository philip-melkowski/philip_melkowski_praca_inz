# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from analyze_keywords import COMPLEX_CANDIDATES, SIMPLE_CANDIDATES  # noqa: E402
from router_baselines import CS, DATASETS_DIR, SEED, knn_score, metrics, read  # noqa: E402

COMPLEX_RE = [re.compile(rf"\b{re.escape(w)}\b") for w, _ in COMPLEX_CANDIDATES]
SIMPLE_RE = [re.compile(rf"\b{re.escape(w)}\b") for w, _ in SIMPLE_CANDIDATES]
K = 20


def l1_features(text: str, tokens: int) -> list[float]:
    low = text.lower()
    return [
        math.log(tokens),
        math.log1p(len(text)),
        math.log1p(text.count("\n")),
        float(text.count("```")),
        sum(c.isdigit() for c in text) / max(len(text), 1),
        float(text.count("?")),
        float(bool(re.search(r"\b(def|class|function|import|return|void|int)\b|[{};]", text))),
        float("http" in low),
        float(sum(bool(r.search(low)) for r in COMPLEX_RE)),
        float(sum(bool(r.search(low)) for r in SIMPLE_RE)),
    ]


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels]
    X = emb[[row[i] for i in ids]]
    F = np.array([l1_features(questions[row[i]]["prompt"], questions[row[i]]["tokens"]) for i in ids])
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    split = np.array([m["split"] for m in meta])
    y = np.array([m["label"] == "COMPLEX" for m in meta])
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    source = np.array([m["source"] for m in meta])
    tr, ca = split == "train", split == "cal"
    d_cal = {"ql": ql[ca], "qs": qs[ca], "y": y[ca]}
    rng = np.random.default_rng(SEED)

    Xt, Ft, yt, gt = X[tr], F[tr], y[tr], group[tr]
    cv = list(GroupKFold(n_splits=5).split(Xt, yt, gt))
    scaler = StandardScaler().fit(Ft)
    Fs, Fts = scaler.transform(F), scaler.transform(Ft)

    def fit_lr(A: np.ndarray, B: np.ndarray) -> tuple[LogisticRegression, float]:
        def cv_auc(c: float) -> float:
            return float(np.mean([roc_auc_score(yt[b], LogisticRegression(C=c, max_iter=3000).fit(A[a], yt[a]).decision_function(A[b])) for a, b in cv]))

        best = max(CS, key=cv_auc)
        return LogisticRegression(C=best, max_iter=3000).fit(A, yt), best

    results = []
    m1, c1 = fit_lr(Fts, Fts)
    results.append(metrics(f"L1: reguły (LR na cechach, C={c1})", m1.decision_function(Fs[ca]), d_cal, rng))
    results.append(metrics(f"L2: kNN k={K}", knn_score(X[ca] @ Xt.T, yt.astype(float), K), d_cal, rng))

    concat_t, concat_all = np.hstack([Xt, Fts]), np.hstack([X, Fs])
    m12, c12 = fit_lr(concat_t, concat_t)
    results.append(metrics(f"L1+L2: LR na [embedding + cechy] (C={c12})", m12.decision_function(concat_all[ca]), d_cal, rng))

    oof = np.zeros(len(yt))
    for a, b in cv:
        oof[b] = knn_score(Xt[b] @ Xt[a].T, yt[a].astype(float), K)
    logit = lambda p: np.log((p + 0.02) / (1.02 - p))  # noqa: E731
    stack_t = np.hstack([logit(oof)[:, None], Fts])
    ms, cs = fit_lr(stack_t, stack_t)
    stack_cal = np.hstack([logit(knn_score(X[ca] @ Xt.T, yt.astype(float), K))[:, None], Fs[ca]])
    s_stack = ms.decision_function(stack_cal)
    results.append(metrics(f"L1+L2: kNN + cechy, stacking (C={cs})", s_stack, d_cal, rng))

    print(f"{'warstwy (zbiór cal)':50s} {'AUROC':>6s} {'95% CI':>13s} {'APGR':>6s} {'95% CI':>13s} {'CPT50':>6s} {'CPT80':>6s}")
    for r in results:
        print(
            f"{r['name']:50s} {r['auc']:6.3f} [{r['auc_ci'][0]:.3f},{r['auc_ci'][1]:.3f}] {r['apgr']:6.3f} "
            f"[{r['apgr_ci'][0]:.3f},{r['apgr_ci'][1]:.3f}] {r['cpt50']:6.2f} {r['cpt80']:6.2f}"
        )
    print("\nAUROC wg źródła (najlepszy model = LR na [embedding + cechy]), zbiór cal:")
    s = m12.decision_function(concat_all[ca])
    for src in sorted(set(source[ca])):
        mask = source[ca] == src
        yy = y[ca][mask]
        auc = roc_auc_score(yy, s[mask]) if 0 < yy.sum() < len(yy) else float("nan")
        print(f"  {src:14s} n={mask.sum():4d} COMPLEX {yy.mean():5.1%} AUROC wewnątrz źródła {auc:.3f}")
    print("\nwagi cech L1 (po standaryzacji, LR):")
    names = ["log tokeny", "log znaki", "log nowe linie", "``` bloki", "udział cyfr", "znaki ?", "kod-podobne", "URL", "słowa COMPLEX", "słowa SIMPLE"]
    for n, w in sorted(zip(names, m1.coef_[0], strict=True), key=lambda x: -abs(x[1])):
        print(f"  {n:16s} {w:+.3f}")


if __name__ == "__main__":
    main()
