"""Podgląd stanu kategoryzacji arena_filtered.jsonl"""
import json
from collections import Counter
from pathlib import Path

records = [json.loads(l) for l in open("data/datasets/arena_filtered.jsonl") if l.strip()]
cats = Counter(r.get("category", "UNKNOWN") for r in records)
print(f"Łącznie rekordów: {len(records)}")
print(f"\nRozkład kategorii:")
for cat, count in cats.most_common():
    print(f"  {cat}: {count}")

unknown = [r for r in records if r.get("category", "UNKNOWN") == "UNKNOWN"]
if unknown:
    print(f"\nPrzykłady UNKNOWN ({len(unknown)} łącznie):")
    for r in unknown[:5]:
        print(f"  - {r.get('prompt', r.get('query', ''))[:100]}")
