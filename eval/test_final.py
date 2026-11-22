# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "scipy"]
# ///
"""Jednorazowa ocena zamrożonego routera na zbiorze test według `docs/PROTOKOL_TESTU_2026-11-22.md`.

R0 = heurystyki (próg 2) + kNN k=20 na zamrożonym indeksie; R1 = R0 + warstwa 3 (d1, parametry z pliku JSON jak w DF)
w strefie [0,20; 0,45). Wersja etykiet z `--labels` (v2: `labels.jsonl`, v3: `data/labels/labels_v3.jsonl`)."""

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import beta
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, SEED, cpt, group_bootstrap, knn_score, pgr_curve, read  # noqa: E402

ROOT = Path(__file__).parent.parent
K = 20
THR = 0.25
CRIT = 0.5
ZONE = (0.20, 0.45)
BOOT = 2000
GRID = tuple(round(0.05 * i, 2) for i in range(1, 20))


class Heuristics:
    """Wierna kopia `server/router/heuristics.py` z DF (punkty za frazy jako całe słowa, długość, cyfry, URL)."""

    def __init__(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        pts = data.get("points", {})
        self.complex = [re.compile(rf"\b{re.escape(v.lower())}\b") for v in data["complex_phrases"]]
        self.simple = [re.compile(rf"\b{re.escape(v.lower())}\b") for v in data["simple_phrases"]]
        self.p_complex = pts.get("complex_phrase", 1.0)
        self.p_simple = pts.get("simple_phrase", -1.0)
        self.p_url = pts.get("url", 1.0)
        self.length = pts.get("length", [{"chars": 400, "points": 1.0}, {"chars": 1500, "points": 1.0}])
        self.digits = pts.get("digits", {"over": 0.1, "points": -1.0})

    def points(self, text: str) -> float:
        low = text.lower()
        total = self.p_complex * sum(bool(p.search(low)) for p in self.complex)
        total += self.p_simple * sum(bool(p.search(low)) for p in self.simple)
        total += sum(s["points"] for s in self.length if len(text) > s["chars"])
        if self.digits is not None and sum(c.isdigit() for c in text) / max(len(text), 1) > self.digits["over"]:
            total += self.digits["points"]
        if "http" in low:
            total += self.p_url
        return total


def decider_score(params: dict[str, Any], answers: dict[str, float], knn: float) -> float:
    lg = lambda p: math.log(min(max(p, 1e-4), 1 - 1e-4) / (1 - min(max(p, 1e-4), 1 - 1e-4)))  # noqa: E731
    z = params["intercept"] + params["knn_weight"] * lg(knn) + sum(w * lg(answers[n]) for n, w in params["weights"].items())
    return 1 / (1 + math.exp(-z))


def upper(k: int, n: int, conf: float) -> float:
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def bonferroni_threshold(score: np.ndarray, bad: np.ndarray, target: float) -> float | None:
    order = np.argsort(score, kind="stable")
    cum = np.cumsum(bad[order])
    conf = 1 - 0.05 / len(GRID)
    best = None
    for f in GRID:
        n = round(f * len(score))
        if n >= 50 and upper(int(cum[n - 1]), n, conf) <= target:
            best = float(score[order][n - 1])
    return best


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main(args: argparse.Namespace) -> None:
    rng = np.random.default_rng(SEED)
    index = np.load(ROOT / args.index)
    heur = Heuristics(ROOT / args.heuristics)
    params = json.loads((ROOT / args.decider).read_text(encoding="utf-8"))
    print(f"indeks {args.index} ({sha(ROOT / args.index)}), heurystyki ({sha(ROOT / args.heuristics)}), warstwa 3 {args.decider} ({sha(ROOT / args.decider)})")
    print(f"etykiety: {args.labels} ({sha(ROOT / args.labels)})\n")

    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    with (ROOT / args.labels).open(encoding="utf-8") as f:
        labels = {r["id"]: r for r in map(json.loads, f)}
    test = [q for q in questions if q["split"] == "test" and q["id"] in labels]

    train_sources = [r["source"] for r in labels.values() if r["split"] in ("train", "cal")] + [
        r["source"] for r in read("labels_extra.jsonl") if r["id"] in {q["id"] for q in read("questions_extra_split.jsonl") if q["split"] == "extra_train"}
    ]
    train_y = [r["delta"] > THR for r in labels.values() if r["split"] in ("train", "cal")] + [
        r["delta"] > THR for r in read("labels_extra.jsonl") if r["id"] in {q["id"] for q in read("questions_extra_split.jsonl") if q["split"] == "extra_train"}
    ]
    src_rate: dict[str, float] = {}
    for s in set(train_sources):
        v = [y for y, ss in zip(train_y, train_sources, strict=True) if ss == s]
        src_rate[s] = float(np.mean(v))
    overall = float(np.mean(train_y))

    l3_answers: dict[str, dict[str, float]] = {}
    if args.decider_answers:
        with (DATASETS_DIR / args.decider_answers).open(encoding="utf-8") as f:
            l3_answers = {r["id"]: r["answers"] for r in map(json.loads, f) if "answers" in r}

    vec = np.asarray(index["vectors"], dtype=np.float32)
    vec = vec / np.linalg.norm(vec, axis=1, keepdims=True)
    lab = np.asarray(index["labels"], dtype=np.float32)

    def evaluate(qs: Sequence[dict[str, Any]], title: str, primary: bool) -> None:
        X = emb[[row[q["id"]] for q in qs]]
        knn = knn_score(X @ vec.T, lab, K)
        pts = np.array([heur.points(q["prompt"]) for q in qs])
        forced = pts >= 2
        r0 = np.where(forced, 1.0, knn)
        zone = (knn >= ZONE[0]) & (knn < ZONE[1]) & ~forced
        missing = [q["id"] for q, z in zip(qs, zone, strict=True) if z and q["id"] not in l3_answers]
        r1 = r0.copy()
        for i, q in enumerate(qs):
            if zone[i] and q["id"] in l3_answers:
                r1[i] = decider_score(params, l3_answers[q["id"]], float(knn[i]))
        y = np.array([labels[q["id"]]["delta"] > THR for q in qs])
        delta = np.array([labels[q["id"]]["delta"] for q in qs])
        ql = np.array([labels[q["id"]]["q_large"] for q in qs])
        qs_ = np.array([labels[q["id"]]["q_small"] for q in qs])
        g = np.array([str(q["group"]) for q in qs])
        length = np.log(np.array([q["tokens"] for q in qs], dtype=float))
        source = np.array([src_rate.get(q["source"], overall) for q in qs])
        scores = {"R0 (warstwy 1+2)": r0, "R1 (+ warstwa 3)": r1, "sama długość": length, "samo źródło": source, "idealny": delta}
        boots = [group_bootstrap(g, rng) for _ in range(BOOT)]
        boots = [b for b in boots if 0 < y[b].sum() < len(b)]
        res = {n: np.array([(roc_auc_score(y[b], s[b]), pgr_curve(s[b], ql[b], qs_[b], rng).mean()) for b in boots]) for n, s in scores.items()}
        print(f"=== {title}: {len(qs)} pytań, COMPLEX {y.mean():.1%}, heurystyki → duży {forced.mean():.1%}, strefa warstwy 3 {zone.mean():.1%} ===")
        if missing:
            print(f"  UWAGA: brak odpowiedzi warstwy 3 dla {len(missing)} pytań w strefie (R1 = R0 dla nich)")
        print(f"  jakość: zawsze duży {ql.mean():.3f}, zawsze mały {qs_.mean():.3f}")
        for n, s in scores.items():
            a = res[n]
            curve = pgr_curve(s, ql, qs_, rng)
            print(
                f"  {n:20s} AUROC {roc_auc_score(y, s):.3f} [{np.percentile(a[:, 0], 2.5):.3f}; {np.percentile(a[:, 0], 97.5):.3f}]"
                f"  APGR {curve.mean():.3f} [{np.percentile(a[:, 1], 2.5):.3f}; {np.percentile(a[:, 1], 97.5):.3f}]  CPT80 {cpt(curve, 0.8):.2f}"
            )
        verdict = {}
        for x, z, key in (("R0 (warstwy 1+2)", "sama długość", "cel 1"), ("R0 (warstwy 1+2)", "samo źródło", "cel 3"), ("R1 (+ warstwa 3)", "R0 (warstwy 1+2)", "R1 − R0")):
            d = res[x] - res[z]
            lo = np.percentile(d[:, 1], 2.5)
            verdict[key] = lo > 0
            print(
                f"  różnica {x} − {z}: APGR {d[:, 1].mean():+.3f} [{lo:+.3f}; {np.percentile(d[:, 1], 97.5):+.3f}]"
                f"  AUROC {d[:, 0].mean():+.3f} [{np.percentile(d[:, 0], 2.5):+.3f}; {np.percentile(d[:, 0], 97.5):+.3f}]"
            )
        auroc_r0 = roc_auc_score(y, r0)
        n_small = len(qs) // 2
        for n, s in (("R0", r0), ("R1", r1)):
            order = np.lexsort((rng.random(len(s)), s))
            small = np.zeros(len(s), dtype=bool)
            small[order[:n_small]] = True
            print(f"  {n}: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: {(small & (delta > CRIT)).mean():.1%} pytań")
        if primary:
            print(
                f"\n  CELE D22: (1) R0 > długość: {'TAK' if verdict['cel 1'] else 'NIE'}; (2) AUROC {auroc_r0:.3f} ≥ 0,64: "
                f"{'TAK' if auroc_r0 >= 0.64 else 'NIE'}; (3) R0 > źródło: {'TAK' if verdict['cel 3'] else 'nie wykazano'}; "
                f"C3 CPT80 {cpt(pgr_curve(r0, ql, qs_, rng), 0.8):.2f} ≤ 0,72: {'TAK' if cpt(pgr_curve(r0, ql, qs_, rng), 0.8) <= 0.72 else 'NIE'}"
            )
            print(f"  SUKCES GŁÓWNY (1 i 2): {'TAK' if verdict['cel 1'] and auroc_r0 >= 0.64 else 'NIE'}")
            print("\n  według źródła (R0):")
            for src in sorted({q["source"] for q in qs}):
                m = np.array([q["source"] == src for q in qs])
                if 0 < y[m].sum() < m.sum():
                    print(f"    {src:14s} n={m.sum():4d} COMPLEX {y[m].mean():5.1%} AUROC {roc_auc_score(y[m], r0[m]):.3f}")
        print()
        return

    in_dom = [q for q in test if not q["ood"]]
    out_dom = [q for q in test if q["ood"]]
    evaluate(in_dom, "TEST W DZIEDZINIE (cele)", True)
    evaluate(out_dom, "TEST POZA DZIEDZINĄ (C6, bez progu)", False)

    print("=== Progi z gwarancją (D20, Bonferroni): FIT = train + cal + extra_train (kNN z CV), sprawdzenie na teście w dziedzinie ===")
    fit_q = [q for q in questions if q["id"] in labels and q["split"] in ("train", "cal")]
    xq = [q for q in read("questions_extra_split.jsonl") if q["split"] == "extra_train"]
    xl = {r["id"]: r for r in read("labels_extra.jsonl")}
    xq = [q for q in xq if q["id"] in xl]
    xemb = np.load(DATASETS_DIR / "embeddings_extra_nomic.npy")
    xrow = {q["id"]: i for i, q in enumerate(read("questions_extra_split.jsonl"))}
    Xf = np.vstack([emb[[row[q["id"]] for q in fit_q]], xemb[[xrow[q["id"]] for q in xq]]])
    df_ = np.array([labels[q["id"]]["delta"] for q in fit_q] + [xl[q["id"]]["delta"] for q in xq])
    yf = df_ > THR
    gf = np.array([str(q["group"]) for q in fit_q] + [str(q["group"]) for q in xq])
    sf = np.zeros(len(yf))
    for a, b in GroupKFold(n_splits=5).split(Xf, groups=gf):
        sf[b] = knn_score(Xf[b] @ Xf[a].T, yf[a].astype(float), K)
    Xt = emb[[row[q["id"]] for q in in_dom]]
    st = knn_score(Xt @ vec.T, lab, K)
    dt = np.array([labels[q["id"]]["delta"] for q in in_dom])
    for name, bad_f, bad_t, targets in (("błąd krytyczny", df_ > CRIT, dt > CRIT, (0.10, 0.12, 0.15)), ("COMPLEX", yf, dt > THR, (0.25, 0.30))):
        for r in targets:
            t = bonferroni_threshold(sf, bad_f, r)
            if t is None:
                print(f"  {name} ≤ {r:.0%}: brak progu na FIT")
                continue
            sel = st <= t
            k, n = int(bad_t[sel].sum()), int(sel.sum())
            print(f"  {name} ≤ {r:.0%}: próg {t:.3f}; test: do małego {sel.mean():.1%}, błąd {k / max(n, 1):.1%} → {'spełniony' if n and k / n <= r else 'NIE'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", default="data/router/router_index_final.npz")
    p.add_argument("--heuristics", default="data/router_l1.json")
    p.add_argument("--decider", default="data/router/router_l3_d1_final.json")
    p.add_argument("--decider-answers", default="layer3_systemone_d1gpu_final_test.jsonl")
    p.add_argument("--labels", default="data/labels/labels_v3.jsonl")
    main(p.parse_args())
