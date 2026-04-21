# Budowa finalnego datasetu

Skrypt: `data/build_dataset.py`

## Źródła

| Źródło | Rekordów |
|---|---|
| Chatbot Arena (`arena_filtered.jsonl`) | 1732 |
| Syntetyczne (`synthetic.jsonl`) | 900 |
| **Łącznie** | **2632** |

## Rozkład etykiet

| Etykieta | Liczba | % |
|---|---|---|
| COMPLEX | 1687 | 64.1% |
| SIMPLE | 945 | 35.9% |
| **Łącznie** | **2632** | 100% |

Bez sztucznego balansowania — zachowany naturalny rozkład. Nierówne klasy obsługiwane
przez ważone F1 przy kalibracji progów.

## Rozkład kategorii

| Kategoria | Liczba |
|---|---|
| WRITING | 470 |
| REASONING | 426 |
| CODING | 397 |
| KNOWLEDGE_STEM | 333 |
| KNOWLEDGE_HUMANITIES | 292 |
| EXTRACTION | 253 |
| ROLEPLAY | 238 |
| MATH | 223 |

## Podział val/test

Stratyfikowany split 70/30 po etykiecie (`random_state=42`).

| Zbiór | Rekordów | COMPLEX | SIMPLE |
|---|---|---|---|
| Validation | 1841 | 1180 | 661 |
| Test | 791 | 507 | 284 |

Test set zamknięty — otwierany raz przy finalnym pomiarze.

## Walidacja schematu

Każdy rekord musi mieć: `query`, `label`, `category`, `source`.
Dozwolone etykiety: `SIMPLE`, `COMPLEX`.
Dozwolone kategorie: 8 kategorii MT-Bench (bez OTHER).
Pominięte przy budowie: 0 rekordów.
