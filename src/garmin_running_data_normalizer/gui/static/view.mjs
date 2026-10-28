// Page logic of the view page (stage G3b): it opens an output on the server,
// asks for the numbers of its panels, and draws them. The rules are in
// view_flow.mjs and the shapes of the charts in view_chart.mjs, which the node
// tests check; this module puts them in the page. Visible text comes from the
// message catalogs, and the page changes text with textContent only, never
// with HTML, so that a name from the computer is never read as markup. The
// page reads outputs only, and never changes them.

import { chooseLanguage, translate } from "./i18n.mjs";
import { ApiError, addressValue, callWithKey, readLaunchKey, readStorage, writeStorage } from "./launch.mjs";
import {
  FINISHED_STATES,
  QUIT_CHANNEL,
  answerFlush,
  connectionMessages,
  lastName,
  normalizePageAddress,
  quitAfterWriting,
  sendLatest,
  settingsMessages,
  stoppedMessage,
  themeAttribute,
  themeMessage,
  themeNowKey,
} from "./flow.mjs";
import {
  FIRST_KEYS,
  GROUPS,
  MAX_PANELS,
  clockOf,
  coverageRuns,
  defaultTypes,
  draggedRange,
  autoGrainOf,
  brushedRange,
  dateText,
  grainKey,
  grainToOpen,
  groupKey,
  itemKey,
  itemListMessage,
  itemsByKey,
  itemsRemembered,
  itemsToOpen,
  kindKey,
  laterSender,
  dropPlace,
  layoutCards,
  layoutNotes,
  lineNames,
  lineStyles,
  monthIndex,
  movedItems,
  overviewGrip,
  panelNotes,
  periodMessage,
  periodRequest,
  periodToOpen,
  rangeProblem,
  readout,
  rememberedItems,
  rememberedKeys,
  settingsAfterForget,
  shelfGroups,
  shelfOpen,
  shiftedRange,
  shown,
  startChoice,
  stopBox,
  summaryMessages,
  tableHeads,
  tableRows,
  tickText,
  timeTickText,
  toggledItems,
  toggledTypes,
  totalItem,
  typeMessage,
  typesRequest,
  typesSummary,
  typesToOpen,
  unitKey,
  viewBar,
  viewHintsShown,
} from "./view_flow.mjs";
import {
  PLOT_LEFT,
  PLOT_RIGHT,
  extent,
  isoDate,
  nearestPeriod,
  overviewShapes,
  panelShapes,
  periodDays,
  periodMiddle,
  sharedExtents,
  timeScale,
  timeTicks,
} from "./view_chart.mjs";

const LANGUAGES = ["en", "ja"];
const LANGUAGE_STORAGE = "language";
// The colors of the page, as on the normalization page (stage G3a).
const THEME_STORAGE = "theme";
const THEME_CHANNEL = "theme";
const HEARTBEAT_INTERVAL_MS = 30000;
// How often the page asks for the answer of the system's dialog (stage B3a).
const CHOOSE_POLL_MS = 500;
// The names of the two tabs of a launch (stage G3b): the normalization page
// and this page find each other by them.
const NORMALIZE_TAB = "garmin-running-normalize";
const VIEW_TAB = "garmin-running-view";
// The rows of a table that are added at a time, as the person scrolls to
// them, so that a table of fifteen years by day opens at once.
const TABLE_ROWS = 400;
const SVG = "http://www.w3.org/2000/svg";
// The parts of the help that a note of a panel opens.
const HELP_LINK_KEYS = {
  zero: "view.help.link_zero",
  calculated: "view.help.link_calculated",
  records: "view.help.link_records",
};
// The keys that move the cross line, by how many periods.
const CROSS_KEYS = { ArrowLeft: -1, ArrowRight: 1, PageUp: -12, PageDown: 12 };
// The view is remembered once the person stops changing it for this long
// (stage K2 of v2.2.0).
const REMEMBER_WAIT_MS = 800;
// What the page says of a change of the layouts that the server could not
// make, by its code; any other code says that it could not be made.
const LAYOUT_PROBLEM_KEYS = {
  LAYOUT_NAME_INVALID: "view.layouts.error.name_invalid",
  LAYOUT_NAME_TAKEN: "view.layouts.error.name_taken",
  LAYOUTS_FULL: "view.layouts.error.full",
  LAYOUT_NOT_FOUND: "view.layouts.error.not_found",
};

const byId = (id) => document.getElementById(id);
const ui = {
  connectionProblem: byId("connection-problem"),
  app: document.querySelector(".view-app"),
  toNormalize: byId("to-normalize"),
  hintsToggle: byId("hints-toggle"),
  helpButton: byId("help-button"),
  nextLine: byId("next-line"),
  nextLabel: byId("next-label"),
  nextText: byId("next-text"),
  outputFilter: byId("output-filter"),
  outputBadge: byId("output-badge"),
  outputSelect: byId("output-select"),
  openLatest: byId("open-latest"),
  chooseOutput: byId("choose-output"),
  periodButtons: [...document.querySelectorAll("[data-period]")],
  periodBack: byId("period-back"),
  periodNext: byId("period-next"),
  rangeRow: byId("range-row"),
  rangeFrom: byId("range-from"),
  rangeTo: byId("range-to"),
  rangeProblem: byId("range-problem"),
  grainButtons: [...document.querySelectorAll("[data-grain]")],
  grainAutoNow: byId("grain-auto-now"),
  typesButton: byId("types-button"),
  typesSummary: byId("types-summary"),
  typesPop: byId("types-pop"),
  typesList: byId("types-list"),
  typesClose: byId("types-close"),
  filtersHint: byId("filters-hint"),
  body: byId("view-body"),
  shelf: byId("shelf"),
  shelfCount: byId("shelf-count"),
  coverageButton: byId("coverage-button"),
  coverageText: byId("coverage-text"),
  shelfFold: byId("shelf-fold"),
  shelfSearch: byId("shelf-search"),
  shelfHint: byId("shelf-hint"),
  shelfGroups: byId("shelf-groups"),
  rail: byId("shelf-rail"),
  shelfOpen: byId("shelf-open"),
  railCount: byId("rail-count"),
  layoutCards: byId("layout-cards"),
  layoutsManage: byId("layouts-manage"),
  layoutSaveAs: byId("layout-save-as"),
  layoutOverwrite: byId("layout-overwrite"),
  layoutSave: byId("layout-save"),
  layoutName: byId("layout-name"),
  layoutSaveButton: byId("layout-save-button"),
  layoutSaveCancel: byId("layout-save-cancel"),
  layoutProblem: byId("layout-problem"),
  layoutsPop: byId("layouts-pop"),
  layoutsPopBody: byId("layouts-pop-body"),
  layoutsPopClose: byId("layouts-pop-close"),
  railLayouts: byId("rail-layouts"),
  railLayoutsPop: byId("rail-layouts-pop"),
  railLayoutsClose: byId("rail-layouts-close"),
  railLayoutCards: byId("rail-layout-cards"),
  partNote: byId("part-note"),
  partText: byId("part-text"),
  emptyBox: byId("empty-box"),
  emptyHeading: byId("empty-heading"),
  emptyText: byId("empty-text"),
  emptyButtons: byId("empty-buttons"),
  emptyPrimary: byId("empty-primary"),
  emptyOther: byId("empty-other"),
  stopBox: byId("stop-box"),
  stopHeading: byId("stop-heading"),
  stopLines: byId("stop-lines"),
  stopNormalize: byId("stop-normalize"),
  stopOther: byId("stop-other"),
  stopCode: byId("stop-code"),
  caveat: byId("caveat"),
  fullEnter: byId("full-enter"),
  fullBar: byId("full-bar"),
  fullText: byId("full-text"),
  fullBack: byId("full-back"),
  addWrap: byId("add-wrap"),
  addItems: byId("add-items"),
  picker: byId("picker"),
  pickerHeading: byId("picker-heading"),
  pickerClose: byId("picker-close"),
  pickerFull: byId("picker-full"),
  pickerGroups: byId("picker-groups"),
  loading: byId("loading"),
  align: byId("align-scales"),
  seriesStop: byId("series-stop"),
  seriesStopHeading: byId("series-stop-heading"),
  seriesStopLines: byId("series-stop-lines"),
  seriesStopCode: byId("series-stop-code"),
  stack: byId("stack"),
  panels: byId("panels"),
  timeAxis: byId("time-axis"),
  announcer: byId("cross-announcer"),
  overview: byId("overview"),
  overviewLabel: byId("overview-label"),
  overviewPlot: byId("overview-plot"),
  quitConfirm: byId("quit-confirm"),
  quitYes: byId("quit-yes"),
  quitNo: byId("quit-no"),
  language: byId("language-select"),
  themeChoices: [byId("theme-auto"), byId("theme-light"), byId("theme-dark")],
  themeNow: byId("theme-now"),
  settingsStatus: byId("settings-status"),
  version: byId("product-version"),
  quit: byId("quit-button"),
  connection: byId("connection-status"),
  helpPanel: byId("help-panel"),
  helpHeading: byId("help-heading"),
  helpClose: byId("help-close"),
  helpParts: {
    zero: byId("help-zero-heading"),
    calculated: byId("help-calculated-heading"),
    records: byId("help-records-heading"),
  },
};

const state = {
  launchKey: null,
  catalogs: {},
  language: "en",
  connected: false,
  connectionKey: null,
  heartbeatTimer: null,
  productVersion: null,
  // The settings as the server read them when the page started.
  settings: null,
  // The other tab forgot the settings: the items and the shelf are written
  // again only when the person changes them.
  forgotten: false,
  hints: false,
  theme: "auto",
  settingsNotice: null,
  quitAsked: false,
  quitKey: null,
  quitting: false,
  stopped: false,
  helpOpen: false,
  // The outputs that the page offers: this launch's run, the list of earlier
  // outputs, and one that the person chose with the system's dialog.
  runOutput: null,
  earlier: null,
  chosen: null,
  choosing: false,
  // The output that is open: how it was chosen, its answer, and a stop.
  target: null,
  opening: null,
  openingTarget: null,
  openSeq: 0,
  view: null,
  stop: null,
  // What the panels ask for.
  items: [],
  shelf: "open",
  period: "all",
  range: null,
  grain: "auto",
  counted: [],
  align: false,
  // The numbers of the panels and of the overview.
  answer: null,
  answerSeq: 0,
  seriesSeq: 0,
  loading: false,
  seriesStop: null,
  coverage: null,
  coverageSeq: 0,
  overview: null,
  overviewSeq: 0,
  // What is open on the page.
  typesOpen: false,
  pickerOpen: false,
  coverageOpen: false,
  folded: {},
  query: "",
  big: null,
  tables: new Set(),
  notesOpen: null,
  cursor: null,
  // Graphs only, which the person chooses for a while; not remembered.
  full: false,
  // The layouts (stage K2 of v2.2.0): the built-in ones of the output that is
  // open, the person's, the built-in ones hidden, and the one used last.
  layouts: { builtIns: [], mine: [], hidden: [], current: null },
  // The field of the name of a new layout, a change of the layouts that could
  // not be made, the window of managing them (with a removal asked or a name
  // being changed), and the window of the cards on the folded shelf.
  layoutSaving: false,
  layoutProblem: null,
  layoutsOpen: false,
  layoutAsk: null,
  layoutRenaming: null,
  railLayoutsOpen: false,
  // The activity types that the person chose (null: those counted at first),
  // which an output that opens counts where it has them (stage K2).
  wantedTypes: null,
};

// The numbers of the panels; the count of the answers tells the drawing that
// they changed.
function setAnswer(answer) {
  state.answer = answer;
  state.answerSeq += 1;
}

// The panels as they are drawn: for each, its item, its chart, and its
// readings, which the cross line moves.
let drawn = [];
let drawnSignature = null;
// The scales that panels of the same unit share.
let drawnShared = new Map();
let redrawFrame = null;

// The watcher of the sizes of the plots of the charts.
let plotWatcher = null;

const themeChannel = typeof BroadcastChannel === "function" ? new BroadcastChannel(THEME_CHANNEL) : null;
const quitChannel = typeof BroadcastChannel === "function" ? new BroadcastChannel(QUIT_CHANNEL) : null;
const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");

function t(key, params) {
  return translate(state.catalogs, state.language, key, params);
}

function formatNumber(value) {
  return typeof value === "number" ? new Intl.NumberFormat(state.language).format(value) : value;
}

// The words of a message of view_flow.mjs or flow.mjs: a text of the output
// as it is, or a key with its parameters, some of them messages themselves.
function describe(message) {
  if (message === null || message === undefined) {
    return "";
  }
  if (typeof message.text === "string") {
    return message.text;
  }
  return t(message.key, describedParams(message));
}

function describedParams(message) {
  const params = {};
  for (const [name, value] of Object.entries(message.params ?? {})) {
    params[name] = formatNumber(value);
  }
  for (const [name, key] of Object.entries(message.keyParams ?? {})) {
    params[name] = typeof key === "string" ? t(key) : describe(key);
  }
  return params;
}

// The nodes of a message whose strong parameters are in bold: each language
// puts them in its own place.
function richNodes(message) {
  if (!Array.isArray(message?.strong) || !message.strong.length || typeof message.key !== "string") {
    return [describe(message)];
  }
  const params = describedParams(message);
  const strong = {};
  for (const name of message.strong) {
    strong[name] = params[name];
    params[name] = `\u0001${name}\u0002`;
  }
  const nodes = [];
  t(message.key, params)
    .split(/\u0001(\w+)\u0002/)
    .forEach((part, index) => {
      if (index % 2 === 0) {
        if (part) {
          nodes.push(part);
        }
      } else {
        const bold = document.createElement("strong");
        bold.textContent = strong[part] ?? "";
        nodes.push(bold);
      }
    });
  return nodes;
}

function setText(element, text) {
  if (element.textContent !== text) {
    element.textContent = text;
  }
}

function element(tag, className = "", text = null) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== null) {
    node.textContent = text;
  }
  return node;
}

function svgElement(tag, attributes = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (value !== null && value !== undefined) {
      node.setAttribute(name, String(value));
    }
  }
  return node;
}

// The small icons of the page, as in the mockup v2.
const ICONS = {
  up: "M8 12.5V3.5M4 7.5l4-4 4 4",
  down: "M8 3.5v9M4 8.5l4 4 4-4",
  close: "M4 4l8 8M12 4l-8 8",
  expand: "M9.5 2.5h4v4M6.5 13.5h-4v-4M13.5 2.5l-4.5 4.5M2.5 13.5L7 9",
  fold: "M4 6l4 4 4-4",
};

function icon(name) {
  const svg = svgElement("svg", { viewBox: "0 0 16 16", width: 14, height: 14, "aria-hidden": "true", focusable: "false" });
  svg.append(svgElement("path", { d: ICONS[name], fill: "none", stroke: "currentColor", "stroke-width": 1.6, "stroke-linecap": "round", "stroke-linejoin": "round" }));
  return svg;
}

function iconButton(name, label, action, key, disabled = false) {
  const button = element("button", "icon-button");
  button.type = "button";
  button.setAttribute("aria-label", label);
  button.dataset.action = action;
  button.dataset.key = key;
  button.disabled = disabled;
  button.append(icon(name));
  return button;
}

function textButton(text, action, key, className = "small") {
  const button = element("button", className, text);
  button.type = "button";
  button.dataset.action = action;
  button.dataset.key = key;
  return button;
}

async function loadCatalog(language) {
  try {
    const response = await fetch(`/i18n/${language}.json`, { cache: "no-store", credentials: "omit" });
    return response.ok ? await response.json() : {};
  } catch {
    return {};
  }
}

async function callApi(path, payload = {}) {
  return callWithKey(state.launchKey, path, payload);
}

function stopHeartbeat() {
  if (state.heartbeatTimer !== null) {
    window.clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = null;
  }
}

function startHeartbeat() {
  stopHeartbeat();
  state.heartbeatTimer = window.setInterval(() => {
    callApi("/api/heartbeat").catch((error) => {
      connectionFailure(error);
      render();
    });
  }, HEARTBEAT_INTERVAL_MS);
}

// Return true when the page lost the server; other errors carry a code.
function connectionFailure(error) {
  const unauthorized = error instanceof ApiError && error.status === 403;
  if (error instanceof ApiError && !unauthorized) {
    return false;
  }
  if (!state.stopped) {
    state.connected = false;
    stopHeartbeat();
    state.connectionKey = unauthorized ? "status.unauthorized" : "status.unavailable";
  }
  return true;
}

// The app stopped, from this page or from the other tab (stage G3b).
function markStopped() {
  // What waits to be remembered is not written: the server stopped.
  viewLater.take();
  state.stopped = true;
  state.connected = false;
  state.quitAsked = false;
  stopHeartbeat();
  state.connectionKey = "status.stopped";
}

// The other tab quit the app: this page says that it stopped.
function quitHeard(event) {
  // The normalization page quits the app: what waits to be remembered is
  // written first, and the page says when it is (stage K2 of v2.2.0).
  if (answerFlush(event.data, rememberNow, quitChannel)) {
    return;
  }
  if (stoppedMessage(event.data)) {
    markStopped();
    render();
  }
}

// --- The colors, the tips, and the settings -------------------------------

function initialTheme() {
  const attribute = document.documentElement.dataset.theme;
  return attribute === "light" || attribute === "dark" ? attribute : "auto";
}

function applyTheme(choice) {
  state.theme = choice;
  const attribute = themeAttribute(choice);
  if (attribute === null) {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = attribute;
  }
  writeStorage(THEME_STORAGE, choice);
}

function noticeOf(answer) {
  return answer?.remembered === true ? null : { code: answer?.notice, writing: true };
}

const rememberTheme = sendLatest(async (choice) => {
  try {
    state.settingsNotice = noticeOf(await callApi("/api/settings/theme", { theme: choice }));
  } catch (error) {
    connectionFailure(error);
  }
  render();
});

function changeTheme(event) {
  applyTheme(event.target.value);
  themeChannel?.postMessage({ theme: state.theme });
  render();
  rememberTheme(state.theme);
}

function themeHeard(event) {
  const heard = themeMessage(event.data);
  if (heard?.forgotten === true) {
    writeStorage(THEME_STORAGE, "auto");
    // The page keeps what it shows; what it remembered is gone, with the
    // layouts of the person (stage K2 of v2.2.0).
    state.settings = settingsAfterForget(state.settings);
    state.forgotten = true;
    viewLater.take();
    takeLayouts([], [], null);
    render();
  } else if (heard !== null) {
    applyTheme(heard.theme);
    render();
  }
}

async function changeHints() {
  state.hints = ui.hintsToggle.checked;
  render();
  try {
    state.settingsNotice = noticeOf(await callApi("/api/settings/hints", { on: state.hints }));
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

// The items and the shelf are remembered, by their names only (stage G3b),
// and from v2.2.0 (stage K2) the layout used last, the period, the grouping,
// and the activity types: once the person stops changing them for a moment,
// one request after the other, so that the last one stays.
let viewWriting = Promise.resolve();
function writeView(value) {
  viewWriting = viewWriting.then(async () => {
    try {
      state.settingsNotice = noticeOf(await callApi("/api/settings/view", value));
    } catch (error) {
      connectionFailure(error);
    }
    render();
  });
  return viewWriting;
}
const viewLater = laterSender(writeView, REMEMBER_WAIT_MS);

// The values of the view that the settings remember.
function viewValues() {
  return {
    items: [...state.items],
    shelf: state.shelf,
    layout: state.layouts.current,
    period: periodRequest(state.period, state.range),
    grain: state.grain,
    types: state.wantedTypes,
  };
}

// The view is remembered when an output opens and when the person changes
// it; after the other tab forgot the settings, only a change of the person
// writes it again.
function rememberItems(byPerson = false) {
  if (byPerson) {
    state.forgotten = false;
  }
  if (state.forgotten || !state.items.length) {
    return;
  }
  viewLater.push(viewValues());
}

// What waits to be remembered is written at once, before the app quits from
// either page (stage K2 of v2.2.0); the promise ends when every write ended,
// that one and one sent before it.
function rememberNow() {
  viewLater.flush();
  return viewWriting;
}

// When the page hides or closes, what waits goes in a request that outlives
// the page.
function rememberOnHide() {
  const value = viewLater.take();
  if (value !== null && state.launchKey) {
    callWithKey(state.launchKey, "/api/settings/view", value, { keepalive: true }).catch(() => {});
  }
}

function changeLanguage(language) {
  if (LANGUAGES.includes(language)) {
    state.language = language;
    writeStorage(LANGUAGE_STORAGE, language);
    render();
  }
}

// --- The tabs -------------------------------------------------------------

// The normalization page, in its tab if there is one, or in a new tab with
// the key of the launch (stage G3b).
function toNormalize() {
  const tab = window.open("", NORMALIZE_TAB);
  if (tab === null) {
    return;
  }
  let href = null;
  try {
    href = tab.location.href;
  } catch {
    href = null;
  }
  const address = normalizePageAddress(href, state.launchKey, state.theme);
  if (address !== null) {
    tab.location.href = address;
  }
  tab.focus();
}

// The normalization page opened this tab again with an address: the key, and
// the output of its run to show.
async function addressChanged() {
  const output = addressValue("output");
  const key = readLaunchKey();
  if (key) {
    state.launchKey = key;
  }
  if (output === "run" && state.connected) {
    await loadOutputs();
    if (state.runOutput !== null) {
      openOutput({ output: "run", name: state.runOutput.name });
    }
  }
}

// --- The outputs ----------------------------------------------------------

async function loadOutputs() {
  try {
    const run = await callApi("/api/run/status");
    state.runOutput =
      FINISHED_STATES.includes(run?.state) && typeof run.output_path === "string"
        ? { path: run.output_path, name: lastName(run.output_path) }
        : null;
    const earlier = await callApi("/api/outputs");
    state.earlier = Array.isArray(earlier?.outputs) ? { list: earlier.list, outputs: earlier.outputs } : null;
  } catch (error) {
    connectionFailure(error);
  }
}

function choice() {
  return startChoice({
    runOutput: state.runOutput,
    earlier: state.earlier?.outputs ?? [],
    remembered: itemsRemembered(state.settings),
  });
}

// The request of an output: this launch's run, a number of the list of
// earlier outputs, or a place that the system's dialog chose.
function targetOf(output) {
  if (output === state.runOutput) {
    return { output: "run", name: output.name };
  }
  if (typeof output?.index === "number") {
    return { output: "earlier", index: output.index, list: state.earlier?.list, name: output.name };
  }
  return { output: "chosen", path: output.path, name: output.name };
}

function targetPayload(target) {
  if (target.output === "earlier") {
    return { output: "earlier", index: target.index, list: target.list };
  }
  if (target.output === "chosen") {
    return { output: "chosen", path: target.path };
  }
  return { output: "run" };
}

const OUTPUT_STOPS = [
  "OUTPUT_OTHER_VERSION",
  "SERIES_OUTPUT_OTHER_VERSION",
  "OUTPUT_CHANGED",
  "OUTPUT_NOT_AVAILABLE",
  "HANDOFF_INVALID",
  "TIMEZONE_DATA_UNAVAILABLE",
];

async function openOutput(target, focus = false) {
  const seq = ++state.openSeq;
  const current = state.view === null ? null : state.items;
  state.opening = target.name;
  state.openingTarget = target;
  state.stop = null;
  state.seriesStop = null;
  state.typesOpen = false;
  state.pickerOpen = false;
  render();
  try {
    const answer = await callApi("/api/view/open", targetPayload(target));
    if (seq !== state.openSeq) {
      return;
    }
    const remembered = rememberedItems(state.settings, answer.items);
    state.items = itemsToOpen(current, remembered, answer.first_items, answer.items);
    state.view = answer;
    state.target = target;
    state.opening = null;
    // The activity types and the period as the person chose them last, where
    // this output has them, and its built-in layouts (stage K2 of v2.2.0).
    state.counted = typesToOpen(state.wantedTypes, answer.types) ?? defaultTypes(answer.types);
    state.layouts.builtIns = Array.isArray(answer.layouts) ? answer.layouts : [];
    state.coverage = answer.coverage;
    state.coverageSeq += 1;
    setAnswer(null);
    state.overview = null;
    state.big = null;
    state.tables = new Set();
    state.notesOpen = null;
    state.cursor = null;
    const period = periodToOpen(periodRequest(state.period, state.range), answer.first_day, answer.last_day) ?? { choice: "all", range: null };
    state.period = period.choice;
    state.range = period.range;
    ui.rangeFrom.value = state.range?.from ?? "";
    ui.rangeTo.value = state.range?.to ?? "";
    rememberItems();
    render();
    // A button that opened it is hidden now.
    if (document.activeElement === document.body || document.activeElement?.closest("[hidden]")) {
      ui.outputSelect.focus();
    }
    requestSeries();
  } catch (error) {
    if (seq !== state.openSeq) {
      return;
    }
    state.opening = null;
    if (!connectionFailure(error)) {
      state.view = null;
      setAnswer(null);
      // The field keeps the output that could not be opened.
      state.target = error.code === "OUTPUT_LIST_CHANGED" ? null : target;
      state.stop = { code: error.code, detail: error.detail };
      if (error.code === "OUTPUT_LIST_CHANGED") {
        await loadOutputs();
      }
    }
    render();
    if (focus || state.stop !== null) {
      ui.stopHeading.focus();
    }
  }
}

function openLatest() {
  const latest = choice().latest;
  if (latest !== null) {
    openOutput(targetOf(latest));
  }
}

function outputChosen() {
  const value = ui.outputSelect.value;
  if (value === "run" && state.runOutput !== null) {
    openOutput(targetOf(state.runOutput));
  } else if (value.startsWith("earlier-")) {
    const output = state.earlier?.outputs.find((entry) => `earlier-${entry.index}` === value);
    if (output) {
      openOutput(targetOf(output));
    }
  } else if (value === "chosen" && state.chosen !== null) {
    openOutput(targetOf(state.chosen));
  }
}

// The system's dialog for a folder, one for all the tabs (stage B3a): the
// request returns when it opens, and the page asks for its answer. A dialog
// that this computer does not have, or that is open in the other tab, is a
// stop of the page; the list of outputs stays.
async function chooseWithDialog(button) {
  state.choosing = true;
  render();
  let chosen = null;
  let failure = null;
  try {
    await callApi("/api/choose", { kind: "folder" });
    let answer = { state: "open" };
    while (answer.state === "open" && state.connected) {
      await new Promise((resolve) => window.setTimeout(resolve, CHOOSE_POLL_MS));
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
  state.choosing = false;
  if (chosen !== null) {
    state.chosen = { path: chosen, name: lastName(chosen) };
    openOutput(targetOf(state.chosen));
    return;
  }
  if (failure !== null) {
    // The output that is shown stays; the stop is told above it.
    state.stop = { code: failure, detail: null };
  }
  render();
  if (failure !== null) {
    ui.stopHeading.focus();
  } else if (!button.disabled && !button.closest("[hidden]")) {
    button.focus();
  }
}

// --- The numbers ----------------------------------------------------------

function seriesPayload(items, period, grain) {
  return {
    view: state.view.view,
    items,
    period,
    grain,
    types: typesRequest(state.counted, state.view.types),
  };
}

// Ask for the numbers of the panels; only the answer of the last request is
// shown. A ticket that the server no longer keeps opens the output again,
// once.
async function requestSeries(again = true) {
  if (state.view === null || !state.items.length) {
    setAnswer(null);
    state.loading = false;
    render();
    requestOverview();
    return;
  }
  const seq = ++state.seriesSeq;
  state.loading = true;
  render();
  try {
    const answer = await callApi("/api/view/series", seriesPayload(state.items, periodRequest(state.period, state.range), state.grain));
    if (seq !== state.seriesSeq) {
      return;
    }
    setAnswer(answer);
    state.stop = null;
    if (answer.coverage) {
      state.coverage = answer.coverage;
      state.coverageSeq += 1;
    }
    state.seriesStop = null;
    if (state.cursor === null || state.cursor >= answer.periods.length) {
      state.cursor = answer.periods.length ? answer.periods.length - 1 : null;
    }
  } catch (error) {
    if (seq !== state.seriesSeq) {
      return;
    }
    if (connectionFailure(error)) {
      // The bar says so.
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null) {
      if (await reopen()) {
        if (seq !== state.seriesSeq) {
          return;
        }
        state.loading = false;
        requestSeries(false);
        return;
      }
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.stop = { code: error.code, detail: error.detail };
    } else {
      state.seriesStop = { code: error.code, detail: error.detail };
    }
  }
  if (seq === state.seriesSeq) {
    state.loading = false;
  }
  render();
  requestOverview();
}

// Open the output that is shown again, for a new ticket, and keep what the
// panels show.
async function reopen() {
  try {
    const answer = await callApi("/api/view/open", targetPayload(state.target));
    state.view = answer;
    return true;
  } catch (error) {
    if (!connectionFailure(error)) {
      state.view = null;
      setAnswer(null);
      state.stop = { code: error.code, detail: error.detail };
      render();
    }
    return false;
  }
}

function overviewKey() {
  return state.big ?? state.items[0] ?? null;
}

// The overview: the whole output by month, of the first panel or of the one
// enlarged.
async function requestOverview() {
  const key = overviewKey();
  if (state.view === null || key === null) {
    state.overview = null;
    render();
    return;
  }
  const signature = JSON.stringify([state.view.view, key, typesRequest(state.counted, state.view.types)]);
  if (state.overview?.signature === signature) {
    return;
  }
  const seq = ++state.overviewSeq;
  try {
    const answer = await callApi("/api/view/series", seriesPayload([key], "all", "month"));
    if (seq === state.overviewSeq) {
      state.overview = { signature, key, answer };
      render();
    }
  } catch (error) {
    if (seq === state.overviewSeq && !connectionFailure(error)) {
      state.overview = null;
    }
    render();
  }
}

function setPeriod(choiceName) {
  if (choiceName === "custom") {
    state.period = "custom";
    state.range = state.range ?? (state.answer?.start ? { from: state.answer.start, to: state.answer.end } : null);
    render();
    ui.rangeFrom.value = state.range?.from ?? "";
    ui.rangeTo.value = state.range?.to ?? "";
    ui.rangeFrom.focus();
    if (state.range !== null) {
      rememberItems(true);
      requestSeries();
    }
    return;
  }
  state.period = choiceName;
  state.cursor = null;
  rememberItems(true);
  requestSeries();
}

function shiftPeriod(direction) {
  const range = shiftedRange(state.answer?.start, state.answer?.end, direction, state.view?.first_day, state.view?.last_day);
  if (range !== null) {
    state.period = "custom";
    state.range = range;
    ui.rangeFrom.value = range.from;
    ui.rangeTo.value = range.to;
    state.cursor = null;
    rememberItems(true);
    requestSeries();
  }
}

function rangeTyped() {
  const problem = rangeProblem(ui.rangeFrom.value, ui.rangeTo.value, state.view?.first_day, state.view?.last_day);
  setText(ui.rangeProblem, problem === null ? "" : t(problem));
  if (problem === null) {
    state.period = "custom";
    state.range = { from: ui.rangeFrom.value, to: ui.rangeTo.value };
    state.cursor = null;
    rememberItems(true);
    requestSeries();
  }
}

function setGrain(grain) {
  state.grain = grain;
  state.cursor = null;
  rememberItems(true);
  requestSeries();
}

function changeTypes(name) {
  state.counted = toggledTypes(state.counted, name, state.view?.types);
  state.wantedTypes = typesRequest(state.counted, state.view?.types);
  rememberItems(true);
  requestSeries();
}

function changeItems(items, refresh = true) {
  const removed = state.items.filter((key) => !items.includes(key));
  state.items = items;
  if (removed.includes(state.big)) {
    state.big = null;
  }
  for (const key of removed) {
    state.tables.delete(key);
  }
  if (removed.includes(state.notesOpen)) {
    state.notesOpen = null;
  }
  rememberItems(true);
  if (refresh && items.some((key) => !state.answer?.panels.some((panel) => panel.item === key))) {
    requestSeries();
  } else {
    render();
    requestOverview();
  }
}

// --- Layouts (stage K2 of v2.2.0) -------------------------------------------

function currentCards() {
  return layoutCards({ ...state.layouts, items: state.items, coverage: state.coverage });
}

// A card chosen: the panels become its items, in its order (those that this
// output knows), and it is the layout used last.
function chooseLayout(id) {
  const card = currentCards().find((entry) => entry.id === id);
  if (card === undefined || state.view === null) {
    return;
  }
  const known = itemsByKey(state.view.items);
  state.layouts.current = id;
  state.layoutProblem = null;
  changeItems(card.items.filter((key) => known.has(key)));
}

// The layouts as the server answers them now; a view that waits to be
// remembered takes the layout used last as it is now.
function takeLayouts(mine, hidden, current) {
  state.layouts.mine = Array.isArray(mine) ? mine : [];
  state.layouts.hidden = Array.isArray(hidden) ? hidden : [];
  state.layouts.current = typeof current === "string" ? current : null;
  if (viewLater.waiting()) {
    viewLater.push(viewValues());
  }
}

// The layouts as the settings hold them now, when another tab changed them.
async function readLayouts() {
  try {
    const status = await callApi("/api/status");
    const settings = status.settings ?? {};
    takeLayouts(settings.view_layouts, settings.view_layouts_hidden, settings.view_layout);
  } catch (error) {
    connectionFailure(error);
  }
}

// One change of the layouts on the server (add, rename, overwrite, move,
// remove, hide, show, reset); a change that cannot be made says why, where
// it was asked.
async function changeLayouts(change, done = null) {
  state.layoutProblem = null;
  try {
    const answer = await callApi("/api/settings/layouts", change);
    takeLayouts(answer.layouts, answer.hidden, answer.layout);
    state.settingsNotice = noticeOf(answer);
    done?.();
  } catch (error) {
    if (!connectionFailure(error)) {
      if (error.code === "LAYOUT_NOT_FOUND") {
        await readLayouts();
      }
      state.layoutProblem = LAYOUT_PROBLEM_KEYS[error.code] ?? "view.layouts.error.other";
    }
  }
  render();
}

function openLayoutSave(open) {
  state.layoutSaving = open;
  state.layoutProblem = null;
  render();
  if (open) {
    ui.layoutName.value = "";
    ui.layoutName.focus();
  } else {
    ui.layoutSaveAs.focus();
  }
}

function saveLayout() {
  changeLayouts({ op: "add", name: ui.layoutName.value, items: [...state.items] }, () => {
    state.layoutSaving = false;
    ui.layoutSaveAs.focus();
  });
}

function overwriteLayout() {
  if (state.layouts.current !== null) {
    changeLayouts({ op: "overwrite", id: state.layouts.current, items: [...state.items] });
  }
}

// The window of managing the layouts: its first button takes the focus, and
// its opener takes it back when it closes.
function openLayouts(open) {
  state.layoutsOpen = open;
  state.layoutAsk = null;
  state.layoutRenaming = null;
  state.layoutProblem = null;
  render();
  if (open) {
    ui.layoutsPopBody.querySelector("button:not([disabled]), input")?.focus();
  } else {
    ui.layoutsManage.focus();
  }
}

// The cards on the folded shelf, in a window of their own.
function openRailLayouts(open) {
  state.railLayoutsOpen = open;
  render();
  if (open) {
    (ui.railLayoutCards.querySelector('[aria-pressed="true"]') ?? ui.railLayoutCards.querySelector("button"))?.focus();
  } else {
    ui.railLayouts.focus();
  }
}

// The buttons of the window of managing the layouts. A removal is asked
// first, with keeping the layout as the button that has the focus.
function layoutsAction(event) {
  const button = event.target.closest("button[data-op]");
  if (button === null) {
    return;
  }
  const { op, id } = button.dataset;
  if (op === "rename") {
    state.layoutRenaming = id;
    state.layoutAsk = null;
    render();
    ui.layoutsPopBody.querySelector("input")?.focus();
  } else if (op === "rename-save") {
    const field = ui.layoutsPopBody.querySelector("input");
    changeLayouts({ op: "rename", id, name: field?.value ?? "" }, () => {
      state.layoutRenaming = null;
    });
  } else if (op === "rename-cancel") {
    state.layoutRenaming = null;
    render();
  } else if (op === "up" || op === "down") {
    changeLayouts({ op: "move", id, direction: op });
  } else if (op === "overwrite") {
    changeLayouts({ op: "overwrite", id, items: [...state.items] });
  } else if (op === "remove") {
    state.layoutAsk = id;
    state.layoutRenaming = null;
    render();
    ui.layoutsPopBody.querySelector('[data-op="keep"]')?.focus();
  } else if (op === "keep") {
    state.layoutAsk = null;
    render();
  } else if (op === "remove-yes") {
    changeLayouts({ op: "remove", id }, () => {
      state.layoutAsk = null;
    });
  } else if (op === "hide" || op === "show") {
    changeLayouts({ op, id });
  } else if (op === "reset") {
    changeLayouts({ op: "reset" });
  }
}

// A card: the name of the layout (a built-in one in the words of the page, the
// person's as text), and under it "(changed)" and the items with a value.
function layoutButton(card, viewing) {
  const button = element("button", "layout-card");
  button.type = "button";
  button.dataset.layout = card.id;
  button.setAttribute("aria-pressed", String(card.current));
  button.disabled = !viewing;
  button.append(element("span", "layout-name", card.builtIn ? t(card.nameKey) : card.name));
  for (const note of layoutNotes(card)) {
    button.append(element("span", "layout-note", describe(note)));
  }
  return button;
}

function renderCards(container, cards, viewing) {
  const signature = JSON.stringify([viewing, cards, state.language]);
  if (container.dataset.signature === signature) {
    return;
  }
  const focused = container.contains(document.activeElement) ? (document.activeElement.dataset.layout ?? null) : null;
  container.replaceChildren(...cards.map((card) => layoutButton(card, viewing)));
  container.dataset.signature = signature;
  if (focused !== null) {
    [...container.querySelectorAll("[data-layout]")].find((node) => node.dataset.layout === focused)?.focus();
  }
}

function opButton(op, id, key, disabled = false) {
  const button = element("button", "small", t(key));
  button.type = "button";
  button.dataset.op = op;
  if (id !== null) {
    button.dataset.id = id;
  }
  button.disabled = disabled;
  return button;
}

// The window of managing: the person's layouts (rename, up, down, remove),
// then the built-in ones (hide or show), and showing them all again.
function renderLayoutsPop(viewing) {
  const signature = JSON.stringify([viewing, state.layouts, state.layoutAsk, state.layoutRenaming, state.language]);
  if (ui.layoutsPopBody.dataset.signature === signature) {
    return;
  }
  const active = document.activeElement;
  const focused = ui.layoutsPopBody.contains(active) ? { op: active.dataset.op ?? null, id: active.dataset.id ?? null } : null;
  const nodes = [element("p", "layouts-group", t("view.layouts.mine"))];
  const mine = state.layouts.mine;
  // A layout is not dragged while one is renamed or a removal is asked.
  const busy = state.layoutAsk !== null || state.layoutRenaming !== null;
  if (!mine.length) {
    nodes.push(element("p", "note", t("view.layouts.none_mine")));
  }
  mine.forEach((layout, index) => {
    const row = element("div", "layouts-row mine");
    if (state.layoutRenaming === layout.id) {
      const field = element("input");
      field.type = "text";
      field.value = layout.name;
      field.maxLength = 60;
      field.setAttribute("aria-label", t("view.layouts.name_label"));
      row.append(field, opButton("rename-save", layout.id, "view.layouts.save"), opButton("rename-cancel", layout.id, "view.layouts.cancel"));
    } else {
      // The grip: a drag, or the arrow keys, move the layout.
      const grip = element("button", "layout-grip", "⋮⋮");
      grip.type = "button";
      grip.dataset.op = "grip";
      grip.dataset.id = layout.id;
      grip.disabled = !viewing || busy || mine.length < 2;
      grip.setAttribute("aria-label", t("view.layouts.grip", { name: layout.name }));
      const buttons = element("div", "layouts-buttons");
      buttons.append(
        opButton("rename", layout.id, "view.layouts.rename", !viewing),
        opButton("up", layout.id, "view.layouts.up", !viewing || index === 0),
        opButton("down", layout.id, "view.layouts.down", !viewing || index === mine.length - 1),
        opButton("overwrite", layout.id, "view.layouts.overwrite", !viewing || !state.items.length),
        opButton("remove", layout.id, "view.layouts.remove", !viewing),
      );
      row.append(grip, element("span", "layout-name", layout.name), buttons);
    }
    nodes.push(row);
    if (state.layoutAsk === layout.id) {
      const ask = element("div", "layouts-ask");
      ask.append(element("p", "", t("view.layouts.remove_ask", { name: layout.name })), opButton("keep", layout.id, "view.layouts.keep"), opButton("remove-yes", layout.id, "view.layouts.remove"));
      nodes.push(ask);
    }
  });
  nodes.push(element("p", "layouts-group", t("view.layouts.built_in")));
  for (const card of layoutCards({ builtIns: state.layouts.builtIns, mine: [], hidden: [], current: null, items: [], coverage: null })) {
    const hidden = state.layouts.hidden.includes(card.id);
    const row = element("div", "layouts-row");
    row.append(element("span", "layout-name", t(card.nameKey)), opButton(hidden ? "show" : "hide", card.id, hidden ? "view.layouts.show" : "view.layouts.hide", !viewing));
    nodes.push(row);
  }
  nodes.push(opButton("reset", null, "view.layouts.show_all", !viewing || !state.layouts.hidden.length));
  ui.layoutsPopBody.replaceChildren(...nodes);
  ui.layoutsPopBody.dataset.signature = signature;
  if (focused !== null) {
    const enabled = [...ui.layoutsPopBody.querySelectorAll("button[data-op]")].filter((node) => !node.disabled);
    const again =
      enabled.find((node) => node.dataset.op === focused.op && (node.dataset.id ?? null) === focused.id) ??
      enabled.find((node) => focused.id !== null && node.dataset.id === focused.id);
    (again ?? ui.layoutsPopBody.querySelector("button:not([disabled]), input"))?.focus();
  }
}

// A drag of the grip of a layout moves its row among the others as the
// pointer moves, and the place goes to the server once, when the grip is let
// go. Escape, or a pointer that the browser takes back, puts the row back.
// The body of the window holds the pointer, so that a row moves freely.
let layoutDrag = null;

function layoutGripDown(event) {
  const grip = event.target.closest('button[data-op="grip"]');
  if (grip === null || grip.disabled || event.button !== 0 || layoutDrag !== null) {
    return;
  }
  event.preventDefault();
  const row = grip.closest(".layouts-row");
  const from = [...ui.layoutsPopBody.querySelectorAll(".layouts-row.mine")].indexOf(row);
  layoutDrag = { id: grip.dataset.id, row, from, to: from, pointer: event.pointerId };
  ui.layoutsPopBody.setPointerCapture(event.pointerId);
  row.classList.add("dragging");
  grip.focus();
}

function layoutGripMove(event) {
  if (layoutDrag === null || event.pointerId !== layoutDrag.pointer) {
    return;
  }
  const others = [...ui.layoutsPopBody.querySelectorAll(".layouts-row.mine")].filter((row) => row !== layoutDrag.row);
  const middles = others.map((row) => {
    const box = row.getBoundingClientRect();
    return box.top + box.height / 2;
  });
  const to = dropPlace(middles, event.clientY);
  if (to !== layoutDrag.to && others.length) {
    layoutDrag.to = to;
    if (to < others.length) {
      others[to].before(layoutDrag.row);
    } else {
      others[others.length - 1].after(layoutDrag.row);
    }
    // A row that moves loses the focus: its grip takes it again, for Escape.
    layoutDrag.row.querySelector(".layout-grip")?.focus();
  }
}

// The drag ends: the rows are drawn again from the layouts, as the server
// answers them.
function endLayoutDrag() {
  const ended = layoutDrag;
  layoutDrag = null;
  if (ended !== null) {
    ended.row.classList.remove("dragging");
    if (ui.layoutsPopBody.hasPointerCapture(ended.pointer)) {
      ui.layoutsPopBody.releasePointerCapture(ended.pointer);
    }
    delete ui.layoutsPopBody.dataset.signature;
  }
  return ended;
}

function layoutGripUp(event) {
  if (layoutDrag === null || event.pointerId !== layoutDrag.pointer) {
    return;
  }
  const { id, from, to } = endLayoutDrag();
  if (to !== from) {
    changeLayouts({ op: "move", id, to });
  } else {
    render();
  }
}

function cancelLayoutDrag() {
  if (endLayoutDrag() !== null) {
    render();
  }
}

// The layouts above the item shelf, their buttons, and their windows.
function renderLayouts(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const cards = currentCards();
  renderCards(ui.layoutCards, cards, viewing);
  renderCards(ui.railLayoutCards, cards, viewing);
  const current = cards.find((card) => card.current) ?? null;
  ui.layoutsManage.disabled = !viewing;
  ui.layoutsManage.setAttribute("aria-expanded", String(state.layoutsOpen));
  ui.layoutSaveAs.disabled = !viewing || !state.items.length;
  ui.layoutSaveAs.setAttribute("aria-expanded", String(state.layoutSaving));
  ui.layoutOverwrite.hidden = !(viewing && current !== null && !current.builtIn && current.changed);
  ui.layoutSave.hidden = !state.layoutSaving;
  ui.layoutSaveButton.disabled = !viewing;
  setText(ui.layoutProblem, state.layoutProblem === null ? "" : t(state.layoutProblem));
  ui.layoutsPop.hidden = !state.layoutsOpen;
  if (state.layoutsOpen) {
    renderLayoutsPop(viewing);
  }
  ui.railLayouts.disabled = !viewing;
  ui.railLayouts.setAttribute("aria-expanded", String(state.railLayoutsOpen));
  ui.railLayoutsPop.hidden = !state.railLayoutsOpen;
}

// --- Drawing --------------------------------------------------------------

function itemName(key) {
  return t(itemKey(key));
}

// The panels of the answer in the order of the items.
function shownPanels() {
  const answer = state.answer;
  if (answer === null) {
    return [];
  }
  const items = itemsByKey(state.view?.items);
  const byItem = new Map(answer.panels.map((panel) => [panel.item, panel]));
  const keys = state.big !== null && state.items.includes(state.big) ? [state.big, ...state.items.filter((key) => key !== state.big)] : state.items;
  return keys.filter((key) => byItem.has(key) && items.has(key)).map((key) => ({ key, item: items.get(key), panel: byItem.get(key) }));
}

function panelMode(key) {
  if (state.big === null || !state.items.includes(state.big)) {
    return "normal";
  }
  return key === state.big ? "big" : "mini";
}

// A short piece of a line, in its color and its dash, beside its name or its
// value; a point, hollow for a sport other than running, where the panel
// shows the records of each day as points.
function lineSwatch(style, points = false) {
  const swatch = svgElement("svg", { viewBox: "0 0 22 8", "aria-hidden": "true", focusable: "false" });
  if (points) {
    swatch.append(svgElement("circle", { cx: 11, cy: 4, r: 3, class: `key-dot c${style.color}${style.dash === null ? "" : " hollow"}` }));
  } else {
    swatch.append(svgElement("line", { x1: 2, x2: 20, y1: 4, y2: 4, class: `key-line c${style.color}`, "stroke-dasharray": style.dash }));
  }
  return swatch;
}

function showsPoints(panel) {
  return panel.lines.some((line) => Array.isArray(line.points));
}

function buildPanel({ key, item, panel }, index, count, periods, grain) {
  const mode = panelMode(key);
  const table = state.tables.has(key) && mode !== "mini";
  const name = itemName(key);
  const section = element("section", `panel-view${table ? " table" : ""}${mode === "normal" ? "" : ` ${mode}`}`);
  section.dataset.key = key;
  const headingId = `panel-${key}-name`;
  section.setAttribute("aria-labelledby", headingId);
  const head = element("div", "panel-head");
  const heading = element("h3", "panel-name", name);
  heading.id = headingId;
  head.append(heading, element("span", "panel-unit", t(unitKey(key))));
  const styles = lineStyles(panel);
  const names = lineNames(panel, state.language);
  if (mode !== "mini") {
    head.append(element("span", "panel-kind", t(kindKey(item, grain))));
    if (panel.lines.length > 1) {
      const keys = element("span", "panel-keys");
      panel.lines.forEach((_line, number) => {
        const entry = element("span", "key");
        entry.append(lineSwatch(styles[number], showsPoints(panel)), describe(names[number]));
        keys.append(entry);
      });
      head.append(keys);
    }
  }
  const read = element("span", "panel-read");
  read.setAttribute("aria-hidden", "true");
  head.append(read);
  const tools = element("span", "panel-tools");
  if (mode !== "mini") {
    const tableButton = textButton(t(table ? "view.panel.chart" : "view.panel.table"), "table", key);
    tableButton.setAttribute("aria-pressed", String(table));
    tools.append(tableButton);
  }
  if (mode === "big") {
    tools.append(textButton(t("view.panel.unbig"), "unbig", key));
  } else {
    tools.append(iconButton("expand", t("view.panel.big", { name }), "big", key));
  }
  if (mode === "normal") {
    tools.append(
      iconButton("up", t("view.panel.up", { name }), "up", key, index === 0),
      iconButton("down", t("view.panel.down", { name }), "down", key, index === count - 1),
    );
  }
  tools.append(iconButton("close", t("view.panel.remove", { name }), "remove", key));
  head.append(tools);
  section.append(head);
  let notesPop = null;
  if (mode !== "mini") {
    const summary = element("div", "panel-summary");
    for (const part of summaryMessages(item, panel, periods, grain, state.language)) {
      const span = element("span");
      span.append(...richNodes(part));
      summary.append(span);
    }
    const notes = panelNotes(item, panel, periods, grain, state.language);
    if (notes.length) {
      const button = textButton(t("view.panel.notes", { n: notes.length }), "notes", key, "info-button");
      const popId = `panel-${key}-notes`;
      button.setAttribute("aria-expanded", String(state.notesOpen === key));
      button.setAttribute("aria-controls", popId);
      summary.append(button);
      notesPop = element("div", `pop notes-pop${mode !== "big" && index >= count / 2 ? " above" : ""}`);
      notesPop.id = popId;
      notesPop.hidden = state.notesOpen !== key;
      notesPop.dataset.key = key;
      notesPop.append(element("p", "pop-title", t("view.panel.about", { name })));
      const list = element("ul");
      for (const note of notes) {
        const entry = element("li", "", describe(note));
        if (note.help) {
          const link = textButton(t(HELP_LINK_KEYS[note.help]), "help", note.help, "info-button");
          entry.append(" ", link);
        }
        list.append(entry);
      }
      notesPop.append(list);
    }
    section.append(summary);
  }
  let body;
  if (table) {
    body = buildTable(item, panel, periods, grain, name);
  } else {
    body = element("div", "panel-chart");
    const plot = element("div", "plot");
    plot.tabIndex = 0;
    plot.setAttribute("role", "img");
    plot.dataset.key = key;
    plot.setAttribute(
      "aria-label",
      t("view.chart.label", {
        name,
        start: describe(periodMessage(periods[0], grain, state.language, { mark: false })),
        end: describe(periodMessage(periods[periods.length - 1], grain, state.language, { mark: false })),
      }),
    );
    body.append(plot);
  }
  section.append(body);
  if (notesPop !== null) {
    section.append(notesPop);
  }
  return { section, key, item, panel, mode, table, read, styles, names };
}

// A table of a panel: every period, newest first, in parts as the person
// scrolls to them.
function buildTable(item, panel, periods, grain, name) {
  const wrap = element("div", "panel-table");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", t("view.table.label", { name }));
  const table = element("table", "t");
  const caption = element("caption", "visually-hidden", t("view.table.caption", { name, kind: t(kindKey(item, grain)) }));
  const head = element("thead");
  const headRow = element("tr");
  tableHeads(item, panel, grain, state.language).forEach((heading, index) => {
    const cell = element("th", index === 0 ? "" : "n", describe(heading));
    cell.scope = "col";
    headRow.append(cell);
  });
  head.append(headRow);
  const body = element("tbody");
  table.append(caption, head, body);
  wrap.append(table);
  const rows = tableRows(item, panel, periods, grain, state.language);
  let shownRows = 0;
  const sentinel = element("tr");
  const more = () => {
    const part = document.createDocumentFragment();
    for (const row of rows.slice(shownRows, shownRows + TABLE_ROWS)) {
      const line = element("tr");
      const period = element("th", "", describe(row.period));
      period.scope = "row";
      line.append(period);
      for (const cell of row.cells) {
        line.append(
          element("td", cell.value === null ? "n empty" : "n", cell.value === null ? t("view.no_value") : describe(cell.value)),
          element("td", "n", cell.count),
        );
      }
      part.append(line);
    }
    shownRows = Math.min(rows.length, shownRows + TABLE_ROWS);
    sentinel.remove();
    body.append(part);
    if (shownRows < rows.length) {
      body.append(sentinel);
    }
  };
  more();
  if (shownRows < rows.length && typeof IntersectionObserver === "function") {
    const watcher = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        more();
        if (shownRows >= rows.length) {
          watcher.disconnect();
        }
      }
    }, { root: wrap, rootMargin: "400px" });
    watcher.observe(sentinel);
  }
  return wrap;
}

// Draw the chart of a panel at the size of its plot, and keep that size: a
// plot whose size changes later is drawn again (renderCharts). The marks of a
// sport other than running are hollow points and dashed lines.
function drawChart(entry) {
  const plot = entry.plot;
  if (plot === null) {
    return;
  }
  const width = plot.clientWidth;
  const height = plot.clientHeight;
  entry.size = `${width} ${height}`;
  entry.shapes = null;
  entry.cross = null;
  if (width < 60 || height < 24) {
    plot.replaceChildren();
    return;
  }
  const { key, item, panel, styles, periods } = entry;
  const lines = panel.lines.map((line) => ({
    values: line.values.map((value) => (Number.isFinite(value) ? shown(key, value) : null)),
    points: Array.isArray(line.points) ? line.points.map(([index, value]) => [index, shown(key, value)]) : undefined,
  }));
  const total = totalItem(item);
  const shapes = panelShapes({
    lines,
    periods,
    start: periods[0].start,
    end: periods[periods.length - 1].end,
    width,
    height,
    total,
    clock: clockOf(key),
    shared: drawnShared.get(key) ?? null,
  });
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, "aria-hidden": "true", focusable: "false" });
  entry.shapes = shapes;
  entry.lines = lines;
  if (shapes.empty) {
    plot.replaceChildren(svg, element("span", "panel-empty", t("view.summary.none")));
    return;
  }
  const step = shapes.ticks.length > 1 ? Math.abs(shapes.ticks[1].value - shapes.ticks[0].value) : 1;
  for (const tick of shapes.ticks) {
    svg.append(svgElement("line", { class: "chart-grid", x1: PLOT_LEFT, x2: width - PLOT_RIGHT, y1: tick.y.toFixed(1), y2: tick.y.toFixed(1) }));
    const label = svgElement("text", { class: "chart-tick", x: PLOT_LEFT - 8, y: (tick.y + 4).toFixed(1), "text-anchor": "end" });
    label.textContent = tickText(key, tick.value, step, state.language);
    svg.append(label);
  }
  if (shapes.base !== null) {
    svg.append(svgElement("line", { class: "chart-base", x1: PLOT_LEFT, x2: width - PLOT_RIGHT, y1: shapes.base.toFixed(1), y2: shapes.base.toFixed(1) }));
  }
  shapes.lines.forEach((shape, number) => {
    const color = `c${styles[number].color}`;
    const dash = styles[number].dash;
    if (shape.bars !== null) {
      if (shape.bars.full) {
        svg.append(svgElement("path", { class: `chart-bar ${color}`, d: shape.bars.full }));
      }
      if (shape.bars.partial) {
        svg.append(svgElement("path", { class: `chart-bar ${color} partial`, d: shape.bars.partial }));
      }
    }
    if (shape.line) {
      svg.append(svgElement("path", { class: `chart-line ${color}`, d: shape.line, "stroke-dasharray": dash }));
    }
    const dots = (path, size) => {
      if (!path) {
        return;
      }
      // A hollow point needs room for its hole.
      const radius = dash !== null ? Math.max(size, 2.4) : size;
      if (radius >= 4) {
        svg.append(svgElement("path", { class: "chart-ring", d: path, "stroke-width": 2 * radius + 4 }));
      }
      svg.append(svgElement("path", { class: `chart-dots ${color}`, d: path, "stroke-width": 2 * radius }));
      if (dash !== null) {
        svg.append(svgElement("path", { class: "chart-hole", d: path, "stroke-width": Math.max(1, 2 * radius - 3) }));
      }
    };
    dots(shape.alone, shape.aloneRadius ?? 4);
    dots(shape.markers, 4);
    dots(shape.points, shape.pointRadius);
    if (shape.zero) {
      svg.append(svgElement("path", { class: "chart-zero", d: shape.zero }));
    }
  });
  const cross = svgElement("g", { class: "cross" });
  cross.setAttribute("display", "none");
  const crossLine = svgElement("line", { class: "chart-cross", y1: shapes.top, y2: shapes.top + shapes.plotHeight });
  cross.append(crossLine);
  const crossDots = panel.lines.map((_line, number) => {
    const dot = svgElement("circle", { class: `chart-cross-dot c${styles[number].color}`, r: 4.5 });
    cross.append(dot);
    return dot;
  });
  svg.append(cross);
  plot.replaceChildren(svg);
  Object.assign(entry, { cross, crossLine, crossDots });
}

// Draw the charts whose plots changed size since they were drawn, the time
// axis at the width of the plots, and the cross line again.
function renderCharts() {
  let changed = false;
  for (const entry of drawn) {
    if (entry.plot !== null && entry.size !== `${entry.plot.clientWidth} ${entry.plot.clientHeight}`) {
      drawChart(entry);
      changed = true;
    }
  }
  const chartWidth = drawn.find((entry) => entry.plot)?.plot.clientWidth ?? ui.panels.clientWidth;
  if (changed || ui.timeAxis.dataset.width !== String(chartWidth)) {
    const periods = drawn[0]?.periods;
    if (periods?.length) {
      drawTimeAxis(periods[0].start, periods[periods.length - 1].end, chartWidth);
      ui.timeAxis.dataset.width = String(chartWidth);
    }
  }
  if (changed) {
    moveCross(state.cursor, false);
  }
}

function drawTimeAxis(start, end, width) {
  ui.timeAxis.replaceChildren();
  if (width < 60) {
    return;
  }
  const height = ui.timeAxis.clientHeight || 24;
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, "aria-hidden": "true", focusable: "false" });
  const scale = timeScale(start, end, PLOT_LEFT, width - PLOT_RIGHT);
  for (const tick of timeTicks(start, end, width - PLOT_LEFT - PLOT_RIGHT)) {
    const x = scale.x(tick.day);
    svg.append(svgElement("line", { class: "axis-tick", x1: x.toFixed(1), x2: x.toFixed(1), y1: 0, y2: 5 }));
    const label = svgElement("text", { class: "axis-text", x: (x + 3).toFixed(1), y: 16 });
    label.textContent = timeTickText(tick, state.language);
    svg.append(label);
  }
  ui.timeAxis.append(svg);
}

function drawOverview(start, end, chartWidth) {
  const overview = state.overview;
  const item = itemsByKey(state.view?.items).get(overview?.key);
  if (!overview || !item || !overview.answer.panels.length) {
    ui.overviewPlot.replaceChildren();
    overviewParts = null;
    return;
  }
  if (chartWidth > 0) {
    ui.overviewPlot.style.width = `${Math.max(0, chartWidth - PLOT_LEFT - PLOT_RIGHT)}px`;
  }
  const width = ui.overviewPlot.clientWidth;
  const height = ui.overviewPlot.clientHeight;
  if (width < 40 || height < 20) {
    return;
  }
  const periods = periodDays(overview.answer.periods);
  const panel = overview.answer.panels[0];
  const values = panel.lines[0]?.values.map((value) => (Number.isFinite(value) ? shown(item.key, value) : null)) ?? [];
  const total = totalItem(item);
  const shapes = overviewShapes({ values, periods, width, height, total, start, end });
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, "aria-hidden": "true", focusable: "false" });
  svg.append(svgElement("path", { class: `overview-marks${total ? "" : " line"}`, d: shapes.marks }));
  const first = new Date(shapes.first * 86400000).getUTCFullYear();
  const last = new Date(shapes.last * 86400000).getUTCFullYear();
  const every = Math.max(1, Math.ceil((last - first + 1) / Math.max(1, Math.floor(width / 60))));
  for (let year = first + 1; year <= last; year += 1) {
    if ((year - first) % every !== 0) {
      continue;
    }
    const x = shapes.scale.x(Math.round(Date.UTC(year, 0, 1) / 86400000));
    const label = svgElement("text", { class: "axis-text", x: (x + 2).toFixed(1), y: height - 2 });
    label.textContent = String(year);
    svg.append(label);
  }
  // The frame and the dimmed sides, which a drag moves (placeFrame).
  const dims = [0, 1].map(() => svgElement("rect", { class: "overview-dim", x: 0, y: 0, height: shapes.base }));
  const frame = svgElement("rect", { class: "overview-frame", y: 0.5, height: shapes.base - 0.5, rx: 3 });
  const handles = [0, 1].map(() =>
    svgElement("rect", { class: "overview-handle", y: (shapes.base / 2 - 9).toFixed(1), width: 6, height: 18, rx: 2 }),
  );
  svg.append(...dims, frame, ...handles);
  overviewParts = { scale: shapes.scale, width, from: start, to: end, dims, frame, handles };
  placeFrame({ from: start, to: end });
  ui.overviewPlot.replaceChildren(svg);
  ui.overviewPlot.dataset.first = String(shapes.first);
  ui.overviewPlot.dataset.last = String(shapes.last);
}

// What the panels show now, to draw them again only when it changes.
function panelsSignature() {
  return JSON.stringify([
    state.answerSeq,
    state.items,
    state.big,
    [...state.tables],
    state.language,
    state.align,
  ]);
}

// The overview is drawn again when its numbers, the period, or its width
// change.
let overviewSignature = null;

function renderOverview(force = false) {
  const answer = state.answer;
  const chartWidth = drawn.find((entry) => entry.plot)?.plot.clientWidth ?? 0;
  const signature = JSON.stringify([state.overview?.signature ?? null, answer?.start ?? null, answer?.end ?? null, chartWidth, ui.overview.clientHeight]);
  if (!force && signature === overviewSignature) {
    return;
  }
  overviewSignature = signature;
  if (answer === null || !answer.periods.length) {
    ui.overviewPlot.replaceChildren();
    overviewParts = null;
    return;
  }
  const periods = periodDays(answer.periods);
  drawOverview(periods[0].start, periods[periods.length - 1].end, chartWidth);
}

function renderPanels(force = false) {
  const signature = panelsSignature();
  if (!force && signature === drawnSignature) {
    renderCharts();
    return;
  }
  const focused = focusMark();
  const answer = state.answer;
  const shownList = shownPanels();
  plotWatcher?.disconnect();
  if (answer === null || !shownList.length || !answer.periods.length) {
    ui.panels.replaceChildren();
    ui.timeAxis.replaceChildren();
    delete ui.timeAxis.dataset.width;
    drawn = [];
    drawnSignature = signature;
    return;
  }
  const periods = periodDays(answer.periods);
  const built = shownList.map((entry) => buildPanel(entry, state.items.indexOf(entry.key), state.items.length, answer.periods, answer.grain));
  ui.panels.replaceChildren(...built.map((entry) => entry.section));
  drawnShared = sharedExtents(
    built.map((entry) => ({
      key: entry.key,
      unitGroup: entry.item.unit_group,
      extent: extent(
        entry.panel.lines.map((line) => ({
          values: line.values.map((value) => (Number.isFinite(value) ? shown(entry.key, value) : null)),
          points: Array.isArray(line.points) ? line.points.map(([index, value]) => [index, shown(entry.key, value)]) : undefined,
        })),
      ),
    })),
    state.align,
  );
  drawn = built.map((entry) => ({
    ...entry,
    periods,
    plot: entry.section.querySelector(".plot"),
    size: null,
    shapes: null,
    cross: null,
  }));
  // The readings first, so that the heads of the panels have their lines
  // before the charts take the room that is left.
  moveCross(state.cursor ?? periods.length - 1, false);
  delete ui.timeAxis.dataset.width;
  renderCharts();
  for (const entry of drawn) {
    if (entry.plot !== null) {
      plotWatcher?.observe(entry.plot);
    }
  }
  drawnSignature = panelsSignature();
  restoreFocus(focused);
}

// The control that has focus, to give it focus again after the panels are
// drawn again.
function focusMark() {
  const active = document.activeElement;
  if (active === null || !ui.panels.contains(active)) {
    return null;
  }
  return { action: active.dataset.action ?? null, key: active.dataset.key ?? active.closest("[data-key]")?.dataset.key ?? null, plot: active.classList.contains("plot"), table: active.classList.contains("panel-table") };
}

function restoreFocus(mark) {
  if (mark === null) {
    return;
  }
  let target = null;
  if (mark.action !== null) {
    target = ui.panels.querySelector(`[data-action="${mark.action}"][data-key="${mark.key}"]:not(:disabled)`);
  } else if (mark.plot) {
    target = ui.panels.querySelector(`.plot[data-key="${mark.key}"]`);
  } else if (mark.table) {
    target = ui.panels.querySelector(`section[data-key="${mark.key}"] .panel-table`);
  }
  (target ?? ui.panels.querySelector(`section[data-key="${mark.key}"] button:not(:disabled)`))?.focus({ preventScroll: true });
}

function scheduleRedraw() {
  if (redrawFrame !== null) {
    return;
  }
  redrawFrame = window.requestAnimationFrame(() => {
    redrawFrame = null;
    if (!ui.stack.hidden) {
      renderPanels();
    }
    if (!ui.overview.hidden) {
      renderOverview();
    }
  });
}

// Move the cross line of every panel to one period, and say the values when
// the keyboard moved it.
function moveCross(index, speak) {
  const answer = state.answer;
  if (answer === null || index === null || !answer.periods.length) {
    return;
  }
  const last = answer.periods.length - 1;
  state.cursor = Math.max(0, Math.min(last, index));
  const spoken = [];
  for (const entry of drawn) {
    if (entry.cross !== null && entry.cross !== undefined && entry.shapes !== null && !entry.shapes.empty) {
      const x = periodMiddle(entry.shapes.scale, entry.periods[state.cursor]);
      entry.cross.setAttribute("display", "inline");
      entry.crossLine.setAttribute("x1", x.toFixed(1));
      entry.crossLine.setAttribute("x2", x.toFixed(1));
      entry.crossDots.forEach((dot, number) => {
        const value = entry.lines[number].values[state.cursor];
        if (Number.isFinite(value)) {
          dot.setAttribute("cx", x.toFixed(1));
          dot.setAttribute("cy", entry.shapes.y(value).toFixed(1));
          dot.setAttribute("display", "inline");
        } else {
          dot.setAttribute("display", "none");
        }
      });
    }
    const reading = readout(entry.item, entry.panel, answer.periods, state.cursor, answer.grain, state.language);
    const nodes = [];
    if (reading !== null) {
      nodes.push(describe(reading.period));
      if (reading.values.length) {
        reading.values.forEach((value, number) => {
          if (number > 0) {
            nodes.push("\u3000");
          }
          // Which line a value is of, where there are two or more.
          if (entry.panel.lines.length > 1) {
            nodes.push(lineSwatch(entry.styles[value.line], showsPoints(entry.panel)));
          }
          nodes.push(element("strong", "", describe(value.value)));
          if (value.count !== null) {
            nodes.push(describe(value.count));
          }
        });
      } else {
        nodes.push(element("span", "no-value", t("view.no_value")));
      }
      // Where a panel has two or more lines, each value says its line.
      const spokenValue = (value) =>
        entry.names[value.line] === null
          ? describe(value.value)
          : t("view.spoken_line", { line: describe(entry.names[value.line]), value: describe(value.value) });
      spoken.push(
        t("view.spoken_item", {
          name: itemName(entry.key),
          value: reading.values.length ? reading.values.map(spokenValue).join(t("view.spoken_separator")) : t("view.no_value"),
        }),
      );
    }
    entry.read.replaceChildren(...nodes);
  }
  if (speak) {
    const period = describe(periodMessage(answer.periods[state.cursor], answer.grain, state.language));
    setText(ui.announcer, t("view.spoken", { period, values: spoken.join(t("view.spoken_separator")) }));
  }
}

function plotKey(event) {
  if (Object.hasOwn(CROSS_KEYS, event.key)) {
    moveCross((state.cursor ?? 0) + CROSS_KEYS[event.key], true);
  } else if (event.key === "Home") {
    moveCross(0, true);
  } else if (event.key === "End") {
    moveCross((state.answer?.periods.length ?? 1) - 1, true);
  } else {
    return;
  }
  event.preventDefault();
}

function plotPointer(event) {
  const plot = event.target.closest(".plot");
  const entry = drawn.find((candidate) => candidate.plot === plot);
  if (!entry || entry.shapes === null || entry.shapes.empty) {
    return;
  }
  const box = plot.getBoundingClientRect();
  const index = nearestPeriod(entry.periods, entry.shapes.scale, event.clientX - box.left);
  if (index !== null && index !== state.cursor) {
    moveCross(index, false);
  }
}

// --- The overview ---------------------------------------------------------

// What a drag on the overview does: the edge that it moves ("from" or "to",
// or null for a new period), the day where it started, the period of the
// frame when it started, and its pointer.
let drag = null;
// The frame of the overview as it is drawn, which a drag moves.
let overviewParts = null;

function overviewDay(event) {
  const first = Number(ui.overviewPlot.dataset.first);
  const last = Number(ui.overviewPlot.dataset.last);
  const box = ui.overviewPlot.getBoundingClientRect();
  if (!Number.isFinite(first) || !Number.isFinite(last) || box.width <= 0) {
    return null;
  }
  const scale = timeScale(first, last, 0, box.width);
  return Math.max(first, Math.min(last, Math.round(scale.day(event.clientX - box.left))));
}

// The frame and the dimmed sides at a period of days of the overview.
function placeFrame(range) {
  const { scale, width, dims, frame, handles } = overviewParts;
  const from = scale.x(range.from);
  const to = scale.x(range.to + 1);
  dims[0].setAttribute("width", Math.max(0, from).toFixed(1));
  dims[1].setAttribute("x", to.toFixed(1));
  dims[1].setAttribute("width", Math.max(0, width - to).toFixed(1));
  frame.setAttribute("x", from.toFixed(1));
  frame.setAttribute("width", Math.max(1, to - from).toFixed(1));
  handles[0].setAttribute("x", (from - 3).toFixed(1));
  handles[1].setAttribute("x", (to - 3).toFixed(1));
}

// The edge of the frame under the pointer, which the shape of the pointer
// and the color of its handle show.
function gripAt(event) {
  if (overviewParts === null) {
    return null;
  }
  const { scale, from, to } = overviewParts;
  return overviewGrip(event.clientX - ui.overviewPlot.getBoundingClientRect().left, scale.x(from), scale.x(to + 1));
}

function showGrip(grip) {
  if (grip === null) {
    delete ui.overviewPlot.dataset.grip;
  } else {
    ui.overviewPlot.dataset.grip = grip;
  }
  overviewParts?.handles.forEach((handle, number) => handle.classList.toggle("on", grip === (number === 0 ? "from" : "to")));
}

function overviewDown(event) {
  const day = overviewDay(event);
  if (day === null || overviewParts === null || event.button !== 0) {
    return;
  }
  const range = { from: overviewParts.from, to: overviewParts.to };
  drag = { grip: gripAt(event), start: day, range, pointer: event.pointerId };
  ui.overviewPlot.setPointerCapture(event.pointerId);
  ui.overviewPlot.dataset.drag = drag.grip ?? "new";
  showGrip(drag.grip);
}

// The frame follows the pointer, and the label says the days of the period.
function overviewMove(event) {
  if (drag === null) {
    showGrip(gripAt(event));
    return;
  }
  const day = overviewDay(event);
  if (day === null) {
    return;
  }
  const range = brushedRange(drag, day, Number(ui.overviewPlot.dataset.first), Number(ui.overviewPlot.dataset.last));
  placeFrame(range);
  setText(
    ui.overviewLabel,
    t("view.overview_range", { from: dateText(isoDate(range.from), state.language), to: dateText(isoDate(range.to), state.language) }),
  );
}

function overviewUp(event) {
  if (drag === null) {
    return;
  }
  const { grip, start, range: before } = drag;
  const day = overviewDay(event) ?? start;
  const range =
    grip === null
      ? draggedRange(start, day)
      : brushedRange(drag, day, Number(ui.overviewPlot.dataset.first), Number(ui.overviewPlot.dataset.last));
  endDrag();
  if (range === null || (range.from === before.from && range.to === before.to)) {
    // A click, or the same period: the frame and the label go back.
    redrawOverview();
    return;
  }
  state.period = "custom";
  state.range = { from: isoDate(range.from), to: isoDate(range.to) };
  ui.rangeFrom.value = state.range.from;
  ui.rangeTo.value = state.range.to;
  state.cursor = null;
  rememberItems(true);
  requestSeries();
}

function endDrag() {
  if (drag !== null && ui.overviewPlot.hasPointerCapture?.(drag.pointer)) {
    ui.overviewPlot.releasePointerCapture(drag.pointer);
  }
  drag = null;
  delete ui.overviewPlot.dataset.drag;
  showGrip(null);
}

// Esc, or a pointer that the browser took: the period stays.
function cancelDrag() {
  endDrag();
  redrawOverview();
}

function redrawOverview() {
  render();
  renderOverview(true);
}

// --- The rest of the page -------------------------------------------------

function replaceLines(container, messages) {
  container.replaceChildren(...messages.map((message) => element("p", "", describe(message))));
}

function renderConnection() {
  const connection = connectionMessages(state.connectionKey);
  const lines = connection.status.map(describe);
  if (state.quitKey !== null) {
    lines.push(t(state.quitKey));
  }
  setText(ui.connection, lines.join(" "));
  ui.connectionProblem.hidden = connection.problem.length === 0;
  replaceLines(ui.connectionProblem, connection.problem);
}

function renderBar() {
  const bar = viewBar({
    stopped: state.stopped,
    view: state.view === null ? null : { name: state.view.name, version: state.view.version },
    opening: state.opening,
    stop: state.stop,
    choice: choice(),
  });
  ui.nextLine.className = `next-line view-next k-${bar.kind}`;
  setText(ui.nextLabel, describe(bar.label));
  setText(ui.nextText, describe(bar.text));
}

function outputOptions(start) {
  const options = [];
  if (selectedOutput() === "") {
    const placeholder = element(
      "option",
      "",
      start.latest === null ? t("view.output.none") : t("view.output.latest", { name: start.latest.name }),
    );
    placeholder.value = "";
    placeholder.disabled = true;
    placeholder.selected = true;
    options.push(placeholder);
  }
  if (state.runOutput !== null) {
    const option = element("option", "", t("view.output.run", { name: state.runOutput.name }));
    option.value = "run";
    options.push(option);
  }
  for (const output of state.earlier?.outputs ?? []) {
    const option = element("option", "", output.name);
    option.value = `earlier-${output.index}`;
    options.push(option);
  }
  if (state.chosen !== null) {
    const option = element("option", "", t("view.output.chosen", { name: state.chosen.name }));
    option.value = "chosen";
    options.push(option);
  }
  return options;
}

// The output that the field shows: the one that opens, else the one shown
// or that could not be opened.
function fieldTarget() {
  if (state.opening !== null) {
    return state.openingTarget;
  }
  return state.view !== null || state.stop !== null ? state.target : null;
}

function selectedOutput() {
  const target = fieldTarget();
  if (target === null || target === undefined) {
    return "";
  }
  if (target.output === "run") {
    return "run";
  }
  if (target.output === "earlier") {
    return `earlier-${target.index}`;
  }
  return "chosen";
}

function renderFilters(live) {
  const start = choice();
  const viewing = live && state.view !== null && state.opening === null;
  const before = live && state.view === null && state.opening === null && state.stop === null;
  ui.outputFilter.classList.toggle("current", before);
  ui.outputBadge.hidden = !before;
  const options = outputOptions(start);
  const signature = JSON.stringify(options.map((option) => [option.value, option.textContent]));
  if (ui.outputSelect.dataset.options !== signature) {
    ui.outputSelect.replaceChildren(...options);
    ui.outputSelect.dataset.options = signature;
  }
  const selected = selectedOutput();
  if (ui.outputSelect.value !== selected && [...ui.outputSelect.options].some((option) => option.value === selected)) {
    ui.outputSelect.value = selected;
  }
  ui.outputSelect.disabled = !live || state.choosing || options.every((option) => option.disabled);
  ui.openLatest.hidden = !before || start.kind !== "remembered";
  setText(ui.openLatest, t("view.output.open_remembered"));
  ui.openLatest.disabled = !live;
  ui.chooseOutput.disabled = !live || state.choosing;
  const answer = state.answer;
  for (const button of ui.periodButtons) {
    button.disabled = !viewing;
    button.setAttribute("aria-pressed", String(viewing && state.period === button.dataset.period));
  }
  ui.rangeRow.hidden = !viewing || state.period !== "custom";
  if (viewing) {
    for (const field of [ui.rangeFrom, ui.rangeTo]) {
      field.min = state.view.first_day ?? "";
      field.max = state.view.last_day ?? "";
    }
  }
  ui.periodBack.disabled = !viewing || shiftedRange(answer?.start, answer?.end, -1, state.view?.first_day, state.view?.last_day) === null;
  ui.periodNext.disabled = !viewing || shiftedRange(answer?.start, answer?.end, 1, state.view?.first_day, state.view?.last_day) === null;
  for (const button of ui.grainButtons) {
    button.disabled = !viewing;
    button.setAttribute("aria-pressed", String(viewing && state.grain === button.dataset.grain));
  }
  const auto = viewing ? autoGrainOf(answer?.start, answer?.end) : null;
  setText(ui.grainAutoNow, auto === null ? "" : t("view.grain.auto_now", { grain: t(grainKey(auto)) }));
  const types = state.view?.types ?? [];
  ui.typesButton.disabled = !viewing || !types.length;
  ui.typesButton.setAttribute("aria-expanded", String(viewing && state.typesOpen));
  setText(ui.typesSummary, viewing ? describe(typesSummary(state.counted, types)) : t("view.types.none_yet"));
  ui.typesPop.hidden = !viewing || !state.typesOpen;
  if (!ui.typesPop.hidden) {
    renderTypes(types);
  }
  ui.filtersHint.hidden = !state.hints || !viewing;
}

function renderTypes(types) {
  const signature = JSON.stringify([types, state.counted, state.language]);
  if (ui.typesList.dataset.signature === signature) {
    return;
  }
  const focused = document.activeElement?.dataset?.type ?? null;
  ui.typesList.replaceChildren(
    ...types.map((entry) => {
      const label = element("label");
      const box = element("input");
      box.type = "checkbox";
      box.checked = state.counted.includes(entry.name);
      box.dataset.type = entry.name;
      // The last type counted stays.
      box.disabled = box.checked && state.counted.length === 1;
      label.append(box, describe(typeMessage(entry.name)), element("span", "type-count", formatNumber(entry.count)));
      return label;
    }),
  );
  ui.typesList.dataset.signature = signature;
  if (focused !== null) {
    [...ui.typesList.querySelectorAll("input")].find((box) => box.dataset.type === focused)?.focus();
  }
}

function coverageBar(months, firstMonth, lastMonth) {
  const svg = svgElement("svg", { class: "coverage", viewBox: "0 0 150 12", preserveAspectRatio: "none", "aria-hidden": "true", focusable: "false" });
  svg.append(svgElement("rect", { class: "coverage-line", x: 0, y: 5.5, width: 150, height: 1 }));
  const span = Math.max(1, lastMonth - firstMonth + 1);
  for (const [first, length] of coverageRuns(months, firstMonth)) {
    svg.append(
      svgElement("rect", {
        class: "coverage-run",
        x: ((first / span) * 150).toFixed(1),
        y: 3,
        width: Math.max(1, (length / span) * 150).toFixed(1),
        height: 6,
        rx: 1.5,
      }),
    );
  }
  return svg;
}

function renderShelf(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const open = state.shelf === "open";
  ui.body.classList.toggle("folded", !open);
  ui.shelf.hidden = !open;
  ui.rail.hidden = open;
  const chosen = state.view === null ? [] : state.items;
  setText(ui.shelfCount, t("view.shelf.count", { n: chosen.length, max: MAX_PANELS }));
  setText(ui.railCount, t("view.shelf.count", { n: chosen.length, max: MAX_PANELS }));
  ui.shelfFold.setAttribute("aria-expanded", "true");
  ui.shelfOpen.setAttribute("aria-expanded", "false");
  ui.coverageButton.setAttribute("aria-expanded", String(state.coverageOpen));
  ui.coverageText.hidden = !state.coverageOpen;
  ui.shelfSearch.disabled = !viewing;
  ui.shelfHint.hidden = !state.hints || !viewing;
  if (viewing && state.view.first_day && state.view.last_day) {
    setText(ui.shelfHint, t("view.hint.shelf", { from: state.view.first_day.slice(0, 4), to: state.view.last_day.slice(0, 4) }));
  }
  const items = state.view?.items ?? [];
  const signature = JSON.stringify([viewing, items.length, chosen, state.coverageSeq, state.query, state.folded, state.language, state.view?.view ?? null]);
  if (ui.shelfGroups.dataset.signature === signature) {
    return;
  }
  const focused = document.activeElement;
  const focusedItem = ui.shelfGroups.contains(focused) ? (focused.dataset.item ?? null) : null;
  const focusedGroup = ui.shelfGroups.contains(focused) ? (focused.dataset.group ?? null) : null;
  const firstMonth = state.view?.first_day ? monthIndex(state.view.first_day) : 0;
  const lastMonth = state.view?.last_day ? monthIndex(state.view.last_day) : 0;
  const searching = state.query.trim() !== "";
  const nodes = [];
  for (const group of items.length ? shelfGroups(items, chosen, state.coverage, state.query, itemName, searching ? {} : state.folded) : []) {
    if (searching && !group.rows.length) {
      continue;
    }
    const button = element("button", "group-button");
    button.type = "button";
    button.dataset.group = group.group;
    button.setAttribute("aria-expanded", String(group.open));
    button.disabled = searching;
    button.append(icon("fold"), t(groupKey(group.group)));
    if (group.chosen) {
      button.append(element("span", "group-count", t("view.shelf.chosen", { n: group.chosen })));
    }
    nodes.push(button);
    if (!group.open) {
      continue;
    }
    for (const row of group.rows) {
      const label = element("label", `shelf-item${row.chosen ? " chosen" : ""}${row.disabled || !viewing ? " disabled" : ""}`);
      const box = element("input");
      box.type = "checkbox";
      box.checked = row.chosen;
      box.disabled = row.disabled || !viewing;
      box.dataset.item = row.key;
      const name = element("span", "item-name", itemName(row.key));
      name.append(element("span", "item-unit", t(unitKey(row.key))));
      label.append(box, name, viewing ? coverageBar(row.months, firstMonth, lastMonth) : element("span"));
      nodes.push(label);
    }
  }
  if (!items.length) {
    for (const group of GROUPS) {
      const button = element("button", "group-button");
      button.type = "button";
      button.disabled = true;
      button.append(icon("fold"), t(groupKey(group)));
      nodes.push(button);
    }
  }
  ui.shelfGroups.replaceChildren(...nodes);
  ui.shelfGroups.dataset.signature = signature;
  const again = focusedItem !== null
    ? ui.shelfGroups.querySelector(`input[data-item="${focusedItem}"]`)
    : focusedGroup !== null
      ? ui.shelfGroups.querySelector(`button[data-group="${focusedGroup}"]`)
      : null;
  again?.focus();
}

function renderPicker(viewing) {
  const folded = state.shelf === "closed";
  ui.addWrap.hidden = !folded || !viewing;
  ui.addItems.disabled = !viewing || state.items.length >= MAX_PANELS;
  ui.addItems.setAttribute("aria-expanded", String(state.pickerOpen));
  ui.picker.hidden = !state.pickerOpen || ui.addWrap.hidden;
  if (ui.picker.hidden) {
    return;
  }
  setText(ui.pickerHeading, t("view.add.heading", { n: state.items.length, max: MAX_PANELS }));
  ui.pickerFull.hidden = state.items.length < MAX_PANELS;
  const signature = JSON.stringify([state.items, state.language]);
  if (ui.pickerGroups.dataset.signature === signature) {
    return;
  }
  const focusedItem = ui.pickerGroups.contains(document.activeElement) ? document.activeElement.dataset.item : null;
  const nodes = [];
  for (const group of shelfGroups(state.view.items, state.items, state.coverage, "", itemName)) {
    nodes.push(element("span", "picker-group", t(groupKey(group.group))));
    for (const row of group.rows) {
      const label = element("label");
      const box = element("input");
      box.type = "checkbox";
      box.checked = row.chosen;
      box.disabled = row.disabled;
      box.dataset.item = row.key;
      label.append(box, itemName(row.key), element("span", "item-unit", t(unitKey(row.key))));
      nodes.push(label);
    }
  }
  ui.pickerGroups.replaceChildren(...nodes);
  ui.pickerGroups.dataset.signature = signature;
  if (focusedItem) {
    ui.pickerGroups.querySelector(`input[data-item="${focusedItem}"]`)?.focus();
  }
}

function renderStop(container, heading, lines, code, box) {
  if (heading !== null) {
    setText(heading, describe(box.heading));
  }
  replaceLines(lines, box.lines);
  setText(code, describe(box.code));
}

function renderStage(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const start = choice();
  ui.partNote.hidden = !viewing || state.view.partial !== true;
  setText(ui.partText, t("view.partial.text", { table: t("result.caption") }));
  // Before an output is open, while one opens, and with no item.
  let empty = null;
  if (state.stopped || !state.connected) {
    const heading = state.stopped ? "status.stopped" : state.connectionKey === null ? "view.empty.waiting" : state.connectionKey;
    empty = { heading: t(heading), text: "", buttons: false };
  } else if (state.opening !== null) {
    empty = { heading: t("view.empty.opening"), text: state.opening, buttons: false };
  } else if (state.view === null && state.stop === null) {
    if (start.kind === "remembered") {
      empty = {
        heading: t("view.empty.remembered_heading"),
        text: t("view.empty.remembered_text", {
          name: start.latest.name,
          items: describe(itemListMessage(rememberedKeys(state.settings), itemName, state.language)),
        }),
        buttons: true,
        primary: t("view.output.open_remembered"),
        action: "latest",
      };
    } else if (start.kind === "latest") {
      empty = {
        heading: t("view.empty.first_heading"),
        text: t("view.empty.latest_text", { name: start.latest.name, items: firstItems() }),
        buttons: true,
        primary: t("view.output.open_latest"),
        action: "latest",
      };
    } else {
      empty = {
        heading: t("view.empty.first_heading"),
        text: t("view.empty.first_text", { other: t("target.other"), items: firstItems() }),
        buttons: true,
        primary: t("view.to_normalize"),
        action: "normalize",
      };
    }
  } else if (viewing && !state.items.length) {
    empty = {
      heading: t("view.empty.items_heading"),
      text: t(state.shelf === "open" ? "view.empty.items_shelf" : "view.empty.items_add", { button: t("view.add.button") }),
      buttons: false,
    };
  }
  ui.emptyBox.hidden = empty === null;
  if (empty !== null) {
    setText(ui.emptyHeading, empty.heading);
    setText(ui.emptyText, empty.text);
    ui.emptyText.hidden = empty.text === "";
    ui.emptyButtons.hidden = !empty.buttons;
    if (empty.buttons) {
      setText(ui.emptyPrimary, empty.primary);
      ui.emptyPrimary.dataset.action = empty.action;
      ui.emptyPrimary.disabled = !live;
      ui.emptyOther.disabled = !live || state.choosing;
    }
  }
  ui.stopBox.hidden = state.stop === null || state.opening !== null;
  if (!ui.stopBox.hidden) {
    const box = stopBox(state.stop.code, state.stop.detail, state.productVersion);
    renderStop(ui.stopBox, ui.stopHeading, ui.stopLines, ui.stopCode, box);
    ui.stopNormalize.hidden = !box.normalize;
    ui.stopNormalize.disabled = !live;
    ui.stopOther.disabled = !live || state.choosing;
  }
  ui.caveat.hidden = !viewing;
  renderPicker(viewing);
  setText(ui.loading, state.loading && viewing ? t("view.loading") : "");
  ui.align.disabled = !viewing;
  ui.align.checked = state.align;
  ui.seriesStop.hidden = !viewing || state.seriesStop === null;
  if (!ui.seriesStop.hidden) {
    renderStop(ui.seriesStop, null, ui.seriesStopLines, ui.seriesStopCode, stopBox(state.seriesStop.code, state.seriesStop.detail, state.productVersion));
  }
  const showPanels = viewing && state.items.length > 0 && state.answer !== null && state.seriesStop === null;
  // Graphs only, while there are panels; a stop shows the whole page again,
  // and the focus goes from the button that hides to what shows instead.
  let refocus = false;
  if (state.full && !showPanels) {
    state.full = false;
    refocus = document.activeElement === ui.fullBack;
    leaveScreen();
  }
  ui.app.classList.toggle("full", state.full);
  if (refocus) {
    [ui.seriesStopHeading, ui.stopHeading, ui.emptyHeading].find((heading) => heading.closest("[hidden]") === null)?.focus();
  }
  ui.fullBar.hidden = !state.full;
  ui.fullEnter.disabled = !showPanels;
  if (state.full) {
    setText(
      ui.fullText,
      t("view.full.text", {
        name: state.view.name,
        from: dateText(state.answer.start, state.language),
        to: dateText(state.answer.end, state.language),
        types: ui.typesSummary.textContent,
      }),
    );
  }
  ui.stack.hidden = !showPanels;
  ui.stack.classList.toggle("waiting", state.loading);
  ui.overview.hidden = !showPanels || state.overview === null;
  // While a drag moves the frame, the label says the days of its period.
  if (state.overview !== null && drag === null) {
    setText(ui.overviewLabel, t("view.overview", { name: itemName(state.overview.key) }));
  }
  if (showPanels) {
    renderPanels();
    if (!ui.overview.hidden) {
      renderOverview();
    }
  } else {
    drawn = [];
    drawnSignature = null;
    overviewSignature = null;
  }
}

// The items of the first time, by their names.
function firstItems() {
  return describe(itemListMessage(FIRST_KEYS, itemName, state.language));
}

function renderFooter(live) {
  ui.version.textContent = state.productVersion === null ? "" : t("app.version", { version: state.productVersion });
  for (const option of ui.language.options) {
    option.textContent = translate(state.catalogs, option.value, "language.name");
  }
  ui.language.value = state.language;
  for (const choiceButton of ui.themeChoices) {
    choiceButton.checked = choiceButton.value === state.theme;
    choiceButton.disabled = !live;
  }
  setText(ui.themeNow, t("theme.now", { mode: t(themeNowKey(darkScheme.matches)) }));
  ui.hintsToggle.checked = state.hints;
  ui.hintsToggle.disabled = !live;
  ui.toNormalize.disabled = state.stopped;
  ui.quit.disabled = !live;
  ui.quitConfirm.hidden = !state.quitAsked;
  ui.quit.setAttribute("aria-expanded", String(state.quitAsked));
  ui.quitYes.disabled = !live;
  const notice = state.settingsNotice;
  setText(ui.settingsStatus, notice === null ? "" : settingsMessages(notice.code, notice.writing).map(describe).join(" "));
}

function renderHelp() {
  ui.helpPanel.hidden = !state.helpOpen;
  ui.helpButton.setAttribute("aria-expanded", String(state.helpOpen));
  document.body.classList.toggle("help-open", state.helpOpen);
}

function render() {
  document.documentElement.lang = state.language;
  for (const node of document.querySelectorAll("[data-i18n]")) {
    setText(node, t(node.dataset.i18n));
  }
  for (const node of document.querySelectorAll("[data-i18n-label]")) {
    node.setAttribute("aria-label", t(node.dataset.i18nLabel));
  }
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) {
    node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder));
  }
  document.title = t("view.title");
  const live = state.connected && !state.stopped && !state.quitting;
  renderConnection();
  renderBar();
  renderFilters(live);
  renderShelf(live);
  renderLayouts(live);
  renderStage(live);
  renderFooter(live);
  renderHelp();
}

// --- Help, quitting, and the controls -------------------------------------

function openHelp(part = null) {
  state.helpOpen = true;
  render();
  const target = part === null ? ui.helpHeading : ui.helpParts[part] ?? ui.helpHeading;
  target.scrollIntoView({ block: "start" });
  target.focus();
}

function closeHelp() {
  state.helpOpen = false;
  render();
  (state.full ? ui.fullBack : ui.helpButton).focus();
}

// Graphs only (the Human maintainer, 2026-10-27): the panels and the overview
// fill the screen where the browser allows it, and the window where it does
// not.
function enterFull() {
  state.full = true;
  state.helpOpen = false;
  state.typesOpen = false;
  state.pickerOpen = false;
  render();
  ui.fullBack.focus();
  try {
    Promise.resolve(document.documentElement.requestFullscreen?.())
      .then(() => {
        // Back came before the browser's full screen.
        if (!state.full) {
          leaveScreen();
        }
      })
      .catch(() => {});
  } catch {
    // The graphs fill the window.
  }
}

function leaveFull() {
  state.full = false;
  // A drag of the overview ends where it was: in the browser's full screen,
  // the browser takes the first Esc, before the page.
  const dragging = drag !== null;
  if (dragging) {
    endDrag();
  }
  render();
  if (dragging) {
    renderOverview(true);
  }
  leaveScreen();
  ui.fullEnter.focus();
}

function leaveScreen() {
  if (document.fullscreenElement) {
    Promise.resolve(document.exitFullscreen?.()).catch(() => {});
  }
}

function askQuit() {
  state.quitAsked = true;
  state.quitKey = null;
  render();
  ui.quitNo.focus();
}

function keepApp() {
  state.quitAsked = false;
  render();
  ui.quit.focus();
}

async function quit() {
  state.quitAsked = false;
  state.quitting = true;
  state.connectionKey = "status.quitting";
  render();
  try {
    await quitAfterWriting(rememberNow, () => callApi("/api/shutdown"));
    markStopped();
    quitChannel?.postMessage({ stopped: true });
  } catch (error) {
    if (!connectionFailure(error)) {
      state.connectionKey = "status.connected";
      // A normalization of the other tab keeps the app running.
      state.quitKey = error.code === "RUN_ACTIVE" ? "view.quit_blocked" : "error.unknown";
    }
  } finally {
    state.quitting = false;
  }
  render();
}

// The notes of a panel open and close by themselves, without drawing the
// panels again; one is open at a time.
function toggleNotes(key, open = state.notesOpen !== key) {
  state.notesOpen = open ? key : null;
  for (const pop of ui.panels.querySelectorAll(".notes-pop")) {
    pop.hidden = pop.dataset.key !== state.notesOpen;
  }
  for (const button of ui.panels.querySelectorAll('button[data-action="notes"]')) {
    button.setAttribute("aria-expanded", String(button.dataset.key === state.notesOpen));
  }
}

function panelAction(event) {
  const button = event.target.closest("button[data-action]");
  if (button === null || !ui.panels.contains(button)) {
    return;
  }
  const key = button.dataset.key;
  switch (button.dataset.action) {
    case "table":
      if (state.tables.has(key)) {
        state.tables.delete(key);
      } else {
        state.tables.add(key);
      }
      break;
    case "big":
      state.big = key;
      state.notesOpen = null;
      for (const other of [...state.tables]) {
        if (other !== key) {
          state.tables.delete(other);
        }
      }
      render();
      requestOverview();
      ui.panels.querySelector(`button[data-action="unbig"][data-key="${key}"]`)?.focus();
      return;
    case "unbig":
      state.big = null;
      state.notesOpen = null;
      render();
      requestOverview();
      ui.panels.querySelector(`button[data-action="big"][data-key="${key}"]`)?.focus();
      return;
    case "up":
    case "down":
      changeItems(movedItems(state.items, key, button.dataset.action === "up" ? -1 : 1), false);
      return;
    case "remove":
      changeItems(state.items.filter((other) => other !== key), false);
      if (!state.items.length) {
        (state.shelf === "open" ? ui.shelfSearch : ui.addItems).focus();
      }
      return;
    case "notes":
      toggleNotes(key);
      return;
    case "help":
      openHelp(key);
      return;
    default:
      return;
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
  ui.language.addEventListener("change", () => changeLanguage(ui.language.value));
  ui.toNormalize.addEventListener("click", toNormalize);
  ui.stopNormalize.addEventListener("click", toNormalize);
  ui.hintsToggle.addEventListener("change", changeHints);
  for (const choiceButton of ui.themeChoices) {
    choiceButton.addEventListener("change", changeTheme);
  }
  darkScheme.addEventListener("change", render);
  themeChannel?.addEventListener("message", themeHeard);
  quitChannel?.addEventListener("message", quitHeard);
  ui.helpButton.addEventListener("click", () => (state.helpOpen ? closeHelp() : openHelp()));
  ui.helpClose.addEventListener("click", closeHelp);
  ui.helpPanel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeHelp();
    }
  });
  ui.quit.addEventListener("click", askQuit);
  ui.quitYes.addEventListener("click", quit);
  ui.quitNo.addEventListener("click", keepApp);
  ui.quitConfirm.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      keepApp();
    }
  });
  ui.outputSelect.addEventListener("change", outputChosen);
  ui.openLatest.addEventListener("click", openLatest);
  ui.chooseOutput.addEventListener("click", () => chooseWithDialog(ui.chooseOutput));
  ui.emptyOther.addEventListener("click", () => chooseWithDialog(ui.emptyOther));
  ui.stopOther.addEventListener("click", () => chooseWithDialog(ui.stopOther));
  ui.emptyPrimary.addEventListener("click", () => (ui.emptyPrimary.dataset.action === "normalize" ? toNormalize() : openLatest()));
  for (const button of ui.periodButtons) {
    button.addEventListener("click", () => setPeriod(button.dataset.period));
  }
  ui.layoutCards.addEventListener("click", (event) => {
    const card = event.target.closest("[data-layout]");
    if (card !== null) {
      chooseLayout(card.dataset.layout);
    }
  });
  ui.railLayoutCards.addEventListener("click", (event) => {
    const card = event.target.closest("[data-layout]");
    if (card !== null) {
      chooseLayout(card.dataset.layout);
      openRailLayouts(false);
    }
  });
  ui.layoutSaveAs.addEventListener("click", () => openLayoutSave(!state.layoutSaving));
  ui.layoutSaveButton.addEventListener("click", saveLayout);
  ui.layoutSaveCancel.addEventListener("click", () => openLayoutSave(false));
  ui.layoutName.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      saveLayout();
    } else if (event.key === "Escape") {
      event.preventDefault();
      openLayoutSave(false);
    }
  });
  ui.layoutOverwrite.addEventListener("click", overwriteLayout);
  ui.layoutsManage.addEventListener("click", () => openLayouts(!state.layoutsOpen));
  ui.layoutsPopClose.addEventListener("click", () => openLayouts(false));
  ui.layoutsPopBody.addEventListener("click", layoutsAction);
  ui.layoutsPopBody.addEventListener("pointerdown", layoutGripDown);
  ui.layoutsPopBody.addEventListener("pointermove", layoutGripMove);
  ui.layoutsPopBody.addEventListener("pointerup", layoutGripUp);
  ui.layoutsPopBody.addEventListener("pointercancel", cancelLayoutDrag);
  ui.layoutsPopBody.addEventListener("lostpointercapture", cancelLayoutDrag);
  ui.layoutsPop.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      // Escape puts a dragged row back first, and then closes the window.
      if (layoutDrag !== null) {
        cancelLayoutDrag();
      } else {
        openLayouts(false);
      }
    } else if (event.key === "Enter" && event.target.matches("input")) {
      event.preventDefault();
      ui.layoutsPopBody.querySelector('[data-op="rename-save"]')?.click();
    } else if ((event.key === "ArrowUp" || event.key === "ArrowDown") && event.target.matches('button[data-op="grip"]') && layoutDrag === null) {
      event.preventDefault();
      changeLayouts({ op: "move", id: event.target.dataset.id, direction: event.key === "ArrowUp" ? "up" : "down" });
    }
  });
  ui.railLayouts.addEventListener("click", () => openRailLayouts(!state.railLayoutsOpen));
  ui.railLayoutsClose.addEventListener("click", () => openRailLayouts(false));
  ui.railLayoutsPop.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      openRailLayouts(false);
    }
  });
  window.addEventListener("pagehide", rememberOnHide);
  ui.periodBack.addEventListener("click", () => shiftPeriod(-1));
  ui.periodNext.addEventListener("click", () => shiftPeriod(1));
  ui.rangeFrom.addEventListener("change", rangeTyped);
  ui.rangeTo.addEventListener("change", rangeTyped);
  for (const button of ui.grainButtons) {
    button.addEventListener("click", () => setGrain(button.dataset.grain));
  }
  ui.typesButton.addEventListener("click", () => {
    state.typesOpen = !state.typesOpen;
    render();
    if (state.typesOpen) {
      ui.typesList.querySelector("input:not(:disabled)")?.focus();
    }
  });
  ui.typesClose.addEventListener("click", () => {
    state.typesOpen = false;
    render();
    ui.typesButton.focus();
  });
  ui.typesPop.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      state.typesOpen = false;
      render();
      ui.typesButton.focus();
    }
  });
  ui.typesList.addEventListener("change", (event) => {
    if (event.target.dataset.type !== undefined) {
      changeTypes(event.target.dataset.type);
    }
  });
  ui.coverageButton.addEventListener("click", () => {
    state.coverageOpen = !state.coverageOpen;
    render();
  });
  ui.shelfFold.addEventListener("click", () => {
    state.shelf = "closed";
    state.coverageOpen = false;
    rememberItems(true);
    render();
    ui.shelfOpen.focus();
  });
  ui.shelfOpen.addEventListener("click", () => {
    state.shelf = "open";
    state.pickerOpen = false;
    rememberItems(true);
    render();
    ui.shelfFold.focus();
  });
  ui.shelfSearch.addEventListener("input", () => {
    state.query = ui.shelfSearch.value;
    render();
  });
  ui.shelfGroups.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-group]");
    if (button !== null) {
      state.folded = { ...state.folded, [button.dataset.group]: button.getAttribute("aria-expanded") === "true" };
      render();
    }
  });
  for (const list of [ui.shelfGroups, ui.pickerGroups]) {
    list.addEventListener("change", (event) => {
      const key = event.target.dataset.item;
      if (key !== undefined) {
        changeItems(toggledItems(state.items, key));
      }
    });
  }
  ui.addItems.addEventListener("click", () => {
    state.pickerOpen = !state.pickerOpen;
    render();
    if (state.pickerOpen) {
      ui.pickerGroups.querySelector("input:not(:disabled)")?.focus();
    }
  });
  ui.pickerClose.addEventListener("click", () => {
    state.pickerOpen = false;
    render();
    ui.addItems.focus();
  });
  ui.picker.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      state.pickerOpen = false;
      render();
      ui.addItems.focus();
    }
  });
  ui.align.addEventListener("change", () => {
    state.align = ui.align.checked;
    render();
  });
  ui.panels.addEventListener("click", panelAction);
  ui.panels.addEventListener("keydown", (event) => {
    if (event.target.classList?.contains("plot")) {
      plotKey(event);
    } else if (event.key === "Escape" && state.notesOpen !== null) {
      event.preventDefault();
      const key = state.notesOpen;
      toggleNotes(key, false);
      ui.panels.querySelector(`button[data-action="notes"][data-key="${key}"]`)?.focus();
    }
  });
  ui.panels.addEventListener("pointermove", (event) => {
    if (event.target.closest?.(".plot")) {
      plotPointer(event);
    }
  });
  ui.overviewPlot.addEventListener("pointerdown", overviewDown);
  ui.overviewPlot.addEventListener("pointermove", overviewMove);
  ui.overviewPlot.addEventListener("pointerup", overviewUp);
  ui.overviewPlot.addEventListener("pointercancel", () => {
    if (drag !== null) {
      cancelDrag();
    }
  });
  ui.overviewPlot.addEventListener("pointerleave", () => {
    if (drag === null) {
      showGrip(null);
    }
  });
  ui.fullEnter.addEventListener("click", enterFull);
  ui.fullBack.addEventListener("click", leaveFull);
  // The browser leaves its full screen by Esc or by its own controls.
  document.addEventListener("fullscreenchange", () => {
    if (document.fullscreenElement === null && state.full) {
      leaveFull();
    }
  });
  // Esc cancels a drag on the overview, or leaves graphs only; the parts of
  // the page that close by Esc take it first.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || event.defaultPrevented) {
      return;
    }
    if (drag !== null) {
      event.preventDefault();
      cancelDrag();
    } else if (state.full) {
      leaveFull();
    }
  });
  // The panels follow the window, and each chart its plot, whose head can
  // take one line more or less.
  if (typeof ResizeObserver === "function") {
    new ResizeObserver(scheduleRedraw).observe(ui.panels);
    plotWatcher = new ResizeObserver(scheduleRedraw);
  } else {
    window.addEventListener("resize", scheduleRedraw);
  }
  window.addEventListener("hashchange", addressChanged);
  // A normalization of the other tab adds an output: the list follows when
  // this tab is shown again.
  document.addEventListener("visibilitychange", async () => {
    if (document.visibilityState === "visible" && state.connected && !state.stopped) {
      await loadOutputs();
      render();
    }
  });
}

async function start() {
  // The output that the normalization page asked for, read before the key,
  // whose reading clears the address.
  const opening = addressValue("output");
  state.launchKey = readLaunchKey();
  window.name = VIEW_TAB;
  state.theme = initialTheme();
  const catalogs = await Promise.all(LANGUAGES.map(loadCatalog));
  state.catalogs = Object.fromEntries(LANGUAGES.map((language, index) => [language, catalogs[index]]));
  state.language = chooseLanguage(LANGUAGES, readStorage(LANGUAGE_STORAGE), navigator.languages ?? [navigator.language]);
  connect();
  render();
  try {
    const status = await callApi("/api/status");
    state.productVersion = typeof status.product_version === "string" ? status.product_version : null;
    state.settings = status.settings !== null && typeof status.settings === "object" ? status.settings : {};
    state.hints = viewHintsShown(state.settings);
    state.shelf = shelfOpen(state.settings) ? "open" : "closed";
    // The layouts and the view as the settings remember them (stage K2 of
    // v2.2.0); an output that opens takes the period and the types where it
    // has them.
    takeLayouts(state.settings.view_layouts, state.settings.view_layouts_hidden, state.settings.view_layout);
    const period = periodToOpen(state.settings.view_period, null, null);
    if (period !== null) {
      state.period = period.choice;
      state.range = period.range;
    }
    state.grain = grainToOpen(state.settings.view_grain);
    state.wantedTypes = Array.isArray(state.settings.view_types) ? [...state.settings.view_types] : null;
    const notice = settingsMessages(state.settings.notice).length ? state.settings.notice : null;
    state.settingsNotice = notice === null ? null : { code: notice, writing: false };
    // The colors that the settings remember win over this tab's (stage G3a).
    applyTheme(state.settings.theme === "light" || state.settings.theme === "dark" ? state.settings.theme : "auto");
    state.connected = true;
    state.connectionKey = "status.connected";
    startHeartbeat();
    await loadOutputs();
    render();
    if (opening === "run" && state.runOutput !== null) {
      openOutput(targetOf(state.runOutput));
    }
  } catch (error) {
    connectionFailure(error);
  }
  render();
}

start();
