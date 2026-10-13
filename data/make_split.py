import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

SEED = 42
SIM_THRESHOLD = 0.95
FRACTIONS = {"train": 0.5, "cal": 0.2, "test": 0.3}
TEST_ONLY_SOURCES = {"mmlu", "mt_bench"}
GSM8K_TEST = 150
DATASETS_DIR = Path(__file__).parent / "datasets"
SRC = DATASETS_DIR / "questions_v2.jsonl"
EMB = DATASETS_DIR / "embeddings_nomic.npy"
OUT = DATASETS_DIR / "questions_v2_split.jsonl"


def groups(emb: np.ndarray) -> list[int]:
    n = len(emb)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    sim = emb @ emb.T
    for i, j in zip(*np.where(np.triu(sim, k=1) >= SIM_THRESHOLD), strict=True):
        parent[find(int(i))] = find(int(j))
    return [find(i) for i in range(n)]


def main() -> None:
    with SRC.open(encoding="utf-8") as f:
        rows: list[dict[str, Any]] = [json.loads(line) for line in f if line.strip()]
    group = groups(np.load(EMB))
    rng = random.Random(SEED)

    split: dict[int, str] = {}
    members: dict[int, list[int]] = defaultdict(list)
    for i, g in enumerate(group):
        members[g].append(i)

    gsm = [i for i, r in enumerate(rows) if r["source"] == "gsm8k"]
    rng.shuffle(gsm)
    gsm_test = set(gsm[:GSM8K_TEST])
    for i, r in enumerate(rows):
        if r["source"] in TEST_ONLY_SOURCES or i in gsm_test:
            split[i] = "test"

    pool = [i for i in range(len(rows)) if i not in split]
    total = len(rows)
    need = {k: round(total * v) for k, v in FRACTIONS.items()}
    need["test"] -= len(split)
    share = {k: v / sum(need.values()) for k, v in need.items()}

    by_source: dict[str, list[int]] = defaultdict(list)
    for g, idx in members.items():
        free = [i for i in idx if i in pool]
        if free:
            by_source[rows[free[0]]["source"]].append(g)
    for source, gs in by_source.items():
        rng.shuffle(gs)
        sizes = [len([i for i in members[g] if i in pool]) for g in gs]
        target = {k: share[k] * sum(sizes) for k in share}
        got = dict.fromkeys(share, 0)
        for g, s in zip(gs, sizes, strict=True):
            k = max(share, key=lambda k: target[k] - got[k])
            got[k] += s
            for i in members[g]:
                if i in pool:
                    split[i] = k

    out = [{**r, "group": group[i], "split": split[i], "ood": r["source"] in TEST_ONLY_SOURCES or i in gsm_test} for i, r in enumerate(rows)]
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")

    print("podział:", dict(Counter(r["split"] for r in out)))
    for source in sorted({r["source"] for r in out}):
        print(f"  {source}:", dict(Counter(r["split"] for r in out if r["source"] == source)))
    cross = sum(len({out[i]["split"] for i in idx}) > 1 for idx in members.values())
    print("grup podobnych pytań rozdzielonych między zbiory:", cross)
    print("typy w teście:", dict(Counter(r["type"] for r in out if r["split"] == "test")))


if __name__ == "__main__":
    main()
