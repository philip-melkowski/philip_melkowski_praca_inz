# eval/: analizy i eksperymenty

Skrypty z nagłówkiem `# /// script` uruchamiaj `uv run --python 3.13 eval/<plik>.py`. Czytają pytania, etykiety i embeddingi z `data/datasets/` (poza gitem, zob. `data/README.md`). Skrypty importują się nawzajem (`sys.path`), więc **nie przenoś ich do podkatalogów**.

Kolumna „Wpis” to **pierwszy** wpis `docs/DZIENNIK.md`, w którym skrypt występuje: tam jest powód powstania, parametry i wynik. Zasady: strojenie tylko na train (i cal) w walidacji krzyżowej po grupach; zbiór `test` zamknięty (`CLAUDE.md`).

## Wspólne, od których zależą inne
| Skrypt | Do czego | Wpis |
|---|---|---|
| `router_baselines.py` | wczytywanie danych (`read`, `DATASETS_DIR`), kNN (`knn_score`), krzywa PGR i punkty odniesienia (zawsze mały/duży, losowy, oracle, długość, źródło) | 18 |
| `label_analysis.py` | rozkład etykiet i wrażliwość na próg Δ | 18 |
| `analyze_keywords.py`, `l1_heuristics.py` | listy kandydatów słów COMPLEX/SIMPLE i cechy warstwy 1 (importowane przez `l1_*`, `router_lexical`) | 19 |

## Warstwy 1–2 i router
| Skrypt | Do czego | Wpis |
|---|---|---|
| `router_layers.py`, `router_extra.py` | ablacja warstw 1 i 2, testy parowane, klastry, górna granica | 19, 20 |
| `router_cv.py` | walidacja krzyżowa po grupach na train+cal (3010 pytań): główne liczby routera | 24 |
| `router_models.py` | przegląd klasyfikatorów na embeddingach | 28 |
| `embedder_compare.py`, `embed_latency.py` | porównanie embedderów i ich opóźnienia | 30 |
| `knn_k_sweep.py`, `knn_weighting.py` | wpływ k i ważenia w kNN | 53, 65 |
| `certified_threshold.py` | próg certyfikowany (Clopper–Pearson); **znany błąd w `pick()`** (wpis 97) | 54 |
| `threshold_table.py` | tabela progów: udział dużego, jakość | — |
| `learning_curve.py` | krzywa uczenia kNN | 41 |
| `error_analysis.py`, `category_analysis.py` | błąd krytyczny i kosztowy; analiza wg kategorii (kategorie tylko do analizy) | 34, 35 |
| `arena_comparison.py`, `judge_agreement.py` | zgodność etykiet z głosowaniami Areny; zgodność sędziów | 31, 32 |
| `robustness_generate.py`, `robustness_eval.py` | odporność: literówki, parafrazy, synonimy | 23 |
| `latency.py` | opóźnienie warstw 1+2 | 23 |
| `export_index.py` | eksport indeksu kNN dla `RouterService` (`data/router/…`) | 25 |

## Warstwa 1 (heurystyki)
| Skrypt | Do czego | Wpis | Status |
|---|---|---|---|
| `l1_points.py` | tabela punktów i próg 2 pkt; generuje `data/router_l1.json` | 62 | **w usłudze** |
| `router_lexical.py`, `router_l1_expanded.py`, `router_l1_keyword_rule.py` | poszerzona lista słów, tf-idf, reguła binarna | 45, 46, 50 | sprawdzone, nie przyjęte |
| `router_l1_shortcut.py`, `router_l1_cascade.py` | czy warstwa 1 może odciąć część pytań | 47, 48 | sprawdzone; „do małego” odrzucone |
| `l1_blend.py` | model logistyczny z wagą | 61 | odrzucone, zapis |
| `analyze_length.py` | długość a trudność | — | historyczny |

## Warstwa 3 (modele decyzyjne)
| Skrypt | Do czego | Wpis |
|---|---|---|
| `layer3_probe.py`, `layer3_eval.py` | pierwsza wersja testu (logprobs z `/v1/completions`), sprawdzona tylko na danych syntetycznych | 32 |
| `layer3_systemone.py` | zbieranie odpowiedzi przez `POST /v1/systemone` (`--url`, `--model`, `--questions`, `--splits`, `--concurrency`; wznawialny) → `data/datasets/layer3_systemone_<model>_<zestaw>.jsonl` | 86 |
| `layer3_systemone_eval.py` | krok 1: AUROC pojedynczych pytań i regresji na wszystkich | 86 |
| `layer3_systemone_vs_knn.py` | krok 2: zysk ponad kNN i ponad samo źródło, strefa niepewności (train) | 90 |
| `layer3_systemone_cal.py` | **jednorazowy pomiar na cal** według protokołu z wpisu 91; nie uruchamiać ponownie dla zmienionego zestawu | 92 |
| `layer3_selfassess.py` | samoocena `qwen3:8b` z logprobs (natywne `/api/chat`) | 98 |
| `layer3_learning_curve.py` | ile etykiet potrzebuje kNN, by dogonić zero-shot | 99 |
| `layer3_questions/v1.json` | **zamrożony** zestaw 8 pytań `noul` (SHA-256 we wpisie 91) | 86, 91 |

## Dane oceny człowieka i wykresy
| Skrypt | Do czego | Wpis |
|---|---|---|
| `human_rate.py`, `human_check_eval.py` | ocena 100 odpowiedzi przez człowieka i zgodność z sędzią | 38, 42 |
| `dataset_roleplay_check.py` | udział fan-fiction i odgrywania ról | 51 |
| `plot_pgr.py`, `plot_summary.py` | wykresy do `docs/figures/` | 21, 32 |
