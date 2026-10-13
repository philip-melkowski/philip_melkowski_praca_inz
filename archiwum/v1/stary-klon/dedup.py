import json
import re
from pathlib import Path

DEDUP_THRESHOLD = 0.4

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"


def normalize(text: str) -> set[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return set(text.split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> None:
    path = DATA_DIR / "synthetic.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(f"Przed deduplikacją: {len(records)}")

    fingerprints: dict[str, list[set[str]]] = {"SIMPLE": [], "COMPLEX": []}
    kept: list[dict] = []
    removed = 0

    for record in records:
        label = record["label"]
        words = normalize(record["prompt"])
        if any(jaccard(words, fp) >= DEDUP_THRESHOLD for fp in fingerprints[label]):
            removed += 1
            continue
        fingerprints[label].append(words)
        kept.append(record)

    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in kept) + "\n")
    print(f"Usunięto duplikatów: {removed}")
    print(f"Po deduplikacji: {len(kept)}")


if __name__ == "__main__":
    main()
