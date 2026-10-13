# CLAUDE.md — deepfellow-router

Praca inżynierska: dynamiczny i semantyczny routing zapytań LLM według złożoności, zintegrowany z DeepFellow Infra jako `RouterService`.

## Source of truth

- **Koncepcja, architektura, technologie, kryteria sukcesu, harmonogram, aktualny stan:** `../koncepcja.md` — przy rozbieżności wygrywa ten plik.
- **Zakres etapów i szczegółowe specyfikacje (filtry Areny, scoring L1):** `STAGES.md`
- **Raporty i decyzje:** `docs/stage1/`, `docs/stage2/`
- **Literatura:** `docs/references/`

Nie duplikuj treści z `koncepcja.md` w innych plikach — linkuj.

## Kluczowe fakty

- Dwie klasy złożoności: SIMPLE / COMPLEX; osiem kategorii (MT-Bench): CODING, REASONING, MATH, WRITING, ROLEPLAY, EXTRACTION, KNOWLEDGE_STEM, KNOWLEDGE_HUMANITIES (+ UNKNOWN w klasyfikatorze).
- Klasyfikator kaskadowy: heurystyki → embeddingi (`nomic-embed-text`) → Qwen 1.5B zero-shot; każdy wymiar (złożoność, kategoria) rozstrzygany niezależnie.
- Router: macierz complexity × category w YAML; SIMPLE → Qwen 1.5B, COMPLEX → Llama 3 70B.
- Integracja: nowy serwis `RouterService` (`Base2Service`) w DeepFellow Infra, wpięty w `lifecycle.py`; wywołania modeli in-process przez `EndpointRegistry`.
- Map-Reduce tylko dla COMPLEX, poprzedzony heurystyką rozkładalności.
- Brak fine-tuningu — zero-shot i reguły.
- Dane: 2632 rekordy (COMPLEX 1687, SIMPLE 945), split 70/30 (`random_state=42`): validation 1841, test 791. **Test set zamknięty** — otwierany raz, na końcu.
- Dane syntetyczne i LLM-as-Judge: Gemini 2.5 Flash (inny niż testowane modele).

## Stack

Python 3.13, `uv`, strict pyright, PyYAML, tiktoken (cl100k_base).

## Struktura

```
config/router.yaml   # progi, wagi, macierz routingu (planowane)
router/              # classifier, router, mapreduce (planowane)
data/                # skrypty i datasety (Stage 1, gotowe)
eval/                # analizy i kalibracja
docs/                # raporty, decyzje, literatura
```

`deepfellow-infra/` w tym katalogu to osobny, nieśledzony klon frameworka (własny `.git`).
