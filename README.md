# GhostType

A lightweight Python script that reads a text file and types it out for you — keystroke by keystroke — with human-like speed variation, natural punctuation pauses, and Google Docs-friendly autosave checkpoints.

Useful for demos, presentations, filling out forms, or anything where you want text to appear as if it's being typed live.

---

## How it works

1. Put your text in `input.txt`
2. Run the script
3. You have **5 seconds** to click into the window you want the text typed into
4. GhostType does the rest

Move your mouse to the **top-left corner of your screen** at any time to immediately stop the script (pyautogui failsafe).

---

## Setup

**Requirements:** Python 3.7+

```bash
# 1. Clone the repo
git clone https://github.com/adityadipakpatel/GhostType.git
cd GhostType

# 2. Install the dependency
pip install -r requirements.txt
```

> **Linux users:** you may also need `python3-xlib` or `python3-tk`:
> ```bash
> sudo apt install python3-xlib python3-tk
> ```

---

## Usage

### 1. Put your text in `input.txt`

Replace the contents of `input.txt` with whatever you want typed out.

### 2. Configure speed

Open `ghosttype.py` and edit the settings near the top.

**Option A — use a preset:**
```python
SPEED = "normal"   # "slow" | "normal" | "fast"
```

| Setting    | Approx. speed |
|------------|--------------|
| `"slow"`   | ~30 WPM      |
| `"normal"` | ~60 WPM      |
| `"fast"`   | ~120 WPM     |

**Option B — set an exact WPM** (overrides `SPEED` when set):
```python
WPM = 75   # types at exactly 75 words per minute
```

### 3. Configure Google Docs autosave pauses

GhostType has two pauses specifically for keeping Google Docs happy:

**Full stop pause** — after every `.`, GhostType stops long enough for Docs to register and save the sentence:
```python
FULLSTOP_PAUSE = (4.5, 5.5)   # random 4.5–5.5 seconds (default)
FULLSTOP_PAUSE = 5.0           # or a fixed value
```

**Word chunk pause** — every 8–10 words, GhostType takes a longer break to force a version history checkpoint:
```python
WORD_CHUNK_SIZE  = 9             # pause roughly every 9 words
WORD_CHUNK_PAUSE = (4.5, 5.5)   # pause duration in seconds
```

### 4. Run it

```bash
python ghosttype.py
```

You can also pass a different file as an argument:

```bash
python ghosttype.py my_other_file.txt
```

---

## Typing behaviour

GhostType doesn't type at a flat, robotic speed. It adds variation to feel natural:

- **Random jitter** on every keystroke (±30%)
- **Full stop pause** — ~5 second stop after `.` for Google Docs to save
- **Word chunk pause** — ~5 second stop every 8–10 words for version history
- **Punctuation pauses** — shorter pauses after `!` `?` `,` `;` `:`
- **Newline pauses** — a beat between paragraphs
- **Occasional thinking pauses** — random longer pauses scattered through the text

---

## Aborting

Move your mouse to the **top-left corner** of your screen to stop immediately. This is pyautogui's built-in failsafe.

---

## File structure

```
GhostType/
├── ghosttype.py      # main script
├── input.txt         # put your text here
├── requirements.txt
├── .gitignore
└── README.md
```

---

## License

MIT
