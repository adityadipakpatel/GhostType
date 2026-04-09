#!/usr/bin/env python3
"""
ghosttype.py — Reads a text file and types it out using your keyboard.
Waits 5 seconds after launch so you can focus the target window.

GitHub: https://github.com/adityadipakpatel/GhostType
"""

import time
import random
import sys
import os

try:
    import pyautogui
except ImportError:
    print("Missing dependency: pyautogui\nRun:  pip install pyautogui")
    sys.exit(1)

# ─────────────────────────────────────────────
#  SPEED SETTINGS  (edit these)
# ─────────────────────────────────────────────

# Option A — pick a preset:
#   "slow"   →  ~30 WPM
#   "normal" →  ~60 WPM  (default)
#   "fast"   →  ~120 WPM
SPEED = "normal"

# Option B — set an exact WPM (overrides SPEED above if set)
# Average English word is ~5 characters.
# Example: WPM = 80  →  types at exactly 80 words per minute
WPM = None

# ─────────────────────────────────────────────
#  GOOGLE DOCS AUTOSAVE PAUSES
# ─────────────────────────────────────────────

# Pause after every "." — long enough for Google Docs to register + save.
# Use a fixed number:    FULLSTOP_PAUSE = 5.0
# Or a random range:     FULLSTOP_PAUSE = (4.5, 5.5)
FULLSTOP_PAUSE = (4.5, 5.5)

# Pause every N words — forces a version control checkpoint in Google Docs.
# After typing this many words, GhostType stops for WORD_CHUNK_PAUSE seconds.
WORD_CHUNK_SIZE  = 9             # pause every ~9 words (randomly 8–10)
WORD_CHUNK_PAUSE = (4.5, 5.5)   # how long to pause (seconds)

# ─────────────────────────────────────────────
#  INPUT FILE
# ─────────────────────────────────────────────

INPUT_FILE = "input.txt"

# ─────────────────────────────────────────────
#  COUNTDOWN DURATION (seconds before typing)
# ─────────────────────────────────────────────

COUNTDOWN = 5

# ─────────────────────────────────────────────
#  (no need to edit below this line)
# ─────────────────────────────────────────────

SPEED_PRESETS = {
    "slow":   0.12,   # ~30 WPM
    "normal": 0.06,   # ~60 WPM
    "fast":   0.03,   # ~120 WPM
}

# Pause multipliers after punctuation (multiplied against base delay)
# "." is handled separately via FULLSTOP_PAUSE above
PUNCTUATION_PAUSES = {
    "!":  (2.5, 4.0),
    "?":  (2.5, 4.0),
    ",":  (1.4, 2.2),
    ";":  (1.4, 2.2),
    ":":  (1.2, 1.8),
    "\n": (1.8, 3.0),
}

# Occasional "thinking" pause scattered through the text
THINKING_PAUSE_EVERY  = 80
THINKING_PAUSE_CHANCE = 0.25
THINKING_PAUSE_RANGE  = (0.4, 1.2)


def resolve_base_delay() -> float:
    if WPM is not None:
        return 60.0 / (float(WPM) * 5)
    key = SPEED.strip().lower()
    if key not in SPEED_PRESETS:
        print(f"Unknown SPEED '{SPEED}'. Choose: slow / normal / fast")
        sys.exit(1)
    return SPEED_PRESETS[key]


def rand_pause(setting) -> float:
    if isinstance(setting, (list, tuple)):
        return random.uniform(setting[0], setting[1])
    return float(setting)


def format_pause(setting) -> str:
    if isinstance(setting, (list, tuple)):
        return f"{setting[0]}–{setting[1]}s"
    return f"{setting}s"


def load_text(path: str) -> str:
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def countdown(seconds: int):
    print(f"\nSwitch to your target window now!\n")
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  Typing now!              ")


def type_text(text: str, base_delay: float):
    pyautogui.FAILSAFE = True

    total          = len(text)
    since_thinking = 0
    word_count     = 0
    # Pick first chunk target randomly between 8–10 words
    next_chunk_at  = random.randint(
        max(1, WORD_CHUNK_SIZE - 1),
        WORD_CHUNK_SIZE + 1
    )

    for idx, char in enumerate(text):
        # ── type the character ──────────────────────────────────────────
        try:
            pyautogui.typewrite(char, interval=0)
        except Exception:
            pass

        # ── count words (space after a word = word boundary) ────────────
        if char == " ":
            word_count += 1
            if word_count >= next_chunk_at:
                word_count    = 0
                next_chunk_at = random.randint(
                    max(1, WORD_CHUNK_SIZE - 1),
                    WORD_CHUNK_SIZE + 1
                )
                time.sleep(rand_pause(WORD_CHUNK_PAUSE))
                since_thinking = 0
                continue

        # ── full stop: long pause for Google Docs autosave ──────────────
        if char == ".":
            time.sleep(rand_pause(FULLSTOP_PAUSE))
            word_count     = 0   # reset chunk counter — sentence already saved
            since_thinking = 0
            continue

        # ── base delay with small random jitter (~±30%) ─────────────────
        jitter = random.uniform(0.70, 1.30)
        delay  = base_delay * jitter

        # ── other punctuation pause ──────────────────────────────────────
        if char in PUNCTUATION_PAUSES:
            low, high = PUNCTUATION_PAUSES[char]
            delay *= random.uniform(low, high)

        # ── occasional thinking pause ────────────────────────────────────
        since_thinking += 1
        if since_thinking >= THINKING_PAUSE_EVERY:
            since_thinking = 0
            if random.random() < THINKING_PAUSE_CHANCE:
                delay += random.uniform(*THINKING_PAUSE_RANGE)

        time.sleep(delay)

        # progress indicator every 100 chars
        if (idx + 1) % 100 == 0:
            pct = (idx + 1) / total * 100
            print(f"  {pct:.0f}% typed ({idx+1}/{total} chars)", end="\r", flush=True)

    print(f"\n\nDone! {total} characters typed.")


def main():
    target_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE

    base_delay = resolve_base_delay()
    text       = load_text(target_file)

    speed_label = f"{WPM} WPM (manual)" if WPM is not None \
                  else f"{SPEED}  ({round(60 / (base_delay * 5))} WPM)"

    print(f"─────────────────────────────────────")
    print(f"  GhostType")
    print(f"─────────────────────────────────────")
    print(f"  File         : {target_file}")
    print(f"  Chars        : {len(text)}")
    print(f"  Speed        : {speed_label}")
    print(f"  Full stop    : pause {format_pause(FULLSTOP_PAUSE)} after each \".\"")
    print(f"  Word chunks  : pause {format_pause(WORD_CHUNK_PAUSE)} every ~{WORD_CHUNK_SIZE} words")
    print(f"  Tip          : Move mouse to top-left corner to abort.")

    countdown(COUNTDOWN)
    type_text(text, base_delay)


if __name__ == "__main__":
    main()
