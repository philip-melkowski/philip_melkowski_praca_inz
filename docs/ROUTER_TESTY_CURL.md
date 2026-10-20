# Testy RouterService: zestaw żądań curl

Zestaw żądań do pokazania działania routera w DeepFellow Infra (`model=router`). Każde żądanie ma krótki opis, co sprawdza, oraz oczekiwany wynik. Tam, gdzie test został uruchomiony na prawdziwych modelach (2026-10-20, `qwen3:8b` i `Qwen/Qwen3.8-27B-FP8`), podany jest zaobserwowany wynik. Pozostałe mają tylko oczekiwanie i są oznaczone jako „nieuruchomione”.

## Jak czytać wynik

Router dopisuje do odpowiedzi trzy nagłówki:

| Nagłówek | Znaczenie |
|---|---|
| `X-Router-Model` | model, który odpowiedział (mały `qwen3:8b` albo duży `Qwen/Qwen3.8-27B-FP8`) |
| `X-Router-Layer` | warstwa, która podjęła decyzję: `heuristics` (warstwa 1), `knn` (warstwa 2), `fallback` (awaria routera → duży model) |
| `X-Router-Score` | wynik kNN od 0 do 1 (udział pytań trudnych wśród 20 najbliższych sąsiadów); powyżej progu 0,3 → duży model. Przy warstwie `heuristics` nagłówka nie ma, bo embedding w ogóle nie jest liczony |

Warstwa 1 (heurystyki) działa tylko w jedną stronę: zapytanie z co najmniej 2 punktami idzie od razu do dużego modelu. Zapytanie poniżej 2 punktów przechodzi do kNN.

Konfiguracja z testu: `k = 20`, `threshold = 0.3`, `heuristic_threshold = 2`, indeks z 3010 pytań (train + cal).

## Przygotowanie

```bash
export BASE=http://localhost:8086
export KEY=API_KEY          # klucz API DeepFellow (z testu: wartość API_KEY)
```

Sprawdzenie, jakie modele widzi DeepFellow (powinny być `router`, `qwen3:8b`, `Qwen/Qwen3.8-27B-FP8`):

```bash
curl -s $BASE/v1/models -H "Authorization: Bearer $KEY"
```

Każde żądanie poniżej ma `-i` (pokazuje nagłówki) i `"reasoning_effort":"none"` (wyłącza tryb myślenia, żeby odpowiedzi były krótkie).

---

## 1. kNN: proste pytanie → mały model (test A)

**Sprawdzamy:** czy proste pytanie faktograficzne trafia do małego modelu przez warstwę 2.

```bash
curl -i $BASE/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","messages":[{"role":"user","content":"What is the capital of France?"}],"reasoning_effort":"none"}'
```

- Oczekiwane: `X-Router-Model: qwen3:8b`, `X-Router-Layer: knn`, niski `X-Router-Score` (< 0,3).
- Zaobserwowane: `qwen3:8b`, `knn`, wynik **0,1947**. Odpowiedź: „The capital of France is Paris.”

## 2. kNN: trudne pytanie otwarte → duży model (test B)

**Sprawdzamy:** czy pytanie kreatywne i długie trafia do dużego modelu przez kNN (heurystyki dają mu tylko 1 punkt, więc same go nie przekierują).

```bash
curl -i $BASE/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","messages":[{"role":"user","content":"Write a long fantasy story where a dragon and a knight argue about whether loyalty or freedom matters more, with vivid dialogue and a twist ending."}],"reasoning_effort":"none"}'
```

- Oczekiwane: duży model, `knn`, wynik ≥ 0,3.
- Zaobserwowane: `Qwen/Qwen3.8-27B-FP8`, `knn`, wynik **0,7035**. Duży model napisał całe opowiadanie (2509 tokenów).

## 3. Heurystyki: pytanie z wieloma frazami trudności (test C)

**Sprawdzamy:** czy warstwa 1 kieruje do dużego modelu bez liczenia embeddingu. Fraza „analyze”, „compare”, „evaluate”, „trade-offs”, „step by step” = 5 punktów (próg 2).

```bash
curl -i $BASE/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","messages":[{"role":"user","content":"Analyze and compare these two designs, then evaluate the trade-offs step by step."}],"reasoning_effort":"none"}'
```

- Oczekiwane: duży model, `X-Router-Layer: heuristics`, brak nagłówka `X-Router-Score`.
- Zaobserwowane: `Qwen/Qwen3.8-27B-FP8`, `heuristics`, nagłówka wyniku brak. (Duży model odpisał, że brakuje samych projektów do porównania, co jest poprawne, bo pytanie było tylko próbą reguły.)

## 4. Streaming (test D)

**Sprawdzamy:** czy nagłówki `X-Router-*` docierają także przy odpowiedzi strumieniowej (`stream: true`).

```bash
curl -i -N $BASE/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","stream":true,"messages":[{"role":"user","content":"What is 17*23?"}],"reasoning_effort":"none"}'
```

- Oczekiwane: nagłówki przed pierwszym `data:`, strumień kończy się `data: [DONE]`.
- Zaobserwowane: `qwen3:8b`, `knn`, wynik **0,0973**, nagłówki przed strumieniem, strumień zakończony `data: [DONE]`.

## 5. Narzut opóźnienia routingu (test F)

**Sprawdzamy:** ile czasu router dodaje do odpowiedzi. To samo pytanie (trafia do małego modelu), raz przez `router`, raz bezpośrednio do `qwen3:8b`. Narzut to różnica czasów. Cel z planu pracy: poniżej 50 ms.

```bash
# przez router
for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{time_total}\n" $BASE/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","messages":[{"role":"user","content":"What is the capital of France?"}],"max_tokens":8,"reasoning_effort":"none"}'; done

# bezpośrednio do małego modelu
for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{time_total}\n" $BASE/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"What is the capital of France?"}],"max_tokens":8,"reasoning_effort":"none"}'; done
```

Zaobserwowane (sekundy):

| Seria | Pomiary | Średnia |
|---|---|---|
| przez router | 0,408 / 0,369 / 0,368 / 0,368 / 0,370 | 0,376 |
| bezpośrednio | 0,369 / 0,378 / 0,356 / 0,351 / 0,361 | 0,363 |

Narzut ok. 13 ms wg średnich (ok. 7 ms bez pierwszego, wolniejszego pomiaru), czyli poniżej celu 50 ms. Uwaga: tylko 5 pomiarów w serii, a rozrzut czasów bezpośrednich (ok. 27 ms) jest większy niż różnica, więc wynik oznacza „kilka do kilkunastu ms, na pewno poniżej 50”, a nie dokładną wartość.

---

## Dodatkowe zapytania (nieuruchomione)

Punkty heurystyk poniżej policzono kodem usługi (`HeuristicScorer` z `data/router_l1.json`). To jest pewne. Wynik kNN (wybór modelu przy < 2 punktach) zależy od embeddingu i **nie jest sprawdzony**, więc podano tylko oczekiwanie.

Wspólny szablon (podmień treść w `content`):

```bash
curl -i $BASE/v1/chat/completions -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","messages":[{"role":"user","content":"TREŚĆ"}],"reasoning_effort":"none"}'
```

| Nr | Treść zapytania | Punkty heurystyk | Sprawdzamy | Oczekiwane |
|---|---|---|---|---|
| 6 | `Compare the pros and cons of Postgres and MongoDB for a small web shop and recommend one.` | 3 | kilka fraz („compare”, „pros and cons”, „recommend”) | `heuristics` → duży |
| 7 | `Debug this and explain why it fails: def f(x): return x[1] if x else None` | 2 | próg dokładnie na granicy (2 punkty wystarczają) | `heuristics` → duży |
| 8 | `Design and implement a rate limiter, then optimize it and refactor the result.` | 4 | zadanie programistyczne | `heuristics` → duży |
| 9 | `Compare these two articles https://example.com/a and https://example.com/b.` | 2 | URL daje punkt (1) i razem z „compare” (1) osiąga próg | `heuristics` → duży |
| 10 | `Translate 'good morning' into German.` | −1 | fraza prosta („translate”) odejmuje punkt | `knn`, spodziewany mały |
| 11 | `Define the word 'entropy'. List three examples.` | −2 | dwie frazy proste („define”, „list”) | `knn`, spodziewany mały |
| 12 | `Hello!` | 0 | bardzo krótkie, bez fraz | `knn` (wynik zależy od embeddingu) |
| 13 | `Plan a three day trip to Rome for two people who like museums but hate crowds.` | 1 | jedna fraza trudności, poniżej progu 2: heurystyka nie decyduje | `knn`, kierunek zależy od embeddingu |

## Testy niezakończone (nieuruchomione)

### Awaria warstwy kNN → duży model (test E)

**Sprawdzamy:** czy po awarii routera (tu: niedostępny model embeddingów) zapytanie nie ginie, tylko idzie do dużego modelu.

1. Zatrzymaj Ollamę (albo usługę z `nomic-embed-text`).
2. Wyślij żądanie z punktu 1 (stolica Francji).
3. Włącz Ollamę z powrotem.

- Oczekiwane: odpowiedź przychodzi od dużego modelu, `X-Router-Layer: fallback`. Nie wiadomo, czy nagłówek `X-Router-Score` jest wtedy obecny.
- Uwaga: przy zatrzymanej Ollamie mały model też jest niedostępny, ale ten test dotyczy tylko ścieżki do dużego modelu (vLLM).

### Restart DeepFellow (test G)

**Sprawdzamy:** czy usługa `router` i model `router` wracają same po restarcie, bez ponownej instalacji.

1. Zatrzymaj i uruchom DeepFellow (`just dev`).
2. Wyślij żądanie z punktu 1.

- Oczekiwane: odpowiedź i nagłówki jak w teście A, bez ponownego wywoływania `install` usługi.

## Co zobaczyć w logach DeepFellow

Każda decyzja jest zapisywana jako jedna linia:

```
router decision: {"model": ..., "layer": ..., "score": ..., "heuristic": ..., "latency_ms": ...}
```

Pole `latency_ms` to czas samej decyzji routera (bez generowania odpowiedzi), a `heuristic` to liczba punktów z warstwy 1.
