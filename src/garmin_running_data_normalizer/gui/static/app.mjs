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
  afterChange,
  apartReport,
  announcement,
  boxStates,
  boxSummary,
  boxesSetBySettings,
  boxesToConfirm,
  bundlePlan,
  changeMessages,
  changePlan,
  changeRows,
  changedBox,
  checkMessages,
  decideHidden,
  checkParts,
  connectionMessages,
  controls,
  defaultOutputName,
  defaultSnapshotLabel,
  downloadSourceMessage,
  earlierChoices,
  errorBox,
  errorMessages,
  exportTime,
  familyRows,
  findingMessages,
  forgetOutcome,
  formatElapsed,
  foundChoices,
  helpReturnTarget,
  helpSteps,
  hintsShown,
  importFieldsShown,
  importProblem,
  lastName,
  launchSettings,
  localTimeIso,
  lockAge,
  lockOffered,
  movesProposedName,
  nameMessages,
  nextLine,
  nextLineKind,
  nextOutputName,
  outputCheckMessages,
  outputMissingRemembered,
  outputNameProblem,
  outputSetBySettings,
  outsideUrl,
  packMade,
  placeMessages,
  previousRows,
  primaryControl,
  progressBar,
  progressMessage,
  reportFacts,
  reportRows,
  reportUrl,
  resultDetails,
  resultRows,
  resultTotal,
  runSummary,
  sameContentNoted,
  settingsMessages,
  settingsPresentAfterRun,
  shouldFocusResult,
  signedChange,
  snapshotRows,
  stalledSeconds,
  stepRows,
  storeMessages,
  storeMissingRemembered,
  storeProblem,
  storeReady,
  storeSetBySettings,
  warningMessages,
} from "./flow.mjs";

const LANGUAGES = ["en", "ja"];
const LAUNCH_KEY_HEADER = "X-Launch-Key";
const LAUNCH_KEY_STORAGE = "launchKey";
const LANGUAGE_STORAGE = "language";
const HEARTBEAT_INTERVAL_MS = 30000;
const POLL_INTERVAL_MS = 1000;
// The time before an explanation that opened is given to its live region,
// after the region was emptied (stage C1).
const INFO_SPEAK_DELAY_MS = 100;
// How often the page asks for the answer of the system's dialog (stage B3a).
const CHOOSE_POLL_MS = 500;
// How long a step of "How to use" lights up its box.
const SPOT_MS = 2000;
// How long the page waits after the folder for the output is typed before it
// asks the server about it (stage B4a).
const PLACE_DELAY_MS = 300;
// How many free names the page tries for its own proposed name of the output
// (stage B5a).
const MAX_NAME_TRIES = 20;
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
  // The line of the report of a stop of the first and second box, after
  // the buttons that fix it (stage B6a).
  checkReport: byId("check-report"),
  checkChoices: byId("check-choices"),
  extractArea: byId("extract-area"),
  extractConfirm: byId("extract-confirm"),
  // The fields of an import and normalizing the Snapshots again (stage B4b-1).
  importArea: byId("import-area"),
  snapshotLabel: byId("snapshot-label"),
  downloadedAt: byId("downloaded-at"),
  downloadedAtHelp: byId("downloaded-at-help"),
  importResult: byId("import-result"),
  rerunArea: byId("rerun-area"),
  rerunText: byId("rerun-text"),
  rerunToggle: byId("rerun-toggle"),
  howSnapshots: byId("how-snapshots"),
  howSingle: byId("how-single"),
  howNote: byId("how-note"),
  storeArea: byId("store-area"),
  // Removing the lock file that a stopped import left (stage B4b-2).
  lockArea: byId("lock-area"),
  lockTime: byId("lock-time"),
  lockConfirm: byId("lock-confirm"),
  lockRemove: byId("lock-remove"),
  cancelConfirmText: byId("cancel-confirm-text"),
  snapshotDecide: byId("snapshot-decide"),
  snapshotHeading: byId("snapshot-heading"),
  storePath: byId("store-path"),
  storeCreate: byId("store-create"),
  storeOpen: byId("store-open"),
  storeOpenOther: byId("store-open-other"),
  // Looking again for a remembered store or folder that is not found
  // (stage B4c).
  storeSearch: byId("store-search"),
  storeCreateNew: byId("store-create-new"),
  storeCheck: byId("store-check"),
  storeResult: byId("store-result"),
  storeReport: byId("store-report"),
  storeSameNote: byId("store-same-note"),
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
  outputSearch: byId("output-search"),
  outputParentNote: byId("output-parent-note"),
  outputName: byId("output-name"),
  // What keeps the name from being a new folder (stage B5a).
  outputNameNote: byId("output-name-note"),
  timezone: byId("timezone"),
  timezoneList: byId("timezone-list"),
  safePack: byId("safe-pack"),
  packFile: byId("pack-file"),
  packMade: byId("pack-made"),
  packReveal: byId("pack-reveal"),
  packResult: byId("pack-result"),
  outputDecide: byId("output-decide"),
  runHeading: byId("run-heading"),
  resultHeading: byId("result-heading"),
  resultHeadline: byId("result-headline"),
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
  // The place of the Support Bundle, the file that it makes, and showing it
  // where it is saved (stage B5a).
  bundlePlace: byId("bundle-place"),
  bundleChoose: byId("bundle-choose"),
  bundlePlan: byId("bundle-plan"),
  bundleReveal: byId("bundle-reveal"),
  bundleRevealResult: byId("bundle-reveal-result"),
  // The output of the check and the Support Bundle of the fourth box, and
  // the change since the output before (stage B5b).
  targetHeading: byId("target-heading"),
  targetRun: byId("target-run"),
  targetRunName: byId("target-run-name"),
  targetEarlier: byId("target-earlier"),
  targetList: byId("target-list"),
  targetChosen: byId("target-chosen"),
  targetCheck: byId("target-check"),
  targetCheckResult: byId("target-check-result"),
  columnChange: byId("column-change"),
  familyTotalChange: byId("family-total-change"),
  resultsChange: byId("results-change"),
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
  // The settings of an earlier launch, and forgetting them (stage B4c).
  settingsStatus: byId("settings-status"),
  infoAnnouncer: byId("info-announcer"),
  forgetButton: byId("forget-button"),
  forgetConfirm: byId("forget-confirm"),
  forgetYes: byId("forget-yes"),
  forgetNo: byId("forget-no"),
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
  // The GitHub report (stage B5c): its table, its link, the button of the
  // fourth box, and the links to pages outside this app.
  reportValues: byId("report-values"),
  reportOpen: byId("report-open"),
  toolsReport: byId("tools-report"),
  outsideLinks: document.querySelectorAll("a[data-link]"),
  aroundLinks: [
    ["help.get_step1", byId("get-step1-before"), byId("get-step1-after")],
    ["report.security", byId("report-security-before"), byId("report-security-after")],
  ],
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
  store: { chooserError: null, busy: false, answer: null, checked: null, unlocked: false, unlockError: null },
  // The way to normalize: "snapshots" (the default, decision 20261011-10),
  // "single", or "rerun"; where the download time of the Export came from;
  // whether the user changed the proposed label or time; and the label of
  // the Snapshot that the last run imported (stage B4b-1).
  how: "snapshots",
  importSource: null,
  labelEdited: false,
  timeEdited: false,
  lastImported: null,
  runLabel: null,
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
  // The GitHub report (stage B5c): what the open report is about, this
  // computer's values from the server, whether this launch is a later one,
  // the button of the run that stopped, and the stops that the page shows,
  // in the order that the last render drew them.
  report: null,
  reportComputer: null,
  launch: "first",
  runErrorPart: "run.start",
  shownStops: [],
  // Whether the tips under the box headings show: on at a first launch,
  // off at a later one, and as the person last switched them, which the
  // settings remember (stage B4c).
  hintsOn: true,
  // The settings of an earlier launch (stage B4c): the places that they
  // remembered, what to tell of them (a code, and whether it came from
  // writing them), whether the second and third boxes still hold the
  // remembered places on a later launch, and the question that forgets them,
  // which says when they are forgotten.
  remembered: { store: null, outputParent: null },
  // Whether the name of the output is the page's own proposal, which moves on
  // to a free name; the folder that the person chose for the Support Bundle
  // (null for next to the output), and the error of its dialog (stage B5a).
  nameProposed: true,
  bundleFolder: null,
  bundleChooserError: null,
  // The output that the check and the Support Bundle of the fourth box are
  // for (stage B5b): this run's ("run"), one of the list of earlier outputs
  // ("earlier", by its number and its place in that list), or a folder that
  // the person chose ("chosen"); the list, with the output before the last
  // run and what a run is compared with; the error of the dialog; and the
  // check, the bundle, and showing it, of that output.
  earlier: null,
  target: { kind: "run", index: null, path: null },
  targetChooserError: null,
  tools: emptyTools(),
  settingsNotice: null,
  snapshotAuto: false,
  outputAuto: false,
  // Whether there is a file of the settings to forget (stage C1), and the
  // key of what the bar tells after forgetting them.
  settingsPresent: false,
  forget: { asked: false, busy: false, key: null },
  // The information buttons that are open, and the timer that gives the
  // one that opened last to its live region (stage C1).
  infos: new Set(),
  infoTimer: null,
  // The message beside the example question that was copied last.
  copy: null,
  // The step of "How to use" whose box lights up, and its timer.
  spot: null,
  spotTimer: null,
};

class ApiError extends Error {
  constructor(status, code, detail = null) {
    super(`API request failed with HTTP ${status}`);
    this.status = status;
    this.code = code;
    // The version that made an output that this version cannot check
    // (stage B5b).
    this.detail = detail;
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
  // A part that has numbers of its own is a message itself (stage B4b-1).
  for (const [name, key] of Object.entries(message.keyParams ?? {})) {
    params[name] = typeof key === "string" ? t(key) : describe(key);
  }
  return t(message.key, params);
}

function errorLines(code, detail) {
  return errorMessages(code, detail).map(describe);
}

// The line at the end of the explanation of a stop in a red part of a box,
// whose button opens the GitHub report in the help panel with the values of
// that stop (stage B5c): the red boxes, the stops that the check of the
// Export and the Snapshot Store show, and those of the output check and of
// the buttons of the fourth box. A note under a field has none, as the
// mockup v10 has it. The page notes each stop that it shows, for a report
// opened from elsewhere.
function reportLine(code, partKey) {
  state.shownStops.push({ code, partKey });
  const [before, after] = aroundPart("report.line");
  return { text: `${before}${t("report.line_button")}${after}`, className: "report", report: { code, partKey } };
}

// The words before and after the part of a message that is a button or a
// link, which each language puts in its own place as {part} (stage B5c).
function aroundPart(key) {
  const [before, after = ""] = t(key, { part: "\u0000" }).split("\u0000");
  return [before, after];
}

// The lines of a stop, with that line at their end.
function stopLines(code, detail, partKey) {
  const lines = errorLines(code, detail);
  return typeof code === "string" && code !== "" ? [...lines, reportLine(code, partKey)] : lines;
}

// Lines with kinds, with that line after the code of each stop among them.
function reportedKindLines(lines, partKey) {
  return lines.flatMap((line) => {
    const [item] = kindLines([line]);
    const code = line.kind === "error" && line.message?.key === "error.code" ? line.message.params?.code : null;
    return typeof code === "string" && code !== "" ? [item, reportLine(code, partKey)] : [item];
  });
}

// The page renders every second during a run. Rebuilding a live region
// makes screen readers repeat it, so text changes only when it differs. A
// line is its text, or its text with a kind that gives it a mark and a color
// (stage B3b).
function replaceLines(container, lines) {
  const items = lines.map((line) => (typeof line === "string" ? { text: line, className: "" } : line));
  // The line of a report differs by its stop too (stage B5c).
  const reportOf = (item) => (item.report ? `${item.report.code} ${item.report.partKey}` : "");
  const current = Array.from(container.children, (line) => [line.textContent, line.className, line.dataset.report ?? ""]);
  if (
    current.length === items.length &&
    current.every(
      ([text, className, report], index) =>
        text === items[index].text && className === items[index].className && report === reportOf(items[index]),
    )
  ) {
    return;
  }
  container.replaceChildren(
    ...items.map((item) => {
      const line = document.createElement("p");
      line.className = item.className;
      if (item.report) {
        line.dataset.report = reportOf(item);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "link-button report-link";
        button.dataset.code = item.report.code;
        button.dataset.part = item.report.partKey;
        button.textContent = t("report.line_button");
        const [before, after] = aroundPart("report.line");
        line.append(before, button, after);
      } else {
        line.textContent = item.text;
      }
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
    throw new ApiError(
      response.status,
      typeof body?.error === "string" ? body.error : null,
      typeof body?.version === "string" ? { version: body.version } : null,
    );
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

// The labels of the Snapshots of the open store, which a new one may not take.
function storeLabels() {
  const answer = state.store.answer;
  return answer?.state === "store" && Array.isArray(answer.snapshots)
    ? answer.snapshots.map((item) => item?.label).filter((label) => typeof label === "string")
    : [];
}

// The fields of an import as the page holds them (stage B4b-1).
function importFields() {
  return { label: ui.snapshotLabel.value.trim(), time: ui.downloadedAt.value.trim() };
}

// One view of the page's state, for the rules in flow.mjs.
function view() {
  const run = state.run;
  // Normalizing the Snapshots again takes no Export (stage B4b-1).
  const how = state.how;
  const rerun = how === "rerun";
  const answer = state.store.answer;
  const snapshotCount =
    answer?.state === "store" && Array.isArray(answer.snapshots) ? answer.snapshots.length : 0;
  const checked = !rerun && isCheckCurrent();
  const failedBox = run.state === "failed" ? errorBox(run.error_code, ui.inputPath.value, run.error_detail) : null;
  const requestBox = state.runError !== null ? errorBox(state.runError, ui.inputPath.value) : null;
  // The timezone data that the check found missing belongs to the third box,
  // and the first box is not ready without it (stage B3b).
  const parts = checked && state.check.error === undefined ? checkParts(state.check) : null;
  const timezoneProblem = parts !== null && parts.timezone !== null;
  const ready = parts !== null && !parts.stops && !timezoneProblem;
  // An extracted folder needs the confirmation that its extraction was
  // complete; a ZIP file does not. Only the page asks for it (stage B3a).
  const extractNeeded = ready && state.check.kind === "folder";
  const checkedReady = rerun || (ready && (!extractNeeded || ui.extractConfirm.checked));
  // The fields of an import keep the run from starting once the Export is
  // ready (stage B4b-1).
  const importIssue = how === "snapshots" && checkedReady ? importProblem(importFields(), storeLabels()) : null;
  const current = {
    how,
    newStore: how === "snapshots" && answer?.state === "new",
    snapshotCount,
    storeProblem: storeProblem(how, state.store),
    storeReady: storeReady(how, state.store),
    importProblem: importIssue,
    connected: state.connected,
    runState: run.state,
    starting: state.starting,
    checking: state.checking,
    choosing: state.choosing !== null,
    choosingFolder: state.choosing !== null && state.choosingFor !== "input",
    outputBusy: outputBusy(),
    forgetBusy: state.forget.busy,
    settingsPresent: state.settingsPresent,
    checkedReady,
    extractNeeded,
    extractConfirmed: ui.extractConfirm.checked,
    exportReady: rerun || (checkedReady && requestBox !== "export" && importIssue === null),
    // A name or a time of an import that cannot be used is a problem of the
    // first box, as the codes of a registration are (stage B4b-1).
    exportProblem:
      !rerun &&
      ((checked && (state.check.error !== undefined || parts.stops)) || requestBox === "export" || importIssue !== null),
    timezoneProblem,
    snapshotDecided: state.snapshotDecided,
    outputDecided: state.outputDecided && requestBox !== "output",
    // A box that holds the remembered place is set by itself while it has no
    // problem (stage B4c).
    snapshotAuto: storeSetBySettings(state.snapshotAuto, how, state.store),
    outputAuto: outputSetBySettings(state.outputAuto, state.place, ui.outputParent.value.trim()) && requestBox !== "output",
    outputProblem:
      outputMissingRemembered(state.place, ui.outputParent.value.trim(), state.remembered.outputParent) ||
      outputNameProblem(state.place, ui.outputParent.value.trim(), ui.outputName.value.trim()) !== null,
    editedSinceRun: state.editedSinceRun,
    failedBox,
    requestBox,
    result: run.result,
    // The way of the last run, its import, and whether it made the store
    // (stage B4b-1).
    runHow: run.how,
    imported: run.imported ?? null,
    madeStore: typeof run.stage_seconds?.creating_store === "number",
    outputPath: run.output_path,
    inputFilled: ui.inputPath.value.trim() !== "",
    inputPath: ui.inputPath.value,
    outputParent: ui.outputParent.value,
    outputName: ui.outputName.value,
    timezone: ui.timezone.value,
  };
  current.stepNumbers = stepNumbers(current);
  return current;
}

// The Export that the run will import, with its name and time, while the
// first box is ready for it and no finished run shows its own (stage B4b-1).
function pendingImport(current) {
  const importing =
    current.how === "snapshots" &&
    current.checkedReady &&
    current.importProblem === null &&
    !current.storeProblem &&
    (!FINISHED_STATES.includes(state.run.state) || state.editedSinceRun);
  return importing ? { label: ui.snapshotLabel.value.trim(), time: localTimeIso(ui.downloadedAt.value) } : null;
}

// The place of the import in the order of the Snapshots and their number
// after it, for the names of the steps: from the run once it has imported,
// otherwise from the list with the Export that the run will import.
function stepNumbers(current) {
  const imported = state.run.imported;
  if (imported) {
    return { order: imported.order, count: imported.snapshot_count };
  }
  const rows = snapshotRows(state.store.answer, pendingImport(current));
  const pending = rows.find((row) => row.state === "pending");
  return pending === undefined ? {} : { order: pending.order, count: rows.length };
}

function renderCheck(current) {
  // Normalizing the Snapshots again takes no Export (stage B4b-1).
  if (current.how === "rerun") {
    replaceLines(ui.checkResult, []);
    ui.extractArea.hidden = true;
    renderChoices([]);
    return;
  }
  const lines = [];
  // The dialog for the store or the output speaks in its own box (stage B4a).
  const choosingExport = state.choosing !== null && state.choosingFor === "input";
  if (choosingExport) {
    lines.push(t("choose.open"));
  } else if (state.chooserError !== null) {
    lines.push(...stopLines(state.chooserError, undefined, "export.heading"));
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
    lines.push(...stopLines(state.check.error, undefined, "export.heading"));
  } else if (state.check) {
    // Red, then yellow, then what the check found, each with its mark
    // (stage B3b), and the report after each stop (stage B5c).
    lines.push(...reportedKindLines(checkMessages(state.check), "export.heading"));
  }
  // The line of the report comes after the buttons that choose one of the
  // Exports of a mixed input (stage B6a).
  const parts = apartReport(lines);
  replaceLines(ui.checkResult, parts.lines);
  replaceLines(ui.checkReport, parts.report);
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
const ROW_STATE_KEYS = {
  kept: "store.row_kept",
  pending: "store.row_pending",
  added: "store.row_added",
};

function renderStore(current) {
  const store = state.store;
  const answer = store.answer;
  const opened = answer?.state === "store";
  // This Export alone does not use the store (stage B4b-1).
  const single = current.how === "single";
  ui.storeArea.classList.toggle("unused", single);
  ui.howNote.hidden = !single;
  setText(ui.howNote, single ? t("how.single_note") : "");
  setText(ui.storePath, typeof answer?.path === "string" ? answer.path : "");
  // A remembered store that is not found: another one, a look again, or a
  // new one, as for an open store (stage B4c).
  const remembered = { ...store, remembered: state.remembered.store };
  const missing = storeMissingRemembered(remembered);
  ui.storeCreate.hidden = opened || missing;
  ui.storeOpen.hidden = opened || missing;
  ui.storeOpenOther.hidden = !opened && !missing;
  ui.storeSearch.hidden = !missing;
  ui.storeCreateNew.hidden = !opened && !missing;
  ui.storeCheck.hidden = !opened;
  const choosing = state.choosing !== null && String(state.choosingFor).startsWith("store");
  // The line of the report comes after the check and the button that remove
  // the lock file (stage B6a).
  const storeParts = apartReport(reportedKindLines(storeMessages({ ...remembered, choosing }, current.how), "snapshot.heading"));
  replaceLines(ui.storeResult, storeParts.lines);
  replaceLines(ui.storeReport, storeParts.report);
  // The Export that the run will import, in its place (stage B4b-1), and
  // that one of the same content adds no new Snapshot (stage B6a).
  const rows = snapshotRows(answer, pendingImport(current), state.lastImported);
  ui.storeList.hidden = rows.length === 0;
  ui.storeSameNote.hidden = !sameContentNoted(rows);
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
      time.className = "nowrap time-col";
      time.textContent = row.time;
      const files = document.createElement("td");
      files.className = "n";
      files.textContent = row.files === null ? "—" : formatNumber(row.files);
      // The Export that the run imports, and the one that it imported, are
      // marked as the steps are; the others are plain (stage B4b-1).
      const rowState = document.createElement("td");
      const words = t(ROW_STATE_KEYS[row.state] ?? ROW_STATE_KEYS.kept);
      if (row.state === "pending" || row.state === "added") {
        const pill = document.createElement("span");
        pill.className = `pill k-${row.state === "pending" ? "run" : "done"}`;
        pill.textContent = words;
        rowState.append(pill);
      } else {
        rowState.className = "kept";
        rowState.textContent = words;
      }
      tableRow.className = row.state === "pending" ? "r-run" : row.state === "added" ? "r-done" : "";
      tableRow.append(order, label, time, files, rowState);
      return tableRow;
    }),
  );
}

// The lock file that a stopped import left (stage B4b-2): when it was
// written, the person's check that no other command uses the store, and the
// button that removes it.
function renderLock(current) {
  const offered = lockOffered(current.how, state.store, ACTIVE_STATES.includes(state.run.state) || state.starting);
  ui.lockArea.hidden = !offered;
  const age = offered ? lockAge(state.store.answer?.lock_created_at, Date.now()) : null;
  setText(ui.lockTime, age === null ? "" : describe(age));
}

// The fields of an import in the first box: the label and the download time,
// where the time came from, and what keeps the run from starting
// (stage B4b-1).
function renderImport(current) {
  const shown = importFieldsShown(current);
  ui.importArea.hidden = !shown;
  // Where the proposed time came from, until the user changes it.
  const source = state.timeEdited ? null : downloadSourceMessage(state.importSource);
  setText(ui.downloadedAtHelp, source === null ? t("import.time_help") : describe(source));
  const code = shown ? current.importProblem : null;
  const lines = typeof code === "string" ? errorMessages(code) : [];
  replaceLines(ui.importResult, kindLines(lines.map((line, index) => ({ kind: "error", start: index === 0, message: line }))));
}

// Normalizing the Snapshots again, at the foot of the first box, when the
// open store holds some (stage B4b-1).
function renderRerun(current) {
  const rerun = current.how === "rerun";
  ui.rerunArea.hidden = !(rerun || (state.store.answer?.state === "store" && current.snapshotCount > 0));
  setText(ui.rerunText, rerun ? t("rerun.chosen", { count: formatNumber(current.snapshotCount) }) : t("rerun.help"));
  setText(ui.rerunToggle, t(rerun ? "rerun.back" : "rerun.button"));
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
  const parent = ui.outputParent.value.trim();
  lines.push(...kindLines(placeMessages(state.place, parent, state.remembered.outputParent)));
  replaceLines(ui.outputParentNote, lines);
  ui.outputSearch.hidden = !outputMissingRemembered(state.place, parent, state.remembered.outputParent);
  // A name of something that is there already, in red before the run
  // (stage B5a).
  replaceLines(ui.outputNameNote, kindLines(nameMessages(outputNameProblem(state.place, parent, ui.outputName.value.trim()))));
}

// The bar at the bottom (stage B4c): what to tell of the settings, the
// question that forgets them, and its answer.
function renderSettings() {
  const lines = [];
  if (state.forget.key !== null) {
    lines.push(t(state.forget.key));
  } else if (state.settingsNotice !== null) {
    lines.push(...settingsMessages(state.settingsNotice.code, state.settingsNotice.writing).map(describe));
  }
  replaceLines(ui.settingsStatus, lines);
  ui.forgetConfirm.hidden = !state.forget.asked;
  ui.forgetButton.setAttribute("aria-expanded", String(state.forget.asked));
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
    lines = stopLines(run.error_code, run.error_detail, "run.start");
  } else if (state.runError !== null) {
    box = current.requestBox;
    lines = stopLines(state.runError, undefined, state.runErrorPart);
  } else if (current.timezoneProblem && !current.exportProblem) {
    box = "output";
    const finding = checkParts(state.check).timezone;
    lines = [...findingMessages(finding).map(describe), reportLine(finding.code, "output.heading")];
    heading = "error.heading_check";
  }
  for (const [name, error] of Object.entries(ui.errors)) {
    const shown = name === box || (box === "snapshot" && name === "run");
    error.area.hidden = !shown;
    setText(error.heading, t(heading));
    replaceLines(error.lines, shown ? lines : []);
  }
}

function familyRow(row, showChange = false) {
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
  warnings.textContent = row.warnings === null ? "—" : formatNumber(row.warnings);
  // The change since the output before (stage B5b).
  if (showChange) {
    const change = document.createElement("td");
    change.className = "n";
    change.textContent = row.change === null || row.change === undefined ? "—" : signedChange(row.change, formatNumber);
    tableRow.append(name, records, change, status, warnings);
  } else {
    tableRow.append(name, records, status, warnings);
  }
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
  name.textContent = describe({ key: row.key, params: row.params });
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

function renderSteps(current) {
  const run = state.run;
  // The steps of the chosen way; a run that made its store names it.
  const newStore = current.madeStore || current.newStore;
  const rows = stepRows(run, outputCheckState(), state.output?.seconds ?? null, state.how, newStore, current.stepNumbers);
  ui.stepsRows.replaceChildren(...rows.map(stepRow));
  const started = ACTIVE_STATES.includes(run.state) || TERMINAL_STATES.includes(run.state);
  setText(ui.stepsCaption, started ? "" : t("steps.caption"));
  setText(ui.stepsTotalLabel, t(FINISHED_STATES.includes(run.state) ? "steps.total" : "steps.elapsed"));
  setText(ui.stepsTotal, started ? formatElapsed(run.elapsed_seconds) : "—");
}

function renderResults() {
  const run = state.run;
  const change = changeView();
  // Before a run, the counts of the output before (stage B5b).
  const before = run.state === "idle" && !state.starting && state.earlier?.previous ? state.earlier.previous : null;
  const rows = before !== null ? previousRows(before) : change.rows;
  ui.columnChange.hidden = !change.shown;
  ui.familyTotalChange.hidden = !change.shown;
  ui.familyRows.replaceChildren(...rows.map((row) => familyRow(row, change.shown)));
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
  setText(ui.resultsCaption, before !== null ? t("results.previous", { name: before.name }) : t(caption));
  replaceLines(ui.resultsChange, change.table.map(describe));
}

// The change since the output before the run (stage B5b): the rows of the
// run with their change, whether the column shows, and the lines under the
// table and in the fourth box.
function changeView() {
  const run = state.run;
  const rows = resultRows(run);
  const previous = state.earlier?.previous ?? null;
  if (!FINISHED_STATES.includes(run.state) || previous === null) {
    return { rows, shown: false, table: [], run: [] };
  }
  const plan = changePlan(previous, {
    snapshots: run.how === "snapshots" || run.how === "rerun",
    version: state.earlier.current?.version,
    run_all_version: state.earlier.current?.run_all_version,
    timezone: run.timezone,
  });
  const changed = changeRows(rows, previous);
  const lines = changeMessages(plan, previous, changed);
  return { rows: changed, shown: plan.comparable, table: lines.table, run: lines.run };
}

function renderRun(states, current) {
  const run = state.run;
  const summary = runSummary(run, states, current);
  // The hidden words before it name the heading for a screen reader, which
  // may list headings alone (stage C1).
  setText(ui.resultHeadline, describe(summary.headline));
  ui.runExitRow.hidden = summary.exitCode === null;
  setText(ui.runExit, summary.exitCode === null ? "" : t("result.exit_code", { code: summary.exitCode }));
  setText(ui.runSub, summary.sub === null ? "" : describe(summary.sub));
  // Progress changes every second, so it stays out of live regions; the
  // hidden announcer speaks only when the stage changes.
  const running = run.state === "running";
  setText(ui.fitProgressLabel, running ? describe(progressMessage(run.progress)) : "");
  // The bar of the files of an import, or of the FIT files (stage B4b-1).
  const bar = running ? progressBar(run.progress) : null;
  ui.fitProgress.hidden = bar === null;
  if (bar !== null) {
    ui.fitProgress.max = bar.max;
    ui.fitProgress.value = bar.value;
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
  replaceLines(ui.runResult, [...resultDetails(run), ...changeView().run].map(describe));
  ui.nextActions.hidden = !FINISHED_STATES.includes(run.state);
}

function outputBusy() {
  const output = state.output;
  return output !== null && (output.checking || output.opening);
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
    checkLines.push(...stopLines(output.checkError, undefined, "output_check.heading"), ...warnings);
  } else if (finished && output.check !== null) {
    checkLines.push(...outputCheckMessages(output.check, state.run.result).map(describe));
  }
  replaceLines(ui.outputCheck, checkLines);
  const openLines = [];
  if (finished && output.openError !== null) {
    openLines.push(...stopLines(output.openError, undefined, "open.folder"));
  } else if (finished && output.opened) {
    openLines.push(t("open.requested"));
  }
  replaceLines(ui.openResult, openLines);
  // Where the Support Bundle goes, and the file that the button makes, before
  // it is made (stage B5a).
  setText(
    ui.bundlePlace,
    state.bundleFolder === null ? t("bundle.next_to_output") : t("bundle.chosen_folder", { folder: state.bundleFolder }),
  );
  // For the output of the fourth box (stage B5b).
  const tools = state.tools;
  replaceLines(ui.bundlePlan, targetReady() ? bundlePlan(targetPath(), state.bundleFolder).map(describe) : []);
  const bundleLines = [];
  if (state.choosing !== null && state.choosingFor === "bundle") {
    bundleLines.push(t("choose.open"));
  } else if (state.bundleChooserError !== null) {
    bundleLines.push(...stopLines(state.bundleChooserError, undefined, "bundle.button"));
  }
  if (tools.bundling) {
    bundleLines.push(t("bundle.creating"));
  } else if (tools.bundleError !== null) {
    bundleLines.push(...stopLines(tools.bundleError, tools.bundleDetail, "bundle.button"));
  } else if (tools.bundle !== null) {
    bundleLines.push(t("bundle.saved", { count: formatNumber(tools.bundle.member_count) }));
  }
  replaceLines(ui.bundleResult, bundleLines);
  ui.bundleReveal.hidden = tools.bundle === null;
  // What showing it said, under its button.
  replaceLines(ui.bundleRevealResult, tools.bundle !== null ? revealLines(tools.reveal) : []);
  renderTarget(finished);
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

// The GitHub report in the help panel (stage B5c): the values that go in,
// in the order of the form, and the link that opens the form with them. Both
// come from the same rows, so that the link carries what the table shows.
function renderReport(current) {
  if (state.help !== "report") {
    return;
  }
  const english = (key) => translate(state.catalogs, "en", key);
  const facts = {
    ...(state.report ?? {}),
    launch: state.launch,
    how: current.how,
    exportKind: current.how === "rerun" ? null : state.check?.kind,
  };
  const rows = reportRows(facts, state.reportComputer, english);
  const key = JSON.stringify([state.language, rows]);
  if (ui.reportValues.dataset.key !== key) {
    ui.reportValues.dataset.key = key;
    ui.reportValues.replaceChildren(
      ...rows.map((row) => {
        const line = document.createElement("tr");
        const name = document.createElement("th");
        name.scope = "row";
        name.textContent = t(row.key);
        const value = document.createElement("td");
        if (row.value === "") {
          value.className = "empty";
          value.textContent = t(row.person ?? "report.not_given");
        } else {
          value.textContent = row.value;
        }
        line.append(name, value);
        return line;
      }),
    );
  }
  const href = reportUrl(rows);
  if (ui.reportOpen.getAttribute("href") !== href) {
    ui.reportOpen.setAttribute("href", href);
  }
}

// The links to pages outside this app, to the documents at the tag of this
// version (stage B5c). They open in a new tab only when they are pressed.
function renderOutsideLinks() {
  for (const [key, before, after] of ui.aroundLinks) {
    const [first, last] = aroundPart(key);
    setText(before, first);
    setText(after, last);
  }
  for (const link of ui.outsideLinks) {
    const target = state.language === "ja" && link.dataset.linkJa ? link.dataset.linkJa : link.dataset.link;
    const href = outsideUrl(target, state.productVersion);
    if (href === null) {
      link.removeAttribute("href");
    } else if (link.getAttribute("href") !== href) {
      link.setAttribute("href", href);
    }
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
  // The External-safe Pack that the run made, shown where it is saved
  // (stage B5a).
  const made = state.output !== null && FINISHED_STATES.includes(state.run.state) && state.run.safe_pack === true;
  ui.packReveal.hidden = !made;
  // The file that the run made, which the line of the next run's file does
  // not name.
  replaceLines(ui.packMade, made ? packMade(state.run.output_path).map(describe) : []);
  replaceLines(ui.packResult, made ? revealLines(state.output.reveals.safe_pack) : []);
}

// The output of the fourth box (stage B5b): this run's, one of the earlier
// outputs, or one that the person chose, and the check of it.
function renderTarget(finished) {
  ui.targetRun.checked = state.target.kind === "run";
  ui.targetEarlier.checked = state.target.kind !== "run";
  setText(ui.targetRunName, finished ? t("target.run_name", { name: lastName(state.run.output_path) }) : t("target.run_none"));
  const choices = earlierChoices(state.earlier?.outputs);
  replaceOptions(ui.targetList, [
    { value: "", text: t("target.pick") },
    ...choices.map((choice) => ({ value: String(choice.index), text: describe(choice) })),
    { value: "other", text: t(choices.length > 0 ? "target.other" : "target.none_found") },
  ]);
  ui.targetList.value =
    state.target.kind === "earlier" && Number.isInteger(state.target.index)
      ? String(state.target.index)
      : state.target.kind === "chosen"
        ? "other"
        : "";
  ui.targetChosen.hidden = state.target.kind !== "chosen";
  setText(ui.targetChosen, state.target.kind === "chosen" ? t("target.chosen", { path: state.target.path }) : "");
  const tools = state.tools;
  const lines = [];
  if (state.choosing !== null && state.choosingFor === "target") {
    lines.push(t("choose.open"));
  } else if (state.targetChooserError !== null) {
    lines.push(...stopLines(state.targetChooserError, undefined, "target.check"));
  }
  if (tools.checking) {
    lines.push(t("output_check.running"));
  } else if (tools.checkError !== null) {
    lines.push(...stopLines(tools.checkError, tools.checkDetail, "target.check"));
  } else if (tools.check !== null) {
    // The warnings of a run go with the output of that run only.
    lines.push(...outputCheckMessages(tools.check, state.target.kind === "run" ? state.run.result : null).map(describe));
  }
  replaceLines(ui.targetCheckResult, lines);
}

// Options of a list, rebuilt only when they change.
function replaceOptions(select, options) {
  const current = Array.from(select.options, (option) => [option.value, option.textContent]);
  if (current.length === options.length && current.every(([value, text], index) => value === options[index].value && text === options[index].text)) {
    return;
  }
  select.replaceChildren(
    ...options.map((item) => {
      const option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.text;
      option.disabled = item.value === "";
      return option;
    }),
  );
}

function targetReady() {
  const target = state.target;
  if (target.kind === "run") {
    return state.output !== null && FINISHED_STATES.includes(state.run.state);
  }
  if (target.kind === "earlier") {
    return state.earlier !== null && Number.isInteger(target.index);
  }
  return typeof target.path === "string" && target.path !== "";
}

// What the server takes for the output of an action: the page names a place
// only for a folder that the person chose.
function targetPayload() {
  const target = state.target;
  if (target.kind === "earlier") {
    return { output: "earlier", index: target.index, list: state.earlier?.list };
  }
  if (target.kind === "chosen") {
    return { output: "chosen", path: target.path };
  }
  return {};
}

function targetPath() {
  const target = state.target;
  return target.kind === "run" ? state.run.output_path : target.path;
}

function toolsBusy() {
  const tools = state.tools;
  return tools.checking || tools.bundling || tools.reveal?.busy === true;
}

// Another output for the fourth box: what it did for the one before goes.
function setTarget(kind, index = null, path = null) {
  state.target = { kind, index, path };
  state.tools = emptyTools();
  state.targetChooserError = null;
}

// The list of earlier outputs, from the server, with the output before the
// last run (stage B5b). An earlier output that the box holds keeps its place
// in the new list, by its folder.
async function loadEarlier() {
  try {
    state.earlier = await callApi("/api/outputs");
    if (state.target.kind === "earlier") {
      const same = state.earlier.outputs.find((output) => output.path === state.target.path);
      state.target = same ? { kind: "earlier", index: same.index, path: same.path } : { kind: "earlier", index: null, path: null };
    }
    // Before a run of this launch, the box is for an earlier output, as the
    // mockup v10 does.
    const finished = state.output !== null && FINISHED_STATES.includes(state.run.state);
    if (!finished && state.target.kind === "run") {
      const first = state.earlier.outputs[0];
      setTarget("earlier", first ? first.index : null, first ? first.path : null);
    }
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

function chooseEarlier(value) {
  if (value === "other") {
    chooseWithDialog("folder", "target", ui.targetList);
    return;
  }
  const output = state.earlier?.outputs.find((item) => String(item.index) === value);
  if (output) {
    setTarget("earlier", output.index, output.path);
  }
  render();
}

async function checkTarget() {
  if (!targetReady()) {
    return;
  }
  const tools = state.tools;
  tools.checking = true;
  tools.check = null;
  tools.checkError = null;
  tools.checkDetail = null;
  render();
  try {
    tools.check = await callApi("/api/check-output", targetPayload());
  } catch (error) {
    if (!connectionFailure(error)) {
      tools.checkError = error.code;
      tools.checkDetail = error.detail;
      if (error.code === "OUTPUT_LIST_CHANGED") {
        loadEarlier();
      }
    }
  } finally {
    tools.checking = false;
    render();
    returnFocus(ui.targetCheck, ui.targetHeading);
  }
}

// What showing a file where it is saved said (stage B5a).
function revealLines(reveal) {
  if (reveal?.error) {
    return stopLines(reveal.error, undefined, "reveal.button");
  }
  return reveal?.opened ? [t("open.requested")] : [];
}

function renderControls(states, current) {
  const enabled = controls(current, states);
  for (const field of [ui.inputPath, ui.extractConfirm, ui.outputParent, ui.outputName, ui.timezone, ui.safePack]) {
    field.disabled = !enabled.form;
  }
  // Normalizing the Snapshots again takes no Export (stage B4b-1).
  const rerun = state.how === "rerun";
  ui.chooseZip.disabled = !enabled.choose || rerun;
  ui.chooseFolder.disabled = !enabled.choose || rerun;
  ui.inputPath.disabled = !enabled.form || rerun;
  ui.howSnapshots.checked = state.how !== "single";
  ui.howSingle.checked = state.how === "single";
  ui.howSnapshots.disabled = !enabled.form || rerun;
  ui.howSingle.disabled = !enabled.form || rerun;
  ui.snapshotLabel.disabled = !enabled.form;
  ui.downloadedAt.disabled = !enabled.form;
  ui.rerunToggle.disabled = !enabled.choose;
  for (const button of ui.checkChoices.children) {
    button.disabled = !enabled.choose;
  }
  ui.outputBrowse.disabled = !enabled.browse;
  ui.outputSearch.disabled = !enabled.browse;
  // The place of the Support Bundle and showing the files where they are
  // saved (stage B5a).
  ui.bundleChoose.disabled = !enabled.browse;
  ui.packReveal.disabled = !enabled.outputActions;
  // The output of the fourth box and its actions (stage B5b), never while a
  // run is active.
  const toolsFree = state.connected && !(ACTIVE_STATES.includes(state.run.state) || state.starting) && !toolsBusy();
  const runFinished = state.output !== null && FINISHED_STATES.includes(state.run.state);
  ui.targetRun.disabled = !toolsFree || !runFinished;
  ui.targetEarlier.disabled = !toolsFree;
  ui.targetList.disabled = !toolsFree || state.target.kind === "run" || state.choosing !== null;
  ui.targetCheck.disabled = !toolsFree || !targetReady();
  ui.bundleReveal.disabled = !toolsFree;
  // The settings are forgotten only when there is a file of them, never
  // while a run, which remembers its places when it ends, is active (stages
  // B4c and C1).
  ui.forgetButton.disabled = !enabled.forget;
  ui.forgetYes.disabled = !enabled.forget;
  for (const button of [ui.storeCreate, ui.storeOpen, ui.storeOpenOther, ui.storeSearch, ui.storeCreateNew, ui.storeCheck]) {
    button.disabled = !enabled.choose || state.store.busy || state.how === "single";
  }
  // The lock file is removed only after the person's check (stage B4b-2).
  ui.lockConfirm.disabled = !enabled.choose || state.store.busy;
  ui.lockRemove.disabled = !enabled.choose || state.store.busy || !ui.lockConfirm.checked;
  ui.check.disabled = !enabled.check || rerun;
  ui.snapshotDecide.disabled = !enabled.decideSnapshot;
  ui.outputDecide.disabled = !enabled.decideOutput;
  // A box that the settings set needs no confirmation until it changes
  // (stage B4c).
  ui.snapshotDecide.hidden = decideHidden(states.snapshot, state.snapshotAuto);
  ui.outputDecide.hidden = decideHidden(states.output, state.outputAuto);
  ui.start.disabled = !enabled.start;
  // One button only is filled with the accent color: the next step (stage
  // C1). After a run, the main action is to open the output.
  const primary = primaryControl(current, states, enabled);
  ui.snapshotDecide.classList.toggle("primary", primary === "snapshotDecide");
  ui.outputDecide.classList.toggle("primary", primary === "outputDecide");
  ui.start.classList.toggle("primary", primary === "start");
  ui.openFolder.classList.toggle("primary", primary === "openFolder");
  ui.cancel.disabled = !enabled.cancel;
  // Cancelling an import also says that the store is completed by the next
  // one (stage B4b-2).
  const importing = (state.run.how ?? state.how) === "snapshots";
  setText(ui.cancelConfirmText, t(importing ? "run.cancel_confirm_import" : "run.cancel_confirm"));
  ui.quit.disabled = !enabled.quit;
  ui.openFolder.disabled = !enabled.outputActions;
  ui.openStartHere.disabled = !enabled.outputActions;
  // The bundle's name is fixed, so a second one would be refused.
  ui.bundle.disabled = !toolsFree || !targetReady() || state.tools.bundle !== null;
  // The report waits for a run to end, as the mockup v10 has it (stage B5c).
  ui.toolsReport.disabled = ACTIVE_STATES.includes(state.run.state);
}

function render() {
  state.shownStops = [];
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
  renderImport(current);
  renderRerun(current);
  renderStore(current);
  renderLock(current);
  renderPlace();
  renderSettings();
  renderBrowser();
  renderErrors(current);
  renderRun(states, current);
  renderSteps(current);
  renderResults();
  renderOutput();
  renderPackFile();
  renderControls(states, current);
  renderHelp(states, current);
  renderReport(current);
  renderOutsideLinks();
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
      state.settingsPresent = settingsPresentAfterRun(state.settingsPresent, state.run);
      state.cancelAsked = false;
      state.editedSinceRun = false;
      if (FINISHED_STATES.includes(state.run.state) && state.output === null) {
        // The name is taken now; propose another one for the next run.
        ui.outputName.value = nextOutputName(ui.outputName.value.trim(), new Date());
        state.nameProposed = true;
        checkOutput();
        // The output of this run is the one of the fourth box (stage B5b).
        setTarget("run");
      }
      loadEarlier();
      // A run may have made the default place (stage B4a).
      lookPlace();
      // A Snapshot run may have made the store and imported into it; the
      // list shows what it imported (stage B4b-1).
      if (state.run.how === "snapshots" || state.run.how === "rerun") {
        const imported = state.run.imported;
        state.lastImported = imported && imported.same_content === false ? state.runLabel : null;
        // A name that a Snapshot took is not the next one: the page proposes
        // the next name again, as for the output (stage B6a).
        if (imported && imported.same_content === false) {
          state.labelEdited = false;
        }
        const path = state.store.answer?.path;
        if (typeof path === "string") {
          storeAction("open", path, null);
        }
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
    // Showing the External-safe Pack where it is saved (stage B5a); the
    // Support Bundle is that of the fourth box (stage B5b).
    reveals: { safe_pack: null },
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
  if (!targetReady()) {
    return;
  }
  const tools = state.tools;
  tools.bundling = true;
  tools.bundleError = null;
  tools.bundleDetail = null;
  tools.reveal = null;
  render();
  try {
    // Next to the output, or in the folder that the person chose (stage
    // B5a), of the output of the fourth box (stage B5b).
    tools.bundle = await callApi("/api/support-bundle", {
      ...targetPayload(),
      ...(state.bundleFolder === null ? {} : { folder: state.bundleFolder }),
    });
  } catch (error) {
    if (!connectionFailure(error)) {
      tools.bundleError = error.code;
      tools.bundleDetail = error.detail;
      if (error.code === "OUTPUT_LIST_CHANGED") {
        loadEarlier();
      }
    }
  } finally {
    tools.bundling = false;
    render();
    returnFocus(ui.bundle, ui.bundleHeading);
  }
}

// Show the Support Bundle or the External-safe Pack where it is saved; the
// server knows the file, and the page sends no place (stage B5a).
async function revealFile(target, button, fallback) {
  // The bundle is that of the fourth box (stage B5b), the pack that of the
  // run.
  const holder = target === "bundle" ? state.tools : state.output;
  if (holder === null) {
    return;
  }
  const keep = (reveal) => {
    if (target === "bundle") {
      holder.reveal = reveal;
    } else {
      holder.reveals[target] = reveal;
    }
  };
  keep({ busy: true, opened: false, error: null });
  render();
  try {
    await callApi("/api/open-output", { target });
    keep({ busy: false, opened: true, error: null });
  } catch (error) {
    keep({ busy: false, opened: false, error: connectionFailure(error) ? null : error.code });
  }
  render();
  returnFocus(button, fallback);
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
    proposeImport(path, answer);
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

// The proposed fields of an import, from the check of an Export (stage
// B4b-1): the download time from the time of the ZIP file or of the newest
// file of a folder (decision 20261017-16), and the label from its date. A
// field that the user changed stays, until another Export is checked.
let proposedFor = null;
function proposeImport(path, answer) {
  if (proposedFor !== path) {
    proposedFor = path;
    state.labelEdited = false;
    state.timeEdited = false;
  }
  state.importSource = typeof answer.downloaded_from === "string" ? answer.downloaded_from : null;
  if (!state.timeEdited) {
    const time = typeof answer.downloaded_at === "string" ? exportTime(answer.downloaded_at) : "—";
    ui.downloadedAt.value = time === "—" ? "" : time;
  }
  proposeLabel();
}

// The proposed label follows the download time and the labels of the store,
// until the user changes it.
function proposeLabel() {
  if (!state.labelEdited) {
    ui.snapshotLabel.value = defaultSnapshotLabel(ui.downloadedAt.value.trim(), storeLabels());
  }
}

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
  if (purpose === "bundle") {
    return ui.bundleHeading;
  }
  if (purpose === "target") {
    return ui.targetHeading;
  }
  return purpose === "input" ? ui.inputHeading : purpose === "output" ? ui.outputHeading : ui.snapshotHeading;
}

// The error of the last dialog, shown in the box of its purpose.
function setChooserError(purpose, code) {
  if (purpose === "input") {
    state.chooserError = code;
  } else if (purpose === "output") {
    state.placeChooserError = code;
  } else if (purpose === "bundle") {
    state.bundleChooserError = code;
  } else if (purpose === "target") {
    state.targetChooserError = code;
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
  } else if (purpose === "store-open" || purpose === "store-place") {
    // Another store, or the place of a new one, is a change of the second
    // box, which asks for its confirmation again (stage B4c).
    changeBox(purpose);
    storeAction(purpose === "store-open" ? "open" : "place", path, focusTarget);
  } else if (purpose === "bundle") {
    // The folder for the Support Bundle (stage B5a); another one may be made
    // there.
    state.bundleFolder = path;
    const tools = state.tools;
    tools.bundle = null;
    tools.bundleError = null;
    tools.bundleDetail = null;
    tools.reveal = null;
    render();
    returnFocus(focusTarget, ui.bundleHeading);
  } else if (purpose === "target") {
    // An output that the person chose for the fourth box (stage B5b).
    setTarget("chosen", null, path);
    render();
    returnFocus(focusTarget, ui.targetHeading);
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
  store.unlocked = false;
  store.unlockError = null;
  if (action !== "check") {
    store.checked = null;
  }
  render();
  try {
    if (action === "unlock") {
      // The lock file that a stopped import left (stage B4b-2): removed
      // only with the person's check; a stop leaves the store as it is, and
      // the store is opened again.
      const answer = await callApi("/api/store/unlock", { path, confirmed: ui.lockConfirm.checked });
      ui.lockConfirm.checked = false;
      if (answer.unlocked === true) {
        const { unlocked: _done, ...opened } = answer;
        store.answer = opened;
        store.unlocked = true;
      } else {
        store.unlockError = answer.error_code;
        store.answer = await callApi("/api/store/open", { path });
      }
      return;
    }
    const answer = await callApi(`/api/store/${action}`, { path });
    if (action === "check") {
      store.checked = answer;
    } else {
      store.answer = answer;
    }
  } catch (error) {
    if (!connectionFailure(error)) {
      const failed = { state: "error", path, error_code: error.code };
      if (action === "unlock") {
        store.unlockError = error.code;
      } else if (action === "check") {
        store.checked = failed;
      } else {
        store.answer = failed;
      }
    }
  } finally {
    store.busy = false;
    proposeLabel();
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
    // With the name, as the start of a run checks it (stage B5a): the page's
    // own proposal moves on to a free name, while the field still holds it.
    let name = ui.outputName.value.trim();
    let answer = await callApi("/api/place", { path, name });
    for (
      let tries = 0;
      tries < MAX_NAME_TRIES && movesProposedName(answer.name_problem, state.nameProposed) && ui.outputName.value.trim() === name;
      tries += 1
    ) {
      name = nextOutputName(name, new Date());
      ui.outputName.value = name;
      answer = await callApi("/api/place", { path, name });
    }
    state.place = { ...answer, path, name };
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

// Choose the way to normalize; the second box asks for its confirmation
// again, and a stop or a cancellation that the page showed gives way
// (stage B4b-1).
function setHow(how) {
  state.how = how;
  changeBox("how");
  state.runError = null;
  state.editedSinceRun = true;
  if (state.run.state === "failed" || state.run.state === "cancelled") {
    state.run = { state: "idle" };
  }
  render();
}

// A change in a box takes back its confirmation, and the remembered place
// that set it (stage B4c).
function changeBox(purpose) {
  Object.assign(
    state,
    afterChange(changedBox(purpose), {
      snapshotDecided: state.snapshotDecided,
      snapshotAuto: state.snapshotAuto,
      outputDecided: state.outputDecided,
      outputAuto: state.outputAuto,
    }),
  );
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
  // The line of a removed lock file says to press Run normalization
  // (stage B4b-2).
  state.store.unlocked = false;
  state.store.unlockError = null;
  state.quitKey = null;
  state.cancelAsked = false;
  // The previous result would read as the answer to this attempt.
  state.run = { state: "idle" };
  state.output = null;
  if (state.target.kind === "run") {
    state.tools = emptyTools();
  }
  state.announced = null;
  render();
  try {
    const request = {
      input: inputValue(),
      output_parent: ui.outputParent.value.trim(),
      output_name: ui.outputName.value.trim(),
      timezone: ui.timezone.value.trim(),
      external_safe_pack: ui.safePack.checked,
    };
    // A Snapshot run names its way, its store, and for an import its fields
    // (stage B4b-1); normalizing the Snapshots again takes no Export.
    state.runLabel = null;
    if (state.how !== "single") {
      request.how = state.how;
      request.store = state.store.answer?.path;
      request.new_store = state.how === "snapshots" && state.store.answer?.state === "new";
      if (state.how === "snapshots") {
        request.label = ui.snapshotLabel.value.trim();
        request.downloaded_at = localTimeIso(ui.downloadedAt.value);
        state.runLabel = request.label;
      } else {
        delete request.input;
      }
    }
    state.lastImported = null;
    state.run = await callApi("/api/run/start", request);
    startPolling();
  } catch (error) {
    if (!connectionFailure(error)) {
      state.runError = error.code;
      state.runErrorPart = "run.start";
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
      state.runErrorPart = "run.cancel";
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
        state.runErrorPart = "quit.button";
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
  // (stage B4a), the folder for the output, or that of the Support Bundle
  // (stage B5a).
  const start =
    target === "input"
      ? ui.inputPath.value
      : target === "output"
        ? ui.outputParent.value
        : target === "bundle"
          ? state.bundleFolder ?? ui.outputParent.value
          : target === "target"
            ? state.target.path ?? state.defaultFolder ?? ui.outputParent.value
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
  state.report = null;
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
  // The report of its own part is about what the page shows (stage B5c).
  if (section === "report" && state.report === null) {
    state.report = reportFacts(state.shownStops, state.run);
  }
  render();
  ui.helpSections[section].heading.focus();
}

// The GitHub report in the help panel, about a stop or about what the page
// shows (stage B5c). GitHub opens only from its link there.
function openReport(facts, opener) {
  state.report = facts;
  openHelp("report", opener);
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
  const opening = !state.infos.has(name);
  if (opening) {
    state.infos.add(name);
  } else {
    state.infos.delete(name);
  }
  render();
  speakInfo(opening ? name : null);
}

function closeInfo(name) {
  if (state.infos.delete(name)) {
    render();
    speakInfo(null);
    ui.infos[name].button.focus();
  }
}

// An explanation that opens is spoken once by a hidden live region, while
// focus stays on its button (stage C1). Only opening and closing change the
// region, never a render, so that it is not repeated; it is emptied first, so
// that the same explanation is spoken again when it opens again.
function speakInfo(name) {
  window.clearTimeout(state.infoTimer);
  ui.infoAnnouncer.textContent = "";
  if (name === null) {
    return;
  }
  state.infoTimer = window.setTimeout(() => {
    ui.infoAnnouncer.textContent = ui.infos[name].region.innerText.replace(/\s+/g, " ").trim();
  }, INFO_SPEAK_DELAY_MS);
}

// The person switched the tips: the next launch shows them so too
// (stage B4c).
async function changeHints() {
  state.hintsOn = ui.hintsToggle.checked;
  state.forget.key = null;
  render();
  try {
    const answer = await callApi("/api/settings/hints", { on: state.hintsOn });
    state.settingsNotice = answer?.remembered === true ? null : { code: answer?.notice, writing: true };
    // The file of the settings is there to forget now (stage C1).
    if (answer?.remembered === true) {
      state.settingsPresent = true;
    }
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

// Forgetting the remembered settings asks first, above the bar (stage B4c).
function askForget() {
  state.forget.asked = true;
  state.forget.key = null;
  render();
  ui.forgetNo.focus();
}

function keepSettings() {
  state.forget.asked = false;
  render();
  ui.forgetButton.focus();
}

async function forgetSettings() {
  state.forget.busy = true;
  render();
  try {
    const answer = await callApi("/api/settings/forget");
    const outcome = forgetOutcome(answer);
    state.forget.key = outcome.key;
    state.settingsPresent = outcome.present;
    state.settingsNotice = outcome.notice === null ? null : { code: outcome.notice, writing: false };
  } catch (error) {
    if (!connectionFailure(error) && error.code !== "RUN_ACTIVE") {
      state.settingsNotice = { code: "SETTINGS_NOT_REMOVED", writing: false };
    }
  } finally {
    state.forget.busy = false;
    state.forget.asked = false;
    render();
    returnFocus(ui.forgetButton, ui.runHeading);
  }
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
  } else if (![ui.extractConfirm, ui.snapshotLabel, ui.downloadedAt].includes(event?.target)) {
    // The fields of the first box leave the third box as it was decided, or
    // as it was set by the settings (stage B4c).
    changeBox("output");
  }
  if (event?.target === ui.outputParent) {
    state.placeChooserError = null;
    schedulePlace();
  }
  // A name that the person gave is theirs, and is checked as they type it
  // (stage B5a).
  if (event?.target === ui.outputName) {
    state.nameProposed = false;
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
  // Looking again for the remembered store or folder (stage B4c).
  ui.storeSearch.addEventListener("click", () => storeAction("open", state.remembered.store, ui.storeSearch));
  ui.outputSearch.addEventListener("click", lookPlace);
  ui.forgetButton.addEventListener("click", askForget);
  ui.forgetYes.addEventListener("click", forgetSettings);
  ui.forgetNo.addEventListener("click", keepSettings);
  ui.forgetConfirm.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      keepSettings();
    }
  });
  ui.lockConfirm.addEventListener("change", render);
  ui.lockRemove.addEventListener("click", () => storeAction("unlock", state.store.answer?.path, ui.lockRemove));
  ui.check.addEventListener("click", () => runCheck());
  // The way to normalize, and normalizing the Snapshots again (stage B4b-1).
  for (const radio of [ui.howSnapshots, ui.howSingle]) {
    radio.addEventListener("change", () => setHow(radio.value));
  }
  ui.rerunToggle.addEventListener("click", () => setHow(state.how === "rerun" ? "snapshots" : "rerun"));
  ui.snapshotLabel.addEventListener("input", (event) => {
    state.labelEdited = true;
    fieldChanged(event);
  });
  ui.downloadedAt.addEventListener("input", (event) => {
    state.timeEdited = true;
    proposeLabel();
    fieldChanged(event);
  });
  ui.snapshotDecide.addEventListener("click", () => decide("snapshot"));
  ui.outputDecide.addEventListener("click", () => decide("output"));
  ui.start.addEventListener("click", startRun);
  ui.cancel.addEventListener("click", askCancel);
  ui.cancelYes.addEventListener("click", cancelRun);
  ui.cancelNo.addEventListener("click", keepRunning);
  ui.openFolder.addEventListener("click", () => openOutput("folder"));
  ui.openStartHere.addEventListener("click", () => openOutput("start_here"));
  ui.bundle.addEventListener("click", makeBundle);
  ui.bundleChoose.addEventListener("click", () => chooseWithDialog("folder", "bundle", ui.bundleChoose));
  // The output of the fourth box (stage B5b).
  ui.targetRun.addEventListener("change", () => {
    setTarget("run");
    render();
  });
  ui.targetEarlier.addEventListener("change", () => {
    const first = state.earlier?.outputs[0];
    setTarget("earlier", first ? first.index : null, first ? first.path : null);
    render();
  });
  ui.targetList.addEventListener("change", () => chooseEarlier(ui.targetList.value));
  ui.targetCheck.addEventListener("click", checkTarget);
  ui.bundleReveal.addEventListener("click", () => revealFile("bundle", ui.bundleReveal, ui.bundleHeading));
  ui.packReveal.addEventListener("click", () => revealFile("safe_pack", ui.packReveal, ui.outputHeading));
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
  // The GitHub report: from the fourth box, about what the page shows, and
  // from the line under a stop, about that stop (stage B5c).
  ui.toolsReport.addEventListener("click", () => openReport(reportFacts(state.shownStops, state.run), ui.toolsReport));
  document.addEventListener("click", (event) => {
    const button = event.target instanceof Element ? event.target.closest("button.report-link") : null;
    if (button !== null) {
      openReport({ code: button.dataset.code, partKey: button.dataset.part, exitCode: 2 }, button);
    }
  });
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
  connect();
  render();
  try {
    const status = await callApi("/api/status");
    state.productVersion =
      typeof status.product_version === "string" ? status.product_version : null;
    // This computer's values of the GitHub report (stage B5c).
    state.reportComputer = status.report !== null && typeof status.report === "object" ? status.report : null;
    // The product's default, as the CLI takes it (stage A5a).
    if (typeof status.default_timezone === "string" && ui.timezone.value === "") {
      ui.timezone.value = status.default_timezone;
    }
    // The settings of an earlier launch (stage B4c): the places that it
    // remembered, which set the second and third boxes by themselves, and
    // the tips.
    const settings = launchSettings(status);
    state.launch = settings.launch;
    state.remembered = { store: settings.store, outputParent: settings.outputParent };
    state.settingsPresent = settings.present;
    state.settingsNotice = settings.notice === null ? null : { code: settings.notice, writing: false };
    state.hintsOn = hintsShown(settings);
    Object.assign(state, boxesSetBySettings(settings));
    if (settings.outputParent !== null && ui.outputParent.value === "") {
      ui.outputParent.value = settings.outputParent;
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
    // The outputs of earlier runs, and the one before (stage B5b).
    loadEarlier();
    // The remembered store (stage B4c), or the store at the default place,
    // if there is one, and the folder for the output (stage B4a).
    if (state.remembered.store !== null) {
      storeAction("open", state.remembered.store, null);
    } else if (state.defaultFolder !== null) {
      storeAction("place", state.defaultFolder, null);
    }
    lookPlace();
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

start();

// What the fourth box did for its output: the check, the Support Bundle, and
// showing it where it is saved (stage B5b).
function emptyTools() {
  return {
    checking: false,
    check: null,
    checkError: null,
    checkDetail: null,
    bundling: false,
    bundle: null,
    bundleError: null,
    bundleDetail: null,
    reveal: null,
  };
}
