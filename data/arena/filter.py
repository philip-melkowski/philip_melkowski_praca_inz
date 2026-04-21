from datasets import load_dataset
import json
import tiktoken
from pathlib import Path

STRONG_MODELS = {"gpt-4", "claude-v1", "claude-instant-v1"}

WEAK_MODELS = {
    "llama-13b",
    "dolly-v2-12b",
    "stablelm-tuned-alpha-7b",
    "fastchat-t5-3b",
    "chatglm-6b",
    "oasst-pythia-12b",
    "alpaca-13b",
    "RWKV-4-Raven-14B",
    "mpt-7b-chat",
}

MIN_PROMPT_TOKENS = 16
_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def extract_prompt(conversation: list[dict]) -> str | None:
    conversation = list(conversation)
    if not conversation:
        return None
    first = dict(conversation[0])
    if first.get("role") == "user":
        return first.get("content", "").strip()
    return None


def classify(winner: str, strong_is_model_a: bool) -> str | None:
    if winner == "tie (bothbad)":
        return None
    if winner == "tie":
        return "SIMPLE"
    winner_is_a = winner == "model_a"
    if winner_is_a == strong_is_model_a:
        return "COMPLEX"
    return "SIMPLE"


def filter_arena() -> None:
    print("Pobieranie datasetu...")
    ds = load_dataset("lmsys/chatbot_arena_conversations", split="train")
    df = ds.to_pandas()

    print(f"Rekordów wejściowych: {len(df)}")

    df = df[df["conversation_a"].apply(len) == 2]
    print(f"Po filtrze single-turn: {len(df)}")

    df = df[df["language"] == "English"]
    print(f"Po filtrze języka: {len(df)}")

    results = []

    for _, row in df.iterrows():
        model_a: str = row["model_a"]
        model_b: str = row["model_b"]

        a_strong = model_a in STRONG_MODELS
        b_strong = model_b in STRONG_MODELS
        a_weak = model_a in WEAK_MODELS
        b_weak = model_b in WEAK_MODELS

        if not ((a_strong and b_weak) or (a_weak and b_strong)):
            continue

        prompt = extract_prompt(row["conversation_a"])
        if not prompt:
            continue

        if count_tokens(prompt) < MIN_PROMPT_TOKENS:
            continue

        label = classify(row["winner"], strong_is_model_a=a_strong)
        if label is None:
            continue

        strong_model = model_a if a_strong else model_b
        weak_model = model_b if a_strong else model_a

        results.append(
            {
                "question_id": str(row["question_id"]),
                "prompt": prompt,
                "label": label,
                "source": "chatbot_arena",
                "strong_model": strong_model,
                "weak_model": weak_model,
                "winner": row["winner"],
            }
        )

    # deduplikacja — przy kolizji zachowujemy pierwszy napotkany (kolejność z datasetu)
    seen: set[str] = set()
    deduped = []
    for r in results:
        if r["prompt"] in seen:
            continue
        seen.add(r["prompt"])
        deduped.append(r)

    print(f"Po deduplicacji: {len(deduped)} (usunięto {len(results) - len(deduped)})")

    from collections import Counter
    label_counts = Counter(r["label"] for r in deduped)
    print(f"\nRozkład etykiet: {dict(label_counts)}")
    print(f"Bitwy wg strong_model: {dict(Counter(r['strong_model'] for r in deduped))}")
    print(f"Bitwy wg weak_model: {dict(Counter(r['weak_model'] for r in deduped))}")

    out_path = Path(__file__).parent.parent / "datasets" / "arena_filtered.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for record in deduped:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nZapisano do: {out_path}")


if __name__ == "__main__":
    filter_arena()
