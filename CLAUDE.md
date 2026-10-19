# CLAUDE.md — deepfellow-router

Praca inżynierska: dynamiczny i semantyczny routing zapytań LLM według złożoności, zintegrowany z DeepFellow Infra jako `RouterService`.

## Source of truth

- **Obowiązujący plan:** `../koncepcja.md` (wersja tekstowa artefaktu https://claude.ai/artifact/XZ71pUD3iWFG8ARaHg8jLL) — przy rozbieżności wygrywa ten plik.
- **Stare plany (nieobowiązujące, nie usuwać):** `archiwum/v1/` (koncepcja, STAGES, router_notes, dawne CLAUDE.md).
- **Raporty z przygotowania danych:** `docs/stage1/`; analizy długości i słów: `docs/stage2/` (do powtórzenia na zmierzonych etykietach).
- **Literatura:** `docs/references/`

Nie duplikuj treści z `koncepcja.md` w innych plikach — linkuj.

## Kluczowe fakty

- Dwie klasy: SIMPLE / COMPLEX. Etykieta jest zmierzona: Δ = jakość dużego − średnia jakość małego (3 próbki), COMPLEX gdy Δ > 0,25. Ocena: sędzia Gemini (pytania otwarte) lub automatycznie (pytania z poprawną odpowiedzią).
- Router: warstwa 1 reguły → warstwa 2 kNN/klastry na embeddingach → opcjonalnie warstwa 3 (mały model zero-shot, po teście go/no-go). Wynik 0–1 vs próg; awaria → duży model.
- Para modeli jest parametrem (duży ok. 27B z DF, mały ok. 8B). Kategorie tylko do analizy, bez Map-Reduce w rdzeniu.
- Konfiguracja jako opcje serwisu DF (JSON), nie YAML. Integracja: `RouterService` (`Base2Service`), wywołania in-process przez `EndpointRegistry`. DF: `../kod/deepfellow-infra` (v0.34.0).
- Dane: nowy zbiór (Arena, Gemini, czaty, TriviaQA/NQ, GSM8K, MMLU, HumanEval, MT-Bench), nowy podział 50/20/30, test zamknięty, otwierany raz. Dawny podział i dawne etykiety nie obowiązują.
- Metryki: PGR, APGR, CPT, punkty odniesienia, bootstrap.

## Stack

Python 3.13, `uv`, strict pyright, tiktoken (cl100k_base).

## Struktura

```
archiwum/v1/         # stare plany
data/                # skrypty i datasety
eval/                # analizy i kalibracja
docs/                # raporty, literatura
```

## Potok i skrypty (stan 2026-10-19)

Dziennik wszystkich kroków i decyzji: `docs/DZIENNIK.md` (dopisywać na bieżąco, w tym odrzucone opcje). Podsumowanie wyników: `docs/POSTEPY_2026-10-19.md`; uruchomienie routera: `docs/ROUTER_URUCHOMIENIE.md`; cele przed testem: `docs/CELE_PRZED_TESTEM.md`.

- `data/`: `collect_questions.py` → `embed_questions.py` (nomic przez DF) → `make_split.py` → `generate_answers.py` (uruchamiany na komputerze z modelami) → `score_gold.py` (ocena automatyczna) + `judge_open.py` (sędzia Gemini, klucz w `~/.config/inz/gemini_key`) → `make_labels.py` (`labels.jsonl`). Zbiory w `data/datasets/` nie są w gicie.
- `eval/`: `label_analysis.py`, `router_baselines.py`, `router_layers.py`, `router_extra.py`, `router_cv.py`, `router_models.py`, `embedder_compare.py`, `robustness_generate.py` + `robustness_eval.py`, `latency.py`, `threshold_table.py`, `export_index.py` (indeks dla DF), `layer3_probe.py` + `layer3_eval.py`, wykresy `plot_*.py`.
- **Zbiór `test` jest zamknięty**: nie używać go do strojenia ani wyboru; strojenie tylko walidacją krzyżową po grupach na train (i cal).
- Płatne wywołania API (Gemini): tylko po zgodzie użytkownika na konkretny wydatek.
- Komendy skryptów z nagłówkiem `# /// script` uruchamiać przez `uv run <plik>`; systemowy `python3` jest za stary (użyć `uv run --python 3.13`).

Framework DeepFellow: tylko `../kod/deepfellow-infra`. Stare klony usunięto 2026-10-13 (nieśledzone pliki z jednego z nich: `archiwum/v1/stary-klon/`).
