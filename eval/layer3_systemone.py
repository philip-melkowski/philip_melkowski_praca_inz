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

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"


async def run(args: argparse.Namespace) -> None:
    questions_set = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    with (DATASETS_DIR / "questions_v2_split.jsonl").open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    with (DATASETS_DIR / "labels.jsonl").open(encoding="utf-8") as f:
        labelled = {json.loads(line)["id"] for line in f if line.strip()}
    rows = [r for r in rows if r["split"] in args.splits and r["id"] in labelled]
    if args.limit:
        rows = random.Random(42).sample(rows, min(args.limit, len(rows)))
    out = Path(args.output) if args.output else DATASETS_DIR / f"layer3_systemone_{args.model}_{Path(args.questions).stem}.jsonl"
    done = {json.loads(line)["id"] for line in out.open(encoding="utf-8")} if out.exists() else set()
    todo = [r for r in rows if r["id"] not in done]
    print(f"zestaw: {args.questions} ({len(questions_set)} pytań), model: {args.model}, pytań: {len(rows)}, do zrobienia: {len(todo)}, wynik: {out}")

    url = args.url.rstrip("/") + "/v1/systemone"
    key = os.environ.get(args.key_env, args.default_key)
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0, "err": 0}
    t0 = time.time()

    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {key}"}, timeout=args.timeout) as client:

        async def one(r: dict[str, Any]) -> None:
            async with sem:
                start = time.perf_counter()
                try:
                    resp = await client.post(url, json={"model": args.model, "state": r["prompt"], "questions": questions_set})
                    resp.raise_for_status()
                    answers = resp.json()["answers"]
                    entry = {"id": r["id"], "answers": {name: a["noul"] for name, a in answers.items()}, "seconds": round(time.perf_counter() - start, 3)}
                except Exception as e:
                    counter["err"] += 1
                    entry = {"id": r["id"], "error": str(e)[:200]}
                    print(f"błąd {r['id']}: {entry['error']}")
            async with lock:
                if "error" not in entry:
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                counter["n"] += 1
                if counter["n"] % 20 == 0 or counter["n"] == len(todo):
                    print(f"{counter['n']}/{len(todo)}, błędów {counter['err']}, {time.time() - t0:.0f}s")

        await asyncio.gather(*(one(r) for r in todo))


def main() -> None:
    p = argparse.ArgumentParser(description="Warstwa 3: odpowiedzi modelu decyzyjnego (/v1/systemone) na zestaw pytań typowanych.")
    p.add_argument("--url", default="http://localhost:8086", help="DF (lub Ollama: http://localhost:11434)")
    p.add_argument("--model", default="nimble")
    p.add_argument("--questions", default=str(Path(__file__).parent / "layer3_questions" / "v1.json"))
    p.add_argument("--output", default="", help="domyślnie data/datasets/layer3_systemone_<model>_<zestaw>.jsonl")
    p.add_argument("--splits", nargs="+", default=["train"])
    p.add_argument("--limit", type=int, default=0, help="losowa próbka (ziarno 42), 0 = wszystkie")
    p.add_argument("--key-env", default="DF_LOCAL_KEY", help="zmienna środowiskowa z kluczem")
    p.add_argument("--default-key", default="API_KEY", help="klucz, gdy zmienna nie jest ustawiona (lokalny DF)")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--timeout", type=float, default=180)
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
