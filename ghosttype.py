#!/usr/bin/env python3
"""
ghosttype.py — Reads a text file and types it out using your keyboard.
Waits a few seconds after launch so you can focus the target window.

GitHub: https://github.com/adityadipakpatel/GhostType
"""

import argparse
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union

try:
    import pyautogui
except ImportError:
    print("Missing dependency: pyautogui\nRun:  pip install -r requirements.txt")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init()
except ImportError:
    class _NoColor:
        def __getattr__(self, _name):
            return ""
    Fore = Style = _NoColor()

try:
    from tqdm import tqdm
    _TQDM_AVAILABLE = True
except ImportError:
    _TQDM_AVAILABLE = False


PauseSetting = Union[float, Tuple[float, float]]

# ─────────────────────────────────────────────
#  CONSTANTS (not meant to be reconfigured)
# ─────────────────────────────────────────────

SPEED_PRESETS = {
    "slow":   0.12,   # ~30 WPM
    "normal": 0.06,   # ~60 WPM
    "fast":   0.03,   # ~120 WPM
}

SPEED_LABELS = {
    "slow": "~30 WPM",
    "normal": "~60 WPM",
    "fast": "~120 WPM",
}

PUNCTUATION_PAUSES = {
    "!":  (2.5, 4.0),
    "?":  (2.5, 4.0),
    ",":  (1.4, 2.2),
    ";":  (1.4, 2.2),
    ":":  (1.2, 1.8),
    "\n": (1.8, 3.0),
}

QWERTY_NEIGHBORS = {
    "a": "qsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}

# ─────────────────────────────────────────────
#  CONFIG (loaded from .env, overridable via CLI flags)
# ─────────────────────────────────────────────


@dataclass
class Config:
    speed: str = "normal"
    wpm: Optional[float] = None
    fullstop_pause: PauseSetting = (4.5, 5.5)
    word_chunk_size: int = 9
    word_chunk_pause: PauseSetting = (4.5, 5.5)
    input_file: str = "input.txt"
    countdown: int = 5
    typo_chance: float = 0.0
    typo_pause: PauseSetting = (0.15, 0.35)
    thinking_pause_every: int = 80
    thinking_pause_chance: float = 0.25
    thinking_pause_range: PauseSetting = (0.4, 1.2)
    sound_on_complete: bool = True
    color: bool = True


def _env(name: str) -> Optional[str]:
    val = os.getenv(name)
    return val if val not in (None, "") else None


def env_str(name: str, default: str) -> str:
    return _env(name) or default


def env_int(name: str, default: int) -> int:
    val = _env(name)
    return int(val) if val is not None else default


def env_float_or_none(name: str, default: Optional[float]) -> Optional[float]:
    val = _env(name)
    return float(val) if val is not None else default


def env_bool(name: str, default: bool) -> bool:
    val = _env(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_pause(name: str, default: PauseSetting) -> PauseSetting:
    val = _env(name)
    if val is None:
        return default
    parts = [p.strip() for p in val.split(",") if p.strip()]
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return (float(parts[0]), float(parts[1]))
    raise ValueError(f"Invalid pause range for {name}: {val!r} (expected 'x' or 'x,y')")


def load_config() -> Config:
    return Config(
        speed=env_str("SPEED", "normal"),
        wpm=env_float_or_none("WPM", None),
        fullstop_pause=env_pause("FULLSTOP_PAUSE", (4.5, 5.5)),
        word_chunk_size=env_int("WORD_CHUNK_SIZE", 9),
        word_chunk_pause=env_pause("WORD_CHUNK_PAUSE", (4.5, 5.5)),
        input_file=env_str("INPUT_FILE", "input.txt"),
        countdown=env_int("COUNTDOWN", 5),
        typo_chance=env_float_or_none("TYPO_CHANCE", 0.0),
        typo_pause=env_pause("TYPO_PAUSE", (0.15, 0.35)),
        thinking_pause_every=env_int("THINKING_PAUSE_EVERY", 80),
        thinking_pause_chance=env_float_or_none("THINKING_PAUSE_CHANCE", 0.25),
        thinking_pause_range=env_pause("THINKING_PAUSE_RANGE", (0.4, 1.2)),
        sound_on_complete=env_bool("SOUND_ON_COMPLETE", True),
        color=env_bool("COLOR_OUTPUT", True),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="GhostType — types out a text file like a human.",
        epilog="Settings default to .env, and can be overridden with these flags.",
    )
    p.add_argument("file", nargs="?", help="Text file to type (overrides INPUT_FILE)")
    p.add_argument("--speed", choices=["slow", "normal", "fast"], help="Speed preset")
    p.add_argument("--wpm", type=float, help="Exact words-per-minute (overrides --speed)")
    p.add_argument("--countdown", type=int, help="Seconds to wait before typing starts")
    p.add_argument("--dry-run", action="store_true", help="Show the time estimate only; don't type anything")
    p.add_argument("-y", "--yes", action="store_true", help="Skip the y/n confirmation prompt")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    p.add_argument("--no-sound", action="store_true", help="Disable the completion sound/notification")
    return p.parse_args()


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────


def rand_pause(setting: PauseSetting) -> float:
    if isinstance(setting, (list, tuple)):
        return random.uniform(setting[0], setting[1])
    return float(setting)


def avg_pause(setting: PauseSetting) -> float:
    if isinstance(setting, (list, tuple)):
        return (setting[0] + setting[1]) / 2
    return float(setting)


def format_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s:02d}s"
    else:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m:02d}m {s:02d}s"


def format_clock(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def colorize(text: str, color: str, cfg: Config) -> str:
    if not cfg.color:
        return text
    return f"{color}{text}{Style.RESET_ALL}"


def resolve_base_delay(cfg: Config) -> float:
    if cfg.wpm is not None:
        return 60.0 / (float(cfg.wpm) * 5)
    key = cfg.speed.strip().lower()
    if key not in SPEED_PRESETS:
        print(f"Unknown SPEED '{cfg.speed}'. Choose: slow / normal / fast")
        sys.exit(1)
    return SPEED_PRESETS[key]


def estimate_duration(text: str, base_delay: float, cfg: Config) -> dict:
    char_count = len(text)
    word_count = len(text.split())
    line_count = text.count("\n")
    alpha_count = sum(1 for c in text if c.isalpha())

    typing_time = char_count * base_delay

    punct_time = 0.0
    for char, (lo, hi) in PUNCTUATION_PAUSES.items():
        n = text.count(char)
        punct_time += n * base_delay * ((lo + hi) / 2)

    fullstop_count = text.count(".")
    fullstop_time = fullstop_count * avg_pause(cfg.fullstop_pause)

    effective_words = max(0, word_count - fullstop_count)
    chunk_pauses = effective_words / max(1, cfg.word_chunk_size)
    chunk_time = chunk_pauses * avg_pause(cfg.word_chunk_pause)

    thinking_windows = char_count / cfg.thinking_pause_every
    thinking_time = thinking_windows * cfg.thinking_pause_chance * sum(cfg.thinking_pause_range) / 2

    typo_time = 0.0
    if cfg.typo_chance > 0:
        typo_time = alpha_count * cfg.typo_chance * (2 * base_delay + 2 * avg_pause(cfg.typo_pause))

    total = typing_time + punct_time + fullstop_time + chunk_time + thinking_time + typo_time

    return {
        "char_count": char_count,
        "word_count": word_count,
        "line_count": line_count + 1,
        "fullstops": fullstop_count,
        "chunk_pauses": int(chunk_pauses),
        "typing_time": typing_time,
        "punct_time": punct_time,
        "fullstop_time": fullstop_time,
        "chunk_time": chunk_time,
        "thinking_time": thinking_time,
        "typo_time": typo_time,
        "total": total,
    }


def load_text(path: str) -> str:
    if not os.path.isfile(path):
        print(f"File not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def notify_done(cfg: Config):
    if not cfg.sound_on_complete:
        return
    print("\a", end="", flush=True)
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", "GhostType", "Typing complete!"],
                check=False, timeout=2,
            )
        except Exception:
            pass


# ─────────────────────────────────────────────
#  DISPLAY
# ─────────────────────────────────────────────


def print_summary(est: dict, base_delay: float, cfg: Config, finish_time: datetime):
    speed_label = (
        f"{cfg.wpm:g} WPM (manual)" if cfg.wpm is not None
        else f"{cfg.speed} ({SPEED_LABELS.get(cfg.speed.lower(), '?')})"
    )

    print()
    print(colorize("  ┌─────────────────────────────────────────┐", Fore.CYAN, cfg))
    print(colorize("  │              GhostType                  │", Fore.CYAN, cfg))
    print(colorize("  └─────────────────────────────────────────┘", Fore.CYAN, cfg))
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
    if cfg.typo_chance > 0:
        print(f"    Typos        ~{cfg.typo_chance * 100:.0f}% chance per letter (auto-corrected)")
    print()
    print("  ESTIMATED TIME BREAKDOWN")
    print(f"    Typing               {format_duration(est['typing_time'])}")
    print(f"    Punctuation pauses   {format_duration(est['punct_time'])}")
    print(f"    Full stop pauses     {format_duration(est['fullstop_time'])}  ({est['fullstops']} × ~{avg_pause(cfg.fullstop_pause):.1f}s)")
    print(f"    Word chunk pauses    {format_duration(est['chunk_time'])}  (~{est['chunk_pauses']} pauses × ~{avg_pause(cfg.word_chunk_pause):.1f}s)")
    print(f"    Thinking pauses      {format_duration(est['thinking_time'])}")
    if cfg.typo_chance > 0:
        print(f"    Typo corrections     {format_duration(est['typo_time'])}")
    print("    ─────────────────────────────────")
    print(f"    Total (approx)       {colorize(format_duration(est['total']), Fore.YELLOW, cfg)}")
    print()
    print(f"  Estimated finish time: {colorize(format_clock(finish_time), Fore.YELLOW, cfg)} (if you start now)")
    print()
    print("  Tip: Move your mouse to the top-left corner to abort at any time.")
    print()


def confirm():
    while True:
        answer = input("  Start typing? [y/n]: ").strip().lower()
        if answer == "y":
            return
        if answer == "n":
            print("\n  Aborted.")
            sys.exit(0)
        print("  Please type y or n.")


def countdown(seconds: int, total_estimate: float, cfg: Config):
    duration_label = format_duration(total_estimate)
    print()
    print(colorize("  Switch to your target window now!", Fore.CYAN, cfg))
    print(f"  Typing will take about {duration_label} once it starts.\n")
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  Typing now!              ")


# ─────────────────────────────────────────────
#  TYPING
# ─────────────────────────────────────────────


def maybe_typo(char: str, cfg: Config):
    """With small probability, mistype `char`, pause, backspace, and retype it correctly."""
    if cfg.typo_chance <= 0 or not char.isalpha():
        return
    if random.random() >= cfg.typo_chance:
        return
    neighbors = QWERTY_NEIGHBORS.get(char.lower(), "")
    wrong = random.choice(neighbors) if neighbors else random.choice("abcdefghijklmnopqrstuvwxyz")
    if char.isupper():
        wrong = wrong.upper()
    try:
        pyautogui.typewrite(wrong, interval=0)
        time.sleep(rand_pause(cfg.typo_pause))
        pyautogui.press("backspace")
        time.sleep(rand_pause(cfg.typo_pause))
    except Exception:
        pass


def type_text(text: str, cfg: Config, base_delay: float):
    pyautogui.FAILSAFE = True

    total = len(text)
    typed = 0
    since_thinking = 0
    word_count = 0
    next_chunk_at = random.randint(max(1, cfg.word_chunk_size - 1), cfg.word_chunk_size + 1)

    progress = None
    if _TQDM_AVAILABLE:
        progress = tqdm(total=total, unit="ch", ncols=70, desc="Typing")

    try:
        for char in text:
            maybe_typo(char, cfg)

            try:
                pyautogui.typewrite(char, interval=0)
            except Exception:
                pass

            typed += 1
            if progress:
                progress.update(1)
            elif typed % 100 == 0:
                pct = typed / total * 100
                print(f"  {pct:.0f}% typed ({typed}/{total} chars)", end="\r", flush=True)

            if char == " ":
                word_count += 1
                if word_count >= next_chunk_at:
                    word_count = 0
                    next_chunk_at = random.randint(max(1, cfg.word_chunk_size - 1), cfg.word_chunk_size + 1)
                    time.sleep(rand_pause(cfg.word_chunk_pause))
                    since_thinking = 0
                    continue

            if char == ".":
                time.sleep(rand_pause(cfg.fullstop_pause))
                word_count = 0
                since_thinking = 0
                continue

            jitter = random.uniform(0.70, 1.30)
            delay = base_delay * jitter

            if char in PUNCTUATION_PAUSES:
                low, high = PUNCTUATION_PAUSES[char]
                delay *= random.uniform(low, high)

            since_thinking += 1
            if since_thinking >= cfg.thinking_pause_every:
                since_thinking = 0
                if random.random() < cfg.thinking_pause_chance:
                    delay += random.uniform(*cfg.thinking_pause_range)

            time.sleep(delay)
    except KeyboardInterrupt:
        if progress:
            progress.close()
        print(f"\n\n{colorize(f'Interrupted — {typed}/{total} characters were typed.', Fore.YELLOW, cfg)}")
        sys.exit(130)

    if progress:
        progress.close()

    print(f"\n{colorize(f'Done! {total} characters typed.', Fore.GREEN, cfg)}")
    notify_done(cfg)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────


def main():
    cfg = load_config()
    args = parse_args()

    if args.file:
        cfg.input_file = args.file
    if args.speed:
        cfg.speed = args.speed
    if args.wpm is not None:
        cfg.wpm = args.wpm
    if args.countdown is not None:
        cfg.countdown = args.countdown
    if args.no_color:
        cfg.color = False
    if args.no_sound:
        cfg.sound_on_complete = False

    base_delay = resolve_base_delay(cfg)
    text = load_text(cfg.input_file)
    est = estimate_duration(text, base_delay, cfg)
    finish_time = datetime.now() + timedelta(seconds=est["total"])

    print_summary(est, base_delay, cfg, finish_time)

    if args.dry_run:
        print("  Dry run — no keys were sent.\n")
        return

    if not args.yes:
        confirm()

    countdown(cfg.countdown, est["total"], cfg)
    type_text(text, cfg, base_delay)


if __name__ == "__main__":
    main()
