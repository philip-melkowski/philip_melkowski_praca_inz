# STATUS: od tego pliku zaczyna każda sesja

Stan na: **2026-10-27**. Ostatni wpis dziennika: **114**. Plik jest importowany z `CLAUDE.md`, więc musi być krótki (≤ 100 linii; sprawdza to `tools/check_docs.py`). Szczegóły są w dokumentach, do których odsyłam; **liczb nie kopiuj z innych miejsc bez sprawdzenia, tu jest ich tylko tyle, ile trzeba**.

**Obowiązek na koniec sesji:** zaktualizuj ten plik (data, „w toku”, „następne kroki”, numer ostatniego wpisu), dopisz wpis do `DZIENNIK.md`, uruchom `uv run --python 3.13 tools/check_docs.py`. Commit i push tylko na prośbę autora.

## Projekt w czterech zdaniach
Praca inżynierska: `RouterService` w DeepFellow Infra (DF) wybiera dla każdego zapytania mały model (`qwen3:8b`) albo duży (`Qwen/Qwen3.8-27B-FP8`). Etykieta jest zmierzona: Δ = jakość dużego − średnia jakość małego (3 próbki), COMPLEX gdy Δ > 0,25. Kaskada: warstwa 1 (heurystyki punktowe) → warstwa 2 (kNN na embeddingach `nomic-embed-text`) → opcjonalna warstwa 3 (model decyzyjny w strefie niepewności) → awaria zawsze do dużego. Plan: `KONCEPCJA.md`; co z niego już nie obowiązuje: `DECYZJE.md`.

## Gdzie jesteśmy (fakty)
- **Dane:** 4313 pytań (train 2157 / cal 862 / test 1294), 4304 z etykietą (train 2151 / cal 859); 35,4% COMPLEX. **Zbiór test jest zamknięty** i otwiera się raz. **Cal jest „zużyty”**: użyty do oceny kNN, porównania dwóch modeli warstwy 3 i (za zgodą autora, 27.10) jednego potwierdzenia puli v2 z Clefem; kolejne użycie tylko za zgodą autora, nowe warianty w walidacji krzyżowej po grupach na train (`DECYZJE.md` D15).
- **Warstwy 1–2 (offline, train+cal, 3010 pytań, CV po grupach):** kNN k=20 AUROC 0,682, APGR 0,605; sama warstwa 1 AUROC ok. 0,555. Sufit embeddingów ok. 0,68–0,71 (wpis 30), krzywa uczenia płaska.
- **Warstwa 3 (model decyzyjny przez `/v1/systemone`, zestaw 8 pytań v1 zamrożony):** `docs/WARSTWA3_nimble_wyniki.md`, wpisy 86–104. Na cal `nimble` i `basal-2.0-4.5B` przeszły G1 (zysk AUROC w strefie 0,20–0,45: +0,066 i +0,084), ale **cały router ze strefą poprawia się mało** (+0,013 n.s. i +0,019). Na train podobnie `strands-decider:2b`, `d1:3b`, `tev1:4b`; samoocena `qwen3:8b` słabsza, `laya` bez sygnału, `kev` przerwany (pamięć). Zero-shot jedno pytanie ≈ kNN uczony na ok. 1000–1500 etykiet (wpis 99). Opinia asystenta: opcjonalne rozszerzenie, nie rdzeń (`PRZEMYSLENIA_2026-10-25.md`). **Decyzja go/no-go należy do autora.**
- **Warstwa 3, 27.10 (`WARSTWA3_PULA_PYTAN_2026-10-27.md`, wpisy 111–112):** Clef 27B q4 (df.test) najlepszy model (v1, strefa +0,099). Pula 34 pytań (`pool_v2.json`) + GBM: strefa AUROC 0,708 na train, **na cal 0,699 vs v1 0,642 (+0,057, istotne)**; APGR routera nadal mało (+0,014 n.s. na cal). **Sam Clef bez kNN (pula + GBM) 0,744** ≈ kNN + Clef 0,750, a sam kNN 0,687: kNN dokłada niewiele. Nasycenie ok. 0,75; czas rośnie z liczbą pytań (8 → 0,4 s, 34 → 1,5 s przez internet). Odrzucone: łączenie modeli, duży Qwen jako oceniający, cel ciągły, pula v3, krótszy zestaw. **d1:3b z pulą + GBM ≈ Clef** (0,747 / strefa 0,696), więc tani model jest realną alternatywą; `strands-decider:2b` z pulą słabszy (0,726 / strefa 0,675).
- **Integracja DF:** `RouterService` jest w klonie DF (`kod/deepfellow-infra`, gałąź `feat/router-service`, fork `philip-melkowski/deepfellow-infra`; upstream `simplito` nigdy). Ma warstwy 1–2, awarię → duży; test z prawdziwymi Qwenami OK (wpis 70, narzut ok. 13 ms). **Niewykonane testy E (awaria embeddingów) i G (restart DF).** Warstwy 3 w usłudze nie ma. Endpoint `systemone` w DF jest na gałęzi w wewnętrznym GitLabie (wpis 85).
- **Nowe dane (wpisy 105–109):** 1500 dodatkowych pytań (Dolly, CodeChat, Arena 140k): odpowiedzi dużego i małego (3 próbki) wygenerowane; ucięte przy 2048 powtórzone z limitem 4096; **decyzja: ocenić tak, jak są** (limit 4096 to część protokołu). Pliki są tylko na komputerze służbowym (poza gitem).
- **Dokumenty pracy:** szkice 2 rozdziałów (`docs/praca/`, z [UZUPEŁNIĆ]); reszty tekstu nie ma. Prezentacja: plik Keynote autora, wersja zaktualizowana 27.10 o warstwę 3 i stan prac (15 slajdów, poza repozytorium, wpis 114; zob. `INDEX.md`).

## W toku / następne kroki (propozycje asystenta, nie decyzje; kolejność do ustalenia z autorem)
1. Scalić nowe odpowiedzi z `answers.jsonl` (komputer prywatny), ocenić sędzią Gemini (**płatne, tylko po zgodzie autora na kwotę**), policzyć nowe etykiety i podział nowych pytań.
2. Warstwa 3: zmierzyć czas Clefa (8 i 34 pytania) i kandydatów na docelowym GPU; ustalić przed testem listę porównywanych wariantów routera (sam kNN / sam model decyzyjny / kNN + L3 w strefie / kNN + L3 zawsze) i kryterium jakość–koszt (D19); zdecydować go/no-go.
3. Analizy na gotowych danych: szum etykiet i sufit AUROC, spadek jakości przy 20/40/50% do małego, zgodność 3 próbek małego jako sygnał po generacji (`PRZEMYSLENIA` pkt 5).
4. Benchmark systemowy na GPU (opóźnienie, przepustowość) i testy E, G w DF; poprawka dopasowania słów jako podciągu w DF (`server/router/heuristics.py`: „prove” trafia w „improve”).
5. Poprawki kodu ewaluacji: bootstrap po grupach, `pick()` w `certified_threshold.py` (wpis 97).
6. Zaktualizować `CELE_PRZED_TESTEM.md` (C1–C6, w tym moc C1), uzyskać zgodę promotora, **otworzyć test raz**.
7. Pisanie pracy (połowa pozostałego czasu).

## Decyzje czekające na autora
- Go/no-go warstwy 3 i wybór modelu; zestaw v1 (8) czy pula v2 (34) + GBM (D18); czy porównywać w pracy architektury, w tym sam model decyzyjny jako router (D19), co może zmienić strukturę pracy.
- Kwota na ocenę sędzią nowych/zmienionych odpowiedzi; zatwierdzenie C1–C6 (propozycja, nie zatwierdzone); zgoda promotora.
- Dwa niepotrzebne klony DF poza `kod/deepfellow-infra` (zob. niżej); usunąć dopiero na polecenie.

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
