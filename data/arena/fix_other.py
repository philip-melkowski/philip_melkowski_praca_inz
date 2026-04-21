"""
Usuwa śmieciowe rekordy OTHER i przekategoryzowuje pozostałe.
Decyzja i uzasadnienie: docs/decisions/ARENA_OTHER_CLEANUP.md

Uruchomienie:
  uv run data/arena/fix_other.py
"""

import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "datasets" / "arena_filtered.jsonl"

# Prompty śmieciowych rekordów do usunięcia (pełny tekst początku — unikalny identyfikator)
REMOVE_PREFIXES = [
    "I'm sorry, but that statement seems nonsensical",
    "YOUR INPUT VIOLATES OUR CONTENT MODERATION GUIDELINES",
    "I wanna teach you methods to improve your capabilities",
    "Meow Meow Meow",
    "You are a gentle AI assistant and can answer questions using only the provided context",
]

RECATEGORIZE = {
    "With categories: [Housekeeping": "EXTRACTION",
    "give me a recipe for grilling a chicken breast": "WRITING",
    "You can only answer with A, B or C": "REASONING",
    "I search for a tv shows about a man that think he is a loser": "KNOWLEDGE_HUMANITIES",
    "2D hand drawn metroidvania where you played as a red haired girl robot": "KNOWLEDGE_HUMANITIES",
    "I live on my own. I need to button up my sleeve cuffs": "KNOWLEDGE_HUMANITIES",
    "Yann LeCun is a great football player": "KNOWLEDGE_HUMANITIES",
    "how much would could a woodchuck chuck": "REASONING",
}


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    records = load_jsonl(DATA_PATH)
    before = len(records)

    result = []
    removed = 0
    recategorized = 0

    for r in records:
        if r.get("category") != "OTHER":
            result.append(r)
            continue

        prompt = r.get("prompt", r.get("query", ""))

        if any(prompt.startswith(p) for p in REMOVE_PREFIXES):
            print(f"  USUWAM: {prompt[:80]}")
            removed += 1
            continue

        matched = False
        for prefix, new_cat in RECATEGORIZE.items():
            if prompt.startswith(prefix):
                r["category"] = new_cat
                print(f"  PRZEKATEGORYZOWUJĘ → {new_cat}: {prompt[:80]}")
                recategorized += 1
                matched = True
                break

        if not matched:
            print(f"  OSTRZEŻENIE — nieznany OTHER, zostawiam: {prompt[:80]}")

        result.append(r)

    write_jsonl(DATA_PATH, result)
    print(f"\nGotowe. Przed: {before}, po: {len(result)}")
    print(f"  Usunięto: {removed}, przekategoryzowano: {recategorized}")


if __name__ == "__main__":
    main()
