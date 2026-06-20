# Running the QE Trainer on a Raspberry Pi 5 (headless)

"Headless" = no monitor/keyboard needed; you set it up over WiFi from your Mac.
The bot uses **outbound** polling, so the Pi needs no port forwarding — it just
needs internet.

> **One-poller rule:** Telegram allows only ONE process polling a token at a time.
> Keep using the bot on your Mac until the Pi is live; we stop the Mac one at the
> very end (Step 4).

---

## 1. Flash the microSD with the right settings (on your Mac)

The CanaKit card comes preloaded, but flashing it yourself lets us enable SSH +
WiFi up front, which is what makes "headless" work. ~5 minutes:

1. Install **Raspberry Pi Imager**: https://www.raspberrypi.com/software/
2. Insert the microSD (use the included USB reader if needed).
3. In Imager:
   - **Device:** Raspberry Pi 5
   - **OS:** Raspberry Pi OS (64-bit)
   - **Storage:** the microSD card
4. Click **Next → Edit Settings** and set:
   - **Hostname:** `qe-pi`
   - **Enable SSH** (use password authentication is fine)
   - **Username / password:** pick yours (e.g. `jacob` / a password you'll remember)
   - **Configure wireless LAN:** your WiFi name + password + country
   - **Locale / timezone:** yours
5. **Save → Write.** When done, put the microSD in the Pi and power it on.
   Give it ~1–2 minutes to boot and join WiFi the first time.

## 2. Find the Pi and log in (from your Mac)

```bash
ping qe-pi.local          # should reply once it's up
ssh jacob@qe-pi.local     # use the username you set (type 'yes' on first connect)
```
If `qe-pi.local` doesn't resolve, find the Pi's IP in your router's device list
and use `ssh jacob@THAT_IP` instead. **Send me that hostname or IP** and I'll run
the next two steps with you.

## 3. Push the project + install (two commands)

```bash
# on your Mac:
bash ~/qe-trainer/deploy/sync_pi.sh jacob@qe-pi.local

# then on the Pi:
ssh jacob@qe-pi.local
cd ~/qe-trainer && bash deploy/setup_pi.sh
```
`setup_pi.sh` installs Python, builds a virtualenv, installs dependencies, and
registers a **systemd** service that auto-starts on boot and auto-restarts on
crash — then launches the bot.

## 4. Hand off from the Mac

Stop the Mac instance so only the Pi polls (Ctrl-C in its terminal, or
`bash ~/qe-trainer/install_service.sh stop` if you used launchd). Then verify:
```bash
sudo systemctl status qe-trainer
journalctl -u qe-trainer -f      # look for "Application started"
```
Message the bot from your phone — it now runs on the Pi, laptop closed. ✅

---

## Updating later (after we add topics/media)
```bash
bash ~/qe-trainer/deploy/sync_pi.sh jacob@qe-pi.local
ssh jacob@qe-pi.local "sudo systemctl restart qe-trainer"
```

## Notes
- **/ask** stays off until `ANTHROPIC_API_KEY=` is in `.env` (then re-sync + restart).
- Diagrams are pre-generated on your Mac and synced as PNGs — the Pi doesn't need
  matplotlib/pymupdf at runtime.
- The Pi must stay powered + on WiFi. A wired Ethernet cable is even more reliable
  if it's near your router.
