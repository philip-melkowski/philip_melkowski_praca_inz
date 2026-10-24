# Warstwa 3 (LLM jako sędzia trudności): propozycja i rozpoznanie modeli Jev

Stan na 2026-10-20. To **propozycja asystenta do decyzji autora**, nic z niej nie jest zaimplementowane ani zmierzone. Obowiązującym planem pozostaje `../../koncepcja.md` (warstwa 3 opcjonalna, po teście go/no-go) oraz decyzje z dziennika (wpisy 67–68: warstwa 3 tylko w strefie niepewności kNN). Co sprawdzono, a czego nie, opisuje sekcja 7.

## 1. Co warstwa 3 ma robić

Router widzi tylko tekst pytania. Warstwa 2 (kNN) ustawia pytania według podobieństwa do pytań o znanej trudności, ale nie wie, czy **mały model zna konkretny fakt** (TriviaQA: 81% trudnych pytań trafia do małego, HumanEval: 84%). Warstwa 3 ma dać drugi, niezależny sygnał dla pytań, w których kNN jest niepewny: model „sędzia” czyta pytanie i zwraca prawdopodobieństwo, że jest ono trudne (duży model będzie wyraźnie lepszy, Δ > 0,25).

## 2. Jak mogłaby działać

```
pytanie
  └─ warstwa 1 (heurystyki): ≥ 2 pkt → duży
  └─ warstwa 2 (kNN): wynik s
        s ≤ t_dół  → mały
        s ≥ t_góra → duży
        pomiędzy   → warstwa 3 (strefa niepewności)
              sędzia zwraca q = P(trudne)
              wynik końcowy z = f(s, q)   (regresja logistyczna lub izotoniczna, dopasowana walidacją krzyżową na train+cal)
              z ≥ τ → duży, w przeciwnym razie mały
              błąd, przekroczenie czasu lub niska pewność sędziego → duży (bezpieczna strona)
```

- Progi `t_dół`, `t_góra`, `τ` i budżet czasu sędziego byłyby opcjami administratora, jak dotychczasowy próg.
- Granice strefy dobiera się tak, by jakość nie spadła poniżej ustalonego poziomu (wpis 68). Poziomu jeszcze nie ustalono.
- Każda decyzja logowana: warstwa (`judge`), `s`, `q`, czas.

## 3. Wariant „sędzia czyta pytanie” a wariant „sędzia czyta odpowiedź”

- **Podstawowy (proponowany):** sędzia czyta tylko pytanie, przed odpowiedzią. Mieści się w obecnej architekturze (router decyduje przed generowaniem).
- **Alternatywny (zmienia architekturę, nie wchodzi do propozycji bez decyzji autora):** mały model odpowiada, sędzia ocenia odpowiedź („przyjmij czy eskaluj”), niepewne idą jeszcze raz do dużego. To wprost schemat z artykułu o JEV (sekcja 4). Mógłby wykryć brak wiedzy małego modelu, którego z samego pytania nie widać, ale kosztuje opóźnienie (dwa modele przy eskalacji) i utrudnia streaming (odpowiedź małego trzeba by buforować).

## 4. Jev: co to jest i czy pasuje

**Jev** (TypeSafe AI, wrzesień 2026) to „typed decision model”: nie generuje tekstu. Dostaje stan (tu: pytanie) i pytanie o ograniczonym zbiorze odpowiedzi (tak/nie, wybór z listy, skala porządkowa) i zwraca prawdopodobieństwa odpowiedzi w jednym przebiegu. Jev jest usługą w chmurze (zamknięty), 0,042 USD za milion tokenów wejściowych, mediana ok. 0,15 s (artykuł CMU) lub ok. 100 ms (wpis DeepEval). Powstały też otwarte odpowiedniki.

| Model | Licencja | Rozmiar i sprzęt (z kart modeli) | Uwagi |
|---|---|---|---|
| **basal-omni-1.0-mini** (Remek Kinas, polski autor) | Apache-2.0 | 8B, ok. 16 GB GPU, GGUF (llama.cpp, Ollama), vLLM, MLX | do 255 opcji, plik kalibracji `CALIBRATION.json`, 61 ms p50 (H100) |
| basal-omni-1.0-max | Apache-2.0 | 12B, ok. 24 GB GPU | dokładniejszy, cięższy |
| JEV-9B / JEV-27B (AutoTrust) | Apache-2.0 | 9B ok. 18 GB; 27B ok. 54 GB; vLLM | ok. 90–137 ms (B200) |
| openjev | **CC-BY-NC-4.0** | 27B, GGUF Q4 16,5 GB | tylko niekomercyjnie |
| Jev (TypeSafe) | zamknięty | tylko usługa w chmurze | zbyt „zewnętrzny” dla założenia on-premises |

**Czy pasuje: częściowo.**

Za:
- Typowane prawdopodobieństwa w jednym przebiegu (twórcy deklarują dobrą kalibrację, niesprawdzoną przeze mnie): dokładnie to, czego potrzebuje progowa decyzja. Omija problem, że czat DF nie przekazuje `logprobs` (wpis 27).
- Szybkie (kilkadziesiąt–kilkaset ms), więc możliwe w strefie niepewności.
- Artykuł CMU („JEV-as-a-Judge: Accept When Confident, Escalate When Unsure”, arXiv 2609.26550) opisuje dokładnie nasz mechanizm sterowania: pewność decyduje, czy przyjąć werdykt, czy przekazać dalej. Przy progu zamrożonym przed testem kaskada eskalowała 31% par i była o 0,9 pkt dokładniejsza od GPT-6 przy 41% jego kosztu. Próg wybrany dolną granicą przedziału ufności (zamiast estymaty punktowej) zmniejszył ryzyko utraty ponad 2 pkt z ok. 45% do ok. 5% przy ok. 100 lokalnych etykietach. To to samo podejście, które mamy w tabeli certyfikowanych progów (wpis 54).
- Są otwarte modele na licencji Apache-2.0, które da się uruchomić lokalnie.

Przeciw i ryzyka:
- Te modele są trenowane do oceny tego, co **da się odczytać z tekstu**. Według artykułu CMU Jev jest o 3 pkt od GPT-6, gdy werdykt wynika wprost z tekstu, a o 7–28 pkt gorszy na wiedzy eksperckiej, kodzie, matematyce i logice, czyli tam, gdzie werdykt trzeba wyprowadzić. Nasze pytanie („czy dużemu modelowi będzie lepiej niż małemu”) to przewidywanie zdolności innego modelu, a nie czytanie z tekstu. Dokładnie w wiedzy i kodzie router myli się najbardziej. **To jest hipoteza do sprawdzenia, nie oczekiwany wynik.**
- Artykuł UPenn („Jev vs. LLMs as Rubric Judges”) podaje, że sędziowie LLM powtarzają prawie wszystkie najpewniejsze błędy Jev (96,0%), więc kaskada zyskuje najwyżej 1,5 pkt. U nas tego sprawdzić się nie da bez własnego testu (liczby z ekstraktu strony, nie z całego tekstu).
- Wrażliwość na kolejność: w artykule CMU 95 z 1850 par (5,1%) zmieniło werdykt Jev po odwróceniu kolejności; karty otwartych odpowiedników podają 7% (JEV-27B, 16 opcji), 11,5% (JEV-9B) i 2,3% (openjev). Trzeba uśredniać po kilku kolejnościach albo je losować.
- Zasoby: basal-omni-mini wymaga ok. 16 GB pamięci GPU obok modelu 27B. Czy komputer służbowy to pomieści, nie wiadomo.
- Wszystkie podane wyniki to deklaracje twórców i badań z ostatnich tygodni; niczego nie odtwarzałem.

**Wniosek (propozycja):** Jev jest pasującą **formą** sędziego (typowany, probabilistyczny, szybki), ale nie ma dowodu, że zawiera informację o trudności dla naszej pary modeli. Wpisać go jako jeden z wariantów w test go/no-go obok tańszych, a nie zakładać z góry. Wariant z chmurowym Jev tylko jako górna poprzeczka odniesienia, nie jako część rozwiązania (zasada on-premises).

## 5. Warianty do testu go/no-go

Wszystkie liczone na tych samych pytaniach z train+cal (strefa niepewności), bez zbioru testowego.

| Wariant | Opis | Koszt |
|---|---|---|
| **A. Własny prompt na qwen3:8b** | prompt SIMPLE/COMPLEX, prawdopodobieństwo z `logprobs` przez `/v1/completions` (istniejące `eval/layer3_probe.py`) | bez nowych modeli |
| **B. Odczyt „jak Jev” na qwen3:8b** | ponumerowane opcje (np. 0–4), prawdopodobieństwa pierwszego tokenu; uśrednianie po kolejnościach | bez nowych modeli |
| **C. basal-omni-1.0-mini** | typowane pytanie z kryteriami (tak/nie: „czy mały model odpowie równie dobrze”, lub skala), kalibracja z naszych etykiet | pobranie 8B, ok. 16 GB GPU |
| D. Jev (chmura) jako poprzeczka | te same pytania, tylko do pomiaru górnej granicy | szacunkowo ułamki dolara przy ok. 1 mln tokenów; **wymaga zgody autora** |
| E. Sonda liniowa (plan B z koncepcji) | klasyfikator na reprezentacjach modelu, bez strojenia wag modelu | zależy od dostępu do reprezentacji |

Kolejność: A i B najpierw (taniej, na istniejących modelach), potem C, D tylko jeśli A–C dają sygnał.

## 6. Cele i kryteria go/no-go (propozycja, liczby do ustalenia)

Ocena wyłącznie walidacją krzyżową po grupach na train+cal; progi zamrożone przed otwarciem zbioru testowego (zasada z artykułu CMU i z `CELE_PRZED_TESTEM.md`).

| Cel | Miara | Proponowany próg |
|---|---|---|
| G1. Informacja ponad kNN | AUROC wyniku łączonego (s, q) na pytaniach ze strefy wobec samego kNN | wzrost z przedziałem ufności (bootstrap) powyżej zera, np. ≥ +0,03 |
| G2. Jakość przy tym samym koszcie | krzywa jakość a udział dużego (jak slajd 11): router ze strefą wobec samego kNN | co najmniej na poziomie kNN przy mniejszym udziale dużego (lub wyżej przy tym samym) |
| G3. Bezpieczeństwo | odsetek poważnych błędów (Δ > 0,5) wśród pytań wysłanych do małego | nie wyższy niż samego kNN; dolna granica Clopper–Pearsona jak w tabeli certyfikowanych progów |
| G4. Koszt strefy | odsetek pytań trafiających do warstwy 3 | do ustalenia (np. ≤ 50%, wpis 67) |
| G5. Opóźnienie | mediana czasu decyzji warstwy 3 i średni narzut (udział × czas) | do ustalenia (cel ogólny z planu: < 50 ms dla mediany całości; warstwa 3 będzie ten cel przekraczać, więc potrzebny osobny budżet) |
| G6. Kalibracja | ECE prawdopodobieństw sędziego po kalibracji | ≤ 0,05 |
| G7. Stabilność | zmiana werdyktu po zmianie kolejności opcji i po literówkach/parafrazach | ≤ 10% (parafrazy: jak dotąd ≤ 15%) |
| G8. Wdrażalność | licencja, pamięć obok modelu 27B, lokalnie | Apache-2.0 lub podobna; mieści się w GPU; błąd lub przekroczenie czasu → duży model |

**Go:** G1 spełnione oraz co najmniej jedno z G2, G3, a G4–G8 w granicach. **No-go:** przedział G1 obejmuje zero. Wynik negatywny też jest wynikiem do opisania w pracy (tak jak „heurystyki nie dodają nic do kNN”).

Zgodnie z planem trzeba pokazać ablację: warstwa 2, warstwa 1 + 2, warstwa 1 + 2 + 3 (strefa) oraz wariant porównawczy „warstwa 3 dla każdego pytania” (wpis 67).

## 7. Czego nie sprawdzono

- Pełnych tekstów: przeczytałem artykuł CMU 2609.26550 (strony 1–6 z PDF-a) oraz wpis DeepEval i fragmenty artykułu UPenn 2609.29769 (część liczb z ekstraktu strony). **Nieprzeczytane:** artykuł 2609.30216 („Jev in the Wild”, PDF nie dał tekstu), tekst Medium (błąd 403), leaderboard JevBench (zbyt duża strona), repozytorium silnika basal (rkinas/basal) i strony TypeSafe.
- Rozmiarów, licencji i sprzętu z kart modeli (HF, Featherless): z odczytu kart, część z podsumowania ucinanych stron. Liczby z benchmarków i kalibracji są deklaracjami autorów, nie odtworzone.
- Nikt nie sprawdził, czy modele Jev niosą informację o trudności dla pary qwen3:8b / Qwen3.8-27B. To jest właśnie test go/no-go.
- Brak informacji, ile pamięci GPU zostaje na komputerze służbowym obok modelu 27B.

## 8. Źródła

- [JEV-as-a-Judge: Accept When Confident, Escalate When Unsure (CMU, arXiv 2609.26550)](https://arxiv.org/pdf/2609.26550)
- [Jev vs. LLMs as Rubric Judges (UPenn, arXiv 2609.29769)](https://arxiv.org/html/2609.29769v1)
- [Introducing Jev for Evals (DeepEval)](https://deepeval.com/blog/introducing-jev-in-deepeval)
- [Jev vs LLM-as-a-Judge (OpenRouter)](https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/)
- [Jev as a judge (Langfuse)](https://langfuse.com/changelog/2026-09-22-jev-as-a-judge)
- [basal-omni-1.0-mini (Remek, Hugging Face)](https://huggingface.co/Remek/basal-omni-1.0-mini) i [karta na Featherless](https://featherless.ai/models/Remek/basal-omni-1.0-mini)
- [JEV-9B](https://huggingface.co/autotrust/JEV-9B), [JEV-27B](https://huggingface.co/autotrust/JEV-27B) (AutoTrust), [openjev](https://huggingface.co/openjev/openjev), [Jev-Omni](https://huggingface.co/akhilaaa3/Jev-Omni)
