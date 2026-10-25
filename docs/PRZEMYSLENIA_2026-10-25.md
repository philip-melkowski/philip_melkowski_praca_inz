# Przemyślenia o kierunku pracy (2026-10-25)

Notatka asystenta dla autora. Powstała na podstawie trzech raportów agentów badawczych (rodzina basal i fine-tuning; literatura o routingu z lat 2024–2026; krytyczna analiza całego repozytorium), sprawdzenia ich najważniejszych twierdzeń i wyników testu warstwy 3. Wszystko tu to **propozycje do decyzji autora**, nie zmiany planu. Oznaczenia: **[S]** = sprawdzone przeze mnie w plikach lub źródle, **[A]** = z raportu agenta, niesprawdzone, **[O]** = moja opinia.

---

## 1. Najważniejsze w pięciu punktach

1. **Rdzeń pracy stoi na solidnych nogach. Słabo idzie tekst i pomiary systemowe, nie badania.** Etykiety są zmierzone dla pary modeli, a metodologia jest staranna: CV po grupach, bootstrap, zamknięty test, protokół zapisany przed pomiarem. kNN z APGR ok. 0,61 to poziom routerów RouteLLM uczonych bez dodatkowych etykiet. Największe ryzyko to brak tekstu pracy i brak benchmarku na docelowym sprzęcie. [S/O]
2. **Warstwa 3 (model decyzyjny) daje mały, graniczny zysk.** Sama miara G1 jest skonstruowana tak, że sprzyja nowej cesze (punkt 3.2). Uczciwie trzeba ją opisać jako rozdział eksperymentalny, nie jako rdzeń routera. [S/O]
3. **Jest za to ciekawsza obserwacja, którą warto wyeksponować.** Jedno pytanie zero-shot do modelu decyzyjnego („czy mały model wystarczy?”) daje AUROC jak kNN uczony na 2151 etykietach: na cal 0,689 wobec 0,690. To historia „zimnego startu”: router dla nowej pary modeli bez zbierania etykiet. Pasuje też do pierwotnej tezy „bez fine-tuningu i bez danych preferencji”. **Krzywa uczenia na train (wpis 99):** kNN dochodzi do poziomu zero-shot (ok. 0,68) dopiero przy ok. 1000–1500 etykietach; przy 100 etykietach ma 0,58. [S/O]
4. **Sufit ok. 0,69 AUROC to nie wada naszego kNN, tylko granica routingu z samego tekstu pytania.** Literatura z lat 2025–2026 przebija ją tylko sygnałami z wnętrza modelu (aktywacje prefill, sondy) albo po wygenerowaniu odpowiedzi (kaskady). To należy powiedzieć wprost w pracy. [A, częściowo S]
5. **Zamrozić zakres.** Po basal nie dokładać nowych modeli decyzyjnych ani embedderów. Każdy kolejny wariant zużywa cal, a czas jest potrzebny na test końcowy, benchmark i pisanie. [O]

---

## 2. Co wiemy o basal (raport agenta, kluczowe punkty sprawdzone w pakiecie)

- **Rodzina.**
  - basal-2.0 (mini 1,5B / 4.5B / max 11B) to fine-tune polskiego **Bielika v3**, PL i EN, Apache-2.0.
  - Na angielskim panelu zadań **basal-2.0 wypada gorzej niż basal-1.5** (4.5B: 0,652 wobec 0,688). Testujemy więc najnowszy, ale nie najlepszy po angielsku. [A]
  - Dla zadań po angielsku agent wskazuje jako lepszych kandydatów `basal-omni-1.0-mini-MLX` (Gemma 4 E4B) albo `basal-1.5-4.5B`. [A]
- **Fine-tuning.**
  - Kodu treningowego w pakiecie nie ma. [A, drzewo repo]
  - Model to jednak zwykły LlamaForCausalLM: odczyt decyzji to softmax po logitach liter opcji, bez osobnej „głowy”. Przepis z raportu technicznego basal-1.0: LoRA r=32, lr 5e-5, 1 epoka, strata tylko na tokenie opcji. [A, oparte na `prompt.py` i raporcie]
  - **LoRA na naszych etykietach jest więc technicznie wykonalna**, np. `mlx_lm.lora` na mini albo 4.5B na tym Macu. Byłby to jednak kolejny klasyfikator nadzorowany. Moje przewidywanie: wyjdzie w okolicach kNN, bo etykiety są szumne, a train mały. [O]
- **`basal-calibrate`.**
  - Dopasowuje tylko **temperatury**, czyli przekształcenie zachowujące kolejność, więc **nie zmienia AUROC**. Daje za to skalibrowane prawdopodobieństwa i certyfikowane progi błędu (np. 5%). [A, zgodne z `docs/CALIBRATION.md`]
  - Dostarczony `CALIBRATION.mlx.json` ma temperaturę dla `noul` 2,71, czyli spłaszcza prawdopodobieństwa. Na AUROC nie wpływa. [A]
- **Funkcje silnika przydatne dla routera:**
  - typ `act` z macierzą kosztów i `max_error`: zwraca `deferred`, gdy niepewny, czyli gotowa „strefa niepewności”,
  - `score`: wartość oczekiwana na skali,
  - `--orders 2`: uśrednianie po kolejnościach opcji, przeciw błędowi pozycji,
  - `--mlx-packed`: ok. 1,5 raza szybciej na M5. [A]
- **Czas.** basal-2.0-mini MLX deklaruje ok. 31–49 ms na decyzję, 4.5B ok. 130–280 ms. Zmierzone u nas dla 4.5B na M5: ok. 1,4 s na żądanie z 8 pytaniami, czyli ok. 170 ms na pytanie. [A/S]

**Wniosek [O].** Basal jest najbardziej „otwartym” z modeli decyzyjnych, bo ma jawny przepis treningowy, kalibrację i działa na Macu. Dla pracy największą wartość ma jednak nie fine-tuning, tylko **mały model (mini) jako tani kandydat na warstwę 3**. Mieści się obok modelu 27B na GPU i ma czasy rzędu dziesiątek ms. Trzeba go jednak sprawdzić na danych innych niż cal (punkt 5).

---

## 3. Warstwa 3: co naprawdę wiemy

### 3.1. Fakty [S]

- nimble, zestaw v1, cal (859 pytań):
  - w strefie zysk AUROC +0,066 [+0,007; +0,126],
  - cały router ze strefą +0,013 [−0,005; +0,028],
  - nimble dla każdego pytania +0,033 [+0,009; +0,057],
  - poważne błędy 3,4% wobec 3,7%.
- Najlepsze pytanie to `small_model_enough`. Pytania `code` i `multistep` nie niosą sygnału.

### 3.2. Zastrzeżenie, które zgłosił agent analizy, a które przyjmuję [S/O]

- **G1 sprzyja nowej cesze.** Strefa jest wybierana po wyniku kNN, więc w jej obrębie kNN ma z konstrukcji wąski zakres wyników i AUROC bliski losowemu (0,586). Każda cecha niezależna od kNN łatwo go tam pobije. Reguła była zapisana przed pomiarem, ale była „łaskawa”. **Dla architektury rozstrzyga cały router ze strefą, a ten wynik jest nieistotny.**
- **Cal nie był całkiem świeży.** Był wcześniej zbiorem ewaluacyjnym dla kNN (wpisy 19–20, 23), a granice strefy wzięto z kwantyli train+cal. Poprawiłem to w `WARSTWA3_nimble_wyniki.md` (zastrzeżenie 8, wpis 96).

### 3.3. Co z tego wynika dla pracy [O]

- **Uczciwa teza o warstwie 3:** „model decyzyjny niesie sygnał częściowo niezależny od embeddingów (ρ = 0,60), ale w architekturze z bramką niepewności poprawa całego routera jest nieistotna statystycznie przy naszym rozmiarze danych”.
- **Ta sama obserwacja z drugiej strony jest pozytywna:** zero-shot model decyzyjny ≈ kNN uczony nadzorowanie. Proponuję zmienić rolę warstwy 3 w narracji z „poprawiacza kNN” na **alternatywę bez etykiet (zimny start) i składnik fuzji**.
- **Czy wpinać do `RouterService`:** tylko jeśli pomiar na docelowym GPU da p50 rzędu ≤ 100–200 ms. Wtedy jako opcja domyślnie wyłączona, a przy przekroczeniu czasu decyzja kNN, nie automatycznie duży model (inaczej rośnie koszt). Pomiar czasu `nimble` na GPU w DF zajmie jedno popołudnie i rozstrzyga sprawę.

---

## 4. Co mówi literatura (raport agenta; kluczowe liczby sprawdzone)

- **RouteLLM (ICLR 2025), MT-Bench, tabela 1 [S]:**
  - routery uczone tylko na danych Arena mają APGR 0,391 (BERT), 0,573 (causal LLM), 0,580 (matrix factorization), 0,610 (SW ranking); losowy router 0,500,
  - dopiero dodatkowe etykiety od sędziego GPT-4 dają 0,68–0,80,
  - na MMLU routery tylko z Areny są na poziomie losowym (0,44–0,48), a pomaga dopiero ok. 1500 złotych etykiet.
- **Wniosek dla nas [O].** Nasze APGR 0,61 jest na poziomie najlepszych routerów RouteLLM bez dodatkowych etykiet. Para RouteLLM (GPT-4 kontra Mixtral) ma jednak dużo większą przepaść jakości niż nasza (8B kontra 27B z jednej rodziny). Porównanie należy przedstawić jako orientacyjne, nie jako bezpośrednie.
- **LLMRouterBench (2026) [A, abstrakt]:** wiele routerów nie pokonuje „najlepszego pojedynczego modelu”, a wybór embeddera ma małe znaczenie. Wspiera nasz wynik o suficie embeddingów.
- **Sygnały z wnętrza modelu [A, abstrakty]:**
  - aktywacje prefill (NVIDIA 2026) i liniowe sondy na stanach ukrytych („LLMs Encode Their Failures”, ICLR 2026) przebijają routery semantyczne;
  - stany ukryte przed generacją niosą sygnał „wiem / nie wiem” (Ni i in., ACL 2025).

  To najmocniejsza droga ponad sufit, ale wymaga dostępu do stanów ukrytych małego modelu.
- **Kaskady [A]:**
  - JEV-as-a-Judge: progi z dolną granicą ufności, zamrożone przed testem; Jev traci 7–28 pkt na wiedzy, kodzie i matematyce.
  - „Jev vs LLMs as Rubric Judges”: AUROC pewności 0,57–0,70, czasem poniżej 0,5; zalecenie, by walidować każde kryterium osobno.

  Zgadza się to z naszym obrazem: małe i niestabilne zyski, brak sygnału w kodzie.
- **Wiedza faktograficzna [A]:** PopQA (Mallen i in. 2023): skuteczność modeli silnie zależy od popularności encji (odsłony Wikipedii). To tania cecha, celująca dokładnie w naszą słabość na TriviaQA.

---

## 5. Pomysły, uporządkowane według wartości dla pracy i kosztu [O]

| # | Pomysł | Wartość | Koszt | Uwagi |
|---|---|---|---|---|
| 1 | **Analiza szumu etykiet i sufitu:** AUROC tylko na pytaniach z wyraźnym Δ (np. \|Δ\| > 0,4), korelacja wyniku routera z ciągłym Δ, górna granica z niezgodności 3 próbek małego modelu | wysoka (odpowiada na „dlaczego tylko 0,69”) | < 1 dzień | potrzebne pliki z ocenami poszczególnych próbek (prawdopodobnie na komputerze prywatnym) |
| 2 | **Spadek jakości jak w Hybrid LLM:** utrata jakości wobec „zawsze duży” przy 20%, 40% i 50% ruchu do małego | wysoka (praktyczny argument) | < 1 dzień | z istniejących danych |
| 3 | **Górna granica sygnału po generacji:** zgodność 3 odpowiedzi małego modelu (self-consistency) jako predyktor COMPLEX | wysoka (odpowiada na pytanie recenzenta „czemu nie kaskada”) | ok. 1 dzień | z istniejących odpowiedzi; pokazuje, ile daje patrzenie na odpowiedź |
| 4 | **Benchmark systemowy na docelowym GPU:** p50/p90 opóźnienia, przepustowość, pamięć i zużycie GPU, „zawsze duży” wobec routera | **konieczna** (obiecana w planie) | 1–2 dni | bez tego nie da się mówić o oszczędnościach |
| 5 | **Czas `nimble` (i ewentualnie basal-mini) na GPU w DF** | rozstrzyga o warstwie 3 | pół dnia | |
| 6 | **Popularność encji** (NER, odsłony Wikipedii) jako cecha dla pytań z wiedzy | średnio-wysoka | 1–2 dni | celuje w TriviaQA; ryzyko: nowy wariant, a cal już wykorzystany |
| 7 | **Sonda liniowa na stanach ukrytych `qwen3:8b`** (plan B z koncepcji, wariant E) | potencjalnie najwyższa | 3–5 dni | Ollama nie zwraca stanów ukrytych; potrzebne `mlx-lm` albo HF; ryzyko rozrostu zakresu |
| 8 | LoRA na basal-mini jako router uczony | niska do średniej | 1–2 dni | prawdopodobnie ≈ kNN; ciekawostka do „dalszych prac” |
| 9 | `basal-calibrate` / typ `act` z macierzą kosztów | niska teraz | pół dnia | nie zmienia AUROC; przydatne dopiero przy wdrożeniu |

**Rekomendacja [O]:** zrobić 1–5, rozważyć 6, a 7–9 opisać w „dalszych pracach”. Punkty 1–3 to analizy na gotowych danych, bez nowego wywoływania modeli i bez zużywania cal ani testu.

---

## 6. Problem metodyczny: zużywanie danych [O]

Cal był już zbiorem ewaluacyjnym dla kNN, potem dla nimble, a teraz dla basal. Każde kolejne „sprawdzenie na cal” jest mniej warte. Propozycja:

- Od teraz **żadnych nowych wariantów oceniać na cal**. Nowe pomysły tylko w walidacji krzyżowej na train, a cal i test zostają do raportu.
- **Wszystkie oceniane warianty raportować w pracy razem** (tabela „sprawdziliśmy N wariantów”), żeby czytelnik widział ryzyko wielokrotnych porównań.
- **Test otworzyć raz**, dla ustalonej wersji routera (warstwa 1 + kNN, opcjonalnie warstwa 3 jako drugorzędna), po zapisaniu C1–C6 i zgodzie promotora.

---

## 7. Plan na resztę pracy [O]

1. **Teraz:** zamrozić zakres. basal dokończyć, raportować oba modele decyzyjne, nie wybierać lepszego na cal.
2. **Analizy na gotowych danych** (punkty 1–3 z tabeli): 2–3 dni.
3. **Na sprzęcie DF:** czas warstwy 3 i benchmark systemowy, dokończenie testów E i G. Do tego poprawka w `engine.py` (dopasowanie słów kluczowych jako podciąg: „prove” trafia w „improve”) [S] i commit.
4. **Protokół testu końcowego:** zaktualizować `CELE_PRZED_TESTEM.md` (aktualna wersja routera), uzyskać zgodę promotora, otworzyć test raz (z OOD).
5. **Pisanie, co najmniej połowa pozostałego czasu.** Szkielet:
   1. wstęp,
   2. przegląd literatury: RouteLLM, FrugalGPT, Hybrid LLM, kaskady, modele decyzyjne,
   3. dane i etykiety, w tym **obie** wartości zgodności człowiek–sędzia: 0,361 przed poprawkami i 0,592 po [S],
   4. projekt routera,
   5. implementacja w DeepFellow,
   6. ewaluacja,
   7. warstwa 3 jako eksperyment,
   8. ograniczenia,
   9. wnioski,

   plus deklaracja użycia narzędzi AI zgodnie z regulaminem uczelni.

**Definicja „gotowe” [O, za agentem analizy]:**
- test otwarty raz, a C1–C6 zaraportowane (spełnione czy nie),
- `RouterService` zacommitowany, testy przechodzą,
- benchmark z docelowego sprzętu,
- warstwa 3 opisana z decyzją i uzasadnieniem,
- tekst bez „[UZUPEŁNIĆ]”,
- jedno spójne źródło liczb.

---

## 8. Pytania, których należy się spodziewać od recenzenta [A/O]

1. Dlaczego próg Δ > 0,25 i na ile można ufać sędziemu LLM? Jaka jest zgodność z człowiekiem **przed** poprawkami?
2. Ile realnie oszczędza router: GPU-godziny, opóźnienie, przepustowość? Sam „% wywołań” nie wystarczy.
3. kNN na etykietach to uczenie nadzorowane. Jak to się ma do pierwotnej obietnicy „bez uczenia”? (Odpowiedź: model decyzyjny zero-shot ≈ kNN, punkt 3.3.)
4. Dlaczego decyzja przed odpowiedzią, a nie kaskada, skoro wiedzy i kodu nie widać w treści pytania? (Odpowiedź: pomysł 3 z tabeli i opóźnienie kaskady.)
5. Czy wynik przenosi się na inną parę modeli i poza dziedzinę?
6. Czy warstwa 3 się opłaca, skoro wymaga dodatkowego modelu na GPU?
7. Co się stało z Map-Reduce i kategoriami z pierwotnej koncepcji? (Odpowiedź: świadomie wypadły, trzeba to uzasadnić w tekście.)
8. Jaki jest wkład autora, a jaki asystenta AI?

---

## 9. Niespójności w dokumentach do uporządkowania [A, wybrane sprawdzone]

- `CLAUDE.md` na `main` to stara wersja (Qwen 1.5B / Llama 70B, YAML, Map-Reduce). Na `stage/2-classifier` jest aktualna. Po scaleniu gałęzi problem zniknie.
- Warstwa 3 opisana jako „mały model zero-shot z logprobs” (`CLAUDE.md`, `CELE_PRZED_TESTEM.md`, `POSTEPY`, `praca/02`), a teraz to model decyzyjny przez `systemone`.
- AUROC warstwy 1: 0,577 (wersja z regresją logistyczną) w `POSTEPY`, `praca/02` i prezentacji, a 0,555 (wersja punktowa, ta w usłudze) w nowych dokumentach. Trzeba wybrać i opisać, która jest która.
- `POSTEPY`: zgodność człowiek–sędzia 0,592 bez wzmianki o 0,361 przed poprawkami [S].
- „Test nieużyty” a wydrukowany odsetek COMPLEX w teście (30,6%) [S; dziennik to już przyznaje].
- `INDEX.md` nie zna dokumentów o warstwie 3 i podaje stare zakresy wpisów dziennika.
- `CLAUDE.md` wymienia NQ, którego w zbiorze nie ma [A].
- Dziennik, wpis 83: 2157 / 862 to wszystkie pytania w train / cal; z etykietami jest ich 2151 / 859. Warto to dopisać.

---

## 10. Druga runda: pogłębione badania (pięciu agentów)

### 10.1. Router bez etykiet: to jest najmocniejsza „własna” teza pracy [A/O]

- **Najbliższa analogia w literaturze:** „Zero-Shot Confidence Estimation for Small LLMs” (2026, arXiv 2605.02241). Router lokalny→chmura z modelami 7–8B [A]:
  - sygnał zero-shot (średni logprob odpowiedzi) daje AUROC 0,650–0,714, a routery nadzorowane w stylu RouteLLM 0,644–0,676;
  - poza dziedziną zero-shot wypada wyraźnie lepiej (0,72–0,83 wobec 0,51–0,56);
  - router nadzorowany uczony na 1000 etykiet nie przebił sygnału zero-shot.

  Nasze 0,689 ≈ 0,690 dokładnie pasuje do tego obrazu.
- **Nikt (w znalezionych źródłach) nie użył modeli decyzyjnych typu Jev/nimble do routingu mały/duży** [A]. Są tylko blogi o routingu intencji. To realna luka, którą praca może wypełnić.
- **„Just Ask Jev” (arXiv 2609.29429)** [A, czytane w części]:
  - ranking się przenosi, progi nie (średnie p nie trafia w lokalny odsetek klasy);
  - próg dopasowany na **10 etykietach** wyraźnie poprawia F1;
  - wybranie „najlepszego pytania” na danych ewaluacyjnych zawyża AUROC o ok. 0,008, czyli więcej niż typowy zysk z lepszego sformułowania;
  - typ `score` (3 poziomy, wartość oczekiwana) wygrywa z `noul` na 19 z 31 zbiorów.
- **Propozycja eksperymentu: krzywa uczenia.** Liczba etykiet k ∈ {0, 10, 25, 50, 100, 200, 500, 1000, 2150}.
  - Porównać kNN uczony na k etykietach z modelem decyzyjnym + progiem z k etykiet.
  - Próg bez etykiet: kwantyl budżetu, czyli „X% ruchu do dużego”.
  - Oczekiwany obraz: model decyzyjny jest płaski od k = 0, a kNN dogania go dopiero przy dużym k. Punkt przecięcia to liczba do pracy.
  - Wszystko na train, bez cal i testu.

### 10.2. Kaskada a routing przed odpowiedzią: odpowiedź dla recenzenta [A/O]

- **Sygnały po generacji są silniejsze dla wiedzy faktograficznej.** Entropia pierwszego tokenu odpowiedzi daje AUROC ok. 0,82, zgodność próbek ok. 0,79 (arXiv 2605.05166, modele 7–8B) [A]. Recenzent będzie miał rację co do natury błędów.
- **Ale kaskady wygrywają w literaturze przy stosunku kosztów modeli 10–200×** (FrugalGPT, AutoMix, MoT) [A]. U nas 8B wobec 27B to ok. 3–4×:
  - koszt kaskady: c_mały + e·c_duży (e = odsetek eskalacji),
  - koszt routingu: (1−r)·c_mały + r·c_duży (r = odsetek do dużego),
  - przy R = c_duży / c_mały ≈ 3,4 zmarnowana generacja małego to ok. 30% kosztu dużego. Kaskada wygrywa tylko wtedy, gdy lepszy sygnał po odpowiedzi obniża odsetek eskalacji o więcej niż 1/R.
  - Do tego kaskada psuje streaming (odpowiedź małego trzeba buforować przed decyzją).
- **„Calibration, Cascading, Cleaning” (arXiv 2601.07965), para Llama 8B→70B:** APGR 0,70 (MMLU), 0,69 (MBPP), 0,76 (GSM8K) z prawdopodobieństwa pierwszego tokenu małego modelu, wobec 0,55 dla RouteLLM-MF [A]. Wyniki bezpośrednio porównywalne z naszym APGR.
- **Analiza na istniejących danych, bez nowych generacji** (propozycja agenta, rozsądna):
  - zgodność 3 próbek małego modelu metodą leave-one-out (exact-match albo podobieństwo embeddingów) jako sygnał po generacji,
  - AUROC ogółem i dla każdej kategorii, połączenie z kNN,
  - krzywa jakość–koszt–opóźnienie dla 4 polityk: routing, kaskada, hybryda (kaskada tylko w strefie niepewności), dwie wyrocznie.

  Tezę „routing przed odpowiedzią + kaskada tylko w strefie” wspiera Dekoninck i in. (cascade routing, ICML 2025): wybór paradygmatu zależy od jakości estymatorów przed i po odpowiedzi.

### 10.3. Sondy na stanach ukrytych `qwen3:8b`: wykonalne w 2–3 dni [A/O]

- **Literatura** (prefill activations, „LLMs Encode Their Failures”, Ni i in., SEP):
  - liniowa sonda na ostatnim tokenie promptu, warstwy środkowe i górne, 0,5–10 tys. etykiet,
  - zysk nad mocnym routerem tekstowym +0,05–0,07 AUC,
  - najsilniejsza dla wiedzy faktograficznej i matematyki, mieszana dla kodu.
- **Wykonalność na Macu:** agent sprawdził, że `mlx-lm` zwraca stany wszystkich warstw (test na Qwen3-0.6B, 0,13 s na prompt). Dla Qwen3-8B 4-bit (ok. 4,7 GB) to ok. 1–1,5 h ekstrakcji na 4300 pytań. vLLM ma tryb `extract_hidden_states` dla dokładnego modelu bf16.
- **Pułapka:** sonda na małym modelu przewiduje głównie „mały się wyłoży”. Pytania, na których obaj zawodzą (etykieta SIMPLE), dostaną fałszywy sygnał COMPLEX. Rozwiązanie: cel wielowyjściowy (q_mały i q_duży) albo bezpośrednio Δ.
- **Wartość wdrożeniowa:** gdy pytanie idzie do małego, prefill sondy to prefill generacji (KV cache), więc routing jest prawie darmowy.
- **Moja ocena [O]:** to najbardziej obiecujący kierunek ponad sufit 0,69, ale też największe ryzyko rozrostu zakresu. Rozważyć jako jeden porządnie zrobiony eksperyment albo jako „dalsze prace”.

### 10.4. Szum etykiet i protokół testu: konkretne poprawki [A, częściowo S]

- **Sufit AUROC z szumu etykiet** (wyprowadzenie agenta, model szumu zależnego od klasy):
  - AUROC_obs − ½ = (1−α−β)·(AUROC_prawdziwe − ½), gdzie α i β to odsetki etykiet błędnie zaliczonych do każdej z klas,
  - przy zgodności sędziego test–retest 90% sufit wynosi ok. **0,94**; przy zgodności Flash vs Pro 79% ok. **0,87**,
  - szum losowania odpowiedzi obniża to dalej.

  Te liczby uwzględniają tylko szum sędziego. Szum losowania odpowiedzi (duży model ma jedną próbkę, mały trzy) może obniżyć sufit znacznie bardziej. Dopiero pełna procedura agenta (rozbicie wariancji Δ, najlepiej z 2 dodatkowymi próbkami dużego dla ok. 200 pytań) powie, ile z różnicy między 0,69 a 1,0 to szum etykiet, a ile brak informacji w samym pytaniu. [O: wzór do sprawdzenia przed cytowaniem]
- **Wcześniejsza rzetelność połówkowa 0,905 jest zawyżona:** jedna próbka dużego modelu i ocena sędziego są wspólne dla obu połówek [A].
- **Błędy w kodzie** potwierdzone i sprawdzone (wpis 97): bootstrap po pytaniach zamiast po grupach (na cal bez znaczenia) oraz `pick()` w progach certyfikowanych.
- **C1 w `CELE_PRZED_TESTEM.md` ma prawdopodobnie za małą moc** [A, szacunek]:
  - w części testowej z dziedziny jest ok. 766 pytań, więc połowa szerokości przedziału wynosi ok. ±0,03 przy oczekiwanym efekcie +0,023,
  - moc ok. 40%, czyli „niespełnione” jest bardziej prawdopodobne niż nie, nawet przy prawdziwym efekcie.
  - Propozycja: miara główna = parowana różnica APGR router − „sama długość” (w CV +0,082, duża moc), a C1 jako drugorzędna z policzoną mocą.
- **Progi certyfikowane są koncepcyjnie poprawne.** Praca ACL SRW 2026 (Uddin i Bauer) robi niemal to samo, czyli regresję logistyczną na embeddingach z górną granicą Clopper–Pearson [A, czytane z PDF]. Trzeba tylko:
  - poprawić `pick()` na Learn-then-Test,
  - opisać, że gwarancja jest marginalna, zakłada wymienialność i dotyczy błędów według sędziego.

### 10.5. Routery produkcyjne i benchmark systemowy [A]

- **Narzut naszego routera (ok. 13 ms) jest konkurencyjny:** Not Diamond 10–100 ms, Arch-Router ok. 51 ms, vLLM Semantic Router 50–127 ms (inna praca).
- **Żaden dostawca nie publikuje benchmarku systemowego on-prem.** Raportują koszt w $ i jakość. To nisza dla pracy.
- **Od LiteLLM warto wziąć losową kontrolę o tym samym udziale małego modelu.** Ich router regułowy nie różnił się istotnie od losowego.
- **Kluczowa subtelność benchmarku:** gdy oba modele stale siedzą w VRAM, router nie daje „bezczynnego GPU”, tylko **wyższą przepustowość przy zadanym SLO (goodput)** i mniejszą kolejkę na dużym modelu.
- **Plan benchmarku:**
  - scenariusze: zawsze duży / router z wymuszonym dużym (sam narzut) / router / wyrocznia / losowy przy tym samym udziale / zawsze mały,
  - ruch: przemiatanie tempa Poissona do nasycenia, 2 min rozgrzewki + ≥ 10 min, 3 powtórzenia,
  - narzędzia: `vllm bench serve` oraz własny klient zapisujący nagłówki `X-Router-*`, metryki DCGM,
  - główny wykres: goodput przy SLO w funkcji tempa.
- **Luki w `RouterService`** (do weryfikacji przed poprawkami):
  - brak limitu czasu na embedding (zawieszenie embeddera blokuje żądanie),
  - dopasowanie podciągu także w `heuristics.py:67`,
  - brak metryk Prometheus,
  - brak obsługi błędu w trakcie streamu,
  - klasyfikowana tylko ostatnia wiadomość rozmowy, brak przypięcia modelu do rozmowy.

---

## 11. Źródła

- [RouteLLM (Ong i in., ICLR 2025)](https://arxiv.org/pdf/2406.18665), tabele 1–2 sprawdzone
- [Hybrid LLM (Ding i in., ICLR 2024)](https://arxiv.org/html/2404.14618v1)
- [LLMRouterBench](https://arxiv.org/html/2601.07206)
- [LLM Router: Prefill Activations (2026)](https://arxiv.org/abs/2603.20895)
- [LLMs Encode Their Failures (ICLR 2026)](https://arxiv.org/html/2602.09924)
- [Ni i in., ACL 2025](https://arxiv.org/abs/2502.11677v1)
- [Cascade routing (Dekoninck i in., ICML 2025)](https://arxiv.org/html/2410.10347v3)
- [JEV-as-a-Judge](https://arxiv.org/pdf/2609.26550)
- [Jev vs LLMs as Rubric Judges](https://arxiv.org/html/2609.29769v1)
- [PopQA (Mallen i in., 2023)](https://arxiv.org/pdf/2212.10511)
- [basal (silnik)](https://github.com/rkinas/basal), [CALIBRATION.md](https://github.com/rkinas/basal/blob/main/docs/CALIBRATION.md), [basal-2.0-4.5B](https://huggingface.co/Remek/basal-2.0-4.5B)
- [JEV-9B](https://huggingface.co/autotrust/JEV-9B), [JEV-27B](https://huggingface.co/autotrust/JEV-27B)

Linki oznaczone [A] agent czytał w części tylko w abstrakcie; szczegóły do sprawdzenia przed cytowaniem w pracy.
