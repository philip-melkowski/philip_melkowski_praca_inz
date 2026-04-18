# CLAUDE.md — deepfellow-router

Praca inżynierska: **Semantyczny router zapytań LLM** zintegrowany z platformą DeepFellow Infra.

## Cel projektu

Zbudować system routingu zapytań, który automatycznie kieruje każde zapytanie do odpowiedniego modelu językowego (Qwen 1.5B lub Llama 70B) na podstawie oceny złożoności — osiągając niższą latencję i mniejsze zużycie GPU przy akceptowalnej degradacji jakości odpowiedzi.

Punkty odniesienia w literaturze: **RouteLLM** (Ong et al., 2024) i **FrugalGPT** (Chen et al., 2023).

---

## Architektura systemu

```
HTTP /v1/chat/completions
        │
        ▼
CLASSIFIER (kaskada 3-warstwowa)
  [1] Heurystyki     (<1ms)   — pewny wynik → decyzja
  [2] Embeddings     (~5–15ms) — pewny wynik → decyzja
  [3] Qwen 1.5B zero-shot (~10–20ms) — decyzja finalna
        │
        ├── SIMPLE ──────────────────→ Qwen 1.5B → odpowiedź
        │
        └── COMPLEX
                │
                ▼
        MAP-REDUCE CHECK (heurystyka)
                │
           ┌────┴────┐
           NIE      TAK
           │         │
           ▼         ▼
        ROUTER   dekompozycja (Qwen 1.5B zero-shot)
           │     → [sub-task1, sub-task2, ...] + graf zależności
        Llama 70B    │
                     ▼
                CLASSIFIER + ROUTER na każdym sub-tasku
                     │
                   MERGE
              ┌─────┴─────┐
         niezależne    zależne
         konkatenacja  LLM synthesizer
```

### Integracja z DeepFellow

Router działa jako **Custom Endpoint** wywoływany przed `/v1/chat/completions` — nie modyfikuje core'u DeepFellow Infra.

---

## Moduły

### 1. Classifier

Kaskada trzech warstw — minimalizuje latencję, każda warstwa uruchamia się tylko gdy poprzednia ma niską pewność.

**Warstwa 1 — Heurystyki** (scoring):
- długość promptu w tokenach (progi: 50 / 150 / 400)
- obecność słów kluczowych: `analyze`, `compare`, `implement`, `step by step`, itp.
- liczba niezależnych poleceń/kroków
- jeden próg THRESHOLD → SIMPLE / COMPLEX
- "pewność" = odległość sumy punktów od progu

**Warstwa 2 — Embeddings**:
- dwa centroidy (SIMPLE i COMPLEX) wyznaczone ze zbioru walidacyjnego
- nowe zapytanie wektoryzowane przez model embeddings z DeepFellow
- pewność = różnica cosine similarity do centroidów
- próg confidence konfigurowalny w YAML

**Warstwa 3 — Mały model zero-shot**:
- Qwen 1.5B zapytany: `"Oceń złożoność. Odpowiedz: SIMPLE lub COMPLEX. Zapytanie: {prompt}"`
- pewność = softmax zwycięskiego tokenu
- zawsze zwraca decyzję (koniec kaskady)

### 2. Router

Wybiera model docelowy na podstawie wyniku klasyfikatora. Konfigurowany przez YAML — bez zmiany kodu.

```python
def router(request, complexity_result) -> model:
    # complexity_result.complexity: SIMPLE | COMPLEX
    # complexity_result.confidence: float
    ...
```

YAML config zawiera:
- progi i wagi heurystyki (warstwa 1)
- próg confidence embeddings (warstwa 2)
- przypisanie klas do modeli (SIMPLE → Qwen 1.5B, COMPLEX → Llama 70B)
- fallback policy (niski confidence → Llama 70B)

### 3. Map-Reduce

Uruchamiany tylko dla COMPLEX.

**Heurystyka rozkładalności** — zapytanie jest kandydatem gdy:
- zawiera spójniki enumeracyjne: *i, oraz, a także, po czym, następnie*
- ma strukturę wielopunktową (numerowaną/bulletową)
- liczba niezależnych poleceń przekracza próg

**Dekompozycja** — Qwen 1.5B zwraca JSON z listą sub-tasków i grafem zależności (jednym wywołaniem).

**Merge**:
- sub-taski niezależne → konkatenacja (zero latencji)
- sub-taski zależne → LLM synthesizer

---

## Dane testowe

Dane służą do **ewaluacji i kalibracji progów** — nie do trenowania modeli.

### Schemat każdego rekordu

```
query:      str
label:      SIMPLE | COMPLEX
category:   CODING | REASONING | CREATIVE_WRITING | TRANSLATION | FACTUAL_QA | MATH
source:     chatbot_arena | llm_generated
```

### Źródło 1 — Chatbot Arena

Dataset: `lmsys/chatbot_arena_conversations` (HuggingFace, gated).

Mapowanie głosowań na etykiety:
- strong wygrał → COMPLEX
- tie → SIMPLE (słabszy model wystarczył)
- weak wygrał → SIMPLE
- tie (bothbad) → odrzucamy

Podział modeli (Elo z leaderboard 2023-06):
- STRONG: gpt-4 (1227), claude-v1 (1178)
- WEAK: llama-13b, dolly-v2, stablelm, fastchat-t5, chatglm, oasst-pythia, alpaca, RWKV-14B, mpt-7b, vicuna-7b
- MEDIUM (wykluczone): gpt-3.5-turbo, claude-instant-v1, palm-2, vicuna-13b, guanaco-33b, wizardlm-13b, koala, gpt4all

Filtry: tylko STRONG vs WEAK, single-turn, angielski, min 16 tokenów.
Wynik po filtrach: ~1374 rekordów (COMPLEX: 1161, SIMPLE: 213) — niezbalansowane.

### Źródło 2 — LLM-generated

Model generujący MUSI być inny niż Qwen 1.5B i Llama 70B (żeby nie testować na danych z tych samych modeli).
Generować trzy typy: wyraźnie SIMPLE, wyraźnie COMPLEX, przypadki graniczne.
Ręczna weryfikacja ~15–20% próbki.

Cel: zbilansować klasy po stronie SIMPLE.

### Podział zbioru

```
70% — validation set (kalibracja progów w YAML, otwarte)
30% — test set       (zamknięty, otwierany raz — finalny pomiar)
```

### Kalibracja progów

Dla każdej kombinacji wartości progów puszczamy validation set przez classifier, mierzymy metryki, wybieramy najlepszą kombinację. Dopiero potem otwieramy test set.

---

## Metryki

### Classifier

- **Accuracy + F1** (F1 liczony względem klasy COMPLEX — błędna klasyfikacja COMPLEX→SIMPLE jest najgorsza)
- **Błąd A** (critical): COMPLEX → Qwen 1.5B — niska jakość odpowiedzi
- **Błąd B** (costly): SIMPLE → Llama 70B — zmarnowane zasoby GPU

### Quality Degradation

Porównanie: statyczna architektura (zawsze Llama 70B) vs router.

```
statyczna:  zapytanie → Llama 70B → odpowiedź_referencyjna
router:     zapytanie → Classifier → Router → model → odpowiedź_routera
```

- **ROUGE** — dla klasy SIMPLE (tłumaczenia, streszczenia, formatowanie)
- **GPT-as-Judge** (skala 1–5) — dla klasy COMPLEX (kod, złożone rozumowanie)

### Benchmarki systemowe

Porównanie architektury statycznej vs z routerem:

| Metryka | Opis |
|---|---|
| Latency | Średni czas odpowiedzi |
| GPU utilization | Zużycie GPU pod obciążeniem |
| Throughput | req/s |
| Response Quality | ROUGE / GPT-as-Judge |

### Metryki z RouteLLM (do porównania z literaturą)

**PGR** (Performance Gap Recovered):
```
PGR = (jakość_routera - jakość_słabego) / (jakość_mocnego - jakość_słabego)
```

**APGR** — pole pod krzywą PGR dla wszystkich wartości progu (0%–100% zapytań do mocnego modelu). Losowy routing = 0.5, dobry router = 0.8+.

**CPT(X%)** — ile minimum % zapytań musi trafić do mocnego modelu żeby osiągnąć PGR = X%. Im niższe tym lepszy router.

---

## Stack techniczny

- Python 3.13, `uv` jako package manager
- FastAPI (custom endpoint w DeepFellow Infra)
- Konfiguracja przez YAML
- Model embeddings z DeepFellow (do warstwy 2)
- Qwen 1.5B — model SIMPLE + zero-shot classifier
- Llama 70B — model COMPLEX

---

## Struktura repozytorium (planowana)

```
deepfellow-router/
├── CLAUDE.md
├── README.md
├── config/
│   └── router.yaml          # progi, wagi, przypisanie modeli
├── router/
│   ├── classifier/
│   │   ├── heuristics.py    # warstwa 1
│   │   ├── embeddings.py    # warstwa 2
│   │   └── zeroshot.py      # warstwa 3
│   ├── classifier.py        # kaskada
│   ├── router.py            # wybór modelu
│   └── mapreduce.py         # dekompozycja + merge
├── data/
│   ├── prepare_arena.py     # filtrowanie chatbot arena
│   ├── generate_synthetic.py
│   └── datasets/            # gitignore — duże pliki
├── eval/
│   ├── calibrate.py         # kalibracja progów na validation set
│   ├── evaluate.py          # finalny pomiar na test set
│   └── metrics.py           # PGR, APGR, CPT, ROUGE, itp.
└── tests/
```

---

## Przewaga nad literaturą

- Kaskada heurystyk + embeddings + zero-shot **nie wymaga fine-tuningu routera** ani danych preferencji (w odróżnieniu od RouteLLM)
- Obsługa zapytań wieloetapowych przez Map-Reduce — czego RouteLLM i FrugalGPT nie adresują
- Integracja z istniejącą platformą on-premises (DeepFellow Infra)
