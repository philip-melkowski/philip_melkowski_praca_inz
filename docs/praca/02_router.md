# Szkic: router (roboczy, do redakcji przez autora)

Status: szkic z dziennika (`../DZIENNIK.md`, wpisy 5–8, 18–21, 23–28, 30). Miejsca **[UZUPEŁNIĆ]** wymagają danych lub decyzji autora.

## 1. Architektura

Router jest usługą `RouterService` w DeepFellow Infra (v0.34.0) i rejestruje model `router` w endpoincie `/v1/chat/completions`. Dla każdego żądania: (1) wyodrębnia tekst ostatniej wiadomości użytkownika; (2) warstwa 1 (reguły) może od razu skierować żądanie do dużego modelu; (3) warstwa 2 oblicza embedding tekstu lokalnym modelem `nomic-embed-text` (prefiks `classification: `) i wyznacza wynik 0–1 jako średnią etykiet k najbliższych sąsiadów (k=20, ważona podobieństwem kosinusowym) w indeksie zapytań uczących; (4) wynik porównywany jest z progiem administratora: wynik ≥ próg → duży model, w przeciwnym razie mały; (5) żądanie jest przekazywane wybranemu modelowi in-process przez `EndpointRegistry`. Każda awaria klasyfikatora (embedding, indeks, wymiary) kieruje żądanie do dużego modelu; to samo dotyczy niedostępnego małego modelu przed rozpoczęciem odpowiedzi. Każda decyzja jest logowana (model, warstwa, wynik, opóźnienie) i zwracana w nagłówkach `X-Router-*`. Warstwa 3 (mały model zero-shot z pewnością z logprobs) jest opcjonalna i podlega testowi go/no-go **[UZUPEŁNIĆ: wynik testu]**; w DeepFellow v0.34.0 żądanie czatu nie przenosi `logprobs`, więc test wymaga endpointu `/v1/completions`.

Konfiguracja to opcje usługi w JSON (`services.json`): modele, indeks, model embeddingowy, k, próg, reguły. Bez fine-tuningu modeli.

## 2. Wybór embeddera

Wymagania: lokalnie, szybko (cel poniżej 50 ms dla warstw 1+2), okno obejmujące zapytania. Ollama w kontenerze Docker na macOS nie ma dostępu do GPU (196–242 ms na zapytanie), Docker Model Runner nie uruchomił modelu na maszynie z 8 GB RAM; wybrano natywną Ollamę z usługą DF `ollama-external` (średnio 22 ms przez DF). Porównano cztery embeddery (kNN, walidacja krzyżowa po grupach, train+cal): nomic-embed-text, qwen3-embedding:0.6b, bge-m3, mxbai-embed-large. Różnice jakości są małe (AUROC 0,68–0,71); qwen3 jest minimalnie lepszy (AUROC +0,019, APGR +0,008, to drugie nieistotne), ale ok. 3 razy wolniejszy (p50 52 ms wobec 17,6 ms). Wybrano nomic-embed-text.

## 3. Ewaluacja

Metryki wg RouteLLM, liczone offline na zapisanych odpowiedziach: PGR (część przewagi dużego modelu odzyskana przy danym udziale zapytań kierowanych do dużego), APGR (PGR uśredniony po udziałach), CPT(50%) i CPT(80%) (minimalny udział dużego modelu dający 50% i 80% PGR), AUROC rozróżniania COMPLEX/SIMPLE; przedziały ufności z bootstrapu. Punkty odniesienia: losowy, sama długość, samo źródło, regresja logistyczna, oracle. Strojenie tylko walidacją krzyżową po grupach na train; ocena na cal; test nie był używany.

## 4. Wyniki (walidacja krzyżowa po grupach na train+cal, 3010 zapytań, Δ > 0,25)

| Metoda | AUROC | APGR |
|---|---|---|
| losowy | 0,50 | 0,50 |
| sama długość | 0,525 | 0,523 |
| samo źródło | 0,631 | 0,582 |
| warstwa 1 (reguły) | 0,577 | 0,543 |
| warstwa 2 (kNN) | **0,682** | **0,605** |
| warstwa 1 + 2 | 0,676 | 0,603 |
| oracle | 1,00 | 0,89 |

kNN istotnie przewyższa samą długość (APGR +0,082, CI [0,064; 0,101]) i samo źródło (+0,023, CI [0,009; 0,038]); reguły nie dodają nic do kNN. Żaden z dziewięciu przetestowanych klasyfikatorów (regresja logistyczna, SVM, MLP, boosting, regresja na Δ, kNN o różnym k) nie jest istotnie lepszy od kNN, więc sufit informacji w embeddingach wynosi ok. 0,68–0,71 AUROC. Szacunek górnej granicy wynikającej z szumu etykiet (zawyżony, bo duży ma jedną próbkę): AUROC ok. 0,9.

Interpretacja praktyczna (poza próbką): próg 0,3 kieruje 54% zapytań do dużego modelu przy jakości 0,777 wobec 0,846 dla „zawsze duży” i 0,625 dla „zawsze mały”; próg 0,5 kieruje 20% przy jakości 0,694. Efekt jest realny, ale umiarkowany.

Odporność (299 zapytań z cal): literówki (3% liter), parafrazy i zamiana ok. 20% słów na synonimy zmieniają decyzję dla 6–10% zapytań (losowe wyniki: 42–48%); korelacja wyników z oryginałem 0,92–0,95. Opóźnienie warstw 1+2 (natywna Ollama, M1 8 GB, bez DF): p50 20,6 ms, p90 65,5 ms; kNN trwa 0,08 ms.

## 4a. Analizy uzupełniające (dopisane 2026-11-22, tylko train, wpisy 117–118)

**Szum etykiet.** Na pytaniach z wyraźną różnicą jakości (Δ > 0,4 wobec Δ ≤ 0) AUROC kNN rośnie z 0,687 do 0,749 [0,722; 0,772]; korelacja Spearmana wyniku z ciągłym Δ wynosi 0,33. Część „sufitu” to więc pytania blisko progu, na których etykieta jest niepewna, a nie tylko brak informacji w tekście. Pytania, na których mały model jest wyraźnie lepszy (Δ ≤ −0,1), router myli z trudnymi (AUROC 0,58 wobec Δ > 0,5).

**Spadek jakości wobec „zawsze duży”** (jak w Hybrid LLM; jakość 0,847, „zawsze mały” 0,618):

| Ruch do małego | kNN | samo źródło | losowo |
|---|---|---|---|
| 20% | −2,9% [2,2; 3,6] | −2,7% | −5,4% |
| 40% | −7,1% | −7,5% | −10,8% |
| 50% | −9,6% | −10,5% | −13,5% |
| 60% | −12,1% | −13,6% | −16,2% |

Router zmniejsza stratę jakości wobec losowania o ok. 25–45% (więcej przy mniejszym ruchu do małego); przy małym udziale ruchu do małego modelu (20%) samo źródło daje podobny wynik.

**Progi z gwarancją** (górna granica Clopper–Pearson, metoda Bonferroniego na siatce udziałów, D20): na train błąd krytyczny (Δ > 0,5 wysłane do małego) ≤ 15% przy 65% ruchu do małego; COMPLEX ≤ 30% przy 40%; niższe cele bez progu. Wcześniejsza tabela (prezentacja, slajd 9) była liczona procedurą, która nie dawała poprawnej gwarancji.

**Nowe źródła** (Dolly, CodeChat, Arena 140k; 1050 pytań `extra_train`): kNN uczony na starych danych ma na nich AUROC 0,616, a w obrębie jednego źródła 0,54–0,59; po dołożeniu nowych pytań do indeksu (CV) 0,675, na starych bez zmian (0,687 → 0,691). Router słabo przenosi się na rodzaje zapytań, których nie ma w indeksie.

## 5. Ograniczenia i dalsze kroki

Test poza dziedziną i błąd krytyczny dopiero na zbiorze test (jednokrotne otwarcie, po zatwierdzeniu celów: `../CELE_PRZED_TESTEM.md`); `RouterService` działa z prawdziwymi modelami, testy awarii i restartu zaliczone (rozdział o implementacji); pełny benchmark routera w DF na docelowym sprzęcie **[UZUPEŁNIĆ]**; zgoda promotora **[UZUPEŁNIĆ]**.
