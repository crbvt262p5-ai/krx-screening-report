#!/bin/zsh

set -uo pipefail

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

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') run start ====="
  python3 scripts/check_krx_network_health.py
  network_exit=$?
  echo "network_exit=$network_exit"
  python3 -m krx_screening.main
  main_exit=$?
  echo "main_exit=$main_exit"

  python3 scripts/verify_krx_outputs.py
  verify_exit=$?
  echo "verify_exit=$verify_exit"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') run end ====="

  if [ "$main_exit" -ne 0 ]; then
    exit "$main_exit"
  fi
  exit "$verify_exit"
} >> "$LOG_DIR/krx_screening_runner.log" 2>&1
