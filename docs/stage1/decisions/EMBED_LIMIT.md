# Limit długości pytań wynikający z modelu embeddingowego

Data: 2026-10-13

## Decyzja
Embeddingi liczy `nomic-embed-text` (Ollama w DeepFellow v0.34.0) z prefiksem `classification: `. Pytania, które nie mieszczą się w oknie modelu, są usuwane z bazy pytań.

## Powód
- Okno nomic-embed-text w Ollamie to 2048 tokenów (`ollama show`: `context length 2048`; log serwera: `n_ctx_slot = 2048`). `OLLAMA_CONTEXT_LENGTH=4096` ustawione w DF nie podnosi limitu, bo to rodzimy limit tego modelu w tej wersji.
- Dłuższe pytania miałyby embedding policzony tylko z początku, co zniekształcałoby kNN, klastry i usuwanie duplikatów.
- Rozważone: `qwen3-embedding:0.6b` (okno 4096 po ustawieniu w DF), ale ok. 1217 ms na pytanie wobec ok. 196 ms dla nomic (pomiar na 25 pytaniach, procesor w Dockerze na macOS). Cel opóźnienia routera (< 50 ms dla warstw 1+2) wykluczył wolniejszy model.

## Co zrobiono
`data/filter_embed_limit.py` sprawdza przez `/v1/embeddings` liczbę tokenów nomic (`usage.prompt_tokens`) dla pytań o co najmniej 600 tokenach tiktoken (69 pytań) i usuwa te, dla których liczba ≥ 2047 (okno wypełnione, czyli tekst ucięty).

Wynik: usunięte 1 pytanie z 4314 (`wildchat-02975`, 1467 tokenów tiktoken), zostało 4313. Usunięte pytanie jest w `data/datasets/removed_too_long.jsonl`, stan sprzed filtra w `data/datasets/questions_v2.before_filter.jsonl`.

## Konsekwencje i ograniczenia
- Baza pomija pytania dłuższe niż ok. 2000 tokenów; router w produkcji dostałby je i embedding byłby liczony tylko z początku. Opisać w ograniczeniach pracy.
- Opóźnienie: cel < 50 ms dla warstw 1+2. Pomiar na MacBooku M1 8 GB przez DF (`/v1/embeddings`, 100 prawdziwych pytań, po rozgrzaniu): średnio 22 ms, p50 17 ms, p90 36 ms, max 97 ms, co mieści się w celu. Dotyczy tylko embeddingu, bez warstw 1 i 2.
- Konfiguracja: natywna Ollama na macOS (Metal, `brew install ollama`, port 11434) podpięta w DF jako usługa `ollama-external` (`http://localhost:11434`). Ollama w Dockerze na macOS nie ma dostępu do GPU i dawała ok. 196–242 ms. Docker Model Runner (`ai/nomic-embed-text-v1.5`, llama.cpp-Metal) nie uruchomił modelu na tym komputerze (`inference backend took too long to initialize`).
- Ten sam model i prefiks muszą być używane w całym projekcie (indeks i produkcja).
