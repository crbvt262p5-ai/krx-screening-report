#!/bin/zsh

set -euo pipefail

ROOT="/Users/taeheehong/Documents/Playground"
PLIST_SRC="$ROOT/automation/com.playground.krx-screening.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.playground.krx-screening.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Installed launchd agent: $PLIST_DST"
