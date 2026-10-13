# Etap 1 — Zbieranie i przygotowanie danych

## Cel

Zbudować dataset treningowy/ewaluacyjny do klasyfikatora SIMPLE/COMPLEX złożony z trzech źródeł, łącznie ~3000–3700 rekordów. Każdy rekord: `{prompt, label, category, source}`.

Kategorie: `CODING`, `REASONING`, `CREATIVE_WRITING`, `TRANSLATION`, `FACTUAL_QA`, `MATH`

Podział finalny: **70% validation / 30% test** (stratyfikowany, seed=42)

---

## Wymagania wstępne — modele (BLOKUJĄCE)

Przed uruchomieniem jakiegokolwiek skryptu ustalić i zapisać dokładne wersje:

| Rola | Dostawca | Do ustalenia |
|---|---|---|
| Generator / kategoryzator / judge | Gemini API | konkretny model ID, nie alias |
| Słaby model (router prod + dane borderline) | DeepFellow | nazwa z `/v1/models` |
| Silny model (router prod + dane borderline) | Groq | nazwa z Groq API |
| Model embeddingowy (warstwa 2 classifiera) | DeepFellow | nazwa z `/v1/models` |

Wersje muszą być udokumentowane w `config/models.yaml` przed generowaniem.

---

## Źródło 1 — Chatbot Arena (gotowe częściowo)

**Plik:** `data/arena_filtered.jsonl` (~1374 rekordów)
**Status:** prompty + labele są, brakuje pola `category`

### Kroki
1. Sprawdzić aktualny schemat `arena_filtered.jsonl`
2. Napisać skrypt `data_pipeline/arena/categorize.py`:
   - wczytuje rekordy bez `category`
   - batch request do Gemini: klasyfikuj prompt do jednej z 6 kategorii
   - zapisuje wzbogacone rekordy do `data/arena_categorized.jsonl`
3. Walidacja: sprawdzić rozkład kategorii, odrzucić rekordy z brakami

**Oczekiwany wynik:** `data/arena_categorized.jsonl` — ~1374 rek., pełny schemat

---

## Źródło 2 — Synthetic (~1500–2000 rekordów)

Gemini generuje prompty w stylu realnych użytkowników z gotowym labelem i kategorią.

### Kroki
1. Napisać `data_pipeline/synthetic/generate.py`:
   - prompt systemowy definiujący styl i zakres
   - generowanie po ~50 rekordów per batch (6 kategorii × ~2 poziomy trudności)
   - każdy rekord: `{prompt, label, category, source: "synthetic"}`
2. Deduplikacja Jaccard (`data_pipeline/synthetic/dedup.py`) — próg: 0.5
   - deduplikacja wewnątrz zbioru synthetic
   - deduplikacja cross-source wobec arena
3. Zapisać do `data/synthetic.jsonl`

**Oczekiwany wynik:** `data/synthetic.jsonl` — ~1500–2000 rek. po dedup

---

## Źródło 3 — Borderline (~300 rekordów)

Prompty z "szarej strefy" — Gemini generuje, modele oceniają blind, label wynika z różnicy jakości.

### Kroki
1. `data_pipeline/borderline/generate_prompts.py`:
   - Gemini generuje ~350 promptów bez etykiet, z intencją bycia niejednoznacznym
   - format: `{prompt, category, source: "borderline"}`
2. `data_pipeline/borderline/collect_responses.py`:
   - dla każdego promptu: zapytaj słaby model (DeepFellow) → `response_weak`
   - dla każdego promptu: zapytaj silny model (Groq) → `response_strong`
   - zapisz pary do pliku pośredniego
3. `data_pipeline/borderline/judge.py`:
   - Gemini ocenia obie odpowiedzi (blind — nie wie który model) w skali 1–5
   - identyczny prompt oceny dla obu odpowiedzi
   - label: `COMPLEX` jeśli `score_strong - score_weak >= 1`, inaczej `SIMPLE`
4. Zapisać do `data/borderline.jsonl`

**Oczekiwany wynik:** `data/borderline.jsonl` — ~300 rek. z labelem wynikającym z oceny

---

## Łączenie źródeł

`data_pipeline/build_dataset.py`:
1. Wczytuje arena_categorized + synthetic + borderline
2. Dedup cross-source (Jaccard 0.5)
3. Stratyfikowany podział 70/30 (seed=42) po `label × category`
4. Zapisuje:
   - `data/validation.jsonl`
   - `data/test.jsonl`
   - `data/dataset_stats.json` — rozkłady, liczności

**Oczekiwany wynik:**

| Plik | Rek. (szacunek) |
|---|---|
| `validation.jsonl` | ~2300 |
| `test.jsonl` | ~1000 |

Rozkład SIMPLE/COMPLEX: dążymy do ~50/50 lub max 60/40.

---

## Struktura plików po etapie

```
data/
├── arena_filtered.jsonl        # wejście (istniejące)
├── arena_categorized.jsonl     # wyjście kroku 1
├── synthetic.jsonl             # wyjście kroku 2
├── borderline.jsonl            # wyjście kroku 3
├── validation.jsonl            # finalny zbiór walidacyjny
├── test.jsonl                  # finalny zbiór testowy
└── dataset_stats.json          # statystyki
config/
└── models.yaml                 # wersje modeli użytych w tym etapie
data_pipeline/
├── arena/
│   └── categorize.py
├── synthetic/
│   ├── generate.py
│   └── dedup.py
├── borderline/
│   ├── generate_prompts.py
│   ├── collect_responses.py
│   └── judge.py
└── build_dataset.py
```

---

## Kryteria ukończenia etapu

- [ ] Wersje wszystkich modeli zapisane w `config/models.yaml`
- [ ] `arena_categorized.jsonl` — pełny schemat, brak null w `category`
- [ ] `synthetic.jsonl` — min. 1500 rek. po dedup
- [ ] `borderline.jsonl` — min. 250 rek. z labelem
- [ ] `validation.jsonl` + `test.jsonl` — łącznie min. 3000 rek.
- [ ] `dataset_stats.json` — rozkład SIMPLE/COMPLEX max 60/40
- [ ] Wszystkie skrypty działają z `uv run`

---

## Rezultaty (do uzupełnienia)

*— do uzupełnienia po zakończeniu etapu —*
