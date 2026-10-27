# Warstwa 3: Clef i nowe zestawy pytań (2026-10-27)

Praca samodzielna na prośbę autora. Szczegóły, liczby i wszystkie warianty: `docs/DZIENNIK.md`, wpisy 111–112. Wszystko liczone na train (walidacja krzyżowa po grupach); jedno potwierdzenie na cal; **test nie był używany**.

## Najważniejsze w skrócie

1. **Clef 27B (q4) to najlepszy dotąd model decyzyjny**, ale tylko trochę lepszy od innych. Na v1 (8 pytań), w strefie niepewności kNN: zysk AUROC +0,099 (tev1 +0,093, d1 +0,087, nimble +0,081). Na całym train: 0,724 (d1 0,712, nimble 0,710, sam kNN 0,686).
2. **Nowa pula 34 pytań (v2) z modelem GBM** zamiast regresji logistycznej (LR) daje wyraźnie więcej:
   - train, strefa: 0,708 (v1 LR 0,668);
   - cal, strefa: 0,699 (v1 LR 0,642), różnica +0,057 [+0,009; +0,108], istotna.
3. **Główny wskaźnik routera (APGR) rośnie mało, bez istotności.** Cały router z L3 w strefie, na cal: v1 +0,006, pula v2 + GBM +0,014 [−0,004; +0,031] względem samego kNN. AUROC poprawia się wyraźnie, APGR prawie nie.
4. **Wynik się nasyca.** Pomysły, które nic nie dodały:
   - 20 kolejnych pytań (v3);
   - łączenie kilku modeli decyzyjnych;
   - duży Qwen jako router;
   - inne cele uczenia.

   Górna granica to mniej więcej 0,75 AUROC na całości i 0,71 w strefie.
5. **Koszt.** Czas Clefa rośnie mniej więcej liniowo z liczbą pytań (p50 przez internet): 8 pytań 0,41 s, 34 pytania 1,5 s. Krótszego zestawu z tym samym zyskiem nie udało się znaleźć.

## Co sprawdzono

| Ścieżka | Wynik (strefa AUROC, train, chyba że zaznaczono) | Wniosek |
|---|---|---|
| Clef q4, v1 (8 pytań) | 0,667 (kNN 0,568); całość 0,724 | najlepszy model, niewielka przewaga |
| Clef, pula v2 (34), LR | 0,686; całość 0,737 | +0,018 vs v1, na granicy istotności |
| Clef, pula v2, **GBM** | **0,708**; całość **0,750**; cal 0,699 / 0,752 | najlepszy wariant, potwierdzony na cal |
| Wybór pytań zachłanny / 8 najlepszych pojedynczo | 0,667 / 0,667 | nie lepszy niż v1: najlepsze pytania mierzą to samo („trudność”) |
| Wybór wg ważności GBM (4/8/12/16 pytań) | 0,653 / 0,668 / 0,680 / 0,686 | brak skrótu, zysk rośnie z liczbą pytań |
| Pula v3 (+20 pytań o formę i intencję, razem 54) | LR 0,692, GBM 0,706 | nasycenie, nie warto |
| GBM na v1 innych modeli | d1 +0,123, nimble +0,114, strands, tev1 ≈ LR, basal gorzej | trop niestabilny na v1 |
| Łączenie modeli (Clef + tev1, sześć modeli) | 0,674 / 0,665–0,691 | ≤ +0,01, modele mówią to samo |
| Duży Qwen 27B ocenia cyfrą 0–9 (różnica, trudność) | 0,636; z Clefem nic nie dodaje | odrzucone |
| Samoocena qwen3:8b | 0,614 | słabiej niż modele decyzyjne |
| Cel ciągły (Δ, ql i qs osobno) zamiast etykiety | APGR −0,008 … −0,023 (sam kNN) | zostaje etykieta binarna |
| Szerokość strefy L3 (Clef v1, router) | 0,20–0,45: APGR +0,017; 0,10–0,60: +0,023; wszędzie +0,022 | 0,20–0,45 to rozsądny kompromis kosztu |

## Gdzie L3 pomaga

Clef v1, w strefie, AUROC kNN → kNN + L3:

| Źródło | kNN | kNN + L3 |
|---|---|---|
| chatbot_arena | 0,569 | 0,664 |
| wildchat | 0,490 | 0,595 |
| llm_generated | 0,659 | 0,702 |
| triviaqa | 0,406 | 0,532 |

Zysk jest głównie na pytaniach otwartych.

Z nowej puli działają pytania ogólne o trudność: `deep_analysis`, `quality_sensitive`, `hard_for_ai`, `ambiguous`, `both_fail`. Pytania wymyślone z przeglądu przykładów pojedynczo nie działają: odgrywanie ról, język inny niż angielski, tłumaczenie, pytania podchwytliwe.

## Uwagi do metody

- Na train sprawdzono kilkanaście wariantów, więc najlepszy wynik z train jest lekko zawyżony. Dlatego jest potwierdzenie na cal, z planem porównań zapisanym przed wynikiem.
- Cal był już wcześniej użyty do porównania modeli, więc i on jest lekko optymistyczny. Prawdziwą ocenę da dopiero test albo świeża część nowych danych.
- GBM nie był strojony. Ustawienia domyślne leżą w środku sprawdzonego zakresu (całość 0,735–0,758).
- Czasy z df.test idą przez internet i współdzielony serwer, więc to nie jest pomiar opóźnienia.

## Do decyzji autora

1. **Który zestaw w routerze:**
   - v1 (8 pytań): tańszy, czas mniej więcej ×1;
   - pula v2 (34 pytania) + GBM: lepsze AUROC, czas mniej więcej ×3,7.

   APGR różni się mało.
2. **Czy L3 w strefie, czy dla każdego zapytania.** Dla każdego zapytania wychodzi lepiej (cal: APGR +0,028 wobec +0,014), ale kosztuje wywołanie przy każdym zapytaniu.
3. **Pomiar opóźnienia** na maszynie z GPU, na miejscu.
4. **Potwierdzenie na świeżych danych**, po ocenie nowych pytań sędzią.
