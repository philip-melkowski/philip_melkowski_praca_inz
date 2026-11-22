# STATUS: od tego pliku zaczyna każda sesja

Stan na: **2026-11-22**. Ostatni wpis dziennika: **124**. Plik jest importowany z `CLAUDE.md`, więc musi być krótki (≤ 100 linii; sprawdza to `tools/check_docs.py`). Szczegóły są w dokumentach, do których odsyłam; **liczb nie kopiuj z innych miejsc bez sprawdzenia, tu jest ich tylko tyle, ile trzeba**.

**Obowiązek na koniec sesji:** zaktualizuj ten plik (data, „w toku”, „następne kroki”, numer ostatniego wpisu), dopisz wpis do `DZIENNIK.md`, uruchom `uv run --python 3.13 tools/check_docs.py`. Commit i push tylko na prośbę autora.

## Projekt w czterech zdaniach
Praca inżynierska: `RouterService` w DeepFellow Infra (DF) wybiera dla każdego zapytania mały model (`qwen3:8b`) albo duży (`Qwen/Qwen3.8-27B-FP8`). Etykieta jest zmierzona: Δ = jakość dużego − średnia jakość małego (3 próbki), COMPLEX gdy Δ > 0,25. Kaskada: warstwa 1 (heurystyki punktowe) → warstwa 2 (kNN na embeddingach `nomic-embed-text`) → opcjonalna warstwa 3 (model decyzyjny w strefie niepewności) → awaria zawsze do dużego. Plan: `KONCEPCJA.md`; co z niego już nie obowiązuje: `DECYZJE.md`.

## Gdzie jesteśmy (fakty)
- **Dane:** 4313 pytań (train 2157 / cal 862 / test 1294), 4304 z etykietą (train 2151 / cal 859); 35,4% COMPLEX. **Zbiór test jest zamknięty** i otwiera się raz. **Cal jest „zużyty”**: użyty do oceny kNN, porównania dwóch modeli warstwy 3 i (za zgodą autora, 27.10) jednego potwierdzenia puli v2 z Clefem; kolejne użycie tylko za zgodą autora, nowe warianty w walidacji krzyżowej po grupach na train (`DECYZJE.md` D15).
- **Warstwy 1–2 (offline, train+cal, 3010 pytań, CV po grupach):** kNN k=20 AUROC 0,682, APGR 0,605; sama warstwa 1 AUROC ok. 0,555. Sufit embeddingów ok. 0,68–0,71 (wpis 30), krzywa uczenia płaska.
- **Warstwa 3 (model decyzyjny przez `/v1/systemone`, zestaw 8 pytań v1 zamrożony):** `docs/WARSTWA3_nimble_wyniki.md`, wpisy 86–104. Na cal `nimble` i `basal-2.0-4.5B` przeszły G1 (zysk AUROC w strefie 0,20–0,45: +0,066 i +0,084), ale **cały router ze strefą poprawia się mało** (+0,013 n.s. i +0,019). Na train podobnie `strands-decider:2b`, `d1:3b`, `tev1:4b`; samoocena `qwen3:8b` słabsza, `laya` bez sygnału, `kev` przerwany (pamięć). Zero-shot jedno pytanie ≈ kNN uczony na ok. 1000–1500 etykiet (wpis 99). Opinia asystenta: opcjonalne rozszerzenie, nie rdzeń (`PRZEMYSLENIA_2026-10-25.md`). **Decyzja go/no-go należy do autora.**
- **Warstwa 3, 27.10 (`WARSTWA3_PULA_PYTAN_2026-10-27.md`, wpisy 111–112):** Clef 27B q4 (df.test) najlepszy model (v1, strefa +0,099). Pula 34 pytań (`pool_v2.json`) + GBM: strefa AUROC 0,708 na train, **na cal 0,699 vs v1 0,642 (+0,057, istotne)**; APGR routera nadal mało (+0,014 n.s. na cal). **Sam Clef bez kNN (pula + GBM) 0,744** ≈ kNN + Clef 0,750, a sam kNN 0,687: kNN dokłada niewiele. Nasycenie ok. 0,75; czas rośnie z liczbą pytań (8 → 0,4 s, 34 → 1,5 s przez internet). Odrzucone: łączenie modeli, duży Qwen jako oceniający, cel ciągły, pula v3, krótszy zestaw. **d1:3b z pulą + GBM ≈ Clef** (0,747 / strefa 0,696), więc tani model jest realną alternatywą; `strands-decider:2b` z pulą słabszy (0,726 / strefa 0,675).
- **Integracja DF:** `RouterService` jest w klonie DF (`kod/deepfellow-infra`, gałąź `feat/router-service`, fork `philip-melkowski/deepfellow-infra`; upstream `simplito` nigdy). 27.10 gałąź przeniesiona (rebase) na aktualny `main` z GitLaba, który ma już `/v1/systemone` (wpis 115). Ma warstwy 1–2, awarię → duży; test z prawdziwymi Qwenami OK (wpis 70, narzut ok. 13 ms). **Warstwa 3 dodana 27.10** (opcjonalna, `decider_path`; zestaw v1 + regresja logistyczna, tylko w strefie 0,20–0,45, błąd lub limit 5 s → duży); działa na żywo (pokaz na seminarium 28.10, wpis 116). **Testy E (awaria embeddingów) i G (restart DF) zaliczone 22.11** (wpis 117). Słowa kluczowe dopasowywane jako całe słowa (poprawka „prove”/„improve”, commit d654a30, wypchnięty do forka). Clef na df.test nazywa się teraz `clef:27b` (inna wersja niż q4_K_M; plik `router_l3_clef27b_v1.json`). Gałąź po rebase wypchnięta do forka (`5a633c7`); klon na komputerze prywatnym trzeba zrównać z forkiem.
- **Nowe dane (wpisy 105–109):** 1500 dodatkowych pytań (Dolly, CodeChat, Arena 140k): odpowiedzi dużego i małego (3 próbki) wygenerowane; ucięte przy 2048 powtórzone z limitem 4096; **decyzja: ocenić tak, jak są** (limit 4096 to część protokołu). **22.11 ocenione sędzią (1498/1500, ok. 4,5 USD), etykiety `labels_extra.jsonl` (COMPLEX 49,9%), podział-propozycja `extra_train` 1051 / `extra_val` 449** (wpis 118). Pliki tylko na komputerze służbowym (poza gitem).
- **Dokumenty pracy:** szkice 5 części (`docs/praca/`: wstęp i literatura, dane, router, implementacja w DF, warstwa 3; z [UZUPEŁNIĆ]/[SPRAWDZIĆ]); brak ewaluacji na teście, ograniczeń i wniosków. Prezentacja: plik Keynote autora, wersja zaktualizowana 27.10 o warstwę 3 i stan prac (15 slajdów, poza repozytorium, wpis 114; zob. `INDEX.md`).

## W toku / następne kroki (propozycje asystenta, nie decyzje; kolejność do ustalenia z autorem)
1. Nowe pytania ocenione i z etykietami (wpis 118). **Etykiety v3 gotowe (wpis 124):** po ponownej ocenie 343 pytań z odpowiedziami przy limicie 4096 zmieniło się 96 klas z 4304 (train 60, cal 14, test 22); same liczby w `data/labels/` (`labels_v3.jsonl`, `sample_scores_v3.jsonl`). Zostaje: decyzja o roli `extra_val` i o dołożeniu nowych pytań do indeksu; indeks i `labels_v3` do przeliczenia na komputerze, na którym działa router. Bieżąca notatka: `PRACA_SAMODZIELNA_2026-11-22.md`.
2. Warstwa 3: czas d1 na GPU zmierzony (8 pytań p50 0,11 s, 34 pytania 0,36 s; wpis 118), Clef na GPU niesprawdzony; d1 nie jest w katalogu modeli decyzyjnych DF; ustalić przed testem listę porównywanych wariantów routera (sam kNN / sam model decyzyjny / kNN + L3 w strefie / kNN + L3 zawsze) i kryterium jakość–koszt (D19); zdecydować go/no-go.
3. Analizy: szum etykiet i spadek jakości zrobione na train (wpis 117); zostaje zgodność 3 próbek małego (oceny próbek na komputerze prywatnym).
4. Benchmark systemowy na GPU (opóźnienie, przepustowość): potrzebny dostęp od autora (tunel lub mesh).
5. Poprawki ewaluacji zrobione (wpis 117); **poprawny `pick()` zmienia tabelę ryzyka ze slajdu 9**, wybór metody (LTT czy Bonferroni) do decyzji autora.
6. Zaktualizować `CELE_PRZED_TESTEM.md` (C1–C6, w tym moc C1), uzyskać zgodę promotora, **otworzyć test raz**.
7. Pisanie pracy: redakcja szkiców przez autora, sprawdzenie źródeł [SPRAWDZIĆ], ewaluacja po otwarciu testu, ograniczenia, wnioski.

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
