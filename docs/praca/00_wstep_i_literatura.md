# Szkic: wstęp i przegląd literatury (roboczy, do redakcji przez autora)

Status: szkic asystenta z 2026-11-22. Źródła wyłącznie z repozytorium (`../PRZEMYSLENIA_2026-10-25.md` pkt 4 i 11, `../WARSTWA3_propozycja.md`, `../DZIENNIK.md` wpisy 4, 79). Pozycje oznaczone **[SPRAWDZIĆ]** były czytane tylko w abstrakcie i trzeba je przeczytać przed cytowaniem. Miejsca **[UZUPEŁNIĆ]** wymagają autora.

## 1. Wstęp

### 1.1. Problem
Duże modele językowe odpowiadają lepiej niż małe, ale wymagają więcej pamięci GPU, energii i czasu. W samodzielnie hostowanej infrastrukturze administrator ma zwykle dwie skrajne opcje: kierować cały ruch do dużego modelu (wysoki koszt) albo do małego (niższa jakość tam, gdzie była potrzebna). Wiele zapytań, np. proste pytania o fakty czy krótkie przekształcenia tekstu, mały model obsłuży równie dobrze. Celem routingu jest wybór modelu osobno dla każdego zapytania, **zanim** którykolwiek model odpowie, tak by jak najwięcej ruchu obsłużył mały model przy niewielkiej utracie jakości.

### 1.2. Cel i zakres pracy
Praca projektuje, wdraża i ocenia router zapytań dla pary modeli z jednej rodziny (`qwen3:8b` i `Qwen3.8-27B`) w DeepFellow Infra. Zakres:
- pomiar trudności zapytania dla konkretnej pary modeli (zamiast cudzych etykiet z głosowań),
- kaskada trzech warstw: heurystyki, kNN na embeddingach, opcjonalny model decyzyjny w strefie niepewności,
- usługa `RouterService` w DF z bezpieczną awarią do dużego modelu,
- ocena offline (AUROC, APGR, spadek jakości, progi z gwarancją) i jednorazowa ocena na zamkniętym zbiorze testowym.

### 1.3. Teza i wkład **[UZUPEŁNIĆ: sformułowanie autora]**
Propozycja asystenta:
1. Etykiety trudności trzeba mierzyć dla konkretnej pary modeli: etykiety z głosowań Chatbot Arena prawie nie przewidują przewagi naszego dużego modelu (AUROC 0,55).
2. Routing z samego tekstu zapytania ma sufit ok. 0,69 AUROC; część tego sufitu wynika z szumu etykiet blisko progu, a część z braku informacji o tym, co wie mały model.
3. Model decyzyjny zapytany wprost o trudność daje ranking porównywalny z kNN uczonym na ok. 1000–1500 etykietach, bez żadnych etykiet; to droga do routera dla nowej pary modeli bez kosztownego pomiaru.
4. Router działa jako zwykła usługa infrastruktury z narzutem rzędu kilkudziesięciu milisekund.

### 1.4. Układ pracy
Rozdział 2: przegląd literatury. Rozdział 3: dane i pomiar etykiet. Rozdział 4: projekt routera. Rozdział 5: implementacja w DeepFellow Infra. Rozdział 6: ewaluacja. Rozdział 7: warstwa 3 jako eksperyment. Rozdział 8: ograniczenia. Rozdział 9: wnioski. **[UZUPEŁNIĆ: deklaracja użycia narzędzi AI zgodnie z regulaminem uczelni.]**

## 2. Przegląd literatury

### 2.1. Routing przed odpowiedzią
- **RouteLLM** (Ong i in., ICLR 2025): routery uczone na preferencjach z Chatbot Arena dla pary GPT-4 / Mixtral; miary PGR, APGR i CPT, które przejmujemy. Na MT-Bench routery uczone tylko na danych Areny mają APGR 0,391–0,610 (losowy 0,500); dodatkowe etykiety od sędziego GPT-4 podnoszą wynik do 0,68–0,80; na MMLU routery z samej Areny są na poziomie losowym, a pomaga ok. 1500 etykiet ze znaną odpowiedzią (tabele 1–2 sprawdzone). Nasze APGR 0,61 jest na poziomie najlepszych routerów RouteLLM bez dodatkowych etykiet, ale porównanie jest orientacyjne: para GPT-4 / Mixtral ma znacznie większą różnicę jakości niż nasza para z jednej rodziny.
- **Hybrid LLM** (Ding i in., ICLR 2024): router oparty na przewidywanej różnicy jakości dwóch modeli; raportuje spadek jakości przy danym odsetku ruchu do małego modelu, co powtarzamy w analizie uzupełniającej. **[SPRAWDZIĆ: szczegóły metody i liczby przed cytowaniem.]**
- **LLMRouterBench** (2026): wiele routerów nie pokonuje najlepszego pojedynczego modelu, a wybór embeddera ma małe znaczenie; zgodne z naszym sufitem embeddingów. **[SPRAWDZIĆ: czytane w abstrakcie.]**

### 2.2. Kaskady i routing po odpowiedzi
- **FrugalGPT** **[UZUPEŁNIĆ: źródło nie jest opisane w repozytorium; dodać po przeczytaniu]**: kaskada modeli od najtańszego, z oceną odpowiedzi przed eskalacją.
- **Cascade routing** (Dekoninck i in., ICML 2025): połączenie routingu i kaskady w jednym schemacie. **[SPRAWDZIĆ.]**
- Kaskady widzą odpowiedź, więc mają więcej informacji, ale płacą za wygenerowanie odpowiedzi małego modelu przed decyzją i komplikują strumieniowanie. Praca świadomie wybiera routing przed odpowiedzią; kaskadę omawiamy jako alternatywę.

### 2.3. Sygnały z wnętrza modelu
- Aktywacje fazy prefill (NVIDIA, 2026) i liniowe sondy na stanach ukrytych („LLMs Encode Their Failures”, ICLR 2026) przebijają routery semantyczne; stany ukryte przed generacją niosą sygnał „wiem / nie wiem” (Ni i in., ACL 2025). **[SPRAWDZIĆ: wszystkie trzy czytane w abstrakcie.]** To najmocniejsza droga ponad sufit tekstu, ale wymaga dostępu do stanów ukrytych małego modelu, którego Ollama nie udostępnia; w pracy jako dalszy kierunek.
- **PopQA** (Mallen i in., 2023): skuteczność modeli na pytaniach o fakty silnie zależy od popularności encji; to wyjaśnia słabość routera na TriviaQA i wskazuje tanią cechę na przyszłość.

### 2.4. Modele decyzyjne i sędziowie
- Modele decyzyjne (Jev i otwarte odpowiedniki, m.in. basal, `nimble`, Clef) zwracają prawdopodobieństwa odpowiedzi na typowane pytania bez generowania tekstu.
- **JEV-as-a-Judge** (CMU, 2026): schemat „pewny przyjmij, niepewny przekaż”, progi zamrożone przed testem i wybierane dolną granicą przedziału ufności; ten sam artykuł raportuje słabsze wyniki tam, gdzie werdykt trzeba wyprowadzić (wiedza, kod, matematyka, logika), czyli tam, gdzie nasz router myli się najczęściej. **[SPRAWDZIĆ: przeczytane strony 1–6.]**
- „Jev vs LLMs as Rubric Judges” (2026): AUROC pewności 0,57–0,70, czasem poniżej 0,5; zalecenie walidacji każdego kryterium osobno. **[SPRAWDZIĆ.]**
- Progi z gwarancją: górna granica Clopper–Pearson i procedura Learn-then-Test; w pracy przyjęto wariant z poprawką Bonferroniego na z góry ustalonej siatce (D20). **[UZUPEŁNIĆ: źródła dla Clopper–Pearson i Learn-then-Test (Angelopoulos i in.) po sprawdzeniu.]**

### 2.5. Luka, którą wypełnia praca
Większość prac uczy routery na cudzych etykietach preferencji i dla par modeli o dużej różnicy jakości. Praca mierzy etykiety dla pary modeli z jednej rodziny, pokazuje granicę routingu z samego tekstu, sprawdza model decyzyjny jako źródło sygnału bez etykiet i wdraża router w działającej infrastrukturze z pomiarem narzutu i zachowania przy awariach.
