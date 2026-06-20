#!/usr/bin/env bash
# Run this ON YOUR MAC to push the project up to the Raspberry Pi:
#   bash deploy/sync_pi.sh jacob@qe-pi.local
#   (or by IP)  bash deploy/sync_pi.sh jacob@192.168.1.42
#
# Lands in ~/qe-trainer on the Pi (no sudo needed). Skips local junk and the
# local progress DB so the Pi keeps its own study history. Includes .env + media.
set -euo pipefail

DEST="${1:?Usage: bash deploy/sync_pi.sh user@pi-host}"

rsync -avz --delete \
  --exclude '__pycache__/' --exclude '*.pyc' \
  --exclude '.venv/' \
  --exclude 'logs/' \
  --exclude 'progress.db' \
  --exclude '.env' \
  --exclude '.git/' \
  "$HOME/qe-trainer/" "$DEST:qe-trainer/"

echo
echo "Synced to $DEST:~/qe-trainer"
echo "Next:  ssh $DEST   then   cd ~/qe-trainer && bash deploy/setup_pi.sh"
