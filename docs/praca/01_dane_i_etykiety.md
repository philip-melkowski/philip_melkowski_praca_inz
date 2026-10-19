# Szkic: dane i pomiar etykiet (roboczy, do redakcji przez autora)

Status: szkic zbudowany z dziennika prac (`../DZIENNIK.md`, wpisy 3–17, 22, 29–31). Liczby aktualne na 2026-10-19. Miejsca oznaczone **[UZUPEŁNIĆ]** wymagają decyzji lub danych autora.

## 1. Cel pomiaru

Router wybiera dla każdego zapytania mały albo duży model. Aby go uczyć i oceniać, potrzebna jest odpowiedź na pytanie: *czy dla tego zapytania warto użyć dużego modelu?* Nie zakładamy, że odpowiedź wynika z rozmiaru lub tematu zapytania; mierzymy ją na parze modeli, która będzie używana w systemie. Para jest parametrem: w pomiarze duży model to Qwen3.8-27B-FP8 (vLLM), mały to qwen3:8b (Ollama).

## 2. Zbiór zapytań

Zbiór liczy 4313 zapytań w języku angielskim, jednoturowych, o długości od 16 do 1500 tokenów (tiktoken, cl100k_base):

| Źródło | Zapytań | Rodzaj oceny |
|---|---|---|
| Chatbot Arena | 1726 | sędzia (otwarte) |
| WildChat | 999 | sędzia (otwarte) |
| Zapytania wygenerowane przez Gemini | 450 | sędzia (otwarte) |
| MT-Bench | 78 | sędzia (otwarte) |
| GSM8K | 300 | automatyczna (liczba) |
| MMLU | 300 | automatyczna (litera) |
| TriviaQA | 296 | automatyczna (dopasowanie odpowiedzi) |
| HumanEval | 164 | automatyczna (testy kodu) |

Z WildChat odfiltrowano zapytania oznaczone jako toksyczne lub zredagowane, z flagą moderacji OpenAI, z wynikami detoxify > 0,1 oraz zapytania o wspólnym początku (80 znaków), ponieważ pierwsza próbka była zdominowana przez szablony. Jedno zapytanie przekraczało okno modelu embeddingowego (2048 tokenów) i zostało usunięte z bazy. Licencje: WildChat ODC-By, GSM8K i MMLU i HumanEval MIT, MT-Bench Apache 2.0; TriviaQA nie ma licencji w metadanych zbioru **[UZUPEŁNIĆ: opis w ograniczeniach]**.

### Podział

Zbiór dzielimy na train (2151), cal (859) i test (1294). Zapytania o podobieństwie embeddingów ≥ 0,95 (prawie-duplikaty) tworzą grupy trafiające zawsze do jednego zbioru, więc żadne takie zapytanie nie „przecieka” między uczeniem a testem. MMLU, MT-Bench i 150 zapytań GSM8K trafiają wyłącznie do testu (ocena poza dziedziną). Zbiór test jest zamknięty: odpowiedzi dla niego wygenerowano i oceniono, ale nie służył on do wyboru metody, hiperparametrów ani progów.

## 3. Protokół generowania odpowiedzi

Każde zapytanie wysłano do obu modeli: mały odpowiada trzykrotnie, duży raz, z temperaturą 0,7, limitem 2048 tokenów i wyłączonym trybem „myślenia” (`reasoning_effort: none`; wcześniejszy zapis `chat_template_kwargs` był po cichu odrzucany przez DeepFellow). Zapytania ze znaną odpowiedzią dostały jednakowy dopisek formatu dla obu modeli (GSM8K: „Answer: <number>”, TriviaQA: krótka fraza, HumanEval: pełna funkcja w bloku kodu). Wygenerowano 17252 odpowiedzi; brak pustych odpowiedzi i śladów myślenia. Ucięte przy limicie: duży 6,7%, mały 1,7% (głównie zapytania otwarte); dla zapytań otwartych oszacowaliśmy, że zmienia to odsetek zapytań COMPLEX najwyżej o ok. 2 punkty procentowe.

## 4. Ocena jakości odpowiedzi

- **Zapytania ze znaną odpowiedzią (1060)**: ocena automatyczna 0/1. GSM8K: liczba po ostatnim „Answer:”; MMLU: wskazana litera (trzy reguły, od najbardziej do najmniej rygorystycznej); TriviaQA: dowolny dopuszczalny alias jako cały wyraz w znormalizowanej odpowiedzi; HumanEval: wykonanie ostatniego bloku kodu z testami zbioru w osobnym procesie z limitem 10 s. Odpowiedź bez rozpoznanej odpowiedzi liczymy jako błędną.
- **Zapytania otwarte (3244)**: sędzia Gemini 3.8 Flash ocenia wszystkie cztery odpowiedzi do jednego zapytania naraz w skali 1–5, w losowej kolejności i bez nazw modeli; oceny normalizujemy do (ocena−1)/4. Ucięte odpowiedzi oznaczamy w poleceniu dla sędziego. 9 zapytań sędzia zablokował jako niedozwolone; pominięto je. Ocena wszystkich zapytań kosztowała ok. 8 USD.

Kontrole sędziego: obciążenie długością (korelacja różnicy Δ z różnicą długości odpowiedzi 0,06); zgodność z drugim sędzią (Gemini Pro) na 100 zapytaniach **[UZUPEŁNIĆ po zakończeniu: wstępnie na 42 zapytaniach zgodność klasy COMPLEX 76%, korelacja ocen Spearmana 0,80]**; zgodność z oceną człowieka na 100 odpowiedziach **[UZUPEŁNIĆ: ocena do wykonania, `kontrola_ludzka/zadanie.md`]**.

## 5. Etykieta

Dla każdego zapytania: Δ = Q_duży − średnia(Q_mały), gdzie Q jest jakością w skali 0–1. Zapytanie jest COMPLEX, gdy Δ > 0,25 (dla ocen sędziego to różnica co najmniej jednego punktu w skali 1–5), w przeciwnym razie SIMPLE. Próg jest wartością startową; wrażliwość badamy dla 0,15 i 0,35. Flaga „oba zawiodły” (Q_duży < 0,5 i średnia małego < 0,5) oznacza zapytania, na które żaden model nie umie odpowiedzieć: etykieta pozostaje SIMPLE, a zapytania zostają w danych (338 zapytań).

## 6. Wyniki pomiaru

- Poprawność dla zapytań ze znaną odpowiedzią (duży / mały): GSM8K 97% / 97%, HumanEval 94% / 83%, MMLU 81% / 66%, TriviaQA 60% / 47%.
- Odsetek COMPLEX: razem 35,4% (4304 zapytania z etykietą); WildChat 48%, Arena 45%, MT-Bench 32%, MMLU 28%, TriviaQA 20%, HumanEval 18%, zapytania od Gemini 16%, GSM8K 4%. Przy progach 0,15 i 0,35: 51,5% i 27,6%.
- Powtarzalność: dla zapytań otwartych etykieta wyznaczona z jednej próbki małego modelu jest identyczna we wszystkich trzech próbkach w 74% zapytań (ze znaną odpowiedzią: 92%).
- Porównanie z głosowaniami ludzi w Arenie (inne modele, inna epoka): zmierzone Δ słabo przewiduje wygraną silniejszego modelu (AUROC 0,55), co potwierdza, że etykiet nie należy przenosić między parami modeli.

## 7. Ograniczenia

Jedna para modeli i jeden zbiór; duży model ma jedną próbkę na zapytanie; oceny otwartych zależą od jednego sędzia; ucięte odpowiedzi; TriviaQA bez licencji w metadanych; pomiar obejmuje tylko zapytania jednoturowe w języku angielskim.
