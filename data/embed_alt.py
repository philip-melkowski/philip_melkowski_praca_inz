# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "httpx>=0.28"]
# ///
import argparse
import json
import time
from pathlib import Path

import httpx
import numpy as np

DATASETS_DIR = Path(__file__).parent / "datasets"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen3-embedding:0.6b")
    p.add_argument("--prefix", default="Instruct: Rate how complex this user request is for a language model\nQuery: ")
    p.add_argument("--num-ctx", type=int, default=4096)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--output", default=str(DATASETS_DIR / "embeddings_qwen3.npy"))
    args = p.parse_args()

    with (DATASETS_DIR / "questions_v2_split.jsonl").open(encoding="utf-8") as f:
        prompts = [json.loads(line)["prompt"] for line in f if line.strip()]
    vecs: list[list[float]] = []
    t0 = time.time()
    with httpx.Client(timeout=300) as client:
        for i in range(0, len(prompts), args.batch):
            r = client.post(
                "http://localhost:11434/api/embed",
                json={"model": args.model, "input": [args.prefix + t for t in prompts[i : i + args.batch]], "options": {"num_ctx": args.num_ctx}},
            )
            r.raise_for_status()
            vecs.extend(r.json()["embeddings"])
            if (i // args.batch) % 25 == 0:
                print(f"{len(vecs)}/{len(prompts)} {time.time() - t0:.0f}s", flush=True)
    v = np.array(vecs, dtype=np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    np.save(args.output, v)
    print(f"zapisano {args.output}: {v.shape}, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
