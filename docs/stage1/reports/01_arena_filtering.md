# 01 — Filtrowanie Chatbot Arena

Skrypt: `data/arena/filter.py`
Dataset źródłowy: `lmsys/chatbot_arena_conversations` (HuggingFace, gated)

## Podział modeli

Źródło Elo: https://lmsys.org/blog/2023-06-22-leaderboard/ (dane z okresu kwiecień–czerwiec 2023).
Kryterium podziału: próg liczbowy — WEAK ≤ 980, MEDIUM 981–1150, STRONG ≥ 1151.

**STRONG** (Elo ≥ 1151 → wymagają mocnego modelu → COMPLEX):
- `gpt-4` (1227), `claude-v1` (1178), `claude-instant-v1` (1156)

**WEAK** (Elo ≤ 980 → słaby model wystarczył → SIMPLE):
- `llama-13b` (826), `dolly-v2-12b` (850), `stablelm-tuned-alpha-7b` (871), `fastchat-t5-3b` (897), `chatglm-6b` (905), `oasst-pythia-12b` (924), `alpaca-13b` (930), `RWKV-4-Raven-14B` (950), `mpt-7b-chat` (956)

**MEDIUM — wykluczone** (Elo 981–1150 → niejednoznaczny sygnał):
- `gpt4all-13b-snoozy` (986), `koala-13b` (992), `vicuna-7b` (1008), `palm-2` (1038), `wizardlm-13b` (1048), `vicuna-13b` (1061), `guanaco-33b` (1065), `gpt-3.5-turbo` (1130)

Bierzemy tylko pary STRONG vs WEAK — obie strony muszą należeć do tych grup.

## Mapowanie głosowań na etykiety

| Wynik głosowania | Etykieta | Uzasadnienie |
|---|---|---|
| STRONG wygrał | COMPLEX | Słaby model nie wystarczył |
| WEAK wygrał | SIMPLE | Słaby model poradził sobie |
| tie (normalne) | SIMPLE | Słaby model był wystarczający |
| tie (bothbad) | — odrzucamy | Brak sygnału jakości |

## Filtry (w kolejności aplikowania)

1. **Para modeli** — obie strony muszą należeć do STRONG lub WEAK (nie MEDIUM)
2. **Single-turn** — wykluczamy całe konwersacje wieloturowe
3. **Język** — `language == "English"` (pole z datasetu)
4. **Minimalna długość** — `len(tiktoken.get_encoding("cl100k_base").encode(query)) >= 16`
5. **Duplikaty** — `drop_duplicates(subset=["query"])`, przy kolizji zachowujemy rekord z niższym `question_id`

Przy każdym filtrze logujemy liczebność przed i po — pełny audit trail.

## Wynik

**1738 rekordów** po filtrowaniu, zapisanych do `data/datasets/arena_filtered.jsonl`.

Znane problemy z datasetu: `docs/stage1/decisions/KNOWN_ISSUES.md`
