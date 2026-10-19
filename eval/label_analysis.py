import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"
THRESHOLD = 0.25


def read(name: str) -> list[dict[str, Any]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def per_sample() -> dict[str, dict[str, list[float]]]:
    q: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"large": [], "small": []})
    for s in read("scores_gold.jsonl"):
        q[s["id"]]["large" if s["model"].startswith("Qwen/") else "small"].append(1.0 if s["correct"] is True else 0.0)
    for j in read("judge_open.jsonl"):
        for s in j["scores"]:
            q[j["id"]]["large" if s["model"].startswith("Qwen/") else "small"].append((s["score"] - 1) / 4)
    return q


def main() -> None:
    labels = {r["id"]: r for r in read("labels.jsonl")}
    quality = per_sample()
    for group in ("open", "gold"):
        ids = [i for i in labels if labels[i]["type"] == group]
        stable = flips = 0
        agree_split = []
        for i in ids:
            ql, qs = quality[i]["large"][0], quality[i]["small"]
            single = [ql - s > THRESHOLD for s in qs]
            stable += len(set(single)) == 1
            flips += (ql - st.mean(qs) > THRESHOLD) != (sum(single) >= 2)
            agree_split.append((ql - qs[0] > THRESHOLD, ql - st.mean(qs[1:]) > THRESHOLD))
        n = len(ids)
        print(
            f"{group:5s} n={n}: etykieta z pojedynczej próbki małego zgodna we wszystkich 3 próbkach: {stable / n:.1%}; "
            f"próbka 0 vs średnia próbek 1–2 — ta sama klasa: {sum(a == b for a, b in agree_split) / n:.1%}"
        )
        print(f"       średnie odchylenie Q_mały między próbkami: {st.mean(st.pstdev(quality[i]['small']) for i in ids):.3f}")
    print("\nstara etykieta (z poprzedniego planu) vs zmierzona:")
    legacy = {r["id"]: r.get("legacy_label") for r in read("questions_v2_split.jsonl")}
    for src in ("chatbot_arena", "llm_generated"):
        c = Counter((legacy[i], labels[i]["label"]) for i in labels if labels[i]["source"] == src and legacy[i])
        n = sum(c.values())
        print(f"  {src}: " + ", ".join(f"stara {a} → zmierzona {b}: {v}" for (a, b), v in sorted(c.items())) + f"; zgodność {(c[('COMPLEX', 'COMPLEX')] + c[('SIMPLE', 'SIMPLE')]) / n:.1%}")


if __name__ == "__main__":
    main()
