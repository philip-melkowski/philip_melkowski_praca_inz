# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
"""Parametry warstwy 3 dla RouterService (DF, plik `decider_path`): regresja logistyczna na logit(kNN) i logitach
odpowiedzi modelu decyzyjnego, uczona tylko na train (kNN dla train z walidacji krzyżowej po grupach, jak w
`layer3_systemone_cal.py`). Cal i test nie są używane."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from layer3_systemone_cal import K, ZONE, load, logit  # noqa: E402
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    l3 = load(args.l3)
    question_set = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    names = list(question_set)
    tr = [i for i in l3 if i in labels and labels[i]["split"] == "train"]
    assert all(set(l3[i]["answers"]) == set(names) for i in tr), "plik L3 ma inne pytania niż zestaw"

    y = np.array([labels[i]["delta"] > 0.25 for i in tr])
    X = emb[[row[i] for i in tr]]
    N = logit(np.array([[l3[i]["answers"][n] for n in names] for i in tr]))
    groups = np.array([questions[row[i]]["group"] for i in tr])
    knn = np.zeros(len(tr))
    for a, b in GroupKFold(n_splits=5).split(X, groups=groups):
        knn[b] = knn_score(X[b] @ X[a].T, y[a].astype(float), K)

    m = LogisticRegression(C=1.0, max_iter=3000).fit(np.column_stack([logit(knn), N]), y)
    coef = m.coef_[0]
    params = {
        "model": args.model,
        "questions": question_set,
        "intercept": float(m.intercept_[0]),
        "knn_weight": float(coef[0]),
        "weights": {n: float(w) for n, w in zip(names, coef[1:], strict=True)},
        "zone_low": ZONE[0],
        "zone_high": ZONE[1],
        "timeout_seconds": args.timeout,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"train: {len(tr)} pytań, model {args.model}, zapisano {args.out}")
    print(f"wyraz wolny {params['intercept']:+.3f}, kNN {params['knn_weight']:+.3f}")
    for n, w in params["weights"].items():
        print(f"  {n:20s} {w:+.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--l3", required=True, help="odpowiedzi modelu decyzyjnego na train (layer3_systemone_*.jsonl)")
    p.add_argument("--questions", default=str(Path(__file__).parent / "layer3_questions" / "v1.json"))
    p.add_argument("--model", required=True, help="nazwa modelu decyzyjnego w DF")
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--out", required=True)
    main(p.parse_args())
