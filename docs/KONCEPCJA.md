# Koncepcja pracy: router zapytań (mały / duży model)

> **Kanoniczna kopia planu leży w repozytorium (od 2026-10-27).** Do tej daty plik był poza repozytorium (`koncepcja.md` w katalogu nadrzędnym). Decyzje autora zapadłe później, które zmieniają ten plan, są w `docs/DECYZJE.md` (tabela ze statusem) i tam, gdzie wprost zastępują tekst poniżej, mają pierwszeństwo; sam tekst planu zmieniono tylko w ścieżkach plików. Plan zmienia wyłącznie autor pracy.

Źródło: artefakt https://claude.ai/artifact/XZ71pUD3iWFG8ARaHg8jLL (przyjęty jako obowiązujący plan 2026-10-13). Ten plik jest jego zwięzłą wersją tekstową. Stare plany: `archiwum/v1/`.

Temat: Dynamiczny i semantyczny routing zapytań na podstawie złożoności zadania. Platforma: DeepFellow Infra (nowy `RouterService`, `/v1/chat/completions` z `model=router`).

## Cel
Dla każdego pytania wybrać przed odpowiedzią mały (SIMPLE) lub duży (COMPLEX) model, tak by zaoszczędzić koszt przy niewielkiej utracie jakości. Dwie klasy, bo dwa modele i jasna, mierzalna definicja.

## Etykieta (zmierzona)
- Mały model odpowiada 3×, duży 1–2×, jednakowy limit długości.
- Pytania z poprawną odpowiedzią (liczba, litera, fakt, kod z testami): ocena automatyczna 0/1. Pytania otwarte: sędzia Gemini, skala 1–5, wszystkie odpowiedzi naraz, losowa kolejność, bez nazw modeli; normalizacja (ocena−1)/4.
- Δ = Q_duży − średnia(Q_mały). COMPLEX gdy Δ > 0,25, inaczej SIMPLE. Próg startowy (autorski), wrażliwość dla 0,15 i 0,35. Ciągłe Δ zachowane.
- Flaga „oba zawiodły" (Q_duży < 0,5 i mały słaby): etykieta SIMPLE; w danych zostają, decyzja o usunięciu z uczenia po pomiarze (raport na całości i bez nich).
- Kontrola ludzka: 100 odpowiedzi, zgodność z sędzią raportowana.

## Dane (propozycja, licencje i dostępność do sprawdzenia)
Arena 1732 (mamy), pytania Gemini ≈450 z 900 (mamy), prawdziwe czaty WildChat/LMSYS ≈1000, TriviaQA/NQ ≈300, GSM8K ≈300, MMLU ≈300, HumanEval 164, MT-Bench 80. Razem ≈4600, sędzia ≈3300.
Tylko angielski, jedna tura, ≥16 tokenów. MMLU i MT-Bench wyłącznie test poza dziedziną; GSM8K dzielony. Podział ≈50% uczenie / ≈20% kalibracja / ≈30% test (zamknięty, otwierany raz). Usunięcie z testu pytań o podobieństwie embeddingów ≥0,95 do uczących. Walidacja krzyżowa przy dostrajaniu. Kategorie zostają w danych tylko do analizy błędów.

## Router
Warstwy: (1) reguły: tokeny (tiktoken cl100k_base), lista słów (wariant A, bez lematyzacji), struktura; (2) kNN (k>1) lub klastry na embeddingach liczonych lokalnie w DF modelem `nomic-embed-text` z prefiksem `classification: ` (okno 2048 tokenów, dłuższe pytania usunięte z bazy, zob. `docs/stage1/decisions/EMBED_LIMIT.md`); (3) opcjonalnie mały model zero-shot, pewność z logprobs, kalibracja regresją izotoniczną, wchodzi tylko po teście go/no-go. Każda warstwa musi udowodnić zysk (ablacja L2, L1+L2, L1+L2+L3). Wynik: liczba 0–1 vs próg administratora. Awaria klasyfikatora → duży model. Każda decyzja logowana. Bez fine-tuningu modeli. Plan B dla L3: większy model lokalny lub sonda liniowa (uzgodnić z promotorem).

## Integracja
`RouterService` na bazie `Base2Service`, wpięty w `lifecycle.py`; konfiguracja jako opcje serwisu (JSON, `services.json`; modele, próg, L3 on/off, k, lista słów); indeks embeddingów w pakiecie; wywołania in-process przez `EndpointRegistry`. Weryfikacja na DF v0.34.0 (klon DF poza tym repozytorium; ścieżki: `CLAUDE.md`).

## Ewaluacja
PGR, APGR, CPT(50/80%) wg RouteLLM, liczone offline na zapisanych odpowiedziach; punkty odniesienia: zawsze mały/duży, losowy, oracle, sama długość, samo źródło, regresja logistyczna. Dodatkowo: udział dużego, AUROC, wyniki wg trudności, odporność (parafrazy, literówki, synonimy ≈5%), kontrola routing collapse, test poza dziedziną, bootstrap, błąd krytyczny i kosztowy osobno, opóźnienie p50/p90 (cel <50 ms dla L1+L2). Cele liczbowe ustalane po pomiarze punktów odniesienia, przed otwarciem testu. Porównanie etykiet z głosowań Areny ze zmierzonymi jako analiza.

## Poza rdzeniem
Kategorie w routerze, Map-Reduce (opcjonalny etap końcowy), więcej niż dwa modele.

## Modele
Para jest parametrem. Duży: ok. 27B (Qwen3) w DF użytkownika, mały: ok. 8B. Dokładne nazwy, kwantyzację i tryb myślenia zapisać przed pomiarem.

## Kolejność
0 przygotowanie (modele, sędzia, DF v0.34.0) → 1 dane → 2 test potoku na ≈30 pytaniach, potem pełny pomiar (godziny, sędzia kilka USD) → 3 analiza zgodności etykiet z Areną i szumu; stop przy nieprzewidywalnych etykietach → 4 warstwy 1–2 i punkty odniesienia → 5 warstwa 3 i kalibracja → 6 RouterService → 7 ewaluacja końcowa → 8 Map-Reduce (opcja). Pisanie równolegle.

## Do potwierdzenia
Limit/cena Gemini, logprobs w DF, licencje zbiorów, opcje usługi na v0.34.0, zgoda promotora, termin.
