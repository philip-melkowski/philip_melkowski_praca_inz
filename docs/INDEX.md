# Mapa dokumentów (stan 2026-10-27)

Zacznij od `STATUS.md`. Reszty szukaj tu. Kolumna „Status”: **aktualny**, **historyczny** (zapis stanu z danego dnia, nie poprawiany), **zastąpiony** (patrz wskazany plik). Plik, którego tu nie ma, jest błędem mapy: `uv run --python 3.13 tools/check_docs.py` to wykrywa.

## Czytaj najpierw

| Plik | Do czego | Status |
|---|---|---|
| `STATUS.md` | gdzie jesteśmy, co w toku, co czeka na autora (importowany z `CLAUDE.md`) | aktualny |
| `DECYZJE.md` | rejestr: co obowiązuje, co zastąpione lub odrzucone, z numerami wpisów | aktualny |
| `KONCEPCJA.md` | plan pracy (kanoniczna kopia; zmienia go tylko autor) | aktualny, z odchyleniami w `DECYZJE.md` |
| `DZIENNIK.md` | chronologia wszystkich kroków i decyzji (wpisy 1–112). **Czytaj od końca** albo `grep -n "^### 10[0-9]"`; dopisuj na dole | aktualny |

## Wyniki i analizy

| Plik | Do czego | Status |
|---|---|---|
| `WARSTWA3_PULA_PYTAN_2026-10-27.md` | warstwa 3: Clef 27B, pula 34 pytań + GBM (potwierdzenie na cal), sam model decyzyjny bez kNN, ścieżki odrzucone | aktualny (27.10; wpisy 111–112) |
| `WARSTWA3_nimble_wyniki.md` | wynik testu go/no-go warstwy 3 na `nimble` (train i cal), cele G1–G8 | historyczny (24.10); dalsze modele: wpisy 95–104, nowsze wyniki w pliku wyżej |
| `WARSTWA3_propozycja.md` | warianty A–E i cele G1–G8 przed testem | historyczny; wyniki w pliku wyżej |
| `PRZEMYSLENIA_2026-10-25.md` | opinie asystenta i wyniki agentów badawczych (literatura, szum etykiet, benchmark); **sekcja 9: znane niespójności dokumentów** | aktualny; to propozycje, nie decyzje |
| `CELE_PRZED_TESTEM.md` | cele liczbowe C1–C6 przed otwarciem testu | propozycja niezatwierdzona; zdanie o warstwie 3 nieaktualne (D16) |
| `POSTEPY_2026-10-19.md`, `POSTEPY_2026-10-19.pdf` | podsumowanie wyników warstw 1–2 | historyczny (19.10; bez warstwy 3 i nowych danych) |
| `figures/` | wykresy do pracy i prezentacji (`prezentacja/` dla slajdów) | aktualny |
| `kontrola_ludzka/` | ocena 100 odpowiedzi przez człowieka; **pliki ok. 3000 linii, klucze `klucz*.json` zawierają oceny sędziego: nie czytać w całości** | aktualny (oceny ostateczne: `zadanie_warstwowe_ostateczne.md`) |

## Uruchamianie i integracja z DF

| Plik | Do czego | Status |
|---|---|---|
| `ROUTER_URUCHOMIENIE.md` | instalacja i uruchomienie usługi `router` w DF | aktualny (zdanie „nie uruchamiana z Qwenem” nieaktualne od wpisu 70) |
| `ROUTER_TESTY_CURL.md` | zestaw żądań curl z oczekiwanymi i zaobserwowanymi wynikami | aktualny; testy E i G niewykonane |
| `START_KOMPUTER_SLUZBOWY.md` | notatka startowa z 24.10 dla komputera służbowego | zastąpiony przez `CLAUDE.md` i `STATUS.md` |

## Praca i prezentacja

| Plik | Do czego | Status |
|---|---|---|
| `praca/01_dane_i_etykiety.md`, `praca/02_router.md` | robocze szkice rozdziałów (z [UZUPEŁNIĆ]) | aktualny, do redakcji przez autora |
| `PREZENTACJA_zarys.md` | zarys 12 slajdów | historyczny |
| `prezentacja_postepy.pptx`, `prezentacja_notatki.js` | stara kopia prezentacji (16 slajdów) | zastąpiony: aktualna jest prezentacja Keynote autora (15 slajdów od 27.10, poza repozytorium, wpis 114); nie przebudowywać |
| `references/routellm_notes.md`, `references/routellm_notes.pdf` | notatki z RouteLLM (ok. 470 linii; czytać fragmentami) | aktualny |
| `references/STRUKTURA_REPO_DLA_AGENTOW.md` | przegląd literatury o urządzaniu repozytorium dla agentów i co z niego zastosowano | aktualny |

## Przygotowanie danych i analizy warstwy 1 (etap 1–2)

| Plik | Do czego | Status |
|---|---|---|
| `stage1/reports/`, `stage1/decisions/` | raporty z zebrania i oczyszczenia danych, limit embeddingu (`EMBED_LIMIT.md`), znane problemy | historyczny; część dotyczy starego planu |
| `stage2/reports/`, `stage2/decisions/` | analiza długości i słów kluczowych dla warstwy 1 | historyczny; liczby na starych etykietach, powtórzone na zmierzonych w `eval/` |

## Poza `docs/`

| Ścieżka | Do czego |
|---|---|
| `CLAUDE.md` | zasady, komendy, pułapki (czytane automatycznie) |
| `README.md` | opis repozytorium dla człowieka |
| `eval/README.md`, `data/README.md` | indeksy skryptów i plików danych (z odsyłaczami do wpisów dziennika) |
| `tools/check_docs.py` | sprawdza spójność dokumentacji (mapa, linki, długość `STATUS.md`, numer wpisu) |
| `archiwum/v1/` | stare plany (nieobowiązujące, nie usuwać) |
| `data/router/router_index_train_cal.npz` | indeks kNN dla `RouterService` (wektory i etykiety, bez treści pytań) |
