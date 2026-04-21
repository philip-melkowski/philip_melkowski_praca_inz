"""
Kategoryzacja rekordów z Chatbot Arena przez Gemini 2.5 Flash.
Przypisuje kategorię MT-Bench do każdego promptu który ma category=UNKNOWN.

Uruchomienie:
  uv run data/arena/categorize.py

Wymagane zmienne środowiskowe:
  GEMINI_API_KEY
"""

import json
import os
import time
from pathlib import Path

from google import genai

GEMINI_MODEL = "gemini-2.5-flash"
REQUESTS_PER_MINUTE = 14
DATA_PATH = Path(__file__).parent.parent / "datasets" / "arena_filtered.jsonl"

CATEGORIES = [
    "CODING",
    "REASONING",
    "MATH",
    "WRITING",
    "ROLEPLAY",
    "EXTRACTION",
    "KNOWLEDGE_STEM",
    "KNOWLEDGE_HUMANITIES",
    "OTHER",
]

PROMPT_TEMPLATE = """\
Classify the following user query into exactly one category.

Categories:
- CODING: programming, debugging, code review, SQL, algorithms
- REASONING: logical reasoning, puzzles, argumentation, decision making
- MATH: calculations, proofs, mathematical problems
- WRITING: essays, emails, creative writing, summaries, persuasion
- ROLEPLAY: character-based scenarios, simulations, role-playing dialogues
- EXTRACTION: information extraction from text, translation, formatting, data parsing
- KNOWLEDGE_STEM: science, technology, engineering, medicine, biology, physics, chemistry
- KNOWLEDGE_HUMANITIES: history, law, philosophy, economics, psychology, social sciences
- OTHER: does not fit any of the above categories

Query:
{query}

Reply with exactly one word from the list above.\
"""


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def categorize(client: genai.Client, query: str) -> str:
    prompt = PROMPT_TEMPLATE.format(query=query[:1000])
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    category = response.text.strip().upper()
    if category in CATEGORIES:
        return category
    for cat in CATEGORIES:
        if cat in category:
            return cat
    return "OTHER"  # fallback — do ręcznego przeglądu


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Ustaw GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)
    records = load_jsonl(DATA_PATH)

    to_categorize = [(i, r) for i, r in enumerate(records) if r.get("category", "UNKNOWN") == "UNKNOWN"]
    print(f"Rekordów do kategoryzacji: {len(to_categorize)}")

    if not to_categorize:
        print("Wszystkie rekordy mają już kategorię.")
        return

    for idx, (i, record) in enumerate(to_categorize):
        try:
            category = categorize(client, record.get("prompt") or record.get("query", ""))
            records[i]["category"] = category

            if (idx + 1) % 50 == 0:
                write_jsonl(DATA_PATH, records)
                print(f"  [{idx+1}/{len(to_categorize)}] checkpoint zapisany")
            else:
                print(f"  [{idx+1}/{len(to_categorize)}] {category} — {record.get('prompt', record.get('query', ''))[:60]}")

            time.sleep(60 / REQUESTS_PER_MINUTE)

        except Exception as e:
            print(f"  Błąd [{idx+1}]: {e} — pomijam")

    write_jsonl(DATA_PATH, records)
    print(f"\nGotowe. Zaktualizowano {DATA_PATH}")

    from collections import Counter
    cats = Counter(r.get("category", "UNKNOWN") for r in records)
    print(f"Rozkład kategorii: {dict(cats)}")


if __name__ == "__main__":
    main()
