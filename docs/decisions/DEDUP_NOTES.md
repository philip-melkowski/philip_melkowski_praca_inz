# Czyszczenie duplikatów BORDERLINE

## Problem

Po wygenerowaniu 100 rekordów BORDERLINE przez `data/synthetic/generate.py` wykryto duplikaty
semantyczne — pytania o tym samym temacie sformułowane inaczej. Deduplikacja Jaccard z progiem 0.6
(użyta przy generowaniu) nie wyłapała ich bo różniły się wystarczająco słowami.

## Analiza (próg Jaccard 0.4)

Skrypt: `data/synthetic/dedup_borderline.py`

Znaleziono 5 par, z czego 3 to prawdziwe duplikaty a 2 to false positives (podobna struktura zdania, różny temat):

| Para | Query A | Query B | Similarity | Decyzja |
|---|---|---|---|---|
| [6] / [93] | "Explain the concept of 'half-life'..." | "Briefly explain the concept of 'half-life'..." | 0.48 | duplikat — usunąć [93] |
| [11] / [55] | "Craft a short encouraging message..." | "Write a short encouraging message..." | 0.47 | duplikat — usunąć [55] |
| [44] / [62] | "Briefly explain supply and demand..." | "Explain supply and demand using a simple example..." | 0.41 | duplikat — usunąć [62] |
| [6] / [80] | "Explain the concept of 'half-life'..." | "Explain the concept of recursion..." | 0.42 | false positive — różny temat |
| [80] / [93] | "Explain the concept of recursion..." | "Briefly explain the concept of 'half-life'..." | 0.44 | false positive — różny temat |

## Decyzja

Usunięto ręcznie indeksy **55, 62, 93** przez:
```
uv run data/synthetic/dedup_borderline.py --remove 55,62,93
```

Po usunięciu: 97 rekordów BORDERLINE → regeneracja 3 brakujących przez `data/synthetic/generate.py` (idempotentny).

## Zmiana progu w generate.py

Próg Jaccard obniżony z 0.6 → 0.5 w `data/synthetic/generate.py` żeby uniknąć podobnych duplikatów przy przyszłych generacjach.
