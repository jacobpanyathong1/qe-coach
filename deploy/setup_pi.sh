#!/usr/bin/env bash
# Run this ON THE RASPBERRY PI after syncing the project to ~/qe-trainer:
#   cd ~/qe-trainer && bash deploy/setup_pi.sh
#
# Works for any username (pi, jacob, ...) — it detects your user + home dir and
# generates the systemd service accordingly. Idempotent: safe to re-run.
set -euo pipefail

RUN_USER="${SUDO_USER:-$USER}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # the synced ~/qe-trainer

echo "[1/5] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip

echo "[2/5] Building Python venv + installing dependencies (scikit-learn may take a few min on a Pi)..."
cd "$APP_DIR"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -q -r requirements.txt
mkdir -p logs

echo "[3/5] Generating systemd service for user '$RUN_USER' at $APP_DIR..."
sudo tee /etc/systemd/system/qe-trainer.service >/dev/null <<EOF
[Unit]
Description=QE Academy (PWA web app)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python $APP_DIR/webapp/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] Enabling service (auto-start on boot)..."
sudo systemctl daemon-reload
sudo systemctl enable qe-trainer >/dev/null

echo "[5/5] Starting the web app..."
sudo systemctl restart qe-trainer
sleep 2
sudo systemctl --no-pager --full status qe-trainer | head -n 14 || true
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "================================================================"
echo " ✅ QE Academy is running on this Pi (auto-starts on every boot)."
echo "    On your home Wi-Fi, open:   http://${IP:-<pi-ip>}:8000"
echo "    Live logs:                  journalctl -u qe-trainer -f"
echo
echo " To reach it from ANYWHERE (cellular), install Tailscale:"
echo "    curl -fsSL https://tailscale.com/install.sh | sh"
echo "    sudo tailscale up        # opens a login link — approve it"
echo "    tailscale ip -4          # the address to use, e.g. 100.x.y.z:8000"
echo "================================================================"
