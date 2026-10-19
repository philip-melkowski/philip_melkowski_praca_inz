# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, read  # noqa: E402
from router_l1_expanded import counts, pick_terms  # noqa: E402
from router_layers import l1_features  # noqa: E402

THR = 0.25
SHARES = (0.3, 0.4, 0.5, 0.6, 0.7)
FORCED = (0.05, 0.10, 0.20)
BOOT = 1000


def quality_at(score: np.ndarray, ql: np.ndarray, qs: np.ndarray, share: float) -> float:
    n_large = int(round(share * len(score)))
    order = np.argsort(-score, kind="stable")
    big = np.zeros(len(score), dtype=bool)
    big[order[:n_large]] = True
    return float(np.where(big, ql, qs).mean())


def cascade(first: np.ndarray, knn: np.ndarray, frac: float, direction: str) -> np.ndarray:
    n = int(frac * len(first))
    out = knn.copy()
    if direction == "large":
        out[np.argsort(-first)[:n]] = 10.0
    else:
        out[np.argsort(first)[:n]] = -10.0
    return out


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    texts = [questions[row[i]]["prompt"] for i in ids]
    F = np.array([l1_features(questions[row[i]]["prompt"], questions[row[i]]["tokens"]) for i in ids])
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    y = np.array([m["delta"] for m in meta]) > THR
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    folds = list(GroupKFold(n_splits=5).split(X, groups=group))
    s = {k: np.zeros(len(ids)) for k in ("L1 obecna", "L1 + lista słów", "kNN")}
    for tr, te in folds:
        s["kNN"][te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), 20)
        sc = StandardScaler().fit(F[tr])
        s["L1 obecna"][te] = LogisticRegression(C=0.1, max_iter=3000).fit(sc.transform(F[tr]), y[tr]).predict_proba(sc.transform(F[te]))[:, 1]
        cx, sx = pick_terms([texts[i] for i in tr], y[tr], 100)
        ftr = np.column_stack([F[tr], counts([texts[i] for i in tr], cx), counts([texts[i] for i in tr], sx)])
        fte = np.column_stack([F[te], counts([texts[i] for i in te], cx), counts([texts[i] for i in te], sx)])
        sc2 = StandardScaler().fit(ftr)
        s["L1 + lista słów"][te] = LogisticRegression(C=0.1, max_iter=3000).fit(sc2.transform(ftr), y[tr]).predict_proba(sc2.transform(fte))[:, 1]

    rng = np.random.default_rng(SEED)
    n = len(ids)
    boots = [rng.integers(0, n, n) for _ in range(BOOT)]
    print(f"{n} pytań, CV po grupach. Jakość (0–1) przy danym udziale zapytań do dużego modelu; kaskada = warstwa 1 decyduje o X% pytań, reszta przez kNN.")
    print(f"zawsze mały {qs.mean():.3f}, zawsze duży {ql.mean():.3f}\n")
    base = {sh: quality_at(s["kNN"], ql, qs, sh) for sh in SHARES}
    print(f"{'wariant':44s} " + " ".join(f"{int(sh * 100):>12d}% duży" for sh in SHARES))
    print(f"{'kNN sam':44s} " + " ".join(f"{base[sh]:14.3f}" for sh in SHARES))
    for name in ("L1 obecna", "L1 + lista słów"):
        for direction in ("large", "small"):
            for frac in FORCED:
                sc_ = cascade(s[name], s["kNN"], frac, direction)
                vals, diffs = [], []
                for sh in SHARES:
                    if direction == "large" and sh < frac:
                        vals.append(float("nan")); diffs.append(None); continue
                    vals.append(quality_at(sc_, ql, qs, sh))
                    d = np.array([quality_at(sc_[b], ql[b], qs[b], sh) - quality_at(s["kNN"][b], ql[b], qs[b], sh) for b in boots])
                    diffs.append((np.percentile(d, 2.5), np.percentile(d, 97.5)))
                label = f"{name} → {'duży' if direction == 'large' else 'mały'} {int(frac * 100)}%, reszta kNN"
                print(f"{label:44s} " + " ".join(f"{v:14.3f}" for v in vals))
                print(f"{'   różnica vs kNN, 95% CI':44s} " + " ".join(f"{('%+.3f..%+.3f' % d) if d else '':>14s}" for d in diffs))


if __name__ == "__main__":
    main()
