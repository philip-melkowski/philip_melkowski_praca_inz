"""
Analiza długości promptów w validation secie.
Cel: sprawdzić czy długość tokenu jest dobrym sygnałem dla klasyfikatora (warstwa 1).

Uruchomienie:
  uv run eval/analyze_length.py
"""

import json
import statistics
from pathlib import Path

import tiktoken

VALIDATION_PATH = Path(__file__).parent.parent / "data" / "datasets" / "validation.jsonl"
ENCODER = tiktoken.get_encoding("cl100k_base")
BUCKETS = [(0, 50), (50, 150), (150, 400), (400, float("inf"))]


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def token_count(text: str) -> int:
    return len(ENCODER.encode(text))


def percentile(data: list[float], p: float) -> float:
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)


def print_stats(label: str, lengths: list[int]) -> None:
    print(f"\n  {label} (n={len(lengths)}):")
    print(f"    min={min(lengths)}  max={max(lengths)}  mean={statistics.mean(lengths):.1f}")
    print(f"    p10={percentile(lengths, 10):.0f}  p25={percentile(lengths, 25):.0f}  "
          f"p50={percentile(lengths, 50):.0f}  p75={percentile(lengths, 75):.0f}  "
          f"p90={percentile(lengths, 90):.0f}  p95={percentile(lengths, 95):.0f}")


def main() -> None:
    records = load_jsonl(VALIDATION_PATH)
    print(f"Wczytano {len(records)} rekordów z validation setu")

    by_label: dict[str, list[int]] = {"SIMPLE": [], "COMPLEX": []}
    for r in records:
        length = token_count(r["query"])
        by_label[r["label"]].append(length)

    # --- Statystyki ---
    print("\n=== Statystyki długości (tokeny) ===")
    for label, lengths in by_label.items():
        print_stats(label, lengths)

    # --- Overlap ---
    print("\n=== Overlap klas ===")
    simple = by_label["SIMPLE"]
    complex_ = by_label["COMPLEX"]
    median_complex = percentile(complex_, 50)
    median_simple = percentile(simple, 50)

    simple_above_median_complex = sum(1 for l in simple if l > median_complex) / len(simple) * 100
    complex_below_median_simple = sum(1 for l in complex_ if l < median_simple) / len(complex_) * 100

    print(f"  Mediana COMPLEX: {median_complex:.0f} tokenów")
    print(f"  Mediana SIMPLE:  {median_simple:.0f} tokenów")
    print(f"  % SIMPLE powyżej mediany COMPLEX: {simple_above_median_complex:.1f}%")
    print(f"  % COMPLEX poniżej mediany SIMPLE: {complex_below_median_simple:.1f}%")

    # --- Rozkład w przedziałach ---
    print("\n=== Rozkład w przedziałach tokenów ===")
    print(f"  {'Przedział':<15} {'SIMPLE':>10} {'SIMPLE%':>10} {'COMPLEX':>10} {'COMPLEX%':>10}")
    for lo, hi in BUCKETS:
        label_hi = f"{hi}" if hi != float("inf") else "∞"
        bucket_label = f"{lo}–{label_hi}"
        s = sum(1 for l in simple if lo <= l < hi)
        c = sum(1 for l in complex_ if lo <= l < hi)
        print(f"  {bucket_label:<15} {s:>10} {s/len(simple)*100:>9.1f}% {c:>10} {c/len(complex_)*100:>9.1f}%")


if __name__ == "__main__":
    main()
