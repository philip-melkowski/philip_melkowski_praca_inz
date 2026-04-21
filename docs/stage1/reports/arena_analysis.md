# Analiza rozkładu — Chatbot Arena (filtered)

Wygenerowane przez: `data/arena/analyze.py`

Po czyszczeniu kategorii OTHER (`data/arena/fix_other.py`) — usunięto 6 śmieciowych rekordów,
8 przekategoryzowano. Szczegóły: `docs/decisions/ARENA_OTHER_CLEANUP.md`.

## Rozkład etykiet

| Etykieta | Liczba | % |
|---|---|---|
| COMPLEX | 1466 | 84.6% |
| SIMPLE | 266 | 15.4% |
| **Łącznie** | **1732** | 100% |

## Długość promptów (tokeny)

| | min | p25 | p50 | p75 | p95 | max |
|---|---|---|---|---|---|---|
| COMPLEX | 16 | 21 | 35 | 75 | 339 | 1179 |
| SIMPLE | 16 | 23 | 34 | 75 | 371 | 772 |

**Overlap długości:** 16–772 tokenów (zakres wspólny obu klas)

## Rozkład wyników głosowań

| Wynik | Etykieta | Liczba | % |
|---|---|---|---|
| strong won | COMPLEX | 1466 | 84.6% |
| weak won | SIMPLE | 148 | 8.5% |
| tie | SIMPLE | 118 | 6.8% |

## Rozkład SIMPLE/COMPLEX wg strong_model

| Model | COMPLEX | SIMPLE | % COMPLEX |
|---|---|---|---|
| claude-instant-v1 | 260 | 73 | 78.1% |
| claude-v1 | 567 | 89 | 86.4% |
| gpt-4 | 639 | 104 | 86.0% |

## Rozkład SIMPLE/COMPLEX wg weak_model

| Model | COMPLEX | SIMPLE | % COMPLEX |
|---|---|---|---|
| RWKV-4-Raven-14B | 234 | 53 | 81.5% |
| alpaca-13b | 207 | 38 | 84.5% |
| chatglm-6b | 166 | 25 | 86.9% |
| dolly-v2-12b | 99 | 8 | 92.5% |
| fastchat-t5-3b | 163 | 40 | 80.3% |
| llama-13b | 69 | 7 | 90.8% |
| mpt-7b-chat | 163 | 41 | 79.9% |
| oasst-pythia-12b | 245 | 44 | 84.8% |
| stablelm-tuned-alpha-7b | 120 | 10 | 92.3% |

## Top 20 słów kluczowych — COMPLEX (częstsze niż w SIMPLE)

| Słowo | Liczba wystąpień |
|---|---|
| answer | 250 |
| write | 239 |
| use | 213 |
| please | 177 |
| following | 177 |
| only | 157 |
| more | 149 |
| each | 148 |
| give | 141 |
| text | 140 |
| like | 135 |
| make | 134 |
| code | 133 |
| time | 130 |
| want | 114 |
| using | 114 |
| list | 113 |
| question | 112 |
| them | 106 |
| her | 98 |

## Top 20 słów kluczowych — SIMPLE (częstsze niż w COMPLEX)

| Słowo | Liczba wystąpień |
|---|---|
| million | 15 |
| aim | 14 |
| hub | 14 |
| intersection | 14 |
| motor | 13 |
| axle | 12 |
| korea | 11 |
| document | 11 |
| ghz | 10 |
| --- | 10 |
| member | 10 |
| fees | 10 |
| drug | 9 |
| frame | 9 |
| pens | 9 |
| ends | 8 |
| coordinates | 8 |
| deposit | 8 |
| audrey | 8 |
| becky | 8 |
