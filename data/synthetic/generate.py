import json
import os
import random
import re
import time
from pathlib import Path

from google import genai

MODEL = "gemini-2.5-flash"
REQUESTS_PER_MINUTE = 14
BATCH_SIZE = 15
JACCARD_THRESHOLD = 0.6
AVOID_EXAMPLES_IN_PROMPT = 8

CATEGORIES = [
    "CODING",
    "REASONING",
    "MATH",
    "WRITING",
    "ROLEPLAY",
    "EXTRACTION",
    "KNOWLEDGE_STEM",
    "KNOWLEDGE_HUMANITIES",
]

# Few-shot examples z MT-Bench
SIMPLE_EXAMPLES = [
    "Write a persuasive email to convince your introverted friend, who dislikes public speaking, to volunteer as a guest speaker at a local event. Use compelling arguments and address potential objections. Please be concise.",
    "One morning after sunrise, Suresh was standing facing a pole. The shadow of the pole fell exactly to his right. Can you tell me the direction towards which the shadow was pointing - east, south, west, or north? Explain your reasoning steps.",
    "Write a simple website in HTML. When a user clicks the button, it shows a random joke from a list of 4 jokes.",
    "Implement a program to find the common elements in two arrays without using any extra data structures.",
    "Describe five key principles in evaluating an argument in analytical writing.",
]

COMPLEX_EXAMPLES = [
    "x+y = 4z, x*y = 4z^2, express x-y in z",
    "Implement a function to find the median of two sorted arrays of different sizes with O(1) space complexity and O(n) time complexity.",
    "Photosynthesis is a vital process for life on Earth. Could you outline the two main stages of photosynthesis, including where they take place within the chloroplast, and the primary inputs and outputs for each stage?",
    "Provide insights into the correlation between economic indicators such as GDP, inflation, and unemployment rates. Explain how fiscal and monetary policies affect those indicators.",
]

PROMPT_TEMPLATE = """\
You are generating evaluation data for a query complexity classifier for LLMs.

Definitions:
- SIMPLE query: a weak model (e.g. 7B) answers just as well as a strong model (e.g. GPT-4)
- COMPLEX query: a strong model answers noticeably better than a weak model
- BORDERLINE query: genuinely ambiguous — could go either way depending on the model

Examples of SIMPLE queries:
{simple_examples}

Examples of COMPLEX queries:
{complex_examples}

Categories: {categories}

Generate exactly {n} queries of type "{query_type}".
Requirements:
- Each query must be realistic (something a real user would type)
- Vary topics across categories
- For SIMPLE: straightforward, clear answer, no deep reasoning needed
- For COMPLEX: multi-step reasoning, deep domain knowledge, or nuanced analysis
- For BORDERLINE: genuinely on the edge — looks simple but requires depth, or looks complex but has a clear answer
- Do NOT repeat or closely paraphrase the examples above
- Do NOT generate queries similar to these already generated:
{avoid_examples}

Return a JSON array of objects. Each object must have:
- "query": the question text
- "category": one of {categories}

Output ONLY the JSON array, no explanation.

JSON array:\
"""


def normalize(text: str) -> set[str]:
    text = re.sub(r"[^a-z0-9\s]", "", text.lower())
    return set(text.split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_duplicate(query: str, fingerprints: list[set[str]]) -> bool:
    words = normalize(query)
    return any(jaccard(words, fp) >= JACCARD_THRESHOLD for fp in fingerprints)


def build_prompt(query_type: str, n: int, existing: list[str]) -> str:
    simple = "\n".join(f"- {e}" for e in SIMPLE_EXAMPLES)
    complex_ = "\n".join(f"- {e}" for e in COMPLEX_EXAMPLES)
    sample = random.sample(existing, min(AVOID_EXAMPLES_IN_PROMPT, len(existing)))
    avoid = "\n".join(f"- {p[:120]}" for p in sample) if sample else "  (none yet)"
    cats = ", ".join(CATEGORIES)
    return PROMPT_TEMPLATE.format(
        simple_examples=simple,
        complex_examples=complex_,
        categories=cats,
        n=n,
        query_type=query_type,
        avoid_examples=avoid,
    )


def parse_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).rstrip("` \n")
    return json.loads(text.strip())


def generate_batch(
    client: genai.Client, query_type: str, n: int, existing: list[str]
) -> list[dict]:
    prompt = build_prompt(query_type, n, existing)
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return parse_response(response.text)


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Ustaw zmienną środowiskową GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)

    # label -> (query_type, target_count)
    # BORDERLINE trafia do osobnego pliku — ręczna weryfikacja decyduje o etykiecie
    targets = {
        "SIMPLE": ("SIMPLE", 600),
        "COMPLEX": ("COMPLEX", 200),
        "BORDERLINE": ("BORDERLINE", 100),
    }

    out_path = Path(__file__).parent.parent / "datasets" / "synthetic.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing_records: list[dict] = []
    if out_path.exists():
        with open(out_path) as f:
            existing_records = [json.loads(line) for line in f if line.strip()]
    print(f"Istniejących rekordów: {len(existing_records)}")

    counts: dict[str, int] = {k: 0 for k in targets}
    fingerprints: dict[str, list[set[str]]] = {k: [] for k in targets}
    queries_by_label: dict[str, list[str]] = {k: [] for k in targets}

    for r in existing_records:
        label = r["label"]
        if label in counts:
            counts[label] += 1
            fingerprints[label].append(normalize(r["query"]))
            queries_by_label[label].append(r["query"])

    with open(out_path, "a") as f:
        for label, (query_type, target) in targets.items():
            needed = target - counts[label]
            print(f"\n{label}: potrzeba {needed} nowych rekordów")
            if needed <= 0:
                continue

            generated = 0
            skipped = 0

            while generated < needed:
                batch_n = min(BATCH_SIZE, needed - generated)
                try:
                    raw = generate_batch(client, query_type, batch_n, queries_by_label[label])
                    for item in raw:
                        query = item.get("query", "").strip()
                        category = item.get("category", "").strip().upper()

                        if not query or category not in CATEGORIES:
                            skipped += 1
                            continue
                        if is_duplicate(query, fingerprints[label]):
                            skipped += 1
                            continue

                        record = {
                            "query": query,
                            "label": label,
                            "category": category,
                            "source": "llm_generated",
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        fingerprints[label].append(normalize(query))
                        queries_by_label[label].append(query)
                        generated += 1
                        if generated >= needed:
                            break

                    print(f"  {label}: {generated}/{needed} (pominięto: {skipped})")
                    time.sleep(60 / REQUESTS_PER_MINUTE)
                except Exception as e:
                    print(f"  Błąd: {e}, retry za 10s...")
                    time.sleep(10)

    print(f"\nGotowe. Zapisano do: {out_path}")


if __name__ == "__main__":
    main()
