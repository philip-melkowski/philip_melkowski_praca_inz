import json
import statistics as st
from collections import defaultdict
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent / "datasets"
THRESHOLDS = (0.15, 0.25, 0.35)
THRESHOLD = 0.25
OUT = DATASETS_DIR / "labels.jsonl"


def read(name: str) -> list[dict[str, Any]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    questions = {r["id"]: r for r in read("questions_v2_split.jsonl")}
    quality: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"large": [], "small": []})
    trunc: dict[str, dict[str, int]] = defaultdict(lambda: {"large": 0, "small": 0})

    for s in read("scores_gold.jsonl"):
        side = "large" if s["model"].startswith("Qwen/") else "small"
        quality[s["id"]][side].append(1.0 if s["correct"] is True else 0.0)
        trunc[s["id"]][side] += s["truncated"]
    for j in read("judge_open.jsonl"):
        for s in j["scores"]:
            side = "large" if s["model"].startswith("Qwen/") else "small"
            quality[j["id"]][side].append((s["score"] - 1) / 4)
            trunc[j["id"]][side] += s["truncated"]

    rows = []
    for qid, q in quality.items():
        ql, qs = q["large"][0], st.mean(q["small"])
        delta = ql - qs
        meta = questions[qid]
        rows.append(
            {
                "id": qid,
                "source": meta["source"],
                "type": meta["type"],
                "split": meta["split"],
                "ood": meta["ood"],
                "q_large": ql,
                "q_small": qs,
                "delta": delta,
                "label": "COMPLEX" if delta > THRESHOLD else "SIMPLE",
                "both_failed": ql < 0.5 and qs < 0.5,
                "truncated_large": trunc[qid]["large"],
                "truncated_small": trunc[qid]["small"],
            }
        )
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    print(f"pytań z etykietą: {len(rows)} z {len(questions)}")
    header = f"{'grupa':14s} {'n':>5s}" + "".join(f" {'Δ>' + str(t):>9s}" for t in THRESHOLDS) + f" {'oba zawiodły':>13s} {'śr.Δ':>6s}"
    print(header)

    def line(name: str, v: list[dict[str, Any]]) -> None:
        cols = "".join(f" {sum(r['delta'] > t for r in v) / len(v):9.1%}" for t in THRESHOLDS)
        print(f"{name:14s} {len(v):5d}{cols} {sum(r['both_failed'] for r in v):13d} {st.mean(r['delta'] for r in v):6.2f}")

    for src in sorted({r["source"] for r in rows}):
        line(src, [r for r in rows if r["source"] == src])
    print()
    for typ in ("open", "gold"):
        line(typ, [r for r in rows if r["type"] == typ])
    for sp in ("train", "cal", "test"):
        line(sp, [r for r in rows if r["split"] == sp])
    line("RAZEM", rows)


if __name__ == "__main__":
    main()
