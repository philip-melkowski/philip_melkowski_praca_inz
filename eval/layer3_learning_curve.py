# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, read  # noqa: E402

K = 20
SIZES = (10, 25, 50, 100, 200, 500, 1000, 1500)
REPEATS = 100
EVAL_SHARE = 0.3


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    with Path(args.input).open(encoding="utf-8") as f:
        l3 = {r["id"]: r for r in (json.loads(line) for line in f if line.strip())}
    ids = [i for i in l3 if i in labels and labels[i]["split"] == "train"]
    names = list(l3[ids[0]]["answers"])
    y = np.array([labels[i]["delta"] > 0.25 for i in ids])
    X = emb[[row[i] for i in ids]]
    N = logit(np.array([[l3[i]["answers"][n] for n in names] for i in ids]))
    group = np.array([questions[row[i]]["group"] for i in ids])
    sme = names.index(args.zero_shot) if args.zero_shot in names else 0
    sign = -1.0 if args.zero_shot == "small_model_enough" else 1.0
    groups = np.unique(group)
    rng = np.random.default_rng(SEED)
    print(f"train: {len(ids)} pytań, {len(groups)} grup; w każdym powtórzeniu {EVAL_SHARE:.0%} grup odłożone do oceny, etykiety losowane z reszty; {REPEATS} powtórzeń")
    print(f"zero-shot: {args.zero_shot} (0 etykiet; kierunek {'odwrócony' if sign < 0 else 'wprost'})\n")
    print(f"{'etykiet':>8s}  {'kNN k=20':22s} {'LR na 8 cechach':22s} {'kNN + LR(8)':22s} {'zero-shot (0 etykiet)':22s}")
    for n_lab in SIZES:
        res: dict[str, list[float]] = {"knn": [], "lr": [], "both": [], "zs": []}
        for _ in range(REPEATS):
            ev_groups = rng.choice(groups, int(len(groups) * EVAL_SHARE), replace=False)
            ev = np.isin(group, ev_groups)
            pool = np.flatnonzero(~ev)
            if n_lab > len(pool):
                break
            lab = rng.choice(pool, n_lab, replace=False)
            if not 0 < y[lab].sum() < n_lab:
                continue
            e = np.flatnonzero(ev)
            k = min(K, n_lab)
            s_knn = knn_score(X[e] @ X[lab].T, y[lab].astype(float), k)
            m = LogisticRegression(C=1.0, max_iter=3000).fit(N[lab], y[lab])
            s_lr = m.decision_function(N[e])
            k_lab = knn_score(X[lab] @ X[lab].T, y[lab].astype(float), min(k + 1, n_lab))  # in-sample, includes self
            mb = LogisticRegression(C=1.0, max_iter=3000).fit(np.column_stack([logit(k_lab), N[lab]]), y[lab])
            s_both = mb.decision_function(np.column_stack([logit(s_knn), N[e]]))
            for key, s in (("knn", s_knn), ("lr", s_lr), ("both", s_both), ("zs", sign * N[e, sme])):
                res[key].append(roc_auc_score(y[e], s))
        if not res["knn"]:
            continue

        def fmt(a: list[float]) -> str:
            v = np.array(a)
            return f"{v.mean():.3f} [{np.percentile(v, 5):.3f},{np.percentile(v, 95):.3f}]"

        print(f"{n_lab:8d}  {fmt(res['knn']):22s} {fmt(res['lr']):22s} {fmt(res['both']):22s} {fmt(res['zs']):22s}")
    print("\n[przedziały: 5.–95. percentyl z powtórzeń, czyli zmienność losowania etykiet i podziału, nie przedział ufności]")
    print("uwaga: kNN + LR(8) uczony na wyniku kNN liczonym w próbce (z samym sobą), więc dla małej liczby etykiet jest przeszacowany po stronie uczenia")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Krzywa uczenia na train: ile etykiet potrzebuje kNN, żeby dogonić model decyzyjny zero-shot.")
    p.add_argument("input", help="plik z eval/layer3_systemone.py (train)")
    p.add_argument("--zero-shot", default="small_model_enough", help="pytanie użyte bez etykiet")
    main(p.parse_args())
