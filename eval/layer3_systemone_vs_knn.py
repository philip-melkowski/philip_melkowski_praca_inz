# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

K = 20
BOOT = 1000
ZONE = (0.20, 0.45)


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def ci(a: np.ndarray, signed: bool = False) -> str:
    f = "+.3f" if signed else ".3f"
    return f"{a.mean():{f}} [{np.percentile(a, 2.5):{f}},{np.percentile(a, 97.5):{f}}]"


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
    source = np.array([labels[i]["source"] for i in ids])
    N = logit(np.array([[l3[i]["answers"][n] for n in names] for i in ids]))
    X = emb[[row[i] for i in ids]]
    n = len(ids)
    print(f"{args.splits}: {n} pytań; COMPLEX {y.mean():.1%}; walidacja krzyżowa po grupach (5 części), kNN dla części uczącej liczony wewnętrzną CV (bez przecieku); test nie jest używany\n")

    def knn_oof(idx: np.ndarray) -> np.ndarray:
        out = np.zeros(len(idx))
        for a, b in GroupKFold(n_splits=5).split(idx, groups=group[idx]):
            out[b] = knn_score(X[idx[b]] @ X[idx[a]].T, y[idx[a]].astype(float), K)
        return out

    def src_prior(tr: np.ndarray, te: np.ndarray) -> np.ndarray:
        prior = {s: y[tr][source[tr] == s].mean() for s in set(source[tr])}
        return np.array([prior.get(s, y[tr].mean()) for s in source[te]])

    sme = names.index("small_model_enough") if "small_model_enough" in names else 0
    scores = {k: np.zeros(n) for k in ("kNN", "nimble (8)", "samo źródło", "źródło + nimble", "kNN + small_model_enough", "kNN + nimble (8)", "kNN + źródło", "kNN + źródło + nimble")}
    knn_all = np.zeros(n)
    for tr, te in GroupKFold(n_splits=5).split(X, y, group):
        k_tr = logit(knn_oof(tr))
        k_te = logit(knn_score(X[te] @ X[tr].T, y[tr].astype(float), K))
        knn_all[te] = 1 / (1 + np.exp(-k_te))
        s_tr = logit(src_prior(tr, tr))
        s_te = logit(src_prior(tr, te))
        feats = {
            "kNN": (k_tr[:, None], k_te[:, None]),
            "nimble (8)": (N[tr], N[te]),
            "samo źródło": (s_tr[:, None], s_te[:, None]),
            "źródło + nimble": (np.column_stack([s_tr, N[tr]]), np.column_stack([s_te, N[te]])),
            "kNN + small_model_enough": (np.column_stack([k_tr, N[tr, sme]]), np.column_stack([k_te, N[te, sme]])),
            "kNN + nimble (8)": (np.column_stack([k_tr, N[tr]]), np.column_stack([k_te, N[te]])),
            "kNN + źródło": (np.column_stack([k_tr, s_tr]), np.column_stack([k_te, s_te])),
            "kNN + źródło + nimble": (np.column_stack([k_tr, s_tr, N[tr]]), np.column_stack([k_te, s_te, N[te]])),
        }
        for k, (a, b) in feats.items():
            scores[k][te] = LogisticRegression(C=1.0, max_iter=3000).fit(a, y[tr]).decision_function(b)

    print("korelacja Spearmana z wynikiem kNN (poza próbką):")
    for j, nm in enumerate(names):
        print(f"  {nm:22s} {spearmanr(knn_all, N[:, j]).statistic:+.3f}")
    print(f"  {'nimble (8), LR':22s} {spearmanr(knn_all, scores['nimble (8)']).statistic:+.3f}\n")

    rng = np.random.default_rng(SEED)

    def report(mask: np.ndarray, title: str) -> None:
        idx = np.flatnonzero(mask)
        bs = [b for b in (idx[rng.integers(0, len(idx), len(idx))] for _ in range(BOOT)) if 0 < y[b].sum() < len(b)]
        res = {k: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in bs]) for k, s in scores.items()}
        print(f"=== {title}: {mask.sum()} pytań ({mask.mean():.0%}), COMPLEX {y[mask].mean():.1%} ===")
        print(f"{'metoda':26s} {'AUROC [95% CI]':24s} {'APGR [95% CI]':24s}")
        for k, a in res.items():
            print(f"{k:26s} {ci(a[:, 0]):24s} {ci(a[:, 1]):24s}")
        for a_, b_ in (("kNN + nimble (8)", "kNN"), ("kNN + small_model_enough", "kNN"), ("źródło + nimble", "samo źródło"), ("kNN + źródło + nimble", "kNN + źródło")):
            d = res[a_] - res[b_]
            print(f"  zysk {a_} − {b_}: AUROC {ci(d[:, 0], True)}, APGR {ci(d[:, 1], True)}")
        print()

    report(np.ones(n, dtype=bool), "wszystkie pytania")
    report((knn_all >= ZONE[0]) & (knn_all <= ZONE[1]), f"strefa niepewności kNN {ZONE[0]}–{ZONE[1]} (wpis 67)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Warstwa 3 na train: czy model decyzyjny mówi coś ponad kNN i ponad samo źródło pytania.")
    p.add_argument("input", help="plik z eval/layer3_systemone.py")
    p.add_argument("--splits", nargs="+", default=["train"])
    main(p.parse_args())
