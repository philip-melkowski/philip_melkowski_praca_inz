# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from layer3_systemone_vs_knn import BOOT, K, ZONE, ci, logit  # noqa: E402
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

V1 = ["rare_knowledge", "multistep", "code", "long_answer", "single_correct", "open_ended", "constraints", "small_model_enough"]


def in_zone(k: np.ndarray) -> np.ndarray:
    return (k >= ZONE[0]) & (k <= ZONE[1])


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    runs: list[tuple[str, dict[str, dict[str, float]]]] = []
    for path in args.inputs:
        with Path(path).open(encoding="utf-8") as f:
            runs.append((Path(path).stem.removeprefix("layer3_systemone_"), {r["id"]: r["answers"] for r in (json.loads(line) for line in f if line.strip())}))
    ids = sorted(set.intersection(*(set(a) for _, a in runs)) & {i for i in labels if labels[i]["split"] in args.splits})
    # cechy: pytanie (jeden plik) albo plik/pytanie (kilka modeli)
    names = [f"{m}/{q}" if len(runs) > 1 else q for m, a in runs for q in a[ids[0]]]
    F = logit(np.array([[v for _, a in runs for v in a[i].values()] for i in ids]))
    y = np.array([labels[i]["delta"] > 0.25 for i in ids])
    ql = np.array([labels[i]["q_large"] for i in ids])
    qs = np.array([labels[i]["q_small"] for i in ids])
    group = np.array([questions[row[i]]["group"] for i in ids])
    X = emb[[row[i] for i in ids]]
    n = len(ids)
    v1 = [j for j, nm in enumerate(names) if nm.split("/")[-1] in V1]
    print(f"{args.splits}: {n} pytań, {len(names)} cech z {len(runs)} plików; COMPLEX {y.mean():.1%}; zewnętrzna CV po grupach (5), wybór cech wewnętrzną CV na części uczącej; test nie jest używany\n")

    def knn_oof(idx: np.ndarray) -> np.ndarray:
        out = np.zeros(len(idx))
        for a, b in GroupKFold(n_splits=5).split(idx, groups=group[idx]):
            out[b] = knn_score(X[idx[b]] @ X[idx[a]].T, y[idx[a]].astype(float), K)
        return out

    def zone_auc(k: np.ndarray, feats: np.ndarray, yy: np.ndarray, gg: np.ndarray) -> float:
        """AUROC w strefie dla LR(kNN + cechy) liczony wewnętrzną CV (wynik do wyboru cech)."""
        s = np.zeros(len(yy))
        A = np.column_stack([logit(k), feats])
        for a, b in GroupKFold(n_splits=5).split(A, yy, gg):
            s[b] = LogisticRegression(C=args.C, max_iter=3000).fit(A[a], yy[a]).decision_function(A[b])
        z = in_zone(k)
        return roc_auc_score(yy[z], s[z])

    def greedy(k: np.ndarray, Ftr: np.ndarray, yy: np.ndarray, gg: np.ndarray) -> list[int]:
        chosen: list[int] = []
        best = zone_auc(k, np.zeros((len(yy), 0)), yy, gg)
        while len(chosen) < args.max_features:
            cand = [(zone_auc(k, Ftr[:, chosen + [j]], yy, gg), j) for j in range(Ftr.shape[1]) if j not in chosen]
            auc, j = max(cand)
            if auc - best < args.min_gain:
                break
            chosen.append(j)
            best = auc
        return chosen

    def top_single(k: np.ndarray, Ftr: np.ndarray, yy: np.ndarray, gg: np.ndarray) -> list[int]:
        """Pytania o największym zysku pojedynczo (wewnętrzna CV): stabilniejsza alternatywa dla wyboru zachłannego."""
        gains = [zone_auc(k, Ftr[:, [j]], yy, gg) for j in range(Ftr.shape[1])]
        return list(np.argsort(gains)[::-1][: args.top])

    methods = ["kNN", f"kNN + v1 ({len(v1)})", f"kNN + wszystkie ({len(names)}), C={args.C}", f"kNN + wszystkie, C={args.C / 10:g}", "kNN + wybór zachłanny", "GBM: kNN + wszystkie", "GBM: sam kNN", f"kNN + {args.top} najlepszych pojedynczo", f"GBM: kNN + {args.top} najlepszych"]
    scores = {m: np.zeros(n) for m in methods}
    knn_all = np.zeros(n)
    picked: list[list[str]] = []
    for fold, (tr, te) in enumerate(GroupKFold(n_splits=5).split(X, y, group)):
        k_tr = knn_oof(tr)
        k_te = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)
        knn_all[te] = k_te
        sel = greedy(k_tr, F[tr], y[tr], group[tr])
        top = top_single(k_tr, F[tr], y[tr], group[tr])
        picked.append([names[j] for j in sel])
        print(f"część {fold + 1}: {args.top} najlepszych pojedynczo {[names[j] for j in top]}", flush=True)
        print(f"część {fold + 1}: wybrane {picked[-1]}", flush=True)
        feats = {
            methods[0]: [],
            methods[1]: v1,
            methods[2]: list(range(len(names))),
            methods[3]: list(range(len(names))),
            methods[4]: sel,
            methods[7]: top,
        }
        for m, cols in feats.items():
            a = np.column_stack([logit(k_tr), F[tr][:, cols]])
            b = np.column_stack([logit(k_te), F[te][:, cols]])
            C = args.C / 10 if m == methods[3] else args.C
            scores[m][te] = LogisticRegression(C=C, max_iter=5000).fit(a, y[tr]).decision_function(b)
        gbm = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=SEED)
        scores[methods[5]][te] = gbm.fit(np.column_stack([logit(k_tr), F[tr]]), y[tr]).predict_proba(np.column_stack([logit(k_te), F[te]]))[:, 1]
        scores[methods[8]][te] = gbm.fit(np.column_stack([logit(k_tr), F[tr][:, top]]), y[tr]).predict_proba(np.column_stack([logit(k_te), F[te][:, top]]))[:, 1]
        scores[methods[6]][te] = gbm.fit(logit(k_tr)[:, None], y[tr]).predict_proba(logit(k_te)[:, None])[:, 1]  # kontrola: czy zysk GBM bierze się z nieliniowości samego kNN

    z = in_zone(knn_all)
    if args.dump:
        np.savez(args.dump, ids=np.array(ids), y=y, ql=ql, qs=qs, knn=knn_all, **{m: s for m, s in scores.items()})
    print("\npojedyncze cechy w strefie (poza próbką): AUROC samej cechy (>0,5 = wyższa wartość → COMPLEX) i zysk kNN + cecha względem kNN")
    single = []
    for j, nm in enumerate(names):
        s = np.zeros(n)
        for tr, te in GroupKFold(n_splits=5).split(X, y, group):
            k_tr = knn_oof(tr)
            k_te = knn_score(X[te] @ X[tr].T, y[tr].astype(float), K)
            s[te] = LogisticRegression(C=args.C, max_iter=3000).fit(np.column_stack([logit(k_tr), F[tr, j]]), y[tr]).decision_function(np.column_stack([logit(k_te), F[te, j]]))
        single.append((roc_auc_score(y[z], s[z]) - roc_auc_score(y[z], scores["kNN"][z]), roc_auc_score(y[z], F[z, j]), nm))
    for gain, auc, nm in sorted(single, reverse=True):
        print(f"  {nm:40s} AUROC {auc:.3f}   zysk {gain:+.3f}")

    from collections import Counter

    print("\nczęstość wyboru (na 5 części):", ", ".join(f"{nm} {c}" for nm, c in Counter(x for p in picked for x in p).most_common()))

    rng = np.random.default_rng(SEED)
    for mask, title in ((np.ones(n, dtype=bool), "wszystkie pytania"), (z, f"strefa niepewności kNN {ZONE[0]}–{ZONE[1]}")):
        idx = np.flatnonzero(mask)
        bs = [b for b in (idx[rng.integers(0, len(idx), len(idx))] for _ in range(BOOT)) if 0 < y[b].sum() < len(b)]
        res = {m: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs[b], rng).mean()) for b in bs]) for m, s in scores.items()}
        print(f"\n=== {title}: {mask.sum()} pytań, COMPLEX {y[mask].mean():.1%} ===")
        print(f"{'metoda':34s} {'AUROC [95% CI]':24s} {'APGR [95% CI]':24s}")
        for m, a in res.items():
            print(f"{m:34s} {ci(a[:, 0]):24s} {ci(a[:, 1]):24s}")
        for m in methods[1:]:
            d = res[m] - res["kNN"]
            print(f"  zysk {m} − kNN: AUROC {ci(d[:, 0], True)}, APGR {ci(d[:, 1], True)}")
        d = res["kNN + wybór zachłanny"] - res[methods[1]]
        print(f"  wybór zachłanny − v1: AUROC {ci(d[:, 0], True)}, APGR {ci(d[:, 1], True)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Warstwa 3 na train: wybór pytań modelu decyzyjnego (zachłanny, zagnieżdżona CV po grupach) i porównanie z v1, regresją na wszystkich i GBM.")
    p.add_argument("inputs", nargs="+", help="pliki z eval/layer3_systemone.py (kilka = cechy kilku modeli)")
    p.add_argument("--splits", nargs="+", default=["train"])
    p.add_argument("--C", type=float, default=1.0)
    p.add_argument("--max-features", type=int, default=8)
    p.add_argument("--dump", default="", help="zapis wyników poza próbką (.npz) do dalszych analiz")
    p.add_argument("--top", type=int, default=8, help="liczba pytań w wariancie „najlepsze pojedynczo”")
    p.add_argument("--min-gain", type=float, default=0.002)
    main(p.parse_args())
