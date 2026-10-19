# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

THR = 0.25
PATTERN = re.compile(
    r"natsuki|sayori|yuri\b|monika|clubroom|naruto|freedom planet|\blilac\b|react to|characters react|\bsakura\b|\bau\b|fanfic|fan fic|roleplay|role-play|\bhinata\b|sonic|\bminecraft\b|\bpokemon\b|\banime\b",
    re.IGNORECASE,
)


def cv(X: np.ndarray, y: np.ndarray, ql: np.ndarray, qs: np.ndarray, group: np.ndarray) -> tuple[float, float]:
    oof = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        oof[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), 20)
    rng = np.random.default_rng(SEED)
    return float(roc_auc_score(y, oof)), float(pgr_curve(oof, ql, qs, rng).mean())


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    texts = [questions[row[i]]["prompt"] for i in ids]
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    source = np.array([m["source"] for m in meta])
    y = np.array([m["delta"] for m in meta]) > THR
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    fic = np.array([bool(PATTERN.search(t)) for t in texts])
    print(f"train+cal: {len(ids)} pytań; wzorzec fan-fiction/role-play/anime pasuje do {fic.sum()} ({fic.mean():.1%})")
    print(f"  COMPLEX wśród nich {y[fic].mean():.1%}, wśród reszty {y[~fic].mean():.1%}")
    for src in sorted(set(source)):
        m = source == src
        print(f"  {src:14s} n={m.sum():4d} dopasowane {fic[m].sum():4d} ({fic[m].mean():5.1%})")
    all_ = cv(X, y, ql, qs, group)
    no = cv(X[~fic], y[~fic], ql[~fic], qs[~fic], group[~fic])
    only = cv(X[fic], y[fic], ql[fic], qs[fic], group[fic])
    print(f"\nkNN CV: wszystkie       AUROC {all_[0]:.3f} APGR {all_[1]:.3f} (n={len(y)})")
    print(f"kNN CV: bez dopasowanych AUROC {no[0]:.3f} APGR {no[1]:.3f} (n={(~fic).sum()})")
    print(f"kNN CV: tylko dopasowane AUROC {only[0]:.3f} APGR {only[1]:.3f} (n={fic.sum()})")
    print(f"\nukształtowanie grup: liczba grup prawie-duplikatów wśród dopasowanych {len(set(group[fic]))} przy {fic.sum()} pytaniach")


if __name__ == "__main__":
    main()
