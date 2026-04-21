# Decyzja: dobór listy słów kluczowych dla warstwy 1 klasyfikatora

## Kontekst

Warstwa 1 klasyfikatora (heurystyki) przyznaje punkty COMPLEX, gdy w prompcie pojawią się
słowa kluczowe. Lista kandydatów pochodzi z dwóch zewnętrznych źródeł:
- **Bloom's Taxonomy** (Anderson & Krathwohl, 2001) — hierarchia poziomów kognitywnych,
  poziomy 3–6 (Apply, Analyze, Evaluate, Create) jako sygnały COMPLEX
- **AgentBus** — praktyczny system routingu LLM, lista fraz używanych w produkcji

Kandydaci SIMPLE zostali odrzuceni — słowa takie jak `what is`, `list`, `describe` pojawiają
się równie często w COMPLEX i aktywnie szkodzą precision.

Weryfikacja empiryczna na validation secie (1841 rekordów, COMPLEX: 1180, SIMPLE: 661):
skrypt `eval/analyze_keywords.py`, metryki: precision i recall dla każdej frazy.

Pełne wyniki weryfikacji: `docs/reports/classifier_keywords_research.md`

---

## Opcja A — Filtr empiryczny (precision ≥ 80% i recall ≥ 1%)

**Frazy (11):**
```
develop, analyze, step by step, design, plan, recommend,
solve, build, implement, generate, evaluate
```

**Za:** tylko frazy potwierdzone empirycznie na naszych danych — minimalne ryzyko false positives,
każda fraza udowodniła że jest wystarczająco częsta by być użyteczna.

**Przeciw:** odrzuca rzadkie ale bardzo precyzyjne frazy (np. `debug`, `optimize`, `trade-offs`
z precision 100%) tylko dlatego że dataset jest za mały by osiągnąć recall ≥ 1%.

---

## Opcja B — Wszystkie frazy ze źródeł (bez filtrowania)

**Frazy (~42 kandydatów):** cała lista z Blooma i AgentBus, włącznie z frazami o niskiej
precision i zerowym recall na naszym datasecie.

**Za:** lista pochodzi z solidnych zewnętrznych źródeł — nie ma powodu nie ufać Bloomowi
i praktykom systemów routingu; classifier jest kalibrowany progami w YAML więc złe frazy
można wyłapać i usunąć później.

**Przeciw:** frazy z niską precision (`calculate` 58.6%, `compose` 41.7%, `explain why` 50.0%)
aktywnie wprowadzają błędy — SIMPLE prompt z `calculate` dostaje punkty COMPLEX. Frazy z
zerowymi matchami (`differentiate`, `distinguish`, `refactor`, `architect`) nie wnoszą nic
w praktyce.

---

## Opcja C — Filtr tylko po precision (precision ≥ 80%, bez ograniczenia recall)

**Frazy (25):** wszystkie z opcji A plus rzadkie ale precyzyjne:
```
develop, analyze, step by step, design, plan, recommend, solve, build,
implement, generate, evaluate,
organize, relate, assess, critique, justify, argue, judge, weigh,
compute, invent, optimize, debug, trade-offs, contrast
```

**Za:** zachowuje rzadkie frazy o wysokiej precision (100%) które mimo małego datasetu
są wiarygodne — `debug`, `optimize`, `trade-offs` to silne sygnały COMPLEX w każdym kontekście.
Odrzuca tylko frazy z niską precision które aktywnie szkodzą.

**Przeciw:** część fraz (np. `organize`, `relate`) ma 1–3 matches w datasecie — za mało
by statystycznie ufać 100% precision; może to przypadek.

---

---

## Kwestia lematyzacji

Obecna implementacja matchuje frazy dosłownie — `solve` trafia na `solve` ale nie na `solving`,
`solved`, `solver`. Lematyzacja (sprowadzenie słów do formy podstawowej) rozwiązałaby ten problem.

**Dlaczego lematyzacja została odrzucona:**
- Wymaga `spacy` lub `nltk` jako dodatkowej zależności
- Dodaje ~10–50ms latencji na prompcie — niszczy cel warstwy 1 (<1ms)
- Precision może spaść — `planning a trip` → `plan` ale to nie sygnał COMPLEX

**Alternatywa: ręczne odmiany fraz**
Zamiast lematyzacji — dopisanie najpopularniejszych form gramatycznych bezpośrednio do listy:

```
implement → implement, implementing, implemented
analyze → analyze, analyzing, analysing (brytyjska pisownia)
solve → solve, solving, solved
design → design, designing, designed
generate → generate, generating, generated
...
```

Zero kosztu czasowego, pełna kontrola nad tym co matchujemy.

**Do ustalenia z promotorem:** czy lematyzacja powinna być wspomniana w pracy jako świadoma
decyzja odrzucona ze względu na latencję, czy wystarczy ręczne rozwiązanie bez wzmianki.

---

## Do ustalenia z promotorem

Pytanie dotyczy metodologii: czy listę słów kluczowych budujemy:
1. **empirycznie** (opcja A) — tylko co potwierdzone na danych,
2. **na podstawie literatury** (opcja B) — ufamy źródłom bez filtrowania,
3. **hybrydowo** (opcja C) — literatura jako baza, dane jako filtr jakości (tylko precision).

Kluczowy dylemat: czy mały dataset (1841 rekordów) jest wystarczający do empirycznej weryfikacji,
czy lepiej zaufać zewnętrznym źródłom i zostawić kalibrację progom w YAML?
