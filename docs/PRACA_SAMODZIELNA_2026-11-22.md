# Praca samodzielna, 22.11.2026

Notatka z pracy bez nadzoru autora (prośba autora: „przerobić wszystkie kroki”). Uzupełniana po każdym etapie. Szczegóły i pełne liczby: `DZIENNIK.md`, wpisy 117–118. Na końcu lista spraw do decyzji autora.

## Stan na start
- Dostępy od autora: klucz Gemini (limit 20 USD), klucze DF na GPU (`~/.config/inz/df_gpu_key`, `df_gpu_admin_key`), tunele: DF na GPU `localhost:18088`, Ollama na GPU `localhost:21434` (df-5070ti-03, RTX 5070 Ti 16 GB).
- Zgody: commity, force push repozytorium pracy (wykonał autor), metoda progów: Bonferroni (D20).
- Bez zgody i nie robię: otwarcie zbioru test, decyzja go/no-go warstwy 3, wybór modelu, ponowne użycie cal.

## Zrobione

### 1. Poprawki ewaluacji (wpis 117)
- Bootstrap po grupach prawie-duplikatów (`group_bootstrap`). Na train przedziały prawie bez zmian (grupy niemal jednoelementowe).
- `pick()` w progach certyfikowanych: poprawne Learn-then-Test nie daje na train żadnego progu; przyjęta metoda Bonferroniego (D20) daje: błąd krytyczny ≤ 15% przy 65% do małego, COMPLEX ≤ 30% przy 40% do małego. **Tabela ryzyka ze slajdu 9 była liczona starym, błędnym `pick()`.**

### 2. Analizy na train (wpis 117)
- Szum etykiet: AUROC 0,687 na wszystkich, 0,749 na pytaniach z wyraźną różnicą (Δ > 0,4 wobec Δ ≤ 0). Część „sufitu” to pytania blisko progu.
- Spadek jakości wobec „zawsze duży”: 20% do małego −2,9%, 40% −7,1%, 50% −9,6% (losowo −5,4 / −10,8 / −13,5%).
- Niewykonane: zgodność 3 próbek małego (oceny próbek są na komputerze prywatnym).

### 3. DF (wpis 117)
- Słowa kluczowe reguł dopasowywane jako całe słowa („prove” ≠ „improve”), commit d654a30 w `feat/router-service` (niewypchnięty).
- Testy E (awaria embeddingów → duży) i G (restart DF → router wraca sam): zaliczone na żywo.
- Clef na df.test zmienił nazwę na `clef:27b` (inna wersja niż q4_K_M, liczby różnią się o 0,01–0,05; decyzje w przykładach pokazu bez zmian). Dodany plik `router_l3_clef27b_v1.json`, instrukcja pokazu zaktualizowana.

### 4. Ocena nowych pytań sędzią (wpis 118)
- 1500 pytań (Dolly, CodeChat, Arena 140k), odpowiedzi scalone z ponownymi (limit 4096): 363 ucięte zastąpione, nadal uciętych 80.
- Sędzia `gemini-3.8-flash` jak w pomiarze głównym: 1498 ocenionych, 2 zablokowane przez Gemini. Koszt ok. 4,5 USD (cennik z wcześniejszych wpisów, niezweryfikowany na rachunku).
- Zmienione odpowiedzi z pomiaru głównego (ponowne z 4096 dla starych pytań) **nieocenione**: wymagają `answers.jsonl` z komputera prywatnego.

### 5. Etykiety i podział nowych pytań (wpis 118)
- Embeddingi zgodne z pomiarem głównym (cos ≥ 0,99999). Żadne nowe pytanie nie jest prawie-duplikatem starego (test bezpieczny).
- Podział (propozycja): `extra_train` 1051, `extra_val` 449 (30% grup każdego źródła, świeży zbiór walidacyjny zamiast zużytego cal).
- COMPLEX: 49,9% (Arena 140k 56,7%, CodeChat 64,3%, Dolly 28,6%), wyraźnie więcej niż w pomiarze głównym (35,4%).
- Przenoszenie routera (tylko `extra_train`): kNN ze starym indeksem na nowych źródłach AUROC 0,616 (w obrębie źródła 0,54–0,59). Z nowymi pytaniami w indeksie (CV) 0,675 na nowych; na starych 0,687 → 0,691 (bez istotnej zmiany).

### 6. Czasy na GPU (wpis 118)
Ollama na df-5070ti-03 (RTX 5070 Ti), wołana przez tunel SSH (czasy zawierają sieć), 200 pytań z train:

| składnik | 1 naraz p50 / p90 | 4 naraz p50 | przepustowość |
|---|---|---|---|
| embedding `nomic-embed-text` | 36 / 69 ms | – | 22/s |
| d1:3b, 8 pytań (v1) | 110 / 148 ms | 308 ms | ok. 12,5/s |
| d1:3b, 34 pytania (pula v2) | 361 / 461 ms | 1204 ms | ok. 3,3/s |
| `qwen3:8b` generowanie | 2,2 s na ≤ 256 tokenów | – | 112 tok/s |

- d1 nie działa przez `/v1/systemone` w DF: katalog DF (`static/ollama-min.json`) zalicza `d1:3b` do zwykłych modeli językowych. Modele decyzyjne w katalogu: Clef, Clef-flash, nimble, nimble-v3, tev1. Do wdrożenia d1 trzeba go dopisać do katalogu (zmiana w DF) albo użyć modelu z listy. Pomiar zrobiony bezpośrednio na Ollamie (czas modelu nie zależy od DF).
- Rozmiaru Clefa 27B nie sprawdziłem (katalog DF go nie podaje), więc nie wiem, czy zmieści się na tej karcie.

### 7. Cele przed testem (wpis 118)
- Dopisana aktualizacja w `CELE_PRZED_TESTEM.md` (propozycja): moc C1 ok. 37–54%, hipoteza główna router − „sama długość” (moc ok. 99%), Bonferroni, przed otwarciem testu dokończyć etykiety 66 pytań testowych z ponownych odpowiedzi (komputer prywatny).

### 8. Szkice pracy (wpis 118)
- Nowe: `praca/03_implementacja_df.md` (architektura w DF, przebieg decyzji, awarie, testy, opóźnienie), `praca/04_warstwa3.md` (eksperyment z modelami decyzyjnymi, tabele wyników, koszt czasu, wdrożenie, wnioski).
- `praca/02_router.md`: dopisana sekcja 4a (szum etykiet, spadek jakości, progi Bonferroniego, nowe źródła) i poprawione zdanie o testach z prawdziwymi modelami.
- `praca/00_wstep_i_literatura.md`: wstęp (problem, cel, propozycja tezy, układ) i przegląd literatury tylko ze źródeł opisanych w repozytorium; pozycje czytane w abstrakcie oznaczone [SPRAWDZIĆ], FrugalGPT i źródła dla Learn-then-Test do dopisania.
- Do napisania: ewaluacja na teście (po otwarciu), ograniczenia, wnioski, deklaracja użycia narzędzi AI.

## W toku
- Nic; dalsze kroki wymagają decyzji autora (lista niżej).

## Do decyzji autora
1. Podział nowych pytań: czy `extra_val` (449) ma być świeżym zbiorem walidacyjnym zamiast cal.
2. Czy nowe pytania wchodzą do indeksu routera (poprawa na nowych źródłach, na starych bez zmian).
3. Warstwa 3: go/no-go i model (d1 3B na GPU: 0,11 s dla 8 pytań; Clef tylko na df.test). Jeśli d1: dopisać go do katalogu modeli decyzyjnych DF.
4. Moc C1 ok. 40–55%: czy miarą główną ma być różnica router − „sama długość” (moc ok. 99%).
5. Push gałęzi DF (`feat/router-service` z poprawką słów kluczowych): wymaga tokenu GitHuba.
6. Ponowna ocena zmienionych odpowiedzi pomiaru głównego: na komputerze prywatnym.
