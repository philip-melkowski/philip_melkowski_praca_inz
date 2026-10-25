# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

K = 20
BOOT = 1000


def ci(a: np.ndarray) -> str:
    return f"{a.mean():.3f} [{np.percentile(a, 2.5):.3f},{np.percentile(a, 97.5):.3f}]"


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    with Path(args.input).open(encoding="utf-8") as f:
        l3 = {r["id"]: r for r in (json.loads(line) for line in f if line.strip())}
    ids = [i for i in l3 if i in labels and labels[i]["split"] in args.splits]
    names = list(l3[ids[0]]["answers"])
    y = np.array([labels[i]["delta"] > 0.25 for i in ids])
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    group = np.array([questions[row[i]]["group"] for i in ids])
    P = np.clip(np.array([[l3[i]["answers"][n] for n in names] for i in ids]), 1e-4, 1 - 1e-4)
    F = np.log(P / (1 - P))
    X = emb[[row[i] for i in ids]]
    sec = np.array([l3[i]["seconds"] for i in ids])
    print(f"{args.splits}: {len(ids)} pytań z odpowiedziami modelu decyzyjnego; COMPLEX {y.mean():.1%}; czas żądania p50 {np.median(sec):.2f} s, p90 {np.percentile(sec, 90):.2f} s")
    print("walidacja krzyżowa po grupach (5 części); zbiór test nie jest używany\n")

    folds = list(GroupKFold(n_splits=5).split(F, y, group))
    lr = np.zeros(len(ids))
    knn = np.zeros(len(ids))
    coefs = []
    for tr, te in folds:
        m = LogisticRegression(C=1.0, max_iter=3000).fit(F[tr], y[tr])
        lr[te] = m.decision_function(F[te])
        coefs.append(m.coef_[0])
        knn[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)

    rng = np.random.default_rng(SEED)
    boots = [b for b in (rng.integers(0, len(ids), len(ids)) for _ in range(BOOT)) if 0 < y[b].sum() < len(ids)]
    print(f"{'pytanie do modelu':22s} {'AUROC [95% CI]':24s} {'średnie P: SIMPLE / COMPLEX':28s}")
    for j, n in enumerate(names):
        a = np.array([roc_auc_score(y[b], P[b, j]) for b in boots])
        print(f"{n:22s} {ci(a):24s} {P[~y, j].mean():.3f} / {P[y, j].mean():.3f}")
    print("(AUROC < 0,5: wyższe P oznacza łatwiejsze pytanie; siła sygnału to odległość od 0,5)\n")

    res = {
        n: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in boots])
        for n, s in (("nimble: wszystkie pytania (LR, CV)", lr), ("odniesienie: kNN k=20 (CV)", knn))
    }
    print(f"{'metoda':36s} {'AUROC [95% CI]':24s} {'APGR [95% CI]':24s}")
    for n, a in res.items():
        print(f"{n:36s} {ci(a[:, 0]):24s} {ci(a[:, 1]):24s}")
    print("\nwspółczynniki LR (średnia z 5 części, cechy w logitach):")
    for n, c in zip(names, np.mean(coefs, axis=0), strict=True):
        print(f"  {n:22s} {c:+.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Warstwa 3, krok 1: sam model decyzyjny (bez kNN) na train.")
    p.add_argument("input", help="plik z eval/layer3_systemone.py")
    p.add_argument("--splits", nargs="+", default=["train"])
    main(p.parse_args())
