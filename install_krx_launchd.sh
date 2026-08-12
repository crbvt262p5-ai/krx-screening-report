#!/bin/zsh

set -euo pipefail

ROOT="/Users/taeheehong/Documents/Playground"
PLIST_SRC="$ROOT/automation/com.playground.krx-screening.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.playground.krx-screening.plist"
LOG_DIR="$ROOT/logs"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$LOG_DIR"
: > "$LOG_DIR/launchd.err.log"
: > "$LOG_DIR/launchd.out.log"
cp "$PLIST_SRC" "$PLIST_DST"
chmod 644 "$PLIST_DST"
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "Installed launchd agent: $PLIST_DST"
