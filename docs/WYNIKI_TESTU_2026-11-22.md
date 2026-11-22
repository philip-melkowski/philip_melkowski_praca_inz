# Wyniki jednorazowego otwarcia zbioru test (2026-11-22)

Protokół: `PROTOKOL_TESTU_2026-11-22.md` (zapisany i zacommitowany przed otwarciem, router zamrożony w commicie 767a0cd). Ocena: `eval/test_final.py`. Wynik główny: etykiety v3; v2 dla porównania. Po otwarciu niczego w routerze ani protokole nie zmieniano.

## Najważniejsze (w dziedzinie, 766 pytań, etykiety v3)

| Cel (D22) | Wynik | Spełniony |
|---|---|---|
| 1. APGR routera R0 > „sama długość” | +0,055 [+0,019; +0,092] | **tak** |
| 2. AUROC R0 ≥ 0,64 | 0,674 [0,635; 0,712] | **tak** |
| 3. APGR R0 > „samo źródło” | −0,003 [−0,032; +0,025] | nie wykazano |
| C3. CPT80 ≤ 0,72 | 0,67 | tak |

**Sukces główny (cele 1 i 2): spełniony** (na v3 i na v2).

- **Warstwa 3 (R1, d1, wariant dodatkowy):** wobec R0 APGR **+0,022 [+0,010; +0,035]**, AUROC +0,035 [+0,020; +0,053]; błąd krytyczny przy 50% do dużego 4,6% wobec 5,6%. Warstwa 3 jest wołana dla 43% zapytań w dziedzinie. Poza dziedziną bez zysku (+0,007 [−0,020; +0,037]).
- **Poza dziedziną (528, MMLU, MT-Bench, GSM8K):** R0 AUROC 0,657, APGR 0,649; lepszy od długości w AUROC (+0,111), na poziomie źródła.
- **Progi z gwarancją (Bonferroni, D20)** wyznaczone na train + cal + `extra_train`: wszystkie spełnione na teście (np. błąd krytyczny ≤ 15%: 65,7% do małego, błąd 11,3%; COMPLEX ≤ 30%: 51,3% do małego, 27,0%).
- **Według źródła (R0, v3):** GSM8K 0,931, wygenerowane przez Gemini 0,733, WildChat 0,596, Arena 0,584, HumanEval 0,527, TriviaQA 0,408 (wiedza faktograficzna nadal najsłabsza).

## C4 i C5 (wpis 127)

| Miara | Wynik | Cel |
|---|---|---|
| C4: zmiana decyzji R0 przy 30% do dużego (300 pytań testowych) | literówki 8,3%, synonimy 8,3%, parafrazy 13,0% (losowo 40,7%) | ≤ 15%: **spełniony** |
| C5: decyzja R0 przez DF, DF i Ollama na jednym komputerze | p50 12,5 ms, p90 18,5 ms | < 50 ms: **spełniony** |
| C5: decyzja R0 przez DF, embeddingi na zdalnym GPU przez tunel SSH/VPN | p50 61,2 ms, p90 74,6 ms | < 50 ms: niespełniony (sieć) |
| R1: decyzja z warstwą 3 (d1 na GPU przez tunel) | p50 74,4 ms; zapytania z warstwą 3 p50 194,5 ms | bez celu |

Uwaga: przy czterech modelach na karcie 16 GB Ollama przeładowywała d1 i warstwa 3 przekraczała 5 s (router przechodził wtedy na duży model, zgodnie z projektem); przy trzech modelach (mały, embeddingi, d1) bez przekroczeń.

## Pełne wyjście: etykiety v3 (wynik główny)

```
indeks data/router/router_index_final.npz (ee402377f4cd22c8), heurystyki (13e9e69fa9524415), warstwa 3 data/router/router_l3_d1_final.json (d3135bec9b52e65c)
etykiety: data/labels/labels_v3.jsonl (f252b46d50dd3ad8)

=== TEST W DZIEDZINIE (cele): 766 pytań, COMPLEX 37.6%, heurystyki → duży 6.8%, strefa warstwy 3 43.2% ===
  jakość: zawsze duży 0.852, zawsze mały 0.634
  R0 (warstwy 1+2)     AUROC 0.674 [0.635; 0.712]  APGR 0.600 [0.570; 0.631]  CPT80 0.67
  R1 (+ warstwa 3)     AUROC 0.709 [0.670; 0.745]  APGR 0.623 [0.590; 0.655]  CPT80 0.63
  sama długość         AUROC 0.572 [0.531; 0.617]  APGR 0.545 [0.516; 0.577]  CPT80 0.76
  samo źródło          AUROC 0.663 [0.626; 0.700]  APGR 0.605 [0.572; 0.634]  CPT80 0.65
  idealny              AUROC 1.000 [1.000; 1.000]  APGR 0.900 [0.855; 0.951]  CPT80 0.29
  różnica R0 (warstwy 1+2) − sama długość: APGR +0.055 [+0.019; +0.092]  AUROC +0.100 [+0.048; +0.153]
  różnica R0 (warstwy 1+2) − samo źródło: APGR -0.003 [-0.032; +0.025]  AUROC +0.011 [-0.030; +0.052]
  różnica R1 (+ warstwa 3) − R0 (warstwy 1+2): APGR +0.022 [+0.010; +0.035]  AUROC +0.035 [+0.020; +0.053]
  R0: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 5.6% pytań
  R1: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 4.6% pytań

  CELE D22: (1) R0 > długość: TAK; (2) AUROC 0.674 ≥ 0,64: TAK; (3) R0 > źródło: nie wykazano; C3 CPT80 0.67 ≤ 0,72: TAK
  SUKCES GŁÓWNY (1 i 2): TAK

  według źródła (R0):
    chatbot_arena  n= 349 COMPLEX 44.4% AUROC 0.584
    gsm8k          n=  30 COMPLEX  3.3% AUROC 0.931
    humaneval      n=  33 COMPLEX 21.2% AUROC 0.527
    llm_generated  n=  92 COMPLEX 12.0% AUROC 0.733
    triviaqa       n=  60 COMPLEX 18.3% AUROC 0.408
    wildchat       n= 202 COMPLEX 51.0% AUROC 0.596

=== TEST POZA DZIEDZINĄ (C6, bez progu): 528 pytań, COMPLEX 22.0%, heurystyki → duży 4.0%, strefa warstwy 3 43.2% ===
  jakość: zawsze duży 0.880, zawsze mały 0.765
  R0 (warstwy 1+2)     AUROC 0.657 [0.604; 0.707]  APGR 0.649 [0.582; 0.709]  CPT80 0.57
  R1 (+ warstwa 3)     AUROC 0.657 [0.603; 0.707]  APGR 0.656 [0.591; 0.716]  CPT80 0.61
  sama długość         AUROC 0.546 [0.477; 0.612]  APGR 0.566 [0.472; 0.648]  CPT80 0.88
  samo źródło          AUROC 0.654 [0.625; 0.685]  APGR 0.613 [0.568; 0.691]  CPT80 0.58
  idealny              AUROC 1.000 [1.000; 1.000]  APGR 1.195 [1.052; 1.450]  CPT80 0.10
  różnica R0 (warstwy 1+2) − sama długość: APGR +0.083 [-0.012; +0.179]  AUROC +0.111 [+0.037; +0.185]
  różnica R0 (warstwy 1+2) − samo źródło: APGR +0.018 [-0.064; +0.098]  AUROC +0.002 [-0.045; +0.048]
  różnica R1 (+ warstwa 3) − R0 (warstwy 1+2): APGR +0.007 [-0.020; +0.037]  AUROC -0.001 [-0.024; +0.023]
  R0: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 3.4% pytań
  R1: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 3.6% pytań

=== Progi z gwarancją (D20, Bonferroni): FIT = train + cal + extra_train (kNN z CV), sprawdzenie na teście w dziedzinie ===
  błąd krytyczny ≤ 10%: brak progu na FIT
  błąd krytyczny ≤ 12%: próg 0.197; test: do małego 18.4%, błąd 8.5% → spełniony
  błąd krytyczny ≤ 15%: próg 0.411; test: do małego 65.7%, błąd 11.3% → spełniony
  COMPLEX ≤ 25%: próg 0.202; test: do małego 23.0%, błąd 16.5% → spełniony
  COMPLEX ≤ 30%: próg 0.349; test: do małego 51.3%, błąd 27.0% → spełniony
```

## Pełne wyjście: etykiety v2 (porównanie)

```
indeks data/router/router_index_final.npz (ee402377f4cd22c8), heurystyki (13e9e69fa9524415), warstwa 3 data/router/router_l3_d1_final.json (d3135bec9b52e65c)
etykiety: data/datasets/labels.jsonl (937f121443059ef7)

=== TEST W DZIEDZINIE (cele): 766 pytań, COMPLEX 36.7%, heurystyki → duży 6.8%, strefa warstwy 3 43.2% ===
  jakość: zawsze duży 0.841, zawsze mały 0.634
  R0 (warstwy 1+2)     AUROC 0.667 [0.628; 0.706]  APGR 0.603 [0.571; 0.639]  CPT80 0.64
  R1 (+ warstwa 3)     AUROC 0.701 [0.663; 0.739]  APGR 0.625 [0.590; 0.661]  CPT80 0.60
  sama długość         AUROC 0.548 [0.505; 0.592]  APGR 0.528 [0.499; 0.563]  CPT80 0.78
  samo źródło          AUROC 0.662 [0.625; 0.699]  APGR 0.609 [0.577; 0.645]  CPT80 0.64
  idealny              AUROC 1.000 [1.000; 1.000]  APGR 0.925 [0.875; 0.985]  CPT80 0.28
  różnica R0 (warstwy 1+2) − sama długość: APGR +0.075 [+0.035; +0.116]  AUROC +0.119 [+0.069; +0.172]
  różnica R0 (warstwy 1+2) − samo źródło: APGR -0.006 [-0.036; +0.022]  AUROC +0.005 [-0.036; +0.048]
  różnica R1 (+ warstwa 3) − R0 (warstwy 1+2): APGR +0.021 [+0.008; +0.034]  AUROC +0.034 [+0.018; +0.051]
  R0: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 5.5% pytań
  R1: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 4.4% pytań

  CELE D22: (1) R0 > długość: TAK; (2) AUROC 0.667 ≥ 0,64: TAK; (3) R0 > źródło: nie wykazano; C3 CPT80 0.64 ≤ 0,72: TAK
  SUKCES GŁÓWNY (1 i 2): TAK

  według źródła (R0):
    chatbot_arena  n= 349 COMPLEX 43.3% AUROC 0.567
    gsm8k          n=  30 COMPLEX  3.3% AUROC 0.931
    humaneval      n=  33 COMPLEX 18.2% AUROC 0.500
    llm_generated  n=  92 COMPLEX 12.0% AUROC 0.733
    triviaqa       n=  60 COMPLEX 18.3% AUROC 0.408
    wildchat       n= 202 COMPLEX 50.0% AUROC 0.589

=== TEST POZA DZIEDZINĄ (C6, bez progu): 528 pytań, COMPLEX 21.8%, heurystyki → duży 4.0%, strefa warstwy 3 43.2% ===
  jakość: zawsze duży 0.876, zawsze mały 0.764
  R0 (warstwy 1+2)     AUROC 0.654 [0.602; 0.704]  APGR 0.655 [0.581; 0.719]  CPT80 0.56
  R1 (+ warstwa 3)     AUROC 0.654 [0.600; 0.705]  APGR 0.662 [0.591; 0.729]  CPT80 0.61
  sama długość         AUROC 0.542 [0.474; 0.609]  APGR 0.560 [0.460; 0.643]  CPT80 0.88
  samo źródło          AUROC 0.654 [0.624; 0.685]  APGR 0.626 [0.574; 0.708]  CPT80 0.58
  idealny              AUROC 1.000 [1.000; 1.000]  APGR 1.220 [1.067; 1.498]  CPT80 0.10
  różnica R0 (warstwy 1+2) − sama długość: APGR +0.096 [-0.007; +0.205]  AUROC +0.112 [+0.038; +0.187]
  różnica R0 (warstwy 1+2) − samo źródło: APGR +0.016 [-0.071; +0.100]  AUROC -0.000 [-0.048; +0.045]
  różnica R1 (+ warstwa 3) − R0 (warstwy 1+2): APGR +0.008 [-0.020; +0.039]  AUROC -0.001 [-0.024; +0.024]
  R0: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 3.4% pytań
  R1: błąd krytyczny (Δ > 0,5 do małego) przy 50% do dużego: 3.6% pytań

=== Progi z gwarancją (D20, Bonferroni): FIT = train + cal + extra_train (kNN z CV), sprawdzenie na teście w dziedzinie ===
  błąd krytyczny ≤ 10%: brak progu na FIT
  błąd krytyczny ≤ 12%: próg 0.247; test: do małego 28.2%, błąd 9.3% → spełniony
  błąd krytyczny ≤ 15%: próg 0.459; test: do małego 72.2%, błąd 11.4% → spełniony
  COMPLEX ≤ 25%: próg 0.247; test: do małego 28.2%, błąd 17.6% → spełniony
  COMPLEX ≤ 30%: próg 0.346; test: do małego 49.2%, błąd 25.7% → spełniony
```
