# Start na komputerze służbowym: test warstwy 3 (modele decyzyjne)

Notatka dla Claude'a uruchomionego na komputerze służbowym autora (inne konto Claude, bez historii rozmowy). Przeczytaj ją najpierw, potem `CLAUDE.md` w katalogu głównym repozytorium i końcówkę `docs/DZIENNIK.md` (wpisy 79 i późniejsze).

## 0. Układ katalogów na tym komputerze (inny niż w `CLAUDE.md`)

Na komputerze służbowym jest katalog `inz/`, a w nim **osobno**:

- `inz/philip_melkowski_praca_inz/`: repozytorium pracy (na prywatnym komputerze nazywa się `deepfellow-router`; to ten sam projekt, fork `philip-melkowski/philip_melkowski_praca_inz`). Tu pracujesz.
- `inz/deepfellow-infra/`: klon DeepFellow Infra (na prywatnym komputerze: `kod/deepfellow-infra`).

Ścieżki w `CLAUDE.md` (`../koncepcja.md`, `../kod/deepfellow-infra`) **tu nie zadziałają**. Plik `koncepcja.md` leży poza repozytorium i nie jest w gitcie (w repo jest tylko stara wersja `archiwum/v1/koncepcja.md`, nieobowiązująca). Aktualny plan jest w artefakcie https://claude.ai/artifact/XZ71pUD3iWFG8ARaHg8jLL; jeśli go nie widzisz, poproś autora o wklejenie albo skopiowanie `koncepcja.md` do `inz/`. Do samego testu warstwy 3 wystarczy ta notatka i `docs/WARSTWA3_propozycja.md`.

## 1. Projekt w trzech zdaniach

Praca inżynierska: `RouterService` w DeepFellow Infra kieruje każde zapytanie do małego modelu (`qwen3:8b`) albo dużego (`Qwen/Qwen3.8-27B-FP8`). Router to kaskada: warstwa 1 reguły, warstwa 2 kNN na embeddingach (`nomic-embed-text`), warstwa 3 opcjonalna (sędzia w strefie niepewności), awaria zawsze kieruje do dużego modelu. Plan: `../koncepcja.md` (przy rozbieżności wygrywa).

## 2. Na czym stanęło

- Etykiety zmierzone: Δ = jakość dużego − średnia jakość małego (3 próbki); COMPLEX gdy Δ > 0,25 (35,4% z 4304 pytań).
- Warstwa 2 (kNN, k=20, próg 0,3): **AUROC 0,682**, APGR 0,605 (3010 pytań train+cal, walidacja krzyżowa po grupach). Sufit dla samych embeddingów to ok. 0,68–0,69; krzywa uczenia płaska. Warstwa 1 sama: AUROC ok. 0,555.
- Warstwa 3 **nie jest zaimplementowana**. Jest propozycja `docs/WARSTWA3_propozycja.md` (warianty A–E, cele G1–G8) i skrypty `eval/layer3_probe.py` + `eval/layer3_eval.py` (sprawdzone tylko na danych syntetycznych).
- Zbiór `test` jest **zamknięty**: nie używać do strojenia ani wyboru. Strojenie tylko walidacją krzyżową po grupach na train (i cal).

## 3. Co chcemy teraz sprawdzić (test go/no-go)

Pytanie: czy model decyzyjny (zwraca prawdopodobieństwa zamiast tekstu) niesie informację o trudności pytania **ponad** kNN (AUROC 0,682)?

Model decyzyjny dostaje pytanie jako `state` i serię typowanych pytań, np. czy potrzeba rzadkiej wiedzy, czy rozumowanie wieloetapowe, czy długa odpowiedź, czy kod. Odpowiedzi (prawdopodobieństwa) są cechami; łączymy je z wynikiem kNN regresją logistyczną i liczymy zysk AUROC w walidacji krzyżowej po grupach z przedziałem ufności (bootstrap).

- **Go**: przedział zysku AUROC nie obejmuje zera (cel G1) oraz poprawa jakości przy tym samym koszcie albo brak gorszych poważnych błędów (G2/G3). **No-go**: przedział obejmuje zero.
- Zestaw pytań do modelu **zamrozić przed uruchomieniem** i zapisać w dzienniku; nie dobierać go po obejrzeniu wyników.
- Zero-shot „czy to trudne” prawdopodobnie tylko powtarza heurystyki (hipoteza autora/asystenta, niesprawdzona); dlatego cechy z kilku pytań.

### Modele

- **nimble** (Bespoke, 9B, Apache 2.0): autor ma do niego dostęp przez Ollamę. Zacznij od niego.
- Qweny `qwen3:8b` i `Qwen/Qwen3.8-27B-FP8` dostępne na tym komputerze (warianty A/B z propozycji: odczyt prawdopodobieństw SIMPLE/COMPLEX; wymaga logprobs, patrz niżej).
- Później (po zgodzie admina): `pplx-decider` (27B, Perplexity, HF `perplexity-ai/pplx-decider-v1.2`, w Ollamie 17 GB), `clef-flash`, `basal-2.0-max` (osobny serwer `basal-serve`). Prośba do admina: `~/Desktop/DLA_ADMINA_modele_decyzyjne.txt` na komputerze prywatnym autora, nie w repozytorium.
- Test ma być na modelu, który realnie moglibyśmy wdrożyć; skrypt ma więc przyjmować nazwę modelu jako parametr i dać się powtórzyć dla każdego kandydata.

## 4. Techniczne: endpoint `/v1/systemone`

Ollama od 0.35.0 (część modeli od 0.35.1) ma `POST /v1/systemone`:

```json
{"model": "nimble", "state": "<pytanie>", "questions": {"nazwa": {"type": "noul", "instructions": "...", "criteria": {"true": "...", "false": "..."}}}}
```

- Typy pytań: `noul` (tak/nie, P(true)), `choice` (2–26 opcji), `score` (poziomy uporządkowane). Do 64 pytań w jednym żądaniu, limit 64 KiB, bez streamingu.
- Odpowiedź: `answers.<nazwa>` z `probabilities` i `confidence` (to ostrość rozkładu, nie skalibrowana poprawność).
- Ollama wybiera kodowanie promptu po metadanych GGUF; **basal nie ma kodowania w Ollamie** (issue ollama/ollama#18760), więc działa tylko przez własny `basal-serve` (ten sam schemat, bez pola `model`).
- Sprawdź wersję: `ollama --version`, i czy endpoint odpowiada: `curl localhost:11434/v1/systemone ...` (przykład w kartach modeli na ollama.com).
- DeepFellow (nasza gałąź i upstream 0.36.0) **nie ma jeszcze** endpointu `systemone`; podobno jest dodawany. Na razie wołaj Ollamę bezpośrednio, DF nie jest potrzebny do testu.
- `ChatCompletionRequest` w DF nie ma `logprobs`; dla wariantów A/B użyj natywnego `/api/chat` Ollamy albo `/v1/completions` (tak robi `eval/layer3_probe.py`).

## 5. Dane (ważne)

Katalog `data/datasets/` **nie jest w gitcie** (pytania, etykiety, embeddingi). Potrzebne pliki: `questions_v2_split.jsonl`, `labels.jsonl`, `embeddings_nomic.npy`. Autor musi je skopiować na ten komputer (albo uruchamiasz skrypt na prywatnym komputerze, wołając modele z tego przez tunel SSH). Nie wysyłaj tych danych do zewnętrznych usług i nie commituj ich.

## 6. Zasady pracy z autorem

- Odpowiadaj **po polsku, prosto**, krok po kroku.
- Gdy autor zadaje **pytanie**, tylko odpowiedz; nie zmieniaj plików ani planu bez wyraźnej prośby. Zmiany planu/architektury najpierw zaproponuj i zapisz.
- **Sprawdzaj od razu**, co da się zweryfikować (pliki, liczby, dokumentacja w sieci). Nie kwestionuj słów autora bez sprawdzenia.
- Każdy krok i decyzję zapisuj w `docs/DZIENNIK.md` (ostatni wpis ma numer 80; dopisuj kolejne), propozycje oznaczaj jako własne asystenta.
- Płatne wywołania API (Gemini, Jev w chmurze) tylko po zgodzie autora na konkretny wydatek. Klucz Gemini jest tylko w `~/.config/inz/gemini_key` (na tym komputerze go nie ma i nie jest potrzebny).
- Nic nie usuwaj bez pytania. Commit i push tylko na prośbę, push tylko do `origin` (fork `philip-melkowski/philip_melkowski_praca_inz`).
- Stack: Python 3.13, `uv` (`uv run --python 3.13 plik.py`), strict pyright; skrypty mają nagłówek `# /// script`.
- Pliku Keynote (`~/Desktop/prezentacja_postepy.key`) tu nie ma i nie ruszamy go.

## 7. Proponowany pierwszy krok

1. Sprawdź, co jest na komputerze: `ollama --version`, `ollama list`, czy `nimble` jest pobrany, czy endpoint odpowiada (jedno zapytanie testowe `noul`).
2. Zapytaj autora o dane z punktu 5 i o to, czy wolno użyć obu Qwenów jako modeli pomocniczych.
3. Zaproponuj (nie zakładaj) zestaw 5–8 pytań typowanych i skrypt `eval/layer3_systemone.py` z parametrem `--model`, wznawianiem (jak `layer3_probe.py`) i oceną zysku AUROC nad kNN. Uzgodnij z autorem, zapisz w dzienniku, dopiero wtedy uruchom.
