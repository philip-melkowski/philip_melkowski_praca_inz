# 04 — Kategoryzacja rekordów z Areny

## Problem

Rekordy z Chatbot Arena nie mają kategorii — pole `category` = `UNKNOWN` po filtrowaniu.
Kategorie są potrzebne do stratyfikowanego splitu i analizy wyników per kategoria.

## Kategoryzacja przez Gemini 2.5 Flash

Skrypt: `data/arena/categorize.py`

Gemini 2.5 Flash przypisuje każdemu promptowi jedną z 8 kategorii MT-Bench:
`CODING`, `REASONING`, `MATH`, `WRITING`, `ROLEPLAY`, `EXTRACTION`, `KNOWLEDGE_STEM`, `KNOWLEDGE_HUMANITIES`

Kategoryzacja uruchomiona na wszystkich 1738 rekordach (checkpoint co 50 rekordów).
Wymagane zmienne środowiskowe: `GEMINI_API_KEY`

### Wynik kategoryzacji (przed czyszczeniem)

| Kategoria | Liczba |
|---|---|
| WRITING | 334 |
| CODING | 297 |
| REASONING | 284 |
| KNOWLEDGE_STEM | 257 |
| KNOWLEDGE_HUMANITIES | 221 |
| MATH | 118 |
| EXTRACTION | 118 |
| ROLEPLAY | 95 |
| OTHER | 14 |

## Przegląd i czyszczenie OTHER

MT-Bench nie ma kategorii OTHER. Wszystkie 14 rekordów OTHER przejrzano ręcznie.

Szczegółowe uzasadnienie decyzji dla każdego rekordu: `docs/stage1/decisions/ARENA_OTHER_CLEANUP.md`

Skrypt czyszczący: `data/arena/fix_other.py`

### Wynik czyszczenia

- 6 rekordów usuniętych (śmieć: odpowiedzi modelu, system prompty, bezsensowny tekst)
- 8 rekordów przekategoryzowanych do właściwych kategorii MT-Bench

## Wynik końcowy

**1732 rekordów**, 0 × OTHER, 8 kategorii MT-Bench:

| Kategoria | Liczba |
|---|---|
| WRITING | 335 |
| CODING | 297 |
| REASONING | 286 |
| KNOWLEDGE_STEM | 257 |
| KNOWLEDGE_HUMANITIES | 225 |
| EXTRACTION | 119 |
| MATH | 118 |
| ROLEPLAY | 95 |
