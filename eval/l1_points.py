# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from l1_heuristics import COMPLEX_PHRASES, SIMPLE_PHRASES, features  # noqa: E402
from router_baselines import SEED, knn_score, read  # noqa: E402

POINTS = {
    "complex_phrase": 1.0,
    "simple_phrase": -1.0,
    "url": 1.0,
    "length": [{"chars": 400, "points": 1.0}, {"chars": 1500, "points": 1.0}],
    "digits": {"over": 0.1, "points": -1.0},
}
THRESHOLDS = (1, 2, 3, 4)
OUT = Path(__file__).parent.parent / "data" / "router_l1.json"


def points(f: list[float]) -> float:
    chars = round(float(np.expm1(f[0])))
    total = POINTS["complex_phrase"] * f[7] + POINTS["simple_phrase"] * f[8]
    total += sum(s["points"] for s in POINTS["length"] if chars > s["chars"])
    if f[3] > POINTS["digits"]["over"]:
        total += POINTS["digits"]["points"]
    return total + (POINTS["url"] if f[6] else 0.0)


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    labels = {r["id"]: r for r in read("labels.jsonl")}
    qs = [q for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    pts = np.array([points(features(q["prompt"])) for q in qs])
    delta = np.array([labels[q["id"]]["delta"] for q in qs])
    y = delta > 0.25
    print(f"{len(qs)} pytań (train+cal); bazowo COMPLEX {y.mean():.1%}, błąd krytyczny (Δ > 0,5) {(delta > 0.5).mean():.1%}")
    print("rozkład punktów:", {int(k): int(v) for k, v in zip(*np.unique(pts, return_counts=True), strict=True)})
    print(f"\n{'próg (pkt ≥)':>12s} {'do dużego':>10s} {'% COMPLEX wśród nich':>21s} {'% krytycznych wśród nich':>25s} {'średnie Δ':>10s}")
    for t in THRESHOLDS:
        m = pts >= t
        if m.any():
            print(f"{t:12d} {m.mean():10.1%} {y[m].mean():21.1%} {(delta[m] > 0.5).mean():25.1%} {delta[m].mean():+10.3f}")
    spec = {"complex_phrases": COMPLEX_PHRASES, "simple_phrases": SIMPLE_PHRASES, "points": POINTS}
    OUT.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nzapisano {OUT} (frazy COMPLEX {len(COMPLEX_PHRASES)}, SIMPLE {len(SIMPLE_PHRASES)})")


if __name__ == "__main__":
    main()
