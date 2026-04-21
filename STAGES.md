# Project Stages

## Materiały referencyjne

Notatki i PDF-y z literatury na której bazuje projekt:
- `docs/references/routellm_notes.md` / `.pdf` — notatki z RouteLLM (Ong et al., 2024)
- `docs/references/router_notes.md` / `.pdf` — notatki ogólne o routingu LLM

---

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
   - Raport zapisany jako `docs/stage1/reports/arena_analysis.md`

3. **[data] Generowanie danych syntetycznych**
   - Model: Gemini 2.5 Flash (`gemini-2.5-flash`, free tier — 15 req/min, 1500/dzień)
   - Trzy typy z celami: 600 SIMPLE, 200 COMPLEX, 100 BORDERLINE
   - BORDERLINE = przypadki graniczne — etykieta ustalana ręcznie w kroku #4
   - Few-shot examples: z MT-Bench (`lmsys/mt_bench_human_judgments`) — ręcznie wyselekcjonowane
   - Kategorie (MT-Bench) generowane przez Gemini razem z pytaniem (jedno wywołanie)
   - Skrypt: `data/synthetic/generate.py`, zapis do `data/datasets/synthetic.jsonl`
   > MMLU (`cais/mmlu`) odrzucone — format wielokrotnego wyboru (A/B/C/D) nie pasuje do otwartych zapytań z Areny i syntetycznych; może wprowadzić bias w klasyfikatorze.

4. **[data] Etykietowanie BORDERLINE przez LLM-as-Judge**
   - Przed etykietowaniem: czyszczenie duplikatów w BORDERLINE (Jaccard próg obniżony do 0.5), regeneracja brakujących
   - Słaby model: **Llama 3 8B** (DeepFellow) — proxy dla modeli WEAK z Areny (oryginalne niedostępne w Ollama)
   - Każde pytanie BORDERLINE → Llama 3 8B generuje odpowiedź → Gemini 2.5 Flash ocenia jakość
   - Dobra odpowiedź → SIMPLE, słaba → COMPLEX
   - Skrypty: `data/synthetic/dedup_borderline.py`, `data/synthetic/label_borderline.py`

5. **[data] Kategoryzacja rekordów z Areny**
   - Rekordy z Areny nie mają kategorii (pole `category` = `UNKNOWN`)
   - Gemini 2.5 Flash przypisuje kategorię do każdego promptu z Areny
   - Kategorie: CODING, REASONING, MATH, WRITING, ROLEPLAY, EXTRACTION, KNOWLEDGE_STEM, KNOWLEDGE_HUMANITIES (brak OTHER — wzorowane na MT-Bench)
   - Skrypt: `data/arena/categorize.py`, aktualizuje `arena_filtered.jsonl`
   - Po kategoryzacji: przegląd 14 rekordów OTHER — 6 usuniętych (śmieć: odpowiedzi modeli, system prompty), 8 przekategoryzowanych
   - Skrypt: `data/arena/fix_other.py`; wynik: 1732 rekordów (było 1738)
   - Szczegóły decyzji: `docs/stage1/decisions/ARENA_OTHER_CLEANUP.md`
   - Raport końcowy: `docs/stage1/reports/arena_analysis.md`

6. **[data] Budowa finalnego datasetu**
   - Połączenie danych Arena (z kategoriami) + syntetycznych
   - Bez sztucznego balansowania — zachowujemy naturalny rozkład
   - Uzasadnienie: podcinanie COMPLEX = utrata realnych danych z Areny; rozkład uwzględniany przy kalibracji (ważone F1, stratyfikowany split)
   - Finalny rozkład: COMPLEX 1687, SIMPLE 945 (łącznie 2632)
   - Stratyfikowany split 70/30, `random_state=42`: validation 1841, test 791
   - Walidacja schematu: odrzuca rekordy z błędną etykietą, kategorią spoza MT-Bench lub pustym query
   - Skrypt: `data/build_dataset.py`; raport: `docs/stage1/reports/dataset_build.md`

7. **[data] Testy jednostkowe skryptów data prep**  *(odkładane na później)*
   - Framework: `pytest`
   - Testy dla `data/arena/filter.py`, `data/synthetic/generate.py`
   - Bez otwierania test setu

### Szczegóły

#### Kategorie zapytań

Wzorowane na MT-Bench (LMSYS) — 8 kategorii pokrywających realne przypadki użycia, porównywalne z literaturą.

| Kategoria | Opis |
|---|---|
| `CODING` | Programowanie, debugowanie, code review |
| `REASONING` | Logiczne wnioskowanie, analiza argumentów |
| `MATH` | Obliczenia, dowody, zadania matematyczne |
| `WRITING` | Pisanie esejów, streszczeń, listów, kreatywne pisanie |
| `ROLEPLAY` | Scenariusze z postacią, symulacje dialogów |
| `EXTRACTION` | Wyciąganie informacji z tekstu, tłumaczenia, formatowanie |
| `KNOWLEDGE_STEM` | Nauki ścisłe, technologia, inżynieria, medycyna |
| `KNOWLEDGE_HUMANITIES` | Historia, prawo, filozofia, nauki społeczne |

Kategorie nadawane przez Gemini razem z generowaniem pytania (jedno wywołanie). Rekordów z Areny — kategoryzacja osobnym skryptem po zebraniu wszystkich danych.

#### Specyfikacja filtrowania Chatbot Arena

Źródło Elo: https://lmsys.org/blog/2023-06-22-leaderboard/ (dane z okresu kwiecień–czerwiec 2023).
Kryterium podziału: próg liczbowy — WEAK ≤ 980, MEDIUM 981–1150, STRONG ≥ 1151.

**STRONG** (Elo ≥ 1151 → wymagają mocnego modelu → COMPLEX):
- `gpt-4` (1227), `claude-v1` (1178), `claude-instant-v1` (1156)

**WEAK** (Elo ≤ 980 → słaby model wystarczył → SIMPLE):
- `llama-13b` (826), `dolly-v2-12b` (850), `stablelm-tuned-alpha-7b` (871), `fastchat-t5-3b` (897), `chatglm-6b` (905), `oasst-pythia-12b` (924), `alpaca-13b` (930), `RWKV-4-Raven-14B` (950), `mpt-7b-chat` (956)

**MEDIUM — wykluczone** (Elo 981–1150 → niejednoznaczny sygnał):
- `gpt4all-13b-snoozy` (986), `koala-13b` (992), `vicuna-7b` (1008), `palm-2` (1038), `wizardlm-13b` (1048), `vicuna-13b` (1061), `guanaco-33b` (1065), `gpt-3.5-turbo` (1130)

Bierzemy tylko pary STRONG vs WEAK (obie strony muszą należeć do tych grup).

**Mapowanie głosowań na etykiety:**

| Wynik głosowania | Etykieta | Uzasadnienie |
|---|---|---|
| STRONG wygrał | COMPLEX | Słaby model nie wystarczył |
| WEAK wygrał | SIMPLE | Słaby model poradził sobie |
| tie (normalne) | SIMPLE | Słaby model był wystarczający |
| tie (bothbad) | — odrzucamy | Brak sygnału jakości |

**Filtry:**
1. Para modeli — obie strony muszą należeć do STRONG lub WEAK (nie MEDIUM)
2. Single-turn — wykluczamy całe konwersacje wieloturowe
3. Język — `language == "English"` (pole z datasetu)
4. Minimalna długość — `len(tiktoken.get_encoding("cl100k_base").encode(query)) >= 16`
5. Duplikaty — `drop_duplicates(subset=["query"])`, przy kolizji zachowujemy rekord z niższym `question_id`

---

## Stage 2 — Classifier

Branch: `stage/2-classifier`

### Analizy wstępne (przed implementacją)

- **Długość promptów jako sygnał** — analiza na validation secie wykazała że długość jest
  użytecznym sygnałem pomocniczym, ale nie decydującym (23.8% COMPLEX krótszych niż mediana SIMPLE).
  Szczegóły: `docs/stage2/reports/classifier_length_analysis.md`

- **Słowa kluczowe jako sygnał** — badania literaturowe (Bloom's Taxonomy, RouteLLM arXiv:2406.18665,
  ACAR arXiv:2602.21231, survey arXiv:2502.00409, Mechanistic Interpretability arXiv:2602.17229,
  AgentBus) dały listę kandydatów na frazy COMPLEX. Kandydaci SIMPLE odrzuceni — te słowa
  pojawiają się równie często w COMPLEX. Weryfikacja empiryczna na validation secie (precision ≥ 80%,
  recall ≥ 1%) — skrypt: `eval/analyze_keywords.py`. 11/42 fraz przeszło próg.
  Pełne źródła i wyniki: `docs/stage2/reports/classifier_keywords_research.md`
  **Finalna lista fraz do ustalenia z promotorem** — 3 opcje opisane w `docs/stage2/decisions/KEYWORD_SELECTION.md`

### Issues

8. **[classifier] Warstwa 1 — Heurystyki**
   - Scoring oparty na: długości promptu w tokenach, obecności słów kluczowych, liczbie kroków
   - Listy słów kluczowych wywodzone z Bloom's Taxonomy i systemów routingu z literatury,
     zweryfikowane empirycznie na validation secie (precision/recall)
   - Suma punktów porównywana z progiem THRESHOLD → SIMPLE/COMPLEX
   - Confidence = znormalizowana odległość sumy od progu (wartość w [0, 1])
   - Progi i wagi konfigurowane przez `config/router.yaml`
   - Skrypt: `router/classifier/heuristics.py`
   - Analizy wstępne: `docs/stage2/reports/classifier_length_analysis.md`, `docs/stage2/reports/classifier_keywords_research.md`

### Szczegóły

#### Scoring heurystyk — warstwa 1

Każdy sygnał daje punkty, które sumują się do wyniku końcowego. Wynik porównywany z progiem THRESHOLD.

**Długość promptu (tiktoken cl100k_base):**

| Zakres tokenów | Punkty |
|---|---|
| < 50 | 0 |
| 50–150 | +1 |
| 150–400 | +2 |
| > 400 | +3 |

Uzasadnienie progów: `docs/stage2/reports/classifier_length_analysis.md`

**Słowa kluczowe:**
- Obecność frazy z listy COMPLEX → +1 punkt za frazę (do ustalonego max)
- Brak sygnałów = niski score = skłaniamy się ku SIMPLE (brak aktywnego karania)
- Frazy: `develop, analyze, step by step, design, plan, recommend, solve, build, implement, generate, evaluate`
- Uzasadnienie doboru fraz: `docs/stage2/reports/classifier_keywords_research.md`

**Confidence:**
```
confidence = min(|score - THRESHOLD| / THRESHOLD, 1.0)
```

Wszystkie progi i wagi konfigurowane w `config/router.yaml`.

