// Page logic for the GUI: it connects the run page to the server API. Visible
// text comes from the message catalogs. Message keys appear only as literal
// strings, here and in flow.mjs, so that tests can check them against the
// catalogs.

import { DEFAULT_LANGUAGE, chooseLanguage, translate } from "./i18n.mjs";
import {
  ACTIVE_STATES,
  FINISHED_STATES,
  TERMINAL_STATES,
  controls,
  defaultOutputName,
  errorMessage,
  familyRows,
  findingMessages,
  formatElapsed,
  outputCheckMessages,
  progressMessage,
  resultMessages,
  stalledSeconds,
} from "./flow.mjs";

const LANGUAGES = ["en", "ja"];
const LAUNCH_KEY_HEADER = "X-Launch-Key";
const LAUNCH_KEY_STORAGE = "launchKey";
const LANGUAGE_STORAGE = "language";
const HEARTBEAT_INTERVAL_MS = 30000;
const POLL_INTERVAL_MS = 1000;
const DEFAULT_TIMEZONE = "Asia/Tokyo";

const byId = (id) => document.getElementById(id);
const ui = {
  version: byId("product-version"),
  connection: byId("connection-status"),
  language: byId("language-select"),
  quit: byId("quit-button"),
  inputPath: byId("input-path"),
  inputBrowse: byId("input-browse"),
  check: byId("check-button"),
  checkResult: byId("check-result"),
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
  start: byId("start-button"),
  cancel: byId("cancel-button"),
  runStatus: byId("run-status"),
  runElapsed: byId("run-elapsed"),
  resultHeading: byId("result-heading"),
  runResult: byId("run-result"),
  familyTable: byId("family-table"),
  familyRows: byId("family-rows"),
  outputActions: byId("output-actions"),
  outputCheck: byId("output-check"),
  openFolder: byId("open-folder-button"),
  openStartHere: byId("open-start-here-button"),
  openResult: byId("open-result"),
  bundle: byId("bundle-button"),
  bundleResult: byId("bundle-result"),
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
  starting: false,
  run: { state: "idle" },
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

function codeLines(code) {
  const lines = [describe(errorMessage(code))];
  if (typeof code === "string" && code !== "") {
    lines.push(t("error.code", { code }));
  }
  return lines;
}

function replaceLines(container, lines) {
  container.replaceChildren(
    ...lines.map((text) => {
      const line = document.createElement("p");
      line.textContent = text;
      return line;
    }),
  );
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

function isCheckCurrent() {
  return (
    state.check !== null &&
    state.check.path === ui.inputPath.value.trim() &&
    state.check.timezone === ui.timezone.value.trim()
  );
}

function renderCheck() {
  const lines = [];
  if (state.checking) {
    lines.push(t("check.running"));
  } else if (state.check?.error !== undefined) {
    lines.push(...codeLines(state.check.error));
  } else if (state.check) {
    lines.push(t(state.check.ready ? "check.ready" : "check.not_ready"));
    for (const finding of state.check.findings) {
      const { message, action } = findingMessages(finding);
      lines.push(action ? `${t(message)} ${t(action)}` : t(message));
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
    message = codeLines(browser.error).join(" ");
  } else if (browser.folders.length === 0) {
    message = t("browser.empty");
  } else if (browser.truncated) {
    message = t("browser.truncated", { count: formatNumber(browser.folders.length) });
  }
  ui.browserMessage.textContent = message;
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

function familyRow(row) {
  const tableRow = document.createElement("tr");
  const values = [
    row.nameKey ? t(row.nameKey) : row.family,
    t(row.statusKey),
    formatNumber(row.records),
    formatNumber(row.warnings),
  ];
  values.forEach((value, index) => {
    const cell = document.createElement(index === 0 ? "th" : "td");
    if (index === 0) {
      cell.scope = "row";
    }
    cell.textContent = value;
    tableRow.append(cell);
  });
  return tableRow;
}

function renderRun() {
  const run = state.run;
  const lines = [];
  if (state.runError !== null) {
    lines.push(...codeLines(state.runError));
  }
  if (state.quitKey !== null) {
    lines.push(t(state.quitKey));
  }
  if (run.state === "running") {
    lines.push(describe(progressMessage(run.progress)));
    const stalled = stalledSeconds(run);
    if (stalled !== null) {
      lines.push(t("run.stalled", { seconds: formatNumber(stalled) }));
    }
  } else if (run.state === "cancelling") {
    lines.push(t("run.cancelling"));
  }
  replaceLines(ui.runStatus, lines);
  const shown = ACTIVE_STATES.includes(run.state) || TERMINAL_STATES.includes(run.state);
  ui.runElapsed.textContent = shown
    ? t("run.elapsed", { time: formatElapsed(run.elapsed_seconds) })
    : "";
  const terminal = TERMINAL_STATES.includes(run.state);
  ui.resultHeading.hidden = !terminal;
  replaceLines(ui.runResult, terminal ? resultMessages(run).map(describe) : []);
  const rows = run.state === "finished" ? familyRows(run.result) : [];
  ui.familyTable.hidden = rows.length === 0;
  ui.familyRows.replaceChildren(...rows.map(familyRow));
}

function outputBusy() {
  const output = state.output;
  return output !== null && (output.checking || output.opening || output.bundling);
}

function renderOutput() {
  const output = state.output;
  ui.outputActions.hidden = output === null || !FINISHED_STATES.includes(state.run.state);
  if (ui.outputActions.hidden) {
    return;
  }
  const checkLines = [];
  if (output.checking) {
    checkLines.push(t("output_check.running"));
  } else if (output.checkError !== null) {
    checkLines.push(...codeLines(output.checkError));
  } else if (output.check !== null) {
    checkLines.push(...outputCheckMessages(output.check).map(describe));
  }
  replaceLines(ui.outputCheck, checkLines);
  const openLines = [];
  if (output.openError !== null) {
    openLines.push(...codeLines(output.openError));
  } else if (output.opened) {
    openLines.push(t("open.requested"));
  }
  replaceLines(ui.openResult, openLines);
  const bundleLines = [];
  if (output.bundling) {
    bundleLines.push(t("bundle.creating"));
  } else if (output.bundleError !== null) {
    bundleLines.push(...codeLines(output.bundleError));
  } else if (output.bundle !== null) {
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
}

function renderControls() {
  const enabled = controls({
    connected: state.connected,
    runState: state.run.state,
    starting: state.starting,
    checking: state.checking,
    outputBusy: outputBusy(),
    checkedReady: isCheckCurrent() && state.check.ready === true,
    inputPath: ui.inputPath.value,
    outputParent: ui.outputParent.value,
    outputName: ui.outputName.value,
    timezone: ui.timezone.value,
  });
  for (const field of [ui.inputPath, ui.outputParent, ui.outputName, ui.timezone, ui.safePack]) {
    field.disabled = !enabled.form;
  }
  ui.inputBrowse.disabled = !enabled.browse;
  ui.outputBrowse.disabled = !enabled.browse;
  ui.check.disabled = !enabled.check;
  ui.start.disabled = !enabled.start;
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
  ui.connection.textContent = state.connectionKey === null ? "" : t(state.connectionKey);
  for (const option of ui.language.options) {
    option.textContent = translate(state.catalogs, option.value, "language.name");
  }
  ui.language.value = state.language;
  renderCheck();
  renderBrowser();
  renderRun();
  renderOutput();
  renderControls();
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

async function pollRun() {
  try {
    state.run = await callApi("/api/run/status");
    if (TERMINAL_STATES.includes(state.run.state)) {
      stopPolling();
      if (FINISHED_STATES.includes(state.run.state) && state.output === null) {
        // The name is taken now; propose a new one for the next run.
        ui.outputName.value = defaultOutputName(new Date());
        checkOutput();
      }
    }
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(pollRun, POLL_INTERVAL_MS);
}

// Check the finished output as the CLI's validate-handoff and doctor
// --run-output would; the server knows which folder the run published.
async function checkOutput() {
  const output = {
    checking: true,
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
  const timezone = ui.timezone.value.trim();
  state.checking = true;
  state.check = null;
  render();
  try {
    const answer = await callApi("/api/check-input", { input: path, timezone });
    state.check = {
      path,
      timezone,
      ready: answer.ready === true,
      findings: Array.isArray(answer.findings) ? answer.findings : [],
    };
    if (state.check.ready) {
      await suggestOutputParent(path);
    }
  } catch (error) {
    if (!connectionFailure(error)) {
      state.check = { path, timezone, error: error.code };
    }
  } finally {
    state.checking = false;
    render();
  }
}

async function startRun() {
  state.starting = true;
  state.runError = null;
  state.quitKey = null;
  // The previous result would read as the answer to this attempt.
  state.run = { state: "idle" };
  state.output = null;
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
  }
}

async function cancelRun() {
  if (!window.confirm(t("run.cancel_confirm"))) {
    return;
  }
  try {
    state.run = await callApi("/api/run/cancel");
  } catch (error) {
    if (!connectionFailure(error)) {
      state.runError = error.code;
    }
  }
  render();
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

function fieldChanged() {
  if (state.check !== null && !isCheckCurrent()) {
    state.check = null;
    renderCheck();
  }
  renderControls();
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
  ui.timezone.value = DEFAULT_TIMEZONE;
  ui.outputName.value = defaultOutputName(new Date());
  ui.language.addEventListener("change", () => changeLanguage(ui.language.value));
  ui.quit.addEventListener("click", quit);
  ui.check.addEventListener("click", runCheck);
  ui.start.addEventListener("click", startRun);
  ui.cancel.addEventListener("click", cancelRun);
  ui.openFolder.addEventListener("click", () => openOutput("folder"));
  ui.openStartHere.addEventListener("click", () => openOutput("start_here"));
  ui.bundle.addEventListener("click", makeBundle);
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
  for (const field of [ui.inputPath, ui.outputParent, ui.outputName, ui.timezone]) {
    field.addEventListener("input", fieldChanged);
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
    state.connected = true;
    state.connectionKey = "status.connected";
    startHeartbeat();
    state.run = await callApi("/api/run/status");
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
