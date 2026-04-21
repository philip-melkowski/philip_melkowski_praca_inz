"""
Weryfikacja empiryczna kandydatów na słowa kluczowe dla warstwy 1 klasyfikatora.
Dla każdej frazy liczymy precision i recall na validation secie.

Metodologia: docs/reports/classifier_keywords_research.md

Uruchomienie:
  uv run eval/analyze_keywords.py
"""

import json
import re
from pathlib import Path

VALIDATION_PATH = Path(__file__).parent.parent / "data" / "datasets" / "validation.jsonl"

# Kandydaci COMPLEX — źródło przy każdej frazie: B=Bloom, A=AgentBus
COMPLEX_CANDIDATES = [
    # Bloom: Analyze
    ("analyze", "B"),
    ("compare", "B+A"),
    ("contrast", "B"),
    ("differentiate", "B"),
    ("examine", "B"),
    ("distinguish", "B"),
    ("organize", "B"),
    ("relate", "B"),
    # Bloom: Evaluate
    ("evaluate", "B+A"),
    ("assess", "B+A"),
    ("critique", "B"),
    ("justify", "B"),
    ("appraise", "B"),
    ("argue", "B"),
    ("defend", "B"),
    ("judge", "B"),
    ("weigh", "B"),
    ("recommend", "B"),
    # Bloom: Apply
    ("implement", "B+A"),
    ("solve", "B"),
    ("demonstrate", "B"),
    ("calculate", "B"),
    ("compute", "B"),
    # Bloom: Create + AgentBus
    ("design", "B+A"),
    ("build", "B"),
    ("develop", "B"),
    ("construct", "B"),
    ("generate", "B"),
    ("plan", "B"),
    ("compose", "B"),
    ("formulate", "B"),
    ("invent", "B"),
    # AgentBus
    ("optimize", "A"),
    ("refactor", "A"),
    ("architect", "A"),
    ("debug", "A"),
    ("investigate", "A"),
    ("explain why", "A"),
    ("step by step", "A"),
    ("pros and cons", "A"),
    ("trade-offs", "A"),
    ("review code", "A"),
]

# Kandydaci SIMPLE — źródło przy każdej frazie: B=Bloom, A=AgentBus
SIMPLE_CANDIDATES = [
    # Bloom: Remember
    ("what is", "B+A"),
    ("who is", "B+A"),
    ("when did", "B+A"),
    ("where is", "B+A"),
    ("define", "B"),
    ("name", "B"),
    ("identify", "B"),
    ("recall", "B"),
    ("state", "B"),
    ("repeat", "B"),
    # Bloom: Understand
    ("classify", "B"),
    ("describe", "B"),
    ("locate", "B"),
    ("recognize", "B"),
    ("summarize", "B"),
    ("translate", "B+A"),
    ("paraphrase", "B"),
    # AgentBus
    ("list", "A"),
    ("format", "A"),
    ("convert", "A"),
    ("is this", "A"),
    ("yes or no", "A"),
]


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"\b" + re.escape(phrase) + r"\b", text, re.IGNORECASE))


def analyze(
    records: list[dict],
    candidates: list[tuple[str, str]],
    target_label: str,
) -> list[dict]:
    total_target = sum(1 for r in records if r["label"] == target_label)
    results = []

    for phrase, source in candidates:
        matches = [r for r in records if contains_phrase(r["query"], phrase)]
        if not matches:
            results.append({
                "phrase": phrase,
                "source": source,
                "matches": 0,
                "precision": 0.0,
                "recall": 0.0,
            })
            continue

        correct = sum(1 for r in matches if r["label"] == target_label)
        precision = correct / len(matches) * 100
        recall = correct / total_target * 100

        results.append({
            "phrase": phrase,
            "source": source,
            "matches": len(matches),
            "precision": precision,
            "recall": recall,
        })

    return sorted(results, key=lambda x: -x["precision"])


def print_results(results: list[dict], target_label: str, min_precision: float, min_recall: float) -> None:
    print(f"\n{'Fraza':<20} {'Źródło':<8} {'Matches':>8} {'Precision':>10} {'Recall':>8}  {'OK?':>5}")
    print("-" * 65)
    for r in results:
        ok = "✓" if r["precision"] >= min_precision and r["recall"] >= min_recall else "✗"
        print(
            f"  {r['phrase']:<18} {r['source']:<8} {r['matches']:>7} "
            f"{r['precision']:>9.1f}% {r['recall']:>7.2f}%  {ok:>5}"
        )


def main() -> None:
    records = load_jsonl(VALIDATION_PATH)
    print(f"Wczytano {len(records)} rekordów (validation set)")

    n_complex = sum(1 for r in records if r["label"] == "COMPLEX")
    n_simple = sum(1 for r in records if r["label"] == "SIMPLE")
    print(f"COMPLEX: {n_complex}, SIMPLE: {n_simple}")

    MIN_PRECISION = 80.0
    MIN_RECALL = 1.0

    print(f"\n=== Kandydaci COMPLEX (próg: precision≥{MIN_PRECISION}%, recall≥{MIN_RECALL}%) ===")
    complex_results = analyze(records, COMPLEX_CANDIDATES, "COMPLEX")
    print_results(complex_results, "COMPLEX", MIN_PRECISION, MIN_RECALL)

    print("\n=== Podsumowanie ===")
    complex_ok = [r for r in complex_results if r["precision"] >= MIN_PRECISION and r["recall"] >= MIN_RECALL]
    print(f"COMPLEX: {len(complex_ok)}/{len(complex_results)} fraz przeszło próg")
    print(f"\nFrazy do implementacji: {[r['phrase'] for r in complex_ok]}")


if __name__ == "__main__":
    main()
