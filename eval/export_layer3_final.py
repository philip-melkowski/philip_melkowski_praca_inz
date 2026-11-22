# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""Parametry warstwy 3 routera do testu (wariant A z wpisu 126): d1:3b, zestaw v1, regresja logistyczna na
logit(kNN) i logitach odpowiedzi, uczona na train + `extra_train` (etykiety v3, odpowiedzi d1 z GPU), kNN z CV po grupach.
Wynik w formacie pliku `decider_path` w DF."""

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
from layer3_choose_final import ZONE, collect, inner_knn, logit  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "data" / "router" / "router_l3_d1_final.json"


def main() -> None:
    d = collect(("train",), ("extra_train",))
    assert d["has_l3"].all()
    knn = inner_knn(d["X"], d["y"], d["g"])
    m = LogisticRegression(C=1.0, max_iter=3000).fit(np.column_stack([logit(knn), d["V1"]]), d["y"])
    questions = json.loads((ROOT / "eval" / "layer3_questions" / "v1.json").read_text(encoding="utf-8"))
    names = list(questions)
    params = {
        "model": "d1:3b",
        "questions": questions,
        "intercept": float(m.intercept_[0]),
        "knn_weight": float(m.coef_[0][0]),
        "weights": {n: float(w) for n, w in zip(names, m.coef_[0][1:], strict=True)},
        "zone_low": ZONE[0],
        "zone_high": ZONE[1],
        "timeout_seconds": 5.0,
    }
    OUT.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(d['y'])} pytań → {OUT.name}; wyraz wolny {params['intercept']:+.3f}, kNN {params['knn_weight']:+.3f}")
    for n, w in params["weights"].items():
        print(f"  {n:20s} {w:+.3f}")


if __name__ == "__main__":
    main()
