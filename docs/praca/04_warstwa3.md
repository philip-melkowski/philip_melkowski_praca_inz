# Szkic: warstwa 3 – model decyzyjny w strefie niepewności (roboczy, do redakcji przez autora)

Status: szkic asystenta z 2026-11-22, zbudowany z dziennika (`../DZIENNIK.md`, wpisy 79–104, 111–118) i raportów `../WARSTWA3_nimble_wyniki.md`, `../WARSTWA3_PULA_PYTAN_2026-10-27.md`. Rozdział opisuje eksperyment, a nie rdzeń routera (D14a, D17). Miejsca **[UZUPEŁNIĆ]** wymagają decyzji autora.

## 1. Motywacja

kNN na embeddingach ocenia zapytanie po podobieństwie do zapytań o znanej trudności. Nie wie jednak, czy mały model zna konkretny fakt albo poradzi sobie z konkretnym zadaniem; stąd sufit ok. 0,69 AUROC i błędy na pytaniach o wiedzę i kod (rozdział o routerze). Warstwa 3 ma dostarczyć drugi, niezależny sygnał, tylko tam, gdzie kNN jest niepewny: dla wyniku kNN w strefie [0,20; 0,45), czyli dla ok. połowy zapytań (D15).

## 2. Model decyzyjny i protokół

**Model decyzyjny** nie pisze odpowiedzi. Dostaje tekst (tu: zapytanie użytkownika) i zestaw pytań z ustalonymi opcjami, np. tak/nie, i zwraca prawdopodobieństwo każdej odpowiedzi w jednym przebiegu. W DF i Ollamie służy do tego punkt końcowy `POST /v1/systemone` (D16; pierwotny plan zakładał odczyt prawdopodobieństw z małego modelu, ten wariant sprawdzono jako „samoocenę” i wypadł słabiej).

**Zestaw v1** (8 pytań, zamrożony przed pomiarem na cal, SHA-256 we wpisie 91): rzadka wiedza, rozumowanie wieloetapowe, kod, długa odpowiedź, jedna sprawdzalna odpowiedź, zadanie otwarte, wiele wymagań formy, „czy mały model wystarczy”. Odpowiedzi (logity prawdopodobieństw) łączy z logitem wyniku kNN regresja logistyczna uczona na train.

**Ochrona przed dopasowaniem do danych:** eksperymenty na train (walidacja krzyżowa po grupach, wynik kNN dla części uczącej z wewnętrznej CV); zestaw pytań zamrożony przed jednorazowym pomiarem na cal; cal użyty raz dla `nimble` i basal, potem tylko jedno potwierdzenie puli v2 z Clefem za zgodą autora (D15, D15a); zbiór test nieużywany.

**Miary:** G1 – zysk AUROC w strefie (kNN + model wobec samego kNN), go, gdy dolna granica 95% CI > 0; dodatkowo AUROC i APGR całego routera ze strefą oraz odsetek poważnych błędów (Δ > 0,5 wysłane do małego).

## 3. Wyniki

### 3.1. Wiele modeli, zestaw v1

| Model | Gdzie liczony | Zysk AUROC w strefie | Uwagi |
|---|---|---|---|
| `nimble` (9B) | **cal** | +0,066 [+0,007; +0,126] | router ze strefą na całym cal +0,013 [−0,005; +0,028], n.s. |
| basal-2.0-4.5B | **cal** | +0,084 [+0,025; +0,144] | router ze strefą +0,019 [+0,004; +0,035] |
| `nimble` | train | +0,081 [+0,042; +0,116] | |
| basal-2.0-4.5B | train | +0,077 [+0,041; +0,113] | |
| `strands-decider` (2B) | train | +0,083 [+0,047; +0,122] | |
| `d1` (3B) | train | +0,087 [+0,050; +0,128] | |
| `tev1` (4B) | train | +0,093 [+0,054; +0,131] | |
| Clef 27B (q4) | train | +0,099 [+0,060; +0,137] | najlepszy, przedziały nakładają się z innymi |
| samoocena `qwen3:8b` | train | +0,045 [+0,009; +0,081] | odczyt prawdopodobieństw z małego modelu |
| `laya` (ModernBERT) | train | +0,002 [−0,026; +0,030] | brak sygnału |

Wszystkie działające modele dają podobny zysk (ok. +0,08–0,10 AUROC w strefie), więc sygnał jest raczej cechą zadania niż konkretnego modelu. Najsilniejsze pytania u wszystkich: długa odpowiedź, zadanie otwarte, jedna sprawdzalna odpowiedź, „czy mały wystarczy”.

### 3.2. Większy zestaw pytań i nieliniowe łączenie (Clef, d1)

Pula 34 pytań (`pool_v2.json`) z modelem GBM (zespół drzew decyzyjnych) zamiast regresji logistycznej:

| Wariant | AUROC w strefie | AUROC całość | Gdzie |
|---|---|---|---|
| kNN | 0,569 | 0,686 | train |
| Clef, v1 + LR | 0,668 | 0,725 | train |
| Clef, pula v2 + GBM | 0,708 | 0,750 | train |
| d1, pula v2 + GBM | 0,696 | 0,747 | train |
| Clef, pula v2 + GBM | **0,699** (v1 0,642; różnica +0,057 [+0,009; +0,108]) | 0,752 | **cal** (D15a) |

Mimo wyraźnej poprawy AUROC **APGR całego routera ze strefą rośnie mało**: na cal +0,014 [−0,004; +0,031] wobec samego kNN. Wynik nasyca się ok. 0,75 AUROC; dokładanie pytań (pula v3), łączenie kilku modeli, duży Qwen jako oceniający i cel ciągły nic nie dodały (wpis 112).

### 3.3. Model decyzyjny bez kNN i bez etykiet

- Sam Clef z pulą i GBM (bez kNN): AUROC 0,744 wobec 0,750 z kNN i 0,687 samego kNN (train). Przy dobrym modelu decyzyjnym kNN dokłada niewiele.
- Jedno pytanie zero-shot („czy mały model wystarczy?”) daje ranking, który kNN osiąga dopiero przy ok. 1000–1500 etykietach (krzywa uczenia, wpis 99). To argument za routerem „bez zimnego startu” dla nowej pary modeli.

### 3.4. Koszt czasu

| Model, zestaw | Sprzęt | p50 |
|---|---|---|
| `nimble`, v1 | Mac M5 16 GB | 3,7 s |
| d1, v1 | Mac M5 | 0,8 s |
| Clef 27B, v1 / pula v2 | df.test przez internet | 0,41 s / 1,5 s |
| **d1, v1 / pula v2** | **RTX 5070 Ti (Ollama, tunel SSH)** | **0,11 s / 0,36 s** |

Na GPU d1 z 8 pytaniami kosztuje ok. 0,1 s na zapytanie w strefie, ok. 12,5 żądań/s przy 4 równoległych (wpis 118).

## 4. Wdrożenie

Warstwa 3 jest w `RouterService` jako opcja (`decider_path`): zestaw v1 i regresja logistyczna (wagi to zwykłe liczby, bez nowych zależności w DF), tylko w strefie, błąd lub 5 s → duży model. Wzór w DF zgadza się z `predict_proba` z biblioteki scikit-learn z dokładnością 10⁻¹⁶. Działanie pokazano na żywo (seminarium 28.10): zapytanie z wynikiem kNN 0,26 (sam kNN: mały) przeszło do dużego po ocenie modelu decyzyjnego (0,52), a zapytanie z wynikiem 0,39 (sam kNN: duży) do małego (0,28); oba zgodnie z prawdziwą etykietą.

## 5. Wnioski

- Model decyzyjny niesie informację o trudności, której nie ma kNN: powtarzalnie dla kilku modeli i potwierdzone na cal.
- Zysk dla całego routera jest mały i na granicy istotności: poprawa rankingu w strefie słabo przekłada się na jakość przy danym koszcie.
- Tani model (d1 3B) jest prawie tak dobry jak Clef 27B i na GPU kosztuje ok. 0,1 s.
- Ograniczenia: Clef na df.test zmienił wersję (`clef:27b`, wpis 117), więc wyniki z Clefem dotyczą wersji q4_K_M; cal był użyty kilkakrotnie, więc liczby z cal są lekko optymistyczne; d1 wymaga wpisu w katalogu modeli decyzyjnych DF.

**[UZUPEŁNIĆ: decyzja go/no-go (D17), wybór modelu i zestawu (D18), lista porównywanych wariantów (D19) i wynik na zbiorze testowym, jeśli warstwa 3 wejdzie do porównania.]**
