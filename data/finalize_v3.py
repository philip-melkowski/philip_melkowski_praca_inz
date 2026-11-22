# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Etykiety v3 pomiaru głównego (zadanie z wpisu 123).

`combine`: `judge_open_v3.jsonl` = stare oceny sędziego, w których pytania z `changed_ids.txt` mają nowe oceny
(`judge_open_v3_changed.jsonl`); pytanie zmienione, którego sędzia nie ocenił ponownie, zostaje ze starą oceną (wypisane).
`export`: same liczby, bez treści pytań i odpowiedzi, do gita (`data/labels/`): `labels_v3.jsonl` i
`sample_scores_v3.jsonl` (ocena każdej próbki: id, model, numer próbki, jakość 0–1, ucięta)."""

import argparse
import json
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent / "datasets"
EXPORT_DIR = Path(__file__).parent / "labels"


def read(name: str) -> list[dict[str, Any]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def combine() -> None:
    changed = set((DATASETS_DIR / "changed_ids.txt").read_text(encoding="utf-8").split())
    new = {r["id"]: r for r in read("judge_open_v3_changed.jsonl")}
    out, kept_old = [], []
    for r in read("judge_open.jsonl"):
        if r["id"] in new:
            out.append(new[r["id"]])
        else:
            out.append(r)
            if r["id"] in changed:
                kept_old.append(r["id"])
    write(DATASETS_DIR / "judge_open_v3.jsonl", out)
    print(f"oceny: {len(out)}, nowe: {len(new)}, zmienione pytania otwarte bez nowej oceny: {len(kept_old)} {kept_old[:5]}")


def export() -> None:
    EXPORT_DIR.mkdir(exist_ok=True)
    keys = ("id", "source", "type", "split", "ood", "q_large", "q_small", "delta", "label", "both_failed", "truncated_large", "truncated_small")
    labels = [{k: r[k] for k in keys} for r in read("labels_v3.jsonl")]
    write(EXPORT_DIR / "labels_v3.jsonl", labels)
    samples = [
        {"id": s["id"], "model": s["model"], "sample": s["sample"], "quality": 1.0 if s["correct"] is True else 0.0, "truncated": s["truncated"]}
        for s in read("scores_gold_v3.jsonl")
    ]
    for j in read("judge_open_v3.jsonl"):
        samples += [
            {"id": j["id"], "model": s["model"], "sample": s["sample"], "quality": (s["score"] - 1) / 4, "truncated": s["truncated"]}
            for s in j["scores"]
        ]
    write(EXPORT_DIR / "sample_scores_v3.jsonl", samples)
    print(f"→ {EXPORT_DIR}: labels_v3.jsonl ({len(labels)}), sample_scores_v3.jsonl ({len(samples)}); bez treści pytań i odpowiedzi")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("step", choices=["combine", "export"])
    {"combine": combine, "export": export}[p.parse_args().step]()
