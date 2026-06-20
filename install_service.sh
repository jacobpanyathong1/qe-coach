#!/bin/bash
# Installs the QE Trainer as a background service that starts at login.
# Usage:  bash install_service.sh        (install + start)
#         bash install_service.sh stop   (stop + uninstall)
set -e

PLIST_SRC="/Users/jp/qe-trainer/com.jacob.qetrainer.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.jacob.qetrainer.plist"
LABEL="com.jacob.qetrainer"

if [ "$1" == "stop" ]; then
    echo "Stopping and removing the QE Trainer service…"
    launchctl unload "$PLIST_DST" 2>/dev/null || true
    rm -f "$PLIST_DST"
    echo "Done. The bot will no longer start at login."
    exit 0
fi

# Pre-flight: make sure .env has a token
if [ ! -f "/Users/jp/qe-trainer/.env" ]; then
    echo "ERROR: /Users/jp/qe-trainer/.env not found."
    echo "Copy .env.example to .env and add your TELEGRAM_BOT_TOKEN first."
    exit 1
fi
if ! grep -q "TELEGRAM_BOT_TOKEN=." "/Users/jp/qe-trainer/.env"; then
    echo "ERROR: TELEGRAM_BOT_TOKEN looks empty in .env. Add your token first."
    exit 1
fi

echo "Installing LaunchAgent → $PLIST_DST"
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# Reload cleanly if it was already loaded
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo ""
echo "✅ QE Trainer installed and started."
echo "   It will auto-start whenever you log in."
echo ""
echo "   Check it's running:   launchctl list | grep $LABEL"
echo "   View logs:            tail -f /Users/jp/qe-trainer/logs/bot.log"
echo "   Stop / uninstall:     bash install_service.sh stop"
