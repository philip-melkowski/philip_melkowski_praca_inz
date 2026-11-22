# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Scalanie odpowiedzi na dodatkowe pytania (wpisy 105–109): `answers_extra.jsonl` (duży), `answers_extra_small.jsonl`
(mały, 3 próbki) i ponowne odpowiedzi z limitem 4096 (`answers_rerun4096.jsonl`), które zastępują odpowiedzi ucięte przy
2048 o tym samym id, modelu i numerze próbki. Wynik: `answers_extra_merged.jsonl` w formacie `answers.jsonl`."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent / "datasets"


def read(name: str) -> list[dict[str, Any]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    ids = {q["id"] for q in read("questions_extra.jsonl")}
    base = read("answers_extra.jsonl") + read("answers_extra_small.jsonl")
    key = lambda a: (a["id"], a["model"], a["sample"])  # noqa: E731
    reruns = {key(a): a for a in read("answers_rerun4096.jsonl") if a["id"] in ids and not a.get("error")}
    merged, replaced, missing = [], 0, 0
    for a in base:
        if a["finish_reason"] == "length":
            new = reruns.get(key(a))
            if new is not None:
                a, replaced = new, replaced + 1
            else:
                missing += 1
        merged.append(a)
    per_q = Counter(a["id"] for a in merged)
    assert set(per_q) == ids and set(per_q.values()) == {4}, "każde pytanie musi mieć 1 odpowiedź dużego i 3 małego"
    out = DATASETS_DIR / "answers_extra_merged.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for a in merged:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    cut = Counter(a["model"] for a in merged if a["finish_reason"] == "length")
    print(f"{len(merged)} odpowiedzi na {len(ids)} pytań → {out.name}")
    print(f"ucięte przy 2048 zastąpione ponownymi: {replaced}; ucięte bez ponownej odpowiedzi: {missing}")
    print(f"nadal ucięte (przy 4096 albo bez ponownej): {dict(cut)}")


if __name__ == "__main__":
    main()
