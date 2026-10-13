import json
import os
from pathlib import Path
from typing import Any

import httpx

DATASETS_DIR = Path(__file__).parent / "datasets"
SRC = DATASETS_DIR / "questions_v2.jsonl"
REMOVED = DATASETS_DIR / "removed_too_long.jsonl"
MODEL = "nomic-embed-text"
LIMIT = 2048
CHECK_FROM_TIKTOKEN = 600
URL = os.environ.get("DF_URL", "http://localhost:8086")


def embed_tokens(client: httpx.Client, text: str) -> int:
    r = client.post(f"{URL}/v1/embeddings", json={"model": MODEL, "input": f"classification: {text}"})
    r.raise_for_status()
    return r.json()["usage"]["prompt_tokens"]


def main() -> None:
    with SRC.open(encoding="utf-8") as f:
        rows: list[dict[str, Any]] = [json.loads(line) for line in f if line.strip()]
    headers = {"Authorization": f"Bearer {os.environ['DF_INFRA_API_KEY']}"}
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    with httpx.Client(headers=headers, timeout=300) as client:
        for r in rows:
            n = embed_tokens(client, r["prompt"]) if r["tokens"] >= CHECK_FROM_TIKTOKEN else 0
            (removed if n >= LIMIT - 1 else kept).append({**r, "embed_tokens": n} if n else r)
    SRC.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in kept) + "\n", encoding="utf-8")
    REMOVED.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in removed) + ("\n" if removed else ""), encoding="utf-8")
    print(f"Sprawdzono pytań >= {CHECK_FROM_TIKTOKEN} tokenów tiktoken: {sum(r['tokens'] >= CHECK_FROM_TIKTOKEN for r in rows)}")
    print(f"Usunięto (>= {LIMIT - 1} tokenów nomic, czyli ucięte): {len(removed)}, zostało: {len(kept)}")
    for r in removed:
        print(f"  {r['source']} {r['id']} tiktoken={r['tokens']} nomic>={r['embed_tokens']}")


if __name__ == "__main__":
    main()
