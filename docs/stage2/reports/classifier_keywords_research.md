# Badania nad słowami kluczowymi jako sygnałem złożoności — warstwa 1 klasyfikatora

## Uzasadnienie podejścia

Lista słów kluczowych pochodzi z **zewnętrznych źródeł** — jest niezależna od naszych danych.
Validation set służy wyłącznie do **weryfikacji** że te ogólne sygnały korelują z COMPLEX/SIMPLE
w naszym datasecie. Nie grozi to overfittingiem bo nie uczymy się słów z danych — tylko
potwierdzamy ogólną wiedzę językową liczbowo.

---

## Źródło 1 — Bloom's Taxonomy

**Anderson & Krathwohl (2001)** — hierarchia 6 poziomów kognitywnych od najprostszego do najtrudniejszego.
Lista czasowników: Salisbury University — https://www.salisbury.edu/administration/academic-affairs/instructional-design-delivery/articles/blooms-taxonomy-action-verbs.aspx

Poziomy 1–2 (Remember, Understand) → **SIMPLE**
Poziomy 3–6 (Apply, Analyze, Evaluate, Create) → **COMPLEX**

### Kandydaci SIMPLE z Blooma (poziomy 1–2)

| Poziom | Frazy |
|---|---|
| Remember | `define, list, name, identify, recall, state, repeat` |
| Understand | `classify, describe, explain, locate, recognize, summarize, translate, paraphrase` |

### Kandydaci COMPLEX z Blooma (poziomy 3–6)

| Poziom | Frazy |
|---|---|
| Apply | `execute, implement, solve, use, demonstrate, calculate, apply, compute, operate` |
| Analyze | `analyze, compare, contrast, differentiate, examine, distinguish, organize, relate, experiment` |
| Evaluate | `evaluate, assess, critique, justify, appraise, argue, defend, judge, weigh, recommend` |
| Create | `design, build, develop, create, construct, generate, plan, compose, formulate, invent` |

**Wynik z literatury:** arXiv:2602.17229 ("Mechanistic Interpretability of Cognitive Complexity in LLMs via Linear Probing using Bloom's Taxonomy") — https://arxiv.org/html/2602.17229
TF-IDF oparty wyłącznie na słowach kluczowych osiąga ~73% skuteczności w klasyfikacji poziomu Blooma.
Potwierdza że słowa kluczowe są użytecznym sygnałem, ale niewystarczającym samodzielnie — co
uzasadnia kaskadę z warstwami 2 i 3.

---

## Źródło 2 — AgentBus (praktyczny system routingu LLM)

https://agentbus.sh/posts/how-to-route-llm-traffic-by-cost-and-complexity/

Praktyczny system routingu produkcyjnego. Wymienia konkretne sygnały heurystyczne używane w praktyce.

### Kandydaci COMPLEX z AgentBus

```
analyze, compare, evaluate, explain why, design, architect,
optimize, refactor, review code, step by step, trade-offs,
pros and cons, debug, implement, investigate
```

### Kandydaci COMPLEX — sygnały strukturalne (AgentBus)

- Prompt powyżej ~150 tokenów
- Obecność bloków kodu (` ``` `) razem z kontekstem debugowania
- Wiele niezależnych poleceń w jednym prompcie

### Kandydaci SIMPLE z AgentBus

```
what is, who is, when did, where is, define, list, translate,
format, convert, is this, yes or no
```

---

## Źródło 3 — Literatura routingu LLM (przegląd)

**"Doing More with Less: Survey on LLM Routing" (arXiv:2502.00409)** — https://arxiv.org/html/2502.00409v1
**RouteLLM (Ong et al., 2024, arXiv:2406.18665)** — https://arxiv.org/pdf/2406.18665
**ACAR: Adaptive Complexity-Aware Routing (arXiv:2602.21231)** — https://arxiv.org/abs/2602.21231

RouteLLM i ACAR nie używają list słów kluczowych — uczą router na danych preferencji.
Survey potwierdza że heurystyki leksykalne są stosowane w praktyce jako warstwa pierwsza kaskady,
ale żadna z prac nie publikuje gotowych list. **Heurystyki leksykalne to nasz oryginalny wkład**
uzasadniony Bloomem i AgentBus, a literatura potwierdza zasadność kaskadowego podejścia.

---

## Skonsolidowana lista kandydatów do weryfikacji

### COMPLEX

| Fraza | Źródło |
|---|---|
| `analyze` | Bloom (Analyze) + AgentBus |
| `compare`, `contrast` | Bloom (Analyze) + AgentBus |
| `evaluate`, `assess` | Bloom (Evaluate) + AgentBus |
| `critique`, `justify`, `appraise`, `argue`, `defend`, `judge`, `weigh` | Bloom (Evaluate) |
| `differentiate`, `examine`, `distinguish`, `organize`, `relate` | Bloom (Analyze) |
| `implement`, `solve`, `demonstrate`, `calculate`, `compute` | Bloom (Apply) + AgentBus |
| `design`, `build`, `develop`, `create`, `construct`, `generate`, `plan`, `compose`, `formulate`, `invent` | Bloom (Create) + AgentBus |
| `optimize`, `refactor`, `architect` | AgentBus |
| `debug`, `investigate`, `explain why` | AgentBus |
| `step by step`, `pros and cons`, `trade-offs` | AgentBus |
| `review code` | AgentBus |

**Uwaga:** kandydaci SIMPLE zostali odrzuceni z analizy. Słowa takie jak `what is`, `list`,
`describe` pojawiają się równie często w COMPLEX (`what is the time complexity of this algorithm
and how would you optimize it`). Heurystyka punktuje wyłącznie sygnały COMPLEX — brak sygnałów
oznacza niski score, nie aktywne karanie za słowa SIMPLE.

---

## Metodologia weryfikacji

Dla każdej frazy COMPLEX liczymy na `data/datasets/validation.jsonl`:
- **Precision** — ile % rekordów zawierających tę frazę to faktycznie COMPLEX
- **Recall** — ile % wszystkich COMPLEX zawiera tę frazę

Skrypt: `eval/analyze_keywords.py`

Progi: precision ≥ 80%, recall ≥ 1%. Frazy poniżej progu odrzucane.

---

## Wyniki weryfikacji

Validation set: 1841 rekordów (COMPLEX: 1180, SIMPLE: 661)

### Frazy które przeszły próg (precision ≥ 80%, recall ≥ 1%)

| Fraza | Źródło | Matches | Precision | Recall |
|---|---|---|---|---|
| `develop` | Bloom (Create) | 12 | 100.0% | 1.02% |
| `analyze` | Bloom (Analyze) + AgentBus | 25 | 96.0% | 2.03% |
| `step by step` | AgentBus | 23 | 95.7% | 1.86% |
| `design` | Bloom (Create) + AgentBus | 21 | 95.2% | 1.69% |
| `plan` | Bloom (Create) | 25 | 88.0% | 1.86% |
| `recommend` | Bloom (Evaluate) | 15 | 86.7% | 1.10% |
| `solve` | Bloom (Apply) | 45 | 86.7% | 3.31% |
| `build` | Bloom (Create) | 15 | 86.7% | 1.10% |
| `implement` | Bloom (Apply) + AgentBus | 28 | 85.7% | 2.03% |
| `generate` | Bloom (Create) | 44 | 84.1% | 3.14% |
| `evaluate` | Bloom (Evaluate) + AgentBus | 16 | 81.2% | 1.10% |

### Frazy odrzucone — za niska precision (< 80%)

`compare` (76.9%), `calculate` (58.6%), `explain why` (50.0%), `compose` (41.7%)

### Frazy odrzucone — za niski recall (< 1%), mimo wysokiej precision

`organize`, `relate`, `assess`, `critique`, `justify`, `argue`, `judge`, `weigh`, `compute`,
`invent`, `optimize`, `debug`, `trade-offs`, `contrast`, `evaluate` (wiele fraz Blooma zbyt
rzadkich w danych by być użytecznym sygnałem)

## Frazy do implementacji w `config/router.yaml`

```
develop, analyze, step by step, design, plan, recommend, solve, build, implement, generate, evaluate
```
