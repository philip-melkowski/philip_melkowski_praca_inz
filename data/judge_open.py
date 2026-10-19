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

DATASETS_DIR = Path(__file__).parent / "datasets"
KEY_FILE = Path.home() / ".config" / "inz" / "gemini_key"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

INSTRUCTIONS = """You are grading answers to a user's question. Below are the question and {n} candidate answers in random order.
Grade every answer independently from 1 to 5:
1 = wrong, irrelevant, harmful or a refusal without good reason
2 = mostly unhelpful or contains major errors
3 = acceptable but with noticeable flaws or omissions
4 = good, minor flaws only
5 = excellent: correct, complete, well suited to what the user asked
Judge correctness and usefulness for the user, not length or formatting. Do not prefer an answer because it is longer or comes first.
An answer marked [CUT OFF] was stopped by a length limit: judge only the part shown and do not penalize the missing remainder.
Return JSON: {{"scores": [<score for answer 1>, ..., <score for answer {n}>]}}"""

SCHEMA = {
    "type": "OBJECT",
    "properties": {"scores": {"type": "ARRAY", "items": {"type": "INTEGER"}}},
    "required": ["scores"],
}


def api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
    if not key:
        raise SystemExit("brak klucza: GEMINI_API_KEY albo plik ~/.config/inz/gemini_key")
    return key


def build_prompt(question: str, answers: list[dict[str, Any]]) -> str:
    parts = [INSTRUCTIONS.format(n=len(answers)), f"\n=== QUESTION ===\n{question}"]
    for i, a in enumerate(answers, 1):
        cut = " [CUT OFF]" if a["finish_reason"] == "length" else ""
        parts.append(f"\n=== ANSWER {i}{cut} ===\n{a['content']}")
    return "\n".join(parts)


def done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f if line.strip()}


async def call(client: httpx.AsyncClient, url: str, body: dict[str, Any], retries: int = 5) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            r = await client.post(url, json=body)
            if r.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError("retry", request=r.request, response=r)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError):
            if attempt == retries - 1:
                raise
            await asyncio.sleep(4 * 2**attempt)
    raise RuntimeError("unreachable")


async def run(args: argparse.Namespace) -> None:
    questions: dict[str, dict[str, Any]] = {}
    with (DATASETS_DIR / "questions_v2_split.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["type"] == "open":
                questions[r["id"]] = r
    by_id: dict[str, list[dict[str, Any]]] = {i: [] for i in questions}
    with (DATASETS_DIR / "answers.jsonl").open(encoding="utf-8") as f:
        for line in f:
            a = json.loads(line)
            if a["id"] in by_id:
                by_id[a["id"]].append(a)

    ids = sorted(questions)
    random.Random(args.seed).shuffle(ids)
    if args.limit:
        ids = ids[: args.limit]
    out = Path(args.output)
    done = done_ids(out)
    todo = [i for i in ids if i not in done]
    print(f"pytań otwartych: {len(ids)}, do oceny: {len(todo)} (pominięto: {len(ids) - len(todo)})")

    url = URL.format(model=args.model)
    headers = {"x-goog-api-key": api_key()}
    gen_config: dict[str, Any] = {
        "temperature": 0,
        "responseMimeType": "application/json",
        "responseSchema": SCHEMA,
    }
    if args.thinking:
        gen_config["thinkingConfig"] = json.loads(args.thinking)
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    totals = {"n": 0, "err": 0, "in": 0, "out": 0, "think": 0}
    t0 = time.time()

    async with httpx.AsyncClient(headers=headers, timeout=args.timeout) as client:

        async def one(qid: str) -> None:
            answers = by_id[qid]
            order = list(range(len(answers)))
            random.Random(f"{args.order_seed or args.seed}-{qid}").shuffle(order)
            shown = [answers[i] for i in order]
            body = {
                "contents": [{"role": "user", "parts": [{"text": build_prompt(questions[qid]["prompt"], shown)}]}],
                "generationConfig": gen_config,
            }
            entry: dict[str, Any]
            async with sem:
                try:
                    data = await call(client, url, body)
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    scores = json.loads(text)["scores"]
                    if len(scores) != len(shown):
                        raise ValueError(f"liczba ocen {len(scores)} != {len(shown)}")
                    usage = data.get("usageMetadata", {})
                    entry = {
                        "id": qid,
                        "judge": args.model,
                        "scores": [
                            {"model": a["model"], "sample": a["sample"], "score": s, "truncated": a["finish_reason"] == "length"}
                            for a, s in zip(shown, scores, strict=True)
                        ],
                        "tokens": {
                            "in": usage.get("promptTokenCount", 0),
                            "out": usage.get("candidatesTokenCount", 0),
                            "think": usage.get("thoughtsTokenCount", 0),
                        },
                    }
                except Exception as e:
                    totals["err"] += 1
                    entry = {"id": qid, "error": f"{type(e).__name__}: {e}"[:300]}
            async with lock:
                if "error" in entry:
                    print(f"błąd {qid}: {entry['error']}")
                else:
                    with out.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    for k in ("in", "out", "think"):
                        totals[k] += entry["tokens"][k]
                totals["n"] += 1
                if totals["n"] % 10 == 0 or totals["n"] == len(todo):
                    print(
                        f"{totals['n']}/{len(todo)} gotowe, błędów: {totals['err']}, "
                        f"tokeny wejście/wyjście/myślenie: {totals['in']}/{totals['out']}/{totals['think']}, {time.time() - t0:.0f}s"
                    )

        await asyncio.gather(*(one(i) for i in todo))
    print(f"koniec: {time.time() - t0:.0f}s, błędów: {totals['err']}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--output", default=str(DATASETS_DIR / "judge_open.jsonl"))
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--order-seed", type=int, default=0, help="inne ziarno kolejności odpowiedzi (0 = jak --seed)")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=180)
    p.add_argument("--thinking", default='{"thinkingLevel":"low"}', help='JSON do generationConfig.thinkingConfig, np. \'{"thinkingLevel":"low"}\'')
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
