#!/bin/zsh

set -euo pipefail

cd /Users/taeheehong/Documents/Playground

if [ ! -x ".venv/bin/python" ]; then
  echo "Virtualenv not found at .venv/bin/python"
  exit 1
fi

.venv/bin/python -m telegram_digest.main >> output/cron.log 2>&1
