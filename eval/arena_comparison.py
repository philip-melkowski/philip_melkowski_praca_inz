# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "scikit-learn"]
# ///
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"


def read(name: str) -> list[dict[str, object]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    arena = {str(r["prompt"]): r for r in read("arena_filtered.jsonl")}
    questions = {str(r["id"]): str(r["prompt"]) for r in read("questions_v2_split.jsonl")}
    rows = []
    for lab in read("labels.jsonl"):
        if lab["source"] != "chatbot_arena":
            continue
        a = arena.get(questions[str(lab["id"])])
        if a is not None:
            rows.append((float(lab["delta"]), a["label"], a["winner"]))
    delta = np.array([r[0] for r in rows])
    old = np.array([r[1] == "COMPLEX" for r in rows])
    tie = np.array([r[2] == "tie" for r in rows])
    print(f"pytania Areny z głosem człowieka i zmierzoną etykietą: {len(rows)}")
    print(f"dawna etykieta COMPLEX (silny model wygrał w głosowaniu): {old.mean():.1%}; zmierzone COMPLEX (Δ > 0,25): {(delta > 0.25).mean():.1%}")
    print(f"AUROC: czy zmierzone Δ przewiduje wygraną silnego modelu w głosowaniu: {roc_auc_score(old, delta):.3f}; Spearman {spearmanr(delta, old)[0]:.3f}")
    print(f"średnie Δ: silny wygrał {delta[old].mean():+.3f}, remis lub słaby wygrał {delta[~old].mean():+.3f}; remis {delta[tie].mean():+.3f}")
    print(f"zgodność klas przy progu Δ > 0,25: {np.mean((delta > 0.25) == old):.1%}; dla progu Δ > 0: {np.mean((delta > 0) == old):.1%}")
    print("uwaga: głosowania dotyczą innych modeli (np. gpt-4, claude-v1 vs oasst-pythia, alpaca), nie pary Qwen3.8-27B / qwen3:8b")


if __name__ == "__main__":
    main()
