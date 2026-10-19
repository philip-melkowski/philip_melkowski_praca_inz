module.exports = [
// 1
`MÓW
Dzień dobry. Temat mojej pracy to routing zapytań do modeli językowych według ich trudności.

Najprościej: mam dwa modele, mały i duży. Duży odpowiada lepiej, ale kosztuje więcej czasu i mocy obliczeniowej. Zbudowałem system, który czyta pytanie i, zanim ktokolwiek odpowie, wybiera, do którego modelu je wysłać. Działa jako nowa usługa w DeepFellow Infra.

Najpierw powiem, jaki jest problem i jak zmieniłem podejście do pracy. Potem pokażę, jak sprawdzam, czy pytanie jest trudne, jak działa system i jakie ma wyniki. Na końcu ograniczenia i jedna prośba o decyzję.

WARTO WIEDZIEĆ
Mały model to qwen3:8b, duży to Qwen3.8-27B. Liczby 8 i 27 to miliardy parametrów, czyli rozmiar modelu. Całość zajmie ok. 18–20 minut.`,

// 2
`MÓW
Duży model daje lepsze odpowiedzi, ale jest wolniejszy i potrzebuje mocniejszego sprzętu. Mały jest szybki, ale przy trudnych pytaniach bywa słaby.

Administrator ma dziś dwa wyjścia. Wszystko do dużego modelu: drogo. Wszystko do małego: gorsza jakość tam, gdzie była potrzebna.

Router ma wybierać osobno dla każdego pytania: proste do małego, trudne do dużego. Na rysunku pytanie wchodzi do routera i idzie w jedną z dwóch stron. Dla użytkownika nic się nie zmienia: w DeepFellow to po prostu model o nazwie router.

Trudność jest taka: router musi zdecydować, zanim jakikolwiek model odpowie. Widzi więc tylko treść pytania. Cała praca jest o tym, ile można o trudności pytania wywnioskować z samego jego tekstu.

Cel: jak najwięcej pytań do małego modelu przy prawie niezmienionej jakości.

JEŚLI ZAPYTAJĄ
Dlaczego nie zawsze duży model? Bo to najdroższe rozwiązanie. Pokażę, ile da się zaoszczędzić i jakim kosztem.`,

// 3
`MÓW
Zacznę od tego, jak wyglądała pierwsza wersja pracy.

Informację, że pytanie jest łatwe albo trudne, czyli etykietę, brałem z gotowych danych: z głosowań w Chatbot Arena, gdzie ludzie wybierają lepszą z dwóch odpowiedzi, oraz z pytań wygenerowanych przez Gemini.

Plan miał też trzy warstwy rozpoznawania trudności, konfigurację w pliku YAML, kategorie tematyczne i podział złożonych zadań na części (Map-Reduce). Odpowiedzi miałem oceniać między innymi miarą ROUGE.

ROUGE liczy, ile słów wspólnych ma odpowiedź modelu z odpowiedzią wzorcową. Zrezygnowałem z niej, bo zbieżność słów nie mówi, czy odpowiedź jest poprawna: dobra odpowiedź może być napisana innymi słowami, a zła może mieć wiele wspólnych.

To był rozsądny plan, bo opierał się na literaturze: znany system RouteLLM uczy się właśnie na głosach z Areny. Miał jednak jeden słaby punkt. Pokazuję go na następnym slajdzie.`,

// 4
`MÓW
Sprawdziłem, czy etykiety z Areny pasują do moich dwóch modeli.

Z Areny mam stare etykiety: pytanie jest „trudne”, jeśli w głosowaniu wygrał mocniejszy model. Dla moich dwóch modeli zmierzyłem osobno, o ile duży jest lepszy od małego na każdym pytaniu.

Porównałem jedno z drugim dla 1723 pytań. Wynik to 0,55. Znaczy to: biorę losowo dwa pytania, jedno trudne według Areny, drugie nie. W 55 przypadkach na 100 to pierwsze jest też trudniejsze dla moich modeli. Przy zwykłym rzucie monetą byłoby 50 na 100. Czyli zgodności prawie nie ma. Ta miara nazywa się AUROC i użyję jej później do oceny routera.

Dlaczego tak wyszło? Arena porównywała inne modele, z innej epoki. Gdy gpt-4 wygrywa ze słabym modelem, to zwykle bez względu na pytanie. Stara etykieta mówi więc więcej o różnicy między modelami niż o trudności pytania.

Wniosek: trudność zależy od konkretnej pary modeli. Dlatego sam ją mierzę na swoich dwóch modelach. Zaraz pokażę jak.

UWAGA
To jest analiza, a nie dowód, że moje etykiety są lepsze. Pokazuje tylko, że stare nie pasują do tych modeli.

JEŚLI ZAPYTAJĄ
Czy 0,55 to nie przypadek? Było 1723 pytań, a 0,55 jest bardzo blisko 0,5, więc wniosek jest ostrożny: stara etykieta słabo przewiduje wyniki naszych modeli.`,

// 5
`MÓW
Każde pytanie przechodzi cztery kroki.

Krok 1. Wysyłam je do obu modeli: do małego trzy razy, do dużego raz. Odpowiedzi modeli są losowe, więc jedna próbka małego modelu byłaby za mało pewna.

Krok 2. Oceniam odpowiedzi. Gdy znana jest poprawna odpowiedź, np. wynik zadania, sprawdza automat. W pozostałych przypadkach ocenia drugi model, Gemini, w skali od 1 do 5. Dostaje pytanie i wszystkie odpowiedzi w losowej kolejności i bez nazw modeli, żeby nikogo nie faworyzował.

Krok 3. Liczę różnicę: ocena dużego minus średnia ocena małego.

Krok 4. Jeśli różnica jest większa niż jeden punkt w skali 1–5, pytanie jest TRUDNE (COMPLEX), czyli duży jest wyraźnie lepszy. W przeciwnym razie jest ŁATWE (SIMPLE).

Przykład z rysunku. Duży dostał 5, mały 3, 3 i 4, średnio 3,3. Różnica to 1,7 punktu, więcej niż 1, więc pytanie jest trudne. Na slajdzie te oceny są przeliczone na skalę 0–1, stąd próg 0,25.

Jeśli oba modele odpowiedziały źle, pytanie zostaje łatwe, bo duży model nic by nie dał.

JEŚLI ZAPYTAJĄ
Dlaczego trzy próbki małego? Sprawdziłem, że jedna próbka dałaby tę samą klasę co wszystkie trzy tylko w 74% pytań otwartych. Średnia z trzech zmniejsza ten szum.
Skąd próg jeden punkt? To mój wybór. Sprawdziłem też łagodniejszy i ostrzejszy (odsetek trudnych pytań: 51,5%, 35,4% i 27,6%). Wnioski o routerze są te same.`,

// 6
`MÓW
Mam 4313 pytań z ośmiu źródeł. Dwa to zbiory prawdziwych rozmów z chatbotami: Arena i WildChat. Dalej pytania wygenerowane przez Gemini i zbiory z matematyki, wiedzy i programowania. Dzięki temu są i pytania otwarte, i takie ze znaną poprawną odpowiedzią.

Podzieliłem je na trzy części: 50% do nauki routera, 20% do dostrajania i 30% do końcowego testu. Test jest zamknięty: otworzę go raz, na końcu, żeby nie dopasować routera do testu.

Bardzo podobne pytania trafiają zawsze do jednej części. Inaczej router „znałby” pytania z testu, a wynik byłby zawyżony.

Wynik pomiaru: 35,4% pytań jest trudnych. Ale bardzo różnie zależnie od źródła: w zadaniach matematycznych 4%, w rozmowach z WildChat 48%. Mały model dobrze liczy, a rozmowy otwarte są dla niego trudniejsze. Czyli „trudne” nie zawsze znaczy to, co podpowiada intuicja.

JEŚLI ZAPYTAJĄ
Skąd te źródła? Chciałem mieszankę: prawdziwe, niejednoznaczne rozmowy oraz zadania, w których poprawność da się sprawdzić automatem.
Ograniczenie: to głównie publiczne czaty, więc brakuje zapytań z typowego użycia w firmie. Wracam do tego na końcu.`,

// 7
`MÓW
Etykiety ocenia model, więc sprawdziłem, ile można im ufać.

Pierwsza liczba: 90%. Gdy zmienię kolejność odpowiedzi, ten sam sędzia daje tę samą klasę w 90% pytań. Jest więc w miarę stabilny.

Druga: 79%. Drugi, mocniejszy sędzia zgadza się z pierwszym co do klasy w 79% pytań.

Trzecia: sam oceniłem 100 odpowiedzi, nie wiedząc, który model je napisał. Z sędzią zgadzam się umiarkowanie: korelacja 0,59, identyczna ocena w 43% przypadków, a różnica nie większa niż jeden punkt w 77%.

Czwarta: sędzia jest surowszy ode mnie średnio o 0,4 punktu.

Wniosek: etykiety są użyteczne, ale nie idealne, i tak je opisuję w pracy. To nie przekreśla wyników, bo etykieta opiera się na różnicy ocen dwóch modeli, więc stała surowość sędziego się znosi.

JEŚLI ZAPYTAJĄ
Czy sędzia nie faworyzuje długich odpowiedzi? Sprawdziłem: korelacja z długością to 0,06, czyli prawie żadna.
Który sędzia jest lepszy? Nie rozstrzygam. Używam tańszego, a drugi dostał tylko część pytań.`,

// 8
`MÓW
Router ma trzy warstwy, od najtańszej do najdroższej. Zasada: warstwa zostaje tylko wtedy, gdy pokaże zysk.

Warstwa 1: heurystyki, czyli punkty za proste cechy tekstu pytania. Pytanie dostaje plus jeden punkt za każdą frazę z listy zadań trudnych i minus jeden za każdą frazę z listy łatwych. Do tego plus jeden punkt, gdy jest dłuższe niż 400 znaków, kolejny plus jeden powyżej 1500, minus jeden, gdy ponad 10% znaków to cyfry, i plus jeden za adres internetowy. Wszystkie te punkty administrator może zmienić.

Skąd słowa kluczowe? Z literatury, a nie z moich danych, żeby ich nie dopasować do wyników. Pierwsze źródło to taksonomia Blooma (Anderson i Krathwohl, 2001): hierarchia poziomów myślenia, od zapamiętywania do tworzenia. Słowa z wyższych poziomów, jak „analyze”, „compare”, „evaluate”, „design”, „implement”, wskazują zadania trudniejsze. Słowa z niższych, jak „what is”, „define”, „name”, wskazują łatwiejsze. Drugie źródło to lista fraz z AgentBus, praktycznego systemu routingu modeli językowych: np. „debug”, „refactor”, „step by step”, „trade-offs”.

Jeśli suma punktów dojdzie do progu (domyślnie 2 punkty), pytanie idzie od razu do dużego modelu, bez liczenia embeddingu i bez warstwy 2. Poniżej progu decyduje warstwa 2. Ta warstwa kieruje tylko do dużego modelu, bo pomyłka w tę stronę kosztuje tylko pieniądze, a nie jakość. Próg można kalibrować: wyższy oznacza mniej pytań kierowanych od razu, ale większą pewność. U nas próg 2 punkty obejmuje 6% pytań, z których 52% jest naprawdę trudnych (wśród wszystkich pytań 37%). Próg 3 obejmuje 2% pytań, z czego 55% trudnych. W pomiarze takie kierowanie nie zmienia jakości całego routera (różnice do 0,003, bez wyraźnego wpływu). Warstwa jest opcjonalna: bez pliku z parametrami jest wyłączona.

Warstwa 2: porównanie z podobnymi pytaniami (metoda kNN). To główna część rozwiązania i wyjaśniam ją na następnym slajdzie.

Warstwa 3: mały model sam ocenia, czy pytanie jest trudne. Jeszcze jej nie ma. Wejdzie, jeśli krótki test pokaże zysk. Ten test nazywa się go/no-go: jeśli pomaga, budujemy, jeśli nie, rezygnujemy.

Na końcu router zwraca liczbę od 0 do 1. Administrator ustawia próg: wynik powyżej idzie do dużego modelu, poniżej do małego. Gdy cokolwiek zawiedzie, pytanie idzie do dużego, bo to bezpieczniejsze.

JEŚLI ZAPYTAJĄ
Ile to trwa? Reguły ok. 0,3 ms, a warstwa 2 ok. 20 ms. Warstwa 3 byłaby wywołaniem małego modelu, czyli sekundami, dlatego jest ostatnia.`,

// 9
`MÓW
Router dostaje tekst pytania, a ma zwrócić liczbę od 0 do 1. Robi to w czterech krokach.

Krok 1. Zamienia pytanie na liczby. Komputer nie potrafi porównać dwóch zdań, więc zamieniam każde na listę 768 liczb. To się nazywa embedding. Pytania o podobnym znaczeniu dostają podobne listy, jak punkty leżące blisko siebie na mapie.

Krok 2. Szuka 20 najbardziej podobnych pytań w mojej bazie, czyli takich, których trudność już zmierzyłem.

Krok 3. Sprawdza, ile z tych 20 było trudnych. Wynik to ten odsetek, a podobniejsze pytania liczą się bardziej. Jeśli 14 z 20 było trudnych, wynik jest wysoki i pytanie idzie do dużego modelu.

Krok 4. Porównuje wynik z progiem administratora.

Dlaczego tak, a nie bardziej skomplikowanie? Po pierwsze, nie trzeba niczego trenować: baza to zapisane pytania, a nowe dane to dopisanie wierszy. Po drugie, wynik ma zrozumiałe znaczenie i można pokazać, które pytania były sąsiadami. Po trzecie, liczy się lokalnie w ok. 20 ms, więc pytania nie opuszczają serwera. Po czwarte, sprawdziłem alternatywy: cztery inne modele zamieniające tekst na liczby i dziewięć klasyfikatorów. Żaden nie był istotnie lepszy. Najlepszy z nich jest trzy razy wolniejszy i bez wyraźnej poprawy.

JEŚLI ZAPYTAJĄ
Dlaczego 20 sąsiadów? Przy jednym wynik jest zaszumiony, od ok. 20 jest stabilny, a więcej nie poprawia.
Czy więcej danych pomoże? Niewiele: powyżej ok. 1200 pytań podwojenie bazy poprawia wynik o ok. 0,01.
Ograniczenie: model liczący wektory czyta do 2048 tokenów, więc dłuższe pytania liczy z samego początku.`,

// 10
`MÓW
Najpierw, jak mierzę jakość routera. Weź dwa losowe pytania: jedno naprawdę trudne, drugie łatwe. Czy router dał trudnemu wyższy wynik? Miara AUROC to odsetek takich par, w których tak. 0,5 oznacza zgadywanie, a 1,0 bezbłędny router. Mój router ma 0,682: w 68 parach na 100 ustawia je dobrze. To ta sama miara, której użyłem przy Arenie, tylko tam porównywałem dwie etykiety.

Druga miara to APGR: jaką część możliwego zysku jakości odzyskuję w porównaniu z wysyłaniem wszystkiego do małego modelu. 0,5 odpowiada losowemu wysyłaniu, a 0,91 idealnemu routerowi. Mój ma 0,605.

Wszystkie wyniki są policzone na pytaniach, których router wcześniej nie widział (3010 pytań, walidacja krzyżowa).

Słupki. Losowy ma 0,5. Sama długość pytania 0,525, czyli prawie nic nie mówi. „Samo źródło” 0,631: to router, który nie czyta pytania, tylko wie, z jakiego zbioru pochodzi (matematyka zwykle łatwa, rozmowy trudniejsze). To poprzeczka: czy router wie coś więcej niż rodzaj pytania. Wie, ale niewiele więcej: różnica to 0,05 w AUROC, istotna statystycznie.

Uczciwie: dużą część skuteczności daje samo rozpoznanie rodzaju pytania. Wewnątrz jednego źródła wynik jest słabszy: dla Areny 0,60, a dla pytań o wiedzę (TriviaQA) ok. 0,50, czyli nic.

JEŚLI ZAPYTAJĄ
Czy da się lepiej? Z samego tekstu raczej nie: różne metody dają podobny wynik. Potrzebny byłby inny sygnał, np. warstwa 3.`,

// 11
`MÓW
Jak czytać wykres. Oś pozioma to odsetek pytań wysyłanych do dużego modelu. Oś pionowa to średnia jakość odpowiedzi od 0 do 1. Wszystko do małego daje 0,625, wszystko do dużego 0,846. Szara linia to losowe wysyłanie, a pomarańczowa to router. Router jest wyżej: przy tym samym udziale dużego daje lepszą jakość. Przewaga jest umiarkowana, ok. 0,03.

Przykład: przy progu 0,3 do dużego idzie 54% pytań, a jakość to 0,777. To ok. 46% mniej wywołań dużego modelu za ok. 8% niższą jakość.

Tabela po prawej pokazuje, ile poważnych błędów akceptujemy. Poważny błąd to pytanie, na które duży model odpowiedziałby wyraźnie lepiej (o ponad 2 punkty), a które poszło do małego. Takich pytań jest 15,9% wszystkich.

Czytam tak. Jeśli akceptuję do 12% poważnych błędów wśród pytań wysłanych do małego, do małego idzie 47% pytań. Przy 10% idzie 22%, przy 15% aż 90%. Poniżej ok. 8% żaden próg nie daje gwarancji z 95% pewnością. Router zmniejsza ryzyko, ale go nie usuwa.

Dlaczego tak? Administratorowi łatwiej wybrać „akceptuję do 12% pomyłek” niż liczbę 0,3.

JEŚLI ZAPYTAJĄ
Jak liczone? Próg wyznaczam na jednej części danych, a sprawdzam na drugiej. Pewność 95% liczę metodą Clopper–Pearsona.
Czy 46% oszczędności jest warte 8% jakości? To zależy od administratora, dlatego to on wybiera próg.`,

// 12
`MÓW
Poważny błąd to pytanie, na które duży model byłby wyraźnie lepszy, a router wysłał je do małego. Przy progu 0,3 router pomija 30% takich pytań. Losowo byłoby 46%.

Wykres pokazuje, gdzie myli się najbardziej. Dla pytań otwartych, Areny i WildChat, pomija 25% i 17% takich pytań. Dla pytań o fakty (TriviaQA) aż 81%, a dla zadań programistycznych (HumanEval) 84%.

Dlaczego? Router widzi tylko tekst pytania, a nie to, co wie mały model. Dwa pytania o fakty wyglądają podobnie, ale mały model może znać odpowiedź na jedno i nie znać drugiej. W tekście tego nie widać.

Przy programowaniu tylko 18% zadań jest trudnych. Sąsiedzi nowego zadania są więc zwykle łatwi, wynik jest niski i zadanie idzie do małego. Te trudne wyglądają tak samo jak łatwe.

To nie jest błąd metody, tylko brak informacji w samym tekście. Dlatego rozważam warstwę 3: może sam mały model „czuje”, czy da radę. To hipoteza do sprawdzenia, a nie obietnica.

UWAGA
Próbki są małe: 42 pytania z TriviaQA i 19 z HumanEval. Wnioski ostrożnie.

JEŚLI ZAPYTAJĄ
Czemu zadania z kodu nie są częściej trudne? Mały model rozwiązuje 83% zadań, duży 94%. Różnica jest niewielka.`,

// 13
`MÓW
Implementacja. Usługa RouterService działa w DeepFellow. Napisałem 57 nowych testów, a cały zestaw testów przechodzi. Sprawdziłem ją od początku do końca na osobnej instancji z modelami Gemini: wybór modelu, nagłówki z decyzją, strumieniowanie i przełączenie na duży model przy błędzie. Test wykrył błąd: wycofany model zwracał 404 jako zwykłą odpowiedź i omijał to przełączenie. Naprawiłem. Z modelami Qwen jeszcze nie uruchamiałem. Zrobię to na komputerze służbowym.

Sprawdziłem też dwie rzeczy. Czas: mediana ok. 20 ms, a 90% zapytań w mniej niż 65 ms (cel poniżej 50 ms spełniony dla mediany). Odporność: po literówkach, parafrazach i zamianie na synonimy decyzja zmienia się tylko w 6–10% pytań. Losowo byłoby 42–48%. Router nie jest więc wrażliwy na drobne zmiany sformułowania.

Ograniczenia, które nazywam wprost. Jedna para modeli. Jeden sędzia, a zgodność z człowiekiem jest umiarkowana. Duży model ma jedną próbkę na pytanie. Dane są mało „firmowe”: 63% to publiczne czaty. Wiedza i kod są słabo wykrywane. Warstwa 1 (heurystyki) jest na naszych danych słaba (AUROC ok. 0,55), dlatego jest opcjonalna. Możliwe, że na danych firmowych wypadnie lepiej, ale to hipoteza do sprawdzenia.

JEŚLI ZAPYTAJĄ
Czy zadziała na innych modelach? Router tak, ale etykiety trzeba zmierzyć od nowa: ok. 1,5 doby generowania i ok. 8 USD za sędziego.`,

// 14
`MÓW
Co dalej. Po pierwsze, uruchomić system z modelami Qwen na komputerze służbowym i zmierzyć opóźnienie przez DeepFellow. Po drugie, sprawdzić warstwę 3 (test go/no-go): czy mały model oceniający pytanie poprawia wynik routera. Po trzecie, dodać dane bliższe wdrożeniu, np. własne zapytania, zadania SQL, polecenia biurowe. To wymaga ponownego pomiaru, ale pozwoli też sprawdzić, czy heurystyki warstwy 1 działają lepiej na takich danych. Po czwarte, otworzyć zbiór testowy raz i zrobić ocenę końcową.

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
