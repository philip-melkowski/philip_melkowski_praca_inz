import json
import os
from pathlib import Path

import httpx
import numpy as np

DATASETS_DIR = Path(__file__).parent / "datasets"
SRC = DATASETS_DIR / "questions_v2.jsonl"
OUT = DATASETS_DIR / "embeddings_nomic.npy"
MODEL = "nomic-embed-text"
PREFIX = "classification: "
URL = os.environ.get("DF_URL", "http://localhost:8086")
BATCH = 16


def main() -> None:
    with SRC.open(encoding="utf-8") as f:
        prompts = [json.loads(line)["prompt"] for line in f if line.strip()]
    headers = {"Authorization": f"Bearer {os.environ['DF_INFRA_API_KEY']}"}
    vectors: list[list[float]] = []
    with httpx.Client(headers=headers, timeout=300) as client:
        for i in range(0, len(prompts), BATCH):
            r = client.post(f"{URL}/v1/embeddings", json={"model": MODEL, "input": [PREFIX + p for p in prompts[i : i + BATCH]]})
            r.raise_for_status()
            vectors += [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]
    arr = np.asarray(vectors, dtype=np.float32)
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    np.save(OUT, arr)
    print(arr.shape, "->", OUT)


if __name__ == "__main__":
    main()
