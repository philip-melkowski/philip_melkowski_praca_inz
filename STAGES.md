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
   - Skrypt: `data/arena/filter.py`
   - Szczegółowa specyfikacja filtrów: patrz sekcja niżej

2. **[data] Analiza rozkładu po filtrowaniu**
   - Statystyki: rozkład klas, długości tokenów, kategorie
   - Raport zapisany jako `data/analysis_report.md`

3. **[data] Generowanie danych syntetycznych**
   - Model: Gemini 1.5 Flash (free tier — 15 req/min, 1500/dzień)
   - Trzy typy: wyraźnie SIMPLE, wyraźnie COMPLEX, graniczne
   - Cel: ~300–350 rekordów SIMPLE (uzupełnienie do docelowego balansu)
   - Skrypt: `data/generate_synthetic.py`, zapis do jsonlines

4. **[data] Ręczna weryfikacja próbki syntetycznej**
   - Losowa próbka 15–20% danych syntetycznych
   - Plik do anotacji + dokument z wynikami weryfikacji

5. **[data] Balansowanie klas**
   - Połączenie danych Arena + syntetycznych
   - Docelowy stosunek: **70% COMPLEX / 30% SIMPLE** (bliżej rzeczywistego rozkładu niż 50/50)
   - Uzasadnienie: 50/50 przeszacowałoby SIMPLE w produkcji — Arena naturalnie faworyzuje COMPLEX

6. **[data] Podział val/test + walidacja schematu**
   - **Stratyfikowany** split 70/30, `random_state=42` (zachowuje proporcje klas w obu zbiorach)
   - Walidacja schematu: `query`, `label`, `category`, `source`
   - Zapis do `data/datasets/` (gitignored)

7. **[data] Testy jednostkowe skryptów data prep**
   - Framework: `pytest`
   - Testy dla `data/arena/filter.py` i `data/synthetic/generate.py`
   - Bez otwierania test setu

---

## Specyfikacja filtrowania Chatbot Arena

### Podział modeli

Źródło Elo: https://lmsys.org/blog/2023-06-22-leaderboard/ (dane z okresu kwiecień–czerwiec 2023).
Kryterium podziału: próg liczbowy — WEAK ≤ 980, MEDIUM 981–1150, STRONG ≥ 1151.

**STRONG** (Elo ≥ 1151 → wymagają mocnego modelu → COMPLEX):
- `gpt-4` (1227), `claude-v1` (1178), `claude-instant-v1` (1156)

**WEAK** (Elo ≤ 980 → słaby model wystarczył → SIMPLE):
- `llama-13b` (826), `dolly-v2-12b` (850), `stablelm-tuned-alpha-7b` (871), `fastchat-t5-3b` (897), `chatglm-6b` (905), `oasst-pythia-12b` (924), `alpaca-13b` (930), `RWKV-4-Raven-14B` (950), `mpt-7b-chat` (956)

**MEDIUM — wykluczone** (Elo 981–1150 → niejednoznaczny sygnał):
- `gpt4all-13b-snoozy` (986), `koala-13b` (992), `vicuna-7b` (1008), `palm-2` (1038), `wizardlm-13b` (1048), `vicuna-13b` (1061), `guanaco-33b` (1065), `gpt-3.5-turbo` (1130)

Bierzemy tylko pary STRONG vs WEAK (obie strony muszą należeć do tych grup).

### Mapowanie głosowań na etykiety

| Wynik głosowania | Etykieta | Uzasadnienie |
|---|---|---|
| STRONG wygrał | COMPLEX | Słaby model nie wystarczył |
| WEAK wygrał | SIMPLE | Słaby model poradził sobie |
| tie (normalne) | SIMPLE | Słaby model był wystarczający |
| tie (bothbad) | — odrzucamy | Brak sygnału jakości |

### Filtry

1. **Para modeli** — obie strony muszą należeć do STRONG lub WEAK (nie MEDIUM)
2. **Single-turn** — wykluczamy całe konwersacje wieloturowe (nie tylko pierwszą turę)
3. **Język** — `language == "English"` (pole z datasetu, bez zewnętrznych bibliotek)
4. **Minimalna długość** — `len(tiktoken.get_encoding("cl100k_base").encode(query)) >= 16`
5. **Duplikaty** — `drop_duplicates(subset=["query"])`, przy kolizji zachowujemy rekord z niższym `question_id` (deterministyczne)

### Logowanie

Przy każdym filtrze logujemy liczebność przed i po — pełny audit trail.
