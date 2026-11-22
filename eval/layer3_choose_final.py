# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""Wybór zestawu dla warstwy 3 z d1 (reguła z wpisu 125, zapisana przed wynikiem) i jedno sprawdzenie na `extra_val`.

A = kNN + d1 v1 + regresja logistyczna, B = kNN + d1 pula v2 + GBM; router ze strefą [0,20; 0,45) wyniku kNN.
CV po grupach na stary train + `extra_train`; cal i test nieużywane do oceny (cal tylko w indeksie przy sprawdzeniu)."""

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, group_bootstrap, knn_score, pgr_curve, read  # noqa: E402

ROOT = Path(__file__).parent.parent
K = 20
THR = 0.25
ZONE = (0.20, 0.45)
BOOT = 1000


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def load_l3(name: str) -> dict[str, dict[str, float]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return {r["id"]: r["answers"] for r in map(json.loads, f) if "answers" in r}


def gbm() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=SEED)


def collect(splits_old: tuple[str, ...], splits_new: tuple[str, ...]) -> dict[str, Any]:
    oq, oe = read("questions_v2_split.jsonl"), np.load(DATASETS_DIR / "embeddings_nomic.npy")
    with (ROOT / "data" / "labels" / "labels_v3.jsonl").open(encoding="utf-8") as f:
        ol = {r["id"]: r for r in map(json.loads, f)}
    nq, nl, ne = read("questions_extra_split.jsonl"), {r["id"]: r for r in read("labels_extra.jsonl")}, np.load(DATASETS_DIR / "embeddings_extra_nomic.npy")
    v1 = load_l3("layer3_systemone_d1gpu_v1.jsonl") | load_l3("layer3_systemone_d1gpu_v1_extra.jsonl")
    pool = load_l3("layer3_systemone_d1gpu_pool_v2.jsonl") | load_l3("layer3_systemone_d1gpu_pool_v2_extra.jsonl")
    rows: list[tuple[dict[str, Any], dict[str, Any], np.ndarray]] = []
    rows += [(q, ol[q["id"]], oe[i]) for i, q in enumerate(oq) if q["split"] in splits_old and q["id"] in ol]
    rows += [(q, nl[q["id"]], ne[i]) for i, q in enumerate(nq) if q["split"] in splits_new and q["id"] in nl]
    have_l3 = [r for r in rows if r[0]["id"] in v1 and r[0]["id"] in pool]
    names_v1, names_pool = list(next(iter(v1.values()))), list(next(iter(pool.values())))
    return {
        "ids": [r[0]["id"] for r in rows],
        "X": np.array([r[2] for r in rows]),
        "y": np.array([r[1]["delta"] > THR for r in rows]),
        "ql": np.array([r[1]["q_large"] for r in rows]),
        "qs": np.array([r[1]["q_small"] for r in rows]),
        "g": np.array([str(r[0]["group"]) for r in rows]),
        "V1": logit(np.array([[v1[r[0]["id"]][n] for n in names_v1] if r[0]["id"] in v1 else [0.5] * len(names_v1) for r in rows])),
        "POOL": logit(np.array([[pool[r[0]["id"]][n] for n in names_pool] if r[0]["id"] in pool else [0.5] * len(names_pool) for r in rows])),
        "has_l3": np.array([r[0]["id"] in v1 and r[0]["id"] in pool for r in rows]),
        "n_l3": len(have_l3),
    }


def inner_knn(X: np.ndarray, y: np.ndarray, g: np.ndarray) -> np.ndarray:
    out = np.zeros(len(y))
    for a, b in GroupKFold(n_splits=5).split(X, groups=g):
        out[b] = knn_score(X[b] @ X[a].T, y[a].astype(float), K)
    return out


def fit_predict(kind: str, d_tr: dict[str, np.ndarray], knn_tr: np.ndarray, d_te: dict[str, np.ndarray], knn_te: np.ndarray) -> np.ndarray:
    if kind == "A":
        m = LogisticRegression(C=1.0, max_iter=3000).fit(np.column_stack([logit(knn_tr), d_tr["V1"]]), d_tr["y"])
        return m.predict_proba(np.column_stack([logit(knn_te), d_te["V1"]]))[:, 1]
    m = gbm().fit(np.column_stack([logit(knn_tr), d_tr["POOL"]]), d_tr["y"])
    return m.predict_proba(np.column_stack([logit(knn_te), d_te["POOL"]]))[:, 1]


def router(knn: np.ndarray, p: np.ndarray) -> np.ndarray:
    zone = (knn >= ZONE[0]) & (knn < ZONE[1])
    return np.where(zone, p, knn)


def take(d: dict[str, Any], idx: np.ndarray) -> dict[str, np.ndarray]:
    return {k: d[k][idx] for k in ("X", "y", "ql", "qs", "g", "V1", "POOL")}


def report(title: str, d: dict[str, Any], scores: dict[str, np.ndarray], pairs: list[tuple[str, str]], rng: np.random.Generator) -> dict[str, np.ndarray]:
    y, ql, qs = d["y"], d["ql"], d["qs"]
    boots = [group_bootstrap(d["g"], rng) for _ in range(BOOT)]
    res = {n: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots]) for n, s in scores.items()}
    print(f"=== {title}: {len(y)} pytań, COMPLEX {y.mean():.1%}, w strefie {((scores['kNN'] >= ZONE[0]) & (scores['kNN'] < ZONE[1])).mean():.0%} ===")
    for n, s in scores.items():
        a = res[n]
        print(f"  {n:24s} AUROC {roc_auc_score(y, s):.3f} [{np.percentile(a[:, 0], 2.5):.3f}; {np.percentile(a[:, 0], 97.5):.3f}]  APGR {pgr_curve(s, ql, qs, rng).mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f}; {np.percentile(a[:, 1], 97.5):.3f}]")
    for x, z in pairs:
        diff = res[x] - res[z]
        print(f"  różnica {x} − {z}: AUROC {diff[:, 0].mean():+.3f} [{np.percentile(diff[:, 0], 2.5):+.3f}; {np.percentile(diff[:, 0], 97.5):+.3f}]  APGR {diff[:, 1].mean():+.3f} [{np.percentile(diff[:, 1], 2.5):+.3f}; {np.percentile(diff[:, 1], 97.5):+.3f}]")
    return res


def main() -> None:
    rng = np.random.default_rng(SEED)
    d = collect(("train",), ("extra_train",))
    assert d["has_l3"].all(), f"brak odpowiedzi d1 dla {(~d['has_l3']).sum()} pytań"
    print(f"train + extra_train: {len(d['y'])} pytań (d1 dla wszystkich); test, cal, extra_val nieużywane\n")
    knn = np.zeros(len(d["y"]))
    pa, pb = np.zeros(len(d["y"])), np.zeros(len(d["y"]))
    for tr, te in GroupKFold(n_splits=5).split(d["X"], groups=d["g"]):
        dtr, dte = take(d, tr), take(d, te)
        knn[te] = knn_score(dte["X"] @ dtr["X"].T, dtr["y"].astype(float), K)
        knn_tr = inner_knn(dtr["X"], dtr["y"], dtr["g"])
        pa[te] = fit_predict("A", dtr, knn_tr, dte, knn[te])
        pb[te] = fit_predict("B", dtr, knn_tr, dte, knn[te])
    res = report("CV", d, {"kNN": knn, "A (v1 + LR)": router(knn, pa), "B (pula + GBM)": router(knn, pb)}, [("A (v1 + LR)", "kNN"), ("B (pula + GBM)", "kNN"), ("B (pula + GBM)", "A (v1 + LR)")], rng)
    diff = res["B (pula + GBM)"][:, 1] - res["A (v1 + LR)"][:, 1]
    chosen = "B" if np.percentile(diff, 2.5) > 0 else "A"
    print(f"\nREGUŁA (wpis 125): dolna granica APGR B − A = {np.percentile(diff, 2.5):+.3f} → wybrany wariant {chosen}\n")

    full = d
    idx_index = collect(("train", "cal"), ("extra_train",))
    val = collect((), ("extra_val",))
    assert val["has_l3"].all()
    knn_full = inner_knn(full["X"], full["y"], full["g"])
    knn_val = knn_score(val["X"] @ idx_index["X"].T, idx_index["y"].astype(float), K)
    p_val = fit_predict(chosen, take(full, np.arange(len(full["y"]))), knn_full, take(val, np.arange(len(val["y"]))), knn_val)
    report("SPRAWDZENIE NA extra_val (raz)", val, {"kNN": knn_val, f"router z warstwą 3 ({chosen})": router(knn_val, p_val)}, [(f"router z warstwą 3 ({chosen})", "kNN")], rng)


if __name__ == "__main__":
    main()
