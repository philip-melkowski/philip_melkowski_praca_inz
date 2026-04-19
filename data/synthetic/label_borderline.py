"""
Etykietowanie rekordów BORDERLINE przez LLM-as-Judge.

Flow:
1. Llama 3.1 8B (DeepFellow) odpowiada na pytanie BORDERLINE
2. Gemini 2.5 Flash ocenia jakość odpowiedzi → SIMPLE lub COMPLEX
3. Etykieta BORDERLINE zastąpiona w synthetic.jsonl

Uruchomienie:
  uv run data/synthetic/label_borderline.py [--dry-run]

Wymagane zmienne środowiskowe:
  GEMINI_API_KEY
  DF_API_KEY       — klucz do DeepFellow z Llama 3.1 8B
  DF_URL           — np. http://localhost:8086
"""

import argparse
import json
import os
import time
from pathlib import Path

import httpx
from google import genai

DF_MODEL = "llama3.1:8b"
GEMINI_MODEL = "gemini-2.5-flash"
DATA_PATH = Path(__file__).parent.parent / "datasets" / "synthetic.jsonl"

JUDGE_PROMPT = """\
You are evaluating whether a language model's answer to a question is good enough.

Context:
- SIMPLE = the weak model answered well — the answer is correct, complete, and useful
- COMPLEX = the weak model struggled — the answer is wrong, incomplete, or too shallow

Question:
{query}

Weak model's answer:
{answer}

Evaluate the answer. Reply with exactly one word: SIMPLE or COMPLEX.
"""


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def ask_llama(client: httpx.Client, df_url: str, df_key: str, query: str) -> str:
    response = client.post(
        f"{df_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {df_key}"},
        json={
            "model": DF_MODEL,
            "messages": [{"role": "user", "content": query}],
            "max_completion_tokens": 500,
            "temperature": 0.3,
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def judge_with_gemini(gemini_client: genai.Client, query: str, answer: str) -> str:
    prompt = JUDGE_PROMPT.format(query=query, answer=answer)
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    label = response.text.strip().upper()
    if "SIMPLE" in label:
        return "SIMPLE"
    if "COMPLEX" in label:
        return "COMPLEX"
    return "COMPLEX"  # fallback — wątpliwe → COMPLEX (bezpieczniejsze)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nie zapisuj zmian, tylko pokaż wyniki")
    args = parser.parse_args()

    gemini_key = os.environ.get("GEMINI_API_KEY")
    df_key = os.environ.get("DF_API_KEY")
    df_url = os.environ.get("DF_URL", "http://localhost:8086")

    if not gemini_key:
        raise RuntimeError("Ustaw GEMINI_API_KEY")
    if not df_key:
        raise RuntimeError("Ustaw DF_API_KEY")

    gemini_client = genai.Client(api_key=gemini_key)

    all_records = load_jsonl(DATA_PATH)
    borderline = [(i, r) for i, r in enumerate(all_records) if r["label"] == "BORDERLINE"]
    print(f"Rekordów BORDERLINE do etykietowania: {len(borderline)}")

    results: dict[int, str] = {}

    with httpx.Client() as http_client:
        for idx, (i, record) in enumerate(borderline):
            query = record["query"]
            print(f"\n[{idx+1}/{len(borderline)}] {query[:80]}...")

            try:
                answer = ask_llama(http_client, df_url, df_key, query)
                print(f"  Llama: {answer[:120]}...")

                label = judge_with_gemini(gemini_client, query, answer)
                print(f"  Judge: {label}")
                results[i] = label

                time.sleep(2)  # rate limit Gemini

            except Exception as e:
                print(f"  Błąd: {e} — pomijam, zostaje BORDERLINE")

    if args.dry_run:
        print("\n--- DRY RUN — bez zapisu ---")
        for i, label in results.items():
            print(f"  [{i}] {all_records[i]['query'][:60]} → {label}")
        return

    for i, label in results.items():
        all_records[i]["label"] = label

    write_jsonl(DATA_PATH, all_records)

    remaining = sum(1 for r in all_records if r["label"] == "BORDERLINE")
    print(f"\nZapisano. Pozostało BORDERLINE: {remaining}")
    print(f"Etykietowano: {len(results)}, pominięto błędów: {len(borderline) - len(results)}")


if __name__ == "__main__":
    main()
