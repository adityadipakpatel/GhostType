# GhostType

A lightweight Python script that reads a text file and types it out for you — keystroke by keystroke — with human-like speed variation, natural punctuation pauses, and a dedicated full stop delay for Google Docs autosave.

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

### 3. Set the full stop pause (Google Docs autosave)

After every `.` GhostType will pause to let Google Docs finish autosaving before continuing. You can control how long:

```python
FULLSTOP_PAUSE = (2.0, 3.0)   # random between 2 and 3 seconds (default)
FULLSTOP_PAUSE = 2.5           # fixed 2.5 seconds
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
- **Full stop pause** — 2–3 second hard stop after `.` for Google Docs autosave
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
