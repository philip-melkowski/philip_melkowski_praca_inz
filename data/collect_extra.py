# /// script
# requires-python = ">=3.11"
# dependencies = ["datasets", "tiktoken"]
# ///
import argparse
import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import tiktoken
from datasets import load_dataset

SEED = 42
MIN_TOKENS = 16
MAX_TOKENS = 1500
DATASETS_DIR = Path(__file__).parent / "datasets"
EXISTING = DATASETS_DIR / "questions_v2_split.jsonl"
OUT = DATASETS_DIR / "questions_extra.jsonl"
SPLIT = "extra"  # nowe dane; podział (train/cal) i grupy dopiero po embeddingach, test zostaje bez zmian

ENC = tiktoken.get_encoding("cl100k_base")

Record = dict[str, Any]


def tokens(text: str) -> int:
    return len(ENC.encode(text, disallowed_special=()))


def norm(text: str) -> str:
    return " ".join(text.lower().split())


def latin(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return not letters or sum(c.isascii() for c in letters) / len(letters) >= 0.9  # pole języka w CodeChat bywa błędne


def record(prompt: str, source: str, category: str | None) -> Record:
    return {"prompt": prompt, "source": source, "type": "open", "gold": None, "category": category, "legacy_label": None}


def dolly() -> Iterator[Record]:
    for row in load_dataset("databricks/databricks-dolly-15k", split="train").shuffle(seed=SEED):
        context = re.sub(r"\[\d+\]", "", row["context"]).strip()  # karta zaleca usunąć przypisy Wikipedii
        prompt = f"{row['instruction'].strip()}\n\n{context}" if context else row["instruction"].strip()
        yield record(prompt, "dolly", row["category"].upper())


def codechat() -> Iterator[Record]:
    ds = load_dataset("Suzhen/CodeChat", split="train", streaming=True).shuffle(seed=SEED, buffer_size=10_000)
    for row in ds:
        first = row["conversation"][0][0]
        if first["role"] == "user" and first["language"] == "English":
            yield record(first["content"], "codechat", "CODING")


def arena140k() -> Iterator[Record]:
    ds = load_dataset("lmarena-ai/arena-human-preference-140k", split="train", streaming=True).shuffle(seed=SEED, buffer_size=10_000)
    for row in ds:
        if row["language"] != "en" or len(row["full_conversation"]) != 1:
            continue
        parts = row["conversation_a"][0]["content"]
        if any(p["type"] != "text" or p.get("image") for p in parts):
            continue
        yield record("\n".join(p["text"] for p in parts), "arena140k", "CODING" if row["is_code"] else None)


def main(args: argparse.Namespace) -> None:
    with EXISTING.open(encoding="utf-8") as f:
        existing = [json.loads(line)["prompt"] for line in f if line.strip()]
    seen = {norm(p) for p in existing}
    prefixes = {norm(p)[:80] for p in existing}  # CodeChat i Arena 140k mogą powtarzać nasze WildChat i Arenę
    records: list[Record] = []
    for name, gen in (("dolly", dolly), ("codechat", codechat), ("arena140k", arena140k)):
        kept = dup = 0
        for r in gen():
            if not MIN_TOKENS <= tokens(r["prompt"]) <= MAX_TOKENS or not latin(r["prompt"]):
                continue
            key = norm(r["prompt"])
            if key in seen or key[:80] in prefixes:
                dup += 1
                continue
            seen.add(key)
            prefixes.add(key[:80])
            records.append({"id": f"{r['source']}-{len(records):05d}", **r, "tokens": tokens(r["prompt"]), "split": SPLIT})
            kept += 1
            if kept == args.n:
                break
        print(f"{name}: {kept} pytań, pominięte powtórzenia: {dup}")
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    print(f"razem: {len(records)} -> {OUT}", flush=True)
    os._exit(0)  # strumieniowe load_dataset zostawia wątki, przez które proces nie kończy się sam


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Dodatkowe pytania (Dolly, CodeChat, Arena 140k) do pomiaru; bez Spidera (ocena wymaga uruchamiania SQL).")
    p.add_argument("--n", type=int, default=500, help="pytań z każdego zbioru")
    main(p.parse_args())
