# Protokół jednorazowego otwarcia zbioru test (zapisany przed otwarciem)

Data zapisu: 2026-11-22, przed jakimkolwiek wynikiem na zbiorze test. Podstawa: `DECYZJE.md` D14a, D17, D20, D21, D22 (cele zatwierdzone przez autora; promotor się zgodził wg autora), wpisy 121–126. Po otwarciu testu **nic z tego protokołu ani routera się nie zmienia**; wyniki raportujemy niezależnie od tego, czy cele są spełnione.

## 1. Router (zamrożony przed otwarciem; pliki i SHA-256 w sekcji 6)
- **R0 (główny):** warstwa 1 = heurystyki z `data/router_l1.json`, próg 2 pkt (tylko „do dużego”), słowa jako całe wyrazy; warstwa 2 = kNN k = 20 (średnia ważona podobieństwem), `nomic-embed-text` z prefiksem `classification: `, indeks z **train + cal + `extra_train`** (D21), próg 0,3.
- **R1 (wariant dodatkowy, D17):** R0 + warstwa 3 z d1:3b w strefie [0,20; 0,45) wyniku kNN; zestaw i model łączenia według reguły z wpisu 125 (wynik wyboru: wpis 126); uczenie na train + `extra_train`.
- **Wynik do AUROC/APGR:** dla zapytań skierowanych przez heurystyki do dużego wynik = 1,0; w pozostałych wynik kNN (R0) albo wynik routera ze strefą (R1).

## 2. Dane
- Zbiór test: 1294 pytania; **w dziedzinie 766** (bez MMLU, MT-Bench i 150 pytań GSM8K poza dziedziną; pole `ood`), poza dziedziną 528 – raportowane osobno.
- Etykiety: Δ = jakość dużego − średnia jakość małego (3 próbki), COMPLEX gdy Δ > 0,25.
- **Wersje etykiet:** v3 (`data/labels/labels_v3.jsonl`, ponowne odpowiedzi z limitem 4096, wpis 124) przyszły **przed zamrożeniem**, więc router (indeks, warstwa 3, progi) jest zbudowany na v3, a **wynik główny liczony na v3**; v2 (`labels.jsonl`) raportowane obok dla porównania.

## 3. Cele (D22)
1. APGR(R0) − APGR(„sama długość”) > 0: dolna granica 95% przedziału różnicy parowanej (bootstrap po grupach, 2000 losowań, ziarno 42).
2. AUROC(R0) ≥ 0,64.
3. APGR(R0) − APGR(„samo źródło”) > 0 (jak 1) – raportowany zawsze.
**Sukces główny = 1 i 2.**

Punkty odniesienia: „sama długość” = log liczby tokenów pytania; „samo źródło” = odsetek COMPLEX danego źródła w train + cal + `extra_train` (źródło nieznane w danych uczących → odsetek ogólny); losowy; „zawsze mały”, „zawsze duży”; idealny (prawdziwe Δ).

## 4. Pozostałe miary (raportowane, cele C3–C6 bez zmian)
- C3: CPT80 ≤ 0,72.
- C4: odporność – na próbie 300 pytań testowych w dziedzinie (losowanie ziarnem 7): literówki, parafrazy, synonimy (Gemini 3.8 Flash, jak na cal), zmiana decyzji R0 przy progu dającym 30% do dużego ≤ 15%.
- C5: opóźnienie decyzji R0 przez DF (p50 < 50 ms).
- C6: poza dziedziną (528) i błąd krytyczny (Δ > 0,5 skierowane do małego przy 50% do dużego) – bez progu.
- Progi z gwarancją (D20, Bonferroni): progi wyznaczone na train + cal + `extra_train` (wyniki kNN z CV), sprawdzone na teście.
- R1 wobec R0: różnica AUROC i APGR (parowana, jak wyżej), odsetek zapytań wołających warstwę 3, czas d1 na GPU – bez progu sukcesu.
- Wyniki według źródła (w dziedzinie).

## 5. Czego nie robimy
- Żadnej zmiany routera, progów, zestawu pytań ani metody po zobaczeniu wyników testu.
- Żadnego wyboru między wariantami R0/R1 na podstawie testu (R0 jest główny niezależnie od wyniku).

## 6. Zamrożone pliki
Uzupełniane przy zamrożeniu (wpis 126), przed otwarciem.
