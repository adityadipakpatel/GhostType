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

# Base typing speed. Choose one:
#   "slow"   →  ~30 WPM
#   "normal" →  ~60 WPM  (default)
#   "fast"   →  ~120 WPM
SPEED = "normal"

# Optional: override with exact seconds-per-character (overrides SPEED above)
# Set to None to use SPEED instead.
# Example: CUSTOM_DELAY = 0.05  means 50 ms per character
CUSTOM_DELAY = None

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

# Pause multipliers applied after certain punctuation
PUNCTUATION_PAUSES = {
    ".":  (2.5, 4.0),   # end of sentence — longer pause
    "!":  (2.5, 4.0),
    "?":  (2.5, 4.0),
    ",":  (1.4, 2.2),   # brief pause
    ";":  (1.4, 2.2),
    ":":  (1.2, 1.8),
    "\n": (1.8, 3.0),   # newline / paragraph break
}

# Occasional "thinking" pause — random long pause every N chars
THINKING_PAUSE_EVERY   = 80    # roughly every N characters
THINKING_PAUSE_CHANCE  = 0.25  # probability when the window arrives
THINKING_PAUSE_RANGE   = (0.4, 1.2)   # seconds


def resolve_base_delay() -> float:
    if CUSTOM_DELAY is not None:
        return float(CUSTOM_DELAY)
    key = SPEED.strip().lower()
    if key not in SPEED_PRESETS:
        print(f"Unknown SPEED '{SPEED}'. Choose: slow / normal / fast")
        sys.exit(1)
    return SPEED_PRESETS[key]


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
    pyautogui.FAILSAFE = True   # move mouse to top-left corner to abort

    total   = len(text)
    since_thinking = 0

    for idx, char in enumerate(text):
        # ── type the character ──────────────────────────────────────────
        try:
            pyautogui.typewrite(char, interval=0)
        except Exception:
            # pyautogui can't type some Unicode chars directly
            pyautogui.hotkey("ctrl", "shift")   # no-op fallback; skip unknown
            pass

        # ── base delay with small random jitter (~±30%) ─────────────────
        jitter = random.uniform(0.70, 1.30)
        delay  = base_delay * jitter

        # ── punctuation pause ────────────────────────────────────────────
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
    # Allow overriding the input file from the command line
    target_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE

    base_delay = resolve_base_delay()
    text       = load_text(target_file)

    speed_label = f"custom ({CUSTOM_DELAY}s/char)" if CUSTOM_DELAY else SPEED
    print(f"─────────────────────────────────────")
    print(f"  GhostType")
    print(f"─────────────────────────────────────")
    print(f"  File   : {target_file}")
    print(f"  Chars  : {len(text)}")
    print(f"  Speed  : {speed_label}  ({base_delay:.3f}s base delay)")
    print(f"  Tip    : Move mouse to top-left corner to abort at any time.")

    countdown(COUNTDOWN)
    type_text(text, base_delay)


if __name__ == "__main__":
    main()
