# Generowanie danych syntetycznych

## Cel

Uzupełnienie danych z Chatbot Arena o syntetyczne zapytania, aby osiągnąć docelowy balans klas 50/50 COMPLEX/SIMPLE w finalnym datasecie.

## Model generujący

**Gemini 2.5 Flash** (`gemini-2.5-flash`, Google AI API)
- Free tier: 15 req/min, 1500 req/dzień
- Wybrany zamiast modeli testowanych w systemie (Qwen 1.5B, Llama 70B) — żeby uniknąć circular dependency

## Few-shot examples

Przykłady w prompcie pochodzą z **MT-Bench** (`lmsys/mt_bench_human_judgments`) — ręcznie wyselekcjonowane 5 SIMPLE + 4 COMPLEX z wyraźną, intuicyjną etykietą.

## Typy generowanych zapytań

| Typ | Liczba | Opis |
|---|---|---|
| SIMPLE | 600 | Zapytania gdzie słaby model odpowiada tak samo dobrze jak mocny |
| COMPLEX | 200 | Zapytania wymagające głębokiej wiedzy lub wieloetapowego rozumowania |
| BORDERLINE | 100 | Przypadki graniczne — etykieta ustalana przez LLM-as-Judge (issue #4) |

## Kategorie (wzorowane na MT-Bench)

Każde zapytanie ma przypisaną kategorię generowaną przez Gemini w tym samym wywołaniu:

| Kategoria | Liczba |
|---|---|
| ROLEPLAY | 143 |
| REASONING | 139 |
| WRITING | 136 |
| EXTRACTION | 134 |
| MATH | 105 |
| CODING | 99 |
| KNOWLEDGE_STEM | 78 |
| KNOWLEDGE_HUMANITIES | 66 |

## Schemat rekordu

```json
{
  "query": "...",
  "label": "SIMPLE | COMPLEX | BORDERLINE",
  "category": "CODING | REASONING | MATH | WRITING | ROLEPLAY | EXTRACTION | KNOWLEDGE_STEM | KNOWLEDGE_HUMANITIES",
  "source": "llm_generated"
}
```

## Deduplikacja

Jaccard similarity na znormalizowanych tokenach słownych, próg 0.5 (obniżony z 0.6 po wykryciu duplikatów w BORDERLINE). Duplikaty pomijane w trakcie generowania.

## Parametry skryptu

- Batch size: 15 zapytań na wywołanie
- Rate limit: 14 req/min (poniżej limitu free tier)
- Skrypt idempotentny — wznawia od miejsca przerwania
- Plik wyjściowy: `data/datasets/synthetic.jsonl` (gitignored)

## Etykietowanie BORDERLINE

Po wygenerowaniu wykryto 3 duplikaty semantyczne (Jaccard >= 0.4) — usunięte ręcznie przez `dedup_borderline.py`, brakujące rekordy zregenerowane. Szczegóły: `DEDUP_NOTES.md`.

Etykietowanie przez LLM-as-Judge (`label_borderline.py`):
1. **Llama 3.1 8B** (DeepFellow na VM) generuje odpowiedź na pytanie BORDERLINE
2. **Gemini 2.5 Flash** ocenia jakość odpowiedzi → dobra = SIMPLE, słaba = COMPLEX

Uwaga: Llama 3.1 8B użyta jako proxy modelu słabego — oryginalne modele WEAK z Areny (2023) niedostępne. Model nie wchodzi do testowania systemu routera.

Wyniki etykietowania: 79 → SIMPLE, 21 → COMPLEX (z 100 BORDERLINE).

## Finalny rozkład po etykietowaniu

| Etykieta | Liczba |
|---|---|
| SIMPLE | 679 |
| COMPLEX | 221 |
| **Łącznie** | **900** |
