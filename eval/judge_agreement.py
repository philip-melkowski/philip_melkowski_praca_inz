# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"


def load(name: str) -> dict[str, dict[tuple[str, int], int]]:
    out: dict[str, dict[tuple[str, int], int]] = {}
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[r["id"]] = {(s["model"], s["sample"]): s["score"] for s in r["scores"]}
    return out


def delta(s: dict[tuple[str, int], int]) -> float:
    large = next(v for (m, _), v in s.items() if m.startswith("Qwen/"))
    small = st.mean(v for (m, _), v in s.items() if not m.startswith("Qwen/"))
    return (large - small) / 4


def main(other: str) -> None:
    a, b = load("judge_open.jsonl"), load(other)
    ids = sorted(set(a) & set(b))
    pairs = [(a[i][k], b[i][k]) for i in ids for k in a[i] if k in b[i]]
    x, y = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    da, db = np.array([delta(a[i]) for i in ids]), np.array([delta(b[i]) for i in ids])
    print(f"wspólnych pytań {len(ids)}, ocen {len(pairs)} (sędzia 1: {Path('judge_open.jsonl').stem}, sędzia 2: {Path(other).stem})")
    print(f"oceny 1–5: identyczne {np.mean(x == y):.1%}, w granicach ±1 {np.mean(abs(x - y) <= 1):.1%}, Spearman {spearmanr(x, y)[0]:.3f}, średnia {x.mean():.2f} vs {y.mean():.2f}")
    print(f"Δ (0–1): Spearman {spearmanr(da, db)[0]:.3f}, średnia {da.mean():+.3f} vs {db.mean():+.3f}")
    la, lb = da > 0.25, db > 0.25
    print(f"klasa COMPLEX (Δ > 0,25): zgodność {np.mean(la == lb):.1%}, COMPLEX {la.mean():.1%} vs {lb.mean():.1%}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "judge_open_pro.jsonl")
