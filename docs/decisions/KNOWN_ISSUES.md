# Known Issues — Arena dataset

## Niepoprawne oznaczenia języka

Niektóre rekordy mają `language == "English"` w datasecie Areny, ale prompt jest w innym języku
(zaobserwowano włoski, prawdopodobnie inne). Pole `language` w źródle jest niepewne.

Skrypt filtrujący: `data/arena/filter.py`

**Wpływ:** niewielki — rekordy te przeszły przez filtr i są w datasecie. Gemini poprawnie
je kategoryzuje mimo innego języka.

**Ewentualne rozwiązanie:** dodać do `data/arena/filter.py` weryfikację języka przez `langdetect`
jako dodatkowy filtr po `language == "English"`.

## Zduplikowane zapytania w datasecie Arena

Zaobserwowano obecność semantycznie podobnych promptów (np. "David has three sisters...").
Filtr w `data/arena/filter.py` deduplikuje po dokładnym tekście promptu, ale nie łapie
duplikatów semantycznych. Przy obecnej skali (1732 rekordów po czyszczeniu OTHER) wpływ jest pomijalny.
