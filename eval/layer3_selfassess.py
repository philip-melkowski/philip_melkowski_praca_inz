# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
import argparse
import asyncio
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import httpx

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"

# Prompts frozen before the first run (dziennik, wpis 97).
PROMPTS = {
    "self_simple": (
        "You decide how hard a user request is for a language model.\n"
        "SIMPLE = a small model answers it as well as a large one (short facts, easy arithmetic, simple rewriting, casual chat).\n"
        "COMPLEX = a large model is clearly better (multi-step reasoning, long or hard code, deep analysis, long creative writing).\n"
        "Answer with exactly one word: SIMPLE or COMPLEX.\n\nRequest:\n{prompt}",
        ("sim", "com"),
    ),
    "self_can_answer": (
        "Here is a user request. Do not answer it. Decide whether you, yourself, can answer it fully and correctly.\n"
        "Answer with exactly one word: YES or NO.\n\nRequest:\n{prompt}",
        ("yes", "no"),
    ),
}


def p_first(top: list[dict[str, Any]], pos: str, neg: str) -> float | None:
    p = sum(math.exp(t["logprob"]) for t in top if t["token"].strip().lower().startswith(pos))
    n = sum(math.exp(t["logprob"]) for t in top if t["token"].strip().lower().startswith(neg))
    return p / (p + n) if p + n > 0 else None


async def run(args: argparse.Namespace) -> None:
    with (DATASETS_DIR / "questions_v2_split.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    with (DATASETS_DIR / "labels.jsonl").open(encoding="utf-8") as f:
        labelled = {json.loads(line)["id"] for line in f if line.strip()}
    rows = [r for r in rows if r["split"] in args.splits and r["id"] in labelled]
    if args.limit:
        rows = random.Random(42).sample(rows, min(args.limit, len(rows)))
    out = Path(args.output) if args.output else DATASETS_DIR / f"layer3_selfassess_{args.model.replace(':', '-')}.jsonl"
    done = {json.loads(line)["id"] for line in out.open(encoding="utf-8")} if out.exists() else set()
    todo = [r for r in rows if r["id"] not in done]
    print(f"model: {args.model}, pytań: {len(rows)}, do zrobienia: {len(todo)}, wynik: {out}")
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0, "err": 0}
    t0 = time.time()

    async with httpx.AsyncClient(timeout=args.timeout) as client:

        async def one(r: dict[str, Any]) -> None:
            async with sem:
                start = time.perf_counter()
                try:
                    answers: dict[str, float] = {}
                    for name, (template, (pos, neg)) in PROMPTS.items():
                        resp = await client.post(
                            f"{args.url.rstrip('/')}/api/chat",
                            json={
                                "model": args.model,
                                "messages": [{"role": "user", "content": template.format(prompt=r["prompt"])}],
                                "think": False,
                                "stream": False,
                                "logprobs": True,
                                "top_logprobs": 10,
                                "options": {"num_predict": 1, "temperature": 0, "num_ctx": 8192},
                            },
                        )
                        resp.raise_for_status()
                        p = p_first(resp.json()["logprobs"][0]["top_logprobs"], pos, neg)
                        if p is None:
                            raise ValueError(f"{name}: brak tokenów {pos}/{neg} w top_logprobs")
                        answers[name] = p
                    entry = {"id": r["id"], "answers": answers, "seconds": round(time.perf_counter() - start, 3)}
                except Exception as e:
                    counter["err"] += 1
                    entry = {"id": r["id"], "error": str(e)[:200]}
                    print(f"błąd {r['id']}: {entry['error']}")
            async with lock:
                if "error" not in entry:
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                counter["n"] += 1
                if counter["n"] % 50 == 0 or counter["n"] == len(todo):
                    print(f"{counter['n']}/{len(todo)}, błędów {counter['err']}, {time.time() - t0:.0f}s")

        await asyncio.gather(*(one(r) for r in todo))


def main() -> None:
    p = argparse.ArgumentParser(description="Warstwa 3, wariant A: mały model sam ocenia pytanie (prawdopodobieństwo z logprobs, natywne /api/chat Ollamy).")
    p.add_argument("--url", default="http://localhost:11434")
    p.add_argument("--model", default="qwen3:8b")
    p.add_argument("--output", default="")
    p.add_argument("--splits", nargs="+", default=["train"])
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=1)
    p.add_argument("--timeout", type=float, default=180)
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
