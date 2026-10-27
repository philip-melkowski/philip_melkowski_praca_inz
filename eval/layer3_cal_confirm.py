# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from layer3_select import V1  # noqa: E402
from layer3_systemone_vs_knn import BOOT, K, ZONE, ci, logit  # noqa: E402
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402


def load(path: str) -> dict[str, dict[str, float]]:
    with Path(path).open(encoding="utf-8") as f:
        return {r["id"]: r["answers"] for r in (json.loads(line) for line in f if line.strip())}


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    l3_tr, l3_cal = load(args.train), load(args.cal)
    tr = sorted(i for i in l3_tr if i in labels and labels[i]["split"] == "train")
    te = sorted(i for i in l3_cal if i in labels and labels[i]["split"] == "cal")
    names = list(l3_tr[tr[0]])
    v1 = [j for j, nm in enumerate(names) if nm in V1]
    print(f"uczenie na train ({len(tr)}), pomiar na cal ({len(te)}), {len(names)} pytań modelu decyzyjnego; test nie jest używany")

    def arrays(ids: list[str], l3: dict[str, dict[str, float]]) -> tuple[np.ndarray, ...]:
        y = np.array([labels[i]["delta"] > 0.25 for i in ids])
        F = logit(np.array([[l3[i][n] for n in names] for i in ids]))
        return y, F, emb[[row[i] for i in ids]], np.array([labels[i]["q_large"] for i in ids]), np.array([labels[i]["q_small"] for i in ids])

    y_tr, F_tr, X_tr, _, _ = arrays(tr, l3_tr)
    y, F, X, ql, qs = arrays(te, l3_cal)
    g_tr = np.array([questions[row[i]]["group"] for i in tr])
    k_tr = np.zeros(len(tr))
    for a, b in GroupKFold(n_splits=5).split(X_tr, groups=g_tr):
        k_tr[b] = knn_score(X_tr[b] @ X_tr[a].T, y_tr[a].astype(float), K)
    knn = knn_score(X @ X_tr.T, y_tr.astype(float), K)
    A_tr, A = np.column_stack([logit(k_tr), F_tr]), np.column_stack([logit(knn), F])
    v1c = [0] + [j + 1 for j in v1]

    scores = {
        "kNN": knn,
        f"kNN + v1 ({len(v1)}) LR": LogisticRegression(C=1.0, max_iter=5000).fit(A_tr[:, v1c], y_tr).predict_proba(A[:, v1c])[:, 1],
        f"kNN + wszystkie ({len(names)}) LR C=0,1": LogisticRegression(C=0.1, max_iter=5000).fit(A_tr, y_tr).predict_proba(A)[:, 1],
        f"GBM: kNN + wszystkie ({len(names)})": HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=SEED).fit(A_tr, y_tr).predict_proba(A)[:, 1],
    }
    zone = (knn >= ZONE[0]) & (knn <= ZONE[1])
    for m in list(scores)[1:]:
        scores[f"router ze strefą: {m}"] = np.where(zone, scores[m], knn)
    print(f"COMPLEX {y.mean():.1%}; w strefie {zone.sum()} pytań ({zone.mean():.0%})\n")

    rng = np.random.default_rng(SEED)
    ref = f"kNN + v1 ({len(v1)}) LR"
    for mask, title, keys in ((zone, "STREFA", list(scores)[:4]), (np.ones(len(te), dtype=bool), "CAŁY CAL", list(scores))):
        idx = np.flatnonzero(mask)
        bs = [b for b in (idx[rng.integers(0, len(idx), len(idx))] for _ in range(BOOT)) if 0 < y[b].sum() < len(b)]
        res = {k: np.array([(roc_auc_score(y[b], scores[k][b]), pgr_curve(scores[k][b], ql[b], qs[b], rng).mean()) for b in bs]) for k in keys}
        print(f"=== {title}: {mask.sum()} pytań, COMPLEX {y[mask].mean():.1%} ===")
        print(f"{'metoda':52s} {'AUROC [95% CI]':24s} {'APGR [95% CI]':24s}")
        for k, a in res.items():
            print(f"{k:52s} {ci(a[:, 0]):24s} {ci(a[:, 1]):24s}")
        for k in keys[1:]:
            d = res[k] - res["kNN"]
            print(f"  {k} − kNN: AUROC {ci(d[:, 0], True)}, APGR {ci(d[:, 1], True)}")
        for k in keys[1:]:
            base = f"router ze strefą: {ref}" if k.startswith("router") else ref
            if k != base:
                d = res[k] - res[base]
                print(f"  {k} − {base}: AUROC {ci(d[:, 0], True)}, APGR {ci(d[:, 1], True)}")
        print()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Warstwa 3: jednorazowe potwierdzenie na cal (uczenie na całym train) dla v1, wszystkich pytań puli (LR) i GBM.")
    p.add_argument("--train", required=True, help="wyniki modelu decyzyjnego na train")
    p.add_argument("--cal", required=True, help="wyniki tego samego modelu i zestawu na cal")
    main(p.parse_args())
