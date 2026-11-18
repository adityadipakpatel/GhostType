import {
  DEFAULTS, normalizeConfig, parsePause, pauseToString, estimate,
  formatDuration, formatClock, speedLabel,
} from "./engine.js";

const $ = (id) => document.getElementById(id);

const PAUSE_FIELDS = {
  fullstopPause: "Full-stop pause",
  wordChunkPause: "Word pause",
  punctPause: "Punctuation pause",
  typoPause: "Typo pause",
  thinkingPauseRange: "Thinking pause",
};
const PERCENT_FIELDS = ["typoChance", "thinkingPauseChance"];
const NUMBER_FIELDS = ["wpm", "wordChunkSize", "thinkingPauseEvery"];
const CHECK_FIELDS = ["punctPauseEnabled", "notifyOnComplete"];
const SELECT_FIELDS = ["speed", "inputMode"];

let settings = { ...DEFAULTS };
let status = { state: "idle" };

// ── settings form ──────────────────────────────

function fillForm(s) {
  for (const k of Object.keys(PAUSE_FIELDS)) $(k).value = pauseToString(s[k]);
  for (const k of PERCENT_FIELDS) $(k).value = +(s[k] * 100).toFixed(2);
  for (const k of NUMBER_FIELDS) $(k).value = s[k];
  for (const k of CHECK_FIELDS) $(k).checked = !!s[k];
  for (const k of SELECT_FIELDS) $(k).value = s[k];
  syncVisibility();
}

/** Read the form. Throws with a readable message on invalid input. */
function readForm() {
  const s = {};
  for (const [k, label] of Object.entries(PAUSE_FIELDS)) s[k] = parsePause($(k).value, label);
  for (const k of PERCENT_FIELDS) s[k] = (Number($(k).value) || 0) / 100;
  for (const k of NUMBER_FIELDS) s[k] = Number($(k).value);
  for (const k of CHECK_FIELDS) s[k] = $(k).checked;
  for (const k of SELECT_FIELDS) s[k] = $(k).value;
  return normalizeConfig(s);
}

function syncVisibility() {
  $("wpmRow").hidden = $("speed").value !== "custom";
  $("punctPauseRow").hidden = !$("punctPauseEnabled").checked;
}

function showError(msg) {
  $("error").textContent = msg || "";
  $("error").hidden = !msg;
}

function onFormChange() {
  syncVisibility();
  try {
    settings = readForm();
    showError(null);
    chrome.storage.local.set({ settings });
  } catch (e) {
    showError(e.message);
  }
  renderEstimate();
}

// ── estimate ───────────────────────────────────

function renderEstimate() {
  const text = $("text").value;
  if (!text) {
    $("estimate").textContent = "";
    $("startBtn").disabled = true;
    return;
  }
  const est = estimate(text, settings);
  const finish = new Date(Date.now() + est.total * 1000);
  $("estimate").textContent =
    `${est.charCount} chars · ${est.wordCount} words · ${speedLabel(settings)} · ` +
    `about ${formatDuration(est.total)} (done ~${formatClock(finish)})`;
  $("startBtn").disabled = !!$("error").textContent;
}

// ── status panel ───────────────────────────────

const PILL = { running: "Typing", paused: "Paused", done: "Done", stopped: "Stopped" };

function renderStatus() {
  const s = status;
  const active = s.state !== "idle";
  $("runPanel").hidden = !active;
  $("setupPanel").hidden = active;
  $("pill").hidden = !active;
  if (!active) return;

  $("pill").textContent = PILL[s.state] || s.state;
  $("pill").className = `pill ${s.state}`;
  $("runTab").textContent = s.tabTitle || "tab";

  const total = s.total || 0;
  const index = s.index || 0;
  $("runBar").style.width = total ? `${(index / total) * 100}%` : "0";
  $("runCount").textContent = `${index} / ${total} chars`;

  if (s.state === "running" && s.finishAt) {
    $("runLeft").textContent = `${formatDuration(s.remainingSec)} left · done ~${formatClock(new Date(s.finishAt))}`;
  } else if (s.state === "paused") {
    $("runLeft").textContent = `${formatDuration(s.remainingSec)} left when resumed`;
  } else {
    $("runLeft").textContent = "";
  }

  $("runMsg").textContent = s.message || "";
  $("runMsg").hidden = !s.message;

  const live = s.state === "running" || s.state === "paused";
  $("pauseBtn").hidden = s.state !== "running";
  $("resumeBtn").hidden = s.state !== "paused";
  $("stopBtn").hidden = !live;
  $("resumeStoppedBtn").hidden = !(s.state === "stopped" && s.resumable);
  $("dismissBtn").hidden = live;
}

// ── actions ────────────────────────────────────

async function send(msg) {
  const res = await chrome.runtime.sendMessage(msg);
  if (!res?.ok) throw new Error(res?.error || "Something went wrong.");
  return res;
}

async function act(fn) {
  showError(null);
  try {
    await fn();
  } catch (e) {
    if (status.state === "idle") showError(e.message);
    else { $("runMsg").textContent = e.message; $("runMsg").hidden = false; }
  }
}

$("startBtn").addEventListener("click", () => act(async () => {
  settings = readForm();
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) throw new Error("No active tab found.");
  await send({ type: "start", tabId: tab.id, text: $("text").value, settings });
}));

$("pauseBtn").addEventListener("click", () => act(() => send({ type: "pause" })));
$("resumeBtn").addEventListener("click", () => act(() => send({ type: "resume" })));
$("stopBtn").addEventListener("click", () => act(() => send({ type: "stop" })));
$("resumeStoppedBtn").addEventListener("click", () =>
  act(() => send({ type: "resumeStopped", settings })));
$("dismissBtn").addEventListener("click", () => act(() => send({ type: "dismiss" })));

$("gotoBtn").addEventListener("click", () => act(async () => {
  if (status.tabId == null) return;
  const tab = await chrome.tabs.update(status.tabId, { active: true });
  await chrome.windows.update(tab.windowId, { focused: true });
}));

$("resetBtn").addEventListener("click", () => {
  settings = { ...DEFAULTS };
  fillForm(settings);
  chrome.storage.local.set({ settings });
  showError(null);
  renderEstimate();
});

$("text").addEventListener("input", () => {
  chrome.storage.local.set({ draft: $("text").value });
  renderEstimate();
});

for (const el of document.querySelectorAll("#settings input, #settings select")) {
  el.addEventListener("change", onFormChange);
  el.addEventListener("input", onFormChange);
}

chrome.storage.session.onChanged.addListener((changes) => {
  if (changes.status) {
    status = changes.status.newValue || { state: "idle" };
    renderStatus();
  }
});

// ── init ───────────────────────────────────────

(async () => {
  const { settings: saved, draft } = await chrome.storage.local.get(["settings", "draft"]);
  settings = normalizeConfig(saved);
  fillForm(settings);
  $("text").value = draft || "";
  status = (await chrome.storage.session.get("status")).status || { state: "idle" };
  renderStatus();
  renderEstimate();
})();
