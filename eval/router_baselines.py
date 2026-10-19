# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"
SEED = 42
GRID = np.linspace(0, 1, 101)
KS = (5, 10, 20, 40, 80)
CS = (0.1, 1.0, 10.0)
BOOT = 1000
RANDOM_DRAWS = 200


def read(name: str) -> list[dict[str, Any]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def pgr_curve(score: np.ndarray, q_large: np.ndarray, q_small: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n = len(score)
    order = np.lexsort((rng.random(n), -score))
    gain = (q_large - q_small)[order]
    cum = np.concatenate([[0.0], np.cumsum(gain)])
    total = cum[-1]
    ks = np.round(GRID * n).astype(int)
    return cum[ks] / total if total > 0 else np.zeros_like(GRID)


def cpt(curve: np.ndarray, target: float) -> float:
    hit = np.where(curve >= target)[0]
    return float(GRID[hit[0]]) if len(hit) else float("nan")


def knn_score(sim: np.ndarray, target: np.ndarray, k: int) -> np.ndarray:
    idx = np.argpartition(-sim, k - 1, axis=1)[:, :k]
    w = np.take_along_axis(sim, idx, axis=1).clip(min=1e-6)
    return (w * target[idx]).sum(1) / w.sum(1)


def metrics(name: str, score: np.ndarray, d: dict[str, np.ndarray], rng: np.random.Generator, boot: int = BOOT) -> dict[str, Any]:
    ql, qs, y = d["ql"], d["qs"], d["y"]
    curve = pgr_curve(score, ql, qs, rng)
    auc = roc_auc_score(y, score) if len(set(score)) > 1 else 0.5
    boot_apgr, boot_auc = [], []
    n = len(y)
    for _ in range(boot):
        b = rng.integers(0, n, n)
        if len(set(y[b])) < 2:
            continue
        boot_apgr.append(pgr_curve(score[b], ql[b], qs[b], rng).mean())
        boot_auc.append(roc_auc_score(y[b], score[b]) if len(set(score[b])) > 1 else 0.5)
    return {
        "name": name,
        "auc": auc,
        "auc_ci": np.percentile(boot_auc, [2.5, 97.5]) if boot_auc else np.full(2, np.nan),
        "apgr": curve.mean(),
        "apgr_ci": np.percentile(boot_apgr, [2.5, 97.5]) if boot_apgr else np.full(2, np.nan),
        "cpt50": cpt(curve, 0.5),
        "cpt80": cpt(curve, 0.8),
    }


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels]
    X = emb[[row[i] for i in ids]]
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    split = np.array([m["split"] for m in meta])
    y = np.array([m["label"] == "COMPLEX" for m in meta])
    delta = np.array([m["delta"] for m in meta])
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    tokens = np.array([questions[row[i]]["tokens"] for i in ids], dtype=float)
    source = np.array([m["source"] for m in meta])
    both = np.array([m["both_failed"] for m in meta])
    tr, ca = split == "train", split == "cal"
    print(f"train {tr.sum()}, cal {ca.sum()}; test ({(split == 'test').sum()}) nie jest używany\n")

    rng = np.random.default_rng(SEED)
    d_cal = {"ql": ql[ca], "qs": qs[ca], "y": y[ca]}
    results = []

    draws = [metrics("losowy", rng.random(ca.sum()), d_cal, rng, boot=0) for _ in range(RANDOM_DRAWS)]
    results.append(
        {
            "name": f"losowy (średnia z {RANDOM_DRAWS} losowań)",
            **{k: float(np.mean([r[k] for r in draws])) for k in ("auc", "apgr", "cpt50", "cpt80")},
            "auc_ci": np.percentile([r["auc"] for r in draws], [2.5, 97.5]),
            "apgr_ci": np.percentile([r["apgr"] for r in draws], [2.5, 97.5]),
        }
    )
    results.append(metrics("oracle (prawdziwe Δ)", delta[ca], d_cal, rng))
    results.append(metrics("sama długość (tokeny)", np.log(tokens[ca]), d_cal, rng))
    prior = {s: y[tr & (source == s)].mean() for s in set(source) if (tr & (source == s)).any()}
    results.append(metrics("samo źródło", np.array([prior.get(s, y[tr].mean()) for s in source[ca]]), d_cal, rng))

    Xt, yt, gt = X[tr], y[tr], group[tr]
    dt = delta[tr]
    cv = list(GroupKFold(n_splits=5).split(Xt, yt, gt))

    def cv_auc(fn: Any) -> float:
        aucs = []
        for a, b in cv:
            aucs.append(roc_auc_score(yt[b], fn(a, b)))
        return float(np.mean(aucs))

    best_c = max(CS, key=lambda c: cv_auc(lambda a, b, c=c: LogisticRegression(C=c, max_iter=2000).fit(Xt[a], yt[a]).decision_function(Xt[b])))
    lr = LogisticRegression(C=best_c, max_iter=2000).fit(Xt, yt)
    results.append(metrics(f"regresja logistyczna (C={best_c})", lr.decision_function(X[ca]), d_cal, rng))

    lr2 = LogisticRegression(C=best_c, max_iter=2000).fit(Xt[~both[tr]], yt[~both[tr]])
    results.append(metrics("regresja log. bez 'oba zawiodły' w uczeniu", lr2.decision_function(X[ca]), d_cal, rng))

    for mode, target in (("etykieta 0/1", yt.astype(float)), ("ciągłe Δ", dt)):
        scores = {k: cv_auc(lambda a, b, k=k, t=target: knn_score(Xt[b] @ Xt[a].T, t[a], k)) for k in KS}
        k = max(scores, key=lambda x: scores[x])
        print(f"kNN ({mode}): AUROC w walidacji krzyżowej po grupach: " + ", ".join(f"k={kk}: {v:.3f}" for kk, v in scores.items()) + f" → k={k}")
        results.append(metrics(f"kNN k={k} ({mode})", knn_score(X[ca] @ Xt.T, target, k), d_cal, rng))

    print(f"\n{'metoda (zbiór cal)':44s} {'AUROC':>6s} {'95% CI':>13s} {'APGR':>6s} {'95% CI':>13s} {'CPT50':>6s} {'CPT80':>6s}")
    for r in results:
        print(
            f"{r['name']:44s} {r['auc']:6.3f} [{r['auc_ci'][0]:.3f},{r['auc_ci'][1]:.3f}] {r['apgr']:6.3f} "
            f"[{r['apgr_ci'][0]:.3f},{r['apgr_ci'][1]:.3f}] {r['cpt50']:6.2f} {r['cpt80']:6.2f}"
        )


if __name__ == "__main__":
    main()
