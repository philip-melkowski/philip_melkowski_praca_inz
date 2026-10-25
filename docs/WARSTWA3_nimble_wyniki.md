# Warstwa 3: model decyzyjny `nimble`, wyniki testu go/no-go

Stan na 2026-10-24. Dokument podsumowuje pierwszy test warstwy 3 routera na prawdziwym modelu decyzyjnym. Szczegółowy przebieg i wszystkie decyzje są w `docs/DZIENNIK.md` (wpisy 82–93), a tło i warianty w `docs/WARSTWA3_propozycja.md`. Obowiązującym planem pozostaje `koncepcja.md`.

**W skrócie:** `nimble` niesie informację o trudności pytania, której nie ma kNN. Potwierdziło się to na zbiorze cal, na którym nie dobieraliśmy niczego z warstwy 3 (cal był wcześniej używany do oceny i wyboru konfiguracji kNN, a granice strefy wzięto z kwantyli train+cal; zob. sekcja 7, punkt 8). W strefie niepewności kNN zysk AUROC wynosi +0,066 [+0,007; +0,126], co według ustalonego wcześniej protokołu daje **formalnie GO, ale słabe**. W architekturze, w której warstwa 3 działa tylko w strefie, zysk na całym ruchu jest za mały, żeby go wykazać (+0,013, przedział obejmuje 0). Czasu na docelowym GPU jeszcze nie zmierzono.

---

## 1. Po co warstwa 3

Router ma dwie działające warstwy:

- **Warstwa 1, heurystyki:** sama ma AUROC ok. 0,555.
- **Warstwa 2, kNN na embeddingach `nomic-embed-text`** (k = 20): AUROC ok. 0,68–0,69. Krzywa uczenia jest płaska, więc więcej danych nie pomoże.

kNN ocenia pytanie po podobieństwie do pytań o znanej trudności. Nie wie jednak, czy mały model zna konkretny fakt albo czy poradzi sobie z konkretnym zadaniem. Warstwa 3 ma dać drugi, niezależny sygnał. Według decyzji z wpisu 67 byłaby wołana tylko w **strefie niepewności kNN** (wynik kNN między 0,20 a 0,45).

Etykieta jest ta sama co w całej pracy: Δ = jakość dużego modelu (`Qwen/Qwen3.8-27B-FP8`) − średnia jakość małego (`qwen3:8b`, 3 próbki). Pytanie jest **COMPLEX**, gdy Δ > 0,25.

## 2. Model `nimble` i endpoint `/v1/systemone`

- **Co to za model:** `nimble` to model decyzyjny (Bespoke, 9B, architektura `qwen3_5`, kwantyzacja mxfp8, licencja Apache 2.0). Nie generuje tekstu, tylko zwraca prawdopodobieństwa odpowiedzi na typowane pytania o podany tekst.
- **Endpoint:** `POST /v1/systemone`. Treść żądania to `model`, `state` (u nas pytanie użytkownika) i `questions`, czyli słownik pytań typu `noul` (tak/nie), `choice` albo `score`.
- **Odpowiedź w Ollamie 0.40.5:** `answers.<nazwa> = {"type": "noul", "noul": P(tak)}`. Pól `probabilities` i `confidence`, o których mówiła notatka startowa, w tej wersji nie ma.
- **Jak wołaliśmy:** przez **lokalny DeepFellow** autora (gałąź z GitLaba z endpointem `systemone`, `http://localhost:8086`), który przekazuje żądania do lokalnej Ollamy z modelem `nimble`.
- **Czego nie wykorzystaliśmy:**
  - zdalna maszyna `df-5070ti-02` w czasie testu nie odpowiadała,
  - `df-5070ti-04` i `df.test.simplito.com` nie mają tego endpointu (405).

### Sprzęt i jego ograniczenia

- **Komputer:** MacBook z Apple M5 i 16 GB RAM.
- **Pamięć:** przy domyślnych ustawieniach Ollama zajmowała na `nimble` 17 GB, bo rezerwowała pamięć podręczną na kilka równoległych żądań. System mocno swapował (do ok. 22 GB) i jeden przebieg przerwano z braku pamięci.
- **Obejście:**
  - `OLLAMA_NUM_PARALLEL=1` zmniejsza model do 9,6 GB, ale z czasem runner MLX znów rośnie do ok. 17 GB,
  - restart Ollamy przed każdym przebiegiem,
  - jedno żądanie naraz.
- **Czasy z tego Maca nic nie mówią o czasie w routerze na serwerowym GPU** (punkt 7).

## 3. Zestaw pytań do modelu (v1, zamrożony)

Plik `eval/layer3_questions/v1.json`, SHA-256 `cd0a28c3…068899d`. To propozycja asystenta, przyjęta przez autora jako pierwsza wersja i niezmieniana od pierwszego uruchomienia. Wszystkie pytania są typu `noul` i mają kryteria `true`/`false`.

| Nazwa | Pytanie (skrót, pełna treść w pliku) | Zamierzony sygnał |
|---|---|---|
| `rare_knowledge` | Czy dobra odpowiedź wymaga rzadkiej, specjalistycznej wiedzy, której mały model może nie znać? | fakty niszowe, TriviaQA |
| `multistep` | Czy trzeba rozumowania lub liczenia w kilku zależnych krokach? | matematyka, logika |
| `code` | Czy trzeba napisać, poprawić lub wyjaśnić niebanalny kod? | programowanie |
| `long_answer` | Czy dobra odpowiedź musi być długa (> ok. 300 słów lub dłuższy kod)? | duże zadania |
| `single_correct` | Czy jest jedna sprawdzalna poprawna odpowiedź? | „trafione albo nie” |
| `open_ended` | Czy to zadanie otwarte (twórcze, opinia, rozmowa)? | przeciwwaga dla `single_correct` |
| `constraints` | Czy jest wiele wyraźnych wymagań (format, długość, styl)? | wykonanie poleceń |
| `small_model_enough` | Czy mały model (ok. 8B) odpowie równie dobrze jak duży? | bezpośrednie pytanie o trudność |

Wszystkie 8 pytań idzie w jednym żądaniu razem z treścią pytania użytkownika.

## 4. Jak testowaliśmy

Test miał trzy etapy, uzgodnione z autorem (wpis 86):

1. **Sam `nimble` na train** (2151 pytań): czy i które pytania niosą sygnał. To eksploracja, więc wolno było oglądać wyniki.
2. **`nimble` a kNN na train**: czy mówi coś ponad kNN i ponad samo źródło pytania. Dalej eksploracja.
3. **Jednorazowy pomiar na cal** (859 pytań). Zestaw pytań i cały protokół zapisaliśmy w dzienniku przed uruchomieniem (wpis 91), a ocenę uruchomiliśmy raz.

**Zbiór test (1294 pytania) nie był używany.**

Dlaczego zamrażamy zestaw przed cal, a nie przed pierwszym uruchomieniem: jeśli wypróbuje się wiele zestawów i wybierze najlepszy na tych samych danych, jego wynik jest zawyżony przez przypadek. Dlatego eksperymentujemy na train, a uczciwie sprawdzamy raz na cal. Dobrze to widać na sprawdzeniu skryptu na losowych odpowiedziach: jedno z 8 losowych pytań wyszło tam „istotne”.

Metody:

- **Cechy:** logity 8 prawdopodobieństw z `nimble`.
- **Łączenie:** regresja logistyczna (C = 1,0) na [logit wyniku kNN, 8 cech].
- **Na train:** 5-krotna walidacja krzyżowa po grupach. Wynik kNN dla części uczącej liczyliśmy wewnętrzną walidacją krzyżową, żeby nie było przecieku.
- **Na cal:** wszystko, co się uczy (indeks kNN, regresja), dopasowane wyłącznie na train i zastosowane bez zmian.
- **Przedziały:** 95% z bootstrapu 1000 prób (ziarno 42).
- **Miary:** AUROC (jak dobrze wynik oddziela SIMPLE od COMPLEX; 0,5 to losowo) i APGR (pole pod krzywą odzyskanej jakości; losowo ok. 0,5).

## 5. Wyniki na train (eksploracja)

### 5.1. Każde pytanie osobno

| Pytanie | AUROC [95% CI] | Średnie P(tak): SIMPLE / COMPLEX | Siła sygnału* |
|---|---|---|---|
| `small_model_enough` | 0,317 [0,295; 0,339] | 0,506 / 0,351 | 0,683 (najsilniejszy) |
| `long_answer` | 0,666 [0,642; 0,689] | 0,208 / 0,321 | 0,666 |
| `open_ended` | 0,653 [0,631; 0,675] | 0,147 / 0,224 | 0,653 |
| `single_correct` | 0,397 [0,374; 0,421] | 0,350 / 0,226 | 0,603 |
| `constraints` | 0,579 [0,555; 0,604] | 0,232 / 0,280 | 0,579 |
| `rare_knowledge` | 0,573 [0,548; 0,597] | 0,139 / 0,154 | 0,573 |
| `multistep` | 0,543 [0,519; 0,567] | 0,226 / 0,214 | 0,543 |
| `code` | 0,499 [0,474; 0,524] | 0,166 / 0,169 | 0,50 (brak) |

\* AUROC poniżej 0,5 znaczy, że wyższe „tak” oznacza łatwiejsze pytanie. Siła sygnału to AUROC po odwróceniu kierunku.

Obserwacje:

- **Najlepiej działa pytanie wprost:** „czy mały model wystarczy?”.
- **Pytania o kod i rozumowanie wieloetapowe prawie nic nie dają.** To niestety te obszary, w których kNN myli się najbardziej (TriviaQA, HumanEval). Zgadza się to z ostrzeżeniem z literatury: modele typu Jev są słabsze tam, gdzie werdykt trzeba wyprowadzić, a nie odczytać z tekstu (`WARSTWA3_propozycja.md`, sekcja 4).

### 5.2. Wszystkie pytania razem i porównanie z kNN

| Metoda (train, CV) | AUROC [95% CI] | APGR [95% CI] |
|---|---|---|
| kNN k=20 | 0,686 [0,665; 0,708] | 0,606 [0,589; 0,623] |
| nimble, 8 pytań (LR) | 0,695 [0,674; 0,717] | 0,608 [0,591; 0,625] |
| samo źródło pytania (kontrola) | 0,617 [0,593; 0,641] | 0,577 [0,560; 0,593] |
| źródło + nimble | 0,706 [0,683; 0,728] | 0,615 [0,598; 0,632] |
| kNN + `small_model_enough` | 0,704 [0,683; 0,726] | 0,613 [0,596; 0,630] |
| kNN + nimble | 0,710 [0,689; 0,731] | 0,618 [0,601; 0,635] |
| kNN + źródło | 0,702 [0,679; 0,724] | 0,615 [0,597; 0,633] |
| kNN + źródło + nimble | 0,718 [0,696; 0,740] | 0,622 [0,605; 0,640] |

Zyski (różnice w parach bootstrapu):

- kNN + nimble − kNN: **AUROC +0,024 [+0,006; +0,041]**, APGR +0,012 [+0,001; +0,023]
- kNN + `small_model_enough` − kNN: AUROC +0,018 [+0,001; +0,033]
- źródło + nimble − samo źródło: AUROC +0,089 [+0,069; +0,111]
- kNN + źródło + nimble − (kNN + źródło): AUROC +0,017 [+0,002; +0,031]

„Źródło” to odsetek COMPLEX w zbiorze, z którego pochodzi pytanie. Router go nie zna, więc służy tylko jako kontrola. Sprawdzaliśmy, czy `nimble` nie robi nic więcej niż rozpoznawanie typu pytania (otwarte, oceniane przez sędziego, a takie z poprawną odpowiedzią). Robi więcej: dodaje +0,089 ponad samo źródło i +0,017 ponad kNN ze źródłem.

### 5.3. Ile `nimble` pokrywa się z kNN

Korelacja Spearmana z wynikiem kNN (poza próbką):

| Cecha | ρ |
|---|---|
| nimble, 8 pytań (LR) | +0,60 |
| `small_model_enough` | −0,57 |
| `open_ended` | +0,54 |
| `long_answer` | +0,44 |
| `single_correct` | −0,43 |
| `constraints` | +0,28 |
| `rare_knowledge` | +0,18 |
| `code` | −0,09 |
| `multistep` | −0,05 |

`nimble` w dużej części mówi to samo co kNN, ale nie całkiem. Najsilniejsze cechy pokrywają się z kNN najbardziej, a cechy słabo skorelowane z kNN same niosą mało sygnału.

### 5.4. Strefa niepewności kNN na train

Strefa niepewności kNN to wynik kNN w przedziale 0,20–0,45. Na train trafia do niej 1097 pytań (51%), z czego 35,2% to COMPLEX.

| Metoda | AUROC [95% CI] | APGR [95% CI] |
|---|---|---|
| kNN | 0,568 [0,534; 0,605] | 0,532 [0,507; 0,558] |
| nimble (8) | 0,647 [0,615; 0,677] | 0,584 [0,559; 0,612] |
| kNN + nimble | 0,649 [0,617; 0,680] | 0,584 [0,558; 0,610] |

Zysk kNN + nimble − kNN: **AUROC +0,081 [+0,042; +0,116]**, APGR +0,052 [+0,026; +0,079].

W strefie kNN prawie zgaduje, bo to z definicji pytania, co do których jest niepewny. `nimble` wnosi tam najwięcej. Pasuje to do architektury z wpisu 67.

## 6. Wynik na cal (jednorazowy pomiar, rozstrzygający)

Protokół zapisaliśmy przed uruchomieniem (wpis 91). Cal ma 859 pytań, z czego 34,3% to COMPLEX. W strefie jest 414 pytań (48,2%).

### 6.1. Miara główna G1: strefa niepewności

| Metoda | AUROC [95% CI] | APGR [95% CI] |
|---|---|---|
| kNN | 0,586 [0,525; 0,647] | 0,558 [0,512; 0,600] |
| nimble (8) | 0,649 [0,593; 0,705] | 0,602 [0,561; 0,647] |
| `small_model_enough` (odwr.) | 0,632 [0,576; 0,689] | 0,586 [0,544; 0,633] |
| kNN + `small_model_enough` | 0,640 [0,583; 0,696] | 0,592 [0,551; 0,640] |
| kNN + nimble | 0,653 [0,596; 0,707] | 0,603 [0,564; 0,649] |

- **Zysk AUROC kNN + nimble − kNN: +0,066 [+0,007; +0,126] → GO dla G1** (dolna granica > 0).
- Zysk APGR w strefie: +0,044 [+0,002; +0,090].

### 6.2. Cały cal (dodatkowo)

| Metoda | AUROC [95% CI] | APGR [95% CI] |
|---|---|---|
| kNN | 0,690 [0,653; 0,725] | 0,612 [0,581; 0,644] |
| nimble (8) | 0,705 [0,672; 0,738] | 0,623 [0,594; 0,652] |
| `small_model_enough` (odwr.) | 0,689 [0,654; 0,723] | 0,614 [0,586; 0,643] |
| kNN + `small_model_enough` | 0,714 [0,682; 0,748] | 0,628 [0,597; 0,657] |
| kNN + nimble (dla każdego pytania) | 0,723 [0,689; 0,755] | 0,630 [0,599; 0,660] |
| router ze strefą (nimble tylko w strefie) | 0,703 [0,667; 0,738] | 0,621 [0,590; 0,651] |

- kNN + nimble dla każdego pytania − kNN: **AUROC +0,033 [+0,009; +0,057]**, APGR +0,018 [+0,000; +0,035]
- router ze strefą − kNN: **AUROC +0,013 [−0,005; +0,028]**, APGR +0,009 [−0,004; +0,022]. Przedział obejmuje 0.

### 6.3. Bezpieczeństwo G3: poważne błędy

Poważny błąd to pytanie z Δ > 0,5 wysłane do małego modelu. Porównanie przy tym samym udziale dużego modelu co kNN z progiem 0,3 (58,6% pytań):

- kNN: 3,7% wszystkich pytań,
- router ze strefą: 3,4%,
- różnica −0,3 pkt [−1,3; +0,6]. Nie gorzej, ale też nieistotnie lepiej.

### 6.4. Zestawienie celów

| Cel | Wynik | Status |
|---|---|---|
| G1 informacja ponad kNN w strefie | +0,066 [+0,007; +0,126] | spełniony (na granicy) |
| G2 jakość przy tym samym koszcie | APGR w strefie +0,044 [+0,002; +0,090]; router ze strefą na całości +0,009 (nieistotnie) | częściowo |
| G3 poważne błędy nie gorsze | 3,4% wobec 3,7% | spełniony |
| G4 udział pytań w strefie | 48,2% | w granicach (≤ 50%) |
| G5 opóźnienie | p50 3,7 s, p90 4,3 s na Macu 16 GB | **niezmierzone na docelowym sprzęcie** |
| G6 kalibracja (ECE) | — | niezmierzone |
| G7 stabilność (kolejność, parafrazy) | — | niezmierzone |
| G8 wdrażalność | Apache 2.0; ok. 9,6 GB pamięci przy 1 żądaniu naraz | prawdopodobnie tak, do sprawdzenia obok modelu 27B |

Reguła z propozycji: go = G1 oraz G2 lub G3. **Formalnie GO.**

## 7. Interpretacja i zastrzeżenia

1. **Sygnał jest prawdziwy, ale mały.** Potwierdził się na cal, na którym nie dobieraliśmy zestawu pytań ani regresji warstwy 3, i jest zgodny z train (strefa: +0,081 na train, +0,066 na cal). Dolna granica na cal to +0,007, czyli tuż nad zerem. Przykładowy próg z propozycji („≥ +0,03”) spełnia średnia, ale nie dolna granica.
2. **Zysk w strefie słabo przekłada się na cały router.** Router ze strefą poprawia AUROC na całości o +0,013 i ten wynik mieści się w szumie. Wołanie `nimble` dla każdego pytania daje więcej (+0,033), ale kosztuje wywołanie dla 100% zapytań zamiast ok. 48%. Możliwa przyczyna: wynik łączony w strefie i wynik kNN poza nią mają różne skale, a AUROC liczony na całości zależy od ich wspólnego uszeregowania. Liczy się jednak decyzja przy konkretnym progu, a tę lepiej pokazuje G3. Ta przyczyna to hipoteza asystenta, niesprawdzona.
3. **Najlepsze pytanie to pytanie wprost.** `small_model_enough` samo daje prawie tyle co kNN (cal: 0,689 wobec 0,690). Pytania o kod i rozumowanie wieloetapowe nie działają, a to te obszary, gdzie router myli się najbardziej.
4. **`nimble` częściowo powtarza kNN** (ρ = 0,60), ale nie sprowadza się do rozpoznawania źródła ani typu pytania.
5. **Czas jest największą niewiadomą.** Na Macu z 16 GB jedno żądanie z 8 pytaniami trwało 2,5–9 s, zależnie od zapełnienia pamięci (p50: train 8,9 s ze swapem, cal 3,7 s). Rano bez obciążenia 2 pytania zajmowały 0,6–0,9 s. Karty podobnych modeli podają ok. 60–150 ms na serwerowym GPU. Obecny router dodaje ok. 13 ms przy celu < 50 ms, więc warstwa 3 potrzebowałaby osobnego budżetu czasu.
6. **Cal jest już wykorzystany dla zestawu v1.** Każda zmiana zestawu (np. v2 bez `code` i `multistep`) wymagałaby nowego, niezależnego sprawdzenia. Jedyne nietknięte dane to zamknięty zbiór test, otwierany raz na końcu całej pracy.
7. **Jeden model, jeden zestaw, jedna para modeli.** Wynik dotyczy `nimble` z zestawem v1 dla pary `qwen3:8b` / `Qwen3.8-27B-FP8`. Innych kandydatów (`pplx-decider`, `basal`, wariant A/B na Qwenie z logprobs) nie testowaliśmy.
8. **Cal nie jest całkiem „świeży”, a miara G1 sprzyja nowej cesze** (poprawka po przeglądzie, 2026-10-25).
   - **Wcześniejsze użycie cal.** Cal był wcześniej zbiorem ewaluacyjnym dla kNN (dziennik, wpisy 19–20, 23) i wchodził do walidacji krzyżowej train+cal przy wyborze konfiguracji kNN. Granice strefy 0,20–0,45 wzięto z kwantyli wyniku kNN na train+cal (wpis 67). Nie dobieraliśmy na nim zestawu pytań ani regresji warstwy 3, ale „nietknięty” to za mocne słowo.
   - **G1 a cały router.** Strefę wybiera się po wyniku kNN, więc w jej obrębie kNN ma z konstrukcji wąski zakres wyników, a jego AUROC jest bliski losowemu (0,586). Każda cecha niezależna od kNN łatwo go tam pobije. Dlatego G1 sprzyja warstwie 3. Rozstrzygająca dla architektury jest miara całego routera ze strefą (+0,013, nieistotna) oraz G3. Reguła „go” została zapisana przed pomiarem, ale sama jej konstrukcja była łaskawa.

## 8. Możliwe dalsze kroki (do decyzji autora)

1. **Go z zastrzeżeniami** (rekomendacja asystenta). Pomiar czasu `nimble` na serwerowym GPU w DF (G5), potem wpięcie warstwy 3 w `RouterService` w strefie niepewności: dwa progi strefy i budżet czasu jako opcje serwisu, a przy błędzie lub przekroczeniu czasu duży model.
2. **Wariant „nimble dla każdego pytania”.** Większy zysk (+0,033), ale wywołanie dla każdego zapytania. Ma sens tylko przy krótkim czasie na GPU.
3. **No-go.** Opisać w pracy jako wynik: model decyzyjny daje mały, ledwie istotny zysk ponad kNN, a w architekturze ze strefą nieistotny na całym ruchu.
4. **Niezależnie od decyzji:** zmierzyć G6 (kalibracja) i G7 (stabilność). Rozważyć krótszy zestaw (np. same `small_model_enough`, `long_answer` i `open_ended`), który byłby szybszy. Taki zestaw trzeba jednak sprawdzić na nowych danych.

## 9. Pliki i odtworzenie

| Plik | Co zawiera |
|---|---|
| `eval/layer3_questions/v1.json` | zamrożony zestaw 8 pytań |
| `eval/layer3_systemone.py` | zbieranie odpowiedzi przez `POST /v1/systemone` (parametry `--url`, `--model`, `--questions`, `--splits`, `--concurrency`; wznawianie) |
| `eval/layer3_systemone_eval.py` | krok 1: każde pytanie osobno i wszystkie razem, kNN jako odniesienie (train) |
| `eval/layer3_systemone_vs_knn.py` | krok 2: zysk ponad kNN i ponad źródło, korelacje, strefa (train) |
| `eval/layer3_systemone_cal.py` | krok 3: jednorazowy pomiar na cal według protokołu z wpisu 91 |
| `data/datasets/layer3_systemone_nimble_v1.jsonl` | odpowiedzi `nimble` na train (2151); poza gitem |
| `data/datasets/layer3_systemone_nimble_v1_cal.jsonl` | odpowiedzi `nimble` na cal (859); poza gitem |

Polecenia (lokalny DF na `localhost:8086` z `nimble`; przed długim przebiegiem `launchctl setenv OLLAMA_NUM_PARALLEL 1` i `brew services restart ollama`):

```
uv run --python 3.13 eval/layer3_systemone.py --splits train --concurrency 1
uv run --python 3.13 eval/layer3_systemone.py --splits cal --concurrency 1 --output data/datasets/layer3_systemone_nimble_v1_cal.jsonl
uv run --python 3.13 eval/layer3_systemone_eval.py data/datasets/layer3_systemone_nimble_v1.jsonl
uv run --python 3.13 eval/layer3_systemone_vs_knn.py data/datasets/layer3_systemone_nimble_v1.jsonl
uv run --python 3.13 eval/layer3_systemone_cal.py
```

Przebieg na train trwał łącznie ok. 3,5 h (z przerwami), a na cal ok. 55 min, na Macu M5 z 16 GB.
