# Szkic: implementacja w DeepFellow Infra (roboczy, do redakcji przez autora)

Status: szkic asystenta z 2026-11-22, zbudowany z dziennika (`../DZIENNIK.md`, wpisy 27, 49, 62–70, 115–118). Miejsca **[UZUPEŁNIĆ]** wymagają danych lub decyzji autora.

## 1. Miejsce routera w DeepFellow Infra

DeepFellow Infra (DF) to samodzielnie hostowana infrastruktura modeli z API zgodnym z OpenAI. Usługi (Ollama, vLLM, usługi chmurowe) rejestrują swoje modele w rejestrze punktów końcowych (`EndpointRegistry`), a klient woła je przez `/v1/chat/completions`, `/v1/embeddings` itd. Router zrealizowano jako zwykłą usługę DF, `RouterService` (klasa bazowa `Base2Service`), a nie jako wtyczkę serwera aplikacji (D10). Usługa rejestruje jeden model o nazwie `router`. Dla klienta to po prostu kolejny model: zmiana z dużego modelu na router polega na zmianie pola `model` w żądaniu.

Router nie ma własnego kontenera ani połączeń sieciowych. Wszystkie wywołania (embedding, model decyzyjny, mały i duży model) idą przez ten sam rejestr DF. Dzięki temu router działa z każdym modelem, który DF udostępnia: lokalnym, chmurowym albo przyłączonym z innej infrastruktury przez mesh.

## 2. Przebieg decyzji

Dla każdego żądania router bierze ostatnią wiadomość użytkownika i przechodzi przez kaskadę:

1. **Reguły i heurystyki (warstwa 1, opcjonalna).** Reguły administratora (długość, słowa kluczowe dopasowywane jako całe słowa) oraz punkty heurystyk z pliku `router_l1.json`. Suma punktów od progu (domyślnie 2) kieruje żądanie od razu do dużego modelu, bez liczenia embeddingu (D12). Warstwa działa tylko w stronę dużego modelu.
2. **kNN na embeddingach (warstwa 2).** Embedding `nomic-embed-text` z prefiksem `classification: `, 20 najbliższych sąsiadów w indeksie (wektory i etykiety 0/1, plik `.npz`), wynik = średnia etykiet ważona podobieństwem (D13).
3. **Model decyzyjny (warstwa 3, opcjonalna).** Tylko gdy wynik kNN leży w strefie niepewności [0,20; 0,45): zapytanie i 8 pytań tak/nie trafiają do modelu decyzyjnego przez `/v1/systemone`; regresja logistyczna łączy logit wyniku kNN z logitami odpowiedzi (parametry w pliku JSON, `decider_path`). Opis eksperymentu: rozdział o warstwie 3.
4. **Próg.** Wynik końcowy (kNN albo warstwa 3) porównywany z progiem administratora (domyślnie 0,3): od progu w górę duży model, poniżej mały.

**Awaria zawsze kończy się dużym modelem (D14).** Dotyczy to błędu embeddingu, błędu lub przekroczenia czasu modelu decyzyjnego (5 s) oraz odpowiedzi małego modelu z kodem 404, 408, 429 lub 5xx (wtedy żądanie jest powtarzane na dużym). Uzasadnienie: pomyłka w stronę dużego modelu kosztuje zasoby, a w stronę małego jakość.

Każda odpowiedź niesie nagłówki `X-Router-Model`, `X-Router-Layer` (`rules`, `heuristics`, `knn`, `decider`, `fallback`), `X-Router-Score` i, przy warstwie 3, `X-Router-Decider-Score`. Każda decyzja jest też zapisywana w logu jako jedna linia JSON z czasem decyzji. Strumieniowanie (`stream: true`) działa bez zmian, nagłówki są wysyłane przed pierwszym fragmentem.

## 3. Konfiguracja

Usługę instaluje administrator przez API lub panel DF. Formularz: mały i duży model, ścieżka indeksu, model embeddingowy i prefiks, k, próg, ścieżka heurystyk i ich próg, ścieżka parametrów warstwy 3, reguły. Zmiana pary modeli wymaga nowych etykiet i nowego indeksu (pomiar jak w rozdziale o danych: ok. 1,5 doby generowania i ok. 8 USD za sędziego dla 4313 pytań). Parametry warstwy 3 eksportuje skrypt `eval/export_layer3_params.py` (uczenie tylko na train).

## 4. Testy

- **Testy jednostkowe i integracyjne:** testy routera w zestawie DF (rdzeń, usługa, integracja z prawdziwym rejestrem), w tym warstwa 3 (wzór, strefa, awaria, limit czasu, nagłówki). Cały zestaw DF przechodzi (6394 testy na 22.11), `just check` (ruff, pyright strict, kontrola uwierzytelniania) bez błędów.
- **Test na prawdziwych modelach** (wpis 70): `qwen3:8b` i `Qwen/Qwen3.8-27B-FP8` przez DF; zapytania trafiły do właściwych modeli, nagłówki i strumieniowanie działają.
- **Awaria embeddingów (test E, wpis 117):** po zatrzymaniu Ollamy zapytanie trafia do dużego modelu (`fallback`); po jej powrocie router sam wraca do kNN.
- **Restart DF (test G, wpis 117):** po restarcie usługa i model `router` wracają bez ponownej instalacji.
- **Awaria modelu decyzyjnego (wpisy 116–117):** nieznany model (404) kończy się dużym modelem; wynik kNN zostaje w nagłówku.
- **Pokaz na seminarium (28.10, wpis 116):** pięć zapytań, po jednym na każdą drogę decyzji, z wynikami zgodnymi z przewidzianymi offline.

## 5. Opóźnienie

| Pomiar | Wynik | Źródło |
|---|---|---|
| Sama decyzja warstw 1+2 (bez DF, Mac M1, natywna Ollama) | mediana 20,6 ms, p90 65,5 ms | wpis 23 |
| Narzut routera przez DF (różnica czasów, 5 pomiarów, Mac) | ok. 13 ms (kilka–kilkanaście ms) | wpis 70 |
| Decyzja: heurystyki / kNN / warstwa 3 z Clefem przez internet | 0,1 ms / 18–28 ms / ok. 335 ms | wpis 116 |
| GPU (RTX 5070 Ti, Ollama, przez tunel SSH): embedding | p50 36 ms, p90 69 ms | wpis 118 |
| GPU: model decyzyjny d1 3B, 8 pytań | p50 110 ms, p90 148 ms; ok. 12,5 żądań/s przy 4 naraz | wpis 118 |
| GPU: mały model `qwen3:8b` | ok. 112 tokenów/s | wpis 118 |

Wniosek: warstwy 1–2 dodają kilkadziesiąt milisekund, czyli mało wobec generowania odpowiedzi (sekundy). Warstwa 3 kosztuje ok. 0,1 s na GPU przy 8 pytaniach, ale tylko dla zapytań w strefie niepewności (ok. połowa ruchu). **[UZUPEŁNIĆ: benchmark całego routera w DF na docelowym sprzęcie: p50/p90 opóźnienia i przepustowość wobec „zawsze duży”.]**

## 6. Ograniczenia wdrożenia

- Katalog modeli DF (`static/ollama-min.json`) zalicza `d1:3b` do zwykłych modeli językowych, więc DF nie udostępnia go pod `/v1/systemone`; użycie d1 jako modelu decyzyjnego w DF wymaga dopisania go do katalogu (wpis 118).
- Indeks jest plikiem ładowanym przy instalacji; dołożenie nowych etykiet wymaga ponownej instalacji usługi.
- Router decyduje na podstawie ostatniej wiadomości użytkownika; kontekst rozmowy wieloturowej nie jest brany pod uwagę.
- **[UZUPEŁNIĆ: stan integracji z głównym repozytorium DF (merge request).]**
