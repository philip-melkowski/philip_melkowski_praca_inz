# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, read  # noqa: E402
from router_l1_cascade import quality_at  # noqa: E402
from router_l1_expanded import counts, pick_terms  # noqa: E402

THR = 0.25
SIZES = (5, 10, 30, 100)
SHARES = (0.3, 0.4, 0.5, 0.6, 0.7)
BOOT = 1000


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    texts = [questions[row[i]]["prompt"] for i in ids]
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    source = np.array([m["source"] for m in meta])
    y = np.array([m["delta"] for m in meta]) > THR
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    knn = np.zeros(len(ids))
    fires = {n: np.zeros(len(ids), dtype=bool) for n in SIZES}
    for tr, te in folds:
        knn[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), 20)
        for n in SIZES:
            cx, _ = pick_terms([texts[i] for i in tr], y[tr], n)
            fires[n][te] = counts([texts[i] for i in te], cx) > 0
    print(f"{len(ids)} pytań, CV po grupach; reguła „jeśli prompt zawiera dowolne z N słów COMPLEX → duży”, lista wybierana w każdej części tylko z jej części uczącej\n")
    print(f"bazowo COMPLEX {y.mean():.1%}; kNN wybiera do dużego 30–70% (jakość 0,3: {quality_at(knn, ql, qs, 0.3):.3f}, 0,5: {quality_at(knn, ql, qs, 0.5):.3f}, 0,7: {quality_at(knn, ql, qs, 0.7):.3f})\n")
    print(f"{'N słów':>7s} {'reguła zadziała':>16s} {'% COMPLEX wśród nich':>22s} {'bez warstwy 2':>14s}   jakość kaskady przy udziale do dużego (różnica vs kNN)")
    rng = np.random.default_rng(SEED)
    boots = [rng.integers(0, len(ids), len(ids)) for _ in range(BOOT)]
    for n in SIZES:
        f = fires[n]
        cas = np.where(f, 10.0, knn)
        cells = []
        for sh in SHARES:
            if sh < f.mean():
                cells.append("   (poniżej pokrycia)"); continue
            d = np.array([quality_at(cas[b], ql[b], qs[b], sh) - quality_at(knn[b], ql[b], qs[b], sh) for b in boots])
            cells.append(f"{int(sh * 100)}%: {quality_at(cas, ql, qs, sh):.3f} ({d.mean():+.3f} [{np.percentile(d, 2.5):+.3f};{np.percentile(d, 97.5):+.3f}])")
        print(f"{n:7d} {f.mean():16.1%} {y[f].mean():22.1%} {f.mean():14.1%}   " + "  ".join(cells))
    print("\nPokrycie reguły (N=30) wg źródła:")
    for src in sorted(set(source)):
        m = source == src
        print(f"  {src:14s} n={m.sum():4d} reguła zadziała {fires[30][m].mean():5.1%}, wśród nich COMPLEX {(y[m & fires[30]].mean() if (m & fires[30]).any() else float('nan')):5.1%} (źródło ogółem {y[m].mean():5.1%})")


if __name__ == "__main__":
    main()
