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
  HELP_SECTIONS,
  HELP_STEPS,
  TERMINAL_STATES,
  announcement,
  boxStates,
  boxSummary,
  boxesToConfirm,
  checkMessages,
  checkParts,
  connectionMessages,
  controls,
  defaultOutputName,
  errorBox,
  errorMessages,
  familyRows,
  findingMessages,
  formatElapsed,
  foundChoices,
  helpReturnTarget,
  helpSteps,
  nextLine,
  nextLineKind,
  nextOutputName,
  outputCheckMessages,
  placeMessages,
  progressMessage,
  resultDetails,
  resultRows,
  resultTotal,
  runSummary,
  shouldFocusResult,
  snapshotRows,
  stalledSeconds,
  stepRows,
  storeMessages,
  warningMessages,
} from "./flow.mjs";

const LANGUAGES = ["en", "ja"];
const LAUNCH_KEY_HEADER = "X-Launch-Key";
const LAUNCH_KEY_STORAGE = "launchKey";
const LANGUAGE_STORAGE = "language";
const HINTS_STORAGE = "hints";
const HEARTBEAT_INTERVAL_MS = 30000;
const POLL_INTERVAL_MS = 1000;
// How often the page asks for the answer of the system's dialog (stage B3a).
const CHOOSE_POLL_MS = 500;
// How long a step of "How to use" lights up its box.
const SPOT_MS = 2000;
// How long the page waits after the folder for the output is typed before it
// asks the server about it (stage B4a).
const PLACE_DELAY_MS = 300;
// The information buttons, by the names of their ids (stage B1b), with the
// Snapshot Store and the default place (stage B4a).
const INFOS = ["how", "timezone", "pack", "exit", "tools", "store", "place"];

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
  chooseZip: byId("choose-zip"),
  chooseFolder: byId("choose-folder"),
  inputPath: byId("input-path"),
  check: byId("check-button"),
  checkResult: byId("check-result"),
  checkChoices: byId("check-choices"),
  extractArea: byId("extract-area"),
  extractConfirm: byId("extract-confirm"),
  snapshotDecide: byId("snapshot-decide"),
  snapshotHeading: byId("snapshot-heading"),
  storePath: byId("store-path"),
  storeCreate: byId("store-create"),
  storeOpen: byId("store-open"),
  storeOpenOther: byId("store-open-other"),
  storeCreateNew: byId("store-create-new"),
  storeCheck: byId("store-check"),
  storeResult: byId("store-result"),
  storeList: byId("store-list"),
  storeRows: byId("store-rows"),
  outputHeading: byId("output-heading"),
  browser: byId("browser"),
  browserHeading: byId("browser-heading"),
  browserPath: byId("browser-path"),
  browserHint: byId("browser-hint"),
  browserUp: byId("browser-up"),
  browserChoose: byId("browser-choose"),
  browserClose: byId("browser-close"),
  browserMessage: byId("browser-message"),
  browserList: byId("browser-list"),
  outputParent: byId("output-parent"),
  outputBrowse: byId("output-browse"),
  outputParentNote: byId("output-parent-note"),
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
  familyTotal: byId("family-total"),
  familyTotalText: byId("family-total-text"),
  familyTotalCount: byId("family-total-count"),
  resultsPanel: byId("results-panel"),
  runExitRow: byId("run-exit-row"),
  hintsToggle: byId("hints-toggle"),
  hints: document.querySelectorAll(".hint"),
  helpButton: byId("help-button"),
  helpPanel: byId("help-panel"),
  helpClose: byId("help-close"),
  helpSections: Object.fromEntries(
    HELP_SECTIONS.map((name) => [
      name,
      { nav: byId(`help-nav-${name}`), section: byId(`help-${name}`), heading: byId(`help-${name}-heading`) },
    ]),
  ),
  walk: Object.fromEntries(
    HELP_STEPS.map((step) => [
      step,
      { button: byId(`walk-${step}`), state: byId(`walk-${step}-state`) },
    ]),
  ),
  copyButtons: document.querySelectorAll(".copy-button"),
  aiHelp: byId("ai-help-button"),
  faqHelp: byId("faq-help-button"),
  infos: Object.fromEntries(
    INFOS.map((name) => [name, { button: byId(`${name}-info-button`), region: byId(`${name}-info`) }]),
  ),
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
  // The system's dialog that is open ("zip" or "folder"), the code of a
  // dialog that did not work, whether this system has no dialog, so that the
  // buttons open the folder list of the page instead, and the place that the
  // last dialog or the folder list chose (stage B3a).
  choosing: null,
  chooserError: null,
  chooserMissing: false,
  chosenPath: null,
  // What the open dialog, or the folder list, chooses: "input", the store to
  // open ("store-open"), the place of a new store ("store-place"), or the
  // folder for the output ("output") (stage B4a).
  choosingFor: null,
  // The default place of the outputs, from the server, which holds the
  // default place of the store (stage B4a).
  defaultFolder: null,
  // The Snapshot Store of the second box (stage B4a): the error of the last
  // dialog for it, whether the page is asking the server, the answer of the
  // store or of the place for a new one, and the answer of its check.
  store: { chooserError: null, busy: false, answer: null, checked: null },
  // The server's answer for the folder for the output, the error of the last
  // dialog for it, and the timer of the next question (stage B4a).
  place: null,
  placeChooserError: null,
  placeTimer: null,
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
  // The open part of the help panel, or null when it is closed, and the
  // button that opened it, to return focus to (stage B1b).
  help: null,
  helpOpener: null,
  // Whether the tips under the box headings show; kept for this tab only,
  // until the settings of an earlier launch come (stage B4a).
  hintsOn: true,
  // The information buttons that are open.
  infos: new Set(),
  // The message beside the example question that was copied last.
  copy: null,
  // The step of "How to use" whose box lights up, and its timer.
  spot: null,
  spotTimer: null,
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
// makes screen readers repeat it, so text changes only when it differs. A
// line is its text, or its text with a kind that gives it a mark and a color
// (stage B3b).
function replaceLines(container, lines) {
  const items = lines.map((line) => (typeof line === "string" ? { text: line, className: "" } : line));
  const current = Array.from(container.children, (line) => [line.textContent, line.className]);
  if (
    current.length === items.length &&
    current.every(([text, className], index) => text === items[index].text && className === items[index].className)
  ) {
    return;
  }
  container.replaceChildren(
    ...items.map((item) => {
      const line = document.createElement("p");
      line.textContent = item.text;
      line.className = item.className;
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

// The place of the Export: a place that a dialog or the folder list chose is
// used as it is, and the spaces around a place that was typed or pasted are
// left out (stage B3a).
function inputValue() {
  const value = ui.inputPath.value;
  return value === state.chosenPath ? value : value.trim();
}

// The check of the Export belongs to the first box only: the timezone of the
// third box is checked when the run starts, as the run checks it.
function isCheckCurrent() {
  return state.check !== null && state.check.path === inputValue();
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
  // The timezone data that the check found missing belongs to the third box,
  // and the first box is not ready without it (stage B3b).
  const parts = checked && state.check.error === undefined ? checkParts(state.check) : null;
  const timezoneProblem = parts !== null && parts.timezone !== null;
  const ready = parts !== null && !parts.stops && !timezoneProblem;
  // An extracted folder needs the confirmation that its extraction was
  // complete; a ZIP file does not. Only the page asks for it (stage B3a).
  const extractNeeded = ready && state.check.kind === "folder";
  const checkedReady = ready && (!extractNeeded || ui.extractConfirm.checked);
  return {
    connected: state.connected,
    runState: run.state,
    starting: state.starting,
    checking: state.checking,
    choosing: state.choosing !== null,
    choosingFolder: state.choosing !== null && state.choosingFor !== "input",
    outputBusy: outputBusy(),
    checkedReady,
    extractNeeded,
    extractConfirmed: ui.extractConfirm.checked,
    exportReady: checkedReady && requestBox !== "export",
    exportProblem: (checked && (state.check.error !== undefined || parts.stops)) || requestBox === "export",
    timezoneProblem,
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

function renderCheck(current) {
  const lines = [];
  // The dialog for the store or the output speaks in its own box (stage B4a).
  const choosingExport = state.choosing !== null && state.choosingFor === "input";
  if (choosingExport) {
    lines.push(t("choose.open"));
  } else if (state.chooserError !== null) {
    lines.push(...errorLines(state.chooserError));
  }
  // A stop in the first box shows in its own area; the lines of the check
  // before it would read as the answer to it.
  const stopped =
    (state.run.state === "failed" && current.failedBox === "export") || current.requestBox === "export";
  if (choosingExport || stopped) {
    // Nothing more.
  } else if (state.checking) {
    lines.push(t("check.running"));
  } else if (state.check?.error !== undefined) {
    lines.push(...errorLines(state.check.error));
  } else if (state.check) {
    // Red, then yellow, then what the check found, each with its mark
    // (stage B3b).
    for (const line of checkMessages(state.check)) {
      lines.push({ text: describe(line.message), className: `m-${line.kind}${line.start ? " start" : ""}` });
    }
  }
  replaceLines(ui.checkResult, lines);
  ui.extractArea.hidden = !current.extractNeeded;
  // The Exports of a mixed input that can be chosen, each with its button
  // (stage B3c).
  const shown = !choosingExport && !stopped && !state.checking && isCheckCurrent();
  renderChoices(shown ? foundChoices(state.check) : []);
}

// The buttons change only when the Exports change, so that focus stays.
function renderChoices(choices) {
  const key = JSON.stringify(choices.map((choice) => [describe(choice.message), choice.path]));
  ui.checkChoices.hidden = choices.length === 0;
  if (ui.checkChoices.dataset.key === key) {
    return;
  }
  ui.checkChoices.dataset.key = key;
  ui.checkChoices.replaceChildren(
    ...choices.map((choice) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = describe(choice.message);
      // The page checks the chosen Export at once; focus goes to the heading
      // of the box, as this button goes away with the new check.
      button.addEventListener("click", () => useChosenExport(choice.path, ui.inputHeading));
      return button;
    }),
  );
}

// Lines with a kind, as the check of the Export gives them (stage B3b).
function kindLines(lines) {
  return lines.map((line) => ({
    text: describe(line.message),
    className: `m-${line.kind}${line.start ? " start" : ""}`,
  }));
}

// The Snapshot Store of the second box (stage B4a): its place, the buttons
// for a store that is open or not, its lines, and its Snapshots.
function renderStore() {
  const store = state.store;
  const answer = store.answer;
  const opened = answer?.state === "store";
  setText(ui.storePath, typeof answer?.path === "string" ? answer.path : "");
  ui.storeCreate.hidden = opened;
  ui.storeOpen.hidden = opened;
  ui.storeOpenOther.hidden = !opened;
  ui.storeCreateNew.hidden = !opened;
  ui.storeCheck.hidden = !opened;
  const choosing = state.choosing !== null && String(state.choosingFor).startsWith("store");
  replaceLines(ui.storeResult, kindLines(storeMessages({ ...store, choosing })));
  const rows = snapshotRows(answer);
  ui.storeList.hidden = rows.length === 0;
  const key = JSON.stringify([state.language, rows]);
  if (ui.storeRows.dataset.key === key) {
    return;
  }
  ui.storeRows.dataset.key = key;
  ui.storeRows.replaceChildren(
    ...rows.map((row) => {
      const tableRow = document.createElement("tr");
      const order = document.createElement("th");
      order.scope = "row";
      order.className = "nowrap";
      order.textContent = row.order === null ? "—" : t("store.row_order", { order: formatNumber(row.order) });
      const label = document.createElement("td");
      label.textContent = row.label;
      const time = document.createElement("td");
      time.className = "nowrap";
      time.textContent = row.time;
      const files = document.createElement("td");
      files.className = "n";
      files.textContent = row.files === null ? "—" : formatNumber(row.files);
      tableRow.append(order, label, time, files);
      return tableRow;
    }),
  );
}

// The lines under the folder for the output: its dialog, the default place
// that a run makes, and a cloud that may copy it (stage B4a).
function renderPlace() {
  const lines = [];
  if (state.choosing !== null && state.choosingFor === "output") {
    lines.push({ text: t("choose.open"), className: "m-info start" });
  } else if (state.placeChooserError !== null) {
    const messages = errorMessages(state.placeChooserError);
    lines.push(...kindLines(messages.map((line, index) => ({ kind: "error", start: index === 0, message: line }))));
  }
  lines.push(...kindLines(placeMessages(state.place, ui.outputParent.value.trim())));
  replaceLines(ui.outputParentNote, lines);
}

function renderBrowser() {
  const browser = state.browser;
  ui.browser.hidden = browser === null;
  if (browser === null) {
    return;
  }
  // For the Export, the list also shows ZIP files (stage B3a).
  const exportList = browser.target === "input";
  setText(ui.browserHeading, t(exportList ? "browser.heading_export" : "browser.heading"));
  setText(ui.browserHint, t(exportList ? "browser.hint_export" : "browser.hint"));
  ui.browserPath.textContent = browser.path ?? "";
  ui.browserUp.disabled = browser.loading || !browser.parent;
  ui.browserChoose.disabled = browser.loading || !browser.path;
  const count = Math.max(browser.folders.length, browser.zips.length);
  let message = "";
  if (browser.loading) {
    message = t("browser.loading");
  } else if (browser.error !== null) {
    message = errorLines(browser.error).join(" ");
  } else if (count === 0) {
    message = t(exportList ? "browser.empty_export" : "browser.empty");
  } else if (browser.truncated) {
    message = t(exportList ? "browser.truncated_export" : "browser.truncated", { count: formatNumber(count) });
  }
  setText(ui.browserMessage, message);
}

function childPath(parent, name) {
  const separator = parent.includes("\\") && !parent.includes("/") ? "\\" : "/";
  return parent.endsWith(separator) ? `${parent}${name}` : `${parent}${separator}${name}`;
}

function listItem(name, kind, action) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.className = kind;
  button.textContent = name;
  button.addEventListener("click", action);
  item.append(button);
  return item;
}

// A folder opens; a ZIP file is chosen as the Export at once.
function renderBrowserList() {
  const browser = state.browser;
  const shown = browser !== null && !browser.loading && browser.error === null;
  const folders = shown ? browser.folders : [];
  const zips = shown ? browser.zips : [];
  ui.browserList.replaceChildren(
    ...folders.map((name) => listItem(name, "folder", () => loadFolder(childPath(browser.path, name)))),
    ...zips.map((name) => listItem(name, "zip", () => chooseFromList(childPath(browser.path, name)))),
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
    element.className = `box s-${boxState}${state.spot === box ? " spot" : ""}`;
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
  ui.nextLine.className = `next-line k-${nextLineKind(current, states)}`;
}

// A stop: its lines in the box that it concerns, and the other boxes clear.
// The timezone data that the pre-run check found missing shows in the third
// box, as what keeps a run from starting (stage B3b).
function renderErrors(current) {
  const run = state.run;
  let box = null;
  let lines = [];
  let heading = "error.heading";
  if (run.state === "failed") {
    box = current.failedBox;
    lines = errorLines(run.error_code, run.error_detail);
  } else if (state.runError !== null) {
    box = current.requestBox;
    lines = errorLines(state.runError);
  } else if (current.timezoneProblem && !current.exportProblem) {
    box = "output";
    lines = findingMessages(checkParts(state.check).timezone).map(describe);
    heading = "error.heading_check";
  }
  for (const [name, error] of Object.entries(ui.errors)) {
    const shown = name === box || (box === "snapshot" && name === "run");
    error.area.hidden = !shown;
    setText(error.heading, t(heading));
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
  records.textContent = row.records === null ? "—" : formatNumber(row.records);
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
  const total = resultTotal(run);
  ui.familyTotal.hidden = total === null;
  setText(ui.familyTotalText, total === null ? "" : describe(total));
  setText(ui.familyTotalCount, total === null ? "" : formatNumber(total.params.total));
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
  ui.runExitRow.hidden = summary.exitCode === null;
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
  // The warnings of the run show also while the check runs or after it
  // stopped (stage B2c).
  const warnings = finished ? warningMessages(state.run.result).map(describe) : [];
  if (finished && output.checking) {
    checkLines.push(t("output_check.running"), ...warnings);
  } else if (finished && output.checkError !== null) {
    checkLines.push(...errorLines(output.checkError), ...warnings);
  } else if (finished && output.check !== null) {
    checkLines.push(...outputCheckMessages(output.check, state.run.result).map(describe));
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

// The help panel: open or closed, its part, and the steps of "How to use".
function renderHelp(states, current) {
  const open = state.help !== null;
  ui.helpPanel.hidden = !open;
  document.body.classList.toggle("help-open", open);
  ui.helpButton.setAttribute("aria-expanded", String(open));
  for (const [name, part] of Object.entries(ui.helpSections)) {
    part.section.hidden = name !== state.help;
    if (name === state.help) {
      part.nav.setAttribute("aria-current", "true");
    } else {
      part.nav.removeAttribute("aria-current");
    }
  }
  const steps = helpSteps(states, current.runState);
  for (const [step, walk] of Object.entries(ui.walk)) {
    walk.button.parentElement.className = `walk-${steps[step]}`;
    const words = steps[step] === "done" ? "step_state.done" : steps[step] === "current" ? "badge.current" : null;
    setText(walk.state, words === null ? "" : t(words));
  }
  ui.resultsPanel.classList.toggle("spot", state.spot === "results");
  for (const button of ui.copyButtons) {
    const copied = state.copy !== null && state.copy.id === button.id;
    setText(byId(`${button.id}-result`), copied ? t(state.copy.key) : "");
  }
}

function renderHints() {
  ui.hintsToggle.checked = state.hintsOn;
  for (const hint of ui.hints) {
    hint.hidden = !state.hintsOn;
  }
}

// An information button opens what it explains under it. The meaning of the
// exit code shows only while the exit code shows.
function renderInfos() {
  for (const [name, info] of Object.entries(ui.infos)) {
    const open = state.infos.has(name) && (name !== "exit" || !ui.runExitRow.hidden);
    info.button.setAttribute("aria-expanded", String(open));
    info.region.hidden = !open;
  }
}

function renderPackFile() {
  ui.packFile.hidden = !ui.safePack.checked;
  setText(ui.packFile, ui.safePack.checked ? t("pack.file", { name: ui.outputName.value.trim() }) : "");
}

function renderControls(states, current) {
  const enabled = controls(current, states);
  for (const field of [ui.inputPath, ui.extractConfirm, ui.outputParent, ui.outputName, ui.timezone, ui.safePack]) {
    field.disabled = !enabled.form;
  }
  ui.chooseZip.disabled = !enabled.choose;
  ui.chooseFolder.disabled = !enabled.choose;
  for (const button of ui.checkChoices.children) {
    button.disabled = !enabled.choose;
  }
  ui.outputBrowse.disabled = !enabled.browse;
  for (const button of [ui.storeCreate, ui.storeOpen, ui.storeOpenOther, ui.storeCreateNew, ui.storeCheck]) {
    button.disabled = !enabled.choose || state.store.busy;
  }
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
  renderCheck(current);
  renderStore();
  renderPlace();
  renderBrowser();
  renderErrors(current);
  renderRun(states, current);
  renderSteps();
  renderResults();
  renderOutput();
  renderPackFile();
  renderControls(states, current);
  renderHelp(states, current);
  renderHints();
  renderInfos();
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
      // A run may have made the default place (stage B4a).
      lookPlace();
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

// Focus goes back to the button that started the check: the check button,
// or the button that chose the Export.
async function runCheck(focusTarget = ui.check) {
  const path = inputValue();
  state.checking = true;
  state.check = null;
  state.runError = null;
  state.chooserError = null;
  // A new check is a change in the first box: a stop or a cancellation that
  // the page showed gives way to it.
  state.editedSinceRun = true;
  if (state.run.state === "failed" || state.run.state === "cancelled") {
    state.run = { state: "idle" };
  }
  // Each check asks again that an extracted folder is complete.
  ui.extractConfirm.checked = false;
  render();
  try {
    const answer = await callApi("/api/check-input", { input: path });
    state.check = {
      path,
      ready: answer.ready === true,
      // A ZIP file or a folder, as the server found it, not from the name.
      kind: answer.input_kind === "zip" || answer.input_kind === "folder" ? answer.input_kind : null,
      // The counts of the input, numbers only (stage B3b).
      counts: answer.counts !== null && typeof answer.counts === "object" ? answer.counts : null,
      // The places that the check found, for this page only (stage B3c).
      exportsFound: Array.isArray(answer.exports_found) ? answer.exports_found : [],
      notReadable: answer.not_readable !== null && typeof answer.not_readable === "object" ? answer.not_readable : null,
      findings: Array.isArray(answer.findings) ? answer.findings : [],
    };
  } catch (error) {
    if (!connectionFailure(error)) {
      state.check = { path, error: error.code };
    }
  } finally {
    state.checking = false;
    render();
    returnFocus(focusTarget, ui.inputHeading);
  }
}

const pause = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

// Put a chosen place in the field as it is and check it at once.
function useChosenExport(path, focusTarget) {
  ui.inputPath.value = path;
  state.chosenPath = path;
  ui.inputPath.dispatchEvent(new Event("input"));
  runCheck(focusTarget);
}

// The heading that takes focus after a dialog for ``purpose``, when its
// button cannot.
function purposeHeading(purpose) {
  return purpose === "input" ? ui.inputHeading : purpose === "output" ? ui.outputHeading : ui.snapshotHeading;
}

// The error of the last dialog, shown in the box of its purpose.
function setChooserError(purpose, code) {
  if (purpose === "input") {
    state.chooserError = code;
  } else if (purpose === "output") {
    state.placeChooserError = code;
  } else {
    state.store.chooserError = code;
  }
}

// Use a place that a dialog or the folder list chose: the Export, which the
// page checks at once (stage B3a), the store to open, the folder for a new
// store, or the folder for the output (stage B4a).
function usePlace(purpose, path, focusTarget) {
  if (purpose === "input") {
    useChosenExport(path, focusTarget);
  } else if (purpose === "store-open") {
    storeAction("open", path, focusTarget);
  } else if (purpose === "store-place") {
    storeAction("place", path, focusTarget);
  } else {
    ui.outputParent.value = path;
    ui.outputParent.dispatchEvent(new Event("input"));
    returnFocus(focusTarget, ui.outputHeading);
  }
}

// Open the system's dialog to choose a ZIP file or a folder, and ask for its
// answer until it closes (stage B3a); the store and the output choose
// folders with it too (stage B4a). Without a dialog, the folder list of the
// page opens instead.
async function chooseWithDialog(kind, purpose, button) {
  if (state.chooserMissing) {
    openBrowser(purpose, button);
    return;
  }
  state.choosing = kind;
  state.choosingFor = purpose;
  setChooserError(purpose, null);
  render();
  let chosen = null;
  let failure = null;
  try {
    await callApi("/api/choose", { kind });
    let answer = { state: "open" };
    while (answer.state === "open" && state.connected) {
      await pause(CHOOSE_POLL_MS);
      answer = await callApi("/api/choose/status");
    }
    if (answer.state === "failed") {
      failure = typeof answer.error_code === "string" ? answer.error_code : null;
    } else if (answer.state === "closed" && typeof answer.path === "string") {
      chosen = answer.path;
    }
  } catch (error) {
    if (!connectionFailure(error)) {
      failure = error.code;
    }
  }
  state.choosing = null;
  state.choosingFor = null;
  setChooserError(purpose, failure);
  if (failure === "CHOOSER_NOT_AVAILABLE") {
    state.chooserMissing = true;
    openBrowser(purpose, button);
  } else if (chosen !== null) {
    usePlace(purpose, chosen, button);
  } else {
    render();
    returnFocus(button, purposeHeading(purpose));
  }
}

// Open a store, check the place for a new one, or check the open store, as
// the CLI's snapshot commands do (stage B4a). The page writes nothing in a
// store; a problem of the store is an answer that it shows beside it.
async function storeAction(action, path, focusTarget) {
  const store = state.store;
  store.busy = true;
  store.chooserError = null;
  if (action !== "check") {
    store.checked = null;
  }
  render();
  try {
    const answer = await callApi(`/api/store/${action}`, { path });
    if (action === "check") {
      store.checked = answer;
    } else {
      store.answer = answer;
    }
  } catch (error) {
    if (!connectionFailure(error)) {
      const failed = { state: "error", path, error_code: error.code };
      if (action === "check") {
        store.checked = failed;
      } else {
        store.answer = failed;
      }
    }
  } finally {
    store.busy = false;
    render();
    // The buttons of a store that is open differ from those without one, so
    // the button that was pressed may be gone.
    if (focusTarget !== null) {
      returnFocus(canTakeFocus(focusTarget) ? focusTarget : ui.snapshotHeading, ui.snapshotHeading);
    }
  }
}

// Ask the server about the folder for the output: whether it is there, and
// whether a cloud may copy it (stage B4a).
async function lookPlace() {
  window.clearTimeout(state.placeTimer);
  state.placeTimer = null;
  const path = ui.outputParent.value.trim();
  if (path === "" || !state.connected) {
    state.place = null;
    render();
    return;
  }
  try {
    const answer = await callApi("/api/place", { path });
    state.place = { ...answer, path };
  } catch (error) {
    if (!connectionFailure(error)) {
      state.place = null;
    }
  }
  render();
}

function schedulePlace() {
  window.clearTimeout(state.placeTimer);
  state.placeTimer = window.setTimeout(lookPlace, PLACE_DELAY_MS);
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
  state.infos.delete("exit");
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
      input: inputValue(),
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

// The folder that holds a place, from its text alone, or null at the top.
function parentPath(path) {
  const trimmed = path.replace(/[\\/]+$/, "");
  const parent = trimmed.replace(/[\\/][^\\/]*$/, "");
  return parent === "" || parent === trimmed ? null : parent;
}

// With startFromField, a path from a form field that cannot be listed, such
// as a chosen ZIP file, falls back to the folder that holds it, and then to
// the home folder, so that the browser always has a place to start.
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
    const request = path ? { path } : {};
    if (browser.target === "input") {
      request.zips = true;
    }
    const listing = await callApi("/api/folders", request);
    if (state.browser !== browser) {
      return;
    }
    browser.path = listing.path;
    browser.parent = listing.parent;
    browser.folders = Array.isArray(listing.folders) ? listing.folders : [];
    browser.zips = Array.isArray(listing.zips) ? listing.zips : [];
    browser.truncated = listing.truncated === true;
  } catch (error) {
    if (connectionFailure(error)) {
      state.browser = null;
    } else if (startFromField && path) {
      const parent = parentPath(path);
      await loadFolder(parent, parent !== null);
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
  // The list starts at the place of its purpose: the Export, the store
  // (stage B4a), or the folder for the output.
  const start =
    target === "input"
      ? ui.inputPath.value
      : target === "output"
        ? ui.outputParent.value
        : state.store.answer?.path ?? state.defaultFolder ?? "";
  state.browser = {
    target,
    opener,
    path: null,
    parent: null,
    folders: [],
    zips: [],
    truncated: false,
    loading: true,
    error: null,
  };
  render();
  ui.browserHeading.focus();
  loadFolder(start.trim() || null, true);
}

function closeBrowser() {
  const opener = state.browser?.opener;
  state.browser = null;
  renderBrowserList();
  render();
  opener?.focus();
}

// A place chosen in the folder list, for the purpose that opened it: the
// Export, which the page checks at once (stage B3a), the store, or the folder
// for the output (stage B4a).
function chooseFromList(path) {
  const browser = state.browser;
  if (browser === null || !path) {
    closeBrowser();
    return;
  }
  const opener = browser.opener;
  closeBrowser();
  usePlace(browser.target, path, opener);
}

// Open the help panel at one of its parts; focus goes to that part's heading.
function openHelp(section, opener) {
  state.help = section;
  state.helpOpener = opener;
  state.copy = null;
  render();
  ui.helpSections[section].heading.focus();
}

// A button can take focus back while it is on the page, shown, and enabled.
function canTakeFocus(element) {
  return element.isConnected && !element.disabled && element.closest("[hidden]") === null;
}

function closeHelp() {
  const opener = state.helpOpener;
  state.help = null;
  state.helpOpener = null;
  state.copy = null;
  render();
  const target = helpReturnTarget(opener === null ? null : { usable: canTakeFocus(opener) });
  (target === "opener" ? opener : ui.helpButton).focus();
}

// Closed with the Help button itself, the panel leaves focus on that button.
function toggleHelp() {
  if (state.help === null) {
    openHelp("steps", ui.helpButton);
  } else {
    state.helpOpener = ui.helpButton;
    closeHelp();
  }
}

function showHelpSection(section) {
  state.help = section;
  state.copy = null;
  render();
  ui.helpSections[section].heading.focus();
}

// Light up the box of a step for a moment; focus stays in the help panel.
function spot(step) {
  window.clearTimeout(state.spotTimer);
  state.spot = step;
  render();
  const target = step === "results" ? ui.resultsPanel : ui.boxes[step];
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  target.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
  state.spotTimer = window.setTimeout(() => {
    state.spot = null;
    state.spotTimer = null;
    render();
  }, SPOT_MS);
}

// Copy an example question on this computer only. Safari accepts writeText
// only right after the click, so nothing is awaited before it. The line beside
// the button is emptied first, so that a second copy is announced again.
async function copyExample(button) {
  const text = byId(button.dataset.copy)?.textContent ?? "";
  state.copy = null;
  render();
  try {
    await navigator.clipboard.writeText(text);
    state.copy = { id: button.id, key: "ai.copied" };
  } catch {
    state.copy = { id: button.id, key: "ai.copy_failed" };
  }
  render();
}

function toggleInfo(name) {
  if (state.infos.has(name)) {
    state.infos.delete(name);
  } else {
    state.infos.add(name);
  }
  render();
}

function closeInfo(name) {
  if (state.infos.delete(name)) {
    render();
    ui.infos[name].button.focus();
  }
}

function changeHints() {
  state.hintsOn = ui.hintsToggle.checked;
  writeStorage(HINTS_STORAGE, state.hintsOn ? "on" : "off");
  render();
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
  if (event?.target === ui.inputPath) {
    state.chooserError = null;
  } else if (event?.target !== ui.extractConfirm) {
    state.outputDecided = false;
  }
  if (event?.target === ui.outputParent) {
    state.placeChooserError = null;
    schedulePlace();
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
  ui.chooseZip.addEventListener("click", () => chooseWithDialog("zip", "input", ui.chooseZip));
  ui.chooseFolder.addEventListener("click", () => chooseWithDialog("folder", "input", ui.chooseFolder));
  // The store and the folder for the output are folders (stage B4a).
  ui.storeOpen.addEventListener("click", () => chooseWithDialog("folder", "store-open", ui.storeOpen));
  ui.storeOpenOther.addEventListener("click", () => chooseWithDialog("folder", "store-open", ui.storeOpenOther));
  ui.storeCreate.addEventListener("click", () => chooseWithDialog("folder", "store-place", ui.storeCreate));
  ui.storeCreateNew.addEventListener("click", () => chooseWithDialog("folder", "store-place", ui.storeCreateNew));
  ui.storeCheck.addEventListener("click", () => storeAction("check", state.store.answer?.path, ui.storeCheck));
  ui.check.addEventListener("click", () => runCheck());
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
  ui.outputBrowse.addEventListener("click", () => chooseWithDialog("folder", "output", ui.outputBrowse));
  ui.browserUp.addEventListener("click", () => loadFolder(state.browser?.parent));
  ui.browserChoose.addEventListener("click", () => chooseFromList(state.browser?.path));
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
  ui.extractConfirm.addEventListener("change", fieldChanged);
  ui.hintsToggle.addEventListener("change", changeHints);
  ui.helpButton.addEventListener("click", toggleHelp);
  ui.helpClose.addEventListener("click", closeHelp);
  ui.helpPanel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeHelp();
    }
  });
  for (const [name, part] of Object.entries(ui.helpSections)) {
    part.nav.addEventListener("click", () => showHelpSection(name));
  }
  for (const [step, walk] of Object.entries(ui.walk)) {
    walk.button.addEventListener("click", () => spot(step));
  }
  for (const button of ui.copyButtons) {
    button.addEventListener("click", () => copyExample(button));
  }
  ui.aiHelp.addEventListener("click", () => openHelp("ai", ui.aiHelp));
  ui.faqHelp.addEventListener("click", () => openHelp("faq", ui.faqHelp));
  for (const [name, info] of Object.entries(ui.infos)) {
    info.button.addEventListener("click", () => toggleInfo(name));
    for (const element of [info.button, info.region]) {
      element.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
          closeInfo(name);
        }
      });
    }
  }
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
  // The tips show unless this tab turned them off.
  state.hintsOn = readStorage(HINTS_STORAGE) !== "off";
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
    // The default place, which only the GUI has (stage B4a): the outputs go
    // in it, and the store in its folder snapshots.
    if (typeof status.default_output_parent === "string") {
      state.defaultFolder = status.default_output_parent;
      if (ui.outputParent.value === "") {
        ui.outputParent.value = status.default_output_parent;
      }
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
    // The store at the default place, if there is one, and the folder for
    // the output (stage B4a).
    if (state.defaultFolder !== null) {
      storeAction("place", state.defaultFolder, null);
    }
    lookPlace();
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

start();
