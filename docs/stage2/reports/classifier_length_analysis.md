# Analiza długości promptów — sygnał dla klasyfikatora (warstwa 1)

Skrypt: `eval/analyze_length.py`
Dane: `data/datasets/validation.jsonl` (1841 rekordów: 661 SIMPLE, 1180 COMPLEX)

## Statystyki długości (tokeny, tiktoken cl100k_base)

|  | min | p10 | p25 | p50 | p75 | p90 | p95 | max | mean |
|---|---|---|---|---|---|---|---|---|---|
| SIMPLE | 6 | 12 | 16 | 23 | 31 | 49 | 106 | 772 | 38.5 |
| COMPLEX | 16 | 18 | 23 | 40 | 68 | 169 | 301 | 1179 | 74.9 |

## Overlap klas

| Metryka | Wartość |
|---|---|
| Mediana COMPLEX | 40 tokenów |
| Mediana SIMPLE | 23 tokeny |
| % SIMPLE powyżej mediany COMPLEX | 13.3% |
| % COMPLEX poniżej mediany SIMPLE | 23.8% |

## Rozkład w przedziałach

| Przedział | SIMPLE | SIMPLE% | COMPLEX | COMPLEX% |
|---|---|---|---|---|
| 0–50 | 595 | 90.0% | 735 | 62.3% |
| 50–150 | 41 | 6.2% | 302 | 25.6% |
| 150–400 | 17 | 2.6% | 114 | 9.7% |
| 400–∞ | 8 | 1.2% | 29 | 2.5% |

## Wnioski

**Sygnał istnieje, ale jest słaby:**
- Mediana COMPLEX (40 tok.) wyraźnie wyższa niż SIMPLE (23 tok.) — kierunek się zgadza
- 23.8% COMPLEX jest krótszych niż mediana SIMPLE — dużo krótkich trudnych pytań
- 90% SIMPLE mieści się w 0–50 tokenach, ale też 62% COMPLEX — duży overlap w tym przedziale

**Implikacje dla progów:**
- Próg ~50 tokenów ma sens jako słaby sygnał: powyżej 50 tok. → 37.7% COMPLEX vs 10% SIMPLE
- Powyżej 150 tokenów → prawie na pewno COMPLEX (12.2% COMPLEX vs 3.8% SIMPLE)
- Krótki prompt (<50 tok.) nie wyklucza COMPLEX — długość sama w sobie nie jest decyzyjna

**Wniosek:** długość to użyteczny sygnał pomocniczy w scoringu warstwy 1, ale nigdy jedyny —
potwierdza sens kaskadowego podejścia gdzie każdy sygnał dokłada punkty a nie decyduje samodzielnie.
