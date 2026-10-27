# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"

# DF nie przekazuje logprobs, więc model podaje jedną cyfrę 0–9 (temperatura 0); zapis jako (cyfra + 0,5) / 10, żeby był w (0, 1) jak wyniki /v1/systemone
PROMPTS = {
    "gap": (
        "You are routing requests between a small 8-billion-parameter assistant model and a large, strong model. Request:\n"
        '"""\n{prompt}\n"""\n'
        "On a scale from 0 to 9, how much better would the large model answer this request than the small model? "
        "0 = equally good, 9 = the small model would clearly fail while the large model succeeds. Reply with a single digit only."
    ),
    "difficulty": (
        "Rate how difficult it is for an AI assistant to answer the following request really well. Request:\n"
        '"""\n{prompt}\n"""\n'
        "Use a scale from 0 (trivial) to 9 (extremely hard). Reply with a single digit only."
    ),
}


async def run(args: argparse.Namespace) -> None:
    with (DATASETS_DIR / "questions_v2_split.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    with (DATASETS_DIR / "labels.jsonl").open(encoding="utf-8") as f:
        labelled = {json.loads(line)["id"] for line in f if line.strip()}
    rows = [r for r in rows if r["split"] in args.splits and r["id"] in labelled]
    out = Path(args.output) if args.output else DATASETS_DIR / f"layer3_llmrate_{args.model.replace('/', '_')}.jsonl"
    done = {json.loads(line)["id"] for line in out.open(encoding="utf-8") if line.strip()} if out.exists() else set()
    todo = [r for r in rows if r["id"] not in done]
    print(f"model: {args.model}, pytań: {len(rows)}, do zrobienia: {len(todo)}, wynik: {out}", flush=True)

    url = args.url.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.environ[args.key_env]}"} if os.environ.get(args.key_env) else {}
    extra = json.loads(args.extra_body) if args.extra_body else {}
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0, "err": 0}
    t0 = time.time()

    async with httpx.AsyncClient(headers=headers, timeout=args.timeout) as client:

        async def ask(prompt: str) -> float:
            body = {"model": args.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3, "temperature": 0, **extra}
            for attempt in range(3):
                try:
                    resp = await client.post(url, json=body)
                    resp.raise_for_status()
                    text = resp.json()["choices"][0]["message"].get("content") or ""
                    m = re.search(r"\d", text)
                    if not m:
                        raise ValueError(f"brak cyfry w odpowiedzi: {text!r}")
                    return (int(m.group()) + 0.5) / 10
                except (httpx.HTTPError, ValueError):
                    if attempt == 2:
                        raise
                    await asyncio.sleep(2 * (attempt + 1))
            raise RuntimeError("unreachable")

        async def one(r: dict[str, Any]) -> None:
            async with sem:
                start = time.perf_counter()
                try:
                    answers = {name: await ask(t.format(prompt=r["prompt"])) for name, t in PROMPTS.items()}
                    entry = {"id": r["id"], "answers": answers, "seconds": round(time.perf_counter() - start, 3)}
                except Exception as e:
                    counter["err"] += 1
                    entry = {"id": r["id"], "error": str(e)[:200]}
            async with lock:
                if "error" not in entry:
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                counter["n"] += 1
                if counter["n"] % 50 == 0 or counter["n"] == len(todo):
                    print(f"{counter['n']}/{len(todo)}, błędów {counter['err']}, {time.time() - t0:.0f}s", flush=True)

        await asyncio.gather(*(one(r) for r in todo))


def main() -> None:
    p = argparse.ArgumentParser(description="Warstwa 3, wariant: model językowy ocenia pytanie cyfrą 0–9 (różnica duży–mały, trudność); wynik w formacie layer3_systemone.py.")
    p.add_argument("--url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--key-env", default="API_KEY", help="zmienna środowiskowa z kluczem")
    p.add_argument("--output", default="")
    p.add_argument("--splits", nargs="+", default=["train"])
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--extra-body", default='{"reasoning_effort":"none"}')
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
