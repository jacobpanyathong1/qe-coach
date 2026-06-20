#!/usr/bin/env bash
# Run this ON the VPS as root, AFTER syncing the project to /opt/qe-trainer.
#   ssh root@SERVER_IP
#   cd /opt/qe-trainer && bash deploy/setup_vps.sh
#
# Idempotent: safe to re-run after you push code updates.
set -euo pipefail

APP_DIR=/opt/qe-trainer
SERVICE_USER=qebot

echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip

echo "[2/5] Creating service user '$SERVICE_USER'..."
id -u "$SERVICE_USER" &>/dev/null || \
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"

echo "[3/5] Building Python venv + installing dependencies..."
cd "$APP_DIR"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -q -r requirements.txt
mkdir -p logs
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

echo "[4/5] Installing systemd service..."
cp deploy/qe-trainer.service /etc/systemd/system/qe-trainer.service
systemctl daemon-reload
systemctl enable qe-trainer >/dev/null

echo "[5/5] Starting..."
if ! grep -q "TELEGRAM_BOT_TOKEN=..*" .env 2>/dev/null; then
  echo "  ! No TELEGRAM_BOT_TOKEN found in $APP_DIR/.env"
  echo "    Add it, then run:  systemctl start qe-trainer"
  exit 0
fi
systemctl restart qe-trainer
sleep 2
systemctl --no-pager --full status qe-trainer | head -n 14 || true
echo
echo "Done. Live logs:  journalctl -u qe-trainer -f"
echo "REMINDER: stop the bot on your Mac first — Telegram allows only ONE poller per token."
