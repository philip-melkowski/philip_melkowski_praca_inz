# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEFAULT = ROOT / "docs" / "kontrola_ludzka" / "zadanie_warstwowe.md"
HEADER = re.compile(r"^## (\d+)\s*$", re.MULTILINE)
RATING = re.compile(r"(\*\*Ocena:\*\*)[ \t]*(\S*)")


def blocks(text: str) -> list[tuple[int, int, int]]:
    heads = list(HEADER.finditer(text))
    return [(int(h.group(1)), h.start(), heads[i + 1].start() if i + 1 < len(heads) else len(text)) for i, h in enumerate(heads)]


def current(block: str) -> str:
    m = RATING.search(block)
    return m.group(2) if m else ""


def main(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    spans = blocks(text)
    i = next((k for k, (_, a, b) in enumerate(spans) if not current(text[a:b])), len(spans))
    while 0 <= i < len(spans):
        n, a, b = spans[i]
        block = text[a:b]
        shown = RATING.sub("", block).replace("\n---", "").strip()
        done = sum(1 for _, x, y in spans if current(text[x:y]) not in ("",))
        print(f"\n{'=' * 70}\n[{done}/{len(spans)} ocenionych]\n{shown}\n{'-' * 70}")
        ans = input("Ocena 1-5, 0 = nie umiem ocenić, b = wstecz, q = wyjście: ").strip().lower()
        if ans == "q":
            break
        if ans == "b":
            i = max(i - 1, 0)
            continue
        if ans not in {"0", "1", "2", "3", "4", "5"}:
            print("Wpisz 0-5, b lub q.")
            continue
        value = "-" if ans == "0" else ans
        new_block = RATING.sub(lambda m: f"{m.group(1)} {value}", block, count=1)
        text = text[:a] + new_block + text[b:]
        path.write_text(text, encoding="utf-8")
        spans = blocks(text)
        i += 1
    left = sum(1 for _, a, b in spans if not current(text[a:b]))
    print(f"\nZapisano w {path.name}. Do oceny zostało: {left}.")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT)
