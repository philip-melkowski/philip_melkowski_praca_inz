# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "matplotlib"]
# ///
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, GRID, SEED, knn_score, pgr_curve, read  # noqa: E402

OUT = Path(__file__).parent.parent / "docs" / "figures" / "pgr_cal.png"


def main() -> None:
    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    labels = {r["id"]: r for r in read("labels.jsonl")}
    ids = [q["id"] for q in questions if q["id"] in labels]
    X = emb[[row[i] for i in ids]]
    meta = [labels[i] for i in ids]
    split = np.array([m["split"] for m in meta])
    y = np.array([m["label"] == "COMPLEX" for m in meta])
    delta = np.array([m["delta"] for m in meta])
    ql = np.array([m["q_large"] for m in meta])
    qs = np.array([m["q_small"] for m in meta])
    tokens = np.array([questions[row[i]]["tokens"] for i in ids], dtype=float)
    source = np.array([m["source"] for m in meta])
    tr, ca = split == "train", split == "cal"
    rng = np.random.default_rng(SEED)
    prior = {s: y[tr & (source == s)].mean() for s in set(source) if (tr & (source == s)).any()}
    scores = {
        "oracle (prawdziwe Δ)": delta[ca],
        "kNN na embeddingach (k=20)": knn_score(X[ca] @ X[tr].T, y[tr].astype(float), 20),
        "samo źródło": np.array([prior.get(s, y[tr].mean()) for s in source[ca]]),
        "sama długość": np.log(tokens[ca]),
    }
    fig, ax = plt.subplots(figsize=(7, 4.6))
    styles = {"oracle (prawdziwe Δ)": ("#2a9d8f", "--"), "kNN na embeddingach (k=20)": ("#e76f51", "-"), "samo źródło": ("#264653", "-"), "sama długość": ("#8d99ae", "-")}
    for name, s in scores.items():
        curve = np.mean([pgr_curve(s, ql[ca], qs[ca], np.random.default_rng(SEED + k)) for k in range(20)], axis=0)
        color, ls = styles[name]
        ax.plot(GRID * 100, curve, label=f"{name} (APGR {curve.mean():.2f})", color=color, ls=ls, lw=2)
    ax.plot([0, 100], [0, 1], color="#bbb", lw=1.5, label="losowy (APGR 0,50)")
    ax.set_xlabel("udział zapytań wysłanych do dużego modelu [%]")
    ax.set_ylabel("PGR: odzyskana część przewagi dużego modelu")
    ax.set_title("Jakość a koszt routingu, zbiór kalibracyjny (n=859)")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160)
    print(OUT)


if __name__ == "__main__":
    main()
