module.exports = [
// 1
`MÓW
Dzień dobry. Temat mojej pracy to routing zapytań do modeli językowych według ich trudności.

Najprościej: mam dwa modele, mały i duży. Duży odpowiada lepiej, ale kosztuje więcej czasu i mocy obliczeniowej. Zbudowałem system, który czyta pytanie i, zanim ktokolwiek odpowie, wybiera, do którego modelu je wysłać. Działa jako nowa usługa w DeepFellow Infra.

Najpierw powiem, jaki jest problem i jak zmieniłem podejście do pracy. Potem pokażę, jak sprawdzam, czy pytanie jest trudne, jak działa system i jakie ma wyniki. Na końcu ograniczenia i jedna prośba o decyzję.

WARTO WIEDZIEĆ
Mały model to qwen3:8b, duży to Qwen3.8-27B. Liczby 8 i 27 to miliardy parametrów, czyli rozmiar modelu.
W całej prezentacji „pytanie trudne” znaczy: duży model odpowiada na nie wyraźnie lepiej niż mały. „Pytanie łatwe” znaczy: mały wystarcza.
Całość zajmie ok. 20–25 minut.`,

// 2
`MÓW
Duży model daje lepsze odpowiedzi, ale jest wolniejszy i potrzebuje mocniejszego sprzętu. Mały jest szybki, ale przy trudnych pytaniach bywa słaby.

Administrator ma dziś dwa wyjścia. Wszystko do dużego modelu: drogo. Wszystko do małego: gorsza jakość tam, gdzie była potrzebna.

Router ma wybierać osobno dla każdego pytania: proste do małego (qwen3:8b), trudne do dużego (Qwen 27B). Na rysunku pytanie wchodzi do routera i idzie w jedną z dwóch stron. Dla użytkownika nic się nie zmienia: w DeepFellow to po prostu model o nazwie router.

Trudność jest taka: router musi zdecydować, zanim jakikolwiek model odpowie. Widzi więc tylko treść pytania. Cała praca jest o tym, ile można o trudności pytania wywnioskować z samego jego tekstu.

Cel: jak najwięcej pytań do małego modelu przy prawie niezmienionej jakości.

JEŚLI ZAPYTAJĄ
Dlaczego nie zawsze duży model? Bo to najdroższe rozwiązanie. Pokażę, ile da się zaoszczędzić i jakim kosztem.`,

// 3
`MÓW
Zacznę od tego, jak wyglądała pierwsza wersja pracy.

Informację, że pytanie jest łatwe albo trudne, czyli etykietę, brałem z gotowych danych: z głosowań w Chatbot Arena, gdzie ludzie wybierają lepszą z dwóch odpowiedzi, oraz z pytań wygenerowanych przez Gemini.

Plan miał też trzy warstwy rozpoznawania trudności: proste heurystyki, porównanie z podobnymi pytaniami i mały model. Do tego konfigurację w pliku YAML, kategorie tematyczne i podział złożonych zadań na części (Map-Reduce). Odpowiedzi miałem oceniać między innymi miarą ROUGE.

ROUGE liczy, ile słów wspólnych ma odpowiedź modelu z odpowiedzią wzorcową. Zrezygnowałem z niej, bo zbieżność słów nie mówi, czy odpowiedź jest poprawna: dobra odpowiedź może być napisana innymi słowami, a zła może mieć wiele wspólnych.

To był rozsądny plan, bo opierał się na literaturze: znany system RouteLLM uczy się właśnie na głosach z Areny. Miał jednak jeden słaby punkt. Pokazuję go na następnym slajdzie.`,

// 4
`MÓW
Sprawdziłem, czy etykiety z Areny pasują do moich dwóch modeli.

Z Areny mam stare etykiety: pytanie jest „trudne”, jeśli w głosowaniu wygrał mocniejszy model. Dla moich dwóch modeli zmierzyłem osobno, o ile duży jest lepszy od małego na każdym pytaniu.

Porównałem jedno z drugim dla 1723 pytań. Wynik to 0,55. Mierzę to miarą o nazwie AUROC. Wyobraź sobie losowo wybraną parę pytań: jedno trudne według Areny, drugie nie. Para liczy się jako 1, gdy to pierwsze ma większą zmierzoną przewagę dużego modelu, jako 0, gdy mniejszą, i jako 0,5 przy remisie. AUROC to średnia z takich wyników po wszystkich parach, czyli w praktyce odsetek par ustawionych dobrze. Wynik 0,55 znaczy: w 55 parach na 100. Przy zwykłym rzucie monetą byłoby 50 na 100, a przy pełnej zgodności 100 na 100. Czyli zgodności prawie nie ma. Tej samej miary użyję później do oceny routera.

Dlaczego tak wyszło? Arena porównywała inne modele, z innej epoki. Gdy gpt-4 wygrywa ze słabym modelem, to zwykle bez względu na pytanie. Stara etykieta mówi więc więcej o różnicy między modelami niż o trudności pytania.

Wniosek: trudność zależy od konkretnej pary modeli. Dlatego sam ją mierzę na swoich dwóch modelach. Zaraz pokażę jak.

UWAGA
To jest analiza, a nie dowód, że moje etykiety są lepsze. Pokazuje tylko, że stare nie pasują do tych modeli.

JEŚLI ZAPYTAJĄ
Czy 0,55 to nie przypadek? Było 1723 pytań, a 0,55 jest bardzo blisko 0,5, więc wniosek jest ostrożny: stara etykieta słabo przewiduje wyniki naszych modeli.`,

// 5
`MÓW
Każde pytanie przechodzi cztery kroki.

Mam 4313 pytań z ośmiu źródeł. Krok 1. Wysyłam każde do obu modeli: do małego trzy razy, do dużego raz. Odpowiedzi modeli są losowe, więc jedna próbka małego modelu byłaby za mało pewna.

Krok 2. Oceniam odpowiedzi. Gdy znana jest poprawna odpowiedź, np. wynik zadania, sprawdza automat. W pozostałych przypadkach ocenia drugi model, Gemini, w skali od 1 do 5. Dostaje pytanie i wszystkie odpowiedzi w losowej kolejności i bez nazw modeli, żeby nikogo nie faworyzował.

Krok 3. Liczę różnicę, oznaczoną Δ (delta): ocena dużego minus średnia ocena małego.

Krok 4. Jeśli różnica jest większa niż jeden punkt w skali 1–5, pytanie jest TRUDNE (COMPLEX), czyli duży jest wyraźnie lepszy. W przeciwnym razie jest ŁATWE (SIMPLE).

Przykład z rysunku. Duży dostał 5, mały 3, 3 i 4, średnio 3,3. Różnica to 1,7 punktu, więcej niż 1, więc pytanie jest trudne. Na slajdzie te oceny są przeliczone na skalę 0–1 (wzorem (ocena − 1) / 4): duży dostał 1,00, mały średnio 0,58, więc Δ = 0,42. Granica Δ > 0,25 odpowiada więc jednemu punktowi. Nazywam ją progiem trudności, żeby nie mylić jej z progiem routera, o którym będzie mowa dalej.

Jeśli oba modele odpowiedziały źle, pytanie zostaje łatwe, bo duży model nic by nie dał.

JEŚLI ZAPYTAJĄ
Dlaczego trzy próbki małego? Sprawdziłem, że jedna próbka dałaby tę samą klasę co wszystkie trzy tylko w 74% pytań otwartych. Średnia z trzech zmniejsza ten szum.
Skąd próg jeden punkt? To mój wybór. Sprawdziłem też łagodniejszy i ostrzejszy (odsetek trudnych pytań: 51,5%, 35,4% i 27,6%). Wnioski o routerze są te same.`,

// 6
`MÓW
Mam 4313 pytań z ośmiu źródeł i 17 252 odpowiedzi obu modeli. Dwa źródła to zbiory prawdziwych rozmów z chatbotami: Arena i WildChat. Dalej pytania wygenerowane przez Gemini i zbiory z matematyki, wiedzy i programowania. Dzięki temu są i pytania otwarte, i takie ze znaną poprawną odpowiedzią.

Podzieliłem je na trzy części: 50% do nauki routera, 20% do dostrajania i 30% do końcowego testu. Test jest zamknięty: otworzę go raz, na końcu, żeby nie dopasować routera do testu.

Bardzo podobne pytania trafiają zawsze do jednej części. Inaczej router „znałby” pytania z testu, a wynik byłby zawyżony.

Wynik pomiaru: 35,4% pytań jest trudnych. Ale bardzo różnie zależnie od źródła: w zadaniach matematycznych 4%, w rozmowach z WildChat 48%. Mały model dobrze liczy, a rozmowy otwarte są dla niego trudniejsze. Czyli „trudne” nie zawsze znaczy to, co podpowiada intuicja.

JEŚLI ZAPYTAJĄ
Skąd te źródła? Chciałem mieszankę: prawdziwe, niejednoznaczne rozmowy oraz zadania, w których poprawność da się sprawdzić automatem.
Ograniczenie: to głównie publiczne czaty, więc brakuje zapytań z typowego użycia w firmie. Wracam do tego na końcu.`,

// 7
`MÓW
Etykiety ocenia model, więc sprawdziłem, ile można im ufać.

Pierwsza liczba: 90%. Gdy zmienię kolejność odpowiedzi, ten sam sędzia daje tę samą klasę (trudne albo łatwe) w 90% pytań. Jest więc w miarę stabilny.

Druga: 79%. Drugi, mocniejszy sędzia zgadza się z pierwszym co do klasy w 79% pytań.

Trzecia: sam oceniłem 100 odpowiedzi, nie wiedząc, który model je napisał. Z sędzią zgadzam się umiarkowanie. Korelacja wynosi 0,59 (1 oznaczałaby identyczne uporządkowanie ocen, a 0 brak związku). Dodatkowo identyczną ocenę dałem w 43% przypadków, a różnicę nie większą niż jeden punkt w 77%.

Czwarta: sędzia jest surowszy ode mnie średnio o 0,4 punktu (jego średnia ocena to 3,00, a moja 3,40).

Wniosek: etykiety są użyteczne, ale nie idealne, i tak je opisuję w pracy. To nie przekreśla wyników, bo etykieta opiera się na różnicy ocen dwóch modeli, więc stała surowość sędziego się znosi.

JEŚLI ZAPYTAJĄ
Czy sędzia nie faworyzuje długich odpowiedzi? Sprawdziłem: korelacja z długością to 0,06, czyli prawie żadna.
Który sędzia jest lepszy? Nie rozstrzygam. Używam tańszego, a drugi dostał tylko część pytań.`,

// 8
`MÓW
Router ma trzy warstwy, od najtańszej do najdroższej. Zasada: warstwa zostaje tylko wtedy, gdy pokaże zysk.

Warstwa 1: heurystyki, czyli punkty za proste cechy tekstu pytania. Pytanie dostaje plus jeden punkt za każdą frazę z listy zadań trudnych i minus jeden za każdą frazę z listy łatwych. Do tego plus jeden punkt, gdy jest dłuższe niż 400 znaków, kolejny plus jeden powyżej 1500, minus jeden, gdy ponad 10% znaków to cyfry, i plus jeden za adres internetowy. Administrator może zmienić wszystkie te punkty.
Słowa pochodzą z literatury, a nie z moich danych, żeby ich nie dopasować do wyników. Pierwsze źródło to taksonomia Blooma (Anderson i Krathwohl, 2001), czyli hierarchia poziomów myślenia od zapamiętywania do tworzenia: słowa jak „analyze”, „compare”, „design” wskazują zadania trudniejsze, a „what is”, „define” łatwiejsze. Drugie źródło to lista fraz z AgentBus, praktycznego systemu routingu modeli: np. „debug”, „refactor”, „step by step”.
Gdy suma punktów dojdzie do progu (domyślnie 2), pytanie idzie od razu do dużego modelu, bez dalszych warstw. Ta warstwa kieruje tylko do dużego, bo pomyłka w tę stronę kosztuje tylko pieniądze, a nie jakość. Jest opcjonalna: bez pliku z parametrami jest wyłączona. U nas próg 2 punkty obejmuje 6% pytań, z których 52% jest naprawdę trudnych (wśród wszystkich pytań 37%), więc heurystyki są lepsze od zgadywania o kilkanaście punktów procentowych i obejmują niewiele ruchu. W pomiarze nie zmieniają jakości całego routera.

Warstwa 2: porównanie z podobnymi pytaniami (metoda kNN) na embeddingach, czyli na liczbowym opisie pytania. To główna część rozwiązania i wyjaśniam ją na następnym slajdzie.

Warstwa 3: mały model sam ocenia, czy pytanie jest trudne. Jeszcze jej nie ma. Wejdzie, jeśli krótki test pokaże zysk. Ten test nazywa się go/no-go: jeśli pomaga, budujemy, jeśli nie, rezygnujemy. Nie chcę jej wywoływać dla każdego pytania, bo to wywołanie małego modelu i trwa sekundy. Będzie dotyczyć tylko pytań, przy których warstwa 2 jest niepewna. Wyjaśniam to niżej, po omówieniu wyniku routera.

Na końcu router zwraca liczbę od 0 do 1. To jego wynik dla pytania: im wyższy, tym bardziej router uważa pytanie za trudne, czyli tym większa szansa, że duży model odpowie wyraźnie lepiej. Administrator ustawia próg: wynik powyżej idzie do dużego modelu, poniżej do małego. Gdy cokolwiek zawiedzie, pytanie idzie do dużego, bo to bezpieczniejsze.

Teraz warstwa 3. Niepewna znaczy: wynik warstwy 2 jest w środku skali, między dwoma progami, a nie przy jej końcach. Przykład: poniżej 0,2 pytanie idzie do małego, powyżej 0,45 do dużego, a pomiędzy decyduje warstwa 3. W naszych danych to mniej więcej połowa pytań. Pozostałe, tak czy inaczej rozstrzyga sama warstwa 2. Granice dobiorę na danych do dostrajania tak, żeby jakość nie spadła poniżej ustalonego poziomu. Tego poziomu jeszcze nie ustaliłem.

JEŚLI ZAPYTAJĄ
Ile to trwa? Heurystyki ok. 0,3 ms, a warstwa 2 ok. 20 ms. Warstwa 3 byłaby wywołaniem małego modelu, czyli sekundami, dlatego jest ostatnia i tylko dla pytań w strefie niepewności.`,

// 9
`MÓW
Router dostaje tekst pytania, a ma zwrócić liczbę od 0 do 1. Robi to w czterech krokach.

Krok 1. Zamienia pytanie na liczby. Komputer nie potrafi porównać dwóch zdań, więc zamieniam każde na listę 768 liczb. To się nazywa embedding. Pytania o podobnym znaczeniu dostają podobne listy, jak punkty leżące blisko siebie na mapie.

Krok 2. Szuka 20 najbardziej podobnych pytań w mojej bazie, czyli takich, których trudność już zmierzyłem.

Krok 3. Sprawdza, ile z tych 20 było trudnych. Wynik to ten odsetek, a podobniejsze pytania liczą się bardziej. Jeśli 14 z 20 było trudnych, wynik jest wysoki i pytanie idzie do dużego modelu.

Krok 4. Porównuje wynik z progiem administratora.

Dlaczego tak, a nie bardziej skomplikowanie? Po pierwsze, nie trzeba niczego trenować: baza to zapisane pytania, a nowe dane to dopisanie wierszy. Po drugie, wynik ma zrozumiałe znaczenie i można pokazać, które pytania były sąsiadami. Po trzecie, liczy się lokalnie w ok. 20 ms, więc pytania nie opuszczają serwera.

A dlaczego kNN, a nie same embeddingi? Embedding to tylko lista liczb opisująca pytanie. Sama nie mówi, czy pytanie jest trudne. Potrzebna jest metoda, która z tych liczb zrobi wynik. Najprostsza to porównanie z pytaniami, których trudność już znam, czyli właśnie kNN.
To nie jest mój wymysł. Wzorowałem się na metodzie „Similarity-Weighted Ranking” z artykułu RouteLLM (Ong i in., 2024). Tam nowe zapytanie też zamienia się na embedding, porównuje z 80 tysiącami pytań z Chatbot Arena przez podobieństwo i liczy ważoną sumę głosów ludzi. Ta metoda nie wymaga trenowania. Inne metody z tego artykułu (faktoryzacja macierzy, BERT, duży model językowy) wymagają trenowania albo fine-tuningu, którego mój plan nie przewiduje. Różnię się tym, że uśredniam etykiety zmierzone na własnych modelach, a nie głosy z Areny, i biorę tylko 20 najbliższych pytań, a nie całą historię. Wadą oryginału jest czas i koszt: przeszukuje całą bazę przy każdym zapytaniu (w ich zestawieniu ok. 39 USD za milion zapytań). U mnie baza ma ok. 3 tysięcy wektorów, a wyszukiwanie trwa ok. 1 ms.

Co sprawdziłem. Wyniki routera liczę na pytaniach, których router nie widział w nauce (walidacja krzyżowa: dzielę dane na części, uczę na jednych, oceniam na pozostałych). Miara to AUROC, taka jak na slajdzie 4, tylko teraz pytam, czy router daje wyższy wynik pytaniom trudnym niż łatwym. Cztery modele zamieniające tekst na liczby dały AUROC od 0,679 do 0,709. Najlepszy, qwen3, jest trzy razy wolniejszy (52 ms wobec 17,6 ms) i ma niewielką przewagę, więc zostaje nomic. Dziewięć klasyfikatorów (regresja logistyczna, SVM, sieć MLP, boosting drzew i inne) dało od 0,662 do 0,691. Żaden nie jest istotnie lepszy od kNN. Wniosek: ok. 0,68–0,69 to sufit informacji, który mają w sobie embeddingi dla tych etykiet.

JEŚLI ZAPYTAJĄ
Dlaczego 20 sąsiadów? Przy jednym AUROC to 0,590, bo wynik jest zaszumiony, a od ok. 20 jest stabilny (0,682 przy 20, 0,689 przy 40). Więcej nie poprawia.
Czy ważenie pomaga? Tak, trochę: równe wagi dają 0,677, a ważenie podobieństwem 0,682. Ostrzejsze ważenie daje do 0,702, ale wybrałem je spośród 30 wariantów na tych samych danych, więc nie przyjmuję tego bez potwierdzenia.
Czy więcej danych pomoże? Niewiele: powyżej ok. 1200 pytań podwojenie bazy poprawia wynik o ok. 0,01.
Ograniczenie: model liczący wektory czyta do 2048 tokenów, więc dłuższe pytania liczy z samego początku.`,

// 10
`MÓW
Teraz wyniki routera. Używam dwóch miar.

Pierwsza to AUROC, znany już ze slajdu 4: dla losowej pary pytań, jedno trudne i jedno łatwe, odsetek par, w których router dał trudnemu wyższy wynik. Wynik routera to ta liczba od 0 do 1 ze slajdu 9: im wyższa, tym bardziej router uważa pytanie za trudne (np. 0,7, gdy 14 z 20 podobnych pytań było trudnych). 0,5 to zgadywanie, 1,0 to bezbłędny router. Mój router ma 0,682, czyli w 68 parach na 100 ustawia je dobrze. AUROC nie zależy od progu: ocenia sam wynik routera.
Jak liczy się jedną parę: jeśli trudne pytanie dostało wyższy wynik niż łatwe, para daje 1. Jeśli niższy, 0. Jeśli wyniki są równe, 0,5. Np. trudne dostało 0,70, a łatwe 0,40: wynik pary to 1. AUROC to średnia z wyników wszystkich takich par. U nas jest ok. 1130 trudnych i 1880 łatwych pytań, czyli ponad 2 miliony par.

Druga to APGR. Najpierw „jakość”: to średnia ocena odpowiedzi w skali od 0 do 1. Gdy wszystko idzie do małego, jakość to 0,625, a gdy wszystko do dużego, 0,846. Cały możliwy zysk to więc 0,221. Router, który przy pewnym progu daje jakość 0,777, odzyskuje 0,152 z 0,221, czyli 0,69. To odzyskana część zysku dla jednego progu. Takich punktów jest wiele, po jednym dla każdego progu. APGR to średnia z nich wszystkich, czyli jedna liczba opisująca cały router. Zobaczysz te punkty jako wykres na następnym slajdzie. Losowe wysyłanie daje APGR 0,5, a idealny router 0,91. Mój ma 0,605.

Uwaga, co dokładnie mierzą te liczby: to wynik warstwy 2 (kNN), bo tylko ona daje liczbę od 0 do 1 dla każdego pytania. Warstwę 1 sprawdziłem osobno (ok. 0,55) oraz razem z kNN: kaskada nie zmienia jakości. Warstwy 3 jeszcze nie ma, więc nie ma czego mierzyć. Cały router, ze wszystkimi warstwami, ocenię na zbiorze testowym.
Słupki na wykresie to AUROC. Losowy: 0,5. Sama długość pytania: 0,525, czyli prawie nic nie mówi. „Samo źródło”: 0,631. To router, który w ogóle nie czyta pytania, tylko wie, z jakiego zbioru pochodzi, i daje każdemu pytaniu wynik równy odsetkowi trudnych pytań w tym zbiorze (4% dla zadań matematycznych, 48% dla WildChat). W praktyce źródła nie znamy, więc to tylko poprzeczka. Pytam: czy router wie coś więcej niż rodzaj pytania? Wie, ale niewiele więcej: różnica to 0,05 w AUROC i 0,023 w APGR (0,605 wobec 0,582), istotna statystycznie.

Uczciwie: dużą część skuteczności daje samo rozpoznanie rodzaju pytania. Wewnątrz jednego źródła wynik jest słabszy: dla Areny 0,60, a dla pytań o wiedzę (TriviaQA) ok. 0,50, czyli nic. Heurystyki z warstwy 1 dają same ok. 0,55, więc nie poprawiają kNN.

JEŚLI ZAPYTAJĄ
Czy da się lepiej? Z samego tekstu raczej nie: różne metody dają podobny wynik. Potrzebny byłby inny sygnał, np. warstwa 3.`,

// 11
`MÓW
Ten slajd pokazuje dwie różne rzeczy: po lewej wykres, po prawej tabelę. Wyjaśniam je po kolei, a na końcu, jak się do siebie mają.

LEWA STRONA: WYKRES (to jest obraz APGR)
Oś pozioma to odsetek pytań, które wysyłam do dużego modelu, od 0% do 100%. Oś pionowa to jakość, czyli średnia ocena odpowiedzi w skali 0–1. Liczę ją tak: dla każdego pytania biorę ocenę modelu, do którego poszło, i uśredniam po wszystkich pytaniach.
Wszystko do małego daje 0,625, a wszystko do dużego 0,846. Szara linia to wysyłanie losowe: jakość rośnie po prostu proporcjonalnie do udziału dużego. Pomarańczowa linia to router. Jest wyżej, czyli przy tym samym udziale dużego modelu daje lepszą jakość.
Ten wykres to właśnie te punkty, z których APGR jest średnią. Przy 54% do dużego jakość routera to 0,777, czyli odzyskuję 0,69 luki między 0,625 a 0,846, a przy wysyłaniu losowym byłoby to 0,54. APGR (0,605 wobec 0,5 losowo) mierzy odstęp między liniami.
Jeden punkt jako przykład, próg 0,3: do dużego idzie 54% pytań, jakość to 0,777. To ok. 46% mniej wywołań dużego modelu (100% minus 54%) za ok. 8% niższą jakość (0,846 spada do 0,777). Uwaga: te dwie liczby, 46% i 8%, to odczyt z jednego punktu wykresu, a nie APGR. APGR jest jedną liczbą opisującą całą linię.

PRAWA STRONA: TABELA (to jest inna miara, nie APGR)
Średnia jakość nie pokazuje najgorszych przypadków. Pytanie poważnie błędne to takie, na które duży model odpowiedziałby wyraźnie lepiej (o ponad 2 punkty w skali 1–5), a które poszło do małego. Takich pytań jest 15,9% wszystkich.
Tabela mówi: jeśli akceptuję do 12% poważnych błędów wśród pytań wysłanych do małego, to do małego idzie 47% pytań. Przy 10% idzie 22%, przy 15% aż 90%. Poniżej ok. 8% żaden próg nie daje gwarancji z 95% pewnością.

JAK SIĘ TE DWA OBRAZY DO SIEBIE MAJĄ
To ten sam router i te same progi, oglądane z dwóch stron. Wykres odpowiada na pytanie „ile średnio stracę na jakości”, tabela na pytanie „jak często popełnię poważny błąd”. Np. próg 0,3: z wykresu 54% do dużego i jakość 0,777, z tabeli do małego idzie ok. 47% pytań, a wśród nich ok. 11% to poważne błędy.
Do oceny routera służą AUROC i APGR (nie zależą od progu). Wykres i tabela pomagają administratorowi wybrać jeden próg: albo patrząc na koszt (wykres), albo na ryzyko (tabela).

JEŚLI ZAPYTAJĄ
Jak liczona jest tabela? Próg wyznaczam na jednej części danych, a sprawdzam na drugiej. Pewność 95% liczę metodą Clopper–Pearsona.
Czy 46% oszczędności jest warte 8% jakości? To zależy od administratora, dlatego to on wybiera próg.`,

// 12
`MÓW
Na poprzednim slajdzie pokazałem, że router czasem popełnia poważny błąd: wysyła do małego modelu pytanie, na które duży odpowiedziałby wyraźnie lepiej (o ponad 2 punkty w skali 1–5). Takich pytań jest 15,9% wszystkich.

Wyobraź sobie 100 takich pytań. Przy progu 0,3 router wysyła do dużego modelu 70 z nich i to jest dobrze. Pozostałe 30 trafia do małego, więc użytkownik dostaje gorszą odpowiedź, niż mógł dostać. Stąd 30%. Gdyby router niczego nie umiał i losowo kierował do małego tyle samo pytań co teraz (ok. 46% wszystkich), do małego trafiłoby 46 z tych 100. Router jest więc lepszy od losowania, ale nie bezbłędny.

Wykres pokazuje to osobno dla każdego źródła. Biorę 100 pytań trudnych z danego źródła i liczę, ile z nich router wysłał do małego, czyli w ilu przypadkach się pomylił:
• Arena: 25 ze 100.
• WildChat: 17 ze 100.
• TriviaQA, pytania o fakty: 81 ze 100.
• HumanEval, zadania programistyczne: 84 ze 100.
Przy pytaniach otwartych router myli się więc rzadziej, a przy faktach i programowaniu myli się prawie za każdym razem, gdy pytanie jest trudne.

Dlaczego tak jest? Router widzi tylko tekst pytania, a nie to, co wie mały model. Dwa pytania o fakty wyglądają podobnie, ale mały model może znać odpowiedź na jedno i nie znać drugiej. W tekście tego nie widać.
Przy programowaniu tylko 18% zadań jest trudnych. Sąsiedzi nowego zadania są więc zwykle łatwi, wynik jest niski i zadanie idzie do małego. Te trudne wyglądają tak samo jak łatwe.

To nie jest błąd metody, tylko brak informacji w samym tekście. Dlatego rozważam warstwę 3: może sam mały model „czuje”, czy da radę. To hipoteza do sprawdzenia, a nie obietnica.

UWAGA
Próbki są małe: 42 pytania trudne z TriviaQA i 19 z HumanEval. Wnioski ostrożnie.

JEŚLI ZAPYTAJĄ
Czemu zadania z kodu nie są częściej trudne? Mały model rozwiązuje 83% zadań, duży 94%. Różnica jest niewielka.`,

// 13 (test na prawdziwych modelach)
`MÓW
Do tej pory wszystkie wyniki liczyłem na zapisanych danych. Teraz pokazuję pierwsze uruchomienie całego systemu na prawdziwych modelach: małym qwen3:8b, uruchomionym w programie Ollama, i dużym Qwen 27B, uruchomionym przez vLLM. Oba podłączone przez DeepFellow. Zrobiłem to 20 października na komputerze służbowym i wysłałem do modelu o nazwie router cztery pytania.

Router dopisuje do każdej odpowiedzi trzy nagłówki: który model odpowiedział, która warstwa podjęła decyzję i jaki był wynik kNN, czyli ta liczba od 0 do 1 ze slajdu 9. Dzięki temu decyzję widać bez zaglądania do logów.

Pierwsze pytanie, o stolicę Francji: wynik 0,19, poniżej progu 0,3, więc odpowiada mały model. Drugie, prośba o opowiadanie o smoku i rycerzu: wynik 0,70, powyżej progu, więc odpowiada duży i pisze całe opowiadanie. Trzecie to polecenie „przeanalizuj i porównaj dwa projekty, oceń kompromisy krok po kroku”. Zawiera pięć fraz z listy zadań trudnych, czyli pięć punktów heurystyk przy progu dwóch. Decyduje więc warstwa 1: pytanie idzie od razu do dużego i nawet nie liczę embeddingu, dlatego nie ma wyniku kNN. Przy opowiadaniu heurystyki dały tylko jeden punkt, więc decyzja przeszła do warstwy 2. Czwarte to mnożenie 17 razy 23 wysłane w trybie strumieniowym, czyli odpowiedź przychodzi kawałkami: wynik 0,10, odpowiada mały, a nagłówki z decyzją dochodzą przed pierwszym kawałkiem odpowiedzi.

Potem zmierzyłem, ile czasu dokłada sam router. To samo proste pytanie wysłałem pięć razy przez router i pięć razy bezpośrednio do małego modelu. Średni czas to 0,376 s wobec 0,363 s, czyli router dodaje ok. 13 ms. Cel z planu to mniej niż 50 ms.

Czego jeszcze nie sprawdziłem: przełączenia na duży model, gdy router ulegnie awarii, oraz tego, że po restarcie DeepFellow usługa wraca sama. To zrobię w następnej kolejności.

UWAGA
Pięć pomiarów to mało, a czasy bezpośrednie wahają się o ok. 27 ms, czyli więcej niż sama różnica. Wniosek brzmi więc: narzut to kilka do kilkunastu milisekund i na pewno poniżej 50, a nie dokładnie 13.
Cztery pytania pokazują, że mechanizm działa. Nie mówią, jak dobrze router wybiera. Jakość wyboru pokazują wyniki na zbiorze danych z wcześniejszych slajdów.

JEŚLI ZAPYTAJĄ
Czemu to nie jest to samo co 20,6 ms z następnego slajdu? To dwa różne pomiary: tamten dotyczył samej decyzji routera na moim komputerze, bez DeepFellow, a ten całej drogi przez DeepFellow na komputerze służbowym, jako różnica czasów. Obie liczby są poniżej 50 ms.
Jak rozumieć wynik 0,19? Jako w przybliżeniu odsetek trudnych pytań wśród 20 podobnych z bazy, z większą wagą dla bardziej podobnych.`,

// 14
`MÓW
Implementacja. Usługa RouterService działa w DeepFellow Infra w wersji 0.34. Napisałem 57 nowych testów, a cały zestaw testów (5157) przechodzi. Sprawdziłem ją od początku do końca na osobnej instancji z modelami Gemini: wybór modelu, nagłówki z decyzją, strumieniowanie i przełączenie na duży model przy błędzie (po angielsku fallback). Test wykrył błąd: wycofany model zwracał 404 jako zwykłą odpowiedź i omijał to przełączenie. Naprawiłem. Z modelami Qwen 8B i 27B uruchomiłem ją już na komputerze służbowym i pokazałem to na poprzednim slajdzie. Zostały dwa sprawdzenia: przełączenie na duży model przy awarii i restart usługi.

Sprawdziłem też dwie rzeczy. Czas: mediana 20,6 ms, a 90% zapytań w mniej niż 65 ms (cel poniżej 50 ms spełniony dla mediany). Odporność: po literówkach, parafrazach i zamianie na synonimy decyzja zmienia się tylko w 6–10% pytań. Losowo byłoby 42–48%. Router nie jest więc wrażliwy na drobne zmiany sformułowania.

Ograniczenia, które nazywam wprost. Jedna para modeli. Jeden sędzia, a zgodność z człowiekiem jest umiarkowana. Duży model ma jedną próbkę na pytanie. Dane są mało „firmowe”: 63% to publiczne czaty. Wiedza i kod są słabo wykrywane. Warstwa 1 (heurystyki) jest na naszych danych słaba (AUROC ok. 0,55), dlatego jest opcjonalna. Możliwe, że na danych firmowych wypadnie lepiej, ale to hipoteza do sprawdzenia.

JEŚLI ZAPYTAJĄ
Czy zadziała na innych modelach? Router tak, ale etykiety trzeba zmierzyć od nowa: ok. 1,5 doby generowania i ok. 8 USD za sędziego.`,

// 15 (dodatkowe dane)
`MÓW
Najsłabsza strona moich danych jest taka, że niewiele przypominają zwykłe użycie w firmie. 63% to publiczne czaty z Areny i WildChat, w dużej części zabawa i fikcja literacka. Reszta to znane testy. Brakuje poleceń biurowych, zadań z bazami danych i prawdziwego kodu pisanego przez programistów. Przez to router słabo wykrywa trudny kod, a heurystyki z warstwy 1 mogły wypaść gorzej, niż wypadną na danych z firmy. To jest hipoteza do sprawdzenia, a nie wynik.

Dlatego po prezentacji chcę dołożyć dane z innych publicznych zbiorów. Pokazuję cztery kandydatki. Licencje sprawdziłem na kartach zbiorów: Dolly ma CC BY-SA 3.0, CodeChat ODC-By, Spider CC BY-SA 4.0, a Arena 140k CC BY 4.0 dla promptów. Dwie z nich, Dolly i Spider, to licencje typu ShareAlike, czyli z warunkiem zachowania tej samej licencji. Opiszę to w pracy. Używam tylko promptów, a odpowiedzi generują moje modele, więc warunki dotyczące odpowiedzi modeli w Arenie mnie nie obejmują. Ostateczny wybór zrobię przed pomiarem.

Pierwsza to Dolly, około 15 tysięcy poleceń napisanych przez pracowników firmy Databricks: streszczanie tekstu, wyciąganie informacji, pytania zamknięte, burza mózgów. To najbliższe temu, o co ktoś mógłby pytać asystenta w firmie. Część poleceń ma dołączone fragmenty Wikipedii, z których usunę numery przypisów.

Druga to CodeChat, około 83 tysięcy prawdziwych rozmów programistów z modelami językowymi, w ponad dwudziestu językach programowania. Dałaby dużo więcej prawdziwego kodu niż dzisiejsze zadania z jednego zbioru, HumanEval. To część zbioru WildChat, który już mam, więc najpierw usunę powtórzenia.

Trzecia to Spider, około 8 tysięcy pytań zadawanych bazom danych po angielsku, do których trzeba napisać zapytanie w języku SQL. SQL to język, którym pyta się bazy danych. To nowy rodzaj zadań, typowy dla firm. Pytania napisało 11 studentów uniwersytetu Yale, więc nie są to zapytania prawdziwych użytkowników. Jest najdroższy w ocenie, bo żeby sprawdzić wynik automatem, trzeba uruchamiać zapytania na bazach.

Czwarta to Arena 140k, około 135 tysięcy prawdziwych rozmów z Areny, na wielu tematach i w wielu językach, ze znacznikiem, które dotyczą kodu. Daje więcej różnych pytań. Część pytań z Areny już mam, więc też sprawdzę powtórzenia.

Co trzeba zrobić z każdym zbiorem: tak jak z poprzednimi, wysłać pytania do obu modeli (mały trzy razy, duży raz), ocenić odpowiedzi sędzią i policzyć różnicę Δ. Dopiero wtedy pytania dostają etykiety. Zbiór testowy zostaje zamknięty, nowe dane trafią tylko do części do nauki i dostrajania. Koszt sędziego to moje oszacowanie: ok. 1 dolar na 500 pytań, na podstawie dotychczasowych ok. 8 dolarów za całość. Płatne wywołania zrobię dopiero za zgodą na konkretną kwotę.

UWAGA
To jest plan, nic z tego jeszcze nie zrobiłem. Nie wiem, czy nowe dane poprawią router. Wiem tylko, że obecne nie pokazują zwykłego użycia w firmie, więc ich uzupełnienie jest uzasadnione.

JEŚLI ZAPYTAJĄ
Czy jest zbiór prawdziwych zapytań firmowych? Nie znalazłem go w otwartych zbiorach. Najbliższy jest Dolly, pisany przez pracowników firmy.
Dlaczego nie Bitext, czyli zbiór pytań do obsługi klienta? Jest syntetyczny i szablonowy, więc pewnie prawie same pytania łatwe i bardzo do siebie podobne. Nic by nie powiedział o prawdziwym ruchu.
Dlaczego nie LMSYS-Chat-1M? Wymaga zgody na dostęp. Odrzuciłem go wcześniej.
Dlaczego nie RouterBench, zbiór do badań nad routingiem? Na jego karcie nie ma licencji, a pytania pochodzą ze znanych testów, więc nie dodałby nowych rodzajów pytań.
A licencje? Sprawdziłem je na kartach zbiorów: Dolly CC BY-SA 3.0, CodeChat ODC-By, Spider CC BY-SA 4.0, Arena 140k CC BY 4.0 dla promptów. Dolly i Spider mają ShareAlike, co opiszę w pracy. Prawnej interpretacji nie robiłem, karty podają same licencje. Nie sprawdziłem oficjalnej strony Spider poza kartą.`,

// 16
`MÓW
Co dalej. Po pierwsze, dokończyć test z modelami Qwen 8B i 27B na komputerze służbowym: awaria i restart usługi, a opóźnienie zmierzyć dokładniej, na większej liczbie pomiarów. Po drugie, sprawdzić warstwę 3 (test go/no-go): czy mały model oceniający pytanie poprawia wynik routera, i to tylko w strefie niepewności, czyli tam, gdzie warstwa 2 nie jest pewna. Granice strefy dobiorę tak, żeby jakość nie spadła poniżej ustalonego poziomu, który jeszcze trzeba ustalić. Po trzecie, dodać dane bliższe wdrożeniu, czyli te zbiory, które pokazałem na poprzednim slajdzie: polecenia biurowe, prawdziwy kod i zadania SQL. To wymaga ponownego pomiaru, ale pozwoli też sprawdzić, czy heurystyki warstwy 1 działają lepiej na takich danych. Po czwarte, otworzyć zbiór testowy raz i zrobić ocenę końcową.

Prośba. Proszę o zatwierdzenie celów liczbowych przed otwarciem testu. Po otwarciu nie będę ich zmieniał, a wyniki podam niezależnie od tego, czy cele są spełnione. To zabezpiecza przed dopasowaniem wymagań do wyniku.

Moja propozycja celów:
• router lepszy od „samego źródła” w sposób istotny statystycznie,
• AUROC co najmniej 0,64 (w badaniach 0,68),
• żeby odzyskać 80% możliwego zysku jakości, wysyłam do dużego nie więcej niż 72% pytań (losowo byłoby 80%),
• po literówkach i parafrazach decyzja zmienia się w najwyżej 15% pytań,
• mediana czasu decyzji poniżej 50 ms,
• pytania spoza dziedziny (MMLU, MT-Bench) tylko raportuję, bez progu.

Podsumowanie. Etykiety mierzę z prawdziwych odpowiedzi modeli. Router oparty na podobieństwie pytań daje realny, ale umiarkowany zysk, jest szybki i stabilny. Nie przewidzi tylko tego, czy mały model zna konkretny fakt.`,
];
