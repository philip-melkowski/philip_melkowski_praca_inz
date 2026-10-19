import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

DATASETS_DIR = Path(__file__).parent / "datasets"
QUESTIONS = DATASETS_DIR / "questions_v2_split.jsonl"
ANSWERS = DATASETS_DIR / "answers.jsonl"
OUT = DATASETS_DIR / "scores_gold.jsonl"
CODE_TIMEOUT = 10
NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def to_number(text: str) -> float | None:
    m = NUM.search(text.replace("$", "").replace("\\", ""))
    if not m:
        return None
    try:
        return float(m.group().replace(",", "").rstrip("."))
    except ValueError:
        return None


def score_gsm8k(content: str, gold: dict[str, Any]) -> bool | None:
    marks = list(re.finditer(r"answer\s*[:：]?\s*\**\s*(.*)", content, re.IGNORECASE))
    got = to_number(marks[-1].group(1)) if marks else None
    if got is None:
        nums = NUM.findall(content)
        got = to_number(nums[-1]) if nums else None
    want = to_number(str(gold["answer"]))
    if got is None or want is None:
        return None
    return abs(got - want) < 1e-6


def score_mmlu(content: str, gold: dict[str, Any]) -> bool | None:
    found = re.findall(r"(?:answer|option)[^A-Za-z\n]{0,12}(?:is\s*)?\**\(?([A-D])\b", content, re.IGNORECASE)
    if not found:
        found = re.findall(r"^[\s*#>_-]*\(?([A-D])[.):]?(?:\*\*)?(?:\s|$)", content, re.MULTILINE)
    if not found:
        found = re.findall(r"\*\*\(?([A-D])(?:[.):]|\*\*|\s)", content)
    return found[-1].upper() == gold["answer"] if found else None


def norm(text: str) -> str:
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return " ".join(w for w in text.split() if w not in {"a", "an", "the"})


def score_triviaqa(content: str, gold: dict[str, Any]) -> bool | None:
    got = f" {norm(content)} "
    if got.strip() == "":
        return None
    return any(a and f" {a} " in got for a in map(norm, gold["answers"]))


def score_humaneval(content: str, gold: dict[str, Any], prompt: str) -> bool | None:
    blocks = re.findall(r"```(?:python|py)?\n(.*?)```", content, re.DOTALL)
    if not blocks:
        return None
    imports = "\n".join(line for line in prompt.splitlines() if line.startswith(("import ", "from ")))
    program = f"{imports}\n\n{blocks[-1]}\n\n{gold['test']}\n\ncheck({gold['entry_point']})\n"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "run.py"
        path.write_text(program, encoding="utf-8")
        try:
            r = subprocess.run(
                [sys.executable, "-I", str(path)],
                cwd=tmp,
                capture_output=True,
                timeout=CODE_TIMEOUT,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return False
    return r.returncode == 0


def main() -> None:
    questions: dict[str, dict[str, Any]] = {}
    with QUESTIONS.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["type"] == "gold":
                questions[r["id"]] = r
    with ANSWERS.open(encoding="utf-8") as f:
        answers = [a for a in map(json.loads, f) if a["id"] in questions]

    def score(a: dict[str, Any]) -> dict[str, Any]:
        q = questions[a["id"]]
        src, content, gold = q["source"], a["content"], q["gold"]
        ok = {
            "gsm8k": lambda: score_gsm8k(content, gold),
            "mmlu": lambda: score_mmlu(content, gold),
            "triviaqa": lambda: score_triviaqa(content, gold),
            "humaneval": lambda: score_humaneval(content, gold, q["prompt"]),
        }[src]()
        return {
            "id": a["id"],
            "model": a["model"],
            "sample": a["sample"],
            "source": src,
            "correct": ok,
            "truncated": a.get("finish_reason") == "length",
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        scored = list(pool.map(score, answers))
    OUT.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in scored) + "\n", encoding="utf-8")

    table: dict[tuple[str, str], list[bool | None]] = defaultdict(list)
    for s in scored:
        table[(s["source"], s["model"])].append(s["correct"])
    print(f"{'źródło':10s} {'model':24s} {'n':>5s} {'poprawne':>9s} {'błędne':>7s} {'nieczytelne':>12s}")
    for (src, model), v in sorted(table.items()):
        print(f"{src:10s} {model:24s} {len(v):5d} {sum(x is True for x in v) / len(v):9.1%} {sum(x is False for x in v):7d} {sum(x is None for x in v):12d}")


if __name__ == "__main__":
    main()
