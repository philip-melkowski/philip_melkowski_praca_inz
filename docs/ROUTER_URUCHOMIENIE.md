# Uruchomienie routera w DeepFellow Infra

Stan: usługa `router` napisana, przetestowana jednostkowo i integracyjnie oraz sprawdzona end-to-end na odizolowanej instancji DF z modelami Gemini jako „mały” i „duży” (wpisy 25–26, 33, 39 w `DZIENNIK.md`); **nie uruchamiana jeszcze z Qwenem 8B/27B**. Poniższa instrukcja jest do wykonania na komputerze, na którym stoją oba modele i DF.

## 1. Indeks kNN

Na tym komputerze (z danymi):

```bash
cd deepfellow-router
uv run eval/export_index.py --splits train          # do eksperymentów
uv run eval/export_index.py --splits train cal      # indeks końcowy do testu
```

Powstaje `data/datasets/router_index.npz` (tablice `vectors` ×768 i `labels`, 0/1 dla Δ > 0,25). Skopiuj plik na komputer z DF (ścieżka lokalna dla procesu DF; jeśli DF działa w kontenerze, plik musi być w zamontowanym katalogu).

Uwaga: nie nadpisuj indeksu „train” indeksem „train+cal” przed ostatecznym testem na zbiorze `test`, jeśli chcesz porównywać wyniki cal.

## 2. Embedding

W DF musi działać usługa embeddingów z modelem `nomic-embed-text` (np. `ollama-external` na natywnej Ollamie, jak w `docs/stage1/decisions/EMBED_LIMIT.md`). Prefiks `classification: ` jest dodawany przez router.

## 3. Instalacja usługi i modelu `router` (API administratora)

Zamień `ADMIN_KEY`, nazwy modeli i ścieżkę do indeksu.

```bash
curl -X POST http://localhost:8086/admin/services/router \
  -H "Authorization: Bearer ADMIN_KEY" -H "Content-Type: application/json" \
  -d '{"spec": {
        "small_model": "qwen3:8b",
        "large_model": "Qwen/Qwen3.8-27B-FP8",
        "index_path": "/ścieżka/do/router_index.npz",
        "heuristics_path": "/ścieżka/do/router_l1.json",
        "heuristic_threshold": "2",
        "k": "20",
        "threshold": "0.3"
      }}'

curl -X POST "http://localhost:8086/admin/services/router/models/_?model_id=router" \
  -H "Authorization: Bearer ADMIN_KEY" -H "Content-Type: application/json" -d '{}'
```

Warstwa 1 ma dwie części (obie opcjonalne). **Heurystyki** przyznają punkty: +1 za frazę z listy COMPLEX i −1 za frazę z listy SIMPLE (listy z taksonomii Blooma i AgentBus), +1 powyżej 400 znaków, kolejny +1 powyżej 1500, −1 gdy ponad 10% znaków to cyfry, +1 za adres URL. Tabela punktów i listy fraz są w pliku `data/router_l1.json` (w repozytorium pracy; generuje go `eval/l1_points.py`) i można je edytować. Gdy suma punktów dojdzie do progu `heuristic_threshold` (domyślnie 2), pytanie idzie od razu do dużego modelu, bez embeddingu i bez warstwy 2; poniżej progu decyduje kNN. Bez `heuristics_path` heurystyki są wyłączone. Kalibracja progu (3010 pytań): próg 2 pkt obejmuje 6,4% pytań, wśród nich 51,8% COMPLEX (bazowo 37,4%); próg 3 pkt obejmuje 1,8%, wśród nich 54,7%. **Reguły administratora** (domyślnie wyłączone): `"force_large_over_chars": "4000"`, `"force_large_keywords": "prove, derive"`.

## 4. Użycie

```bash
curl -i http://localhost:8086/v1/chat/completions \
  -H "Authorization: Bearer API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"router","messages":[{"role":"user","content":"What is 17*23?"}],"reasoning_effort":"none"}'
```

W nagłówkach odpowiedzi: `X-Router-Model` (wybrany model), `X-Router-Layer` (`knn`, `rules` lub `fallback`), `X-Router-Score` (wynik 0–1). Każda decyzja jest też logowana jako JSON (`router decision: {...}`).

## 5. Próg

Próg `threshold` (0–1) ustawia administrator. Orientacyjne wartości z pomiaru poza próbką (kNN k=20, train+cal, Δ > 0,25; zob. `POSTEPY_2026-10-19.md`):

| Próg | Do dużego | Jakość (0–1) |
|---|---|---|
| 0,20 | 76,5% | 0,819 |
| 0,30 | 54,3% | 0,777 |
| 0,40 | 35,1% | 0,734 |
| 0,50 | 20,1% | 0,694 |

(„Zawsze duży” 0,846, „zawsze mały” 0,625.)

## 6. Co sprawdzić przy pierwszym uruchomieniu

1. Czy usługa `router` pojawia się w WebUI i czy formularz poprawnie pokazuje pola.
2. Czy po restarcie DF opcje wczytują się z `services.json` i model `router` jest ponownie zarejestrowany.
3. Czy nagłówki `X-Router-*` docierają do klienta także przy `"stream": true`.
4. Opóźnienie: porównaj czas odpowiedzi `router` z czasem bezpośredniego wywołania wybranego modelu; narzut routingu powinien wynosić dziesiątki ms (embedding przez DF + kNN).
5. Zachowanie przy wyłączonym embeddingu (powinno przejść na duży model, nagłówek `X-Router-Layer: fallback`) oraz gdy mały model zwróci błąd 404/408/429/5xx (też `fallback`; sprawdzone w e2e na wycofanym modelu Gemini).

Już sprawdzone w e2e (odizolowana instancja DF na porcie 8087 z `DF_STORAGE_DIR` poza repo, bez mesh i bez Dockera): punkty 1 (usługa widoczna w `GET /admin/services`), 2 (po restarcie model `router` wczytuje się z `services.json`) i 3 (nagłówki przy `stream: true`). WebUI nie było sprawdzane.
