# data/: skrypty i zbiory

`data/datasets/` jest w `.gitignore` (pytania, odpowiedzi, etykiety, embeddingi). Do gita trafiają tylko skrypty, `router_l1.json` (frazy warstwy 1) i `router/router_index_train_cal.npz` (indeks kNN: wektory i etykiety 0/1, bez treści pytań). Kto nie ma `data/datasets/`, musi skopiować pliki z komputera, na którym powstały (stan i lokalizacje: `docs/STATUS.md`, „Dwa komputery”). Nie wysyłaj ich do zewnętrznych usług.

Liczby w nawiasach `W…` to wpisy `docs/DZIENNIK.md`, w których skrypt powstał lub został opisany.

## Potok pomiaru (kolejność uruchamiania)

| Krok | Skrypt | Wejście → wyjście (`data/datasets/`) | Uwagi |
|---|---|---|---|
| 1 | `collect_questions.py` (W3) | źródła (Arena, Gemini, czaty, TriviaQA, GSM8K, MMLU, HumanEval, MT-Bench) → `questions_v2.jsonl` | filtry długości 16–1500 tokenów (cl100k) |
| 2 | `filter_embed_limit.py` (W6) | `questions_v2.jsonl` → ten sam plik, usunięte do `removed_too_long.jsonl` | okno embeddingu 2048 tokenów (`docs/stage1/decisions/EMBED_LIMIT.md`) |
| 3 | `embed_questions.py` (W8) | → `embeddings_nomic.npy` (4313×768) | `nomic-embed-text` przez DF, prefiks `classification: ` |
| 4 | `make_split.py` (W9) | → `questions_v2_split.jsonl` | train/cal/test ok. 50/20/30, grupy prawie-duplikatów razem |
| 5 | `generate_answers.py` (W10) | → `answers.jsonl` | **na komputerze z dostępem do modeli**; mały 3×, duży 1×; wznawialny |
| 6a | `score_gold.py` (W15) | → `scores_gold.jsonl` | ocena automatyczna pytań ze znaną odpowiedzią |
| 6b | `judge_open.py` (W16–17) | → `judge_open.jsonl` (+ `judge_open_pro.jsonl`, `judge_open_rerun.jsonl`) | sędzia Gemini, **płatne**; klucz w `~/.config/inz/gemini_key` |
| 7 | `make_labels.py` (W17) | → `labels.jsonl` | Δ i klasa COMPLEX/SIMPLE (próg 0,25) |

## Nowe pytania i ponowne generowanie (wpisy 105–109)

| Skrypt | Do czego |
|---|---|
| `collect_extra.py` (W105) | 1500 dodatkowych pytań (Dolly, CodeChat, Arena 140k) → `questions_extra.jsonl` (`split = extra`) |
| `run_extra_large.sh`, `run_extra_small.sh` (W105) | odpowiedzi dużego i małego na nowe pytania → `answers_extra.jsonl`, `answers_extra_small.jsonl` |
| `rerun_truncated.py` (W106) | ponowne generowanie uciętych z limitem 4096 → `answers_rerun4096.jsonl` (oryginały bez zmian), wznawialny |

Pliki z tej tabeli i `layer3_systemone_*.jsonl` (wyniki warstwy 3) powstały na komputerze służbowym; po scaleniu z `answers.jsonl` (komputer prywatny) trzeba ocenić nowe i zmienione odpowiedzi sędzią (**płatne, tylko za zgodą autora na kwotę**) i policzyć etykiety.

## Pliki w `data/datasets/` (komputer prywatny)

| Plik | Co zawiera | Skrypt |
|---|---|---|
| `questions_v2_split.jsonl` | **4313 pytań z podziałem i grupami; podstawowy plik pytań** | `make_split.py` |
| `labels.jsonl` | **4304 etykiety (Δ, klasa, liczniki uciętych)** | `make_labels.py` |
| `embeddings_nomic.npy` | **embeddingi używane przez router** | `embed_questions.py` |
| `answers.jsonl` | 17252 odpowiedzi (4313 × 3 małe + 1 duże) | `generate_answers.py` |
| `scores_gold.jsonl`, `judge_open*.jsonl` | oceny automatyczne i sędziego | `score_gold.py`, `judge_open.py` |
| `questions_v2.jsonl`, `questions_v2.before_filter.jsonl`, `removed_too_long.jsonl` | etapy filtrowania pytań | `collect_questions.py`, `filter_embed_limit.py` |
| `embeddings_bgem3.npy`, `embeddings_mxbai.npy`, `embeddings_qwen3.npy` | porównanie embedderów (odrzucone, `DECYZJE.md` D11) | `embed_alt.py` |
| `router_index.npz` | indeks kNN do eksperymentów | `eval/export_index.py` |
| `robustness_variants.jsonl` | warianty pytań (literówki, parafrazy, synonimy) | `eval/robustness_generate.py` |
| `arena_filtered.jsonl`, `synthetic.jsonl`, `dataset.jsonl`, `test.jsonl`, `validation.jsonl` | **stary plan (v1)**: dawny podział i dawne etykiety **nie obowiązują** | `arena/`, `synthetic/`, `build_dataset.py` |

## Podkatalogi

- `arena/`, `synthetic/`, `build_dataset.py`: przygotowanie danych ze starego planu (etap 1, raporty w `docs/stage1/`); pytania Gemini i część Areny trafiły do `questions_v2.jsonl`.
- `router/`: indeks kNN w gicie, używany przez `RouterService` (`DECYZJE.md` D13).
- `router_l1.json`: tabela punktów i listy fraz warstwy 1, edytowalne bez zmiany kodu (`eval/l1_points.py` je generuje).
