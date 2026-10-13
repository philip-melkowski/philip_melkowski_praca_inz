# Dziennik prac i decyzji

Każdy krok i decyzja dopisywane na bieżąco (najnowsze na dole). Obowiązujący plan: `../../koncepcja.md`.

## 2026-10-13

### 1. Przyjęcie nowego planu i archiwizacja starych
- Decyzja: nowy plan (router oparty na zmierzonej różnicy jakości, artefakt https://claude.ai/artifact/XZ71pUD3iWFG8ARaHg8jLL) jest obowiązujący.
- Stare plany przeniesione (nic nie usunięto) do `archiwum/v1/`: `koncepcja.md/.pdf`, `STAGES.md`, `router_notes.md/.pdf`, dawne `CLAUDE.md`.
- Nowa `koncepcja.md` w katalogu głównym; zaktualizowane oba `CLAUDE.md` i pamięć asystenta.

### 2. Porządek w klonach DeepFellow
- Były trzy kopie: `kod/deepfellow-infra` (v0.34.0), `deepfellow-router/deepfellow-infra` (v0.28.0, 291 commitów za), `inz/deepfellow-infra` (ok. v0.24.2).
- Decyzja: zostaje tylko `kod/deepfellow-infra`. Dwie stare usunięte; wcześniej sprawdzone: brak niezapushowanych commitów i stashy. Nieśledzone pliki starszej kopii (`dedup.py`, `plans/`) skopiowane do `archiwum/v1/stary-klon/`.

### 3. Zbieranie pytań
- Skrypt `data/collect_questions.py` → `data/datasets/questions_v2.jsonl`. Źródła: Arena (z istniejących plików), pytania Gemini (450 z 900), WildChat, TriviaQA, GSM8K, MMLU, HumanEval, MT-Bench. Filtry: 16–1500 tokenów (tiktoken), deduplikacja dokładna.
- Licencje sprawdzone na Hugging Face (metadane): WildChat ODC-By, GSM8K/MMLU/HumanEval MIT, MT-Bench Apache 2.0, TriviaQA bez licencji (opisać w ograniczeniach). LMSYS-Chat-1M odrzucony (wymaga zgody).
- Błędy po drodze i poprawki: (a) `splitlines()` przecinało wiersze z Areny, czytanie linia po linii; (b) plik pytań Gemini ma pole `query`, nie `prompt`.
- Problem: pierwsza próbka WildChat zdominowana przez szablony (Midjourney) i zawierała niedozwolone treści mimo flagi `toxic`. Poprawka: odrzucanie pytań z `openai_moderation.flagged`, `detoxify` toksyczność/seksualność > 0,1 oraz jedno pytanie na szablon (pierwsze 80 znaków). Po poprawce 1000 pytań WildChat, mediana 66 tokenów. Pozostaje dużo fan-fiction (rozkład zbioru); dalsze usuwanie podobnych przez embeddingi.

### 4. Magazyn DeepFellow i Docker
- Błąd instalacji Ollamy: `mkdir /host_mnt/.../Desktop: operation not permitted` (Docker Desktop nie ma dostępu do `Desktop`).
- Przyczyna: w `.env` była zmienna `DF_INFRA_STORAGE_DIR`, a DF czyta `DF_STORAGE_DIR`, więc używał katalogu domyślnego pod `Desktop`.
- Decyzja: `DF_STORAGE_DIR=/Users/melkowskiphilip/df-storage` (poza chronionymi katalogami macOS).

### 5. Wybór modelu embeddingowego i sposobu uruchomienia
- Wymagania: lokalnie, szybko (cel < 50 ms dla warstw 1+2), okno pokrywające nasze pytania.
- Zmierzone (25 pytań, M1 8 GB): `qwen3-embedding:0.6b` 1217 ms (okno 4096 po ustawieniu w DF), `nomic-embed-text` w Ollamie w Dockerze 196–242 ms (okno 2048).
- Okno nomic: 2048 tokenów to rodzimy limit tej wersji w Ollamie; `OLLAMA_CONTEXT_LENGTH=4096` w DF nie podnosi go dla tego modelu (sprawdzone logiem `n_ctx_slot` i testem ucięcia). Qwen3 z ustawieniem 4096 w DF faktycznie ma 4096 (model-level 8192 nie zadziałał).
- Decyzja: model `nomic-embed-text` z prefiksem `classification: `.

### 6. Usunięcie pytań ponad limitem embeddingu
- Decyzja: z bazy usuwamy pytania, które nie mieszczą się w oknie nomica. Skrypt `data/filter_embed_limit.py` sprawdza tokeny nomic (`usage.prompt_tokens`) dla pytań ≥ 600 tokenów tiktoken (69 pytań).
- Wynik: usunięte 1 pytanie (`wildchat-02975`), zostało 4313. Zapisane w `data/datasets/removed_too_long.jsonl`; kopia sprzed filtra: `questions_v2.before_filter.jsonl`. Opis: `docs/stage1/decisions/EMBED_LIMIT.md`.

### 7. Ollama w Dockerze vs `ollama-external` vs Docker Model Runner
- **Ollama w Dockerze (usługa `ollama` w DF):** na macOS kontenery nie mają dostępu do GPU Apple, liczy na procesorze; 196–242 ms na pytanie. Odrzucona dla embeddingów.
- **Docker Model Runner (usługa `docker-model-runner`, `ai/nomic-embed-text-v1.5`, llama.cpp-Metal):** po włączeniu TCP (port 12434) DF widział model, ale każde zapytanie kończyło się `inference backend took too long to initialize` (5 prób, brak przyczyny w logu; podejrzenie presji pamięci 8 GB, niepotwierdzone). Odrzucona na tym komputerze.
- **Natywna Ollama + usługa DF `ollama-external` (wybrana):** `brew install ollama`, port 11434, w DF URL `http://localhost:11434`, sync interval 60 s. Używa Metala. Pomiar bezpośredni 33 ms/pytanie; przez DF (100 pytań): średnio 22 ms, p50 17 ms, p90 36 ms, max 97 ms. Cel 50 ms spełniony dla samego embeddingu.
- Wymaga uruchomionej Ollamy (`ollama serve`; trwale: `brew services start ollama`). Ollamę z Dockera usunięto z DF, żeby uniknąć konfliktu nazw modeli.
- To samo okno kontekstu: 2048 tokenów, ten sam model (ID `0a109f422b47`).

### 8. Embeddingi wszystkich pytań
- Skrypt `data/embed_questions.py` → `data/datasets/embeddings_nomic.npy` (4313 × 768, znormalizowane). Model `nomic-embed-text`, prefiks `classification: `, przez DF + natywna Ollama. Czas: ok. 93 s.
- Rozkład podobieństwa do najbliższego sąsiada: mediana 0,768, p90 0,931, p99 0,993. Pytań z sąsiadem ≥ 0,95: 323 (121 Arena, 158 WildChat, 24 Gemini, 16 MMLU, 4 HumanEval). Pary w okolicy 0,95 to faktyczne prawie-duplikaty (różnica jednego słowa); w okolicy 0,90 to już pytania z tego samego szablonu, ale różne. Próg 0,95 z RouteLLM zostaje.

### 9. Podział na zbiory: grupy zamiast usuwania z testu
- Decyzja (zmiana względem planu „usuwamy z testu pytania podobne do uczących"): pytania połączone podobieństwem ≥ 0,95 tworzą grupy (139 grup, 323 pytania, największa 16, MMLU) i **cała grupa trafia do jednego zbioru**. Dzięki temu żadne pytanie nie jest usuwane, a prawie-duplikaty nie przeciekają między uczeniem a testem. Wynik: 0 grup rozdzielonych.
- Reguły: MMLU (300) i MT-Bench (78) w całości do testu; z GSM8K 150 losowych do testu poza dziedziną (flaga `ood`); reszta losowo po grupach, stratyfikowana po źródle (ziarno 42), tak by całość wyszła 50/20/30.
- Skrypt `data/make_split.py` → `data/datasets/questions_v2_split.jsonl` (pola `group`, `split`, `ood`).
- Wynik: train 2157, cal 862, test 1294. Test: 721 pytań otwartych i 573 z poprawną odpowiedzią. Źródła w teście: Arena 349, MMLU 300, WildChat 202, GSM8K 180 (150 poza dziedziną + 30 z podziału), Gemini 92, MT-Bench 78, TriviaQA 60, HumanEval 33.
- Zbiór testowy uznajemy za zamknięty: odpowiedzi modeli dla niego generujemy, ale nie analizujemy ich w trakcie budowy routera.

### 10. Skrypt generowania odpowiedzi (do uruchomienia na komputerze z dostępem do modeli)
- `data/generate_answers.py`: samodzielny (zależność `httpx` przez nagłówek `uv`), woła `/v1/chat/completions` na wskazanej instancji DF, zapisuje `answers.jsonl` (pola: `id`, `model`, `sample`, `content`, `finish_reason`, `usage`, `seconds`), wznawialny (pomija wykonane trójki id/model/sample), błędne wywołania nie są zapisywane.
- Parametry protokołu pomiaru (do ustalenia i zapisania przed pełnym pomiarem): mały model 3 próbki, duży 1; temperatura 0,7 dla obu (żeby próbki małego się różniły); jednakowy `max_tokens` 1024 dla obu; bez promptu systemowego.
- Dopiski formatu odpowiedzi tylko dla pytań ze znaną odpowiedzią (jednakowe dla obu modeli): GSM8K „Answer: <number>”, TriviaQA „krótka fraza”, HumanEval „pełna funkcja w bloku kodu”. MMLU ma instrukcję w treści pytania.
- Modele „myślące” (np. Qwen3): wyłączenie myślenia przez `--extra-body '{"chat_template_kwargs":{"enable_thinking":false}}'` (zależne od serwera, do sprawdzenia).
- Test na atrapie serwera: 6 pytań × (3+1) = 24 odpowiedzi zapisane, ponowne uruchomienie nic nie dublowało.
- Pliki do przeniesienia na drugi komputer: `do_przeniesienia/` (skrypt + `questions_v2_split.jsonl`).
