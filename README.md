# 🏎️ Tesla QE Trainer Bot

A personal Telegram tutor that coaches you toward a **Quality Engineer** role using
**your own reference books**. It runs on your Mac, pings you on your phone, and adapts
to however much time you have that day.

- **37 lessons** across 7 modules (GD&T, SPC, FMEA, APQP, problem solving, vision systems, physics/materials)
- **102 flashcards + 64 quiz questions** with **spaced repetition** (SM-2) so you remember what you learn
- **Progress dashboard** with per-module mastery bars, streaks, and accuracy
- **`/ask`** — ask anything and get an answer grounded in your actual books (RAG over the PDFs)
- Runs **in the background** and sends a **daily reminder**

---

## What you get

| Command | What it does |
|---|---|
| `/start` | Register + see the menu |
| `/today` | Adaptive session — pick **5 / 15 / 30 min** and it sizes the lesson to fit |
| `/quiz` | One quick quiz question (spaced-repetition aware) |
| `/progress` | Your dashboard: mastery bars, streak, accuracy, what's next |
| `/topic` | Jump straight to a module (GD&T, SPC, FMEA, …) |
| `/ask <question>` | Book-grounded answer, e.g. `/ask explain Cp vs Cpk` |
| `/settime HH:MM` | Set your daily reminder time (24-hour) |
| `/help` | Show the menu again |

---

## One-time setup (~10 minutes)

### 1. Get a Telegram bot token
1. Open Telegram, search for **@BotFather**.
2. Send `/newbot`, follow the prompts (give it a name like *QE Trainer*).
3. BotFather replies with a **token** like `8123456789:AAH...`. Copy it.

### 2. (Optional) Get an Anthropic API key — only needed for `/ask`
1. Go to <https://console.anthropic.com/> → sign in.
2. **Settings → API Keys → Create Key**, copy it (`sk-ant-...`).
3. Add a few dollars of credit. `/ask` uses Claude Haiku by default (~a fraction of a cent per question).

### 3. Put your secrets in `.env`
```bash
cd ~/qe-trainer
cp .env.example .env
open -e .env          # paste your token + key, save, close
```
`.env` should look like:
```
TELEGRAM_BOT_TOKEN=8123456789:AAH...your token...
ANTHROPIC_API_KEY=sk-ant-...your key...      # optional, for /ask
```

### 4. Install dependencies
```bash
cd ~/qe-trainer
pip3 install --user -r requirements.txt
```

### 5. (First time only) Build the book search index
Already built (`rag/chunks.json` exists). Re-run only if you add/replace books:
```bash
python3 rag/build_index.py
```

---

## Run it

### Option A — try it manually first (recommended)
```bash
cd ~/qe-trainer
python3 bot.py
```
Then open Telegram on your **phone**, find your bot, and send `/start`.
Press `Ctrl-C` in the terminal to stop.

### Option B — run it in the background, auto-start at login
```bash
cd ~/qe-trainer
bash install_service.sh
```
- Auto-starts whenever your Mac is on and you're logged in.
- Restarts itself if it crashes.
- **Check it's running:** `launchctl list | grep qetrainer`
- **Logs:** `tail -f ~/qe-trainer/logs/bot.log`
- **Stop / uninstall:** `bash install_service.sh stop`

> Your Mac must be **awake** for the bot to respond and send reminders. If the lid is
> closed / asleep it pauses, and resumes when the Mac wakes.

---

## How the learning works

- **Curriculum order** (foundations first): Physics/Materials → SPC → GD&T → FMEA → APQP → 7-Diamonds problem solving → Vision systems. Use `/topic` to jump around.
- **Spaced repetition:** every flashcard and quiz question you see gets scheduled (SM-2). Get it right → you see it again later; miss it → it comes back soon. `/today` and `/quiz` automatically serve what's *due* before introducing new material.
- **`/ask`** retrieves the most relevant passages from your books and has Claude answer using them, citing the book + page.

---

## Adding more material later

The curriculum is plain JSON in `content/` — one file per module, each a list of topics
(`summary`, `key_points`, `flashcards`, `quiz`). To go deeper on, say, FMEA, just append
more topic objects to `content/fmea.json` (keep the `id`s unique, e.g. `fmea-07`).

For `/ask` coverage of a new book: drop the PDF in `~/Documents`, `~/Downloads`, or
`~/Desktop`, add a one-line spec to `SOURCE_SPECS` in `rag/build_index.py`, and re-run it.

> **Note:** the *Advanced Quality Planning (APQP)* PDF is a scanned/image file, so its text
> isn't in the `/ask` index (the APQP **lessons** are still fully written). To make it
> searchable, OCR it first (e.g. `ocrmypdf in.pdf out.pdf`) and re-run `build_index.py`.

---

## Files

```
qe-trainer/
  bot.py              # the Telegram bot (commands, sessions, scheduler, dashboard)
  db.py               # SQLite progress + SM-2 spaced repetition
  content_loader.py   # loads the curriculum JSON
  content/*.json      # the curriculum (edit these to add lessons)
  rag/                # book text index + TF-IDF retriever for /ask
  selftest.py         # offline test: python3 selftest.py
  install_service.sh  # background-service installer
  progress.db         # your progress (created on first run)
  .env                # your secrets (never share this)
```

## Troubleshooting
- **Bot doesn't respond:** is `python3 bot.py` running (or the service loaded)? Check `logs/bot.log`.
- **`/ask` says it needs a key:** add `ANTHROPIC_API_KEY` to `.env` and restart.
- **Reminder didn't fire:** the Mac must be awake at that minute; check `/settime`.
- **Reset progress:** stop the bot and delete `progress.db` (this erases streaks/history).
