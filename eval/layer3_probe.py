# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
import argparse
import asyncio
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

TEMPLATE = (
    "You decide how hard a user request is for a language model.\n"
    "SIMPLE = a small model answers it as well as a large one (short facts, easy arithmetic, simple rewriting, casual chat).\n"
    "COMPLEX = a large model is clearly better (multi-step reasoning, long or hard code, deep analysis, long creative writing).\n"
    "Answer with exactly one word: SIMPLE or COMPLEX.\n\n"
    "Request:\n{prompt}\n\nAnswer:"
)
VERBAL = (
    "You decide how hard a user request is for a language model. Rate from 0 (trivial, any small model answers it perfectly) "
    "to 100 (only a large model can answer it well). Reply with the number only.\n\nRequest:\n{prompt}\n\nRating:"
)


def p_complex_from_logprobs(top: dict[str, float]) -> float | None:
    sim = [math.exp(v) for k, v in top.items() if k.strip().lower().startswith("sim")]
    com = [math.exp(v) for k, v in top.items() if k.strip().lower().startswith("com")]
    if not sim and not com:
        return None
    s, c = sum(sim), sum(com)
    return c / (s + c)


async def run(args: argparse.Namespace) -> None:
    with Path(args.input).open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    rows = [r for r in rows if r["split"] in args.splits and r.get("embed_tokens", r["tokens"]) <= args.max_tokens]
    if args.limit:
        rows = rows[: args.limit]
    out = Path(args.output)
    done = {json.loads(line)["id"] for line in out.open(encoding="utf-8")} if out.exists() else set()
    todo = [r for r in rows if r["id"] not in done]
    print(f"pytań: {len(rows)}, do zrobienia: {len(todo)}")

    base = args.base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {os.environ['API_KEY']}"} if os.environ.get("API_KEY") else {}
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0, "err": 0}
    t0 = time.time()

    async with httpx.AsyncClient(headers=headers, timeout=args.timeout) as client:

        async def one(r: dict[str, Any]) -> None:
            async with sem:
                start = time.perf_counter()
                try:
                    if args.mode == "logprobs":
                        resp = await client.post(
                            f"{base}/v1/completions",
                            json={"model": args.model, "prompt": TEMPLATE.format(prompt=r["prompt"]), "max_tokens": 1, "temperature": 0, "logprobs": 5},
                        )
                        resp.raise_for_status()
                        top = resp.json()["choices"][0]["logprobs"]["top_logprobs"][0]
                        entry = {"id": r["id"], "p_complex": p_complex_from_logprobs(top), "top": top}
                    else:
                        resp = await client.post(
                            f"{base}/v1/chat/completions",
                            json={
                                "model": args.model,
                                "messages": [{"role": "user", "content": VERBAL.format(prompt=r["prompt"])}],
                                "max_tokens": 8,
                                "temperature": 0,
                                "reasoning_effort": "none",
                            },
                        )
                        resp.raise_for_status()
                        text = resp.json()["choices"][0]["message"]["content"] or ""
                        m = re.search(r"\d+(?:\.\d+)?", text)
                        entry = {"id": r["id"], "p_complex": min(float(m.group()), 100.0) / 100 if m else None, "text": text[:40]}
                    entry["seconds"] = round(time.perf_counter() - start, 3)
                except Exception as e:
                    counter["err"] += 1
                    entry = {"id": r["id"], "error": str(e)[:200]}
            async with lock:
                if "error" not in entry:
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                counter["n"] += 1
                if counter["n"] % 20 == 0 or counter["n"] == len(todo):
                    print(f"{counter['n']}/{len(todo)}, błędów {counter['err']}, {time.time() - t0:.0f}s")

        await asyncio.gather(*(one(r) for r in todo))


def main() -> None:
    p = argparse.ArgumentParser(description="Test go/no-go warstwy 3: pewność małego modelu, że pytanie jest COMPLEX.")
    p.add_argument("--input", default="questions_v2_split.jsonl")
    p.add_argument("--output", default="layer3_probe.jsonl")
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True, help="mały model (ten sam, który odpowiada na SIMPLE)")
    p.add_argument("--mode", choices=["logprobs", "verbal"], default="logprobs", help="logprobs: /v1/completions z logprobs=5; verbal: ocena 0-100 przez /v1/chat/completions")
    p.add_argument("--splits", nargs="+", default=["cal"])
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--max-tokens", type=int, default=1500)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=120)
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
