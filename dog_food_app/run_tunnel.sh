#!/bin/zsh
set -euo pipefail

cd /Users/taeheehong/Documents/Playground
/opt/homebrew/opt/cloudflared/bin/cloudflared tunnel --url http://127.0.0.1:8020
