# /// script
# requires-python = ">=3.11"
# ///
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CHECKED = ["CLAUDE.md", "docs/STATUS.md", "docs/INDEX.md", "docs/DECYZJE.md", "data/README.md", "eval/README.md"]
TOP_DIRS = ("docs/", "eval/", "data/", "tools/", "archiwum/")
FILE_SUFFIXES = (".md", ".py", ".sh", ".js", ".pdf")  # bez plików danych (.npz, .json…): leżą w data/datasets/ tylko na jednym z komputerów
STATUS_MAX_LINES = 100


def index_covers(index: str, path: Path) -> bool:
    rel = path.relative_to(DOCS)
    names = [rel.as_posix(), path.name, *[p.as_posix() + "/" for p in rel.parents if p.as_posix() != "."]]
    return any(n in index for n in names)


def broken_paths(text: str) -> list[str]:
    names = {f.name for f in ROOT.rglob("*") if f.is_file() and ".venv" not in f.parts and ".git" not in f.parts}
    found: list[str] = []
    for token in re.findall(r"`([^`\n]+)`", text):
        if " " in token or "*" in token or "<" in token or "…" in token or token.startswith("data/datasets/"):
            continue
        if token.startswith(TOP_DIRS):
            if not (ROOT / token).exists():
                found.append(token)
        elif "/" not in token and token.endswith(FILE_SUFFIXES) and token not in names:
            found.append(token)
    return found


def main() -> int:
    problems: list[str] = []
    index = (DOCS / "INDEX.md").read_text(encoding="utf-8")
    for f in sorted(DOCS.rglob("*")):
        if f.is_file() and f.name != "INDEX.md" and not f.name.startswith(".") and "__pycache__" not in f.parts and not index_covers(index, f):
            problems.append(f"brak w INDEX.md: {f.relative_to(ROOT)}")
    for name in CHECKED:
        problems += [f"{name}: nie istnieje {p}" for p in broken_paths((ROOT / name).read_text(encoding="utf-8"))]
    status = (DOCS / "STATUS.md").read_text(encoding="utf-8")
    if status.count("\n") > STATUS_MAX_LINES:
        problems.append(f"STATUS.md ma {status.count(chr(10))} linii (limit {STATUS_MAX_LINES})")
    last = max(int(n) for n in re.findall(r"^### (\d+)\.", (DOCS / "DZIENNIK.md").read_text(encoding="utf-8"), re.M))
    declared = re.search(r"Ostatni wpis dziennika: \*\*(\d+)\*\*", status)
    if not declared or int(declared.group(1)) != last:
        problems.append(f"STATUS.md: ostatni wpis dziennika to {last}, a w pliku {declared.group(1) if declared else 'brak'}")
    print("\n".join(problems) if problems else "dokumentacja spójna")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
