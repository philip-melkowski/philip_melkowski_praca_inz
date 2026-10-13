import json
import random
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import tiktoken
from datasets import load_dataset

SEED = 42
MIN_TOKENS = 16
MAX_TOKENS = 1500
DATASETS_DIR = Path(__file__).parent / "datasets"
OUT = DATASETS_DIR / "questions_v2.jsonl"

ENC = tiktoken.get_encoding("cl100k_base")

Record = dict[str, Any]


def tokens(text: str) -> int:
    return len(ENC.encode(text, disallowed_special=()))


def ok(text: str) -> bool:
    return MIN_TOKENS <= tokens(text) <= MAX_TOKENS


def take(records: Iterable[Record], n: int) -> list[Record]:
    out: list[Record] = []
    for r in records:
        if ok(r["prompt"]):
            out.append(r)
            if len(out) == n:
                break
    return out


def local(name: str, source: str, field: str, n: int) -> list[Record]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    random.Random(SEED).shuffle(rows)
    recs = (
        {
            "prompt": r[field],
            "source": source,
            "type": "open",
            "gold": None,
            "category": r.get("category"),
            "legacy_label": r["label"],
        }
        for r in rows
    )
    return take(recs, n)


def wildchat(n: int) -> Iterator[Record]:
    ds = load_dataset("allenai/WildChat-1M", split="train", streaming=True).shuffle(seed=SEED, buffer_size=10_000)
    prefixes: Counter[str] = Counter()
    for row in ds:
        conv = row["conversation"]
        if row["language"] != "English" or row["toxic"] or row["redacted"] or len(conv) != 2:
            continue
        if any(m["flagged"] for m in row["openai_moderation"]):
            continue
        if any(d["toxicity"] > 0.1 or d["sexual_explicit"] > 0.1 for d in row["detoxify_moderation"]):
            continue
        prompt = conv[0]["content"]
        prefix = " ".join(prompt.lower().split())[:80]
        prefixes[prefix] += 1
        if prefixes[prefix] > 1:
            continue
        yield {"prompt": prompt, "source": "wildchat", "type": "open", "gold": None, "category": None, "legacy_label": None}


def trivia() -> Iterator[Record]:
    for row in load_dataset("mandarjoshi/trivia_qa", "rc.nocontext", split="validation").shuffle(seed=SEED):
        yield {
            "prompt": row["question"],
            "source": "triviaqa",
            "type": "gold",
            "gold": {"answers": row["answer"]["aliases"]},
            "category": "FACTUAL_QA",
            "legacy_label": None,
        }


def gsm8k() -> Iterator[Record]:
    for row in load_dataset("openai/gsm8k", "main", split="train").shuffle(seed=SEED):
        yield {
            "prompt": row["question"],
            "source": "gsm8k",
            "type": "gold",
            "gold": {"answer": row["answer"].split("####")[-1].strip().replace(",", "")},
            "category": "MATH",
            "legacy_label": None,
        }


def mmlu() -> Iterator[Record]:
    for row in load_dataset("cais/mmlu", "all", split="test").shuffle(seed=SEED):
        options = "\n".join(f"{letter}. {choice}" for letter, choice in zip("ABCD", row["choices"], strict=True))
        yield {
            "prompt": f"{row['question']}\n\n{options}\n\nAnswer with the letter of the correct option.",
            "source": "mmlu",
            "type": "gold",
            "gold": {"answer": "ABCD"[row["answer"]], "subject": row["subject"]},
            "category": "KNOWLEDGE",
            "legacy_label": None,
        }


def humaneval() -> Iterator[Record]:
    for row in load_dataset("openai/openai_humaneval", split="test"):
        yield {
            "prompt": row["prompt"],
            "source": "humaneval",
            "type": "gold",
            "gold": {"test": row["test"], "entry_point": row["entry_point"]},
            "category": "CODING",
            "legacy_label": None,
        }


def mt_bench() -> Iterator[Record]:
    for row in load_dataset("HuggingFaceH4/mt_bench_prompts", split="train"):
        yield {
            "prompt": row["prompt"][0],
            "source": "mt_bench",
            "type": "open",
            "gold": None,
            "category": row["category"].upper(),
            "legacy_label": None,
        }


def main() -> None:
    parts = {
        "arena": local("arena_filtered.jsonl", "chatbot_arena", "prompt", 1732),
        "synthetic": local("synthetic.jsonl", "llm_generated", "query", 450),
        "wildchat": take(wildchat(1000), 1000),
        "triviaqa": take(trivia(), 300),
        "gsm8k": take(gsm8k(), 300),
        "mmlu": take(mmlu(), 300),
        "humaneval": list(humaneval()),
        "mt_bench": list(mt_bench()),
    }
    seen: set[str] = set()
    records: list[Record] = []
    for name, recs in parts.items():
        kept = 0
        for r in recs:
            key = " ".join(r["prompt"].lower().split())
            if key in seen:
                continue
            seen.add(key)
            records.append({"id": f"{r['source']}-{len(records):05d}", **r, "tokens": tokens(r["prompt"])})
            kept += 1
        print(f"{name}: {len(recs)} po filtrze, {kept} po deduplikacji")
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")
    print(f"Razem: {len(records)} -> {OUT}")


if __name__ == "__main__":
    main()
