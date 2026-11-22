# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Pomiar główny: odpowiedzi ucięte przy 2048 zastąpione ponownymi z limitem 4096 (wpis 106, zadanie z wpisu 123).

Wejście: `answers.jsonl` (komputer prywatny) i `answers_rerun4096_main.jsonl` (ponowne odpowiedzi na stare pytania,
odszyfrowane z `data/transfer/`). Numer próbki ponownych odpowiedzi małego modelu był nieznany (`sample_known: false`),
więc zastępują one ucięte próbki danego pytania i modelu w kolejności numerów próbek.
Wyjście: `answers_v3.jsonl` (oryginał bez zmian) i `changed_ids.txt` (pytania ze zmienioną odpowiedzią)."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent / "datasets"


def read(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    answers = read(DATASETS_DIR / "answers.jsonl")
    reruns: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in read(DATASETS_DIR / "answers_rerun4096_main.jsonl"):
        reruns[(r["id"], r["model"])].append(r)
    for v in reruns.values():
        v.sort(key=lambda r: r["sample"])

    truncated: dict[tuple[str, str], list[int]] = defaultdict(list)
    for i, a in enumerate(answers):
        if a.get("finish_reason") == "length":
            truncated[(a["id"], a["model"])].append(i)

    replaced, mismatch = 0, []
    for key, new in reruns.items():
        idx = sorted(truncated.get(key, []), key=lambda i: answers[i]["sample"])
        if len(idx) != len(new):
            mismatch.append((key, len(idx), len(new)))
        for i, r in zip(idx, new, strict=False):
            answers[i] = {**answers[i], "content": r["content"], "finish_reason": r["finish_reason"], "usage": r.get("usage"), "max_tokens": 4096}
            replaced += 1
    changed = sorted({k[0] for k in reruns})
    with (DATASETS_DIR / "answers_v3.jsonl").open("w", encoding="utf-8") as f:
        for a in answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    (DATASETS_DIR / "changed_ids.txt").write_text("\n".join(changed) + "\n", encoding="utf-8")
    still = sum(1 for a in answers if a.get("finish_reason") == "length")
    print(f"zastąpione odpowiedzi: {replaced}; pytania ze zmianą: {len(changed)}; nadal ucięte: {still}")
    if mismatch:
        print(f"UWAGA: {len(mismatch)} par (pytanie, model) z inną liczbą uciętych i ponownych, np. {mismatch[:3]}")


if __name__ == "__main__":
    main()
