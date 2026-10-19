# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scikit-learn"]
# ///
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyze_keywords import COMPLEX_CANDIDATES, SIMPLE_CANDIDATES  # noqa: E402

FEATURE_NAMES = [
    "log znaki",
    "log nowe linie",
    "``` bloki",
    "udział cyfr",
    "znaki ?",
    "kod-podobne",
    "URL",
    "słowa COMPLEX",
    "słowa SIMPLE",
]
CODE_RE = re.compile(r"\b(def|class|function|import|return|void|int)\b|[{};]")
COMPLEX_PHRASES = [w for w, _ in COMPLEX_CANDIDATES]
SIMPLE_PHRASES = [w for w, _ in SIMPLE_CANDIDATES]
_COMPLEX_RE = [re.compile(rf"\b{re.escape(w)}\b") for w in COMPLEX_PHRASES]
_SIMPLE_RE = [re.compile(rf"\b{re.escape(w)}\b") for w in SIMPLE_PHRASES]


def features(text: str) -> list[float]:
    low = text.lower()
    return [
        math.log1p(len(text)),
        math.log1p(text.count("\n")),
        float(text.count("```")),
        sum(c.isdigit() for c in text) / max(len(text), 1),
        float(text.count("?")),
        float(bool(CODE_RE.search(text))),
        float("http" in low),
        float(sum(bool(r.search(low)) for r in _COMPLEX_RE)),
        float(sum(bool(r.search(low)) for r in _SIMPLE_RE)),
    ]


def export_spec(mean: np.ndarray, scale: np.ndarray, coef: np.ndarray, intercept: float, meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "feature_names": FEATURE_NAMES,
        "complex_phrases": COMPLEX_PHRASES,
        "simple_phrases": SIMPLE_PHRASES,
        "mean": [float(x) for x in mean],
        "scale": [float(x) for x in scale],
        "coef": [float(x) for x in coef],
        "intercept": float(intercept),
        **meta,
    }
