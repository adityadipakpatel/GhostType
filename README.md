# GhostType

A lightweight Python script (plus a [Chrome extension](#chrome-extension-types-in-the-background) that types in a background tab) that reads a text file and types it out for you — keystroke by keystroke — with human-like speed variation, natural punctuation pauses, occasional typos, and Google Docs-friendly autosave checkpoints.

Useful for demos, presentations, filling out forms, or anything where you want text to appear as if it's being typed live.

---

## How it works

1. Put your text in `input.txt`
2. Run the script — a summary screen shows character count, word count, speed settings, and an estimated completion time (including the clock time it'll finish at)
3. Type `y` to confirm and start, or `n` to cancel
4. You have a few seconds to click into the window you want the text typed into (shown again with the total estimate as a reminder)
5. GhostType does the rest

Move your mouse to the **top-left corner of your screen** at any time to immediately stop the script (pyautogui failsafe), or press **Ctrl+C** for a clean abort that reports how much was typed.

---

## Setup

**Requirements:** Python 3.8+

```bash
# 1. Clone the repo
git clone https://github.com/adityadipakpatel/GhostType.git
cd GhostType

# 2. Install the dependencies
pip install -r requirements.txt

# 3. Set up your config
cp .env.local .env
```

> **Linux users:** you may also need `python3-xlib` or `python3-tk`:
> ```bash
> sudo apt install python3-xlib python3-tk
> ```

---

## Configuration

All settings live in `.env` (copied from the tracked template `.env.local`). `.env` is gitignored, so your personal tuning never gets committed — `.env.local` stays as the example everyone starts from.

```bash
# Speed preset: slow (~30 WPM) | normal (~60 WPM) | fast (~120 WPM)
SPEED=normal

# Exact words-per-minute. Overrides SPEED when set. Leave blank to use SPEED.
WPM=

# Pause after every "." — long enough for Google Docs to register + save.
FULLSTOP_PAUSE=4.5,5.5

# Stop (like the full-stop pause) at other punctuation: , ; : ! ?
# Off by default — otherwise they just add a small jitter to typing speed.
PUNCTUATION_PAUSE_ENABLED=false
PUNCTUATION_PAUSE=1.0,2.0

# Pause every N words — forces a version history checkpoint in Google Docs.
WORD_CHUNK_SIZE=9
WORD_CHUNK_PAUSE=4.5,5.5

# File to type when none is passed on the command line.
INPUT_FILE=input.txt

# Seconds to wait after confirming, before typing starts.
COUNTDOWN=5

# Chance (0.0-1.0) a letter is mistyped, paused on, backspaced, and
# retyped correctly. 0 disables it.
TYPO_CHANCE=0
TYPO_PAUSE=0.15,0.35

# Occasional longer "thinking" pauses scattered through the text.
THINKING_PAUSE_EVERY=80
THINKING_PAUSE_CHANCE=0.25
THINKING_PAUSE_RANGE=0.4,1.2

# Bell/desktop notification when typing finishes.
SOUND_ON_COMPLETE=true

# Colored terminal output.
COLOR_OUTPUT=true
```

Ranges (`FULLSTOP_PAUSE`, `PUNCTUATION_PAUSE`, `WORD_CHUNK_PAUSE`, `TYPO_PAUSE`, `THINKING_PAUSE_RANGE`) accept either a single number (`5.0`) or `min,max` for randomization.

---

## Usage

### Run it

```bash
python ghosttype.py
```

You'll see a summary like this before anything starts:

```
  ┌─────────────────────────────────────────┐
  │              GhostType                  │
  └─────────────────────────────────────────┘

  TEXT
    Characters   1,240
    Words        214
    Lines        8
    Full stops   12

  SPEED
    Typing       normal (~60 WPM)
    Base delay   0.060s / char

  ESTIMATED TIME BREAKDOWN
    Typing               2m 04s
    Punctuation pauses   18s
    Full stop pauses     1m 00s  (12 × ~5.0s)
    Word chunk pauses    1m 10s  (~23 pauses × ~5.0s)
    Thinking pauses      6s
    ─────────────────────────────────
    Total (approx)       4m 38s

  Estimated finish time: 3:47 PM (if you start now)

  Tip: Move your mouse to the top-left corner to abort at any time.

  Start typing? [y/n]:
```

Typing itself shows a live progress bar with an ETA.

### Command-line flags

Every `.env` setting can be overridden per-run without editing files:

```bash
python ghosttype.py my_other_file.txt   # type a different file
python ghosttype.py --speed fast        # override the speed preset
python ghosttype.py --wpm 85            # type at an exact WPM
python ghosttype.py --countdown 10      # longer countdown
python ghosttype.py --dry-run           # show the estimate only, type nothing
python ghosttype.py -y                  # skip the y/n confirmation
python ghosttype.py --no-color          # plain output, no ANSI colors
python ghosttype.py --no-sound          # no completion bell/notification
```

Run `python ghosttype.py --help` for the full list.

---

## Typing behaviour

GhostType doesn't type at a flat, robotic speed. It adds variation to feel natural:

- **Random jitter** on every keystroke (±30%)
- **Full stop pause** — a stop after `.` for Google Docs to save
- **Word chunk pause** — a stop every 8–10 words for version history
- **Punctuation pauses** — shorter pauses after `!` `?` `,` `;` `:`
- **Newline pauses** — a beat between paragraphs
- **Occasional thinking pauses** — random longer pauses scattered through the text
- **Optional typos** — with `TYPO_CHANCE` set, letters are occasionally mistyped, paused on, backspaced, and corrected, just like a real typist

---

## Aborting

- Move your mouse to the **top-left corner** of your screen to stop immediately (pyautogui's built-in failsafe).
- Press **Ctrl+C** for a clean exit that tells you how many characters were typed before stopping.

---

## Chrome extension (types in the background)

The Python script sends real keystrokes to whatever window is focused, so you can't use your computer while it runs. The Chrome extension in [`extension/`](extension/) sends keystrokes straight to one browser tab through Chrome's debugger API. Once it starts, you can switch tabs, use other apps or minimize Chrome while it types.

### Install

1. Open `chrome://extensions` and turn on **Developer mode** (top right)
2. Click **Load unpacked** and select the `extension/` folder
3. Pin GhostType from the puzzle-piece menu so the ghost icon stays on the toolbar

### Use

1. Open your Google Doc (or any web page) and click where the text should go
2. Click the GhostType icon, paste your text, and check the time estimate
3. Open **Settings** to change speed, pauses, typos and the rest. These are the same options as `.env`, and they're saved between sessions
4. Click **Start typing in this tab**, then do whatever you like

Open the popup at any time to see progress and the finish time, and to **Pause**, **Resume** or **Stop**. You get a desktop notification when typing finishes.

### Good to know

- Chrome shows a *"GhostType started debugging this browser"* bar while typing. That's expected. Clicking **Cancel** on it stops typing.
- Keep the tab open. The extension keeps the computer awake while it types, but closing the laptop lid can still put it to sleep.
- If DevTools is open on the tab, close it first. Only one debugger can attach to a tab at a time.
- If typing stops partway (tab closed, Cancel clicked, Chrome restarted the extension), **Resume from here** continues from the last typed character.
- **Input method:** *Key presses* (default) sends full key-down and key-up events like a real keyboard. *Insert text* is a fallback if a site ignores those.

---

## File structure

```
GhostType/
├── ghosttype.py      # main script
├── input.txt         # put your text here
├── requirements.txt
├── .env.local         # tracked config template — copy to .env
├── .gitignore
├── README.md
└── extension/        # Chrome extension (background typing)
    ├── manifest.json
    ├── background.js # typing loop, drives the tab via chrome.debugger
    ├── engine.js     # pacing + time estimate (port of ghosttype.py)
    ├── popup.html / popup.css / popup.js
    └── icons/
```

---

## License

MIT
