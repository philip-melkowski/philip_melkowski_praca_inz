# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).parent.parent
DATASETS_DIR = ROOT / "data" / "datasets"


def main(task: str, key_path: str) -> None:
    text = Path(task).read_text(encoding="utf-8")
    ratings: dict[int, int] = {}
    for m in re.finditer(r"^## (\d+)\b.*?\*\*Ocena:\*\*[ \t]*(\d)?", text, re.MULTILINE | re.DOTALL):
        if m.group(2):
            ratings[int(m.group(1))] = int(m.group(2))
    key = {k["n"]: k for k in json.loads(Path(key_path).read_text(encoding="utf-8"))}
    pro: dict[tuple[str, str, int], int] = {}
    pro_path = DATASETS_DIR / "judge_open_pro.jsonl"
    if pro_path.exists():
        with pro_path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                for s in r["scores"]:
                    pro[(r["id"], s["model"], s["sample"])] = s["score"]

    ns = sorted(n for n in ratings if n in key)
    print(f"ocenionych odpowiedzi: {len(ns)} z {len(key)}")
    if len(ns) < 10:
        raise SystemExit("za mało ocen (wpisz liczby 1–5 po „Ocena:” w pliku zadania)")
    human = np.array([ratings[n] for n in ns])
    for name, judge in (("Gemini 3.8 Flash", np.array([key[n]["judge_score"] for n in ns])),):
        report(name, human, judge)
    both = [n for n in ns if (key[n]["id"], key[n]["model"], key[n]["sample"]) in pro]
    if len(both) >= 10:
        report(f"Gemini 3.1 Pro (tylko {len(both)} wspólnych)", np.array([ratings[n] for n in both]), np.array([pro[(key[n]["id"], key[n]["model"], key[n]["sample"])] for n in both]))
    big = np.array([key[n]["model"].startswith("Qwen/") for n in ns])
    print(f"\nśrednia oceny człowieka: duży {human[big].mean():.2f} (n={big.sum()}), mały {human[~big].mean():.2f} (n={(~big).sum()})")


def report(name: str, human: np.ndarray, judge: np.ndarray) -> None:
    print(f"\nczłowiek vs {name}:")
    print(f"  identyczne {np.mean(human == judge):.1%}, ±1 {np.mean(abs(human - judge) <= 1):.1%}, Spearman {spearmanr(human, judge)[0]:.3f}")
    print(f"  średnia: człowiek {human.mean():.2f}, sędzia {judge.mean():.2f} (różnica sędzia − człowiek {np.mean(judge - human):+.2f})")
    low = (human <= 2) == (judge <= 2)
    print(f"  zgodność „zła odpowiedź” (ocena ≤ 2 vs > 2): {np.mean(low):.1%}")


if __name__ == "__main__":
    kdir = ROOT / "docs" / "kontrola_ludzka"
    main(sys.argv[1] if len(sys.argv) > 1 else str(kdir / "zadanie.md"), sys.argv[2] if len(sys.argv) > 2 else str(kdir / "klucz.json"))
