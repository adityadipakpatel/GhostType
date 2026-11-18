// engine.js — GhostType timing logic, ported from ghosttype.py.
// Shared by the popup (estimates) and the background worker (typing).

export const SPEED_PRESETS = {
  slow: 0.12,   // ~30 WPM
  normal: 0.06, // ~60 WPM
  fast: 0.03,   // ~120 WPM
};

export const SPEED_LABELS = { slow: "~30 WPM", normal: "~60 WPM", fast: "~120 WPM" };

const PUNCTUATION_PAUSES = {
  "!": [2.5, 4.0],
  "?": [2.5, 4.0],
  ",": [1.4, 2.2],
  ";": [1.4, 2.2],
  ":": [1.2, 1.8],
  "\n": [1.8, 3.0],
};

// Marks that get a genuine stop when punctPauseEnabled is on.
const STOPPING_PUNCTUATION = ["!", "?", ",", ";", ":"];

const QWERTY_NEIGHBORS = {
  a: "qsz", b: "vghn", c: "xdfv", d: "serfcx", e: "wsdr",
  f: "drtgvc", g: "ftyhbv", h: "gyujnb", i: "ujko", j: "huikmn",
  k: "jiolm", l: "kop", m: "njk", n: "bhjm", o: "iklp",
  p: "ol", q: "wa", r: "edft", s: "awedxz", t: "rfgy",
  u: "yhji", v: "cfgb", w: "qase", x: "zsdc", y: "tghu",
  z: "asx",
};

export const DEFAULTS = {
  speed: "normal",          // slow | normal | fast | custom
  wpm: 60,                  // used when speed === "custom"
  fullstopPause: [4.5, 5.5],
  punctPauseEnabled: false,
  punctPause: [1.0, 2.0],
  wordChunkSize: 9,
  wordChunkPause: [4.5, 5.5],
  typoChance: 0,            // 0–1
  typoPause: [0.15, 0.35],
  thinkingPauseEvery: 80,
  thinkingPauseChance: 0.25,
  thinkingPauseRange: [0.4, 1.2],
  inputMode: "keys",        // keys | insertText
  notifyOnComplete: true,
};

// ── small helpers ──────────────────────────────

export function uniform(lo, hi) {
  return lo + Math.random() * (hi - lo);
}

function randInt(lo, hi) {
  return lo + Math.floor(Math.random() * (hi - lo + 1));
}

export function randPause(p) {
  return Array.isArray(p) ? uniform(p[0], p[1]) : Number(p);
}

export function avgPause(p) {
  return Array.isArray(p) ? (p[0] + p[1]) / 2 : Number(p);
}

function isAlpha(ch) {
  return ch.toLowerCase() !== ch.toUpperCase();
}

function count(text, ch) {
  let n = 0;
  for (const c of text) if (c === ch) n++;
  return n;
}

/** "4.5,5.5" → [4.5, 5.5]; "5" → 5. Throws on bad input. */
export function parsePause(str, label) {
  const parts = String(str).split(",").map((s) => s.trim()).filter(Boolean);
  const nums = parts.map(Number);
  if (nums.length === 0 || nums.length > 2 || nums.some((n) => !Number.isFinite(n) || n < 0)) {
    throw new Error(`${label}: enter a number or a range like "4.5,5.5"`);
  }
  if (nums.length === 1) return nums[0];
  return nums[0] <= nums[1] ? nums : [nums[1], nums[0]];
}

export function pauseToString(p) {
  return Array.isArray(p) ? `${p[0]},${p[1]}` : String(p);
}

/** Fill in defaults and clamp values so the typing loop never sees garbage. */
export function normalizeConfig(settings = {}) {
  const c = { ...DEFAULTS, ...settings };
  c.wordChunkSize = Math.max(1, Math.round(Number(c.wordChunkSize) || DEFAULTS.wordChunkSize));
  c.thinkingPauseEvery = Math.max(1, Math.round(Number(c.thinkingPauseEvery) || DEFAULTS.thinkingPauseEvery));
  c.typoChance = Math.min(1, Math.max(0, Number(c.typoChance) || 0));
  c.thinkingPauseChance = Math.min(1, Math.max(0, Number(c.thinkingPauseChance) || 0));
  c.wpm = Math.max(1, Number(c.wpm) || DEFAULTS.wpm);
  return c;
}

export function resolveBaseDelay(cfg) {
  if (cfg.speed === "custom") return 60 / (cfg.wpm * 5);
  return SPEED_PRESETS[cfg.speed] ?? SPEED_PRESETS.normal;
}

export function speedLabel(cfg) {
  return cfg.speed === "custom" ? `${cfg.wpm} WPM` : `${cfg.speed} (${SPEED_LABELS[cfg.speed]})`;
}

// ── estimate ───────────────────────────────────

export function estimate(text, cfg) {
  const base = resolveBaseDelay(cfg);
  const chars = [...text];
  const charCount = chars.length;
  const wordCount = text.split(/\s+/).filter(Boolean).length;
  const alphaCount = chars.filter(isAlpha).length;

  const typing = charCount * base;

  let punct = 0;
  for (const [ch, [lo, hi]] of Object.entries(PUNCTUATION_PAUSES)) {
    const n = count(text, ch);
    if (cfg.punctPauseEnabled && STOPPING_PUNCTUATION.includes(ch)) {
      punct += n * avgPause(cfg.punctPause);
    } else {
      punct += n * base * ((lo + hi) / 2);
    }
  }

  const fullstops = count(text, ".");
  const fullstop = fullstops * avgPause(cfg.fullstopPause);

  const effectiveWords = Math.max(0, wordCount - fullstops);
  const chunkPauses = effectiveWords / Math.max(1, cfg.wordChunkSize);
  const chunk = chunkPauses * avgPause(cfg.wordChunkPause);

  const thinking =
    (charCount / cfg.thinkingPauseEvery) * cfg.thinkingPauseChance * avgPause(cfg.thinkingPauseRange);

  const typo = cfg.typoChance > 0
    ? alphaCount * cfg.typoChance * (2 * base + 2 * avgPause(cfg.typoPause))
    : 0;

  return {
    charCount, wordCount, fullstops,
    chunkPauses: Math.floor(chunkPauses),
    typing, punct, fullstop, chunk, thinking, typo,
    total: typing + punct + fullstop + chunk + thinking + typo,
  };
}

// ── typing pacing ──────────────────────────────

export function createTypingState(cfg) {
  return {
    wordCount: 0,
    sinceThinking: 0,
    nextChunkAt: randInt(Math.max(1, cfg.wordChunkSize - 1), cfg.wordChunkSize + 1),
  };
}

/** Seconds to wait after typing `ch`. Mutates `st`. Mirrors type_text() in ghosttype.py. */
export function nextDelay(ch, st, cfg, base) {
  if (ch === " ") {
    st.wordCount++;
    if (st.wordCount >= st.nextChunkAt) {
      st.wordCount = 0;
      st.nextChunkAt = randInt(Math.max(1, cfg.wordChunkSize - 1), cfg.wordChunkSize + 1);
      st.sinceThinking = 0;
      return randPause(cfg.wordChunkPause);
    }
  }

  if (ch === ".") {
    st.wordCount = 0;
    st.sinceThinking = 0;
    return randPause(cfg.fullstopPause);
  }

  if (cfg.punctPauseEnabled && STOPPING_PUNCTUATION.includes(ch)) {
    st.wordCount = 0;
    st.sinceThinking = 0;
    return randPause(cfg.punctPause);
  }

  let delay = base * uniform(0.7, 1.3);
  if (PUNCTUATION_PAUSES[ch]) {
    const [lo, hi] = PUNCTUATION_PAUSES[ch];
    delay *= uniform(lo, hi);
  }

  st.sinceThinking++;
  if (st.sinceThinking >= cfg.thinkingPauseEvery) {
    st.sinceThinking = 0;
    if (Math.random() < cfg.thinkingPauseChance) delay += randPause(cfg.thinkingPauseRange);
  }
  return delay;
}

/** A wrong neighbouring key to type before `ch`, or null for no typo this time. */
export function typoFor(ch, cfg) {
  if (cfg.typoChance <= 0 || !isAlpha(ch) || Math.random() >= cfg.typoChance) return null;
  const neighbors = QWERTY_NEIGHBORS[ch.toLowerCase()] || "abcdefghijklmnopqrstuvwxyz";
  const wrong = neighbors[Math.floor(Math.random() * neighbors.length)];
  return ch === ch.toUpperCase() ? wrong.toUpperCase() : wrong;
}

// ── formatting ─────────────────────────────────

export function formatDuration(seconds) {
  seconds = Math.max(0, Math.round(seconds));
  if (seconds < 60) return `${seconds}s`;
  const pad = (n) => String(n).padStart(2, "0");
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${pad(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${pad(m)}m ${pad(seconds % 60)}s`;
}

export function formatClock(date) {
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}
