# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "httpx>=0.28"]
# ///
import sys
import time
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402
from router_layers import l1_features  # noqa: E402

N = 200


def pct(v: list[float], p: float) -> float:
    return float(np.percentile(v, p))


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    labels = {r["id"]: r for r in read("labels.jsonl")}
    order = {q["id"]: i for i, q in enumerate(questions)}
    train = [i for i in labels if labels[i]["split"] == "train"]
    Xt = emb[[order[i] for i in train]].astype(np.float32)
    yt = np.array([labels[i]["label"] == "COMPLEX" for i in train], dtype=float)
    cal = [q for q in questions if q["id"] in labels and labels[q["id"]]["split"] == "cal"][:N]

    t_l1, t_emb, t_knn, t_all = [], [], [], []
    with httpx.Client(timeout=60) as client:
        client.post("http://localhost:11434/api/embed", json={"model": "nomic-embed-text", "input": ["classification: warm up"]})
        for q in cal:
            t0 = time.perf_counter()
            l1_features(q["prompt"], q["tokens"])
            t1 = time.perf_counter()
            r = client.post("http://localhost:11434/api/embed", json={"model": "nomic-embed-text", "input": ["classification: " + q["prompt"]]})
            v = np.array(r.json()["embeddings"][0], dtype=np.float32)
            v /= np.linalg.norm(v)
            t2 = time.perf_counter()
            knn_score((v @ Xt.T)[None, :], yt, 20)
            t3 = time.perf_counter()
            t_l1.append((t1 - t0) * 1000)
            t_emb.append((t2 - t1) * 1000)
            t_knn.append((t3 - t2) * 1000)
            t_all.append((t3 - t0) * 1000)
    print(f"{N} pojedynczych zapytań (bez partii), Ollama natywna (Metal), indeks kNN {len(yt)}×{Xt.shape[1]}, numpy na CPU, bez DF")
    for name, v in (("warstwa 1: cechy", t_l1), ("embedding (Ollama)", t_emb), ("kNN (iloczyn + top-k)", t_knn), ("razem L1+L2", t_all)):
        print(f"  {name:24s} p50 {pct(v, 50):6.1f} ms   p90 {pct(v, 90):6.1f} ms   p99 {pct(v, 99):6.1f} ms")


if __name__ == "__main__":
    main()
