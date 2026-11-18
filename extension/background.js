// background.js — runs the typing loop. Keystrokes go to the target tab through
// the Chrome DevTools Protocol (chrome.debugger), so the tab does not need to be
// focused or visible: you can switch tabs, windows or apps while it types.

import {
  normalizeConfig, resolveBaseDelay, estimate, createTypingState,
  nextDelay, typoFor, randPause,
} from "./engine.js";

const PROTOCOL_VERSION = "1.3";
const REPORT_EVERY_MS = 1000;

/** The active run, or null. Lives only as long as this service worker. */
let run = null;

// ── status (read by the popup through chrome.storage.session) ──

async function getStatus() {
  return (await chrome.storage.session.get("status")).status || { state: "idle" };
}

async function setStatus(patch) {
  const next = { ...(await getStatus()), ...patch, updatedAt: Date.now() };
  await chrome.storage.session.set({ status: next });
  return next;
}

// If Chrome restarted this worker mid-run, the loop is gone. Mark it resumable.
const ready = (async () => {
  const s = await getStatus();
  if (s.state === "running" || s.state === "paused") {
    await setStatus({
      state: "stopped",
      resumable: true,
      message: "Typing was interrupted because Chrome restarted the extension. Resume to continue where it stopped.",
    });
  }
})();

// ── CDP input ──────────────────────────────────

const SHIFTED = {
  "!": ["Digit1", 49], "@": ["Digit2", 50], "#": ["Digit3", 51], "$": ["Digit4", 52],
  "%": ["Digit5", 53], "^": ["Digit6", 54], "&": ["Digit7", 55], "*": ["Digit8", 56],
  "(": ["Digit9", 57], ")": ["Digit0", 48], "_": ["Minus", 189], "+": ["Equal", 187],
  "{": ["BracketLeft", 219], "}": ["BracketRight", 221], "|": ["Backslash", 220],
  ":": ["Semicolon", 186], '"': ["Quote", 222], "<": ["Comma", 188], ">": ["Period", 190],
  "?": ["Slash", 191], "~": ["Backquote", 192],
};

const UNSHIFTED = {
  " ": ["Space", 32], ".": ["Period", 190], ",": ["Comma", 188], "/": ["Slash", 191],
  ";": ["Semicolon", 186], "'": ["Quote", 222], "[": ["BracketLeft", 219],
  "]": ["BracketRight", 221], "\\": ["Backslash", 220], "-": ["Minus", 189],
  "=": ["Equal", 187], "`": ["Backquote", 192],
};

const SHIFT = 8;

/** US-layout key info for a printable character, or null if it has no key. */
function keyInfo(ch) {
  if (/^[a-z]$/i.test(ch)) {
    const up = ch.toUpperCase();
    return { code: `Key${up}`, keyCode: up.charCodeAt(0), modifiers: ch === up ? SHIFT : 0 };
  }
  if (/^[0-9]$/.test(ch)) return { code: `Digit${ch}`, keyCode: ch.charCodeAt(0), modifiers: 0 };
  if (UNSHIFTED[ch]) return { code: UNSHIFTED[ch][0], keyCode: UNSHIFTED[ch][1], modifiers: 0 };
  if (SHIFTED[ch]) return { code: SHIFTED[ch][0], keyCode: SHIFTED[ch][1], modifiers: SHIFT };
  return null;
}

function cdp(tabId, method, params) {
  return chrome.debugger.sendCommand({ tabId }, method, params);
}

async function pressKey(tabId, { key, code, keyCode, modifiers = 0, text }) {
  const common = { key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode, modifiers };
  await cdp(tabId, "Input.dispatchKeyEvent",
    text ? { ...common, type: "keyDown", text, unmodifiedText: text } : { ...common, type: "rawKeyDown" });
  await cdp(tabId, "Input.dispatchKeyEvent", { ...common, type: "keyUp" });
}

async function sendChar(tabId, ch, mode) {
  if (ch === "\r") return;
  if (ch === "\n") return pressKey(tabId, { key: "Enter", code: "Enter", keyCode: 13, text: "\r" });
  if (ch === "\t") return pressKey(tabId, { key: "Tab", code: "Tab", keyCode: 9, text: "\t" });

  const info = mode === "keys" ? keyInfo(ch) : null;
  if (info) return pressKey(tabId, { key: ch, text: ch, ...info });
  return cdp(tabId, "Input.insertText", { text: ch });
}

function pressBackspace(tabId) {
  return pressKey(tabId, { key: "Backspace", code: "Backspace", keyCode: 8 });
}

// ── run control ────────────────────────────────

/** Sleep in small slices so Stop/Pause react quickly and progress keeps updating. */
async function sleep(r, seconds) {
  const end = Date.now() + seconds * 1000;
  while (!r.stop && Date.now() < end) {
    await new Promise((res) => setTimeout(res, Math.min(200, end - Date.now())));
    await maybeReport(r);
  }
}

async function waitWhilePaused(r) {
  while (r.paused && !r.stop) {
    await new Promise((res) => setTimeout(res, 300));
    await maybeReport(r);
  }
}

async function maybeReport(r, force = false) {
  const now = Date.now();
  if (!force && now - r.lastReport < REPORT_EVERY_MS) return;
  r.lastReport = now;
  const remaining = estimate(r.chars.slice(r.index).join(""), r.cfg).total;
  await setStatus({
    state: r.paused ? "paused" : "running",
    index: r.index,
    total: r.chars.length,
    remainingSec: remaining,
    finishAt: r.paused ? null : now + remaining * 1000,
  });
}

async function typeLoop(r) {
  const st = createTypingState(r.cfg);
  let error = null;
  try {
    while (r.index < r.chars.length && !r.stop) {
      await waitWhilePaused(r);
      if (r.stop) break;

      const ch = r.chars[r.index];
      const wrong = typoFor(ch, r.cfg);
      if (wrong) {
        await sendChar(r.tabId, wrong, r.cfg.inputMode);
        await sleep(r, randPause(r.cfg.typoPause));
        await pressBackspace(r.tabId);
        await sleep(r, randPause(r.cfg.typoPause));
        if (r.stop) break;
      }

      await sendChar(r.tabId, ch, r.cfg.inputMode);
      r.index++;
      await sleep(r, nextDelay(ch, st, r.cfg, r.baseDelay));
    }
  } catch (e) {
    error = e;
  }
  await finish(r, error);
}

async function finish(r, error) {
  if (!r.detached) await chrome.debugger.detach({ tabId: r.tabId }).catch(() => {});
  chrome.power.releaseKeepAwake();
  chrome.tabs.update(r.tabId, { autoDiscardable: true }).catch(() => {});
  if (run === r) run = null;

  const done = r.index >= r.chars.length;
  let message;
  if (done) message = `Done! ${r.chars.length} characters typed.`;
  else if (r.stopReason) message = r.stopReason;
  else if (error) message = `Stopped: ${error.message || error}`;
  else message = "Stopped.";

  await setStatus({
    state: done ? "done" : "stopped",
    index: r.index,
    total: r.chars.length,
    remainingSec: 0,
    finishAt: null,
    resumable: !done && r.index > 0,
    message,
  });

  if (r.cfg.notifyOnComplete && (done || error || r.stopReason)) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "GhostType",
      message: done ? `Typing complete — ${r.chars.length} characters typed.` : message,
    });
  }
}

chrome.debugger.onDetach.addListener((source, reason) => {
  if (!run || source.tabId !== run.tabId) return;
  run.detached = true;
  run.stop = true;
  run.stopReason =
    reason === "canceled_by_user" ? "Stopped: you clicked Cancel on Chrome's debugging bar."
    : reason === "target_closed" ? "Stopped: the tab was closed."
    : `Stopped: Chrome disconnected GhostType from the tab (${reason}).`;
});

async function start({ tabId, text, settings, fromIndex = 0 }) {
  if (run) throw new Error("GhostType is already typing. Stop it first.");
  if (!text) throw new Error("There's no text to type.");

  const tab = await chrome.tabs.get(tabId).catch(() => null);
  if (!tab) throw new Error("That tab no longer exists.");
  if (!/^https?:/.test(tab.url || "")) {
    throw new Error("GhostType can only type into normal web pages (not chrome:// or extension pages).");
  }

  const cfg = normalizeConfig(settings);
  try {
    await chrome.debugger.attach({ tabId }, PROTOCOL_VERSION);
  } catch (e) {
    throw new Error(/already attached/i.test(e.message)
      ? "Close DevTools (or other debugging extensions) on that tab, then try again."
      : `Couldn't connect to the tab: ${e.message}`);
  }
  // Make the page behave as if it had focus even while it's in the background.
  await cdp(tabId, "Emulation.setFocusEmulationEnabled", { enabled: true }).catch(() => {});
  chrome.tabs.update(tabId, { autoDiscardable: false }).catch(() => {});
  chrome.power.requestKeepAwake("system");

  await chrome.storage.local.set({ runText: text });
  const chars = Array.from(text);
  run = {
    tabId, cfg, chars,
    baseDelay: resolveBaseDelay(cfg),
    index: Math.min(fromIndex, chars.length),
    stop: false, paused: false, detached: false, stopReason: null, lastReport: 0,
  };

  await setStatus({
    state: "running", tabId, tabTitle: tab.title || tab.url,
    startedAt: Date.now(), resumable: false, message: null,
  });
  await maybeReport(run, true);
  typeLoop(run);
}

async function handle(msg) {
  await ready;
  switch (msg.type) {
    case "start":
      await start(msg);
      return {};
    case "resumeStopped": {
      const s = await getStatus();
      const { runText } = await chrome.storage.local.get("runText");
      if (!s.resumable || !runText) throw new Error("Nothing to resume.");
      await start({ tabId: s.tabId, text: runText, settings: msg.settings, fromIndex: s.index });
      return {};
    }
    case "pause":
      if (run) { run.paused = true; await maybeReport(run, true); }
      return {};
    case "resume":
      if (run) { run.paused = false; await maybeReport(run, true); }
      return {};
    case "stop":
      if (run) { run.stop = true; run.paused = false; }
      return {};
    case "dismiss":
      if (!run) await chrome.storage.session.set({ status: { state: "idle" } });
      return {};
    default:
      throw new Error(`Unknown message: ${msg.type}`);
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  handle(msg).then(
    (res) => sendResponse({ ok: true, ...res }),
    (e) => sendResponse({ ok: false, error: e.message || String(e) }),
  );
  return true;
});
