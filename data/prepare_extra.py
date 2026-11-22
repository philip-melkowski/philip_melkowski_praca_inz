# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28", "numpy"]
# ///
"""Embeddingi, grupy i podział dodatkowych pytań (wpisy 105–109, 118). Zbiór test pomiaru głównego bez zmian.

- Embeddingi: `nomic-embed-text` z prefiksem `classification: ` (jak `embed_questions.py`), Ollama pod `--url`. Najpierw
  sprawdzenie zgodności: te same wektory dla 20 pytań z train co w `embeddings_nomic.npy`.
- Grupy prawie-duplikatów: podobieństwo ≥ 0,95 (jak `make_split.py`), liczone łącznie ze starymi pytaniami.
- Podział (propozycja asystenta, do decyzji autora): pytanie w grupie z pytaniem testowym → `excluded` (ochrona testu);
  w grupie ze starym train lub cal → `extra_train`; pozostałe grupy losowo 70% `extra_train`, 30% `extra_val`
  (świeży zbiór walidacyjny zamiast zużytego cal), osobno dla każdego źródła.
Wynik: `embeddings_extra_nomic.npy`, `questions_extra_split.jsonl`."""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx
import numpy as np

DATASETS_DIR = Path(__file__).parent / "datasets"
MODEL = "nomic-embed-text"
PREFIX = "classification: "
SIM_THRESHOLD = 0.95
VAL_SHARE = 0.3
SEED = 42
BATCH = 16


def read(name: str) -> list[dict[str, Any]]:
    with (DATASETS_DIR / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def embed(client: httpx.Client, url: str, prompts: list[str]) -> np.ndarray:
    vectors: list[list[float]] = []
    for i in range(0, len(prompts), BATCH):
        r = client.post(f"{url}/v1/embeddings", json={"model": MODEL, "input": [PREFIX + p for p in prompts[i : i + BATCH]]})
        r.raise_for_status()
        vectors += [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]
    arr = np.asarray(vectors, dtype=np.float32)
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)


def main(args: argparse.Namespace) -> None:
    old = read("questions_v2_split.jsonl")
    old_emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    new = read("questions_extra.jsonl")
    with httpx.Client(timeout=600) as client:
        check = [i for i, q in enumerate(old) if q["split"] == "train"][:20]
        cos = (embed(client, args.url, [old[i]["prompt"] for i in check]) * old_emb[check]).sum(1)
        print(f"zgodność ze starymi embeddingami (20 pytań z train): min cos {cos.min():.6f}")
        if cos.min() < 0.999:
            raise SystemExit("embeddingi różnią się od pomiaru głównego: inny model lub wersja, przerwano")
        emb = embed(client, args.url, [q["prompt"] for q in new])
    np.save(DATASETS_DIR / "embeddings_extra_nomic.npy", emb)

    n_old = len(old)
    allv = np.vstack([old_emb, emb])
    parent = list(range(len(allv)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sim = emb @ allv.T
    for i, j in zip(*np.where(sim >= SIM_THRESHOLD), strict=True):
        a, b = n_old + int(i), int(j)
        if a != b:
            parent[find(a)] = find(b)
    members: dict[int, list[int]] = defaultdict(list)
    for k in range(len(allv)):
        members[find(k)].append(k)

    split: dict[int, str] = {}
    free_groups: dict[str, list[int]] = defaultdict(list)
    for g, idx in members.items():
        new_idx = [k for k in idx if k >= n_old]
        if not new_idx:
            continue
        old_splits = {old[k]["split"] for k in idx if k < n_old}
        if "test" in old_splits:
            for k in new_idx:
                split[k] = "excluded"
        elif old_splits:
            for k in new_idx:
                split[k] = "extra_train"
        else:
            free_groups[new[new_idx[0] - n_old]["source"]].append(g)
    rng = random.Random(SEED)
    for _source, gs in sorted(free_groups.items()):
        rng.shuffle(gs)
        n_val = round(VAL_SHARE * len(gs))
        for pos, g in enumerate(gs):
            for k in members[g]:
                if k >= n_old:
                    split[k] = "extra_val" if pos < n_val else "extra_train"

    out = []
    for i, q in enumerate(new):
        k = n_old + i
        out.append({**q, "group": f"x{find(k)}" if find(k) >= n_old else find(k), "split": split[k], "ood": False})
    (DATASETS_DIR / "questions_extra_split.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print(f"{len(out)} pytań: {dict(Counter(r['split'] for r in out))}")
    for source in sorted({r["source"] for r in out}):
        print(f"  {source}: {dict(Counter(r['split'] for r in out if r['source'] == source))}")
    dup_old = sum(1 for i in range(len(new)) if any(k < n_old for k in members[find(n_old + i)]))
    print(f"w grupie ze starym pytaniem (podobieństwo ≥ {SIM_THRESHOLD}): {dup_old}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:11434", help="Ollama z nomic-embed-text")
    main(p.parse_args())
