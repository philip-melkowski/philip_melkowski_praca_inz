# Szkic: ewaluacja na zbiorze testowym (roboczy, do redakcji przez autora)

Status: szkic asystenta z 2026-11-22, na podstawie `../PROTOKOL_TESTU_2026-11-22.md` i `../WYNIKI_TESTU_2026-11-22.md` (dziennik, wpisy 124–127). Liczby w nawiasach kwadratowych to 95% przedziały ufności z bootstrapu po grupach prawie-duplikatów (2000 losowań).

## 1. Protokół

Zbiór testowy (1294 zapytania, 30% danych) odłożono na początku pracy i nie używano go do żadnego wyboru. Przed otwarciem:
- zamrożono router (pliki i sumy SHA-256 w protokole; commit 767a0cd),
- zapisano cele (D22) i sposób liczenia,
- sprawdzono kod oceny na losowych, zmyślonych etykietach.

Zbiór otwarto raz. Oceniono dwa warianty: **R0** (główny: heurystyki + kNN, indeks z 4060 zapytań) i **R1** (R0 + warstwa 3 z modelem decyzyjnym d1 w strefie niepewności). Wynik główny liczono na etykietach v3, w których odpowiedzi ucięte przy 2048 tokenach zastąpiono odpowiedziami z limitem 4096 (zmiana klasy u 22 z 1294 pytań testowych); etykiety v2 podano dla porównania. Cele liczono na 766 zapytaniach z dziedziny; 528 zapytań spoza dziedziny (MMLU, MT-Bench, część GSM8K) raportowano osobno.

## 2. Cele

| Cel | Wynik (v3) | Wynik (v2) | Spełniony |
|---|---|---|---|
| 1. APGR(R0) − APGR(sama długość) > 0 | +0,055 [+0,019; +0,092] | +0,075 [+0,035; +0,116] | tak |
| 2. AUROC(R0) ≥ 0,64 | 0,674 [0,635; 0,712] | 0,667 [0,628; 0,706] | tak |
| 3. APGR(R0) − APGR(samo źródło) > 0 | −0,003 [−0,032; +0,025] | −0,006 [−0,036; +0,022] | nie wykazano |
| C3. CPT80 ≤ 0,72 | 0,67 | 0,64 | tak |
| C4. zmiana decyzji ≤ 15% (literówki / synonimy / parafrazy) | 8,3 / 8,3 / 13,0% | – | tak |
| C5. p50 decyzji przez DF < 50 ms | 12,5 ms (DF i Ollama na jednym komputerze); 61,2 ms (embeddingi na zdalnym GPU przez tunel) | – | tak / nie (sieć) |

**Sukces główny (cele 1 i 2) spełniony.** Router wyraźnie przewyższa regułę opartą na długości i osiąga zakładany poziom rankingu. Nie wykazano, że jest lepszy od „samego źródła” (reguły znającej rodzaj zapytania, której w praktyce nie da się zastosować, bo źródła nie znamy): router rozpoznaje głównie rodzaj zapytania, a dodatkowa informacja o trudności w obrębie rodzaju jest mała. Moc tego porównania szacowano przed testem na ok. 40–55%.

## 3. Wyniki szczegółowe (v3, w dziedzinie)

| Router | AUROC | APGR | CPT80 |
|---|---|---|---|
| sama długość | 0,572 | 0,545 | 0,76 |
| samo źródło | 0,663 | 0,605 | 0,65 |
| **R0 (warstwy 1+2)** | **0,674** | **0,600** | **0,67** |
| **R1 (+ warstwa 3)** | **0,709** | **0,623** | **0,63** |
| idealny | 1,000 | 0,900 | 0,29 |

Jakość: „zawsze duży” 0,852, „zawsze mały” 0,634. Heurystyki kierują od razu do dużego modelu 6,8% zapytań; warstwa 3 jest pytana dla 43% zapytań.

**Warstwa 3:** R1 − R0: APGR +0,022 [+0,010; +0,035], AUROC +0,035 [+0,020; +0,053]; błąd krytyczny (Δ > 0,5 skierowane do małego przy 50% ruchu do dużego) 4,6% wobec 5,6%. Zysk na teście jest istotny i większy niż w walidacji krzyżowej (+0,008) i na świeżym zbiorze `extra_val` (+0,004, nieistotne); różnicę między zbiorami należy traktować ostrożnie (zmienność próby; test ma inny rozkład źródeł). Poza dziedziną warstwa 3 nie pomaga (+0,007, nieistotne).

**Według źródła (R0, AUROC):** GSM8K 0,931, zapytania wygenerowane przez Gemini 0,733, WildChat 0,596, Chatbot Arena 0,584, HumanEval 0,527, TriviaQA 0,408. Najsłabsze pozostają wiedza faktograficzna i kod, jak w walidacji.

**Poza dziedziną (528):** R0 AUROC 0,657, APGR 0,649; lepszy od długości w AUROC (+0,111 [+0,037; +0,185]), na poziomie źródła.

**Progi z gwarancją** (metoda Bonferroniego, wyznaczone na train + cal + `extra_train`): wszystkie cele zostały dotrzymane na teście, np. „błąd krytyczny ≤ 15%” przy 65,7% ruchu do małego (zaobserwowano 11,3%), „COMPLEX ≤ 30%” przy 51,3% ruchu do małego (27,0%).

## 4. Interpretacja w praktyce

Przy progu, który kieruje połowę ruchu do małego modelu, router zachowuje większość jakości dużego modelu, a progi z gwarancją pozwalają administratorowi wybrać udział ruchu do małego modelu przy kontrolowanym odsetku poważnych błędów. **[UZUPEŁNIĆ: przeliczenie na oszczędność czasu GPU dla konkretnego wdrożenia.]** Analiza na danych uczących (rozdział o routerze, sekcja 4a): przy 20 / 40 / 50% ruchu do małego jakość spada o 2,9 / 7,1 / 9,6% wobec „zawsze duży”, wobec 5,4 / 10,8 / 13,5% przy losowym wyborze.
