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
