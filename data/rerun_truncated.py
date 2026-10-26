# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from generate_answers import build_prompt, call  # noqa: E402

DATASETS_DIR = Path(__file__).parent / "datasets"
LARGE = "Qwen/Qwen3.8-27B-FP8"
SMALL = "qwen3:8b"


def read(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in filter(str.strip, f):
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def jobs_for(model: str, answers: list[Path], labels: Path | None) -> list[dict[str, Any]]:
    """Ucięte odpowiedzi danego modelu: z plików odpowiedzi (znany numer próbki) i z liczników w labels.jsonl (pomiar główny)."""
    jobs: list[dict[str, Any]] = []
    covered: set[str] = set()
    for path in answers:
        for r in read(path):
            if r["model"] == model:
                covered.add(r["id"])
                if r.get("finish_reason") == "length":
                    jobs.append({"id": r["id"], "model": model, "sample": r["sample"], "sample_known": True, "origin": path.name})
    if labels:
        field = "truncated_large" if model == LARGE else "truncated_small"
        for r in read(labels):
            if r["id"] in covered:
                continue
            # answers.jsonl pomiaru głównego jest na innym komputerze: wiadomo ile próbek ucięto, nie które,
            # więc przy scalaniu nowe odpowiedzi zastępują ucięte w kolejności numerów próbek
            for j in range(r.get(field, 0)):
                jobs.append({"id": r["id"], "model": model, "sample": j, "sample_known": False, "origin": labels.name})
    return jobs


async def run(args: argparse.Namespace) -> None:
    questions = {q["id"]: q for path in args.questions for q in read(Path(path))}
    jobs = jobs_for(args.model, [Path(p) for p in args.answers], Path(args.labels) if args.labels else None)
    out = Path(args.output)
    if out.exists() and out.stat().st_size and not out.read_bytes().endswith(b"\n"):
        with out.open("a", encoding="utf-8") as f:
            f.write("\n")
    key = lambda r: (r["id"], r["model"], r["sample"], r["origin"])  # noqa: E731
    done = {key(r) for r in read(out)} if out.exists() else set()
    todo = [j for j in jobs if key(j) not in done]
    print(f"model: {args.model}, uciętych: {len(jobs)}, do zrobienia: {len(todo)}, max_tokens {args.max_tokens}, wynik: {out}")

    url = args.base_url.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {os.environ['API_KEY']}"} if os.environ.get("API_KEY") else {}
    extra = json.loads(args.extra_body) if args.extra_body else {}
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counter = {"n": 0, "err": 0, "length": 0}
    t0 = time.time()

    async with httpx.AsyncClient(headers=headers, timeout=args.timeout) as client:

        async def one(job: dict[str, Any]) -> None:
            body = {
                "model": args.model,
                "messages": [{"role": "user", "content": build_prompt(questions[job["id"]])}],
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
                        **job,
                        "content": choice["message"].get("content") or "",
                        "finish_reason": choice.get("finish_reason"),
                        "usage": data.get("usage"),
                        "seconds": round(time.time() - start, 2),
                        "max_tokens": args.max_tokens,
                    }
                except Exception as e:
                    counter["err"] += 1
                    entry = {**job, "error": str(e)[:300]}
            async with lock:
                if "error" not in entry:
                    counter["length"] += entry["finish_reason"] == "length"
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                counter["n"] += 1
                if counter["n"] % 10 == 0 or counter["n"] == len(todo):
                    print(f"{counter['n']}/{len(todo)} gotowe, błędów: {counter['err']}, nadal uciętych: {counter['length']}, {time.time() - t0:.0f}s")

        await asyncio.gather(*(one(j) for j in todo))
    print(f"koniec: {time.time() - t0:.0f}s, błędów: {counter['err']} (uruchom ponownie, żeby je powtórzyć)")


def main() -> None:
    p = argparse.ArgumentParser(description="Ponowne generowanie odpowiedzi uciętych przy 2048 tokenach z większym limitem; oryginały bez zmian, wynik w osobnym pliku.")
    p.add_argument("--model", required=True, help=f"{LARGE} albo {SMALL}")
    p.add_argument("--base-url", required=True)
    p.add_argument("--questions", nargs="+", default=[str(DATASETS_DIR / "questions_v2_split.jsonl"), str(DATASETS_DIR / "questions_extra.jsonl")])
    p.add_argument("--answers", nargs="*", default=[str(DATASETS_DIR / "answers_extra.jsonl"), str(DATASETS_DIR / "answers_extra_small.jsonl")])
    p.add_argument("--labels", default=str(DATASETS_DIR / "labels.jsonl"), help="liczniki uciętych z pomiaru głównego; pusty napis = pomiń")
    p.add_argument("--output", default=str(DATASETS_DIR / "answers_rerun4096.jsonl"))
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=900)
    p.add_argument("--extra-body", default='{"reasoning_effort":"none"}')
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
