#!/bin/zsh

set -euo pipefail

ROOT="/Users/taeheehong/Documents/Playground"
VENV="$ROOT/.venv"
LOG_DIR="$ROOT/logs"

mkdir -p "$LOG_DIR"

if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

if [ -d "$VENV" ]; then
  source "$VENV/bin/activate"
fi

cd "$ROOT"
export PYTHONPYCACHEPREFIX="$ROOT/.cache/python"
export MPLCONFIGDIR="$ROOT/.cache/matplotlib"
python3 -m krx_screening.main >> "$LOG_DIR/krx_screening_runner.log" 2>&1
python3 scripts/verify_krx_outputs.py >> "$LOG_DIR/krx_screening_runner.log" 2>&1
