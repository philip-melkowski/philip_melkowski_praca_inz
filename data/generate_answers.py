# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
import argparse
import asyncio
import json
import os
import random
import time
from pathlib import Path
from typing import Any

import httpx

FORMAT = {
    "gsm8k": "\n\nSolve the problem step by step. Put the final numeric answer on the last line in the form: Answer: <number>",
    "triviaqa": "\n\nAnswer with a short phrase only.",
    "humaneval": "\n\nComplete the function. Reply with the full function in a single Python code block.",
}


def build_prompt(record: dict[str, Any]) -> str:
    return record["prompt"] + FORMAT.get(record["source"], "")


def done_keys(path: Path) -> set[tuple[str, str, int]]:
    if not path.exists():
        return set()
    keys: set[tuple[str, str, int]] = set()
    with path.open(encoding="utf-8") as f:
        for line in filter(str.strip, f):
            try:
                r = json.loads(line)
            except ValueError:
                continue  # linia urwana przy przerwaniu: zadanie zostanie powtórzone
            keys.add((r["id"], r["model"], r["sample"]))
    return keys


async def call(client: httpx.AsyncClient, url: str, body: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            r = await client.post(url, json=body)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


async def run(args: argparse.Namespace) -> None:
    with Path(args.input).open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    rows = [r for r in rows if r["split"] in args.splits]
    random.Random(args.seed).shuffle(rows)
    if args.limit:
        rows = rows[: args.limit]

    out = Path(args.output)
    if out.exists() and out.stat().st_size and not out.read_bytes().endswith(b"\n"):
        with out.open("a", encoding="utf-8") as f:
            f.write("\n")  # po przerwaniu w trakcie zapisu nowe wiersze nie mogą dokleić się do urwanego
    done = done_keys(out)
    jobs = [
        (r, model, s)
        for r in rows
        for model, n in ((args.small, args.n_small), (args.large, args.n_large))
        for s in range(n)
        if (r["id"], model, s) not in done
    ]
    print(f"pytań: {len(rows)}, zadań do wykonania: {len(jobs)} (pominięto już zrobione: {len(done)})")

    url = args.base_url.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.environ['API_KEY']}"} if os.environ.get("API_KEY") else {}
    extra = json.loads(args.extra_body) if args.extra_body else {}
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0, "err": 0}
    t0 = time.time()

    async with httpx.AsyncClient(headers=headers, timeout=args.timeout) as client:

        async def one(record: dict[str, Any], model: str, sample: int) -> None:
            body = {
                "model": model,
                "messages": [{"role": "user", "content": build_prompt(record)}],
                "temperature": args.temperature,
                "max_tokens": args.max_tokens,
                **extra,
            }
            async with sem:
                start = time.time()
                try:
                    data = await call(client, url, body)
                    choice = data["choices"][0]
                    entry = {
                        "id": record["id"],
                        "model": model,
                        "sample": sample,
                        "content": choice["message"].get("content") or "",
                        "finish_reason": choice.get("finish_reason"),
                        "usage": data.get("usage"),
                        "seconds": round(time.time() - start, 2),
                    }
                except Exception as e:
                    counter["err"] += 1
                    entry = {"id": record["id"], "model": model, "sample": sample, "error": str(e)[:300]}
            async with lock:
                if "error" not in entry:
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                counter["n"] += 1
                if counter["n"] % 10 == 0 or counter["n"] == len(jobs):
                    print(f"{counter['n']}/{len(jobs)} gotowe, błędów: {counter['err']}, {time.time() - t0:.0f}s")

        await asyncio.gather(*(one(*j) for j in jobs))
    print(f"koniec: {time.time() - t0:.0f}s, błędów: {counter['err']} (błędne zadania nie są zapisywane; uruchom ponownie, żeby je powtórzyć)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="questions_v2_split.jsonl")
    p.add_argument("--output", default="answers.jsonl")
    p.add_argument("--base-url", required=True, help="np. http://adres-df:8086 (zmienna API_KEY = klucz)")
    p.add_argument("--small", required=True)
    p.add_argument("--large", required=True)
    p.add_argument("--n-small", type=int, default=3)
    p.add_argument("--n-large", type=int, default=1)
    p.add_argument("--splits", nargs="+", default=["train", "cal", "test"])
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=1024)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("--extra-body", default="", help='JSON dołączany do zapytania, np. \'{"chat_template_kwargs":{"enable_thinking":false}}\'')
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
