# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402

CRITICAL = 0.5


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    pool = [r for r in read("labels.jsonl") if r["split"] in ("train", "cal")]
    X = emb[[row[r["id"]] for r in pool]]
    delta = np.array([r["delta"] for r in pool])
    y = (delta > 0.25).astype(float)
    group = np.array([questions[row[r["id"]]]["group"] for r in pool])
    source = np.array([r["source"] for r in pool])
    score = np.zeros(len(pool))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        score[te] = knn_score(X[te] @ X[tr].T, y[tr], 20)

    crit = delta > CRITICAL
    waste = delta <= 0
    print(f"train+cal, poza próbką, kNN k=20; n={len(pool)}")
    print(f"błąd krytyczny: pytanie, w którym duży jest lepszy o > {CRITICAL} (≥ 2 punkty w skali 1–5 lub 1 poprawna odpowiedź przy mało poprawnych małego), a router wysłał je do małego ({crit.sum()} pytań, {crit.mean():.1%})")
    print(f"błąd kosztowy: pytanie, w którym mały jest tak samo dobry lub lepszy (Δ ≤ 0), a router wysłał je do dużego ({waste.sum()} pytań, {waste.mean():.1%})\n")
    print(f"{'próg':>5s} {'do dużego':>10s} {'błąd krytyczny':>15s} {'błąd kosztowy':>14s} | losowo przy tym samym udziale: krytyczny / kosztowy")
    for t in (0.2, 0.3, 0.4, 0.5):
        big = score >= t
        share = big.mean()
        print(f"{t:5.2f} {share:10.1%} {(~big[crit]).mean():15.1%} {big[waste].mean():14.1%} | {1 - share:.1%} / {share:.1%}")

    t = 0.3
    big = score >= t
    print(f"\nprzy progu {t}: błąd krytyczny wg źródła (udział pytań krytycznych skierowanych do małego / liczba pytań krytycznych)")
    per: dict[str, list[bool]] = defaultdict(list)
    for s, c, b in zip(source, crit, big, strict=True):
        if c:
            per[s].append(not b)
    for s, v in sorted(per.items(), key=lambda kv: -len(kv[1])):
        print(f"  {s:14s} {np.mean(v):6.1%} z {len(v)}")


if __name__ == "__main__":
    main()
