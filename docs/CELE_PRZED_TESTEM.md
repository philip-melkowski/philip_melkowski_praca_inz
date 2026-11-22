# Cele liczbowe ustalone przed otwarciem zbioru test (propozycja)

Status: **propozycja asystenta (2026-10-19), do zatwierdzenia przez autora pracy i promotora.** Zgodnie z `koncepcja.md` cele powstają po pomiarze punktów odniesienia i przed otwarciem testu. Po otwarciu testu nie wolno ich zmieniać; wyniki raportujemy niezależnie od tego, czy cele spełnione.

Punkt wyjścia (walidacja krzyżowa po grupach na train+cal, 3010 pytań, próg Δ > 0,25; zob. `DZIENNIK.md`, wpis 24): kNN na embeddingach AUROC 0,682, APGR 0,605; „samo źródło” 0,631 / 0,582; „sama długość” 0,525 / 0,523; losowy 0,50 / 0,50; oracle APGR 0,89 (na samym cal, 859 pytań: 0,91).

| # | Cel (zbiór test, pytania w dziedzinie, tj. bez MMLU, MT-Bench i 150 pytań GSM8K poza dziedziną) | Uzasadnienie |
|---|---|---|
| C1 | APGR routera (kNN, k=20) wyższy niż „samo źródło” z dolną granicą 95% przedziału różnicy parowanej > 0 | w CV różnica +0,023 [+0,009; +0,038] |
| C2 | AUROC ≥ 0,64 (CV: 0,68; zapas na spadek na nowych danych) | |
| C3 | CPT80 ≤ 0,72 (CV na cal ok. 0,65; losowy 0,80) | |
| C4 | Odporność: zmiana decyzji ≤ 15% dla literówek, parafraz, synonimów przy 30% wysyłanych do dużego (cal: 6–9%) | wpis 23 |
| C5 | Opóźnienie L1+L2 przez DF: p50 < 50 ms (Ollama natywna; cal bez DF: p50 20,6 ms, p90 65,5 ms) | cel z planu |
| C6 | Ruch poza dziedziną (MMLU, MT-Bench, GSM8K-OOD) i błąd krytyczny (pytanie z Δ > 0,5 skierowane do małego przy 50% do dużego): **tylko raportowane, bez progu** | brak danych do wyznaczenia progu |

Uwagi: L1 (reguły) nie wykazała zysku ponad L2 i w rdzeniu zostaje tylko, jeśli ablacja końcowa to uzasadni; warstwa 3 (mały model zero-shot) ma osobny test go/no-go i tu nie ma celów.

---

## Aktualizacja 2026-11-22 (propozycja asystenta, niezatwierdzona; wpisy 117–118)

**Moc testów na zbiorze test** (766 pytań w dziedzinie; błąd standardowy z bootstrapu po grupach na train, 2151 pytań, przeskalowany przez √(2151/766); szacunek przybliżony, bo rozkład źródeł w teście jest inny):

| Porównanie (parowane, router kNN k=20) | Efekt w CV | Moc (α = 0,05, jednostronnie przez dolną granicę 95% CI) |
|---|---|---|
| APGR kNN − „samo źródło” (C1) | +0,023 (train+cal) do +0,029 (train) | ok. 37–54% |
| AUROC kNN − „samo źródło” | +0,070 | ok. 83% |
| APGR kNN − „sama długość” | +0,083 | ok. 99% |

**Propozycje zmian:**
1. **Hipoteza główna:** APGR routera − APGR „sama długość” > 0 (dolna granica 95% CI parowanego). C1 zostaje jako cel drugorzędny z podaną mocą; jego niespełnienie jest prawdopodobne nawet przy prawdziwym efekcie.
2. **Progi certyfikowane:** metoda Bonferroniego (`DECYZJE.md` D20), raportowane bez progu sukcesu (jak C6).
3. **Wersja routera do testu:** bez zmian (warstwy 1 + 2, D14a), z poprawką słów kluczowych (wpis 117). Do decyzji przed otwarciem testu: czy indeks zawiera też nowe pytania (`extra_train`, wpis 118: na starych źródłach bez zmian, na nowych lepiej).
4. **Warstwa 3:** jeśli go (D17), warianty i kryterium jakość–koszt wg D19 ustalić przed otwarciem; wyniki raportowane jako porównanie wariantów, bez progu sukcesu.
5. **Etykiety testu:** przed otwarciem dokończyć ocenę ponownych odpowiedzi z limitem 4096 (66 pytań testowych z uciętą odpowiedzią dużego, wpis 106); wymaga `answers.jsonl` z komputera prywatnego. Bez tego etykiety części testu pochodzą z uciętych odpowiedzi.
6. **C5 (opóźnienie):** dane do tej pory: narzut routera przez DF na Macu ok. 13 ms (wpis 70); na GPU embedding p50 36 ms przez tunel (wpis 118). Pomiar C5 zrobić na docelowym sprzęcie z routerem w DF.
