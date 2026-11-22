# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "scikit-learn", "httpx>=0.28"]
# ///
"""C4 na zbiorze test (protokół, pkt 4): zmiana decyzji zamrożonego routera R0 (heurystyki + kNN na indeksie końcowym)
po literówkach, parafrazach i synonimach, przy progach dających 30% i 50% ruchu do dużego (wyznaczonych na oryginałach).
Warianty: `robustness_variants_test.jsonl` (`robustness_generate.py --split test`), embeddingi przez lokalną Ollamę."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from robustness_eval import embed  # noqa: E402
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402
from test_final import ROOT, Heuristics  # noqa: E402

K = 20
SHARES = (0.3, 0.5)
LIMIT = 0.15


def main() -> None:
    index = np.load(ROOT / "data" / "router" / "router_index_final.npz")
    vec = index["vectors"] / np.linalg.norm(index["vectors"], axis=1, keepdims=True)
    lab = np.asarray(index["labels"], dtype=float)
    heur = Heuristics(ROOT / "data" / "router_l1.json")
    questions = {q["id"]: q for q in read("questions_v2_split.jsonl")}
    variants: dict[str, dict[str, str]] = {}
    for r in read("robustness_variants_test.jsonl"):
        variants.setdefault(r["kind"], {})[r["id"]] = r["text"]
    ids = sorted(set.intersection(*(set(v) for v in variants.values())))

    def r0(texts: list[str]) -> np.ndarray:
        knn = knn_score(embed(texts) @ vec.T, lab, K)
        forced = np.array([heur.points(t) >= 2 for t in texts])
        return np.where(forced, 1.0, knn)

    s0 = r0([questions[i]["prompt"] for i in ids])
    thr = {p: np.quantile(s0, 1 - p) for p in SHARES}
    print(f"{len(ids)} pytań testowych w dziedzinie; router R0 (zamrożony); C4: zmiana decyzji przy 30% do dużego ≤ {LIMIT:.0%}\n")
    print(f"{'wariant':12s} {'Spearman':>9s} {'zmiana decyzji 30%':>19s} {'zmiana decyzji 50%':>19s} {'C4':>5s}")
    for kind, texts in variants.items():
        s = r0([texts[i] for i in ids])
        flips = [float(np.mean((s0 >= thr[p]) != (s >= thr[p]))) for p in SHARES]
        print(f"{kind:12s} {spearmanr(s0, s)[0]:9.3f} {flips[0]:19.1%} {flips[1]:19.1%} {'tak' if flips[0] <= LIMIT else 'NIE':>5s}")
    shuffled = s0[np.random.default_rng(1).permutation(len(s0))]
    print(f"\nodniesienie (wyniki przetasowane): zmiana decyzji 30%: {np.mean((s0 >= thr[0.3]) != (shuffled >= thr[0.3])):.1%}")


if __name__ == "__main__":
    main()
