#!/bin/sh
# Odpowiedzi małego modelu (3 próbki) na dodatkowe pytania, lokalna Ollama; ustawienia jak w pomiarze głównym (dziennik, wpis 13).
# Użycie: sh data/run_extra_small.sh [adres Ollamy] [współbieżność]
# Wznawialne: po przerwaniu uruchomić ponownie, zrobione odpowiedzi są pomijane.
set -e
URL=${1:-http://localhost:11434}
CONC=${2:-4}
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1
caffeinate -i uv run --python 3.13 data/generate_answers.py \
  --input data/datasets/questions_extra.jsonl \
  --output data/datasets/answers_extra_small.jsonl \
  --base-url "$URL" --small qwen3:8b --large Qwen/Qwen3.8-27B-FP8 --n-small 3 --n-large 0 \
  --splits extra --max-tokens 2048 --temperature 0.7 --concurrency "$CONC" \
  --extra-body '{"reasoning_effort":"none"}'
