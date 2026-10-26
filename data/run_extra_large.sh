#!/bin/sh
# Odpowiedzi dużego modelu na dodatkowe pytania (data/collect_extra.py), te same ustawienia co pomiar główny (dziennik, wpis 13):
# temperatura 0,7, max_tokens 2048, bez promptu systemowego, myślenie wyłączone przez "reasoning_effort": "none".
# Użycie: API_KEY=... sh data/run_extra_large.sh <adres DF lub vLLM> [model] [współbieżność]
# Wznawialne: ponowne uruchomienie pomija zrobione pytania, błędne nie są zapisywane.
set -e
URL=${1:?podaj adres, np. https://df.test.simplito.com}
MODEL=${2:-Qwen/Qwen3.8-27B-FP8}
CONC=${3:-4}
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1
caffeinate -i uv run --python 3.13 data/generate_answers.py \
  --input data/datasets/questions_extra.jsonl \
  --output data/datasets/answers_extra.jsonl \
  --base-url "$URL" --small qwen3:8b --large "$MODEL" --n-small 0 --n-large 1 \
  --splits extra --max-tokens 2048 --temperature 0.7 --concurrency "$CONC" \
  --extra-body '{"reasoning_effort":"none"}'
