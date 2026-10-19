# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
import argparse
import asyncio
import json
import random
import string
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
from judge_open import api_key  # noqa: E402

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PROMPTS = {
    "paraphrase": "Rewrite the following user message in different words, keeping exactly the same meaning, task, constraints, difficulty and language. Do not answer it. Return only the rewritten message.\n\n",
    "synonyms": "Rewrite the following user message replacing about 20% of its content words with synonyms or near-synonyms, keeping the same meaning, task, constraints and structure. Do not answer it. Return only the rewritten message.\n\n",
}


def typos(text: str, rng: random.Random, rate: float = 0.03) -> str:
    chars = list(text)
    out: list[str] = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        if ch.isalpha() and rng.random() < rate:
            kind = rng.choice(("drop", "dup", "swap", "sub"))
            if kind == "drop":
                pass
            elif kind == "dup":
                out.append(ch + ch)
            elif kind == "sub":
                out.append(rng.choice(string.ascii_lowercase))
            elif i + 1 < len(chars) and chars[i + 1].isalpha():
                out.extend((chars[i + 1], ch))
                i += 1
            else:
                out.append(ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gemini-3.8-flash")
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--concurrency", type=int, default=8)
    args = p.parse_args()

    def read(name: str) -> list[dict[str, Any]]:
        with (DATASETS_DIR / name).open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    cal = {r["id"] for r in read("labels.jsonl") if r["split"] == "cal"}
    questions = [r for r in read("questions_v2_split.jsonl") if r["id"] in cal and r.get("embed_tokens", r["tokens"]) <= 1500]
    random.Random(args.seed).shuffle(questions)
    questions = questions[: args.n]

    out = DATASETS_DIR / "robustness_variants.jsonl"
    done = set()
    if out.exists():
        done = {(r["id"], r["kind"]) for r in read(out.name)}
    rng = random.Random(args.seed)
    rows: list[dict[str, Any]] = []
    for q in questions:
        if (q["id"], "typos") not in done:
            rows.append({"id": q["id"], "kind": "typos", "text": typos(q["prompt"], rng)})
    if rows:
        with out.open("a", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)

    headers = {"x-goog-api-key": api_key()}
    sem = asyncio.Semaphore(args.concurrency)
    totals = {"in": 0, "out": 0, "err": 0}

    async with httpx.AsyncClient(headers=headers, timeout=120) as client:

        async def one(q: dict[str, Any], kind: str) -> None:
            body = {
                "contents": [{"role": "user", "parts": [{"text": PROMPTS[kind] + q["prompt"]}]}],
                "generationConfig": {"temperature": 0.3, "thinkingConfig": {"thinkingLevel": "low"}},
            }
            async with sem:
                try:
                    r = await client.post(URL.format(model=args.model), json=body)
                    r.raise_for_status()
                    data = r.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    u = data.get("usageMetadata", {})
                    totals["in"] += u.get("promptTokenCount", 0)
                    totals["out"] += u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
                except Exception:
                    totals["err"] += 1
                    return
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"id": q["id"], "kind": kind, "text": text}, ensure_ascii=False) + "\n")

        await asyncio.gather(*(one(q, k) for q in questions for k in PROMPTS if (q["id"], k) not in done))
    print(f"gotowe; tokeny wejście {totals['in']}, wyjście+myślenie {totals['out']}, błędów {totals['err']}")


if __name__ == "__main__":
    asyncio.run(main())
