# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""Czy kNN przenosi się na nowe źródła (Dolly, CodeChat, Arena 140k) i czy nowe dane pomagają (wpis 118).

Tylko stary train i nowe `extra_train`; `extra_val`, cal i test nieużywane.
1. kNN z indeksem ze starego train oceniony na `extra_train` (bez strojenia).
2. CV po grupach na starym train + `extra_train`: AUROC i APGR na każdej części.
"""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, group_bootstrap, knn_score, pgr_curve, read  # noqa: E402

K = 20
THR = 0.25
BOOT = 1000


def block(name: str, y: np.ndarray, s: np.ndarray, ql: np.ndarray, qs: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> None:
    vals = []
    for _ in range(BOOT):
        b = group_bootstrap(groups, rng)
        if 0 < y[b].sum() < len(b):
            vals.append((roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()))
    a = np.array(vals)
    lo, hi = np.percentile(a, 2.5, axis=0), np.percentile(a, 97.5, axis=0)
    print(
        f"  {name:34s} n={len(y):5d} COMPLEX {y.mean():5.1%}  AUROC {roc_auc_score(y, s):.3f} [{lo[0]:.3f}; {hi[0]:.3f}]"
        f"  APGR {pgr_curve(s, ql, qs, rng).mean():.3f} [{lo[1]:.3f}; {hi[1]:.3f}]"
    )


def main() -> None:
    rng = np.random.default_rng(SEED)
    old_q = read("questions_v2_split.jsonl")
    old_lab = {r["id"]: r for r in read("labels.jsonl")}
    old_emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    new_q = read("questions_extra_split.jsonl")
    new_lab = {r["id"]: r for r in read("labels_extra.jsonl")}
    new_emb = np.load(DATASETS_DIR / "embeddings_extra_nomic.npy")

    def take(qs: list[dict], lab: dict, emb: np.ndarray, split: str) -> dict[str, np.ndarray]:
        idx = [i for i, q in enumerate(qs) if q["split"] == split and q["id"] in lab]
        rows = [lab[qs[i]["id"]] for i in idx]
        return {
            "X": emb[idx],
            "y": np.array([r["delta"] > THR for r in rows]),
            "ql": np.array([r["q_large"] for r in rows]),
            "qs": np.array([r["q_small"] for r in rows]),
            "g": np.array([str(qs[i]["group"]) for i in idx]),
            "src": np.array([qs[i]["source"] for i in idx]),
        }

    tr = take(old_q, old_lab, old_emb, "train")
    ex = take(new_q, new_lab, new_emb, "extra_train")
    print(f"stary train {len(tr['y'])}, extra_train {len(ex['y'])}; extra_val, cal i test nieużywane\n")

    print("1. kNN uczony na starym train, oceniany na nowych pytaniach (extra_train):")
    s = knn_score(ex["X"] @ tr["X"].T, tr["y"].astype(float), K)
    block("wszystkie nowe", ex["y"], s, ex["ql"], ex["qs"], ex["g"], rng)
    for src in sorted(set(ex["src"])):
        m = ex["src"] == src
        block(f"  {src}", ex["y"][m], s[m], ex["ql"][m], ex["qs"][m], ex["g"][m], rng)

    print("\n2. CV po grupach (5 części) na starym train + extra_train, wyniki osobno dla każdej części:")
    X = np.vstack([tr["X"], ex["X"]])
    y = np.concatenate([tr["y"], ex["y"]])
    g = np.concatenate([tr["g"], ex["g"]])
    ql, qs = np.concatenate([tr["ql"], ex["ql"]]), np.concatenate([tr["qs"], ex["qs"]])
    is_new = np.arange(len(y)) >= len(tr["y"])
    oof = np.zeros(len(y))
    for a, b in GroupKFold(n_splits=5).split(X, groups=g):
        oof[b] = knn_score(X[b] @ X[a].T, y[a].astype(float), K)
    block("stary train (indeks z obu)", y[~is_new], oof[~is_new], ql[~is_new], qs[~is_new], g[~is_new], rng)
    block("extra_train (indeks z obu)", y[is_new], oof[is_new], ql[is_new], qs[is_new], g[is_new], rng)
    oof_old = np.zeros(len(tr["y"]))
    for a, b in GroupKFold(n_splits=5).split(tr["X"], groups=tr["g"]):
        oof_old[b] = knn_score(tr["X"][b] @ tr["X"][a].T, tr["y"][a].astype(float), K)
    block("stary train (indeks tylko ze starego)", tr["y"], oof_old, tr["ql"], tr["qs"], tr["g"], rng)


if __name__ == "__main__":
    main()
