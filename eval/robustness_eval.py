# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "scikit-learn", "httpx>=0.28"]
# ///
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, pgr_curve, read  # noqa: E402

OLLAMA = "http://localhost:11434/api/embed"
PREFIX = "classification: "
K = 20
SHARES = (0.3, 0.5)


def embed(texts: list[str]) -> np.ndarray:
    vecs: list[list[float]] = []
    with httpx.Client(timeout=120) as client:
        for i in range(0, len(texts), 16):
            r = client.post(OLLAMA, json={"model": "nomic-embed-text", "input": [PREFIX + t for t in texts[i : i + 16]]})
            r.raise_for_status()
            vecs.extend(r.json()["embeddings"])
    v = np.array(vecs)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def main() -> None:
    questions = {q["id"]: q for q in read("questions_v2_split.jsonl")}
    order = {q["id"]: i for i, q in enumerate(read("questions_v2_split.jsonl"))}
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    labels = {r["id"]: r for r in read("labels.jsonl")}
    train = [i for i in labels if labels[i]["split"] == "train"]
    Xt = emb[[order[i] for i in train]]
    yt = np.array([labels[i]["label"] == "COMPLEX" for i in train], dtype=float)

    variants: dict[str, dict[str, str]] = {}
    for r in read("robustness_variants.jsonl"):
        variants.setdefault(r["kind"], {})[r["id"]] = r["text"]
    ids = sorted(set.intersection(*(set(v) for v in variants.values())))
    print(f"pytań z kompletem wariantów: {len(ids)}")

    orig_text = [questions[i]["prompt"] for i in ids]
    stored = emb[[order[i] for i in ids]]
    t0 = time.time()
    fresh = embed(orig_text)
    ms = (time.time() - t0) / len(ids) * 1000
    cos = (stored * fresh).sum(1)
    print(f"kontrola spójności: cosinus zapisanego embeddingu (przez DF) i świeżego (Ollama bezpośrednio): min {cos.min():.4f}, mediana {np.median(cos):.4f}; średni czas {ms:.0f} ms/pytanie (partie po 16)")

    s0 = knn_score(stored @ Xt.T, yt, K)
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    thr = {p: np.quantile(s0, 1 - p) for p in SHARES}
    rng = np.random.default_rng(0)
    base_apgr = pgr_curve(s0, ql, qs, rng).mean()
    print(f"\nrouter kNN k={K}, indeks = train; zbiór = {len(ids)} pytań z cal; APGR oryginałów na tym podzbiorze {base_apgr:.3f}\n")
    print(f"{'wariant':12s} {'Spearman':>9s} {'śr.|Δ wyniku|':>14s} {'zmiana decyzji 30%':>19s} {'zmiana decyzji 50%':>19s} {'APGR':>6s} {'śr. cosinus do orygin.':>23s}")
    for kind, texts in variants.items():
        e = embed([texts[i] for i in ids])
        s = knn_score(e @ Xt.T, yt, K)
        flips = [float(np.mean((s0 >= thr[p]) != (s >= thr[p]))) for p in SHARES]
        print(f"{kind:12s} {spearmanr(s0, s)[0]:9.3f} {np.mean(np.abs(s0 - s)):14.3f} {flips[0]:19.1%} {flips[1]:19.1%} {pgr_curve(s, ql, qs, rng).mean():6.3f} {float(np.mean((e * fresh).sum(1))):23.3f}")
    rnd = np.random.default_rng(1)
    shuffled = s0[rnd.permutation(len(s0))]
    print(f"\nodniesienie: losowo przetasowane wyniki: zmiana decyzji 30%: {np.mean((s0 >= thr[0.3]) != (shuffled >= thr[0.3])):.1%}, 50%: {np.mean((s0 >= thr[0.5]) != (shuffled >= thr[0.5])):.1%}")


if __name__ == "__main__":
    main()
