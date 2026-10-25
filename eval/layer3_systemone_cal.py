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
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, knn_score, pgr_curve, read  # noqa: E402

K = 20
BOOT = 1000
ZONE = (0.20, 0.45)
KNN_THRESHOLD = 0.3
SERIOUS = 0.5


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def ci(a: np.ndarray, signed: bool = False) -> str:
    f = "+.3f" if signed else ".3f"
    return f"{a.mean():{f}} [{np.percentile(a, 2.5):{f}},{np.percentile(a, 97.5):{f}}]"


def load(path: str) -> dict[str, dict[str, float]]:
    with Path(path).open(encoding="utf-8") as f:
        return {r["id"]: r for r in (json.loads(line) for line in f if line.strip())}


def main(args: argparse.Namespace) -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    l3_train, l3_cal = load(args.train), load(args.cal)
    tr = [i for i in l3_train if i in labels and labels[i]["split"] == "train"]
    te = [i for i in l3_cal if i in labels and labels[i]["split"] == "cal"]
    names = list(l3_train[tr[0]]["answers"])
    assert names == list(l3_cal[te[0]]["answers"]), "różne zestawy pytań w train i cal"
    expected = sum(1 for i in labels.values() if i["split"] == "cal")
    print(f"train: {len(tr)} pytań (uczenie), cal: {len(te)} z {expected} pytań z etykietami (pomiar); test nie jest używany")

    def arrays(ids: list[str], l3: dict[str, dict[str, float]]) -> tuple[np.ndarray, ...]:
        y = np.array([labels[i]["delta"] > 0.25 for i in ids])
        d = np.array([labels[i]["delta"] for i in ids])
        ql = np.array([labels[i]["q_large"] for i in ids])
        qs = np.array([labels[i]["q_small"] for i in ids])
        X = emb[[row[i] for i in ids]]
        N = logit(np.array([[l3[i]["answers"][n] for n in names] for i in ids]))
        return y, d, ql, qs, X, N

    y_tr, _, _, _, X_tr, N_tr = arrays(tr, l3_train)
    y, delta, ql, qs, X, N = arrays(te, l3_cal)
    g_tr = np.array([questions[row[i]]["group"] for i in tr])

    k_tr = np.zeros(len(tr))
    for a, b in GroupKFold(n_splits=5).split(X_tr, groups=g_tr):
        k_tr[b] = knn_score(X_tr[b] @ X_tr[a].T, y_tr[a].astype(float), K)
    knn = knn_score(X @ X_tr.T, y_tr.astype(float), K)

    sme = names.index("small_model_enough")
    m_all = LogisticRegression(C=1.0, max_iter=3000).fit(np.column_stack([logit(k_tr), N_tr]), y_tr)
    m_sme = LogisticRegression(C=1.0, max_iter=3000).fit(np.column_stack([logit(k_tr), N_tr[:, sme]]), y_tr)
    m_nim = LogisticRegression(C=1.0, max_iter=3000).fit(N_tr, y_tr)
    comb = m_all.predict_proba(np.column_stack([logit(knn), N]))[:, 1]
    zone = (knn >= ZONE[0]) & (knn <= ZONE[1])
    routed = np.where(zone, comb, knn)
    scores = {
        "kNN": knn,
        "nimble (8)": m_nim.predict_proba(N)[:, 1],
        "small_model_enough (odwr.)": -N[:, sme],
        "kNN + small_model_enough": m_sme.predict_proba(np.column_stack([logit(knn), N[:, sme]]))[:, 1],
        "kNN + nimble (8)": comb,
        "router ze strefą": routed,
    }
    sec = np.array([l3_cal[i]["seconds"] for i in te])
    print(f"COMPLEX {y.mean():.1%}; w strefie {ZONE[0]}–{ZONE[1]}: {zone.sum()} pytań ({zone.mean():.1%}, G4); czas żądania p50 {np.median(sec):.2f} s, p90 {np.percentile(sec, 90):.2f} s (G5, Mac 16 GB, niemiarodajne)\n")

    rng = np.random.default_rng(SEED)

    def report(mask: np.ndarray, title: str, keys: list[str]) -> dict[str, np.ndarray]:
        idx = np.flatnonzero(mask)
        bs = [b for b in (idx[rng.integers(0, len(idx), len(idx))] for _ in range(BOOT)) if 0 < y[b].sum() < len(b)]
        res = {k: np.array([(roc_auc_score(y[b], scores[k][b]), pgr_curve(scores[k][b], ql[b], qs[b], rng).mean()) for b in bs]) for k in keys}
        print(f"=== {title}: {mask.sum()} pytań, COMPLEX {y[mask].mean():.1%} ===")
        print(f"{'metoda':28s} {'AUROC [95% CI]':24s} {'APGR [95% CI]':24s}")
        for k, a in res.items():
            print(f"{k:28s} {ci(a[:, 0]):24s} {ci(a[:, 1]):24s}")
        return res

    keys = ["kNN", "nimble (8)", "small_model_enough (odwr.)", "kNN + small_model_enough", "kNN + nimble (8)"]
    res = report(zone, "STREFA (miara główna G1)", keys)
    d = res["kNN + nimble (8)"] - res["kNN"]
    lo = np.percentile(d[:, 0], 2.5)
    print(f"  G1: zysk AUROC kNN + nimble − kNN w strefie: {ci(d[:, 0], True)}  →  {'GO dla G1' if lo > 0 else 'NO-GO dla G1'} (dolna granica {'>' if lo > 0 else '≤'} 0)")
    print(f"  zysk APGR w strefie: {ci(d[:, 1], True)}\n")

    res = report(np.ones(len(te), dtype=bool), "CAŁY CAL (dodatkowo)", [*keys, "router ze strefą"])
    for a_ in ("kNN + nimble (8)", "router ze strefą"):
        d = res[a_] - res["kNN"]
        print(f"  zysk {a_} − kNN: AUROC {ci(d[:, 0], True)}, APGR {ci(d[:, 1], True)}")

    share = (knn >= KNN_THRESHOLD).mean()
    print(f"\n=== G3: poważne błędy (Δ > {SERIOUS} wysłane do małego), przy tym samym udziale dużego co kNN z progiem {KNN_THRESHOLD}: {share:.1%} ===")
    n_large = int(round(share * len(te)))

    def serious(s: np.ndarray, b: np.ndarray) -> float:
        small = np.argsort(-s[b], kind="stable")[n_large:]
        return float((delta[b][small] > SERIOUS).mean() * len(small) / len(b))

    base = np.arange(len(te))
    bs = [rng.integers(0, len(te), len(te)) for _ in range(BOOT)]
    e_knn = np.array([serious(knn, b) for b in bs])
    e_rt = np.array([serious(routed, b) for b in bs])
    print(f"  kNN: {serious(knn, base):.1%} wszystkich pytań; router ze strefą: {serious(routed, base):.1%}; różnica (router − kNN): {ci(e_rt - e_knn, True)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Warstwa 3: jednorazowy pomiar na cal według protokołu z dziennika (wpis 91).")
    p.add_argument("--train", default=str(DATASETS_DIR / "layer3_systemone_nimble_v1.jsonl"))
    p.add_argument("--cal", default=str(DATASETS_DIR / "layer3_systemone_nimble_v1_cal.jsonl"))
    main(p.parse_args())
