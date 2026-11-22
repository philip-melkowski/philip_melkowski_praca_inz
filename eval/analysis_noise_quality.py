# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
"""Analizy na gotowych danych (PRZEMYSLENIA_2026-10-25.md, pkt 5.1 i 5.2), tylko train, kNN z CV po grupach.

1. Szum etykiet: AUROC kNN na pytaniach z wyraźnym Δ i korelacja wyniku z ciągłym Δ.
2. Spadek jakości jak w Hybrid LLM: jakość przy 20/40/50% ruchu do małego wobec „zawsze duży”.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, group_bootstrap, knn_score, read  # noqa: E402

K = 20
THR = 0.25
BOOT = 1000
SHARES_SMALL = (0.2, 0.4, 0.5, 0.6)


def quality_at(score: np.ndarray, ql: np.ndarray, qs: np.ndarray, share_small: float, rng: np.random.Generator) -> float:
    """Średnia jakość, gdy `share_small` pytań z najniższym wynikiem idzie do małego (remisy losowo)."""
    n = len(score)
    order = np.lexsort((rng.random(n), score))
    small = np.zeros(n, dtype=bool)
    small[order[: round(share_small * n)]] = True
    return float(np.where(small, qs, ql).mean())


def ci(a: np.ndarray, fmt: str = ".3f") -> str:
    return f"{a.mean():{fmt}} [{np.percentile(a, 2.5):{fmt}}; {np.percentile(a, 97.5):{fmt}}]"


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in args.splits]
    X = emb[[row[i] for i in ids]]
    group = np.array([questions[row[i]]["group"] for i in ids])
    source = np.array([labels[i]["source"] for i in ids])
    delta = np.array([labels[i]["delta"] for i in ids])
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    y = delta > THR
    knn = np.zeros(len(ids))
    prior = np.zeros(len(ids))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        knn[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)
        rates = {s: y[tr][source[tr] == s].mean() for s in set(source[tr])}
        prior[te] = [rates.get(s, y[tr].mean()) for s in source[te]]
    rng = np.random.default_rng(SEED)
    boots = [group_bootstrap(group, rng) for _ in range(BOOT)]
    print(f"{'+'.join(args.splits)}: {len(ids)} pytań, kNN k={K} z CV po grupach; test i cal nieużywane, chyba że podano --splits cal\n")

    print("=== 1. Szum etykiet: czy router lepiej rozpoznaje pytania z wyraźną różnicą jakości? ===")
    print("AUROC kNN dla par: COMPLEX z Δ > a  wobec  SIMPLE z Δ ≤ b (95% przedział, bootstrap po grupach)")
    for a, b in ((THR, THR), (0.4, 0.0), (0.5, 0.0), (0.5, -0.1)):
        mask = (delta > a) | (delta <= b)
        yy, ss = delta[mask] > a, knn[mask]
        vals = []
        for bt in boots:
            m = mask[bt]
            yb, sb = (delta[bt] > a)[m], knn[bt][m]
            if 0 < yb.sum() < len(yb):
                vals.append(roc_auc_score(yb, sb))
        print(f"  Δ > {a:+.2f} vs Δ ≤ {b:+.2f}: {mask.sum():4d} pytań ({yy.mean():.0%} COMPLEX), AUROC {roc_auc_score(yy, ss):.3f}, {ci(np.array(vals))}")
    rho = spearmanr(knn, delta).statistic
    rho_b = np.array([spearmanr(knn[bt], delta[bt]).statistic for bt in boots])
    print(f"  korelacja Spearmana wyniku kNN z ciągłym Δ: {rho:.3f}, {ci(rho_b)}")
    print("  sufit AUROC przy szumie etykiet (wzór AUROC_obs − ½ = (1 − α − β)(AUROC − ½), router idealny):")
    for flip in (0.05, 0.10, 0.15, 0.20):
        print(f"    α = β = {flip:.0%} błędnych etykiet → najwyższy obserwowalny AUROC {0.5 + (1 - 2 * flip) * 0.5:.2f}")

    print("\n=== 2. Ile jakości tracimy, wysyłając część ruchu do małego modelu? ===")
    print(f"zawsze duży {ql.mean():.3f}, zawsze mały {qs.mean():.3f}; spadek = 1 − jakość / „zawsze duży” (95% przedział)")
    oracle = delta  # idealny router wysyła do małego pytania z najmniejszym Δ
    print(f"{'do małego':>9s} | {'kNN: jakość':>22s} {'spadek':>22s} | {'samo źródło: spadek':>22s} | {'losowo: spadek':>22s} | {'idealny: spadek':>15s}")
    for f in SHARES_SMALL:
        res = {}
        for name, s in (("knn", knn), ("prior", prior), ("oracle", oracle)):
            res[name] = np.array([quality_at(s[bt], ql[bt], qs[bt], f, rng) / ql[bt].mean() for bt in boots])
        rnd = np.array([(f * qs[bt].mean() + (1 - f) * ql[bt].mean()) / ql[bt].mean() for bt in boots])
        q_knn = quality_at(knn, ql, qs, f, rng)
        print(
            f"{f:9.0%} | {q_knn:22.3f} {ci((1 - res['knn']) * 100, '.1f') + ' %':>22s} | {ci((1 - res['prior']) * 100, '.1f') + ' %':>22s}"
            f" | {ci((1 - rnd) * 100, '.1f') + ' %':>22s} | {(1 - res['oracle']).mean() * 100:13.1f} %"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--splits", nargs="+", default=["train"], choices=["train", "cal"])
    main(p.parse_args())
