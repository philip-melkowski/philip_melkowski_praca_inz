# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28", "numpy"]
# ///
"""Czasy składników routera na GPU (Ollama bezpośrednio, np. przez tunel do df-5070ti-03): embedding `nomic-embed-text`,
model decyzyjny na `/v1/systemone` z zestawem v1 (8 pytań) i pulą v2 (34 pytania), generowanie małego modelu.
Pytania tylko z train (losowe, ziarno 42); test i cal nieużywane. Pomiar wpis 118."""

import argparse
import asyncio
import json
import random
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np

ROOT = Path(__file__).parent.parent
QUESTIONS_DIR = Path(__file__).parent / "layer3_questions"


def prompts(n: int) -> list[str]:
    with (ROOT / "data" / "datasets" / "questions_v2_split.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    rows = [r for r in rows if r["split"] == "train"]
    return [r["prompt"] for r in random.Random(42).sample(rows, n)]


def summary(name: str, times: list[float], wall: float, extra: str = "") -> None:
    t = np.array(times) * 1000
    print(
        f"{name:42s} n={len(t):4d}  p50 {np.percentile(t, 50):7.0f} ms  p90 {np.percentile(t, 90):7.0f} ms  "
        f"p99 {np.percentile(t, 99):7.0f} ms  przepustowość {len(t) / wall:6.2f}/s {extra}"
    )


async def bench(client: httpx.AsyncClient, url: str, bodies: list[dict[str, Any]], concurrency: int) -> tuple[list[float], float, list[dict[str, Any]]]:
    sem = asyncio.Semaphore(concurrency)
    times: list[float] = []
    outs: list[dict[str, Any]] = []

    async def one(body: dict[str, Any]) -> None:
        async with sem:
            t0 = time.perf_counter()
            r = await client.post(url, json=body)
            r.raise_for_status()
            times.append(time.perf_counter() - t0)
            outs.append(r.json())

    t0 = time.perf_counter()
    await asyncio.gather(*(one(b) for b in bodies))
    return times, time.perf_counter() - t0, outs


async def run(args: argparse.Namespace) -> None:
    base = args.url.rstrip("/")
    ps = prompts(args.n)
    sets = {name: json.loads((QUESTIONS_DIR / f"{name}.json").read_text(encoding="utf-8")) for name in ("v1", "pool_v2")}
    print(f"Ollama {base}, {len(ps)} pytań z train; rozgrzewka {args.warmup} żądań przed każdą serią\n")
    async with httpx.AsyncClient(timeout=600) as client:
        emb = [{"model": args.embed_model, "input": "classification: " + p} for p in ps]
        await bench(client, f"{base}/v1/embeddings", emb[: args.warmup], 1)
        times, wall, _ = await bench(client, f"{base}/v1/embeddings", emb, 1)
        summary(f"embedding {args.embed_model}, 1 naraz", times, wall)

        for set_name, qs in sets.items():
            bodies = [{"model": args.decider, "state": p, "questions": qs} for p in ps]
            await bench(client, f"{base}/v1/systemone", bodies[: args.warmup], 1)
            for c in args.concurrency:
                times, wall, _ = await bench(client, f"{base}/v1/systemone", bodies, c)
                summary(f"{args.decider} {set_name} ({len(qs)} pytań), {c} naraz", times, wall)

        chat = [
            {"model": args.small, "messages": [{"role": "user", "content": p}], "max_tokens": args.max_tokens, "reasoning_effort": "none"}
            for p in ps[: args.n_chat]
        ]
        await bench(client, f"{base}/v1/chat/completions", chat[:2], 1)
        times, wall, outs = await bench(client, f"{base}/v1/chat/completions", chat, 1)
        toks = sum(o["usage"]["completion_tokens"] for o in outs)
        summary(f"{args.small} generowanie (≤ {args.max_tokens} tok.), 1 naraz", times, wall, f"  {toks / sum(times):.0f} tok/s")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:21434")
    p.add_argument("--decider", default="d1:3b")
    p.add_argument("--small", default="qwen3:8b")
    p.add_argument("--embed-model", default="nomic-embed-text")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--n-chat", type=int, default=20)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--warmup", type=int, default=5)
    p.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8])
    asyncio.run(run(p.parse_args()))
