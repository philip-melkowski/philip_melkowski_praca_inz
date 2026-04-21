# Plan: przegląd kategoryzacji Arena przed build_dataset

**Status: WYKONANY**

## Cel

Zanim uruchomimy `data/build_dataset.py` (issue #6), upewniamy się że kategoryzacja Areny
przez Gemini 2.5 Flash jest wystarczającej jakości.

## Kroki

### 1. Przegląd rekordów OTHER

```bash
uv run data/arena/inspect.py
```

Oczekiwane: 14 rekordów z kategorią OTHER. Dla każdego sprawdzić ręcznie czy OTHER jest
uzasadnione, czy to błąd klasyfikacji. Jeśli ≥ 3 to błędy → ponowna kategoryzacja tych
rekordów z poprawionym promptem.

### 2. Sprawdzenie duplikatów po kategoryzacji

Przejrzeć kilka par rekordów o tym samym prompcie (po dedup exact-match w filter.py powinno
nie być, ale warto zweryfikować) — wystarczy wzrokowy spot check 10–20 rekordów.

### 3. Próbkowanie jakości per kategoria

Dla każdej z 9 kategorii wylosować 3–5 rekordów i sprawdzić ręcznie czy kategoria pasuje
do treści zapytania.

Kategorie: WRITING, CODING, REASONING, KNOWLEDGE_STEM, KNOWLEDGE_HUMANITIES, MATH,
EXTRACTION, ROLEPLAY, OTHER

### 4. Decyzja

Jeśli liczba błędów w próbce < 10% → kategoryzacja OK, przechodzimy do issue #6.
Jeśli ≥ 10% błędów → analiza gdzie Gemini myli kategorie i ewentualny re-run na
podejrzanych rekordach.

## Następny krok po zatwierdzeniu

Uruchomienie `data/build_dataset.py` — issue #6.
