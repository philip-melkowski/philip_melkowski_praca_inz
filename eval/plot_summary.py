# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn", "matplotlib"]
# ///
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from router_baselines import DATASETS_DIR, knn_score, read  # noqa: E402

FIG = Path(__file__).parent.parent / "docs" / "figures"
NAMES = {
    "wildchat": "WildChat",
    "chatbot_arena": "Arena",
    "mt_bench": "MT-Bench",
    "mmlu": "MMLU",
    "triviaqa": "TriviaQA",
    "humaneval": "HumanEval",
    "llm_generated": "pytania Gemini",
    "gsm8k": "GSM8K",
}
INK, ACCENT, GREY = "#264653", "#e76f51", "#8d99ae"


def style(ax: plt.Axes) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", alpha=0.25)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    labels = read("labels.jsonl")
    by = defaultdict(list)
    for r in labels:
        by[r["source"]].append(r)
    order = sorted(by, key=lambda s: -sum(r["delta"] > 0.25 for r in by[s]) / len(by[s]))

    fig, ax = plt.subplots(figsize=(7, 4))
    share = [sum(r["delta"] > 0.25 for r in by[s]) / len(by[s]) * 100 for s in order]
    ax.barh([f"{NAMES[s]} (n={len(by[s])})" for s in order][::-1], share[::-1], color=ACCENT)
    for i, v in enumerate(share[::-1]):
        ax.text(v + 0.8, i, f"{v:.0f}%", va="center", fontsize=9, color=INK)
    ax.set_xlabel("pytania COMPLEX: duży model lepszy o więcej niż 1 punkt (skala 1–5) [%]")
    ax.set_title("Udział pytań COMPLEX wg źródła", color=INK)
    ax.set_xlim(0, 60)
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "complex_by_source.png", dpi=160)

    fig, ax = plt.subplots(figsize=(7, 4))
    ypos = np.arange(len(order))
    big = [st.mean(r["q_large"] for r in by[s]) for s in order]
    small = [st.mean(r["q_small"] for r in by[s]) for s in order]
    ax.barh(ypos + 0.2, small[::-1], height=0.38, color=GREY, label="mały (qwen3:8b)")
    ax.barh(ypos - 0.2, big[::-1], height=0.38, color=INK, label="duży (Qwen3.8-27B)")
    ax.set_yticks(ypos, [NAMES[s] for s in order][::-1])
    ax.set_xlabel("średnia jakość 0–1 (poprawność lub (ocena−1)/4)")
    ax.set_title("Jakość odpowiedzi obu modeli wg źródła", color=INK)
    ax.set_xlim(0, 1.05)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, fontsize=8, frameon=False)
    style(ax)
    fig.tight_layout()
    fig.savefig(FIG / "quality_by_source.png", dpi=160)

    questions = read("questions_v2_split.jsonl")
    emb = np.load(DATASETS_DIR / "embeddings_nomic.npy")
    row = {q["id"]: i for i, q in enumerate(questions)}
    pool = [r for r in labels if r["split"] in ("train", "cal")]
    X = emb[[row[r["id"]] for r in pool]]
    y = np.array([r["delta"] > 0.25 for r in pool], dtype=float)
    ql = np.array([r["q_large"] for r in pool])
    qs = np.array([r["q_small"] for r in pool])
    group = np.array([questions[row[r["id"]]]["group"] for r in pool])
    score = np.zeros(len(pool))
    for tr, te in GroupKFold(n_splits=5).split(X, groups=group):
        score[te] = knn_score(X[te] @ X[tr].T, y[tr], 20)
    ts = np.linspace(0, 1.01, 120)
    share = np.array([(score >= t).mean() * 100 for t in ts])
    qual = np.array([np.where(score >= t, ql, qs).mean() for t in ts])
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(share, qual, color=ACCENT, lw=2.2, label="router kNN (poza próbką)")
    ax.plot([0, 100], [qs.mean(), ql.mean()], color=GREY, lw=1.5, ls="--", label="losowy podział ruchu")
    for t in (0.2, 0.3, 0.4, 0.5):
        s, q = (score >= t).mean() * 100, np.where(score >= t, ql, qs).mean()
        ax.scatter([s], [q], color=INK, zorder=3)
        ax.annotate(f"próg {t}", (s, q), textcoords="offset points", xytext=(6, -12), fontsize=8, color=INK)
    ax.set_xlabel("udział zapytań wysłanych do dużego modelu [%]")
    ax.set_ylabel("średnia jakość odpowiedzi (0–1)")
    ax.set_title("Kompromis koszt–jakość i progi routera (train+cal, n=3010)", color=INK, fontsize=11)
    ax.set_xlim(0, 100)
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    style(ax)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "threshold_tradeoff.png", dpi=160)
    print("zapisano 3 wykresy w", FIG)


if __name__ == "__main__":
    main()
