// Page logic for the GUI: it connects the page to the server API. Visible
// text comes from the message catalogs. Message keys appear only as literal
// strings, here and in flow.mjs, so that tests can check them against the
// catalogs. The page changes text with textContent only, never with HTML, so
// that a path or a name from the computer is never read as markup.

import { DEFAULT_LANGUAGE, chooseLanguage, translate } from "./i18n.mjs";
import {
  ACTIVE_STATES,
  BOXES,
  FINISHED_STATES,
  TERMINAL_STATES,
  announcement,
  boxStates,
  boxSummary,
  boxesToConfirm,
  connectionMessages,
  controls,
  defaultOutputName,
  errorBox,
  errorMessages,
  familyRows,
  findingMessages,
  formatElapsed,
  nextLine,
  nextOutputName,
  outputCheckMessages,
  progressMessage,
  resultDetails,
  resultRows,
  runSummary,
  shouldFocusResult,
  stalledSeconds,
  stepRows,
} from "./flow.mjs";

const LANGUAGES = ["en", "ja"];
const LAUNCH_KEY_HEADER = "X-Launch-Key";
const LAUNCH_KEY_STORAGE = "launchKey";
const LANGUAGE_STORAGE = "language";
const HEARTBEAT_INTERVAL_MS = 30000;
const POLL_INTERVAL_MS = 1000;

const byId = (id) => document.getElementById(id);
const ui = {
  version: byId("product-version"),
  connection: byId("connection-status"),
  connectionProblem: byId("connection-problem"),
  nextLine: byId("next-line"),
  nextText: byId("next-text"),
  language: byId("language-select"),
  quit: byId("quit-button"),
  boxes: {
    export: byId("box-export"),
    snapshot: byId("box-snapshot"),
    output: byId("box-output"),
    run: byId("box-run"),
  },
  errors: {
    export: { area: byId("export-error"), heading: byId("export-error-heading"), lines: byId("export-error-lines") },
    output: { area: byId("output-error"), heading: byId("output-error-heading"), lines: byId("output-error-lines") },
    run: { area: byId("run-error"), heading: byId("run-error-heading"), lines: byId("run-error-lines") },
  },
  inputHeading: byId("input-heading"),
  inputPath: byId("input-path"),
  inputBrowse: byId("input-browse"),
  check: byId("check-button"),
  checkResult: byId("check-result"),
  snapshotDecide: byId("snapshot-decide"),
  outputHeading: byId("output-heading"),
  browser: byId("browser"),
  browserHeading: byId("browser-heading"),
  browserPath: byId("browser-path"),
  browserUp: byId("browser-up"),
  browserChoose: byId("browser-choose"),
  browserClose: byId("browser-close"),
  browserMessage: byId("browser-message"),
  browserList: byId("browser-list"),
  outputParent: byId("output-parent"),
  outputBrowse: byId("output-browse"),
  outputName: byId("output-name"),
  timezone: byId("timezone"),
  timezoneList: byId("timezone-list"),
  safePack: byId("safe-pack"),
  packFile: byId("pack-file"),
  outputDecide: byId("output-decide"),
  runHeading: byId("run-heading"),
  resultHeading: byId("result-heading"),
  runExit: byId("run-exit"),
  runSub: byId("run-sub"),
  fitProgress: byId("fit-progress"),
  fitProgressLabel: byId("fit-progress-label"),
  runStalled: byId("run-stalled"),
  runElapsed: byId("run-elapsed"),
  runAnnouncer: byId("run-announcer"),
  start: byId("start-button"),
  cancel: byId("cancel-button"),
  startReason: byId("start-reason"),
  cancelConfirm: byId("cancel-confirm"),
  cancelYes: byId("cancel-yes"),
  cancelNo: byId("cancel-no"),
  runStatus: byId("run-status"),
  runResult: byId("run-result"),
  nextActions: byId("next-actions"),
  openFolder: byId("open-folder-button"),
  openStartHere: byId("open-start-here-button"),
  openResult: byId("open-result"),
  toolsToggle: byId("tools-toggle"),
  toolsBody: byId("tools-body"),
  bundleHeading: byId("bundle-heading"),
  bundle: byId("bundle-button"),
  bundleResult: byId("bundle-result"),
  stepsCaption: byId("steps-caption"),
  stepsRows: byId("steps-rows"),
  stepsTotalLabel: byId("steps-total-label"),
  stepsTotal: byId("steps-total"),
  outputCheckArea: byId("output-check-area"),
  outputCheckHeading: byId("output-check-heading"),
  outputCheck: byId("output-check"),
  resultsCaption: byId("results-caption"),
  familyRows: byId("family-rows"),
};

const state = {
  catalogs: {},
  language: DEFAULT_LANGUAGE,
  launchKey: null,
  connected: false,
  productVersion: null,
  connectionKey: null,
  heartbeatTimer: null,
  pollTimer: null,
  checking: false,
  check: null,
  // The second and third boxes are confirmed with their buttons; a change
  // in the third box asks for its confirmation again.
  snapshotDecided: false,
  outputDecided: false,
  starting: false,
  // Whether a box changed after the last run ended; see boxStates().
  editedSinceRun: false,
  cancelAsked: false,
  toolsOpen: false,
  run: { state: "idle" },
  // The id of what the hidden live region said last; see announcement().
  announced: null,
  // The code of a refused run request, shown in the box that it concerns.
  runError: null,
  quitKey: null,
  browser: null,
  // The check of the finished run's output and the actions on it.
  output: null,
};

class ApiError extends Error {
  constructor(status, code) {
    super(`API request failed with HTTP ${status}`);
    this.status = status;
    this.code = code;
  }
}

function t(key, params) {
  return translate(state.catalogs, state.language, key, params);
}

function formatNumber(value) {
  return typeof value === "number" ? new Intl.NumberFormat(state.language).format(value) : value;
}

// Translate a message from flow.mjs: format its numbers and translate the
// parameters that are message keys themselves.
function describe(message) {
  const params = {};
  for (const [name, value] of Object.entries(message.params ?? {})) {
    params[name] = formatNumber(value);
  }
  for (const [name, key] of Object.entries(message.keyParams ?? {})) {
    params[name] = t(key);
  }
  return t(message.key, params);
}

function errorLines(code, detail) {
  return errorMessages(code, detail).map(describe);
}

// The page renders every second during a run. Rebuilding a live region
// makes screen readers repeat it, so text changes only when it differs.
function replaceLines(container, lines) {
  const current = Array.from(container.children, (line) => line.textContent);
  if (current.length === lines.length && current.every((text, index) => text === lines[index])) {
    return;
  }
  container.replaceChildren(
    ...lines.map((text) => {
      const line = document.createElement("p");
      line.textContent = text;
      return line;
    }),
  );
}

function setText(element, text) {
  if (element.textContent !== text) {
    element.textContent = text;
  }
}

// A focused button that becomes disabled loses focus in some browsers and
// keeps it in others. After an action, give focus back to the button, or to a
// heading while the button stays disabled, unless the user has moved on.
function returnFocus(button, fallback) {
  const active = document.activeElement;
  if (active !== null && active !== document.body && active !== button) {
    return;
  }
  (button.disabled ? fallback : button).focus();
}

function readStorage(name) {
  try {
    return window.sessionStorage.getItem(name);
  } catch {
    return null;
  }
}

function writeStorage(name, value) {
  try {
    window.sessionStorage.setItem(name, value);
  } catch {
    // Without storage, the page still works until it is reloaded.
  }
}

// The key arrives in the URL fragment, which is never sent to the server. Keep
// it for this tab only, and remove it from the address bar and the history.
function readLaunchKey() {
  const fromFragment = new URLSearchParams(window.location.hash.slice(1)).get("key");
  if (fromFragment) {
    writeStorage(LAUNCH_KEY_STORAGE, fromFragment);
    window.history.replaceState(null, "", window.location.pathname);
    return fromFragment;
  }
  return readStorage(LAUNCH_KEY_STORAGE);
}

async function loadCatalog(language) {
  try {
    const response = await fetch(`/i18n/${language}.json`, {
      cache: "no-store",
      credentials: "omit",
    });
    return response.ok ? await response.json() : {};
  } catch {
    return {};
  }
}

async function callApi(path, payload = {}) {
  if (!state.launchKey) {
    throw new ApiError(403, null);
  }
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", [LAUNCH_KEY_HEADER]: state.launchKey },
    body: JSON.stringify(payload),
    cache: "no-store",
    credentials: "omit",
  });
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (!response.ok) {
    throw new ApiError(response.status, typeof body?.error === "string" ? body.error : null);
  }
  return body;
}

// Return true when the page lost the server; other errors carry a code.
function connectionFailure(error) {
  const unauthorized = error instanceof ApiError && error.status === 403;
  if (error instanceof ApiError && !unauthorized) {
    return false;
  }
  state.connected = false;
  stopHeartbeat();
  stopPolling();
  state.connectionKey = unauthorized ? "status.unauthorized" : "status.unavailable";
  return true;
}

// The check of the Export belongs to the first box only: the timezone of the
// third box is checked when the run starts, as the run checks it.
function isCheckCurrent() {
  return state.check !== null && state.check.path === ui.inputPath.value.trim();
}

// The check of the output after a run, as one state of the steps table.
function outputCheckState() {
  const output = state.output;
  if (output === null) {
    return null;
  }
  if (output.checking) {
    return "running";
  }
  if (output.checkError !== null) {
    return "error";
  }
  const doctor = output.check?.doctor;
  const warned =
    (Array.isArray(doctor?.warning_codes) && doctor.warning_codes.length > 0) ||
    doctor?.usability_scope !== "FULL_WITHIN_DECLARED_CONTRACT";
  return output.check === null ? null : warned ? "warn" : "done";
}

// One view of the page's state, for the rules in flow.mjs.
function view() {
  const run = state.run;
  const checked = isCheckCurrent();
  const failedBox = run.state === "failed" ? errorBox(run.error_code, ui.inputPath.value) : null;
  const requestBox = state.runError !== null ? errorBox(state.runError, ui.inputPath.value) : null;
  return {
    connected: state.connected,
    runState: run.state,
    starting: state.starting,
    checking: state.checking,
    outputBusy: outputBusy(),
    checkedReady: checked && state.check.ready === true,
    exportReady: checked && state.check.ready === true && requestBox !== "export",
    exportProblem:
      (checked && (state.check.error !== undefined || state.check.ready !== true)) || requestBox === "export",
    snapshotDecided: state.snapshotDecided,
    outputDecided: state.outputDecided && requestBox !== "output",
    editedSinceRun: state.editedSinceRun,
    failedBox,
    requestBox,
    result: run.result,
    outputPath: run.output_path,
    inputFilled: ui.inputPath.value.trim() !== "",
    inputPath: ui.inputPath.value,
    outputParent: ui.outputParent.value,
    outputName: ui.outputName.value,
    timezone: ui.timezone.value,
  };
}

function renderCheck() {
  const lines = [];
  if (state.checking) {
    lines.push(t("check.running"));
  } else if (state.check?.error !== undefined) {
    lines.push(...errorLines(state.check.error));
  } else if (state.check) {
    lines.push(t(state.check.ready ? "check.ready" : "check.not_ready"));
    for (const finding of state.check.findings) {
      lines.push(...findingMessages(finding).map(describe));
    }
  }
  replaceLines(ui.checkResult, lines);
}

function renderBrowser() {
  const browser = state.browser;
  ui.browser.hidden = browser === null;
  if (browser === null) {
    return;
  }
  ui.browserPath.textContent = browser.path ?? "";
  ui.browserUp.disabled = browser.loading || !browser.parent;
  ui.browserChoose.disabled = browser.loading || !browser.path;
  let message = "";
  if (browser.loading) {
    message = t("browser.loading");
  } else if (browser.error !== null) {
    message = errorLines(browser.error).join(" ");
  } else if (browser.folders.length === 0) {
    message = t("browser.empty");
  } else if (browser.truncated) {
    message = t("browser.truncated", { count: formatNumber(browser.folders.length) });
  }
  setText(ui.browserMessage, message);
}

function childPath(parent, name) {
  const separator = parent.includes("\\") && !parent.includes("/") ? "\\" : "/";
  return parent.endsWith(separator) ? `${parent}${name}` : `${parent}${separator}${name}`;
}

function renderBrowserList() {
  const browser = state.browser;
  const folders = browser === null || browser.loading || browser.error !== null ? [] : browser.folders;
  ui.browserList.replaceChildren(
    ...folders.map((name) => {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "folder";
      button.textContent = name;
      button.addEventListener("click", () => loadFolder(childPath(browser.path, name)));
      item.append(button);
      return item;
    }),
  );
}

const BADGE_KEYS = {
  current: "badge.current",
  done: "badge.done",
  error: "badge.error",
  stopped: "badge.stopped",
};

// Each box: its color, its number or mark, its badge, and the green line
// that sums up a confirmed box.
function renderBoxes(states, current) {
  BOXES.forEach((box, index) => {
    const element = ui.boxes[box];
    const boxState = states[box];
    element.className = `box s-${boxState}`;
    if (boxState === "current" || boxState === "error") {
      element.setAttribute("aria-current", "step");
    } else {
      element.removeAttribute("aria-current");
    }
    const mark = boxState === "done" ? "✓" : boxState === "error" || boxState === "stopped" ? "✕" : String(index + 1);
    setText(element.querySelector(".num"), mark);
    const badge =
      box === "run" && boxState === "done" ? "badge.done_run" : BADGE_KEYS[boxState] ?? null;
    setText(element.querySelector(".badge"), badge === null ? "" : t(badge));
    const summary = element.querySelector(".summary");
    if (summary !== null) {
      const words = boxState === "done" ? boxSummary(box, current) : null;
      summary.hidden = words === null;
      setText(summary, words === null ? "" : describe(words));
    }
  });
}

// The line of what to do now, with a color for its kind.
function renderNextLine(states, current) {
  const line = nextLine(current, states);
  ui.nextLine.hidden = line === null;
  if (line === null) {
    return;
  }
  setText(ui.nextText, describe(line));
  const kind = BOXES.some((box) => states[box] === "error")
    ? "error"
    : current.runState === "finished_after_cancel" ||
        (current.runState === "finished" && (current.result?.warning_count ?? 0) > 0)
      ? "warn"
      : current.runState === "finished"
        ? "done"
        : "current";
  ui.nextLine.className = `next-line k-${kind}`;
}

// A stop: its lines in the box that it concerns, and the other boxes clear.
function renderErrors(current) {
  const run = state.run;
  let box = null;
  let lines = [];
  if (run.state === "failed") {
    box = current.failedBox;
    lines = errorLines(run.error_code, run.error_detail);
  } else if (state.runError !== null) {
    box = current.requestBox;
    lines = errorLines(state.runError);
  }
  for (const [name, error] of Object.entries(ui.errors)) {
    const shown = name === box || (box === "snapshot" && name === "run");
    error.area.hidden = !shown;
    replaceLines(error.lines, shown ? lines : []);
  }
}

function familyRow(row) {
  const tableRow = document.createElement("tr");
  tableRow.className = `r-${row.kind}`;
  const name = document.createElement("th");
  name.scope = "row";
  name.textContent = row.nameKey ? t(row.nameKey) : row.family;
  const records = document.createElement("td");
  records.className = "n";
  records.textContent = formatNumber(row.records);
  const status = document.createElement("td");
  const pill = document.createElement("span");
  pill.className = `pill k-${row.kind === "ok" ? "done" : row.kind}`;
  pill.textContent = t(row.statusKey);
  status.append(pill);
  const warnings = document.createElement("td");
  warnings.className = "n";
  warnings.textContent = formatNumber(row.warnings);
  tableRow.append(name, records, status, warnings);
  return tableRow;
}

const STEP_STATE_KEYS = {
  todo: "step_state.todo",
  run: "step_state.run",
  done: "step_state.done",
  warn: "step_state.warn",
  error: "step_state.error",
  cancelled: "step_state.cancelled",
  skipped: "step_state.skipped",
};
const STEP_ROW_KINDS = {
  todo: "todo",
  run: "run",
  done: "done",
  warn: "warn",
  error: "error",
  cancelled: "todo",
  skipped: "todo",
};

function stepRow(row) {
  const tableRow = document.createElement("tr");
  const kind = STEP_ROW_KINDS[row.state];
  tableRow.className = `r-${kind}`;
  const name = document.createElement("th");
  name.scope = "row";
  name.textContent = t(row.key);
  const status = document.createElement("td");
  const pill = document.createElement("span");
  pill.className = `pill k-${kind}`;
  pill.textContent = t(STEP_STATE_KEYS[row.state]);
  status.append(pill);
  const time = document.createElement("td");
  time.className = "n";
  time.textContent = row.seconds === null ? "—" : formatElapsed(row.seconds);
  tableRow.append(name, status, time);
  return tableRow;
}

function renderSteps() {
  const run = state.run;
  const rows = stepRows(run, outputCheckState(), state.output?.seconds ?? null);
  ui.stepsRows.replaceChildren(...rows.map(stepRow));
  const started = ACTIVE_STATES.includes(run.state) || TERMINAL_STATES.includes(run.state);
  setText(ui.stepsCaption, started ? "" : t("steps.caption"));
  setText(ui.stepsTotalLabel, t(FINISHED_STATES.includes(run.state) ? "steps.total" : "steps.elapsed"));
  setText(ui.stepsTotal, started ? formatElapsed(run.elapsed_seconds) : "—");
}

function renderResults() {
  const run = state.run;
  const rows = resultRows(run);
  ui.familyRows.replaceChildren(...rows.map(familyRow));
  let caption = "results.before";
  if (ACTIVE_STATES.includes(run.state)) {
    caption = "results.running";
  } else if (FINISHED_STATES.includes(run.state)) {
    caption = "results.done";
  } else if (run.state === "failed" || run.state === "cancelled") {
    caption = "results.none";
  }
  setText(ui.resultsCaption, t(caption));
}

function renderRun(states, current) {
  const run = state.run;
  const summary = runSummary(run, states, current);
  setText(ui.resultHeading, describe(summary.headline));
  ui.runExit.hidden = summary.exitCode === null;
  setText(ui.runExit, summary.exitCode === null ? "" : t("result.exit_code", { code: summary.exitCode }));
  setText(ui.runSub, summary.sub === null ? "" : describe(summary.sub));
  // Progress changes every second, so it stays out of live regions; the
  // hidden announcer speaks only when the stage changes.
  const running = run.state === "running";
  setText(ui.fitProgressLabel, running ? describe(progressMessage(run.progress)) : "");
  const reading = running && run.progress?.stage === "reading_fit" && Number(run.progress.total) > 0;
  ui.fitProgress.hidden = !reading;
  if (reading) {
    ui.fitProgress.max = Number(run.progress.total);
    ui.fitProgress.value = Number(run.progress.done) || 0;
  }
  const stalled = stalledSeconds(run);
  setText(ui.runStalled, stalled === null ? "" : t("run.stalled", { seconds: formatNumber(stalled) }));
  const spoken = announcement(run);
  if (spoken !== null && spoken.id !== state.announced) {
    state.announced = spoken.id;
    ui.runAnnouncer.textContent = describe(spoken.message);
  }
  const shown = ACTIVE_STATES.includes(run.state) || TERMINAL_STATES.includes(run.state);
  setText(ui.runElapsed, shown ? t("run.elapsed", { time: formatElapsed(run.elapsed_seconds) }) : "");
  const waiting = boxesToConfirm(states);
  setText(
    ui.startReason,
    !shown && waiting.length > 0
      ? t("run.reason", {
          boxes: new Intl.ListFormat(state.language, { type: "conjunction" }).format(waiting.map(String)),
        })
      : "",
  );
  ui.cancelConfirm.hidden = !(state.cancelAsked && run.state === "running");
  const lines = [];
  if (state.quitKey !== null) {
    lines.push(t(state.quitKey));
  }
  replaceLines(ui.runStatus, lines);
  replaceLines(ui.runResult, resultDetails(run).map(describe));
  ui.nextActions.hidden = !FINISHED_STATES.includes(run.state);
}

function outputBusy() {
  const output = state.output;
  return output !== null && (output.checking || output.opening || output.bundling);
}

function renderOutput() {
  const output = state.output;
  const finished = output !== null && FINISHED_STATES.includes(state.run.state);
  ui.outputCheckArea.hidden = !finished;
  const checkLines = [];
  if (finished && output.checking) {
    checkLines.push(t("output_check.running"));
  } else if (finished && output.checkError !== null) {
    checkLines.push(...errorLines(output.checkError));
  } else if (finished && output.check !== null) {
    checkLines.push(...outputCheckMessages(output.check).map(describe));
  }
  replaceLines(ui.outputCheck, checkLines);
  const openLines = [];
  if (finished && output.openError !== null) {
    openLines.push(...errorLines(output.openError));
  } else if (finished && output.opened) {
    openLines.push(t("open.requested"));
  }
  replaceLines(ui.openResult, openLines);
  const bundleLines = [];
  if (finished && output.bundling) {
    bundleLines.push(t("bundle.creating"));
  } else if (finished && output.bundleError !== null) {
    bundleLines.push(...errorLines(output.bundleError));
  } else if (finished && output.bundle !== null) {
    bundleLines.push(
      t("bundle.created", {
        count: formatNumber(output.bundle.member_count),
        path: output.bundle.path,
      }),
    );
    if (output.bundle.human_review_required === true) {
      bundleLines.push(t("bundle.review"));
    }
  }
  replaceLines(ui.bundleResult, bundleLines);
  ui.toolsToggle.setAttribute("aria-expanded", String(state.toolsOpen));
  ui.toolsBody.hidden = !state.toolsOpen;
}

function renderPackFile() {
  ui.packFile.hidden = !ui.safePack.checked;
  setText(ui.packFile, ui.safePack.checked ? t("pack.file", { name: ui.outputName.value.trim() }) : "");
}

function renderControls(states, current) {
  const enabled = controls(current, states);
  for (const field of [ui.inputPath, ui.outputParent, ui.outputName, ui.timezone, ui.safePack]) {
    field.disabled = !enabled.form;
  }
  ui.inputBrowse.disabled = !enabled.browse;
  ui.outputBrowse.disabled = !enabled.browse;
  ui.check.disabled = !enabled.check;
  ui.snapshotDecide.disabled = !enabled.decideSnapshot;
  ui.outputDecide.disabled = !enabled.decideOutput;
  ui.snapshotDecide.hidden = states.snapshot === "done";
  ui.outputDecide.hidden = states.output === "done";
  ui.start.disabled = !enabled.start;
  // After a run, the main action is to open the output, so only that button
  // is the primary one.
  ui.start.classList.toggle("primary", !FINISHED_STATES.includes(state.run.state));
  ui.cancel.disabled = !enabled.cancel;
  ui.quit.disabled = !enabled.quit;
  ui.openFolder.disabled = !enabled.outputActions;
  ui.openStartHere.disabled = !enabled.outputActions;
  // The bundle's name is fixed, so a second one would be refused.
  ui.bundle.disabled = !enabled.outputActions || state.output?.bundle != null;
}

function render() {
  document.documentElement.lang = state.language;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  ui.version.textContent =
    state.productVersion === null ? "" : t("app.version", { version: state.productVersion });
  const connection = connectionMessages(state.connectionKey);
  setText(ui.connection, connection.status.map(describe).join(" "));
  ui.connectionProblem.hidden = connection.problem.length === 0;
  replaceLines(ui.connectionProblem, connection.problem.map(describe));
  for (const option of ui.language.options) {
    option.textContent = translate(state.catalogs, option.value, "language.name");
  }
  ui.language.value = state.language;
  const current = view();
  const states = boxStates(current);
  renderBoxes(states, current);
  renderNextLine(states, current);
  renderCheck();
  renderBrowser();
  renderErrors(current);
  renderRun(states, current);
  renderSteps();
  renderResults();
  renderOutput();
  renderPackFile();
  renderControls(states, current);
}

function stopHeartbeat() {
  if (state.heartbeatTimer !== null) {
    window.clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = null;
  }
}

function startHeartbeat() {
  state.heartbeatTimer = window.setInterval(() => {
    callApi("/api/heartbeat").catch((error) => {
      connectionFailure(error);
      render();
    });
  }, HEARTBEAT_INTERVAL_MS);
}

function stopPolling() {
  if (state.pollTimer !== null) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

// Where focus goes at the end of a run: the headline of the fourth box, or
// the heading of the stop in the box that it concerns.
function endFocusTarget() {
  if (state.run.state !== "failed") {
    return ui.resultHeading;
  }
  const box = errorBox(state.run.error_code, ui.inputPath.value);
  return (ui.errors[box] ?? ui.errors.run).heading;
}

async function pollRun() {
  let ended = false;
  try {
    state.run = await callApi("/api/run/status");
    if (TERMINAL_STATES.includes(state.run.state)) {
      stopPolling();
      ended = true;
      state.cancelAsked = false;
      state.editedSinceRun = false;
      if (FINISHED_STATES.includes(state.run.state) && state.output === null) {
        // The name is taken now; propose another one for the next run.
        ui.outputName.value = nextOutputName(ui.outputName.value.trim(), new Date());
        checkOutput();
      }
    }
  } catch (error) {
    connectionFailure(error);
  }
  render();
  if (ended && shouldFocusResult(document.activeElement, document.body, ui.boxes.run)) {
    endFocusTarget().focus();
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(pollRun, POLL_INTERVAL_MS);
}

// Check the finished output as the CLI's validate-handoff and doctor
// --run-output would; the server knows which folder the run published.
async function checkOutput() {
  const started = performance.now();
  const output = {
    checking: true,
    // The seconds of the check, for the last step of the steps table.
    seconds: null,
    check: null,
    checkError: null,
    opening: false,
    opened: false,
    openError: null,
    bundling: false,
    bundle: null,
    bundleError: null,
  };
  state.output = output;
  render();
  try {
    output.check = await callApi("/api/check-output");
  } catch (error) {
    if (!connectionFailure(error)) {
      output.checkError = error.code;
    }
  } finally {
    output.checking = false;
    output.seconds = (performance.now() - started) / 1000;
    render();
  }
}

async function openOutput(target) {
  const output = state.output;
  if (output === null) {
    return;
  }
  output.opening = true;
  output.opened = false;
  output.openError = null;
  render();
  try {
    await callApi("/api/open-output", { target });
    output.opened = true;
  } catch (error) {
    if (!connectionFailure(error)) {
      output.openError = error.code;
    }
  } finally {
    output.opening = false;
    render();
    returnFocus(target === "folder" ? ui.openFolder : ui.openStartHere, ui.resultHeading);
  }
}

async function makeBundle() {
  const output = state.output;
  if (output === null) {
    return;
  }
  output.bundling = true;
  output.bundleError = null;
  render();
  try {
    output.bundle = await callApi("/api/support-bundle");
  } catch (error) {
    if (!connectionFailure(error)) {
      output.bundleError = error.code;
    }
  } finally {
    output.bundling = false;
    render();
    returnFocus(ui.bundle, ui.bundleHeading);
  }
}

async function suggestOutputParent(inputPath) {
  try {
    const listing = await callApi("/api/folders", { path: inputPath });
    if (typeof listing.parent === "string" && ui.outputParent.value.trim() === "") {
      ui.outputParent.value = listing.parent;
    }
  } catch (error) {
    connectionFailure(error);
  }
}

async function runCheck() {
  const path = ui.inputPath.value.trim();
  state.checking = true;
  state.check = null;
  state.runError = null;
  render();
  try {
    const answer = await callApi("/api/check-input", { input: path });
    state.check = {
      path,
      ready: answer.ready === true,
      findings: Array.isArray(answer.findings) ? answer.findings : [],
    };
    if (state.check.ready) {
      await suggestOutputParent(path);
    }
  } catch (error) {
    if (!connectionFailure(error)) {
      state.check = { path, error: error.code };
    }
  } finally {
    state.checking = false;
    render();
    returnFocus(ui.check, ui.inputHeading);
  }
}

// Confirm a box and move to the next one, as the page asks on a first launch.
function decide(box) {
  if (box === "snapshot") {
    state.snapshotDecided = true;
  } else {
    state.outputDecided = true;
  }
  render();
  (box === "snapshot" ? ui.outputHeading : ui.runHeading).focus();
}

async function startRun() {
  state.starting = true;
  state.runError = null;
  state.quitKey = null;
  state.cancelAsked = false;
  // The previous result would read as the answer to this attempt.
  state.run = { state: "idle" };
  state.output = null;
  state.announced = null;
  render();
  try {
    state.run = await callApi("/api/run/start", {
      input: ui.inputPath.value.trim(),
      output_parent: ui.outputParent.value.trim(),
      output_name: ui.outputName.value.trim(),
      timezone: ui.timezone.value.trim(),
      external_safe_pack: ui.safePack.checked,
    });
    startPolling();
  } catch (error) {
    if (!connectionFailure(error)) {
      state.runError = error.code;
    }
  } finally {
    state.starting = false;
    render();
    if (state.runError !== null) {
      const box = errorBox(state.runError, ui.inputPath.value);
      (ui.errors[box] ?? ui.errors.run).heading.focus();
    } else {
      returnFocus(ui.start, ui.runHeading);
    }
  }
}

// Cancelling asks first, in the box, instead of a dialog of the browser.
function askCancel() {
  state.cancelAsked = true;
  render();
  ui.cancelYes.focus();
}

function keepRunning() {
  state.cancelAsked = false;
  render();
  returnFocus(ui.cancel, ui.runHeading);
}

async function cancelRun() {
  state.cancelAsked = false;
  try {
    state.run = await callApi("/api/run/cancel");
  } catch (error) {
    if (!connectionFailure(error)) {
      state.runError = error.code;
    }
  }
  render();
  returnFocus(ui.cancel, ui.runHeading);
}

async function quit() {
  state.quitKey = null;
  ui.quit.disabled = true;
  try {
    await callApi("/api/shutdown");
    state.connected = false;
    stopHeartbeat();
    stopPolling();
    state.connectionKey = "status.stopped";
  } catch (error) {
    if (!connectionFailure(error)) {
      state.quitKey = error.code === "RUN_ACTIVE" ? "quit.blocked" : null;
      if (state.quitKey === null) {
        state.runError = error.code;
      }
    }
  }
  render();
}

// With startFromField, a path from a form field that cannot be listed falls
// back to the home folder, so that the browser always has a place to start.
async function loadFolder(path, startFromField = false) {
  const browser = state.browser;
  if (browser === null) {
    return;
  }
  browser.loading = true;
  browser.error = null;
  renderBrowserList();
  render();
  try {
    const listing = await callApi("/api/folders", path ? { path } : {});
    if (state.browser !== browser) {
      return;
    }
    browser.path = listing.path;
    browser.parent = listing.parent;
    browser.folders = Array.isArray(listing.folders) ? listing.folders : [];
    browser.truncated = listing.truncated === true;
  } catch (error) {
    if (connectionFailure(error)) {
      state.browser = null;
    } else if (startFromField && path) {
      await loadFolder(null);
      return;
    } else {
      browser.error = error.code;
    }
  }
  browser.loading = false;
  renderBrowserList();
  render();
}

function openBrowser(target, opener) {
  const field = target === "input" ? ui.inputPath : ui.outputParent;
  state.browser = {
    target,
    opener,
    path: null,
    parent: null,
    folders: [],
    truncated: false,
    loading: true,
    error: null,
  };
  render();
  ui.browserHeading.focus();
  loadFolder(field.value.trim() || null, true);
}

function closeBrowser() {
  const opener = state.browser?.opener;
  state.browser = null;
  renderBrowserList();
  render();
  opener?.focus();
}

function chooseFolder() {
  const browser = state.browser;
  if (browser?.path) {
    const field = browser.target === "input" ? ui.inputPath : ui.outputParent;
    field.value = browser.path;
    field.dispatchEvent(new Event("input"));
  }
  closeBrowser();
}

function changeLanguage(language) {
  if (LANGUAGES.includes(language)) {
    state.language = language;
    writeStorage(LANGUAGE_STORAGE, language);
    render();
  }
}

// A change in a field clears a refused request, a stop or a cancellation
// that the page showed, and the check that no longer matches; a change in
// the third box asks for its confirmation again.
function fieldChanged(event) {
  if (state.check !== null && !isCheckCurrent()) {
    state.check = null;
  }
  state.runError = null;
  state.editedSinceRun = true;
  if (state.run.state === "failed" || state.run.state === "cancelled") {
    state.run = { state: "idle" };
  }
  if (event?.target !== ui.inputPath) {
    state.outputDecided = false;
  }
  render();
}

function connect() {
  for (const language of LANGUAGES) {
    const option = document.createElement("option");
    option.value = language;
    option.lang = language;
    ui.language.append(option);
  }
  const zones = typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];
  ui.timezoneList.replaceChildren(
    ...zones.map((zone) => {
      const option = document.createElement("option");
      option.value = zone;
      return option;
    }),
  );
  ui.outputName.value = defaultOutputName(new Date());
  ui.language.addEventListener("change", () => changeLanguage(ui.language.value));
  ui.quit.addEventListener("click", quit);
  ui.check.addEventListener("click", runCheck);
  ui.snapshotDecide.addEventListener("click", () => decide("snapshot"));
  ui.outputDecide.addEventListener("click", () => decide("output"));
  ui.start.addEventListener("click", startRun);
  ui.cancel.addEventListener("click", askCancel);
  ui.cancelYes.addEventListener("click", cancelRun);
  ui.cancelNo.addEventListener("click", keepRunning);
  ui.openFolder.addEventListener("click", () => openOutput("folder"));
  ui.openStartHere.addEventListener("click", () => openOutput("start_here"));
  ui.bundle.addEventListener("click", makeBundle);
  ui.toolsToggle.addEventListener("click", () => {
    state.toolsOpen = !state.toolsOpen;
    render();
  });
  ui.inputBrowse.addEventListener("click", () => openBrowser("input", ui.inputBrowse));
  ui.outputBrowse.addEventListener("click", () => openBrowser("output", ui.outputBrowse));
  ui.browserUp.addEventListener("click", () => loadFolder(state.browser?.parent));
  ui.browserChoose.addEventListener("click", chooseFolder);
  ui.browserClose.addEventListener("click", closeBrowser);
  ui.browser.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeBrowser();
    }
  });
  ui.cancelConfirm.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      keepRunning();
    }
  });
  for (const field of [ui.inputPath, ui.outputParent, ui.outputName, ui.timezone]) {
    field.addEventListener("input", fieldChanged);
  }
  ui.safePack.addEventListener("change", fieldChanged);
}

async function start() {
  state.launchKey = readLaunchKey();
  const catalogs = await Promise.all(LANGUAGES.map(loadCatalog));
  state.catalogs = Object.fromEntries(
    LANGUAGES.map((language, index) => [language, catalogs[index]]),
  );
  state.language = chooseLanguage(
    LANGUAGES,
    readStorage(LANGUAGE_STORAGE),
    navigator.languages ?? [navigator.language],
  );
  connect();
  render();
  try {
    const status = await callApi("/api/status");
    state.productVersion =
      typeof status.product_version === "string" ? status.product_version : null;
    // The product's default, as the CLI takes it (stage A5a).
    if (typeof status.default_timezone === "string" && ui.timezone.value === "") {
      ui.timezone.value = status.default_timezone;
    }
    state.connected = true;
    state.connectionKey = "status.connected";
    startHeartbeat();
    state.run = await callApi("/api/run/status");
    // Speak only about changes that happen while the page is open.
    state.announced = announcement(state.run)?.id ?? null;
    if (ACTIVE_STATES.includes(state.run.state)) {
      startPolling();
    } else if (FINISHED_STATES.includes(state.run.state)) {
      checkOutput();
    }
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

start();
