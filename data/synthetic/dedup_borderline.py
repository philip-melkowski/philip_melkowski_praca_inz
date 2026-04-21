"""
Wykrywa i usuwa duplikaty wśród rekordów BORDERLINE w synthetic.jsonl.

Uruchomienie:
  uv run data/synthetic/dedup_borderline.py                    # podgląd par podobnych
  uv run data/synthetic/dedup_borderline.py --remove 55,62,93  # usuń wskazane indeksy
"""

import argparse
import json
import re
from pathlib import Path

THRESHOLD = 0.4
DATA_PATH = Path(__file__).parent.parent / "datasets" / "synthetic.jsonl"


def normalize(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9\s]", "", text.lower())
    return set(text.split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def find_similar(records: list[dict]) -> list[tuple[int, int, float]]:
    fps = [normalize(r["query"]) for r in records]
    pairs = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            sim = jaccard(fps[i], fps[j])
            if sim >= THRESHOLD:
                pairs.append((i, j, sim))
    return sorted(pairs, key=lambda x: -x[2])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--remove", type=str, help="Indeksy BORDERLINE do usunięcia, np. 55,62,93")
    args = parser.parse_args()

    all_records = load_jsonl(DATA_PATH)
    bl_records = [r for r in all_records if r["label"] == "BORDERLINE"]
    other = [r for r in all_records if r["label"] != "BORDERLINE"]

    print(f"Rekordów BORDERLINE: {len(bl_records)}")

    if args.remove:
        to_remove = {int(i) for i in args.remove.split(",")}
        kept = [r for i, r in enumerate(bl_records) if i not in to_remove]
        removed = len(bl_records) - len(kept)
        final = other + kept
        write_jsonl(DATA_PATH, final)
        print(f"Usunięto: {removed}. Pozostało BORDERLINE: {len(kept)}.")
        print(f"Brakuje {100 - len(kept)} BORDERLINE — zregeneruj przez generate.py")
        return

    pairs = find_similar(bl_records)
    if not pairs:
        print("Brak par powyżej progu Jaccard.")
        return

    print(f"\nPary podobnych rekordów (Jaccard >= {THRESHOLD}):\n")
    for i, j, sim in pairs:
        print(f"  [{i}] {bl_records[i]['query'][:90]}")
        print(f"  [{j}] {bl_records[j]['query'][:90]}")
        print(f"  similarity: {sim:.2f}\n")

    print("Użyj --remove <indeksy> żeby usunąć wskazane rekordy.")


if __name__ == "__main__":
    main()
