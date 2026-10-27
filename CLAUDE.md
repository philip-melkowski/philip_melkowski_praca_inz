# CLAUDE.md — deepfellow-router

Praca inżynierska: dynamiczny i semantyczny routing zapytań LLM według złożoności, zintegrowany z DeepFellow Infra (DF) jako `RouterService`. Repozytorium pracy; framework DF jest w osobnym klonie (ścieżki niżej). Ten plik ma być krótki: stan prac jest w `docs/STATUS.md`, decyzje w `docs/DECYZJE.md`, mapa dokumentów w `docs/INDEX.md`.

@docs/STATUS.md

## Start i koniec sesji
- Start: stan jest wczytany powyżej. Potem `git pull --ff-only` i `git log --oneline -10`. Dziennik (`docs/DZIENNIK.md`, ok. 700 linii) czytaj od końca (`tail`, `grep -n "^### 10[0-9]"`), nie w całości. Pytasz o plan: `docs/KONCEPCJA.md`; o to, co z planu nie obowiązuje: `docs/DECYZJE.md`.
- Koniec: dopisz wpis do `docs/DZIENNIK.md` (kolejny numer, data, co i dlaczego, w tym odrzucone opcje), zaktualizuj `docs/STATUS.md` (data, „w toku”, numer ostatniego wpisu), zmień `docs/DECYZJE.md` jeśli coś zapadło, dodaj nowe dokumenty do `docs/INDEX.md`, uruchom `uv run --python 3.13 tools/check_docs.py`.
- Ta wiedza musi leżeć w repozytorium: pamięć konta Claude jest lokalna, drugi komputer i drugie konto jej nie widzą.

## Zasady współpracy z autorem (obowiązują każde konto)
- Po polsku, prostym językiem, krok po kroku. Nie używaj słowa „pomija”.
- **Pytanie to nie polecenie.** Na pytanie tylko odpowiedz; nie zmieniaj plików, planu, kodu, notatek ani prezentacji bez wyraźnej prośby (co najwyżej zaproponuj w jednym zdaniu i poczekaj).
- **Sprawdzaj od razu to, co da się zweryfikować** (pliki, liczby, licencje, dokumentacja w sieci). Nigdy nie kwestionuj słów autora, zanim sprawdzisz; zgadywanie zamiast sprawdzenia to ten błąd, który autor poprawiał najczęściej.
- Nie zmieniaj planu ani architektury bez pytania; zmianę zapisz w dzienniku i w `docs/DECYZJE.md`. Swoje propozycje oznaczaj jako propozycje asystenta, nie jako decyzje.
- Nic nie usuwaj ani nie przenoś bez pytania (pliki, katalogi, gałęzie, klony). Nie przebudowuj historycznych dokumentów.
- Płatne wywołania API (Gemini, Jev w chmurze): tylko po zgodzie autora na konkretny wydatek. Nie wysyłaj danych z `data/datasets/` do zewnętrznych usług.
- Commit i push tylko na prośbę autora. Push wyłącznie do `origin` (fork `philip-melkowski/philip_melkowski_praca_inz`); do repozytorium `simplito` nigdy. W DF nie dodawaj `Co-Authored-By` (ich `CLAUDE.md` tego zakazuje).
- Wyniki podawaj wiernie: jeśli test nie przeszedł albo krok pominięto, napisz to wprost, z wyjściem polecenia.
- Prezentacja postępów istnieje jako plik Keynote autora (poza repozytorium; lokalizację poda autor).
- Autor skarży się na wolne i skomplikowane odpowiedzi: bądź zwięzły i efektywny.

## Twarde reguły danych i pomiaru
- **Zbiór `test` jest zamknięty**: nie używać go do strojenia, wyboru ani podglądu wyników. Strojenie tylko walidacją krzyżową po grupach na train; `cal` jest „zużyty” (`docs/DECYZJE.md` D15, D15a): kolejne użycie tylko za zgodą autora, z planem porównań zapisanym przed wynikiem.
- Zestaw pytań warstwy 3 `eval/layer3_questions/v1.json` jest zamrożony (SHA-256 w dzienniku, wpis 91): nie edytować.
- Klucz Gemini tylko w `~/.config/inz/gemini_key` (chmod 600): nigdy w czacie, komendach, plikach ani logach. Klucz DF (`API_KEY`) bierze się z `~/.zshrc` autora.
- `docs/kontrola_ludzka/klucz*.json` zawierają oceny sędziego: nie czytać przed oceną człowieka.

## Komendy
- Python 3.13, `uv`, strict pyright. Skrypty z nagłówkiem `# /// script` uruchamiaj `uv run --python 3.13 plik.py` (systemowy `python3` jest za stary).
- Skrypty danych: `data/` (kolejność i opis: `data/README.md`). Analizy: `eval/` (opis i wpisy dziennika: `eval/README.md`). Zbiory w `data/datasets/` nie są w gitcie.
- Sprawdzenie dokumentacji: `uv run --python 3.13 tools/check_docs.py`.
- DF (poza tym repozytorium): komputer prywatny `../kod/deepfellow-infra` (gałąź `feat/router-service`, jedyny właściwy klon); komputer służbowy `../deepfellow-infra`. Komendy DF (`just dev`, `just test`, `just check`) uruchamiaj w jego katalogu.

## Pułapki
- Ścieżki `../` w starszych dokumentach zakładają układ komputera prywatnego; układ obu komputerów: `docs/STATUS.md`.
- Nieśledzone `deepfellow-infra/` i `do_przeniesienia/` w katalogu repozytorium to pozostałości: nie dodawać do gita, nie używać.
- Dokument oznaczony w `docs/INDEX.md` jako historyczny lub zastąpiony nie opisuje stanu obecnego; w razie rozbieżności wygrywa `docs/DECYZJE.md` (decyzje autora zapadłe po napisaniu planu), dalej `docs/KONCEPCJA.md`. Plan i decyzje zmienia tylko autor.
