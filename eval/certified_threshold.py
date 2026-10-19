# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import hashlib
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402

THR = 0.25
CRIT = 0.5
CONF = 0.95
MIN_ACCEPTED = 50
TARGETS_CRIT = (0.02, 0.05, 0.08, 0.10, 0.12, 0.15)
TARGETS_LABEL = (0.15, 0.20, 0.25, 0.30)


def upper_bound(k: int, n: int) -> float:
    return 1.0 if k >= n else float(beta.ppf(CONF, k + 1, n - k))


def pick(score: np.ndarray, bad: np.ndarray, target: float) -> tuple[float, int]:
    order = np.argsort(score, kind="stable")
    cum = np.cumsum(bad[order])
    best_n, best_t = 0, float("nan")
    for n in range(MIN_ACCEPTED, len(score) + 1):
        if upper_bound(int(cum[n - 1]), n) <= target:
            best_n, best_t = n, float(score[order][n - 1])
    return best_t, best_n


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels and labels[q["id"]]["split"] in ("train", "cal")]
    X = emb[[row[i] for i in ids]]
    group = np.array([questions[row[i]]["group"] for i in ids])
    delta = np.array([labels[i]["delta"] for i in ids])
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    y = delta > THR
    score = np.zeros(len(ids))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        score[te] = knn_score(X[te] @ X[tr].T, y[tr].astype(float), 20)
    fit = np.array([int(hashlib.md5(str(g).encode()).hexdigest(), 16) % 10 < 7 for g in group])
    cert = ~fit
    print(f"{len(ids)} pytań (wyniki poza próbką, CV po grupach); FIT {fit.sum()} / CERT {cert.sum()} (podział po grupach)\n")
    for name, bad, targets in (("błąd krytyczny (Δ > 0,5)", delta > CRIT, TARGETS_CRIT), ("etykieta COMPLEX (Δ > 0,25)", y, TARGETS_LABEL)):
        print(f"=== do małego wysyłamy pytania z niskim wynikiem; „błąd” = {name}; bazowo {bad.mean():.1%} wszystkich pytań ===")
        print(f"{'cel błędu ≤':>11s} | {'próg (FIT)':>10s} {'do małego':>10s} {'błąd obs.':>9s} {'górna gr. 95%':>13s} | {'CERT: do małego':>15s} {'błąd obs.':>9s} {'górna gr.':>9s} {'spełniony?':>10s} | {'jakość':>6s}")
        for r in targets:
            t, n = pick(score[fit], bad[fit], r)
            if n == 0:
                print(f"{r:11.0%} | brak progu (żaden próg nie daje gwarancji przy min. {MIN_ACCEPTED} przyjętych)")
                continue
            sel_fit = fit & (score <= t)
            sel_cert = cert & (score <= t)
            kf, nf = int(bad[sel_fit].sum()), int(sel_fit.sum())
            kc, nc = int(bad[sel_cert].sum()), int(sel_cert.sum())
            ub_c = upper_bound(kc, nc) if nc else float("nan")
            small_all = score <= t
            q = np.where(small_all, qs, ql).mean()
            print(f"{r:11.0%} | {t:10.3f} {nf / fit.sum():10.1%} {kf / nf:9.1%} {upper_bound(kf, nf):13.1%} | {nc / cert.sum():15.1%} {kc / max(nc, 1):9.1%} {ub_c:9.1%} {'tak' if kc / max(nc, 1) <= r else 'NIE':>10s} | {q:6.3f}")
        print()
    print(f"jakość: zawsze duży {ql.mean():.3f}, zawsze mały {qs.mean():.3f}; „jakość” = wszystkie pytania z progiem z FIT")


if __name__ == "__main__":
    main()
