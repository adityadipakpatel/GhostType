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

PUNCTUATION_PAUSES = {
    "!":  (2.5, 4.0),
    "?":  (2.5, 4.0),
    ",":  (1.4, 2.2),
    ";":  (1.4, 2.2),
    ":":  (1.2, 1.8),
    "\n": (1.8, 3.0),
}

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


def avg_pause(setting) -> float:
    if isinstance(setting, (list, tuple)):
        return (setting[0] + setting[1]) / 2
    return float(setting)


def format_pause(setting) -> str:
    if isinstance(setting, (list, tuple)):
        return f"{setting[0]}–{setting[1]}s"
    return f"{setting}s"


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s:02d}s"
    else:
        h, rem = divmod(seconds, 3600)
        m, s   = divmod(rem, 60)
        return f"{h}h {m:02d}m {s:02d}s"


def estimate_duration(text: str, base_delay: float) -> dict:
    char_count  = len(text)
    word_count  = len(text.split())
    line_count  = text.count("\n")

    # Pure typing time (base delay × chars, no pauses)
    typing_time = char_count * base_delay

    # Jitter is symmetric so average delay = base_delay (no net change)

    # Punctuation pause time
    punct_time = 0.0
    for char, (lo, hi) in PUNCTUATION_PAUSES.items():
        n = text.count(char)
        # actual pause = base_delay * jitter * multiplier; avg jitter = 1.0
        punct_time += n * base_delay * ((lo + hi) / 2)

    # Full stop pause time
    fullstop_count = text.count(".")
    fullstop_time  = fullstop_count * avg_pause(FULLSTOP_PAUSE)

    # Word chunk pause time
    # Every WORD_CHUNK_SIZE words → one pause; but fullstops reset the counter,
    # so approximate chunks as: (word_count - fullstop_count) / WORD_CHUNK_SIZE
    effective_words  = max(0, word_count - fullstop_count)
    chunk_pauses     = effective_words / max(1, WORD_CHUNK_SIZE)
    chunk_time       = chunk_pauses * avg_pause(WORD_CHUNK_PAUSE)

    # Thinking pauses: ~25% chance every 80 chars, avg pause 0.8s
    thinking_windows = char_count / THINKING_PAUSE_EVERY
    thinking_time    = thinking_windows * THINKING_PAUSE_CHANCE * sum(THINKING_PAUSE_RANGE) / 2

    total = typing_time + punct_time + fullstop_time + chunk_time + thinking_time

    return {
        "char_count":     char_count,
        "word_count":     word_count,
        "line_count":     line_count + 1,
        "fullstops":      fullstop_count,
        "chunk_pauses":   int(chunk_pauses),
        "typing_time":    typing_time,
        "punct_time":     punct_time,
        "fullstop_time":  fullstop_time,
        "chunk_time":     chunk_time,
        "thinking_time":  thinking_time,
        "total":          total,
    }


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
    next_chunk_at  = random.randint(max(1, WORD_CHUNK_SIZE - 1), WORD_CHUNK_SIZE + 1)

    for idx, char in enumerate(text):
        try:
            pyautogui.typewrite(char, interval=0)
        except Exception:
            pass

        if char == " ":
            word_count += 1
            if word_count >= next_chunk_at:
                word_count    = 0
                next_chunk_at = random.randint(max(1, WORD_CHUNK_SIZE - 1), WORD_CHUNK_SIZE + 1)
                time.sleep(rand_pause(WORD_CHUNK_PAUSE))
                since_thinking = 0
                continue

        if char == ".":
            time.sleep(rand_pause(FULLSTOP_PAUSE))
            word_count     = 0
            since_thinking = 0
            continue

        jitter = random.uniform(0.70, 1.30)
        delay  = base_delay * jitter

        if char in PUNCTUATION_PAUSES:
            low, high = PUNCTUATION_PAUSES[char]
            delay *= random.uniform(low, high)

        since_thinking += 1
        if since_thinking >= THINKING_PAUSE_EVERY:
            since_thinking = 0
            if random.random() < THINKING_PAUSE_CHANCE:
                delay += random.uniform(*THINKING_PAUSE_RANGE)

        time.sleep(delay)

        if (idx + 1) % 100 == 0:
            pct = (idx + 1) / total * 100
            print(f"  {pct:.0f}% typed ({idx+1}/{total} chars)", end="\r", flush=True)

    print(f"\n\nDone! {total} characters typed.")


def confirm_or_exit(est: dict, base_delay: float):
    wpm_effective = WPM if WPM is not None else round(60 / (base_delay * 5))
    speed_label   = f"{WPM} WPM (manual)" if WPM is not None else f"{SPEED} ({wpm_effective} WPM)"

    print()
    print("  ┌─────────────────────────────────────────┐")
    print("  │              GhostType                  │")
    print("  └─────────────────────────────────────────┘")
    print()
    print("  TEXT")
    print(f"    Characters   {est['char_count']}")
    print(f"    Words        {est['word_count']}")
    print(f"    Lines        {est['line_count']}")
    print(f"    Full stops   {est['fullstops']}")
    print()
    print("  SPEED")
    print(f"    Typing       {speed_label}")
    print(f"    Base delay   {base_delay:.3f}s / char")
    print()
    print("  ESTIMATED TIME BREAKDOWN")
    print(f"    Typing               {format_duration(est['typing_time'])}")
    print(f"    Punctuation pauses   {format_duration(est['punct_time'])}")
    print(f"    Full stop pauses     {format_duration(est['fullstop_time'])}  ({est['fullstops']} × ~{avg_pause(FULLSTOP_PAUSE):.1f}s)")
    print(f"    Word chunk pauses    {format_duration(est['chunk_time'])}  (~{est['chunk_pauses']} pauses × ~{avg_pause(WORD_CHUNK_PAUSE):.1f}s)")
    print(f"    Thinking pauses      {format_duration(est['thinking_time'])}")
    print(f"    ─────────────────────────────────")
    print(f"    Total (approx)       {format_duration(est['total'])}")
    print()
    print("  Tip: Move mouse to top-left corner to abort at any time.")
    print()

    while True:
        answer = input("  Start typing? [y/n]: ").strip().lower()
        if answer == "y":
            break
        elif answer == "n":
            print("\n  Aborted.")
            sys.exit(0)
        else:
            print("  Please type y or n.")


def main():
    target_file = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE

    base_delay = resolve_base_delay()
    text       = load_text(target_file)
    est        = estimate_duration(text, base_delay)

    confirm_or_exit(est, base_delay)
    countdown(COUNTDOWN)
    type_text(text, base_delay)


if __name__ == "__main__":
    main()
