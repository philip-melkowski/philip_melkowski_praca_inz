"""
Budowa finalnego datasetu z połączenia danych Arena + syntetycznych.
Bez sztucznego balansowania — zachowujemy naturalny rozkład.

Uruchomienie:
  uv run data/build_dataset.py
"""

import json
import random
from collections import Counter
from pathlib import Path

SEED = 42
DATA_DIR = Path(__file__).parent / "datasets"

ARENA_PATH = DATA_DIR / "arena_filtered.jsonl"
SYNTHETIC_PATH = DATA_DIR / "synthetic.jsonl"
DATASET_PATH = DATA_DIR / "dataset.jsonl"
VALIDATION_PATH = DATA_DIR / "validation.jsonl"
TEST_PATH = DATA_DIR / "test.jsonl"

SPLIT_RATIO = 0.7  # 70% validation, 30% test
REQUIRED_FIELDS = {"query", "label", "category", "source"}
VALID_LABELS = {"SIMPLE", "COMPLEX"}
VALID_CATEGORIES = {
    "CODING", "REASONING", "MATH", "WRITING",
    "ROLEPLAY", "EXTRACTION", "KNOWLEDGE_STEM", "KNOWLEDGE_HUMANITIES",
}


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def normalize_arena(records: list[dict]) -> list[dict]:
    """Arena używa pola 'prompt' zamiast 'query' i nie ma kategorii."""
    normalized = []
    for r in records:
        normalized.append({
            "query": r.get("prompt") or r.get("query", ""),
            "label": r["label"],
            "category": r.get("category", "UNKNOWN"),
            "source": r["source"],
        })
    return normalized


def validate(records: list[dict]) -> list[dict]:
    valid = []
    skipped = 0
    for r in records:
        if not REQUIRED_FIELDS.issubset(r.keys()):
            skipped += 1
            continue
        if r["label"] not in VALID_LABELS:
            skipped += 1
            continue
        if r["category"] not in VALID_CATEGORIES:
            skipped += 1
            continue
        if not r["query"].strip():
            skipped += 1
            continue
        valid.append(r)
    if skipped:
        print(f"  Pominięto {skipped} rekordów (błędny schemat lub etykieta)")
    return valid


def stratified_split(records: list[dict], ratio: float, seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    by_label: dict[str, list[dict]] = {}
    for r in records:
        by_label.setdefault(r["label"], []).append(r)

    validation, test = [], []
    for label, recs in by_label.items():
        rng.shuffle(recs)
        cut = int(len(recs) * ratio)
        validation.extend(recs[:cut])
        test.extend(recs[cut:])

    rng.shuffle(validation)
    rng.shuffle(test)
    return validation, test


def main() -> None:
    print("Wczytywanie danych...")
    arena = normalize_arena(load_jsonl(ARENA_PATH))
    synthetic = load_jsonl(SYNTHETIC_PATH)

    print(f"  Arena:      {len(arena)} rekordów")
    print(f"  Syntetyczne: {len(synthetic)} rekordów")

    dataset = arena + synthetic
    print(f"\nŁącznie przed walidacją: {len(dataset)}")

    dataset = validate(dataset)
    print(f"Łącznie po walidacji:    {len(dataset)}")

    label_counts = Counter(r["label"] for r in dataset)
    category_counts = Counter(r["category"] for r in dataset)
    source_counts = Counter(r["source"] for r in dataset)

    print(f"\nRozkład etykiet: {dict(label_counts)}")
    print(f"Rozkład źródeł:  {dict(source_counts)}")
    print(f"Rozkład kategorii: {dict(category_counts)}")

    validation, test = stratified_split(dataset, SPLIT_RATIO, SEED)

    print(f"\nValidation: {len(validation)} ({dict(Counter(r['label'] for r in validation))})")
    print(f"Test:       {len(test)} ({dict(Counter(r['label'] for r in test))}) — zamknięty")

    write_jsonl(DATASET_PATH, dataset)
    write_jsonl(VALIDATION_PATH, validation)
    write_jsonl(TEST_PATH, test)

    print(f"\nZapisano do: {DATA_DIR}")


if __name__ == "__main__":
    main()
