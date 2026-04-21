import json
from collections import Counter
from pathlib import Path

import numpy as np
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

DATA_PATH = Path(__file__).parent.parent / "datasets" / "arena_filtered.jsonl"
OUT_PATH = Path(__file__).parent / "analysis_report.md"


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Pominięto linię {i}: {e}")
    return records


def token_lengths(records: list[dict]) -> list[int]:
    return [len(enc.encode(r["prompt"])) for r in records]


def percentiles(values: list[int]) -> dict:
    arr = np.array(values)
    return {
        "min": int(arr.min()),
        "p25": int(np.percentile(arr, 25)),
        "p50": int(np.percentile(arr, 50)),
        "p75": int(np.percentile(arr, 75)),
        "p95": int(np.percentile(arr, 95)),
        "max": int(arr.max()),
    }


def top_keywords(records: list[dict], other_records: list[dict], n: int = 20) -> list[tuple[str, int]]:
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "are", "was", "were", "be", "been", "have", "has",
        "do", "does", "did", "will", "would", "can", "could", "should", "may",
        "might", "that", "this", "it", "i", "you", "he", "she", "we", "they",
        "what", "how", "why", "when", "where", "which", "who", "not", "no",
        "if", "as", "by", "from", "into", "about", "so", "than", "then",
        "me", "my", "your", "its", "our", "their", "some", "any", "all",
        "there", "here", "also", "just", "up", "out", "one", "two", "three",
    }

    def word_set(records: list[dict]) -> Counter:
        c: Counter = Counter()
        for r in records:
            words = r["prompt"].lower().split()
            for w in words:
                w = w.strip(".,!?;:\"'()[]{}").lower()
                if w and w not in stopwords and len(w) > 2:
                    c[w] += 1
        return c

    target = word_set(records)
    other = word_set(other_records)

    exclusive: Counter = Counter()
    for word, count in target.items():
        if count > other.get(word, 0):
            exclusive[word] = count

    return exclusive.most_common(n)


def analyze() -> None:
    records = load_jsonl(DATA_PATH)
    complex_ = [r for r in records if r["label"] == "COMPLEX"]
    simple = [r for r in records if r["label"] == "SIMPLE"]

    complex_lengths = token_lengths(complex_)
    simple_lengths = token_lengths(simple)

    complex_pct = percentiles(complex_lengths)
    simple_pct = percentiles(simple_lengths)

    winner_counts: Counter = Counter()
    for r in records:
        if r["winner"] == "tie":
            winner_counts["tie"] += 1
        elif r["label"] == "COMPLEX":
            winner_counts["strong won"] += 1
        else:
            winner_counts["weak won"] += 1

    strong_by_model: dict[str, Counter] = {}
    weak_by_model: dict[str, Counter] = {}
    for r in records:
        m = r["strong_model"]
        if m not in strong_by_model:
            strong_by_model[m] = Counter()
        strong_by_model[m][r["label"]] += 1

        m = r["weak_model"]
        if m not in weak_by_model:
            weak_by_model[m] = Counter()
        weak_by_model[m][r["label"]] += 1

    complex_keywords = top_keywords(complex_, simple)
    simple_keywords = top_keywords(simple, complex_)

    lines = []

    lines.append("# Analiza rozkładu — Chatbot Arena (filtered)\n")

    lines.append("## Rozkład etykiet\n")
    lines.append(f"| Etykieta | Liczba | % |")
    lines.append(f"|---|---|---|")
    total = len(records)
    for label, count in [("COMPLEX", len(complex_)), ("SIMPLE", len(simple))]:
        lines.append(f"| {label} | {count} | {count/total*100:.1f}% |")
    lines.append(f"| **Łącznie** | **{total}** | 100% |")
    lines.append("")

    lines.append("## Długość promptów (tokeny)\n")
    lines.append("| | min | p25 | p50 | p75 | p95 | max |")
    lines.append("|---|---|---|---|---|---|---|")
    for label, pct in [("COMPLEX", complex_pct), ("SIMPLE", simple_pct)]:
        lines.append(f"| {label} | {pct['min']} | {pct['p25']} | {pct['p50']} | {pct['p75']} | {pct['p95']} | {pct['max']} |")
    lines.append("")

    overlap_min = max(min(complex_lengths), min(simple_lengths))
    overlap_max = min(max(complex_lengths), max(simple_lengths))
    lines.append(f"**Overlap długości:** {overlap_min}–{overlap_max} tokenów (zakres wspólny obu klas)\n")

    lines.append("## Rozkład wyników głosowań\n")
    lines.append("| Wynik | Etykieta | Liczba | % |")
    lines.append("|---|---|---|---|")
    mapping = {"strong won": "COMPLEX", "weak won": "SIMPLE", "tie": "SIMPLE"}
    for winner, count in winner_counts.most_common():
        lines.append(f"| {winner} | {mapping[winner]} | {count} | {count/total*100:.1f}% |")
    lines.append("")

    lines.append("## Rozkład SIMPLE/COMPLEX wg strong_model\n")
    lines.append("| Model | COMPLEX | SIMPLE | % COMPLEX |")
    lines.append("|---|---|---|---|")
    for model, counts in sorted(strong_by_model.items()):
        c = counts.get("COMPLEX", 0)
        s = counts.get("SIMPLE", 0)
        t = c + s
        lines.append(f"| {model} | {c} | {s} | {c/t*100:.1f}% |")
    lines.append("")

    lines.append("## Rozkład SIMPLE/COMPLEX wg weak_model\n")
    lines.append("| Model | COMPLEX | SIMPLE | % COMPLEX |")
    lines.append("|---|---|---|---|")
    for model, counts in sorted(weak_by_model.items()):
        c = counts.get("COMPLEX", 0)
        s = counts.get("SIMPLE", 0)
        t = c + s
        lines.append(f"| {model} | {c} | {s} | {c/t*100:.1f}% |")
    lines.append("")

    lines.append("## Top 20 słów kluczowych — COMPLEX (częstsze niż w SIMPLE)\n")
    lines.append("| Słowo | Liczba wystąpień |")
    lines.append("|---|---|")
    for word, count in complex_keywords:
        lines.append(f"| {word} | {count} |")
    lines.append("")

    lines.append("## Top 20 słów kluczowych — SIMPLE (częstsze niż w COMPLEX)\n")
    lines.append("| Słowo | Liczba wystąpień |")
    lines.append("|---|---|")
    for word, count in simple_keywords:
        lines.append(f"| {word} | {count} |")
    lines.append("")

    OUT_PATH.write_text("\n".join(lines))
    print(f"Raport zapisany do: {OUT_PATH}")


if __name__ == "__main__":
    analyze()
