# Deploying the QE Trainer to an always-on VPS

Goal: the bot runs 24/7 in the cloud so it answers your phone whether or not your
laptop is open. The bot uses **outbound polling**, so the server needs no open
ports, no domain, no TLS — just internet access.

> **One-poller rule:** Telegram allows only ONE process polling a token at a time.
> Before the VPS bot goes live, **stop the bot on your Mac** (or you'll get a 409
> Conflict). Steps below remind you when.

---

## 1. Create the server  *(the only part I can't do for you)*

Pick a provider and create the smallest Ubuntu box — this bot needs ~150 MB RAM:

| Provider | Plan | ~Price |
|---|---|---|
| **Hetzner Cloud** | CX22 (2 vCPU / 4 GB) | ~€4/mo |
| **DigitalOcean** | Basic Droplet (1 GB) | $6/mo |
| **Fly.io / Vultr** | shared-cpu-1x / $5 plan | ~$5/mo |

When creating it:
- **Image:** Ubuntu 24.04 LTS
- **SSH key:** add your public key so you can log in without a password.
  Don't have one? On your Mac run `ssh-keygen -t ed25519` (press Enter through
  the prompts), then paste the contents of `~/.ssh/id_ed25519.pub` into the
  provider's "SSH keys" field.

Note the server's **public IP** when it's ready.

## 2. Push the project up from your Mac

```bash
bash ~/qe-trainer/deploy/sync.sh root@YOUR_SERVER_IP
```

This rsyncs everything (code, content, RAG index, media images, and your `.env`
with the token) to `/opt/qe-trainer` on the server. It skips the local
`progress.db` so the server keeps its own study history.

## 3. Install + start the service on the server

```bash
ssh root@YOUR_SERVER_IP
cd /opt/qe-trainer && bash deploy/setup_vps.sh
```

This installs Python, builds a virtualenv, installs dependencies, registers a
**systemd** service (`qe-trainer`) that auto-starts on boot and auto-restarts on
crash, and launches it.

## 4. Hand off from the Mac

**Now stop the Mac instance** so only the server polls:
- If it's running in a terminal, press `Ctrl-C` there.
- If you installed the Mac launchd service: `bash ~/qe-trainer/install_service.sh stop`

Then confirm the server bot is healthy:
```bash
systemctl status qe-trainer
journalctl -u qe-trainer -f      # live logs; look for "Application started"
```
Message the bot from your phone — it now works with your laptop closed. ✅

---

## Updating later (after you add topics/media)

```bash
bash ~/qe-trainer/deploy/sync.sh root@YOUR_SERVER_IP   # from the Mac
ssh root@YOUR_SERVER_IP "systemctl restart qe-trainer"
```

## Useful commands (on the server)

```bash
systemctl restart qe-trainer     # restart
systemctl stop qe-trainer        # stop
journalctl -u qe-trainer -n 50   # last 50 log lines
```

## Notes
- **/ask** stays off until you put an `ANTHROPIC_API_KEY=` in `.env` (then re-sync + restart).
- The server doesn't need matplotlib/pymupdf — diagrams are pre-generated on your
  Mac and synced as PNGs. Regenerate locally with `python3 media/diagrams.py` and
  re-sync when you change them.
- Keep your `.env` private; the token controls the bot.
