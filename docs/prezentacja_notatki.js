module.exports = [
// 1
`MÓW
• Temat: routing zapytań do modeli językowych według ich trudności.
• Mam dwa modele: mały (qwen3:8b) i duży (Qwen3.8-27B). Duży odpowiada lepiej, ale kosztuje więcej czasu i mocy.
• System czyta pytanie i zanim ktokolwiek odpowie, wybiera model. Działa jako nowa usługa w DeepFellow Infra.
• Plan: problem i zmiana podejścia, jak mierzę trudność, jak działa router, wyniki, ograniczenia i prośba o decyzję.

WARTO WIEDZIEĆ
• 8 i 27 to miliardy parametrów, czyli rozmiar modelu.
• „Pytanie trudne” = duży model odpowiada na nie wyraźnie lepiej niż mały. „Łatwe” = mały wystarcza.
• Czas: ok. 20–25 minut.`,

// 2
`MÓW
• Duży model: lepsze odpowiedzi, ale wolniejszy i wymaga mocniejszego sprzętu. Mały: szybki, ale słabszy przy trudnych pytaniach.
• Dziś administrator ma dwa wyjścia: wszystko do dużego (drogo) albo wszystko do małego (gorsza jakość tam, gdzie była potrzebna).
• Router wybiera osobno dla każdego pytania: proste do małego (qwen3:8b), trudne do dużego (Qwen 27B). Na rysunku pytanie wchodzi do routera i idzie w jedną z dwóch stron. Dla użytkownika to po prostu model o nazwie router.
• Trudność: router decyduje, zanim model odpowie, więc widzi tylko tekst pytania. Praca sprawdza, ile o trudności da się wywnioskować z samego tekstu.
• Cel: jak najwięcej pytań do małego modelu przy prawie niezmienionej jakości.

JEŚLI ZAPYTAJĄ
• Dlaczego nie zawsze duży? To najdroższe rozwiązanie. Pokażę, ile da się zaoszczędzić i jakim kosztem.`,

// 3
`MÓW
• Etykiety (pytanie łatwe lub trudne) brałem z gotowych danych: z głosowań w Chatbot Arena (ludzie wybierają lepszą z dwóch odpowiedzi) i z pytań wygenerowanych przez Gemini.
• Trzy warstwy (heurystyki, porównanie z podobnymi pytaniami, mały model) zostają, opisuję je na slajdzie 8. Z rdzenia wypadły: konfiguracja w YAML, kategorie tematyczne i podział złożonych zadań na części (Map-Reduce).
• Odpowiedzi miałem oceniać m.in. miarą ROUGE.
• Plan był rozsądny, bo RouteLLM uczy się na głosach z Areny. Miał jednak jeden słaby punkt, pokazany na następnym slajdzie.

DEFINICJE
ROUGE: liczy, ile słów wspólnych ma odpowiedź modelu z odpowiedzią wzorcową.
• Zrezygnowałem z niej, bo zbieżność słów nie mówi o poprawności: dobra odpowiedź może być napisana innymi słowami, a zła może mieć wiele wspólnych.`,

// 4
`MÓW
• Zmieniłem podejście: zamiast cudzych etykiet mierzę trudność sam, na swoich modelach. Dla każdego pytania liczę, o ile duży model odpowiedział lepiej niż mały. Tę przewagę oznaczam Δ (delta). Jak ją liczę, pokażę na następnym slajdzie.
• Najpierw sprawdziłem, czy stare etykiety z Areny pasują do tej zmierzonej przewagi.
• Stara etykieta: pytanie jest „trudne”, jeśli w głosowaniu wygrał mocniejszy model.
• Porównanie dla 1723 pytań: AUROC = 0,55, czyli prawie rzut monetą (0,5).
• Dlaczego: Arena porównywała inne modele z innej epoki. Gdy gpt-4 wygrywa ze słabym modelem, to bez względu na pytanie. Stara etykieta mówi więcej o różnicy między modelami niż o trudności pytania.
• Wniosek: trudność zależy od konkretnej pary modeli, więc mierzę ją sam.

DEFINICJE
AUROC: miara zgodności rankingu z prawdą, od 0 do 1.
• Biorę losową parę pytań: jedno trudne, jedno łatwe.
• Para = 1, gdy trudne dostało wyższy wynik niż łatwe. 0, gdy niższy. 0,5 przy dokładnie równym wyniku (remis). Żaden próg nie jest potrzebny.
• AUROC to średnia z takich wyników po wszystkich parach, czyli odsetek par ułożonych dobrze.
• 0,5 = losowo (50 par na 100 ułożonych dobrze), 1,0 = idealnie (100 na 100). Nasze 0,55 to 55 na 100.
• Tu „wynik” to zmierzona przewaga dużego modelu (Δ), a „trudne” to stare trudne wg Areny. Później w ten sam sposób ocenię router.

UWAGA
• To analiza, a nie dowód, że moje etykiety są lepsze. Pokazuje tylko, że stare nie pasują do tych modeli.

JEŚLI ZAPYTAJĄ
• Czy 0,55 to przypadek? Pytań było 1723, a wynik jest blisko 0,5, więc wniosek jest ostrożny: stara etykieta słabo przewiduje wyniki naszych modeli.
• Ile jest remisów? Ok. 10% par (9,7%).
• Dlaczego nie zwykły odsetek zgodności? Stara etykieta ma dwie wartości, a moja miara jest liczbą. Porównanie par nie wymaga wybierania progu.`,

// 5
`MÓW
• Mam 4313 pytań z ośmiu źródeł. Każde przechodzi cztery kroki.
• Krok 1: wysyłam pytanie do obu modeli, do małego 3 razy, do dużego raz. Odpowiedzi są losowe, więc jedna próbka małego byłaby za mało pewna.
• Krok 2: ocena. Gdy znana jest poprawna odpowiedź (np. wynik zadania), sprawdza automat. W pozostałych przypadkach ocenia Gemini w skali 1–5, dostając pytanie i odpowiedzi w losowej kolejności i bez nazw modeli.
• Krok 3: liczę różnicę Δ = ocena dużego minus średnia ocena małego.
• Krok 4: Δ > 0,25 (czyli ponad 1 punkt w skali 1–5) = TRUDNE (COMPLEX). W przeciwnym razie ŁATWE (SIMPLE).
• Gdy oba modele odpowiedziały źle, pytanie zostaje łatwe, bo duży nic by nie dał.

DEFINICJE
Δ (delta): przewaga dużego modelu = ocena dużego minus średnia ocena małego, w skali 0–1 (oceny przeliczone wzorem (ocena − 1) / 4).
PRÓG TRUDNOŚCI: Δ > 0,25, czyli 1 punkt w skali 1–5. Nie mylić z progiem routera, o którym będzie dalej.

PRZYKŁAD Z RYSUNKU
• Duży dostał 5 (1,00), mały 3, 3 i 4 (średnio 0,58). Δ = 0,42, więc pytanie jest trudne.

JEŚLI ZAPYTAJĄ
• Dlaczego 3 próbki małego? Jedna próbka dałaby tę samą klasę co trzy tylko w 74% pytań otwartych. Średnia z trzech zmniejsza szum.
• Skąd próg 1 punkt? To mój wybór. Sprawdziłem też łagodniejszy i ostrzejszy (odsetek trudnych: 51,5%, 35,4% i 27,6%). Wnioski o routerze są te same.`,

// 6
`MÓW
• 4313 pytań z ośmiu źródeł i 17 252 odpowiedzi obu modeli.
• Źródła: prawdziwe rozmowy (Arena, WildChat), pytania wygenerowane przez Gemini, zbiory z matematyki, wiedzy i programowania. Są pytania otwarte i takie ze znaną poprawną odpowiedzią.
• Podział: 50% do nauki routera, 20% do dostrajania, 30% do testu końcowego. Test jest zamknięty: otworzę go raz, na końcu.
• Bardzo podobne pytania trafiają zawsze do jednej części. Inaczej router „znałby” pytania z testu, a wynik byłby zawyżony.
• Wynik pomiaru: 35,4% pytań jest trudnych (liczone dla 4304 pytań z etykietą; 9 z 4313 zablokował sędzia z powodu treści, więc są poza analizą), ale zależnie od źródła: matematyka 4%, WildChat 48%. Mały model dobrze liczy, a rozmowy otwarte są dla niego trudniejsze.

JEŚLI ZAPYTAJĄ
• Skąd te źródła? Chciałem mieszankę prawdziwych, niejednoznacznych rozmów i zadań, w których poprawność da się sprawdzić automatem.
• Ograniczenie: to głównie publiczne czaty, brakuje zapytań z typowego użycia w firmie. Wracam do tego na końcu.`,

// 7
`MÓW
• Etykiety ocenia model, więc sprawdziłem, ile można im ufać.
• 90%: po zmianie kolejności odpowiedzi ten sam sędzia daje tę samą klasę (trudne lub łatwe) w 90% pytań.
• 79%: drugi, mocniejszy sędzia (Gemini Pro) zgadza się z pierwszym co do klasy w 79% pytań.
• Sam oceniłem 100 odpowiedzi, nie wiedząc, który model je napisał. Korelacja z sędzią 0,59 (1 = identyczne uporządkowanie ocen, 0 = brak związku). Identyczna ocena w 43% przypadków, różnica nie większa niż 1 punkt w 77%.
• Sędzia jest surowszy ode mnie o 0,4 punktu (średnio 3,00 wobec 3,40).
• Wniosek: etykiety są użyteczne, ale nie idealne. Stała surowość sędziego się znosi, bo etykieta to różnica ocen dwóch modeli.

JEŚLI ZAPYTAJĄ
• Czy sędzia faworyzuje długie odpowiedzi? Korelacja z długością to 0,06, czyli prawie żadna.
• Który sędzia jest lepszy? Nie rozstrzygam. Używam tańszego, drugi dostał tylko część pytań.`,

// 8
`MÓW
• Router ma trzy warstwy, od najtańszej do najdroższej. Warstwa zostaje tylko wtedy, gdy pokaże zysk.
• Warstwa 1, heurystyki: punkty za cechy tekstu. +1 za frazę z listy zadań trudnych, −1 za frazę z listy łatwych, +1 za długość powyżej 400 znaków, +1 powyżej 1500, −1 gdy ponad 10% znaków to cyfry, +1 za adres internetowy. Administrator może zmienić punkty.
• Frazy pochodzą z literatury, nie z moich danych, żeby ich nie dopasować do wyników. Taksonomia Blooma (Anderson i Krathwohl, 2001): „analyze”, „compare”, „design” to zadania trudniejsze, „what is”, „define” łatwiejsze. Lista z AgentBus, praktycznego systemu routingu: np. „debug”, „refactor”, „step by step”.
• Suma punktów od progu (domyślnie 2) = pytanie idzie od razu do dużego, bez dalszych warstw. Tylko w tę stronę, bo pomyłka w stronę dużego kosztuje pieniądze, a nie jakość. Warstwa jest opcjonalna: bez pliku z parametrami jest wyłączona.
• U nas próg 2 obejmuje 6% pytań, z których 52% jest naprawdę trudnych (wśród wszystkich 37%). Lepsze od zgadywania, ale obejmuje niewiele ruchu.
• Warstwa 2: porównanie z podobnymi pytaniami (kNN) na embeddingach. Główna część rozwiązania, następny slajd.
• Warstwa 3: mały model sam ocenia, czy pytanie jest trudne. Jeszcze jej nie ma. Wejdzie, jeśli test go/no-go pokaże zysk: jeśli pomaga, budujemy, jeśli nie, rezygnujemy. Wywołanie małego modelu trwa sekundy, więc tylko dla pytań, przy których warstwa 2 jest niepewna.
• Na końcu router zwraca wynik od 0 do 1: im wyższy, tym bardziej pytanie wygląda na trudne. Administrator ustawia próg: powyżej idzie do dużego, poniżej do małego. Gdy cokolwiek zawiedzie, idzie do dużego, bo to bezpieczniejsze.

DEFINICJE
STREFA NIEPEWNOŚCI: wynik warstwy 2 w środku skali, między dwoma progami. Np. poniżej 0,2 do małego, powyżej 0,45 do dużego, pomiędzy decyduje warstwa 3. W naszych danych to ok. połowa pytań.
• Granice dobiorę na danych do dostrajania tak, by jakość nie spadła poniżej ustalonego poziomu. Tego poziomu jeszcze nie ustaliłem.

JEŚLI ZAPYTAJĄ
• Ile to trwa? Heurystyki ok. 0,3 ms, warstwa 2 ok. 20 ms. Warstwa 3 to sekundy, dlatego jest ostatnia i tylko w strefie niepewności.`,

// 9
`MÓW
• Router dostaje tekst pytania, a zwraca liczbę od 0 do 1. Cztery kroki:
• Krok 1: zamieniam pytanie na 768 liczb (embedding). Pytania o podobnym znaczeniu dostają podobne liczby, jak punkty blisko siebie na mapie.
• Krok 2: szukam 20 najbardziej podobnych pytań w bazie, czyli takich, których trudność już zmierzyłem.
• Krok 3: wynik to odsetek trudnych wśród tych 20, przy czym podobniejsze liczą się bardziej. Np. 14 z 20 trudnych = wynik wysoki = duży model.
• Krok 4: porównuję wynik z progiem administratora.

DEFINICJE
EMBEDDING: lista liczb (tu 768) opisująca znaczenie tekstu. Sama nie mówi, czy pytanie jest trudne.
kNN: metoda, która z embeddingu robi wynik: ważony odsetek trudnych wśród k = 20 najbardziej podobnych pytań z bazy.

DLACZEGO TAK
• Bez trenowania: baza to zapisane pytania, nowe dane to dopisanie wierszy.
• Wynik ma zrozumiałe znaczenie i można pokazać sąsiadów.
• Liczy się lokalnie w ok. 20 ms, pytania nie opuszczają serwera.
• Wzorem jest „Similarity-Weighted Ranking” z RouteLLM (Ong i in., 2024): embedding, podobieństwo do 80 tys. pytań z Areny, ważona suma głosów, bez trenowania. Inne metody z artykułu wymagają trenowania lub fine-tuningu.
• Różnice: moje etykiety są zmierzone na własnych modelach, biorę 20 najbliższych, nie całą historię. Baza ma ok. 3 tys. wektorów i ok. 1 ms (oryginał ok. 39 USD za milion zapytań).

CO SPRAWDZIŁEM
• Walidacja krzyżowa: uczę na jednych częściach danych, oceniam na pozostałych. Miara AUROC jak na slajdzie 4.
• 4 modele embeddingów: AUROC 0,679–0,709. Najlepszy (qwen3) jest 3× wolniejszy (52 ms wobec 17,6 ms), więc zostaje nomic.
• 9 klasyfikatorów (regresja logistyczna, SVM, sieć MLP, boosting i inne): 0,662–0,691, żaden istotnie lepszy od kNN. Sufit informacji w embeddingach to ok. 0,68–0,69.

JEŚLI ZAPYTAJĄ
• Dlaczego 20 sąsiadów? Przy 1: AUROC 0,590 (szum). Od ok. 20 stabilnie: 0,682 przy 20, 0,689 przy 40.
• Czy ważenie pomaga? Trochę: równe wagi 0,677, ważenie podobieństwem 0,682. Ostrzejsze do 0,702, ale wybrane z 30 wariantów na tych samych danych, więc nie przyjmuję bez potwierdzenia.
• Czy więcej danych pomoże? Niewiele: powyżej ok. 1200 pytań podwojenie bazy daje ok. +0,01.
• Ograniczenie: model liczący wektory czyta do 2048 tokenów, dłuższe pytania liczy z samego początku.`,

// 10
`DEFINICJE
AUROC (ze slajdu 4): odsetek par (trudne, łatwe), w których router dał trudnemu wyższy wynik. Remis = 0,5. 0,5 to losowo, 1,0 to bezbłędny router. Nie zależy od progu.
• Wynik routera to liczba 0–1 ze slajdu 9: im wyższa, tym bardziej pytanie wygląda na trudne.
• Przykład pary: trudne dostało 0,70, łatwe 0,40, więc para = 1. U nas ok. 1130 trudnych i 1880 łatwych pytań, czyli ponad 2 miliony par.
JAKOŚĆ: średnia ocena odpowiedzi w skali 0–1 (dla każdego pytania ocena modelu, do którego poszło). Wszystko do małego 0,625, wszystko do dużego 0,846. Luka 0,221.
APGR (średni odzyskany zysk): dla jednego progu odzyskany zysk = (jakość routera − 0,625) / 0,221. Np. jakość 0,777 daje 0,152 / 0,221 = 0,69.
• APGR to średnia z tego po wszystkich progach, czyli jedna liczba opisująca cały router. Wykres na następnym slajdzie.
• Losowe wysyłanie daje APGR 0,5, idealny router 0,89 (dla 3010 pytań). Mój ma 0,605.

MÓW
• Mój router ma AUROC 0,682, czyli w 68 parach na 100 ustawia pytania dobrze.
• Słupki na wykresie to AUROC: losowy 0,5, sama długość pytania 0,525 (prawie nic nie mówi), „samo źródło” 0,631, router 0,682.
• „Samo źródło”: router, który nie czyta pytania, tylko wie, z jakiego zbioru pochodzi, i daje wynik równy odsetkowi trudnych w tym zbiorze (matematyka 4%, WildChat 48%). W praktyce źródła nie znamy, to tylko poprzeczka.
• Router wie coś więcej niż rodzaj pytania, ale niewiele: różnica 0,05 w AUROC i 0,023 w APGR (0,605 wobec 0,582), istotna statystycznie.

UWAGA
• Liczby dotyczą warstwy 2 (kNN), bo tylko ona daje wynik 0–1 dla każdego pytania. Warstwa 1 osobno ok. 0,55, w kaskadzie z kNN jakość się nie zmienia. Warstwy 3 jeszcze nie ma. Cały router ocenię na zbiorze testowym.
• Uczciwie: dużą część skuteczności daje samo rozpoznanie rodzaju pytania. Wewnątrz jednego źródła jest słabiej: Arena 0,60, TriviaQA ok. 0,50.

JEŚLI ZAPYTAJĄ
• Czy da się lepiej? Z samego tekstu raczej nie, różne metody dają podobny wynik. Potrzebny byłby inny sygnał, np. warstwa 3.`,

// 11
`MÓW
• Ten slajd pokazuje dwie różne rzeczy: po lewej wykres (obraz APGR), po prawej tabelę (ryzyko poważnych błędów).

WYKRES (LEWA STRONA)
• Oś pozioma: odsetek pytań wysyłanych do dużego modelu (0–100%). Oś pionowa: jakość, czyli średnia ocena odpowiedzi (0–1).
• Wszystko do małego daje 0,625, wszystko do dużego 0,846. Szara linia to wysyłanie losowe. Pomarańczowa to router: wyżej = lepsza jakość przy tym samym udziale dużego.
• Punkty tej linii to te, z których APGR jest średnią. APGR (0,605 wobec 0,5 losowo) mierzy odstęp między liniami.
• Przykład, próg 0,3: do dużego idzie 54% pytań, jakość 0,777. Odzyskuję 0,69 luki między 0,625 a 0,846 (losowo byłoby 0,54).
• To ok. 46% mniej wywołań dużego modelu za ok. 8% niższą jakość (0,846 spada do 0,777). Uwaga: to odczyt z jednego punktu, nie APGR.

DEFINICJE
POWAŻNY BŁĄD: pytanie, na które duży model odpowiedziałby wyraźnie lepiej (o ponad 2 punkty w skali 1–5, czyli Δ > 0,5), a które poszło do małego. Takich pytań jest 15,9%.

TABELA (PRAWA STRONA)
• To inna miara niż APGR. Jeśli akceptuję do 12% poważnych błędów wśród pytań wysłanych do małego, do małego idzie 47% pytań.
• Przy 10% idzie 22% pytań, przy 15% aż 90%. Poniżej ok. 8% żaden próg nie daje gwarancji z 95% pewnością.

JAK SIĘ MAJĄ DO SIEBIE
• To ten sam router i te same progi, oglądane z dwóch stron. Wykres: ile średnio stracę na jakości. Tabela: jak często popełnię poważny błąd.
• Np. próg 0,3: z wykresu 54% do dużego i jakość 0,777. Z tabeli: do małego idzie ok. 47% pytań, wśród nich ok. 11% to poważne błędy.
• Do oceny routera służą AUROC i APGR (nie zależą od progu). Wykres i tabela pomagają wybrać jeden próg: wg kosztu (wykres) albo wg ryzyka (tabela).

JEŚLI ZAPYTAJĄ
• Jak liczona jest tabela? Próg wyznaczam na jednej części danych, sprawdzam na drugiej. Pewność 95% liczę metodą Clopper–Pearsona.
• Czy 46% oszczędności jest warte 8% jakości? To zależy od administratora, dlatego to on wybiera próg.`,

// 12
`MÓW
• Poważny błąd (slajd 11): pytanie trudne wysłane do małego. Takich pytań jest 15,9%.
• Przykład: 100 takich pytań. Przy progu 0,3 router wysyła 70 do dużego (dobrze) i 30 do małego (gorsza odpowiedź niż mogła być). Losowo, przy tym samym udziale pytań do małego (ok. 46% wszystkich), do małego trafiłoby 46. Router jest lepszy od losowania, ale nie bezbłędny.
• Wykres: ile ze 100 trudnych pytań z danego źródła router wysłał do małego. Arena 25, WildChat 17, TriviaQA (fakty) 81, HumanEval (programowanie) 84.
• Przy pytaniach otwartych router myli się rzadziej, przy faktach i kodzie prawie za każdym razem, gdy pytanie jest trudne.
• Dlaczego: router widzi tylko tekst, a nie to, co wie mały model. Dwa pytania o fakty wyglądają podobnie, a mały zna odpowiedź na jedno i nie zna drugiej.
• Kod: tylko 18% zadań jest trudnych, więc sąsiedzi nowego zadania są zwykle łatwi, wynik jest niski i zadanie idzie do małego. Trudne wyglądają jak łatwe.
• To brak informacji w samym tekście, a nie błąd metody. Dlatego rozważam warstwę 3 (mały model może „czuć”, czy da radę). To hipoteza do sprawdzenia, nie obietnica.

UWAGA
• Próbki są małe: 42 pytania trudne z TriviaQA i 19 z HumanEval. Wnioski ostrożnie.

JEŚLI ZAPYTAJĄ
• Czemu zadania z kodu rzadko są trudne? Mały model rozwiązuje 83% zadań, duży 94%. Różnica jest niewielka.`,

// 13 (test na prawdziwych modelach)
`MÓW
• Pierwsze uruchomienie całego systemu na prawdziwych modelach: qwen3:8b (Ollama) i Qwen 27B (vLLM), oba przez DeepFellow. 20 października, komputer służbowy, 4 pytania do modelu router.
• Router dopisuje do odpowiedzi nagłówki: który model, która warstwa, wynik kNN (liczba 0–1 ze slajdu 9).
• Stolica Francji: wynik 0,19, poniżej progu 0,3, więc mały.
• Opowiadanie o smoku i rycerzu: wynik 0,70, więc duży. Heurystyki dały tylko 1 punkt, więc decyzja przeszła do warstwy 2.
• „Przeanalizuj i porównaj dwa projekty, oceń kompromisy krok po kroku”: 5 fraz z listy trudnych = 5 punktów przy progu 2. Decyduje warstwa 1, od razu duży, bez embeddingu, więc bez wyniku kNN.
• Mnożenie 17 razy 23 w trybie strumieniowym (odpowiedź przychodzi kawałkami): wynik 0,10, mały. Nagłówki dochodzą przed pierwszym kawałkiem odpowiedzi.
• Narzut routera: to samo proste pytanie 5 razy przez router i 5 razy bezpośrednio do małego. Średnio 0,376 s wobec 0,363 s, czyli ok. 13 ms. Cel z planu: poniżej 50 ms.
• Jeszcze nie sprawdzone: przełączenie na duży model przy awarii routera i to, czy po restarcie DeepFellow usługa wraca sama.

UWAGA
• 5 pomiarów to mało, a czasy bezpośrednie wahają się o ok. 27 ms, więcej niż sama różnica. Wniosek: narzut to kilka do kilkunastu ms i na pewno poniżej 50, a nie dokładnie 13.
• Cztery pytania pokazują, że mechanizm działa, a nie jak dobrze router wybiera. Jakość wyboru pokazują wyniki na zbiorze danych.

JEŚLI ZAPYTAJĄ
• Czemu to nie to samo co 20,6 ms z następnego slajdu? To dwa pomiary: tamten dotyczył samej decyzji routera na moim komputerze, bez DeepFellow. Ten całej drogi przez DeepFellow na komputerze służbowym, jako różnica czasów. Obie liczby są poniżej 50 ms.
• Jak rozumieć wynik 0,19? Mniej więcej jako odsetek trudnych wśród 20 podobnych pytań z bazy, z większą wagą dla bardziej podobnych.`,

// 14
`MÓW
• RouterService działa w DeepFellow Infra v0.34. 57 nowych testów, cały zestaw (5157) przechodzi.
• Sprawdziłem go od początku do końca na osobnej instancji z modelami Gemini: wybór modelu, nagłówki, strumieniowanie i przełączenie na duży model przy błędzie (po angielsku fallback). Test wykrył błąd: wycofany model zwracał 404 jako zwykłą odpowiedź i omijał przełączenie. Naprawiłem.
• Z modelami Qwen 8B i 27B uruchomiłem go już na komputerze służbowym (poprzedni slajd). Zostały awaria i restart.
• Czas: mediana 20,6 ms, 90% zapytań poniżej 65 ms (cel poniżej 50 ms spełniony dla mediany).
• Odporność: po literówkach, parafrazach i synonimach decyzja zmienia się tylko w 6–10% pytań (losowo byłoby 42–48%).

OGRANICZENIA
• Jedna para modeli i jeden sędzia (zgodność z człowiekiem umiarkowana).
• Duży model ma jedną próbkę na pytanie.
• Dane mało „firmowe”: 63% to publiczne czaty.
• Wiedza i kod są słabo wykrywane.
• Warstwa 1 jest na naszych danych słaba (AUROC ok. 0,55), dlatego opcjonalna. Na danych firmowych może wypaść lepiej, ale to hipoteza do sprawdzenia.

JEŚLI ZAPYTAJĄ
• Czy zadziała na innych modelach? Router tak, ale etykiety trzeba zmierzyć od nowa: ok. 1,5 doby generowania i ok. 8 USD za sędziego.`,

// 15 (dodatkowe dane)
`MÓW
• Najsłabsza strona danych: niewiele przypominają użycie w firmie. 63% to publiczne czaty (Arena, WildChat), w dużej części zabawa i fikcja. Reszta to znane testy. Brakuje poleceń biurowych, SQL i prawdziwego kodu.
• Hipoteza, nie wynik: przez to router słabo wykrywa trudny kod, a heurystyki mogły wypaść gorzej niż na danych z firmy.
• Po prezentacji dołożę dane z publicznych zbiorów. Cztery kandydatki, ostateczny wybór przed pomiarem.

ZBIORY (LICENCJE SPRAWDZONE NA KARTACH)
• Dolly (CC BY-SA 3.0): ok. 15 tys. poleceń napisanych przez pracowników Databricks (streszczanie, wyciąganie informacji, pytania zamknięte). Najbliższe użyciu w firmie. Część ma fragmenty Wikipedii, usunę z nich numery przypisów.
• CodeChat (ODC-By): ok. 83 tys. prawdziwych rozmów programistów z modelami, ponad 20 języków programowania. To część WildChat, więc usunę powtórzenia.
• Spider (CC BY-SA 4.0): ok. 8 tys. pytań do baz danych z odpowiedzią w SQL (język zapytań do baz). Nowy rodzaj zadań. Pytania napisało 11 studentów Yale, nie prawdziwi użytkownicy. Najdroższy w ocenie, bo trzeba uruchamiać zapytania na bazach.
• Arena 140k (CC BY 4.0 dla promptów): ok. 135 tys. prawdziwych rozmów na wielu tematach i w wielu językach, ze znacznikiem „kod”. Część pytań z Areny już mam, więc sprawdzę powtórzenia.

CO Z KAŻDYM ZBIOREM
• Tak jak z poprzednimi: odpowiedzi obu modeli (mały 3 razy, duży raz), sędzia, Δ. Zbiór testowy zostaje zamknięty, nowe dane trafią tylko do nauki i dostrajania.
• Koszt sędziego (moje oszacowanie): ok. 1 USD na 500 pytań, z ok. 8 USD za całość. Płatne wywołania dopiero za zgodą na konkretną kwotę.
• Licencje ShareAlike (Dolly, Spider) wymagają zachowania tej samej licencji, opiszę to w pracy. Używam tylko promptów, więc warunki dotyczące odpowiedzi modeli (Arena) mnie nie obejmują.

UWAGA
• To plan, nic z tego jeszcze nie zrobiłem. Nie wiem, czy nowe dane poprawią router.

JEŚLI ZAPYTAJĄ
• Czy jest zbiór prawdziwych zapytań firmowych? Nie znalazłem w otwartych zbiorach. Najbliższy jest Dolly.
• Dlaczego nie Bitext (obsługa klienta)? Jest syntetyczny i szablonowy, pewnie prawie same pytania łatwe i bardzo podobne.
• Dlaczego nie LMSYS-Chat-1M? Wymaga zgody na dostęp. Odrzuciłem go wcześniej.
• Dlaczego nie RouterBench? Na jego karcie nie ma licencji, a pytania pochodzą ze znanych testów, więc nie dodaje nowych rodzajów.
• Licencje: interpretacji prawnej nie robiłem, karty podają same licencje. Oficjalnej strony Spider poza kartą nie sprawdzałem.`,

// 16
`PLAN
• 1. Dokończyć test z modelami Qwen 8B i 27B na komputerze służbowym: awaria i restart usługi, a opóźnienie zmierzyć dokładniej, na większej liczbie pomiarów.
• 2. Sprawdzić warstwę 3 (test go/no-go): czy mały model oceniający pytanie poprawia router, i to tylko w strefie niepewności, czyli tam, gdzie warstwa 2 nie jest pewna. Granice strefy dobiorę tak, by jakość nie spadła poniżej ustalonego poziomu (jeszcze do ustalenia).
• 3. Dodać dane bliższe wdrożeniu z poprzedniego slajdu (polecenia biurowe, kod, SQL). Wymaga to ponownego pomiaru, ale pozwoli też sprawdzić, czy heurystyki działają lepiej na takich danych.
• 4. Otworzyć zbiór testowy raz i zrobić ocenę końcową.

PROŚBA
• Proszę o zatwierdzenie celów liczbowych przed otwarciem testu. Po otwarciu ich nie zmieniam, a wyniki podam niezależnie od tego, czy cele są spełnione. To zabezpiecza przed dopasowaniem wymagań do wyniku.

PROPOZYCJA CELÓW
• Router lepszy od „samego źródła” w sposób istotny statystycznie.
• AUROC co najmniej 0,64 (w badaniach 0,68).
• Żeby odzyskać 80% możliwego zysku jakości, wysyłam do dużego nie więcej niż 72% pytań (losowo byłoby 80%).
• Po literówkach i parafrazach decyzja zmienia się w najwyżej 15% pytań.
• Mediana czasu decyzji poniżej 50 ms.
• Pytania spoza dziedziny (MMLU, MT-Bench) tylko raportuję, bez progu.

PODSUMOWANIE
• Etykiety mierzę z prawdziwych odpowiedzi modeli.
• Router oparty na podobieństwie pytań daje realny, ale umiarkowany zysk, jest szybki i stabilny.
• Nie przewidzi tylko tego, czy mały model zna konkretny fakt.`,
];
