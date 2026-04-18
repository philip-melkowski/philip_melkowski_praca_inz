# Project Stages

## Branch Strategy

`main` — stable, mergowane po zakończeniu każdego stage'u
`stage/<n>-<name>` — branch roboczy dla danego stage'u

## Stages

| Branch | Stage | Opis |
|---|---|---|
| `stage/1-data` | Data Collection & Prep | Filtrowanie Chatbot Arena, generowanie syntetycznych danych, podział val/test |
| `stage/2-classifier` | Classifier | Implementacja kaskady 3-warstwowej (heurystyki → embeddings → zero-shot) |
| `stage/3-router` | Router | Logika wyboru modelu, integracja z DeepFellow, config YAML |
| `stage/4-mapreduce` | Map-Reduce | Dekompozycja złożonych zapytań, graf zależności, merge |
| `stage/5-eval` | Evaluation | Kalibracja progów, metryki (PGR, APGR, CPT, ROUGE, GPT-as-Judge), benchmarki |
| `stage/6-integration` | Integration & Thesis | Integracja jako Custom Endpoint w DeepFellow Infra, testy end-to-end, dokumentacja |

---

## Stage 1 — Data Collection & Prep

Branch: `stage/1-data`

### Issues

1. **[data] Filtrowanie Chatbot Arena**
   - Pobranie datasetu `lmsys/chatbot_arena_conversations` (HuggingFace, gated)
   - Filtry: STRONG vs WEAK, single-turn, angielski, ≥16 tokenów
   - Mapowanie głosowań → SIMPLE/COMPLEX (tie-bothbad odrzucane)
   - Skrypt: `data/prepare_arena.py`

2. **[data] Analiza rozkładu po filtrowaniu**
   - Statystyki: rozkład klas, długości tokenów, kategorie
   - Raport zapisany jako `data/analysis_report.md`

3. **[data] Generowanie danych syntetycznych**
   - LLM inny niż Qwen 1.5B i Llama 70B
   - Trzy typy: wyraźnie SIMPLE, wyraźnie COMPLEX, graniczne
   - Skrypt: `data/generate_synthetic.py`, zapis do jsonlines

4. **[data] Ręczna weryfikacja próbki syntetycznej**
   - Losowa próbka 15–20% danych syntetycznych
   - Plik do anotacji + dokument z wynikami weryfikacji

5. **[data] Balansowanie klas**
   - Połączenie danych Arena + syntetycznych
   - Wyrównanie proporcji SIMPLE/COMPLEX

6. **[data] Podział val/test + walidacja schematu**
   - Deterministyczny split 70/30
   - Walidacja schematu: `query`, `label`, `category`, `source`
   - Zapis do `data/datasets/` (gitignored)

7. **[data] Testy jednostkowe skryptów data prep**
   - Testy dla `prepare_arena.py` i `generate_synthetic.py`
   - Bez otwierania test setu
