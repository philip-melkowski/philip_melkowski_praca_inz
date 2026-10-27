# Rejestr decyzji: co obowiązuje teraz

Dziennik (`DZIENNIK.md`) opowiada historię po kolei. Ten plik mówi, **co z niej obowiązuje dziś**. Jedna decyzja = jeden wiersz; nowa decyzja, która zastępuje starą, zmienia jej status na „zastąpiona” (nie usuwamy wierszy). Kto decydował: **A** = autor pracy, **As** = propozycja asystenta przyjęta przez autora.

Statusy: **obowiązuje** / **zastąpiona** (przez kogo) / **odrzucona** / **propozycja** (czeka na autora).

## Plan, dane, pomiar

| # | Decyzja | Kto | Status | Wpis |
|---|---|---|---|---|
| D1 | Obowiązujący plan to `KONCEPCJA.md`; stare plany w `archiwum/v1/` (nieobowiązujące, nie usuwać) | A | obowiązuje | 1 |
| D2 | Dwie klasy; etykieta Δ = Q_duży − średnia(Q_mały, 3 próbki), COMPLEX gdy Δ > 0,25 (wrażliwość 0,15 i 0,35) | A | obowiązuje | 17, 24 |
| D3 | Para modeli: `qwen3:8b` (mały) i `Qwen/Qwen3.8-27B-FP8` (duży); myślenie wyłączone; temperatura 0,7 | A | obowiązuje | 10, 13 |
| D4 | Limit odpowiedzi: 2048 tokenów, ucięte tylko z flagą → **4096, ucięte powtórzone** → ocena „tak jak są” | A | D4 (2048): zastąpiona; **obowiązuje 4096 + ocena bez usuwania** | 14, 106, 109 |
| D5 | Podział ok. 50/20/30 (train/cal/test); prawie-duplikaty (embedding ≥ 0,95) zawsze w jednym zbiorze; MMLU, MT-Bench i 150 pytań GSM8K tylko w teście (poza dziedziną) | A | obowiązuje | 9 |
| D6 | **Zbiór test zamknięty**, otwierany raz, na ustalonej wersji routera; strojenie tylko CV po grupach na train (i cal) | A | obowiązuje | 29, `CLAUDE.md` |
| D7 | Ocena: pytania ze znaną odpowiedzią automatycznie; otwarte sędzią Gemini Flash (skala 1–5, losowa kolejność, bez nazw modeli). Drugi sędzia (Pro) tylko kontrola na 100 pytaniach. Płatne wywołania tylko po zgodzie na konkretną kwotę | A | obowiązuje | 16, 17, 36, 37 |
| D8 | Pytania fan-fiction/odgrywania ról zostają w zbiorze; raportować wyniki z nimi i bez nich | As | obowiązuje (do potwierdzenia przez autora) | 52 |
| D9 | Dodatkowe pytania: Dolly 15k, CodeChat, Arena 140k (po 500); Spider pominięty (ocena wymaga uruchamiania SQL). Licencje sprawdzone na kartach zbiorów (CC BY-SA 3.0, ODC-By, CC BY 4.0), bez interpretacji prawnej | A | obowiązuje | 71, 72, 105 |

## Router

| # | Decyzja | Kto | Status | Wpis |
|---|---|---|---|---|
| D10 | Router jako zwykła usługa DF (`RouterService`, `Base2Service`), nie plugin DeepFellow Server | A | obowiązuje | 27 |
| D11 | Embeddingi: `nomic-embed-text` z prefiksem `classification: `, pytania > 2048 tokenów usunięte z bazy. Sprawdzone i odrzucone: `qwen3-embedding`, `bge-m3`, `mxbai-embed-large` | As | obowiązuje | 5, 6, 30 |
| D12 | Warstwa 1: heurystyki punktowe, wyłącznie „do dużego”, próg 2 pkt, domyślnie wyłączona, lista fraz w `data/router_l1.json` | A | obowiązuje; zastępuje wpisy 60–61 | 62, 63 |
| D13 | Warstwa 2: kNN k = 20, średnia ważona podobieństwem kosinusowym, domyślny próg 0,3; indeks train+cal w repozytorium (`data/router/router_index_train_cal.npz`) | As | obowiązuje | 49, 69 |
| D14 | Awaria klasyfikatora lub małego modelu (404/408/429/5xx) → duży model | A | obowiązuje | 49 |
| D14a | Wersja routera do testu końcowego: warstwy 1 + 2; warstwa 3 poza rdzeniem do decyzji go/no-go. Cele C1–C6: `CELE_PRZED_TESTEM.md` (**propozycja, niezatwierdzona**) | As | obowiązuje; C1–C6 czekają | 49 |

## Warstwa 3

| # | Decyzja | Kto | Status | Wpis |
|---|---|---|---|---|
| D15 | Warstwa 3 jest wołana **tylko w strefie niepewności kNN** (wynik 0,20–0,45), jakość jako ograniczenie przy doborze strefy. Eksperymenty na train (CV po grupach); zestaw pytań v1 zamrożony (SHA-256 w dzienniku); cal użyty raz dla `nimble` i `basal-2.0-4.5B`; **kolejne modele tylko na train** | A | obowiązuje | 67, 68, 86, 91, 98 |
| D16 | Warstwa 3 to model decyzyjny przez `POST /v1/systemone` (zamiast „małego modelu zero-shot z logprobs” z `KONCEPCJA.md`). Najpierw sam model, potem połączenie z kNN i heurystykami | A | obowiązuje jako kierunek eksperymentu (zmiana względem planu) | 79, 86 |
| D17 | Go/no-go warstwy 3 i wybór modelu | A | **propozycja** (ocena asystenta: opcjonalne rozszerzenie, nie rdzeń) | 103 |

## Odrzucone lub sprawdzone bez przyjęcia (żeby nie zaczynać od nowa)

| Pomysł | Wynik | Wpis |
|---|---|---|
| Plugin DF zamiast usługi | odłożone przez autora | 27 |
| Warstwa 1 z modelem logistycznym i wagą | usunięty z usługi (dodany bez zgody); skrypt zostaje jako zapis | 61, 62 |
| Reguły warstwy 1 „do małego” | odrzucone (skłonność do pogorszenia jakości) | 47–49 |
| Poszerzona lista słów dla warstwy 1; osobny model tf-idf | nic nie dodają do kNN | 45, 46, 49 |
| Dopasowanie rozmyte (fuzzy) fraz w warstwie 1 | pomysł na później | 73 |
| Najbliższy sąsiad (k = 1) | wyraźnie gorszy (APGR −0,059) | 53, 65 |
| Ostrzejsze ważenie kNN (podobieństwo^10, k = 40) | **propozycja czeka na autora**: APGR +0,009 [+0,003; +0,014], ale wybrane z 30 wariantów na tych samych danych; router bez zmian (k = 20) | 53, 65 |
| Inne embeddingi | patrz D11 | 30 |
| Usuwanie uciętych odpowiedzi z danych | odrzucone (wypadłyby trudne, długie pytania) | 109 |
| Limit 8192 dla uciętych | odrzucone (pętli nie naprawi, koszt godzin) | 109 |

## Jak dodać decyzję
Nowy wiersz w odpowiedniej tabeli (numer kolejny `D…`), wpis w `DZIENNIK.md`, a jeśli decyzja zastępuje starą, zmień status starej i podaj numer nowej. Plan (`KONCEPCJA.md`) zmienia tylko autor.
