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
#  FULL STOP PAUSE  (for Google Docs autosave)
# ─────────────────────────────────────────────

# How long to pause after a "." in seconds.
# Use a fixed number:      FULLSTOP_PAUSE = 2.5
# Or a random range:       FULLSTOP_PAUSE = (2.0, 3.0)
FULLSTOP_PAUSE = (2.0, 3.0)

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

# Pause multipliers applied after punctuation (multiplied by base delay)
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
THINKING_PAUSE_EVERY  = 80    # roughly every N characters
THINKING_PAUSE_CHANCE = 0.25  # probability when the window arrives
THINKING_PAUSE_RANGE  = (0.4, 1.2)   # seconds


def resolve_base_delay() -> float:
    if WPM is not None:
        # 1 word ≈ 5 chars; delay per char = 60 / (WPM * 5)
        return 60.0 / (float(WPM) * 5)
    key = SPEED.strip().lower()
    if key not in SPEED_PRESETS:
        print(f"Unknown SPEED '{SPEED}'. Choose: slow / normal / fast")
        sys.exit(1)
    return SPEED_PRESETS[key]


def resolve_fullstop_pause() -> float:
    if isinstance(FULLSTOP_PAUSE, (list, tuple)):
        return random.uniform(FULLSTOP_PAUSE[0], FULLSTOP_PAUSE[1])
    return float(FULLSTOP_PAUSE)


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

    total = len(text)
    since_thinking = 0

    for idx, char in enumerate(text):
        # ── type the character ──────────────────────────────────────────
        try:
            pyautogui.typewrite(char, interval=0)
        except Exception:
            pass

        # ── full stop: fixed pause for Google Docs autosave ─────────────
        if char == ".":
            time.sleep(resolve_fullstop_pause())
            since_thinking = 0   # reset thinking counter after the break
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

    if WPM is not None:
        speed_label = f"{WPM} WPM (manual)"
    else:
        speed_label = f"{SPEED}  ({round(60 / (base_delay * 5))} WPM)"

    if isinstance(FULLSTOP_PAUSE, (list, tuple)):
        pause_label = f"{FULLSTOP_PAUSE[0]}–{FULLSTOP_PAUSE[1]}s"
    else:
        pause_label = f"{FULLSTOP_PAUSE}s"

    print(f"─────────────────────────────────────")
    print(f"  GhostType")
    print(f"─────────────────────────────────────")
    print(f"  File        : {target_file}")
    print(f"  Chars       : {len(text)}")
    print(f"  Speed       : {speed_label}")
    print(f"  Full stop   : pause {pause_label} after each \".\"")
    print(f"  Tip         : Move mouse to top-left corner to abort.")

    countdown(COUNTDOWN)
    type_text(text, base_delay)


if __name__ == "__main__":
    main()
