# Philip Melkowski, praca inżynierska

Dynamiczny i semantyczny routing zapytań LLM według złożoności zadania: `RouterService` w DeepFellow Infra wybiera dla każdego zapytania mały (`qwen3:8b`) albo duży (`Qwen/Qwen3.8-27B-FP8`) model. Etykiety trudności są zmierzone na odpowiedziach obu modeli; router to kaskada heurystyk, kNN na embeddingach i opcjonalnego modelu decyzyjnego.

Gdzie czego szukać:

- `docs/STATUS.md`: aktualny stan prac i następne kroki (zacznij tutaj)
- `docs/INDEX.md`: mapa wszystkich dokumentów
- `docs/KONCEPCJA.md`: plan pracy; `docs/DECYZJE.md`: co z niego obowiązuje i co zmieniono
- `docs/DZIENNIK.md`: chronologia kroków i decyzji
- `data/`, `eval/`: skrypty pomiaru i analiz (`README.md` w każdym katalogu); zbiory danych nie są w repozytorium
- `CLAUDE.md`: zasady pracy dla agentów AI

Skrypty: Python 3.13, `uv run --python 3.13 <plik>`.
