# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import statistics as st
import sys
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from label_analysis import per_sample  # noqa: E402
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

K = 20
BOOT = 1000
CLUSTERS = (10, 25, 50, 100, 200)


def cluster_score(train_x: np.ndarray, train_y: np.ndarray, test_x: np.ndarray, k: int) -> np.ndarray:
    km = KMeans(n_clusters=k, n_init=3, random_state=SEED).fit(train_x)
    prior = train_y.mean()
    mean = np.array([(train_y[km.labels_ == c].sum() + 5 * prior) / ((km.labels_ == c).sum() + 5) for c in range(k)])
    return mean[km.predict(test_x)]


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels]
    X = emb[[row[i] for i in ids]]
    meta = [labels[i] for i in ids]
    group = np.array([questions[row[i]]["group"] for i in ids])
    split = np.array([m["split"] for m in meta])
    y = np.array([m["label"] == "COMPLEX" for m in meta])
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    tokens = np.array([questions[row[i]]["tokens"] for i in ids], dtype=float)
    source = np.array([m["source"] for m in meta])
    tr, ca = split == "train", split == "cal"
    Xt, yt, gt = X[tr], y[tr].astype(float), group[tr]
    cv = list(GroupKFold(n_splits=5).split(Xt, yt, gt))
    rng = np.random.default_rng(SEED)

    print("klastry (średnia etykieta w klastrze, k-means na embeddingach), walidacja krzyżowa po grupach na train:")
    cv_scores = {}
    for k in CLUSTERS:
        cv_scores[k] = float(np.mean([roc_auc_score(yt[b] > 0.5, cluster_score(Xt[a], yt[a], Xt[b], k)) for a, b in cv]))
        print(f"  k={k:4d}: AUROC {cv_scores[k]:.3f}")
    best = max(cv_scores, key=lambda k: cv_scores[k])
    s_cluster = cluster_score(Xt, yt, X[ca], best)
    s_knn = knn_score(X[ca] @ Xt.T, yt, K)
    prior = {s: y[tr & (source == s)].mean() for s in set(source) if (tr & (source == s)).any()}
    s_source = np.array([prior.get(s, yt.mean()) for s in source[ca]])
    s_len = np.log(tokens[ca])
    cand = {"kNN k=20": s_knn, f"klastry k={best}": s_cluster, "samo źródło": s_source, "sama długość": s_len}

    yc, qlc, qsc = y[ca], ql[ca], qs[ca]
    n = len(yc)
    boots = [rng.integers(0, n, n) for _ in range(BOOT)]
    boots = [b for b in boots if 0 < yc[b].sum() < n]

    def stat(score: np.ndarray, b: np.ndarray) -> tuple[float, float]:
        return roc_auc_score(yc[b], score[b]), float(pgr_curve(score[b], qlc[b], qsc[b], rng).mean())

    res = {name: np.array([stat(s, b) for b in boots]) for name, s in cand.items()}
    print(f"\n{'router (cal)':20s} AUROC [95% CI]           APGR [95% CI]")
    for name, a in res.items():
        print(f"{name:20s} {a[:, 0].mean():.3f} [{np.percentile(a[:, 0], 2.5):.3f},{np.percentile(a[:, 0], 97.5):.3f}]   {a[:, 1].mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f},{np.percentile(a[:, 1], 97.5):.3f}]")
    print("\nróżnice parowane (ta sama próbka bootstrapowa), średnia i 95% CI:")
    for a, b in (("kNN k=20", "samo źródło"), ("kNN k=20", "sama długość"), (f"klastry k={best}", "kNN k=20")):
        d = res[a] - res[b]
        print(f"  {a} − {b}: AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f},{np.percentile(d[:, 0], 97.5):+.3f}]  APGR {d[:, 1].mean():+.3f} [{np.percentile(d[:, 1], 2.5):+.3f},{np.percentile(d[:, 1], 97.5):+.3f}]")

    quality = per_sample()
    cal_ids = [i for i, s in zip(ids, ca, strict=True) if s]
    d0 = np.array([quality[i]["large"][0] - quality[i]["small"][0] for i in cal_ids])
    lab12 = np.array([quality[i]["large"][0] - st.mean(quality[i]["small"][1:]) > 0.25 for i in cal_ids])
    print(f"\nszacunek górnej granicy (cal): AUROC, z jakim Δ z jednej próbki małego przewiduje etykietę z dwóch pozostałych próbek = {roc_auc_score(lab12, d0):.3f}")
    print("  (ten sam wynik dużego w obu — jego szum wspólny, więc to zawyżony pułap; tylko rząd wielkości)")


if __name__ == "__main__":
    main()
