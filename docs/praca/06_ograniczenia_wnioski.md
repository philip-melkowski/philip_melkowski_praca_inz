# Szkic: ograniczenia i wnioski (roboczy, do redakcji przez autora)

Status: szkic asystenta z 2026-11-22, zbudowany z dziennika (wpisy 14, 106–109, 117–127) i dokumentów wyników. Ocena końcowa i ton należą do autora.

## 1. Ograniczenia

**Dane i etykiety**
- Jedna para modeli z jednej rodziny (`qwen3:8b`, `Qwen3.8-27B`) i jeden sędzia (Gemini 3.8 Flash). Zgodność sędziego z człowiekiem jest umiarkowana **[UZUPEŁNIĆ: wartości 0,361 przed poprawkami i 0,592 po, wg PRZEMYSLENIA pkt 7]**.
- Duży model ma jedną próbkę na zapytanie, mały trzy; etykieta jest więc zaszumiona, szczególnie blisko progu Δ = 0,25. Na pytaniach z wyraźną różnicą jakości AUROC kNN rośnie z 0,69 do 0,75.
- Limit długości odpowiedzi 4096 tokenów: część odpowiedzi nadal ucięta (pomiar główny 92, nowe dane 80) i oceniona tak, jak jest (D: wpis 109).
- Dane w dużej części z publicznych czatów; nowe źródła (Dolly, CodeChat, Arena 140k) router bez dołożenia ich do indeksu rozpoznaje słabo (AUROC 0,62). Zapytań z rzeczywistego użycia w firmie brak.
- Część odpowiedzi małego modelu dla nowych pytań wygenerowano na innym sprzęcie (CUDA zamiast Metal, te same wagi).

**Metoda**
- Routing przed odpowiedzią widzi tylko tekst zapytania. Nie wie, co zna mały model: wiedza faktograficzna (TriviaQA 0,41) i kod (HumanEval 0,53) pozostają słabo rozpoznawane.
- Router w dużej mierze rozpoznaje rodzaj zapytania; na teście nie wykazano przewagi nad „samym źródłem”.
- Zbiór cal był używany kilkakrotnie (wybór i porównanie modeli warstwy 3), więc liczby z cal są lekko optymistyczne; dlatego do ostatniego sprawdzenia użyto świeżego `extra_val`, a ocenę końcową zrobiono na nietkniętym teście.
- Warstwa 3: zysk na teście (+0,022 APGR) większy niż w walidacji (+0,004 do +0,008); możliwy wpływ zmienności próby. Wyniki z Clefem dotyczą wersji `clef:27b-q4_K_M`, której nazwa na serwerze się zmieniła.

**Wdrożenie**
- Opóźnienie spełnia cel, gdy model embeddingów działa przy DF (p50 12,5 ms); przez sieć do zdalnego GPU 61 ms.
- Na karcie 16 GB mieszczą się trzy modele naraz w Ollamie; przy czterech warstwa 3 przekraczała limit czasu (router przechodził wtedy bezpiecznie na duży model).
- `d1:3b` wymagał ręcznego dopisania do katalogu modeli decyzyjnych DF; ponowne wygenerowanie katalogu cofnie tę zmianę.
- Indeks to plik ładowany przy instalacji; nowe etykiety wymagają ponownej instalacji usługi.
- Brak pomiaru oszczędności zasobów w rzeczywistym ruchu **[UZUPEŁNIĆ, jeśli będzie]**.

## 2. Wnioski (propozycja asystenta)

1. **Etykiety trzeba mierzyć dla konkretnej pary modeli.** Etykiety z głosowań Chatbot Arena prawie nie przewidują przewagi naszego dużego modelu (AUROC 0,55).
2. **Prosty router działa i spełnia cele.** kNN na embeddingach z heurystykami osiąga na teście AUROC 0,674 i APGR 0,600, istotnie lepiej niż reguła długości; progi z gwarancją pozwalają wybrać udział ruchu do małego modelu przy kontrolowanym ryzyku.
3. **Granica routingu z samego tekstu jest bliska.** Różne klasyfikatory i embeddery dają ok. 0,68–0,71 AUROC; część tej granicy to szum etykiet blisko progu, część brak informacji o wiedzy małego modelu. Ocena gotowej odpowiedzi małego modelu daje dużo więcej (AUROC 0,81 na train), ale to już kaskada, z kosztem wygenerowania odpowiedzi.
4. **Model decyzyjny jest wartościowym dodatkiem.** Na teście warstwa 3 z małym modelem d1 (3B) poprawia router istotnie (APGR +0,022, mniej poważnych błędów) kosztem ok. 0,13–0,19 s dla ok. 43% zapytań. Jedno pytanie do modelu decyzyjnego bez etykiet daje ranking porównywalny z kNN uczonym na 1000–1500 etykietach: to droga do routera dla nowej pary modeli bez kosztownego pomiaru.
5. **Router da się wdrożyć jako zwykła usługa infrastruktury** z bezpiecznym zachowaniem przy awariach (embeddingi, model decyzyjny, mały model) i narzutem kilkunastu milisekund.

## 3. Dalsze prace
- Sygnały z wnętrza małego modelu (sondy na stanach ukrytych) jako sposób przekroczenia granicy tekstu.
- Popularność encji (np. odsłony Wikipedii) dla pytań o fakty.
- Kaskada z oceną odpowiedzi małego modelu tam, gdzie opóźnienie na to pozwala.
- Router dla nowej pary modeli bez etykiet (sam model decyzyjny) i stopniowe dokładanie etykiet z ruchu.
- Pomiar oszczędności w rzeczywistym ruchu firmowym.
