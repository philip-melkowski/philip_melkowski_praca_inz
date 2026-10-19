# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

BOOT = 1000


def main(path: str) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    probe = {}
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("p_complex") is not None and r["id"] in labels:
                probe[r["id"]] = r
    train = [i for i in labels if labels[i]["split"] == "train"]
    Xt = emb[[row[i] for i in train]]
    yt = np.array([labels[i]["delta"] > 0.25 for i in train], dtype=float)
    ids = [i for i in probe if labels[i]["split"] == "cal"]
    X = emb[[row[i] for i in ids]]
    y = np.array([labels[i]["delta"] > 0.25 for i in ids])
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    group = np.array([questions[row[i]]["group"] for i in ids])
    l3 = np.array([probe[i]["p_complex"] for i in ids])
    l2 = knn_score(X @ Xt.T, yt, 20)
    sec = np.array([probe[i].get("seconds", np.nan) for i in ids])
    print(f"cal: {len(ids)} pytań z wynikiem warstwy 3; COMPLEX {y.mean():.1%}; czas wywołania warstwy 3: p50 {np.nanmedian(sec) * 1000:.0f} ms, p90 {np.nanpercentile(sec, 90) * 1000:.0f} ms")

    logit = lambda p: np.log((np.clip(p, 0.01, 0.99)) / (1 - np.clip(p, 0.01, 0.99)))  # noqa: E731
    stack = np.zeros(len(ids))
    feats = np.column_stack([logit(l2), logit(l3)])
    for a, b in GroupKFold(n_splits=5).split(feats, y, group):
        stack[b] = LogisticRegression(max_iter=1000).fit(feats[a], y[a]).decision_function(feats[b])
    iso = np.zeros(len(ids))
    for a, b in GroupKFold(n_splits=5).split(feats, y, group):
        iso[b] = IsotonicRegression(out_of_bounds="clip").fit(l3[a], y[a]).predict(l3[b])

    rng = np.random.default_rng(SEED)
    boots = [b for b in (rng.integers(0, len(ids), len(ids)) for _ in range(BOOT)) if 0 < y[b].sum() < len(ids)]
    methods = {"L2 kNN": l2, "L3 (surowa pewność)": l3, "L3 po kalibracji izotonicznej (CV)": iso, "L2+L3 (regresja logistyczna, CV)": stack}
    res = {n: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots]) for n, s in methods.items()}
    print(f"\n{'metoda (cal)':38s} {'AUROC [95% CI]':24s} {'APGR [95% CI]':24s}")
    for n, a in res.items():
        print(f"{n:38s} {a[:, 0].mean():.3f} [{np.percentile(a[:, 0], 2.5):.3f},{np.percentile(a[:, 0], 97.5):.3f}]  {a[:, 1].mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f},{np.percentile(a[:, 1], 97.5):.3f}]")
    d = res["L2+L3 (regresja logistyczna, CV)"] - res["L2 kNN"]
    print(f"\nzysk L2+L3 względem samego L2: AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f},{np.percentile(d[:, 0], 97.5):+.3f}], APGR {d[:, 1].mean():+.3f} [{np.percentile(d[:, 1], 2.5):+.3f},{np.percentile(d[:, 1], 97.5):+.3f}]")
    print("kryterium go/no-go (propozycja): GO tylko gdy dolna granica 95% CI zysku AUROC > 0 oraz dodatkowe opóźnienie p50 jest akceptowalne; w przeciwnym razie NO-GO.")


if __name__ == "__main__":
    main(sys.argv[1])
