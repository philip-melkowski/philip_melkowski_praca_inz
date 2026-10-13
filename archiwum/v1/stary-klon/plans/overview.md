# DeepFellow Router — przegląd etapów

## Cel projektu

Semantic query router jako custom endpoint w DeepFellow przed `/v1/chat/completions`.
Klasyfikuje zapytania na SIMPLE/COMPLEX i routuje do odpowiedniego modelu.

---

## Etap 1 — Dane

Zbudowanie datasetu SIMPLE/COMPLEX z trzech źródeł (~3000–3700 rekordów).

Źródła:
- **Arena** — prompty z Chatbot Arena, labele z Elo, kategoryzacja przez Gemini
- **Synthetic** — Gemini generuje prompty z labelem i kategorią
- **Borderline** — prompty z szarej strefy, label wynika z oceny słaby vs silny model

Wyniki: `validation.jsonl` + `test.jsonl`

---

## Etap 2 — Classifier

Kaskada trzech warstw klasyfikujących prompt na SIMPLE/COMPLEX:

- **Warstwa 1** — heurystyki (długość, słowa kluczowe, scoring punktowy, <1ms)
- **Warstwa 2** — embeddingi (cosine similarity do centroidów SIMPLE/COMPLEX, ~5–15ms)
- **Warstwa 3** — Qwen zero-shot przez DeepFellow (~10–20ms)

Fallback przy niskim confidence → COMPLEX.

---

## Etap 3 — Kalibracja

Iteracja po progach warstw na `validation.jsonl`. Metryki:
- F1 (klasa COMPLEX)
- Błąd A: COMPLEX sklasyfikowany jako SIMPLE (krytyczny — minimalizujemy)
- Błąd B: SIMPLE sklasyfikowany jako COMPLEX (kosztowny — akceptowalny)

Progi zapisane w `config/router.yaml`. Finalny pomiar na `test.jsonl` (jeden raz).

---

## Etap 4 — Router + Map-Reduce

Custom endpoint w DeepFellow:
- SIMPLE → słaby model (Qwen)
- COMPLEX → heurystyka wieloetapowości:
  - NIE → silny model (Llama 70B)
  - TAK → dekompozycja (Qwen) → sub-taski przez classifier+router → merge
    - niezależne sub-taski: konkatenacja
    - zależne sub-taski: LLM synthesizer (Llama 70B)

---

## Etap 5 — Benchmarki

Porównanie: **zawsze Llama 70B** (baseline) vs **router**.

Metryki operacyjne:
- latency (p50, p95), throughput, GPU utilization

Metryki jakości:
- ROUGE dla SIMPLE
- LLM-as-Judge (Gemini) dla COMPLEX — referencja = Llama 70B na oryginalnym zapytaniu

Metryki porównawcze (zgodne z RouteLLM):
- PGR (Performance Gap Recovered)
- APGR (Adjusted PGR)
- CPT (Cost Per Token)
