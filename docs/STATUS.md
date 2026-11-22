# STATUS: od tego pliku zaczyna każda sesja

Stan na: **2026-11-22**. Ostatni wpis dziennika: **129**. Plik jest importowany z `CLAUDE.md`, więc musi być krótki (≤ 100 linii; sprawdza to `tools/check_docs.py`). Szczegóły są w dokumentach, do których odsyłam; **liczb nie kopiuj z innych miejsc bez sprawdzenia, tu jest ich tylko tyle, ile trzeba**.

**Obowiązek na koniec sesji:** zaktualizuj ten plik (data, „w toku”, „następne kroki”, numer ostatniego wpisu), dopisz wpis do `DZIENNIK.md`, uruchom `uv run --python 3.13 tools/check_docs.py`. Commit i push tylko na prośbę autora.

## Projekt w czterech zdaniach
Praca inżynierska: `RouterService` w DeepFellow Infra (DF) wybiera dla każdego zapytania mały model (`qwen3:8b`) albo duży (`Qwen/Qwen3.8-27B-FP8`). Etykieta jest zmierzona: Δ = jakość dużego − średnia jakość małego (3 próbki), COMPLEX gdy Δ > 0,25. Kaskada: warstwa 1 (heurystyki punktowe) → warstwa 2 (kNN na embeddingach `nomic-embed-text`) → opcjonalna warstwa 3 (model decyzyjny w strefie niepewności) → awaria zawsze do dużego. Plan: `KONCEPCJA.md`; co z niego już nie obowiązuje: `DECYZJE.md`.

## Gdzie jesteśmy (fakty)
- **Zbiór test otwarty raz 22.11** na zamrożonym routerze (`PROTOKOL_TESTU_2026-11-22.md`, wyniki `WYNIKI_TESTU_2026-11-22.md`, wpisy 124–127). **Sukces główny spełniony** (D22, etykiety v3, w dziedzinie 766): R0 − długość APGR +0,055 [+0,019; +0,092], AUROC 0,674 ≥ 0,64; R0 − źródło nie wykazano (−0,003). C3, C4 spełnione; C5: p50 12,5 ms z Ollamą przy DF (spełniony), 61 ms przez tunel do GPU. **Warstwa 3 (R1, d1) na teście: APGR +0,022 [+0,010; +0,035]**, mniej poważnych błędów. Po otwarciu niczego w routerze nie zmieniać.
- **Router zamrożony:** heurystyki (`router_l1.json`, próg 2) + kNN k=20 na `data/router/router_index_final.npz` (train + cal + `extra_train`, etykiety v3) + opcjonalnie warstwa 3 `router_l3_d1_final.json` (d1:3b, zestaw v1 + regresja logistyczna, strefa 0,20–0,45). Sumy SHA w protokole.
- **Dane:** 4313 pytań pomiaru głównego (train 2151 / cal 859 / test 1294 z etykietą; etykiety v3 w `data/labels/` po ponownej ocenie odpowiedzi z limitem 4096, wpis 124) + 1500 nowych (Dolly, CodeChat, Arena 140k; 1498 z etykietą, COMPLEX 49,9%): `extra_train` 1051 (w indeksie), `extra_val` 449 (świeża walidacja zamiast zużytego cal; D21). Pliki danych poza gitem; same liczby w `data/labels/`.
- **Analizy (train):** szum etykiet (AUROC na wyraźnym Δ 0,75), spadek jakości 2,9 / 7,1 / 9,6% przy 20 / 40 / 50% do małego, ocena odpowiedzi małego (kaskada) AUROC 0,81 wobec kNN 0,67 (wpisy 117, 125). Progi z gwarancją: Bonferroni (D20), na teście dotrzymane.
- **DF:** `RouterService` w forku (`feat/router-service`, ostatnio edf2a22: d1 w katalogu modeli decyzyjnych; d654a30: słowa kluczowe jako całe słowa). Testy E i G zaliczone. Gałąź `demo/seminarium-dftest` lokalnie (do usunięcia na polecenie autora). Clef na df.test nazywa się teraz `clef:27b`.
- **GPU:** df-5070ti-03 (RTX 5070 Ti 16 GB) przez tunele autora (DF `localhost:18088`, Ollama `localhost:21434`); d1 v1 p50 0,11 s; Ollama trzyma domyślnie 3 modele (przy 4 warstwa 3 przekracza limit czasu).
- **Tekst pracy:** szkice w `docs/praca/` (`00_wstep_i_literatura.md` … `06_ograniczenia_wnioski.md`: wstęp i literatura, dane, router, implementacja, warstwa 3, ewaluacja, ograniczenia i wnioski) z [UZUPEŁNIĆ]/[SPRAWDZIĆ]. Prezentacja: plik Keynote autora (poza repozytorium); slajd 9 (tabela ryzyka) do poprawy wg D20 – na polecenie autora.

## W toku / następne kroki (propozycje asystenta)
1. Redakcja szkiców przez autora; sprawdzenie źródeł oznaczonych [SPRAWDZIĆ]; deklaracja użycia narzędzi AI.
2. Rozdział o danych: sekcja 6a dopisana 22.11 (nowe źródła, etykiety v3, podział); do redakcji.
3. Prezentacja (na polecenie autora): wyniki testu, poprawiona tabela ryzyka (slajd 9).
4. Opcjonalnie: merge request do DF (router + d1 w katalogu), pomiar oszczędności w realnym ruchu.

## Decyzje czekające na autora
- Usunięcie gałęzi pokazowej DF i dwóch niepotrzebnych klonów DF (zob. niżej).
- Czy wynik warstwy 3 na teście zmienia jej rolę w pracy (teraz: wariant dodatkowy, D17).

## Dwa komputery
| | prywatny | służbowy |
|---|---|---|
| repozytorium | `inz/deepfellow-router` | `inz/philip_melkowski_praca_inz` |
| klon DF | `inz/kod/deepfellow-infra` (jedyny właściwy) | `inz/deepfellow-infra` (wg autora; DF z endpointem `systemone` uruchamiany z gałęzi GitLaba, wpis 85) |
| dane | pełny pomiar, `answers.jsonl`, klucz Gemini `~/.config/inz/gemini_key` | kopia rdzenia, wyniki warstwy 3, nowe pytania i odpowiedzi; Mac M5 16 GB, Ollama, VPN do `df.test.simplito.com`, tunel do `df-5070ti-03` |
Ścieżki `../` w starych dokumentach zakładają układ komputera prywatnego. `data/datasets/` nie jest w gitcie (lista plików: `data/README.md`).

## Pułapki (wiedza, której nie widać z kodu)
- W katalogu `inz/deepfellow-router/` leżą nieśledzone `deepfellow-infra/` (uszkodzony klon, `bad object HEAD`) i `do_przeniesienia/`; w `inz/deepfellow-infra` (poziom wyżej) jest inny, stary klon. Nie używać żadnego z nich.
- Dokumenty o AUROC warstwy 1 podają 0,577 (wersja logistyczna) albo 0,555 (punktowa, ta w usłudze); lista znanych niespójności: `PRZEMYSLENIA_2026-10-25.md` pkt 9.
- `docs/kontrola_ludzka/` (cztery pliki po ok. 3000 linii, klucze z ocenami sędziego): nie czytać w całości.
- `data/judge_open.py --output` to ścieżka względem bieżącego katalogu (nie `data/datasets/`), a `data/finalize_v3.py` czyta z `data/datasets/`: podawaj `--output data/datasets/<plik>`. Skrypt jest wznawialny (pomija ocenione identyfikatory).
- `*.jsonl` jest w `.gitignore`: pliki z liczbami w `data/labels/` dodawaj `git add -f` (tylko liczby, bez treści; repozytorium jest publiczne). Reguła uprawnień Claude Code może blokować płatne wywołania sędziego; autor uruchamia je wtedy sam przez `!`.
- Przepisana historia GitHuba (29.10): po `git fetch` lokalna gałąź może być „ahead/behind”; sprawdź `git patch-id` commitów, potem `reset --hard origin/...` (zob. wpis 124).
