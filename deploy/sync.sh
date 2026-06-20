#!/usr/bin/env bash
# Run this ON YOUR MAC to push the project up to the VPS.
#   bash deploy/sync.sh root@SERVER_IP
#
# Excludes local-only junk and the local progress DB so the server keeps its own
# study history. Includes .env (your token) and the media/ images.
set -euo pipefail

DEST="${1:?Usage: bash deploy/sync.sh user@server_ip}"

rsync -avz --delete \
  --exclude '__pycache__/' --exclude '*.pyc' \
  --exclude '.venv/' \
  --exclude 'logs/' \
  --exclude 'progress.db' \
  --exclude '.git/' \
  "$HOME/qe-trainer/" "$DEST:/opt/qe-trainer/"

echo
echo "Synced to $DEST:/opt/qe-trainer"
echo "Next:  ssh $DEST  then  cd /opt/qe-trainer && bash deploy/setup_vps.sh"
