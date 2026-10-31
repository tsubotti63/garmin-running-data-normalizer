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
  COMPARE_MODES,
  COMPARE_BYS,
  COMPARE_WEEKS,
  FIRST_COMPARE_WEEKS,
  MAX_COMPARE_RACES,
  RANGE_GRAIN,
  compareByFor,
  compareByToOpen,
  compareGrainFor,
  compareGrainsFor,
  compareRaces,
  firstCompareRaces,
  raceChip,
  raceData,
  raceRange,
  raceSlotName,
  raceTicks,
  raceValueMessage,
  racesKept,
  toggledRaces,
  calendarAnswer,
  calendarAt,
  calendarCell,
  calendarDay,
  calendarItem,
  calendarLegend,
  calendarMove,
  calendarPlace,
  calendarReading,
  calendarStep,
  calendarValues,
  calendarWeekdays,
  calendarWeeks,
  calendarZeroDays,
  calendarZeroNote,
  compareAsksAgain,
  compareMonthFor,
  daySlot,
  slotDay,
  FIRST_KEYS,
  MARKS_LOCKED,
  MARKS_NOTICE_KEYS,
  MARK_KINDS,
  MARK_PROBLEM_KEYS,
  MAX_MARKS,
  markDays,
  markDaysProblem,
  marksTaken,
  marksToOpen,
  marksWithin,
  spokenMarks,
  GROUPS,
  MAX_COMPARE_YEARS,
  MAX_PANELS,
  clockOf,
  compareData,
  compareModeFor,
  compareNote,
  compareRange,
  compareReadings,
  compareSeriesChoices,
  compareSlotName,
  compareSpan,
  compareStopBox,
  compareTable,
  compareTicks,
  compareToOpen,
  compareValueGrain,
  compareValueMessage,
  compareYears,
  firstCompareSeries,
  firstCompareYears,
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
  litAfter,
  litKept,
  monthIndex,
  movedItems,
  overviewGrip,
  panelNotes,
  periodMessage,
  periodRequest,
  periodToOpen,
  rangeProblem,
  readout,
  recapColumns,
  recapDays,
  recapDifference,
  recapPartial,
  recapRows,
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
  toggledYears,
  totalItem,
  typeMessage,
  typesRequest,
  typesSummary,
  typesToOpen,
  unitKey,
  valueMessage,
  viewBar,
  viewHintsShown,
  listAfter,
  listColumns,
  listFrom,
  listHead,
  listLimitMessage,
  listOpens,
  listSorted,
  listTitle,
  listValueLine,
  listValueText,
  listWhen,
  sortedListRows,
  countText,
  nearestPoint,
  plotCount,
  plotCut,
  plotItem,
  plotMove,
  plotPairOf,
  plotPairToOpen,
  plotReading,
  plotSortAfter,
  plotWhen,
  sameValues,
  spreadCount,
  spreadEndWords,
  spreadItemOf,
  spreadItemToOpen,
  spreadMove,
  spreadRange,
  spreadReading,
  spreadWide,
  SAVE_ATTRIBUTES,
  SAVE_LEFT_OUT,
  SAVE_LEFT_OUT_VIEWS,
  SAVE_MARKS,
  saveDays,
  saveFileName,
  saveFooter,
  saveFrame,
  saveLines,
  saveNoticeKey,
  saveProblem,
  saveShowable,
  saveViewFileName,
  shoeName,
  shoeWords,
  shoesCount,
  shoesNotes,
  shoesRead,
  shoesTables,
  shoesWhy,
  saveViewFooter,
  saveViewReady,
  saveWindowShows,
  savedAttributes,
  savedPanels,
  yearDrawn,
} from "./view_flow.mjs";
import {
  PLOT_BOTTOM,
  PLOT_LEFT,
  PLOT_RIGHT,
  PLOT_TOP,
  calendarScale,
  extent,
  isoDate,
  labelPlaces,
  markLabels,
  markShapes,
  nearestPeriod,
  overviewShapes,
  panelShapes,
  periodDays,
  periodMiddle,
  plotPlace,
  shapeAt,
  sharedExtents,
  timeScale,
  timeTicks,
  topFirst,
  CHOSEN_RADIUS,
  POINT_RADIUS,
  pointShapes,
  SPREAD_CHOSEN_WIDTH,
  spreadRangeAt,
  spreadShapes,
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
// How near the pointer chooses a point of the chart of two items (stage O1
// of v2.2.0).
const PLOT_REACH = 12;
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

// The words of the kinds of the marks (stage M1 of v2.2.0).
const MARK_KIND_KEYS = {
  race: "view.marks.kind.race",
  injury: "view.marks.kind.injury",
  shoes: "view.marks.kind.shoes",
  other: "view.marks.kind.other",
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
  compareOff: byId("compare-off"),
  compareOffRace: byId("compare-off-race"),
  compareOffCalendar: byId("compare-off-calendar"),
  plotOff: byId("plot-off"),
  spreadOff: byId("spread-off"),
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
  stage: byId("stage"),
  // The menu of the other views (stage O1 of v2.2.0).
  otherViews: byId("other-views"),
  otherMenu: byId("other-views-menu"),
  otherPlot: byId("other-plot"),
  otherSpread: byId("other-spread"),
  // The view by shoes (stage S1 of v2.2.0), and why it cannot be chosen.
  otherShoes: byId("other-shoes"),
  otherShoesWhy: byId("other-shoes-why"),
  fullEnter: byId("full-enter"),
  fullBar: byId("full-bar"),
  fullText: byId("full-text"),
  fullBack: byId("full-back"),
  // The marks (stage M1 of v2.2.0).
  marksShown: byId("marks-shown"),
  marksOpen: byId("marks-open"),
  marksPop: byId("marks-pop"),
  marksPopTitle: byId("marks-pop-title"),
  marksPopClose: byId("marks-pop-close"),
  // The summary of the panels (stage Q1 of v2.2.0).
  recapOpen: byId("recap-open"),
  recapPop: byId("recap-pop"),
  recapTitle: byId("recap-pop-title"),
  recapClose: byId("recap-pop-close"),
  recapDays: byId("recap-days"),
  recapLoading: byId("recap-loading"),
  recapStop: byId("recap-stop"),
  recapStopLines: byId("recap-stop-lines"),
  recapStopCode: byId("recap-stop-code"),
  recapBody: byId("recap-body"),
  recapDifferenceNote: byId("recap-difference-note"),
  recapCut: byId("recap-cut"),
  saveOpen: byId("save-open"),
  savePop: byId("save-pop"),
  saveTitle: byId("save-pop-title"),
  saveClose: byId("save-pop-close"),
  saveAll: byId("save-all"),
  saveAllLabel: byId("save-all-label"),
  saveOne: byId("save-one"),
  savePanel: byId("save-panel"),
  saveTables: byId("save-tables"),
  saveLight: byId("save-light"),
  saveScreen: byId("save-screen"),
  saveMarks: byId("save-marks"),
  saveMarksNone: byId("save-marks-none"),
  saveName: byId("save-name"),
  saveWarn: byId("save-warn"),
  saveProblem: byId("save-problem"),
  saveCancel: byId("save-cancel"),
  saveGo: byId("save-go"),
  saveWhat: byId("save-what"),
  saveScopeField: byId("save-scope-field"),
  saveMarksField: byId("save-marks-field"),
  compareSave: byId("compare-save"),
  plotSave: byId("plot-save"),
  spreadSave: byId("spread-save"),
  // The bar at the bottom of the page, above the windows (stage Q1).
  viewBar: document.querySelector(".view-bar"),
  marksLegend: byId("marks-legend"),
  marksNotice: byId("marks-notice"),
  marksList: byId("marks-list"),
  markFormHeading: byId("mark-form-heading"),
  markDay: byId("mark-day"),
  markEnd: byId("mark-end"),
  markKind: byId("mark-kind"),
  markName: byId("mark-name"),
  markSave: byId("mark-save"),
  markCancel: byId("mark-cancel"),
  markProblem: byId("mark-problem"),
  addWrap: byId("add-wrap"),
  addItems: byId("add-items"),
  picker: byId("picker"),
  pickerHeading: byId("picker-heading"),
  pickerClose: byId("picker-close"),
  pickerFull: byId("picker-full"),
  pickerGroups: byId("picker-groups"),
  loading: byId("loading"),
  align: byId("align-scales"),
  compare: byId("compare"),
  compareBefore: byId("compare-before"),
  compareItem: byId("compare-item"),
  compareMiddle: byId("compare-middle"),
  compareBys: [...document.querySelectorAll("[data-compare-by]")],
  compareRaceNeeded: byId("compare-race-needed"),
  compareAfter: byId("compare-after"),
  compareModes: [...document.querySelectorAll("[data-compare-mode]")],
  compareRowsYear: byId("compare-rows-year"),
  compareRowsRace: byId("compare-rows-race"),
  compareAbout: byId("compare-about"),
  compareAboutText: byId("compare-about-text"),
  compareCalendarAbout: byId("compare-calendar-about"),
  compareCalendarAboutText: byId("compare-calendar-about-text"),
  compareMonth: byId("compare-month"),
  compareMonthField: byId("compare-month-field"),
  compareWeeksField: byId("compare-weeks-field"),
  compareWeeks: byId("compare-weeks"),
  compareSeriesField: byId("compare-series-field"),
  compareSeries: byId("compare-series"),
  compareTable: byId("compare-table"),
  compareTableChart: byId("compare-table-chart"),
  compareTableTable: byId("compare-table-table"),
  compareTableCalendar: byId("compare-table-calendar"),
  compareBack: byId("compare-back"),
  // Two items plotted against each other (stage O1 of v2.2.0).
  plot: byId("plot"),
  plotBefore: byId("plot-before"),
  plotX: byId("plot-x"),
  plotMiddle: byId("plot-middle"),
  plotY: byId("plot-y"),
  plotAfter: byId("plot-after"),
  plotTable: byId("plot-table"),
  plotTableChart: byId("plot-table-chart"),
  plotTableTable: byId("plot-table-table"),
  plotBack: byId("plot-back"),
  plotCount: byId("plot-count"),
  plotLoading: byId("plot-loading"),
  plotStop: byId("plot-stop"),
  plotStopLines: byId("plot-stop-lines"),
  plotStopCode: byId("plot-stop-code"),
  plotBody: byId("plot-body"),
  plotNone: byId("plot-none"),
  plotAnnouncer: byId("plot-announcer"),
  plotCut: byId("plot-cut"),
  // The distribution of one item (stage P1 of v2.2.0).
  spread: byId("spread"),
  spreadBefore: byId("spread-before"),
  spreadItem: byId("spread-item"),
  spreadAfter: byId("spread-after"),
  spreadTable: byId("spread-table"),
  spreadTableChart: byId("spread-table-chart"),
  spreadTableTable: byId("spread-table-table"),
  spreadBack: byId("spread-back"),
  spreadCount: byId("spread-count"),
  spreadLoading: byId("spread-loading"),
  spreadStop: byId("spread-stop"),
  spreadStopLines: byId("spread-stop-lines"),
  spreadStopCode: byId("spread-stop-code"),
  spreadBody: byId("spread-body"),
  spreadNone: byId("spread-none"),
  spreadAnnouncer: byId("spread-announcer"),
  spreadWide: byId("spread-wide"),
  spreadFaster: byId("spread-faster"),
  // The view by shoes (stage S1 of v2.2.0).
  shoes: byId("shoes"),
  shoesTitle: byId("shoes-title"),
  shoesTable: byId("shoes-table"),
  shoesTableChart: byId("shoes-table-chart"),
  shoesTableTable: byId("shoes-table-table"),
  shoesSave: byId("shoes-save"),
  shoesBack: byId("shoes-back"),
  shoesCount: byId("shoes-count"),
  shoesLoading: byId("shoes-loading"),
  shoesStop: byId("shoes-stop"),
  shoesStopLines: byId("shoes-stop-lines"),
  shoesStopCode: byId("shoes-stop-code"),
  shoesStack: byId("shoes-stack"),
  shoesPanels: byId("shoes-panels"),
  shoesAxis: byId("shoes-axis"),
  shoesAnnouncer: byId("shoes-announcer"),
  shoesNone: byId("shoes-none"),
  shoesNotes: byId("shoes-notes"),
  shoesOff: byId("shoes-off"),
  compareYears: byId("compare-years"),
  compareYearsLabel: byId("compare-years-label"),
  compareUpTo: byId("compare-up-to"),
  compareRacesLabel: byId("compare-races-label"),
  compareRaces: byId("compare-races"),
  compareRacesUpTo: byId("compare-races-up-to"),
  compareLoading: byId("compare-loading"),
  compareStop: byId("compare-stop"),
  compareStopHeading: byId("compare-stop-heading"),
  compareStopLines: byId("compare-stop-lines"),
  compareStopCode: byId("compare-stop-code"),
  compareStack: byId("compare-stack"),
  compareLegend: byId("compare-legend"),
  comparePanels: byId("compare-panels"),
  compareAxis: byId("compare-axis"),
  compareAnnouncer: byId("compare-announcer"),
  compareNote: byId("compare-note"),
  seriesStop: byId("series-stop"),
  seriesStopHeading: byId("series-stop-heading"),
  seriesStopLines: byId("series-stop-lines"),
  seriesStopCode: byId("series-stop-code"),
  stack: byId("stack"),
  panels: byId("panels"),
  timeAxis: byId("time-axis"),
  announcer: byId("cross-announcer"),
  listAnnouncer: byId("list-announcer"),
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
  saveStatus: byId("save-status"),
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
  // Comparing one item by year (stage L1 of v2.2.0): its item, the years
  // chosen, the grouping, the series of an item of several lines, whether it
  // shows a table, whether the words of running totals are open, and the
  // place of the cross line; null while the panels show. It is apart from
  // the panels, the period, and the grouping, which it never changes, and it
  // is not remembered.
  compare: null,
  // How it compares and in which month (null: the whole year), which the
  // settings remember.
  compareMode: "rows",
  compareMonth: null,
  // What it compares by (the years, or the race days, with the races chosen
  // in the comparison) and the weeks before a race day, which the settings
  // remember too (stage M2 of v2.2.0).
  compareBy: "year",
  compareWeeks: FIRST_COMPARE_WEEKS,
  // The answers of the last generation of its requests, the count of the
  // generations, whether one is on its way, and a stop.
  compareAnswer: null,
  compareSeq: 0,
  compareLoading: false,
  compareStop: null,
  // Two items plotted against each other (stage O1 of v2.2.0): while the
  // points show, whether their table shows, its order, and the point chosen
  // (its place in the answer); null while the panels show. The pair is
  // remembered apart. The period and the activity types are the page's, so
  // that a change of them while the points show leaves the panels to ask
  // again on the way back (Codex's review of the plan of O1). The answer
  // drawn, the request that it answers, the count of the generations, whether
  // one is on its way, a stop, and the menu of the other views.
  plot: null,
  plotPair: { x: "pace", y: "hr" },
  plotAnswer: null,
  plotAsked: null,
  plotSeq: 0,
  plotLoading: false,
  plotStop: null,
  // The distribution of one item (stage P1 of v2.2.0), as the points: while
  // it shows, whether its table shows and the range chosen; null while the
  // panels show. The item is remembered apart.
  spread: null,
  spreadItem: "dist",
  spreadAnswer: null,
  spreadAsked: null,
  spreadSeq: 0,
  spreadLoading: false,
  spreadStop: null,
  // The view by shoes (stage S1 of v2.2.0), as the distribution: while it
  // shows, whether its tables show and the month of its cross line; null
  // while the panels show. What the server says of the shoes of the output
  // ({count, too_large}), from the answers of opening and of the numbers.
  shoes: null,
  shoesAnswer: null,
  shoesAsked: null,
  shoesSeq: 0,
  shoesLoading: false,
  shoesStop: null,
  shoesAvailable: null,
  // The answers of the numbers and of the shoes both say it again: what the
  // one asked for last said is kept, so that a late answer of data read
  // before does not put back what a newer one said (Codex's review of the
  // diff of S1).
  availableAsks: 0,
  availableFrom: 0,
  panelsStale: false,
  otherOpen: false,
  // The marks of the person (stage M1 of v2.2.0): as the server keeps them,
  // a count that changes with them (which draws the panels again), whether
  // they show, and what to tell of their file; a change that waits for its
  // answer; and the window of the marks, with the mark that it changes (its
  // id), the mark asked to be removed, and what was wrong with a change.
  marks: [],
  marksSeq: 0,
  // Forgetting in the other tab makes a new generation: an answer asked
  // before it is dropped.
  marksGen: 0,
  marksShown: true,
  marksNotice: null,
  marksWaiting: false,
  marksOpen: false,
  // The summary of the panels (stage Q1 of v2.2.0): whether its window is
  // open, its answer and what it asked for, whether an answer is on its way,
  // the generation of its requests, its stop, and whether it showed at the
  // last render.
  recapOpen: false,
  recapAnswer: null,
  recapAsked: null,
  recapLoading: false,
  recapSeq: 0,
  recapStop: null,
  recapShown: false,
  // Saving as an image (stage R1 of v2.2.0): whether its window is open, its
  // choices for this time it opens, why it could not save, and the line
  // after a saving, as what it is said of.
  saveOpen: false,
  // The view whose button opened the window (stage R2 of v2.2.0).
  saveFrom: "panels",
  saveScope: "all",
  savePanel: null,
  saveColors: "light",
  saveMarks: false,
  saveProblem: null,
  saveNotice: null,
  markEditing: null,
  markAsk: null,
  markProblem: null,
  // The list of the activities of one period of a panel (stage M3 of
  // v2.2.0): its item, its period (the index in the answer, and the days),
  // its grouping, the activity types of the answer that drew the panel, its
  // order, and its answer or stop (none while it is on its way); null while
  // none is open. It is apart from the cross line, and not remembered.
  list: null,
  listSeq: 0,
  // The activity types sent for the numbers of the panels, which a list asks
  // for (Codex's review of the plan of M3).
  answerTypes: null,
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
// The key of the panel whose chart names the marks: the top chart that is not
// a low strip, or the top chart (stage M1 of v2.2.0).
let namedKey = null;
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
    // The marks are gone with their file (stage M1 of v2.2.0).
    state.marksGen += 1;
    takeMarks([]);
    state.marksShown = true;
    state.marksNotice = null;
    state.markEditing = null;
    state.markAsk = null;
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
    compare_mode: state.compareMode,
    compare_month: state.compareMonth,
    compare_by: state.compareBy,
    compare_weeks: state.compareWeeks,
    marks_shown: state.marksShown,
    plot: { x: state.plotPair.x, y: state.plotPair.y },
    spread: state.spreadItem,
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
  state.compareSeq += 1;
  // And those of the points, before they could open the output before
  // again (Codex's review of the diff of O1).
  state.plotSeq += 1;
  // And those of a distribution (stage P1).
  state.spreadSeq += 1;
  // And those of the summary (Codex's review of the diff of Q1).
  state.recapSeq += 1;
  state.recapLoading = false;
  const current = state.view === null ? null : state.items;
  // And the answers of the view by shoes, so that none of the output before
  // is drawn for another (stage S1 of v2.2.0, Codex's review of its plan).
  state.shoesSeq += 1;
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
    state.shoesAvailable = answer.shoes ?? null;
    state.availableFrom = ++state.availableAsks;
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
    if (state.compare !== null) {
      if (itemsByKey(answer.items).has(state.compare.key) && compareYears(answer.first_day, answer.last_day).length) {
        Object.assign(state.compare, { years: firstCompareYears(compareYears(answer.first_day, answer.last_day)), series: null, cursor: null });
        // The races of this output, newest first, and the grouping of what
        // it is compared by now (stage M2 of v2.2.0).
        state.compare.races = firstCompareRaces(raceChoices());
        settleCompareGrain(state.compareAnswer?.by ?? null);
      } else {
        state.compare = null;
      }
      state.compareAnswer = null;
      state.compareStop = null;
    }
    // The points go on where the pair can be plotted in this output; their
    // answer is asked for again (Codex's review of the plan of O1).
    if (state.plot !== null) {
      if (plotPairOf(state.plotPair, answer.items) === null) {
        state.plot = null;
      } else {
        state.plot.chosen = null;
      }
      state.plotAnswer = null;
      state.plotAsked = null;
      state.plotStop = null;
    }
    // And a distribution where its item can be counted (stage P1).
    if (state.spread !== null) {
      const key = spreadItemOf(state.spreadItem, answer.items);
      if (key === null) {
        state.spread = null;
      } else {
        state.spreadItem = key;
        state.spread.chosen = null;
      }
      state.spreadAnswer = null;
      state.spreadAsked = null;
      state.spreadStop = null;
    }
    // And the view by shoes where this output has shoes to show (stage S1 of
    // v2.2.0).
    if (state.shoes !== null) {
      if (shoesWhy(state.shoesAvailable) !== null) {
        state.shoes = null;
      } else {
        state.shoes.cursor = null;
      }
      state.shoesAnswer = null;
      state.shoesAsked = null;
      state.shoesStop = null;
    }
    // The summary asks again for the output that opened (stage Q1).
    state.recapAnswer = null;
    state.recapAsked = null;
    state.recapStop = null;
    rememberItems();
    render();
    // A button that opened it is hidden now.
    if (document.activeElement === document.body || document.activeElement?.closest("[hidden]")) {
      ui.outputSelect.focus();
    }
    requestSeries();
    requestCompare();
    requestPlot();
    requestSpread();
    requestShoes();
  } catch (error) {
    if (seq !== state.openSeq) {
      return;
    }
    state.opening = null;
    if (!connectionFailure(error)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
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
  // New numbers close the list of a period (stage M3 of v2.2.0).
  listChanged("numbers");
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
    const payload = seriesPayload(state.items, periodRequest(state.period, state.range), state.grain);
    const asked = ++state.availableAsks;
    const answer = await callApi("/api/view/series", payload);
    if (seq !== state.seriesSeq) {
      return;
    }
    setAnswer(answer);
    state.answerTypes = payload.types;
    state.stop = null;
    if (answer.coverage) {
      state.coverage = answer.coverage;
      state.coverageSeq += 1;
    }
    // As the bars of the shelf: an output read again can have other shoes
    // (Codex's review of the plan of S1 of v2.2.0), unless an answer asked
    // for after this one said it (Codex's review of its diff).
    if (answer.shoes && asked > state.availableFrom) {
      state.shoesAvailable = answer.shoes;
      state.availableFrom = asked;
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
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
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
  const seq = state.openSeq;
  try {
    const answer = await callApi("/api/view/open", targetPayload(state.target));
    // Another output opened meanwhile: its answer stays.
    if (seq !== state.openSeq) {
      return false;
    }
    state.view = answer;
    return true;
  } catch (error) {
    if (seq !== state.openSeq) {
      return false;
    }
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
    const answer = shownAnswer();
    state.range = state.range ?? (answer?.start ? { from: answer.start, to: answer.end } : null);
    render();
    ui.rangeFrom.value = state.range?.from ?? "";
    ui.rangeTo.value = state.range?.to ?? "";
    ui.rangeFrom.focus();
    if (state.range !== null) {
      rememberItems(true);
      requestShown();
    }
    return;
  }
  state.period = choiceName;
  state.cursor = null;
  rememberItems(true);
  requestShown();
}

// The period before or after, from the answer that shows: that of the points
// while they show (Codex's review of the plan of O1).
function shiftPeriod(direction) {
  const answer = shownAnswer();
  const range = shiftedRange(answer?.start, answer?.end, direction, state.view?.first_day, state.view?.last_day);
  if (range !== null) {
    state.period = "custom";
    state.range = range;
    ui.rangeFrom.value = range.from;
    ui.rangeTo.value = range.to;
    state.cursor = null;
    rememberItems(true);
    requestShown();
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
    requestShown();
  }
}

function setGrain(grain) {
  // The points and a distribution have no grouping (stages O1 and P1 of
  // v2.2.0).
  if (otherShown()) {
    return;
  }
  if (comparing()) {
    // A grouping of the comparison, apart from that of the panels.
    if (compareGrainsFor(compareByNow(), compareMonthNow(), compareModeNow()).includes(grain) && grain !== state.compare.grain) {
      state.compare.grain = grain;
      state.compare.cursor = null;
      requestCompare();
    }
    return;
  }
  state.grain = grain;
  state.cursor = null;
  rememberItems(true);
  requestSeries();
}

function changeTypes(name) {
  state.counted = toggledTypes(state.counted, name, state.view?.types);
  state.wantedTypes = typesRequest(state.counted, state.view?.types);
  rememberItems(true);
  requestShown();
  requestCompare();
}

function changeItems(items, refresh = true) {
  listChanged("items");
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

// --- The marks of the person (stage M1 of v2.2.0) --------------------------

// The marks as the server keeps them; the panels are drawn again when they
// changed.
function takeMarks(marks) {
  const taken = marksTaken(marks);
  if (JSON.stringify(taken) !== JSON.stringify(state.marks)) {
    state.marks = taken;
    state.marksSeq += 1;
    listChanged("marks");
    followMarks();
  }
}

// A comparison follows the marks (Codex's review of the plan of M2): the
// races chosen that are still offered, by their days and names now, and the
// years where fewer than two are offered; a new generation of its numbers
// where it asks for another thing than its last request (also one whose
// answer is on its way: Codex's review of the diff), so that an answer for
// the marks before is dropped.
function followMarks() {
  if (!comparing()) {
    return;
  }
  const asked = state.compare.asked ?? null;
  const before = asked?.by ?? null;
  state.compare.races = racesKept(state.compare.races, raceChoices());
  const by = compareByNow();
  const races = by === "race" ? raceChoices().filter((race) => state.compare.races.includes(race.id)) : [];
  const signature = (askedBy, askedRaces) => JSON.stringify([askedBy, askedRaces.map((race) => [race.id, race.day, race.name])]);
  if (asked === null || signature(before, asked.races) !== signature(by, races)) {
    settleCompareGrain(before);
    requestCompare();
  }
}

// A file of the marks that is not used is never written over: the page does
// not change the marks then.
function marksLocked() {
  return MARKS_LOCKED.includes(state.marksNotice);
}

// The marks as the server reads them now, as another tab may have changed
// them; whether they show is the person's choice on this page, and stays.
async function readMarks() {
  const gen = state.marksGen;
  try {
    const status = await callApi("/api/status");
    if (gen !== state.marksGen) {
      return;
    }
    const read = marksToOpen(status.settings ?? {});
    takeMarks(read.marks);
    state.marksNotice = read.notice;
  } catch (error) {
    connectionFailure(error);
  }
}

// One change of the marks on the server (add, change, remove), one at a time:
// a change asked while another waits for its answer is not sent, and the
// controls stay as they are, so that the focus stays where it was. The marks
// of the answer are those that the server keeps, and a change that cannot be
// made says why in the window, with the focus on the field that it is about.
// A mark that another tab removed reads the marks again.
async function changeMarks(change, done = null) {
  if (state.marksWaiting || marksLocked()) {
    return;
  }
  state.marksWaiting = true;
  state.markProblem = null;
  const gen = state.marksGen;
  let field = null;
  try {
    const answer = await callApi("/api/settings/marks", change);
    // The other tab forgot the marks meanwhile: this answer is of before.
    if (gen !== state.marksGen) {
      state.marksWaiting = false;
      render();
      return;
    }
    state.marksNotice = typeof answer.notice === "string" && Object.hasOwn(MARKS_NOTICE_KEYS, answer.notice) ? answer.notice : null;
    if (Array.isArray(answer.marks)) {
      takeMarks(answer.marks);
    } else if (marksLocked()) {
      // The file is not used now: no mark shows, as at a launch.
      takeMarks([]);
    }
    if (answer.remembered === true) {
      done?.();
    }
  } catch (error) {
    if (!connectionFailure(error)) {
      if (error.code === "MARK_NOT_FOUND") {
        await readMarks();
        state.markAsk = null;
        if (!state.marks.some((mark) => mark.id === state.markEditing)) {
          editMark(null, false);
        }
      }
      state.markProblem = MARK_PROBLEM_KEYS[error.code] ?? "view.marks.error.other";
      field = { MARK_NAME_INVALID: ui.markName, MARK_DAY_INVALID: ui.markDay }[error.code] ?? null;
    }
  }
  state.marksWaiting = false;
  render();
  field?.focus();
}

// The window of the marks: it reads the marks again as it opens, its first
// field takes the focus, and its opener takes it back when it closes.
async function openMarks(open) {
  state.marksOpen = open;
  if (open) {
    // One window opens under the right end of the row at a time (stage Q1).
    state.recapOpen = false;
    state.saveOpen = false;
  }
  state.markAsk = null;
  state.markProblem = null;
  editMark(null, false);
  render();
  if (open) {
    focusMarkForm();
    await readMarks();
    render();
  } else {
    ui.marksOpen.focus();
  }
}

// The first field of the form takes the focus, or the button that closes the
// window while the form cannot be used (200 marks, or a file not used).
function focusMarkForm() {
  (ui.markDay.disabled ? ui.marksPopClose : ui.markDay).focus();
}

// The values of the fields of the form, as they were sent.
function markFields() {
  return [ui.markDay.value, ui.markEnd.value, ui.markKind.value, ui.markName.value, state.markEditing];
}

// The form of the window adds a mark, or changes the mark ``id`` with its
// values in the fields.
function editMark(id, focus = true) {
  const mark = state.marks.find((one) => one.id === id) ?? null;
  state.markEditing = mark === null ? null : mark.id;
  state.markProblem = null;
  ui.markDay.value = mark?.day ?? "";
  ui.markEnd.value = mark?.end ?? "";
  ui.markKind.value = mark?.kind ?? MARK_KINDS[0];
  ui.markName.value = mark?.name ?? "";
  if (focus) {
    render();
    focusMarkForm();
  }
}

function saveMark() {
  if (state.marksWaiting || marksLocked()) {
    return;
  }
  const day = ui.markDay.value;
  const end = ui.markEnd.value;
  const problem = markDaysProblem(day, end);
  if (problem !== null) {
    state.markProblem = problem;
    render();
    ui.markDay.focus();
    return;
  }
  // No last day: a mark of one day.
  const values = { kind: ui.markKind.value, name: ui.markName.value, day, ...(end === "" ? {} : { end }) };
  const editing = state.markEditing;
  const sent = JSON.stringify(markFields());
  changeMarks(editing === null ? { op: "add", ...values } : { op: "change", id: editing, ...values }, () => {
    // What was typed after the change was sent stays.
    if (JSON.stringify(markFields()) === sent) {
      editMark(null, false);
    }
    render();
    focusMarkForm();
  });
}

// The buttons of the list of the marks: change, remove (asked first, with
// "Keep it" chosen), and the answer to the question.
function marksAction(event) {
  const button = event.target.closest("button[data-op]");
  if (button === null || button.disabled) {
    return;
  }
  const id = button.dataset.id;
  if (button.dataset.op === "change") {
    state.markAsk = null;
    editMark(id);
  } else if (button.dataset.op === "remove") {
    state.markAsk = id;
    state.markProblem = null;
    render();
    ui.marksList.querySelector('[data-op="keep"]')?.focus();
  } else if (button.dataset.op === "keep") {
    state.markAsk = null;
    render();
    ui.marksList.querySelector(`[data-op="remove"][data-id="${CSS.escape(id)}"]`)?.focus();
  } else if (button.dataset.op === "remove-yes") {
    changeMarks({ op: "remove", id }, () => {
      state.markAsk = null;
      if (state.markEditing === id) {
        editMark(null, false);
      }
      render();
      focusMarkForm();
    });
  }
}

// The window of the marks stays inside the window of the browser, and
// scrolls; it is measured again when the browser's window changes size.
// A window under the row above the panels reaches down to the bar at the
// bottom of the page, which stays on the screen above it, and no further on
// a low screen (stage Q1: the end of a window was under the bar at 1366x650,
// and Codex's review of the diff: 240 pixels at least went under it too).
function fitPop(pop) {
  if (pop.hidden) {
    return;
  }
  const bar = ui.viewBar.getBoundingClientRect();
  const bottom = bar.height > 0 ? Math.min(window.innerHeight, bar.top) : window.innerHeight;
  pop.style.maxHeight = `${Math.max(0, Math.floor(bottom - pop.getBoundingClientRect().top - 12))}px`;
}

function fitMarksWindow() {
  fitPop(ui.marksPop);
}

// Whether the marks show is a change of the person, remembered with the view.
function changeMarksShown() {
  state.marksShown = ui.marksShown.checked;
  listChanged("marks");
  render();
  rememberItems(true);
}

// A small picture of the line of a kind of mark, or of the band of a span.
function markSwatch(kind, span) {
  const swatch = svgElement("svg", { viewBox: "0 0 22 12", width: 22, height: 12, "aria-hidden": "true", focusable: "false" });
  if (span) {
    swatch.append(svgElement("rect", { class: "day-band", x: 3, y: 1, width: 16, height: 10 }));
    for (const x of [3, 19]) {
      swatch.append(svgElement("line", { class: `day-mark ${kind}`, x1: x, x2: x, y1: 0, y2: 12 }));
    }
  } else {
    swatch.append(svgElement("line", { class: `day-mark ${kind}`, x1: 11, x2: 11, y1: 0, y2: 12 }));
  }
  return swatch;
}

// The row of the panels holds the switch and the button of the marks; the
// window says what the panels show, lists the marks (newest first), and adds
// or changes one.
// --- The summary of the panels (stage Q1 of v2.2.0) ----------------------

// Whether the window of the summary can show: an output shown, panels,
// neither a comparison of years nor another view, and not the graphs only
// (Codex's review of the plan of Q1: the row above the panels shows without
// a panel, and full screen hides it by its style only).
function recapShowable(viewing) {
  return viewing && !apart() && state.items.length > 0 && !state.full;
}

// What the summary asks for: the ticket, the period as chosen, the activity
// types counted, and the items of the panels in their order; a change of
// any of them asks again (Codex's simpler form).
function recapKey() {
  return JSON.stringify([state.view?.view ?? null, periodRequest(state.period, state.range), typesRequest(state.counted, state.view?.types), state.items]);
}

// The window opens with the focus on its title, asking again, and its
// button takes the focus back when it closes; the window of the marks, at the
// same place, closes as its button closes it.
function openRecap(open) {
  state.recapOpen = open;
  state.recapAsked = null;
  if (open) {
    // The window of the saving, at the same place, closes too (stage R1).
    state.saveOpen = false;
  }
  if (open && state.marksOpen) {
    state.marksOpen = false;
    state.markAsk = null;
    editMark(null, false);
  }
  render();
  if (open) {
    ui.recapTitle.focus();
  } else {
    ui.recapOpen.focus();
  }
}

// The numbers of the summary: the whole period of the page and the period
// of the same length just before it, as the server makes them; the answer of
// the last request only, kept with what it asked for, so that it is drawn
// for that only. A ticket that the server no longer keeps opens the
// output again once; an output that cannot be read stops the page; another
// stop shows in the window, and the panels stay (Codex's review of the plan).
async function requestRecap(again = true) {
  if (!state.recapShown || state.view === null || !state.items.length) {
    return;
  }
  const seq = ++state.recapSeq;
  const key = recapKey();
  state.recapAsked = key;
  state.recapAnswer = null;
  state.recapStop = null;
  state.recapLoading = true;
  render();
  try {
    const payload = { ...seriesPayload(state.items, periodRequest(state.period, state.range), RANGE_GRAIN), previous: true };
    const answer = await callApi("/api/view/series", payload);
    if (seq !== state.recapSeq) {
      return;
    }
    state.recapAnswer = { key, answer };
  } catch (error) {
    if (seq !== state.recapSeq) {
      return;
    }
    if (connectionFailure(error)) {
      // The bar says so.
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null) {
      if (await reopen()) {
        if (seq !== state.recapSeq) {
          return;
        }
        state.recapLoading = false;
        requestRecap(false);
        return;
      }
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
      state.stop = { code: error.code, detail: error.detail };
    } else {
      state.recapStop = { code: error.code, detail: error.detail };
    }
  }
  if (seq === state.recapSeq) {
    state.recapLoading = false;
  }
  render();
}

// The table of the summary keeps its heads and two rows or so where the
// window is low, which then scrolls as a whole (Codex's review of the diff of
// Q1); a shorter table keeps all of it.
const RECAP_KEPT = 112;

function fitRecapWindow() {
  if (!ui.recapPop.hidden) {
    ui.recapBody.style.minHeight = "";
    ui.recapBody.style.minHeight = `${Math.min(ui.recapBody.scrollHeight, RECAP_KEPT)}px`;
  }
  fitPop(ui.recapPop);
}

// The window of the summary: hidden while it cannot show, its state kept,
// and asked again once when it shows again (the checker's answer 5 of the
// plan of Q1); the focus inside it goes back to its button where it hides.
function renderRecap(viewing, live) {
  // An output that stops closes the window, which another output opens
  // without (the plan of Q1); a stop above an output shown keeps it.
  if (state.view === null && state.stop !== null) {
    state.recapOpen = false;
  }
  const showable = recapShowable(viewing);
  ui.recapOpen.disabled = !viewing || !state.items.length;
  ui.recapOpen.setAttribute("aria-expanded", String(state.recapOpen && showable));
  const focused = ui.recapPop.contains(document.activeElement);
  ui.recapPop.hidden = !state.recapOpen || !showable;
  if (ui.recapPop.hidden) {
    if (state.recapShown) {
      // Answers on their way are dropped, and a ticket that the server no
      // longer keeps is not opened again: the window asks again when it shows
      // again (Codex's review of the diff of Q1).
      state.recapShown = false;
      state.recapSeq += 1;
      state.recapLoading = false;
    }
    if (focused) {
      // To the button, or where it does not show, to the heading of what
      // shows instead, as graphs only does (Codex's review of the diff).
      const shown = (node) => node.closest("[hidden]") === null;
      const target = !ui.recapOpen.disabled && shown(ui.recapOpen) ? ui.recapOpen : [ui.stopHeading, ui.emptyHeading].find(shown);
      target?.focus();
    }
    return;
  }
  if (!state.recapShown) {
    state.recapShown = true;
    state.recapAsked = null;
  }
  if (live && state.recapAsked !== recapKey()) {
    // Asked after this render, once for what it shows.
    state.recapAsked = recapKey();
    queueMicrotask(() => requestRecap());
  }
  const columns = recapColumns(periodRequest(state.period, state.range), state.language);
  // An answer for other items or another period is not drawn under these.
  const answer = state.recapAnswer?.key === recapKey() ? state.recapAnswer.answer : null;
  setText(ui.recapLoading, state.recapLoading ? t("view.loading") : "");
  ui.recapStop.hidden = state.recapStop === null;
  if (!ui.recapStop.hidden) {
    renderStop(ui.recapStop, null, ui.recapStopLines, ui.recapStopCode, stopBox(state.recapStop.code, state.recapStop.detail, state.productVersion));
  }
  const days = answer === null ? null : recapDays(answer, columns, state.language);
  setText(ui.recapDays, days === null ? "" : describe(days));
  ui.recapDifferenceNote.hidden = columns.before === null;
  renderRecapTable(answer, columns);
  fitRecapWindow();
}

// The table of the summary: a row for each item of the panels (a row for
// each series of an item of several), its value in the period shown, in the
// period before, and their difference as a number only; a value of a period
// that the output cuts marked *, with no difference. While an answer is on
// its way the table is empty: a table is read as numbers (the checker's
// answer 4 of the plan of Q1).
function renderRecapTable(answer, columns) {
  const signature = JSON.stringify([state.language, answer, state.items]);
  if (ui.recapBody.dataset.signature === signature) {
    return;
  }
  ui.recapBody.dataset.signature = signature;
  setText(ui.recapCut, "");
  if (answer === null) {
    ui.recapBody.replaceChildren();
    return;
  }
  if (!Array.isArray(answer.panels) || !answer.panels.length) {
    ui.recapBody.replaceChildren(element("p", "note", t("view.summary.none")));
    return;
  }
  const previous = columns.before === null ? null : answer.previous;
  const table = element("table");
  const head = element("tr");
  for (const name of [t("view.recap.item"), describe(columns.now), ...(columns.before === null ? [] : [describe(columns.before), t("view.recap.difference")])]) {
    const cell = element("th", "", name);
    cell.scope = "col";
    head.append(cell);
  }
  const thead = element("thead");
  thead.append(head);
  const tbody = element("tbody");
  const nowWhole = answer.whole === true;
  const beforeWhole = previous !== null && previous.whole === true;
  const beforeOutside = previous === null || typeof previous.start !== "string";
  const valueText = (key, line, cut) => {
    const value = line?.values?.[0];
    return Number.isFinite(value) ? `${describe(valueMessage(key, value, state.language))}${cut ? "*" : ""}` : t("view.recap.none");
  };
  answer.panels.forEach((panel, index) => {
    const key = state.items[index];
    const before = previous?.panels?.[index] ?? null;
    for (const row of recapRows(panel, before, state.language)) {
      const tr = element("tr");
      const name = element("th", "", itemName(key));
      name.scope = "row";
      if (row.name !== null) {
        // The name of the line under that of the item, a word apart when
        // it is read.
        name.append(" ", element("span", "recap-line", describe(row.name)));
      }
      tr.append(name, element("td", "", valueText(key, row.now, !nowWhole)));
      if (columns.before !== null) {
        tr.append(element("td", "", beforeOutside ? "\u2014" : valueText(key, row.before, !beforeWhole)));
        const difference = nowWhole && beforeWhole ? recapDifference(key, row.now?.values?.[0], row.before?.values?.[0], state.language) : null;
        tr.append(element("td", "", difference === null ? "\u2014" : describe(difference)));
      }
      tbody.append(tr);
    }
  });
  table.append(thead, tbody);
  ui.recapBody.replaceChildren(table);
  // The notes of the periods that the output cuts.
  const notes = [];
  const nowPartial = nowWhole ? null : recapPartial(answer.chosen, answer.start, answer.end, state.language);
  if (nowPartial !== null) {
    notes.push(t("view.recap.cut_note", { name: describe(columns.now), partial: describe(nowPartial) }));
  }
  if (previous !== null && !beforeOutside && !beforeWhole) {
    const beforePartial = recapPartial(previous.chosen, previous.start, previous.end, state.language);
    if (beforePartial !== null) {
      notes.push(t("view.recap.cut_note", { name: describe(columns.before), partial: describe(beforePartial) }));
    }
  }
  setText(ui.recapCut, notes.join(" "));
}

// --- Saving as an image (stage R1 of v2.2.0) ------------------------------

// The width of a picture, its margin, and the room of its charts, which are
// those of the page made as wide as that, their heights in the same ratio; the
// gap between the pieces of a heading, the heights of a line of a heading and
// of the line under the picture, and the room of a key of a line (its swatch
// and a gap).
const SAVE_WIDTH = 1200;
const SAVE_MARGIN = 8;
const SAVE_ROOM = SAVE_WIDTH - 2 * SAVE_MARGIN;
const SAVE_GAP = 8;
const SAVE_LINE = 20;
const SAVE_FOOT_LINE = 16;
const SAVE_SWATCH = 26;
const SAVE_TITLE_LINE = 22;

// The chart of the page of a panel, or null where it has none (a table, or a
// plot too small to draw).
function savedChart(key) {
  return drawn.find((entry) => entry.key === key)?.plot?.querySelector(":scope > svg") ?? null;
}

// What a saving does now: the panels in the order shown (the panel made big
// first) without those shown as tables, the one chosen (which stays chosen
// where it no longer shows, so that a picture never takes another panel
// unseen) and those saved, the name of the file from the days of the answer,
// and whether the page draws marks that can go in.
function savePlan() {
  const shown = shownPanels().map((entry) => entry.key);
  const tables = shown.filter((key) => state.tables.has(key) && panelMode(key) !== "mini");
  const charts = shown.filter((key) => !tables.includes(key));
  const chosen = state.savePanel ?? charts[0] ?? null;
  const keys = savedPanels(shown, tables, state.saveScope, chosen);
  const days = saveDays(state.answer);
  return {
    charts,
    tables,
    chosen,
    keys,
    name: days === null ? null : saveFileName(days.start, days.end, keys),
    marksDrawn: ui.panels.querySelector(".plot > svg .day-mark, .plot > svg .day-band") !== null,
  };
}

// Whether the panels can be saved now, as the window shows it and as a saving
// checks it again: an answer not on its way, no stop of the panels, and the
// charts to copy (Codex's review of the plan of R1).
function saveReady(viewing) {
  const plan = savePlan();
  const ready =
    plan.name !== null &&
    plan.keys.every((key) => savedChart(key) !== null) &&
    saveShowable({
      viewing,
      apart: apart(),
      full: state.full,
      items: state.items.length,
      answer: state.answer,
      loading: state.loading,
      stopped: state.seriesStop !== null,
      charts: plan.keys.length,
    });
  return { plan, ready };
}

// The view whose picture a saving makes now: the panels, or the view that
// takes their place (stage R2 of v2.2.0).
function saveViewNow() {
  return comparing() ? "compare" : plotting() ? "plot" : spreading() ? "spread" : shoesShown() ? "shoes" : "panels";
}

// The button of the saving of a view, and the row under which the window
// opens from it: the row above the panels, or the first line of the bar.
function saveButton(view) {
  return { panels: ui.saveOpen, compare: ui.compareSave, plot: ui.plotSave, spread: ui.spreadSave, shoes: ui.shoesSave }[view];
}

function saveRow(view) {
  return view === "panels" ? ui.caveat : saveButton(view).closest(".compare-line");
}

// Whether the page shows an output now, as a saving checks it again.
function viewingNow() {
  return state.connected && !state.stopped && !state.quitting && state.view !== null && state.opening === null;
}

// What a saving from the window does now, which the window, the check at
// the press, and the picture all go by (Codex's review of the plan of R2):
// for the panels, the plan of R1; for another view, its title line, its
// parts, the legend of a calendar, the notes under it, the name of the
// file, and the line under it; whether it can save now, and why not.
function saveTarget(viewing) {
  const view = state.saveFrom;
  if (view === "panels") {
    const { plan, ready } = saveReady(viewing);
    const drawn = plan.keys.filter((key) => savedChart(key) !== null).length;
    const problem = saveProblem({ stopped: state.seriesStop !== null, loading: state.loading, answer: state.answer, drawn, parts: plan.keys.length });
    return { view, plan, ready, name: plan.name, problem, loading: state.loading, marks: false };
  }
  const target = view === "compare" ? saveCompareTarget() : view === "plot" ? savePlotTarget() : view === "spread" ? saveSpreadTarget() : saveShoesTarget();
  const charts = target.parts.filter((part) => part.source !== null).length;
  target.ready =
    viewing &&
    saveViewNow() === view &&
    target.name !== null &&
    charts === target.parts.length &&
    saveViewReady({ answer: target.answer, loading: target.loading, stopped: target.stopped, table: target.table, charts });
  target.problem = saveProblem({
    table: target.table,
    stopped: target.stopped,
    loading: target.loading,
    answer: target.answer,
    empty: target.empty,
    drawn: charts,
    parts: target.parts.length,
  });
  return target;
}

// A comparison: the answer drawn (a table draws no part), its title in the
// words of the page, its rows or strips or one chart, the legend of a
// calendar, and the axis; by race, the names of the races show (the
// checker's answer 5).
function saveCompareTarget() {
  const compare = state.compare;
  const answer = compare !== null && state.compareAnswer !== null && state.compareAnswer.key === compare.key ? state.compareAnswer : null;
  const race = answer?.by === "race";
  const years = answer === null || race ? [] : answer.years;
  const days = answer === null || !race ? [] : answer.races.map((each) => each.day);
  const shown = answer !== null && !ui.compareStack.hidden;
  return {
    view: "compare",
    answer,
    loading: state.compareLoading,
    stopped: state.compareStop !== null,
    table: compare?.table ?? false,
    empty: false,
    title: answer === null ? "" : compareSaveTitle(answer),
    parts: shown ? compared.map(saveComparePart) : [],
    legend: shown && !ui.compareLegend.hidden ? saveCalendarLegend() : null,
    axis: shown && !ui.compareAxis.hidden ? ui.compareAxis.querySelector(":scope > svg") : null,
    notes: [],
    drop: SAVE_LEFT_OUT_VIEWS.compare.join(", "),
    name: answer === null ? null : saveViewFileName("compare", { key: answer.key, years, days }),
    footer:
      answer === null
        ? []
        : saveViewFooter("compare", {
            years,
            days,
            grain: answer.grain,
            answerTypes: answer.types,
            types: state.view?.types,
            version: state.productVersion,
            language: state.language,
            separator: t("view.spoken_separator"),
            daysSeparator: t("view.save.days_separator"),
          }),
    marks: race,
  };
}

// The title of a picture of a comparison in one line, in the words of the
// page (the checker's answer 3): what is compared by what, how it shows, its
// month or the weeks before its races, and its line where it has a choice.
function compareSaveTitle(answer) {
  const race = answer.by === "race";
  const mode = compareModeNow();
  const words = [
    t("view.compare.title_by", { item: itemName(answer.key), by: t(race ? "view.compare.by.race" : "view.compare.by.year") }),
    mode === "rows" && race ? t("view.compare.mode.rows_race") : t(`view.compare.mode.${mode}`),
    race ? t("view.compare.weeks_option", { n: answer.weeks }) : answer.month === null ? t("view.compare.month_all") : describe(compareSlotName(answer.month - 1, "month", null, state.language)),
  ];
  if (!ui.compareSeriesField.hidden && ui.compareSeries.selectedIndex >= 0) {
    words.push(ui.compareSeries.selectedOptions[0].textContent);
  }
  return words.join(t("view.save.separator"));
}

// A part of a picture of a comparison: the words of the head of its row, its
// strip, or its one chart as the page shows them (the name, the days cut, the
// value, the unit, the kind, and the keys with their swatches), its chart,
// and the words that the page shows in place of an empty chart (Codex's
// review of the plan of R2); the reading of the day chosen is not taken.
// The view by shoes (stage S1 of v2.2.0): its answer drawn (its tables draw
// no part), its title, its rows, which the parts of a comparison read, all of
// them, also those scrolled out of the screen, its axis, and its notes (Codex's
// review of the plan of S1); its period and the key of the distance name the
// file, never the names of the shoes.
function saveShoesTarget() {
  const drawn = state.shoes === null ? null : state.shoesAnswer;
  // The rows of the answer shown, not of one on its way, as for the other
  // views (Codex's review of the plan of R2, 2).
  const shown = drawn !== null && !state.shoes.table && shoesDrawn !== null && shoesDrawn[0] === drawn;
  return {
    view: "shoes",
    answer: drawn,
    loading: state.shoesLoading,
    stopped: state.shoesStop !== null,
    table: state.shoes?.table ?? false,
    empty: drawn !== null && !drawn.shoes.length,
    title: drawn === null ? "" : t("view.shoes.title"),
    parts: shown ? shoeRows.map(saveComparePart) : [],
    legend: null,
    axis: shown && !ui.shoesAxis.hidden ? ui.shoesAxis.querySelector(":scope > svg") : null,
    notes: drawn === null ? [] : saveNotesOf([...ui.shoesNotes.children]),
    drop: SAVE_LEFT_OUT_VIEWS.shoes.join(", "),
    name: drawn === null ? null : saveViewFileName("shoes", { key: "dist", start: drawn.start, end: drawn.end }),
    footer:
      drawn === null
        ? []
        : saveViewFooter("shoes", {
            start: drawn.start,
            end: drawn.end,
            answerTypes: state.shoesAsked?.types ?? null,
            types: state.view?.types,
            version: state.productVersion,
            language: state.language,
            separator: t("view.spoken_separator"),
          }),
    marks: false,
  };
}

function saveComparePart(entry) {
  const head = entry.section.querySelector(entry.kind === "calendar" ? ".calendar-side" : ".panel-head");
  const pieces = [];
  for (const node of head?.children ?? []) {
    if (node.matches("h4")) {
      pieces.push({ text: node.textContent, className: "save-name" });
    } else if (node.matches(".panel-unit, .compare-whole")) {
      pieces.push({ text: node.textContent, className: "save-unit" });
    } else if (node.matches(".panel-kind")) {
      pieces.push({ text: node.textContent, className: "save-kind" });
    } else if (node.matches(".panel-keys")) {
      for (const key of node.querySelectorAll(".key")) {
        // The key of a year stood out is bold, as on the page (stage L3 of
        // v2.2.0).
        const className = key.getAttribute("aria-pressed") === "true" ? "save-key lit" : "save-key";
        pieces.push({ text: keyWords(key), className, swatch: () => key.querySelector("svg").cloneNode(true) });
      }
    }
  }
  return {
    pieces: pieces.filter((piece) => piece.text !== ""),
    source: entry.plot.querySelector(":scope > svg"),
    empty: entry.plot.querySelector(".panel-empty")?.textContent ?? null,
  };
}

// The legend of a calendar as the page shows it above its strips, but the
// rule of its steps without where the page reads the values, which a picture
// cannot do (Codex's review of the plan of R2).
function saveCalendarLegend() {
  const pieces = [];
  const notes = [];
  for (const node of ui.compareLegend.children) {
    if (node.matches(".calendar-key")) {
      pieces.push({ text: node.textContent, className: "save-key", swatch: () => node.querySelector("svg").cloneNode(true), swatchSize: [12, 12] });
    } else if (node.matches(".calendar-note")) {
      notes.push(node.textContent === t("view.compare.calendar_note") ? t("view.compare.calendar_steps") : node.textContent);
    } else {
      pieces.push({ text: node.textContent, className: "save-unit" });
    }
  }
  return { pieces: pieces.filter((piece) => piece.text !== ""), notes };
}

// Two items plotted: the answer drawn as a chart, its title in the words of
// the page, and the lines under it that the page shows (the points, those
// cut, and that it shows no relation, which the page never hides).
function savePlotTarget() {
  const answer = plotAnswerNow();
  const asked = state.plotAsked;
  const drawnNow = answer !== null && plotContext !== null && plotContext.answer === answer;
  return {
    view: "plot",
    answer,
    loading: state.plotLoading,
    stopped: state.plotStop !== null,
    table: state.plot?.table ?? false,
    empty: answer !== null && !answer.points.length,
    title: asked === null ? "" : t("view.plot.title", { x: itemName(asked.x), y: itemName(asked.y) }),
    parts: [{ pieces: [], source: drawnNow ? ui.plotBody.querySelector(".plot-points > svg") : null, empty: null }],
    legend: null,
    axis: null,
    notes: [...saveNotesOf([ui.plotCount, ui.plotCut]), t("view.plot.caveat")],
    drop: SAVE_LEFT_OUT_VIEWS.plot.join(", "),
    name: answer === null ? null : saveViewFileName("plot", { keys: [asked.x, asked.y], start: answer.start, end: answer.end }),
    footer:
      answer === null
        ? []
        : saveViewFooter("plot", { start: answer.start, end: answer.end, answerTypes: asked.types, types: state.view?.types, version: state.productVersion, language: state.language }),
    marks: false,
  };
}

// A distribution, as two items plotted: the lines under it are the
// activities counted, the wider width, and that a smaller pace is faster.
function saveSpreadTarget() {
  const answer = spreadAnswerNow();
  const asked = state.spreadAsked;
  const drawnNow = answer !== null && spreadContext !== null && spreadContext.answer === answer;
  return {
    view: "spread",
    answer,
    loading: state.spreadLoading,
    stopped: state.spreadStop !== null,
    table: state.spread?.table ?? false,
    empty: answer !== null && !answer.counts.length,
    title: asked === null ? "" : t("view.spread.title", { item: itemName(asked.item) }),
    parts: [{ pieces: [], source: drawnNow ? ui.spreadBody.querySelector(".spread-bars > svg") : null, empty: null }],
    legend: null,
    axis: null,
    notes: saveNotesOf([ui.spreadCount, ui.spreadWide, ui.spreadFaster]),
    drop: SAVE_LEFT_OUT_VIEWS.spread.join(", "),
    name: answer === null ? null : saveViewFileName("spread", { key: asked.item, start: answer.start, end: answer.end }),
    footer:
      answer === null
        ? []
        : saveViewFooter("spread", {
            start: answer.start,
            end: answer.end,
            key: asked.item,
            answer,
            answerTypes: asked.types,
            types: state.view?.types,
            version: state.productVersion,
            language: state.language,
          }),
    marks: false,
  };
}

// The words of the lines that show under a chart.
function saveNotesOf(nodes) {
  return nodes.filter((node) => node.closest("[hidden]") === null && node.textContent !== "").map((node) => node.textContent);
}

// What the line after a saving is said of (the checker's R1-3); another view
// adds what it shows (stage R2 of v2.2.0).
function saveNoticeNow() {
  const view = saveViewNow();
  return saveNoticeKey({
    ticket: state.view?.view ?? null,
    period: periodRequest(state.period, state.range),
    types: typesRequest(state.counted, state.view?.types),
    items: state.items,
    language: state.language,
    view,
    content: saveContent(view),
  });
}

// What a picture of another view shows, by which the line after its saving
// goes: the item, what it is compared by, the years or the races, how it
// shows, the month or the weeks, and the line; the two items plotted; the
// item of a distribution (the checker's review of the handling of Codex's
// review of the plan of R2), the grouping of a comparison (Codex's review of
// the diff of R2), and the year stood out (stage L3 of v2.2.0).
function saveContent(view) {
  if (view === "compare" && state.compare !== null) {
    const by = compareByNow();
    return [state.compare.key, by, by === "race" ? state.compare.races : state.compare.years, compareModeNow(), compareMonthNow(), state.compareWeeks, state.compare.series, state.compare.grain, state.compare.lit?.id ?? null];
  }
  if (view === "plot") {
    return [state.plotPair.x, state.plotPair.y];
  }
  return view === "spread" ? [state.spreadItem] : null;
}

// The window opens under the row of its button, at its right end, as under
// the row above the panels in R1; placed again each time the page draws, the
// window changes its size, or a chart is drawn again, as the language or the
// wrapping of the row may move the row; not out of the left of the stage
// (Codex's review of the plan of R2). Its width is that of R1, but not wider
// than the stage, which hides what goes out of it (Codex's review of the diff
// of R2), and its place in the fractions of a pixel that R1 had (the checker).
function fitSaveWindow() {
  if (!ui.savePop.hidden) {
    const stage = ui.stage.getBoundingClientRect();
    const row = saveRow(state.saveFrom).getBoundingClientRect();
    const pad = parseFloat(getComputedStyle(ui.stage).paddingLeft) || 0;
    ui.savePop.style.maxWidth = `${Math.max(0, stage.width - 2 * pad)}px`;
    const width = ui.savePop.getBoundingClientRect().width;
    let right = stage.right - row.right;
    if (stage.width - right - width < pad) {
      right = stage.width - pad - width;
    }
    ui.savePop.style.top = `${row.bottom - stage.top + ui.stage.scrollTop}px`;
    ui.savePop.style.right = `${Math.max(0, right)}px`;
  }
  fitPop(ui.savePop);
}

// The window of the saving: where the window of the summary can show, its
// choices of this time it opens, the name of the file that it makes, the line
// before a saving, and why it cannot save; the focus inside it goes back to
// its button where it hides.
function renderSave(viewing) {
  if (state.view === null && state.stop !== null) {
    state.saveOpen = false;
  }
  // The window goes with the view of its button (stage R2 of v2.2.0).
  const view = saveViewNow();
  if (state.saveOpen && state.saveFrom !== view) {
    state.saveOpen = false;
  }
  const showable = saveWindowShows({ viewing, from: state.saveFrom, view, items: state.items.length, full: state.full });
  ui.saveOpen.disabled = !viewing || !state.items.length;
  for (const each of ["compare", "plot", "spread", "shoes"]) {
    saveButton(each).disabled = !viewing;
  }
  for (const each of ["panels", "compare", "plot", "spread", "shoes"]) {
    saveButton(each).setAttribute("aria-expanded", String(state.saveOpen && showable && state.saveFrom === each));
  }
  const focused = ui.savePop.contains(document.activeElement);
  ui.savePop.hidden = !state.saveOpen || !showable;
  if (ui.savePop.hidden) {
    if (focused) {
      const shown = (node) => node.closest("[hidden]") === null;
      const button = saveButton(state.saveFrom);
      const target = !button.disabled && shown(button) ? button : [ui.stopHeading, ui.emptyHeading].find(shown);
      target?.focus();
    }
    return;
  }
  const target = saveTarget(viewing);
  const panels = target.view === "panels";
  // Another view saves its one picture: no panels or marks to choose, and
  // what it saves in one line (the plan of R2).
  ui.saveScopeField.hidden = !panels;
  ui.saveMarksField.hidden = !panels;
  ui.saveWhat.hidden = panels;
  setText(ui.saveWhat, panels ? "" : t("view.save.what", { name: target.title }));
  ui.saveLight.checked = state.saveColors === "light";
  ui.saveScreen.checked = state.saveColors === "screen";
  setText(ui.saveName, target.name ?? "—");
  ui.saveGo.disabled = !target.ready;
  const warn = t("view.save.warn");
  const gone = panels ? renderSavePanels(target.plan) : false;
  // By race, the names of the races, which are those of the marks, show
  // always (the checker's answer 5 of the plan of R2).
  // The view by shoes: the names of all the shoes, also of the rows out of
  // the screen (Codex's review of the plan of S1 of v2.2.0).
  const named = target.view === "shoes" ? t("view.save.warn_shoes") : (panels ? ui.saveMarks.checked : target.marks) ? t("view.save.warn_marks") : null;
  setText(ui.saveWarn, named !== null ? `${warn}${state.language === "ja" ? "" : " "}${named}` : warn);
  const problem = state.saveProblem ?? (gone ? "view.save.gone" : null) ?? target.problem;
  setText(ui.saveProblem, problem !== null ? saveProblemText(problem) : target.loading ? t("view.loading") : "");
  fitSaveWindow();
}

// The words of why the window cannot save: of a view shown as a table, with
// the name of the button that shows its chart again.
function saveProblemText(problem) {
  if (problem !== "view.save.table") {
    return t(problem);
  }
  const calendar = state.saveFrom === "compare" && compareModeNow() === "calendar";
  return t(problem, { button: t(calendar ? "view.compare.table_calendar" : "view.panel.chart") });
}

// The choices of the panels (stage R1): which panels, and the marks; true
// where the panel chosen no longer shows.
function renderSavePanels(plan) {
  setText(ui.saveAllLabel, t("view.save.all", { n: formatNumber(plan.charts.length) }));
  const options = plan.charts.map((key) => [key, itemName(key)]);
  const signature = JSON.stringify(options);
  if (ui.savePanel.dataset.signature !== signature) {
    ui.savePanel.replaceChildren(
      ...options.map(([key, name]) => {
        const option = element("option", "", name);
        option.value = key;
        return option;
      }),
    );
    ui.savePanel.dataset.signature = signature;
  }
  // The panel chosen that no longer shows is not chosen in the list, and the
  // window says so (Codex's review of the plan of R1).
  const gone = state.saveScope === "one" && plan.chosen !== null && !plan.charts.includes(plan.chosen);
  if (plan.charts.includes(plan.chosen)) {
    ui.savePanel.value = plan.chosen;
  } else {
    ui.savePanel.selectedIndex = -1;
  }
  ui.saveAll.checked = state.saveScope === "all";
  ui.saveOne.checked = state.saveScope === "one";
  ui.saveOne.disabled = !plan.charts.length;
  ui.savePanel.disabled = !plan.charts.length;
  ui.saveTables.hidden = !plan.tables.length;
  setText(ui.saveTables, !plan.tables.length ? "" : plan.charts.length ? t("view.save.tables", { n: formatNumber(plan.tables.length) }) : t("view.save.all_tables"));
  if (!plan.marksDrawn) {
    // Chosen again where marks show again, so that their names never go in
    // as chosen before (Codex's review of the diff of R1).
    state.saveMarks = false;
  }
  ui.saveMarks.disabled = !plan.marksDrawn;
  ui.saveMarks.checked = plan.marksDrawn && state.saveMarks;
  ui.saveMarksNone.hidden = plan.marksDrawn;
  return gone;
}

// The line after a saving, in the bar at the bottom, until the output, the
// period, the types, the items, or the language change; a drawing again
// keeps it (the checker's R1-3).
function renderSaveNotice() {
  if (state.saveNotice !== null && state.saveNotice !== saveNoticeNow()) {
    state.saveNotice = null;
  }
  setText(ui.saveStatus, state.saveNotice === null ? "" : t("view.save.notice"));
}

// The window of the saving opens with the focus on its title, each time with
// the first choices, which nothing remembers, so that the names of the marks
// do not go in as chosen before (the plan of R1); the other windows at its
// place close, and the line after a saving goes.
function openSave(open, from = state.saveFrom) {
  state.saveOpen = open;
  state.saveProblem = null;
  if (open) {
    // The view of the button, under whose row the window opens (stage R2).
    state.saveFrom = from;
    state.saveScope = "all";
    state.savePanel = null;
    state.saveColors = "light";
    state.saveMarks = false;
    state.saveNotice = null;
    state.recapOpen = false;
    if (state.marksOpen) {
      state.marksOpen = false;
      state.markAsk = null;
      editMark(null, false);
    }
  }
  render();
  (open ? ui.saveTitle : saveButton(state.saveFrom)).focus();
}

// A choice of the window.
function changeSave(change) {
  Object.assign(state, change, { saveProblem: null });
  render();
}

// Saving: the panels checked again as the window names them, the picture made
// in the box out of the page and handed to the browser as a download from a
// blob: address, all in the press of the button with nothing between, as a
// browser may not save a download that comes later (the checker's R1-4).
// Nothing is sent anywhere. Where it cannot be done, the window stays with
// the reason and the focus on its button, and the line after a saving does
// not show (Codex's review of the plan of R1).
function saveImage() {
  const target = saveTarget(viewingNow());
  let problem = null;
  if (target.view === "panels" && state.saveScope === "one" && !target.plan.keys.length) {
    problem = "view.save.gone";
  } else if (!target.ready || target.name !== ui.saveName.textContent) {
    problem = "view.save.changed";
  }
  if (problem === null) {
    let stage = null;
    let address = null;
    try {
      stage = saveStage(state.saveColors === "light");
      const file = target.view === "panels" ? saveFile(stage, target.plan) : saveViewFile(stage, target);
      address = URL.createObjectURL(new Blob([file], { type: "image/svg+xml;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = address;
      link.download = target.name;
      stage.append(link);
      link.click();
    } catch {
      problem = "view.save.failed";
    } finally {
      stage?.remove();
      if (address !== null) {
        // After the browser has taken the file.
        const taken = address;
        setTimeout(() => URL.revokeObjectURL(taken), 10000);
      }
    }
  }
  state.saveProblem = problem;
  if (problem === null) {
    state.saveOpen = false;
    state.saveNotice = saveNoticeNow();
  }
  render();
  (problem === null ? saveButton(state.saveFrom) : ui.saveGo).focus();
}

// The box out of the page that a picture is made in, in the light colors
// where they are chosen: the only element beside the root of the page that
// has data-theme (the plan of R1).
function saveStage(light) {
  const stage = element("div", "save-stage");
  stage.setAttribute("aria-hidden", "true");
  if (light) {
    stage.dataset.theme = "light";
  }
  document.body.append(stage);
  return stage;
}

// The width and the height of a chart of the page, as its view box has them.
function viewSize(svg) {
  const [, , width, height] = String(svg.getAttribute("viewBox") ?? "").split(/\s+/).map(Number);
  return [width, height];
}

// A part of the page copied into a picture as wide as its charts: the shapes
// of ``source`` (with those that match ``drop`` left out) in a frame of its
// view box, which shows what the page shows outside it too (the checker's
// R1-2). ``prepare`` may change the copy in the box first.
function savePart(svg, stage, source, top, drop, prepare = null) {
  const [width, height] = viewSize(source);
  const copy = source.cloneNode(true);
  stage.append(copy);
  if (drop !== "") {
    for (const node of copy.querySelectorAll(drop)) {
      node.remove();
    }
  }
  prepare?.(copy, width);
  const tall = (height * SAVE_ROOM) / width;
  const part = svgElement("svg", { x: SAVE_MARGIN, y: top.toFixed(1), width: SAVE_ROOM, height: tall.toFixed(1), viewBox: `0 0 ${width} ${height}`, overflow: "visible" });
  part.append(...copy.childNodes);
  copy.remove();
  svg.append(part);
  return tall;
}

// The words of a picture in lines, each piece at its place.
function saveWords(svg, lines, top, height, measure) {
  let y = top;
  for (const line of lines) {
    y += height;
    for (const piece of line) {
      let x = SAVE_MARGIN + piece.x;
      if (piece.swatch) {
        // Each piece makes its own swatch, as the page does (Codex's review
        // of the plan of R2), in its size, by the middle of the words.
        const swatch = piece.swatch();
        const [width, height] = piece.swatchSize ?? [22, 8];
        for (const [name, value] of [["x", x], ["y", y - 5 - height / 2], ["width", width], ["height", height]]) {
          swatch.setAttribute(name, String(value));
        }
        svg.append(swatch);
        x += SAVE_SWATCH;
      }
      const words = svgElement("text", { class: piece.className, x: x.toFixed(1), y });
      words.textContent = piece.text;
      svg.append(words);
    }
  }
  return y;
}

// The picture: for each panel its heading (the words of the heading of the
// page, in lines that fit), its chart copied from the page without the cross
// line, the frame of the list, and, unless they go in, the marks; the names
// of the marks on its top chart as the page places them; then the time axis
// and the line under it. Its styles are written in once it holds everything
// (Codex's review of the plan of R1).
function saveFile(stage, plan) {
  const { svg, ground, probe, measure } = saveBegin(stage);
  const answer = state.answer;
  const marks = state.saveMarks && plan.marksDrawn;
  const drop = [...SAVE_LEFT_OUT, ...(marks ? [] : SAVE_MARKS)].join(", ");
  let y = SAVE_MARGIN;
  plan.keys.forEach((key, index) => {
    const entry = drawn.find((each) => each.key === key);
    const heading = panelHeading(key, entry.item, entry.panel, answer.grain, entry.mode);
    const pieces = [
      { text: heading.name, className: "save-name" },
      { text: heading.unit, className: "save-unit" },
      ...(heading.kind === null ? [] : [{ text: heading.kind, className: "save-kind" }]),
      ...heading.keys.map((line) => ({ text: line.name, className: "save-key", swatch: () => lineSwatch(line.style, heading.points) })),
    ].filter((piece) => piece.text !== "");
    y = saveWords(svg, saveLines(pieces, SAVE_ROOM, SAVE_GAP, measure), y, SAVE_LINE, measure) + 6;
    const top = y;
    // The names of the marks are on the top chart of the page; a picture
    // whose top chart is another one writes them there (the plan of R1).
    const names =
      marks && index === 0 && key !== namedKey
        ? (copy, width) => {
            const periods = entry.periods;
            appendMarkNames(copy, markShapes(state.marks, periods[0].start, periods[periods.length - 1].end, PLOT_LEFT, width - PLOT_RIGHT), width);
          }
        : null;
    y += savePart(svg, stage, savedChart(key), top, drop, names);
    if (entry.shapes?.empty) {
      const empty = svgElement("text", { class: "save-empty", x: SAVE_WIDTH / 2, y: ((top + y) / 2).toFixed(1), "text-anchor": "middle" });
      empty.textContent = t("view.summary.none");
      svg.append(empty);
    }
    y += 10;
  });
  const axis = ui.timeAxis.querySelector(":scope > svg");
  if (axis !== null) {
    y += savePart(svg, stage, axis, y, "");
  }
  const days = saveDays(answer);
  const footer = saveFooter({
    start: days.start,
    end: days.end,
    grain: answer.grain,
    answerTypes: state.answerTypes,
    types: state.view?.types,
    version: state.productVersion,
    language: state.language,
  });
  return saveEnd(svg, ground, probe, y, footer, measure);
}

// A picture of another view (stage R2 of v2.2.0): its title line; the legend
// of a calendar; each part with the words of its head, its chart copied from
// the page without what is left out, and the words of an empty chart; the
// axis of a comparison; the lines under the chart; and the line under the
// picture, in the frame of R1 (saveEnd).
function saveViewFile(stage, target) {
  const { svg, ground, probe, measure } = saveBegin(stage);
  let y = saveWords(svg, saveLines([{ text: target.title, className: "save-title" }], SAVE_ROOM, SAVE_GAP, measure), SAVE_MARGIN, SAVE_TITLE_LINE, measure) + 8;
  if (target.legend !== null) {
    y = saveWords(svg, saveLines(target.legend.pieces, SAVE_ROOM, SAVE_GAP, measure), y, SAVE_LINE, measure) + 2;
    y = saveNotes(svg, target.legend.notes, y, measure) + 8;
  }
  for (const part of target.parts) {
    if (part.pieces.length) {
      y = saveWords(svg, saveLines(part.pieces, SAVE_ROOM, SAVE_GAP, measure), y, SAVE_LINE, measure) + 6;
    }
    const top = y;
    y += savePart(svg, stage, part.source, top, target.drop);
    if (part.empty !== null) {
      const empty = svgElement("text", { class: "save-empty", x: SAVE_WIDTH / 2, y: ((top + y) / 2).toFixed(1), "text-anchor": "middle" });
      empty.textContent = part.empty;
      svg.append(empty);
    }
    y += 10;
  }
  if (target.axis !== null) {
    y += savePart(svg, stage, target.axis, y, "");
  }
  y = saveNotes(svg, target.notes, y, measure);
  return saveEnd(svg, ground, probe, y, target.footer, measure);
}

// The lines under a chart or a legend, one note a line where it fits.
function saveNotes(svg, notes, y, measure) {
  let bottom = y;
  for (const note of notes) {
    bottom = saveWords(svg, saveLines([{ text: note, className: "save-caption" }], SAVE_ROOM, 0, measure), bottom, SAVE_FOOT_LINE, measure) + 2;
  }
  return bottom;
}

// The beginning of a picture: its element in the box, its ground, and the
// measure of its words.
function saveBegin(stage) {
  const svg = svgElement("svg", { width: SAVE_WIDTH });
  stage.append(svg);
  const ground = svgElement("rect", { class: "save-surface", x: 0, y: 0, width: SAVE_WIDTH });
  svg.append(ground);
  const probe = svgElement("text");
  svg.append(probe);
  const measure = (words, piece) => {
    probe.setAttribute("class", piece.className);
    probe.textContent = words;
    return probe.getComputedTextLength() + (piece.swatch ? SAVE_SWATCH : 0);
  };
  return { svg, ground, probe, measure };
}

// The end of a picture: the line under it, its frame, and its styles,
// written once it holds everything (Codex's review of the plan of R1).
function saveEnd(svg, ground, probe, top, footer, measure) {
  const separator = t("view.save.separator");
  const words = footer.map((piece) => describe(piece));
  const footPieces = words.map((each, index) => ({ text: index < words.length - 1 ? `${each}${separator}` : each, className: "save-footer" }));
  const y = saveWords(svg, saveLines(footPieces, SAVE_ROOM, 0, measure), top + 6, SAVE_FOOT_LINE, measure) + SAVE_MARGIN + 4;
  probe.remove();
  svg.setAttribute("height", String(Math.ceil(y)));
  svg.setAttribute("viewBox", `0 0 ${SAVE_WIDTH} ${Math.ceil(y)}`);
  // What the parts show out of their frames, measured in the box at one
  // pixel a unit, grows the frame of the picture (Codex's review of the diff
  // of R1).
  const origin = svg.getBoundingClientRect();
  const boxes = [...svg.querySelectorAll("text, path, line, circle, rect")]
    .filter((node) => node !== ground)
    .map((node) => node.getBoundingClientRect())
    .filter((box) => box.width > 0 || box.height > 0)
    .map((box) => ({ left: box.left - origin.left, top: box.top - origin.top, right: box.right - origin.left, bottom: box.bottom - origin.top }));
  const frame = saveFrame(boxes, SAVE_WIDTH, Math.ceil(y));
  svg.setAttribute("width", String(frame.width));
  svg.setAttribute("height", String(frame.height));
  svg.setAttribute("viewBox", `${frame.x} ${frame.y} ${frame.width} ${frame.height}`);
  for (const [name, value] of [["x", frame.x], ["y", frame.y], ["width", frame.width], ["height", frame.height]]) {
    ground.setAttribute(name, String(value));
  }
  writeSaveStyles(svg);
  return `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(svg)}`;
}

// The styles of the page, written into a picture once it holds everything:
// each element takes the attributes of SVG for what is computed for it in
// the box (savedAttributes), what does not show is left out, and no class or
// style stays; the font is that of the page, on the outer element.
function writeSaveStyles(svg) {
  const nodes = [svg, ...svg.querySelectorAll("*")];
  const computed = new Map(
    nodes.map((node) => {
      const style = getComputedStyle(node);
      return [node, { display: style.display, values: Object.fromEntries(SAVE_ATTRIBUTES.map(([property]) => [property, style.getPropertyValue(property)])) }];
    }),
  );
  const font = getComputedStyle(svg).fontFamily;
  for (const node of nodes) {
    const { display, values } = computed.get(node);
    if (node !== svg && display === "none") {
      node.remove();
      continue;
    }
    const around = node === svg ? null : computed.get(node.parentNode)?.values ?? null;
    const own = SAVE_ATTRIBUTES.map(([, attribute]) => attribute).filter((attribute) => node.hasAttribute(attribute));
    for (const [attribute, value] of savedAttributes(values, around, own)) {
      node.setAttribute(attribute, value);
    }
    node.removeAttribute("class");
    node.removeAttribute("style");
  }
  svg.setAttribute("font-family", font);
}

function renderMarks(viewing, live) {
  const locked = marksLocked();
  ui.marksShown.checked = state.marksShown;
  ui.marksShown.disabled = !viewing || !state.marks.length;
  ui.marksOpen.disabled = !viewing;
  ui.marksOpen.setAttribute("aria-expanded", String(state.marksOpen && viewing));
  ui.marksPop.hidden = !state.marksOpen || !viewing;
  if (ui.marksPop.hidden) {
    return;
  }
  fitMarksWindow();
  setText(ui.marksPopTitle, t("view.marks.title", { n: formatNumber(state.marks.length) }));
  if (ui.marksLegend.dataset.signature !== state.language) {
    const parts = [element("span", "", t("view.marks.legend"))];
    for (const kind of MARK_KINDS) {
      const part = element("span");
      part.append(markSwatch(kind, false), t(MARK_KIND_KEYS[kind]));
      parts.push(part);
    }
    const span = element("span");
    span.append(markSwatch("other", true), t("view.marks.span"));
    parts.push(span);
    ui.marksLegend.replaceChildren(...parts);
    ui.marksLegend.dataset.signature = state.language;
  }
  // What to tell of the file of the marks shows in the window too: why it
  // changes nothing while the file is not used, and a change not written.
  setText(ui.marksNotice, state.marksNotice === null ? "" : t(MARKS_NOTICE_KEYS[state.marksNotice]));
  renderMarksList(live, locked);
  if (ui.markKind.dataset.signature !== state.language) {
    const chosen = ui.markKind.value || MARK_KINDS[0];
    ui.markKind.replaceChildren(
      ...MARK_KINDS.map((kind) => {
        const option = element("option", "", t(MARK_KIND_KEYS[kind]));
        option.value = kind;
        return option;
      }),
    );
    ui.markKind.value = chosen;
    ui.markKind.dataset.signature = state.language;
  }
  const editing = state.marks.find((one) => one.id === state.markEditing) ?? null;
  setText(ui.markFormHeading, editing === null ? t("view.marks.add_heading") : t("view.marks.change_heading", { name: editing.name }));
  setText(ui.markSave, t(editing === null ? "view.marks.add" : "view.marks.save"));
  ui.markCancel.hidden = editing === null;
  const full = editing === null && state.marks.length >= MAX_MARKS;
  const off = !live || locked || full;
  for (const field of [ui.markDay, ui.markEnd, ui.markKind, ui.markName, ui.markSave]) {
    field.disabled = off;
  }
  ui.markCancel.disabled = !live;
  setText(ui.markProblem, state.markProblem !== null ? t(state.markProblem) : full && !locked ? t("view.marks.error.full") : "");
}

function renderMarksList(live, locked) {
  const signature = JSON.stringify([state.language, state.marks, state.markAsk, live, locked]);
  if (ui.marksList.dataset.signature === signature) {
    return;
  }
  const active = document.activeElement;
  const focused = ui.marksList.contains(active) ? { op: active.dataset.op ?? null, id: active.dataset.id ?? null } : null;
  const off = !live || locked;
  const rows = [];
  if (!state.marks.length) {
    rows.push(element("p", "marks-none", t("view.marks.none")));
  }
  for (const mark of [...state.marks].reverse()) {
    const row = element("div", "marks-item");
    const days = markDays(mark, state.language);
    const when = days.end === null ? days.day : t("view.marks.when_span", days);
    const name = element("span", "marks-name", mark.name);
    name.id = `mark-name-${mark.id}`;
    const change = opButton("change", mark.id, "view.marks.change", off);
    const remove = opButton("remove", mark.id, "view.marks.remove", off);
    for (const button of [change, remove]) {
      button.setAttribute("aria-describedby", name.id);
    }
    row.append(markSwatch(mark.kind, mark.end !== null), element("span", "marks-when", when), element("span", "marks-kind", t(MARK_KIND_KEYS[mark.kind])), name, change, remove);
    if (state.markAsk === mark.id) {
      // The question names the group of its two buttons, and each of them.
      const ask = element("div", "marks-ask");
      const question = element("p", "", t("view.marks.remove_ask", { name: mark.name, day: when }));
      question.id = `mark-ask-${mark.id}`;
      ask.setAttribute("role", "group");
      ask.setAttribute("aria-labelledby", question.id);
      const keep = opButton("keep", mark.id, "view.marks.keep", off);
      const yes = opButton("remove-yes", mark.id, "view.marks.remove", off);
      for (const button of [keep, yes]) {
        button.setAttribute("aria-describedby", question.id);
      }
      ask.append(question, keep, yes);
      row.append(ask);
    }
    rows.push(row);
  }
  ui.marksList.replaceChildren(...rows);
  ui.marksList.dataset.signature = signature;
  // The focus goes back to the same button, or to the removal of the same
  // mark when its question closed, or to the form when the mark is gone.
  if (focused !== null) {
    const buttons = [...ui.marksList.querySelectorAll("button[data-op]")];
    const again =
      buttons.find((node) => node.dataset.op === focused.op && node.dataset.id === focused.id) ??
      buttons.find((node) => node.dataset.op === "remove" && node.dataset.id === focused.id);
    if (again !== undefined) {
      again.focus();
    } else {
      focusMarkForm();
    }
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
  // A layout holds panels, which are not shown while comparing years or
  // plotting two items.
  const viewing = live && state.view !== null && state.opening === null && !apart();
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

// The words of the heading of a panel, which the page and a picture of it
// share (the checker's answer 2 of the plan of R1): its name, its unit, the
// kind of its values but on a small panel, also by day, and the keys of its
// lines where it has more than one, as lines or as points.
function panelHeading(key, item, panel, grain, mode) {
  const styles = lineStyles(panel);
  const names = lineNames(panel, state.language);
  const full = mode !== "mini";
  return {
    name: itemName(key),
    unit: t(unitKey(key)),
    kind: full ? t(kindKey(item, grain)) : null,
    keys: full && panel.lines.length > 1 ? panel.lines.map((_line, number) => ({ style: styles[number], name: describe(names[number]) })) : [],
    points: showsPoints(panel),
    styles,
    names,
  };
}

function buildPanel({ key, item, panel }, index, count, periods, grain, marksText = "") {
  const mode = panelMode(key);
  const table = state.tables.has(key) && mode !== "mini";
  const words = panelHeading(key, item, panel, grain, mode);
  const name = words.name;
  const section = element("section", `panel-view${table ? " table" : ""}${mode === "normal" ? "" : ` ${mode}`}`);
  section.dataset.key = key;
  const headingId = `panel-${key}-name`;
  section.setAttribute("aria-labelledby", headingId);
  const head = element("div", "panel-head");
  const heading = element("h3", "panel-name", name);
  heading.id = headingId;
  head.append(heading, element("span", "panel-unit", words.unit));
  const { styles, names } = words;
  if (words.kind !== null) {
    head.append(element("span", "panel-kind", words.kind));
    if (words.keys.length) {
      const keys = element("span", "panel-keys");
      for (const line of words.keys) {
        const entry = element("span", "key");
        entry.append(lineSwatch(line.style, words.points), line.name);
        keys.append(entry);
      }
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
  const compareButton = textButton(t("view.compare.button"), "compare", key);
  compareButton.setAttribute("aria-label", t("view.compare.title", { name }));
  compareButton.disabled = !compareYears(state.view?.first_day, state.view?.last_day).length;
  tools.append(compareButton);
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
    const label = t("view.chart.label", {
      name,
      start: describe(periodMessage(periods[0], grain, state.language, { mark: false })),
      end: describe(periodMessage(periods[periods.length - 1], grain, state.language, { mark: false })),
    });
    // What the chart says of the marks of its days (stage M1 of v2.2.0).
    plot.setAttribute("aria-label", marksText === "" ? label : `${label}${state.language === "ja" ? "" : " "}${marksText}`);
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
    markListable(entry, false);
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
  markListable(entry, listOpens({ item, mode: entry.mode, table: entry.table, empty: shapes.empty, loading: false }));
  // The marks of the person: their bands behind the values, their lines in
  // front, on every chart, also one without values (stage M1 of v2.2.0).
  const dayMarks = state.marksShown ? markShapes(state.marks, periods[0].start, periods[periods.length - 1].end, PLOT_LEFT, width - PLOT_RIGHT) : [];
  appendMarkBands(svg, dayMarks, height);
  if (shapes.empty) {
    appendMarkLines(svg, dayMarks, height);
    plot.replaceChildren(svg, element("span", "panel-empty", t("view.summary.none")));
    if (key === namedKey) {
      appendMarkNames(svg, dayMarks, width);
    }
    return;
  }
  appendListFrame(svg, entry, shapes, height);
  appendScale(svg, key, shapes, width - PLOT_RIGHT);
  shapes.lines.forEach((shape, number) => appendMarks(svg, shape, `c${styles[number].color}`, styles[number].dash));
  appendMarkLines(svg, dayMarks, height);
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
  if (key === namedKey) {
    appendMarkNames(svg, dayMarks, width);
  }
  Object.assign(entry, { cross, crossLine, crossDots });
}

// A chart of the activities with values opens the list of a period: the
// pointer says so, and the chart says how by the keyboard (stage M3 of
// v2.2.0).
function markListable(entry, opens) {
  entry.plot.classList.toggle("listable", opens);
  if (opens) {
    entry.plot.setAttribute("aria-describedby", "list-hint");
  } else {
    entry.plot.removeAttribute("aria-describedby");
  }
}

// The frame of the period whose activities the list shows, behind the values
// of its panel (stage M3 of v2.2.0).
function appendListFrame(svg, entry, shapes, height) {
  const list = state.list;
  const period = list !== null && list.key === entry.key ? entry.periods[list.index] : undefined;
  if (period === undefined) {
    return;
  }
  const left = shapes.scale.x(period.start);
  const right = shapes.scale.x(period.end + 1);
  svg.append(
    svgElement("rect", { class: "list-frame", x: (left - 1).toFixed(1), y: 1, width: Math.max(3, right - left + 2).toFixed(1), height: Math.max(1, height - 2), rx: 3 }),
  );
}

// The bands of the spans among the marks of a chart (markShapes).
function appendMarkBands(svg, dayMarks, height) {
  const bottom = height - PLOT_BOTTOM;
  for (const { band } of dayMarks) {
    if (band !== null) {
      svg.append(svgElement("rect", { class: "day-band", x: band.from.toFixed(1), y: PLOT_TOP, width: band.width.toFixed(1), height: Math.max(1, bottom - PLOT_TOP) }));
    }
  }
}

// The lines of the marks of a chart in the forms of their kinds: one for a
// mark of one day, and the edges of a span that are its own start and end.
function appendMarkLines(svg, dayMarks, height) {
  const bottom = height - PLOT_BOTTOM;
  const line = (kind, x) => svgElement("line", { class: `day-mark ${kind}`, x1: x.toFixed(1), x2: x.toFixed(1), y1: PLOT_TOP, y2: bottom });
  for (const { mark, x, band } of dayMarks) {
    if (band === null) {
      svg.append(line(mark.kind, x));
      continue;
    }
    if (band.starts) {
      svg.append(line(mark.kind, x));
    }
    if (band.ends) {
      svg.append(line(mark.kind, band.end));
    }
  }
}

// The names of the marks on the top chart, as markLabels places them: the
// names that would meet show how many marks they are instead. The chart is in
// the page, so that the names can be measured.
function appendMarkNames(svg, dayMarks, width) {
  if (!dayMarks.length) {
    return;
  }
  const probe = svgElement("text", { class: "day-mark-name" });
  svg.append(probe);
  const measure = (text) => {
    probe.textContent = text;
    return probe.getComputedTextLength();
  };
  const groups = markLabels(dayMarks, measure, (n) => t("view.marks.crowded", { n: formatNumber(n) }), PLOT_LEFT, width - PLOT_RIGHT);
  probe.remove();
  for (const group of groups) {
    const race = group.marks.length === 1 && group.marks[0].kind === "race";
    const name = svgElement("text", { class: `day-mark-name${race ? " race" : ""}`, x: group.x.toFixed(1), y: PLOT_TOP + 10 });
    name.textContent = group.text;
    svg.append(name);
  }
}

// What the label of a chart says of the marks of its days: the top chart
// their number, and the names and days of the first ones; the others their
// number only.
function marksSpoken(marks, named) {
  if (!marks.length) {
    return "";
  }
  const spoken = spokenMarks(marks);
  if (!named) {
    return t("view.marks.spoken_count", { n: formatNumber(spoken.count) });
  }
  const names = spoken.named.map((mark) => {
    const days = markDays(mark, state.language);
    return days.end === null
      ? t("view.marks.spoken_mark", { name: mark.name, day: days.day })
      : t("view.marks.spoken_span", { name: mark.name, day: days.day, end: days.end });
  });
  if (spoken.more > 0) {
    names.push(t("view.marks.spoken_more", { n: formatNumber(spoken.more) }));
  }
  return t("view.marks.spoken", { n: formatNumber(spoken.count), names: names.join(t("view.spoken_separator")) });
}

// The ticks of the values of a chart, with its grid up to ``right``, and the
// baseline of a total.
function appendScale(svg, key, shapes, right) {
  const step = shapes.ticks.length > 1 ? Math.abs(shapes.ticks[1].value - shapes.ticks[0].value) : 1;
  for (const tick of shapes.ticks) {
    svg.append(svgElement("line", { class: "chart-grid", x1: PLOT_LEFT, x2: right, y1: tick.y.toFixed(1), y2: tick.y.toFixed(1) }));
    const label = svgElement("text", { class: "chart-tick", x: PLOT_LEFT - 8, y: (tick.y + 4).toFixed(1), "text-anchor": "end" });
    label.textContent = tickText(key, tick.value, step, state.language);
    svg.append(label);
  }
  if (shapes.base !== null) {
    svg.append(svgElement("line", { class: "chart-base", x1: PLOT_LEFT, x2: right, y1: shapes.base.toFixed(1), y2: shapes.base.toFixed(1) }));
  }
}

// The marks of one line of a chart in its color and its dash: its bars (those
// of the periods cut lighter, and with an edge where they are ``outlined``),
// its line (wider for the ``newest`` year compared), its points, and its dots
// of 0.
function appendMarks(svg, shape, color, dash, { outlined = false, newest = false } = {}) {
  if (shape.bars !== null) {
    if (shape.bars.full) {
      svg.append(svgElement("path", { class: `chart-bar ${color}`, d: shape.bars.full }));
    }
    if (shape.bars.partial) {
      svg.append(svgElement("path", { class: `chart-bar ${color} partial${outlined ? " outlined" : ""}`, d: shape.bars.partial }));
    }
  }
  if (shape.line) {
    svg.append(svgElement("path", { class: `chart-line ${color}${newest ? " newest" : ""}`, d: shape.line, "stroke-dasharray": dash }));
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

function drawTimeAxis(start, end, width, place = ui.timeAxis) {
  place.replaceChildren();
  if (width < 60) {
    return;
  }
  const height = place.clientHeight || 24;
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, "aria-hidden": "true", focusable: "false" });
  const scale = timeScale(start, end, PLOT_LEFT, width - PLOT_RIGHT);
  for (const tick of timeTicks(start, end, width - PLOT_LEFT - PLOT_RIGHT)) {
    const x = scale.x(tick.day);
    svg.append(svgElement("line", { class: "axis-tick", x1: x.toFixed(1), x2: x.toFixed(1), y1: 0, y2: 5 }));
    const label = svgElement("text", { class: "axis-text", x: (x + 3).toFixed(1), y: 16 });
    label.textContent = timeTickText(tick, state.language);
    svg.append(label);
  }
  place.append(svg);
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
  // The marks of the person over the whole output, a short line at the top
  // each, whatever the period (stage M1 of v2.2.0).
  if (state.marksShown) {
    for (const shape of markShapes(state.marks, shapes.first, shapes.last, 0, width)) {
      const x = shape.x.toFixed(1);
      svg.append(svgElement("line", { class: "overview-day-mark", x1: x, x2: x, y1: 0, y2: 10 }));
    }
  }
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
    state.marksSeq,
    state.marksShown,
  ]);
}

// The overview is drawn again when its numbers, the period, or its width
// change.
let overviewSignature = null;

function renderOverview(force = false) {
  const answer = state.answer;
  const chartWidth = drawn.find((entry) => entry.plot)?.plot.clientWidth ?? 0;
  const signature = JSON.stringify([state.overview?.signature ?? null, answer?.start ?? null, answer?.end ?? null, chartWidth, ui.overview.clientHeight, state.marksSeq, state.marksShown]);
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
    closeList();
    ui.panels.replaceChildren();
    ui.timeAxis.replaceChildren();
    delete ui.timeAxis.dataset.width;
    drawn = [];
    drawnSignature = signature;
    return;
  }
  const periods = periodDays(answer.periods);
  // The top chart names the marks; a panel shown as a table has no chart.
  const charts = shownList.filter((entry) => !(state.tables.has(entry.key) && panelMode(entry.key) !== "mini"));
  namedKey = (charts.find((entry) => panelMode(entry.key) !== "mini") ?? charts[0])?.key ?? null;
  const marksNow = state.marksShown ? marksWithin(state.marks, isoDate(periods[0].start), isoDate(periods[periods.length - 1].end)) : [];
  const built = shownList.map((entry) =>
    buildPanel(entry, state.items.indexOf(entry.key), state.items.length, answer.periods, answer.grain, marksSpoken(marksNow, entry.key === namedKey)),
  );
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
  // The list goes with its panel, drawn again (stage M3 of v2.2.0).
  renderList();
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
  // A part of the list, which goes with its panel (stage M3 of v2.2.0).
  if (listBox?.contains(active)) {
    return { list: active.dataset.listFocus ?? "title" };
  }
  return { action: active.dataset.action ?? null, key: active.dataset.key ?? active.closest("[data-key]")?.dataset.key ?? null, plot: active.classList.contains("plot"), table: active.classList.contains("panel-table") };
}

function restoreFocus(mark) {
  if (mark === null) {
    return;
  }
  if (mark.list !== undefined) {
    (listBox?.querySelector(`[data-list-focus="${mark.list}"]`) ?? listBox?.querySelector(".list-title"))?.focus({ preventScroll: true });
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
    if (!ui.compare.hidden && !ui.compareStack.hidden && state.compareAnswer !== null) {
      renderCompareBody();
    }
    if (!ui.plot.hidden) {
      renderPlotBody(plotAnswerNow());
    }
    if (!ui.spread.hidden) {
      renderSpreadBody(spreadAnswerNow());
    }
    if (!ui.shoes.hidden) {
      renderShoesBody(state.shoesAnswer);
    }
    // The window of the saving reads the charts drawn again, while it shows
    // only, so that the focus stays where it is (Codex's review of the plan
    // of R2 and the checker's review of its handling).
    if (state.saveOpen) {
      renderSave(viewingNow());
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
  } else if ((event.key === "Enter" || event.key === " ") && event.target.classList.contains("listable")) {
    // The list of the period of the cross line (stage M3 of v2.2.0).
    openList(event.target.dataset.key, state.cursor ?? (state.answer?.periods.length ?? 1) - 1, true);
  } else if (event.key === "Escape" && state.list !== null && event.target.dataset.key === state.list.key) {
    closeList(true);
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

// A click on a chart of the activities opens the list of the period nearest
// to it; the focus stays on the chart, whose keys move the cross line still
// (stage M3 of v2.2.0).
function plotClick(event, plot) {
  const entry = drawn.find((candidate) => candidate.plot === plot);
  if (!entry || entry.shapes === null || entry.shapes.empty || !plot.classList.contains("listable")) {
    return;
  }
  const box = plot.getBoundingClientRect();
  const index = nearestPeriod(entry.periods, entry.shapes.scale, event.clientX - box.left);
  if (index !== null) {
    openList(entry.key, index, false);
  }
}

// --- The list of the activities of a period (stage M3 of v2.2.0) ----------

// The list as it shows, under the panel of its item; one at a time.
let listBox = null;

// A change of the page that closes the list (view_flow.mjs listAfter).
function listChanged(change) {
  if (state.list !== null && listAfter(state.list, change) === null) {
    closeList();
  }
}

// Draw a chart again, with the frame of the period of the list or without it,
// and its cross line.
function drawAgain(key) {
  const entry = drawn.find((candidate) => candidate.key === key);
  if (entry !== undefined && entry.plot !== null) {
    drawChart(entry);
  }
}

// Open the list of a period of a panel: the cross line goes to the period,
// whose frame the chart draws while the list is open, and moves as before;
// another period of the same panel keeps the order of the list. The heading
// of the list comes into view, the chart staying where it can; the focus
// goes to the heading by the keyboard, and stays on the chart by a pointer.
function openList(key, index, byKey) {
  const entry = drawn.find((candidate) => candidate.key === key);
  const period = state.answer?.periods[index];
  if (
    entry === undefined ||
    period === undefined ||
    !listOpens({ item: entry.item, mode: entry.mode, table: entry.table, empty: entry.shapes === null || entry.shapes.empty, loading: state.loading })
  ) {
    return;
  }
  const before = state.list;
  if (before !== null && before.key === key && before.index === index) {
    if (byKey) {
      focusList();
    }
    return;
  }
  state.list = {
    key,
    index,
    start: period.start,
    end: period.end,
    grain: state.answer.grain,
    types: state.answerTypes,
    sort: before !== null && before.key === key ? before.sort : { column: "when", descending: false },
    answer: null,
    stop: null,
  };
  if (before !== null && before.key !== key) {
    drawAgain(before.key);
  }
  drawAgain(key);
  moveCross(index, false);
  renderList();
  listBox?.querySelector(".list-title")?.scrollIntoView({ block: "nearest" });
  if (byKey) {
    focusList();
  }
  requestList();
}

function focusList() {
  listBox?.querySelector(".list-title")?.focus({ preventScroll: true });
}

// Close the list; an answer on its way is dropped. Closed by the person, the
// focus goes back to the chart of its panel, and the cross line to its period.
function closeList(byPerson = false) {
  const list = state.list;
  if (list === null) {
    return;
  }
  state.list = null;
  state.listSeq += 1;
  listBox?.remove();
  listBox = null;
  drawAgain(list.key);
  moveCross(byPerson ? list.index : state.cursor, false);
  if (byPerson) {
    drawn.find((entry) => entry.key === list.key)?.plot?.focus();
  }
}

function sortList(column) {
  if (state.list === null || !Array.isArray(state.list.answer?.rows)) {
    return;
  }
  state.list.sort = listSorted(state.list.sort, column);
  renderList({ top: true });
}

// Ask for the activities of the period of the list, for the activity types of
// the answer that drew its panel; only the answer of its last request is
// shown. A ticket that the server no longer keeps opens the output again,
// once, as for the numbers.
async function requestList(again = true) {
  const list = state.list;
  if (list === null || state.view === null) {
    return;
  }
  const seq = ++state.listSeq;
  try {
    const answer = await callApi("/api/view/activities", {
      view: state.view.view,
      item: list.key,
      period: { from: list.start, to: list.end },
      types: list.types,
    });
    if (seq !== state.listSeq) {
      return;
    }
    list.answer = answer;
    // What the list has, said once it is there, with its period, so that
    // another period of as many activities is said too (Codex's review of
    // the diff of M3).
    listSay(list, describe(listFrom(list.key, answer.total, state.language)));
  } catch (error) {
    if (seq !== state.listSeq) {
      return;
    }
    if (connectionFailure(error)) {
      list.stop = { code: null, detail: null };
      listSay(list, t("view.list.failed"));
      render();
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null && (await reopen())) {
      if (seq === state.listSeq) {
        requestList(false);
      }
      return;
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
      state.stop = { code: error.code, detail: error.detail };
      render();
      return;
    } else if (seq === state.listSeq) {
      list.stop = { code: error.code, detail: error.detail };
      listSay(list, t("view.list.failed"));
    }
  }
  if (seq === state.listSeq) {
    renderList();
  }
}

// Say what a list has, after its heading.
function listSay(list, text) {
  setText(ui.listAnnouncer, t("view.list.spoken", { title: describe(listTitle(state.answer.periods[list.index], list.grain, state.language)), text }));
}

// The list under the panel of its item: its heading, with the panel that it
// is of, its rows in their order under heads that order them, and the value
// of the panel under them. It follows the language, and goes with its panel
// when the panels are drawn again; the focus stays where it was in it.
function renderList({ top = false } = {}) {
  const list = state.list;
  const entry = list === null ? undefined : drawn.find((candidate) => candidate.key === list.key);
  if (entry === undefined || state.answer === null) {
    return;
  }
  const focused = listBox?.contains(document.activeElement) ? document.activeElement.dataset.listFocus ?? "title" : null;
  // The table keeps where it was scrolled to, sideways too, so that the head
  // that was pressed stays in view (Codex's review of the diff of M3); a new
  // order starts at its top.
  const before = listBox?.querySelector(".list-table");
  const scrolled = { top: top ? 0 : before?.scrollTop ?? 0, left: before?.scrollLeft ?? 0 };
  if (listBox === null) {
    listBox = element("section", "activity-list");
    listBox.setAttribute("aria-labelledby", "list-title");
  }
  const titleText = describe(listTitle(state.answer.periods[list.index], list.grain, state.language));
  const head = element("div", "panel-head");
  const title = element("h3", "panel-name list-title", titleText);
  title.id = "list-title";
  title.tabIndex = -1;
  title.dataset.listFocus = "title";
  head.append(title);
  const answer = list.stop === null ? list.answer : null;
  if (answer !== null) {
    head.append(element("span", "panel-unit", describe(listFrom(list.key, answer.total, state.language))));
  }
  const tools = element("span", "panel-tools");
  const close = textButton(t("view.list.close"), "list-close", list.key);
  close.dataset.listFocus = "close";
  tools.append(close);
  head.append(tools);
  const parts = [head];
  if (list.stop !== null) {
    parts.push(listStop(list.stop));
  } else if (answer === null) {
    parts.push(element("p", "list-note", t("view.loading")));
  } else if (answer.total === 0) {
    parts.push(element("p", "list-note", t("view.list.none")));
  } else if (answer.rows === null) {
    parts.push(element("p", "list-note", describe(listLimitMessage(answer.total, answer.limit, list.grain, state.language))));
  } else {
    parts.push(buildListTable(list, answer.rows, titleText));
  }
  if (answer !== null) {
    const line = element("p", "list-value");
    line.append(...richNodes(listValueLine(list.key, answer.value, state.language)));
    if (answer.rows !== null && answer.total > 0) {
      line.append(" ", element("span", "list-sort-note", t("view.list.sort_note")));
    }
    parts.push(line);
  }
  listBox.replaceChildren(...parts);
  if (entry.section.nextElementSibling !== listBox) {
    entry.section.after(listBox);
  }
  const table = listBox.querySelector(".list-table");
  if (table !== null) {
    table.scrollTop = scrolled.top;
    table.scrollLeft = scrolled.left;
  }
  if (focused !== null) {
    (listBox.querySelector(`[data-list-focus="${focused}"]`) ?? title).focus({ preventScroll: true });
  }
}

// The table of the list: a head for each column, which orders the rows by
// it, and the rows in that order, each named by its date and time; a value
// that an activity does not have shows a dash and says so.
function buildListTable(list, rows, titleText) {
  const wrap = element("div", "list-table");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-labelledby", "list-title");
  const table = element("table", "t");
  const caption = element("caption", "visually-hidden", titleText);
  const head = element("thead");
  const headRow = element("tr");
  const columns = listColumns(list.key);
  for (const column of columns) {
    const cell = element("th", column === "when" || column === "type" ? "" : "n");
    cell.scope = "col";
    const button = element("button", "list-sort", describe(listHead(column)));
    button.type = "button";
    button.dataset.action = "list-sort";
    button.dataset.column = column;
    button.dataset.listFocus = `sort-${column}`;
    if (list.sort.column === column) {
      cell.setAttribute("aria-sort", list.sort.descending ? "descending" : "ascending");
      const arrow = element("span", "list-arrow", list.sort.descending ? "\u25bc" : "\u25b2");
      arrow.setAttribute("aria-hidden", "true");
      button.append(arrow);
    }
    cell.append(button);
    headRow.append(cell);
  }
  head.append(headRow);
  const body = element("tbody");
  const typeName = (name) => describe(typeMessage(name));
  for (const row of sortedListRows(rows, list.sort, typeName, state.language)) {
    const line = element("tr");
    for (const column of columns) {
      const text =
        column === "when"
          ? describe(listWhen(row.datetime, state.language)) || null
          : column === "type"
            ? typeName(row.type)
            : listValueText(column, row.values?.[column], state.language);
      const cell = element(column === "when" ? "th" : "td", column === "when" || column === "type" ? "" : "n");
      if (column === "when") {
        cell.scope = "row";
      }
      if (text === null) {
        cell.classList.add("empty");
        const dash = element("span", "", "\u2014");
        dash.setAttribute("aria-hidden", "true");
        cell.append(dash, element("span", "visually-hidden", t("view.no_value")));
      } else {
        cell.textContent = text;
      }
      line.append(cell);
    }
    body.append(line);
  }
  table.append(caption, head, body);
  wrap.append(table);
  return wrap;
}

// What the list says when it could not be read: that it could not, and the
// words of the code of the server, with the code to quote.
function listStop(stop) {
  const box = element("div", "list-note");
  box.append(element("p", "", t("view.list.failed")));
  if (stop.code !== null) {
    const words = stopBox(stop.code, stop.detail, state.productVersion);
    for (const line of words.lines) {
      box.append(element("p", "", describe(line)));
    }
    if (words.code !== null) {
      box.append(element("p", "stop-code", describe(words.code)));
    }
  }
  return box;
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

// --- Comparing one item by year (stage L1 of v2.2.0) -----------------------

// What a comparison draws now (its item, its years, its axis), and its plots
// as they are drawn: for each, its years, its chart, and its readings, which
// the cross line moves.
let compareContext = null;
let compared = [];
let comparedSignature = null;

function comparing() {
  return state.compare !== null && state.view !== null;
}

function compareItem() {
  return itemsByKey(state.view?.items).get(state.compare?.key) ?? null;
}

// How the item is compared: the way remembered, or one row per year for an
// item that does not add up (the way remembered stays as it is); a calendar
// compares years only, so that by race day it is one row per race (stage N1
// of v2.2.0; a running total by race day stays as it is).
function compareModeOf(item) {
  const mode = compareModeFor(item, state.compareMode);
  return mode === "calendar" && compareByNow() === "race" ? "rows" : mode;
}

function compareModeNow() {
  return compareModeOf(compareItem());
}

// The month that the comparison uses now: none for a calendar, which shows
// whole years; the month remembered stays as it is (Codex's review of the
// plan of N1).
function compareMonthNow() {
  return compareMonthFor(compareModeNow(), state.compareMonth);
}

// The races that a comparison offers: the race marks whose longest span
// meets the days of the output (stage M2 of v2.2.0).
function raceChoices() {
  return state.view === null ? [] : compareRaces(state.marks, state.view.first_day, state.view.last_day);
}

// What the item is compared by now: the race days only with two races
// offered at least; the choice of the person stays as it is.
function compareByNow() {
  return compareByFor(state.compareBy, raceChoices());
}

// The grouping of a comparison after what it is compared by may have
// changed (from ``before``): the first one of its way where it changed, or
// where the grouping is not one that it takes; otherwise as it is.
function settleCompareGrain(before) {
  const by = compareByNow();
  if (by !== before || !compareGrainsFor(by, compareMonthNow(), compareModeNow()).includes(state.compare.grain)) {
    state.compare.grain = compareGrainFor(by, compareModeNow(), compareMonthNow());
    state.compare.cursor = null;
  }
}

// The comparison of one item, from its panel: the newest years of the output
// and the first grouping of the way and the month. The panels, the period,
// and the grouping of the page stay as they are, for the way back.
function enterCompare(key) {
  const item = itemsByKey(state.view?.items).get(key);
  if (state.view === null || item === undefined || !compareYears(state.view.first_day, state.view.last_day).length) {
    return;
  }
  const mode = compareModeOf(item);
  state.compare = {
    key,
    years: firstCompareYears(compareYears(state.view.first_day, state.view.last_day)),
    // The races chosen, newest first (stage M2 of v2.2.0).
    races: firstCompareRaces(raceChoices()),
    grain: compareGrainFor(compareByNow(), mode, compareMonthFor(mode, state.compareMonth)),
    series: null,
    table: false,
    about: false,
    calendarAbout: false,
    cursor: null,
    cursorAxis: null,
    // The year (or the race) stood out on one panel, never remembered
    // (stage L3 of v2.2.0).
    lit: null,
  };
  state.compareAnswer = null;
  state.compareStop = null;
  state.typesOpen = false;
  state.pickerOpen = false;
  state.notesOpen = null;
  state.layoutsOpen = false;
  state.layoutSaving = false;
  state.railLayoutsOpen = false;
  render();
  ui.compareItem.focus();
  requestCompare();
}

// Back to the panels as they were; answers on their way are dropped.
function leaveCompare() {
  const key = state.compare?.key ?? null;
  state.compare = null;
  state.compareAnswer = null;
  state.compareStop = null;
  state.compareLoading = false;
  state.compareSeq += 1;
  render();
  (ui.panels.querySelector(`button[data-action="compare"][data-key="${key}"]`) ?? ui.panels.querySelector('button[data-action="compare"]') ?? ui.outputSelect).focus();
}

// Ask for the numbers of a comparison as one generation: the value of every
// year (or month) of the output, which also names the lines of an item of
// several, and the periods of each year chosen; by race day (stage M2 of
// v2.2.0), the weeks of each race chosen that is still offered and the value
// of its whole span. Answers of an older generation are dropped when they
// come, and a stop of one of them stops the generation; a ticket that the
// server no longer keeps opens the output again, once.
async function requestCompare(again = true) {
  const compare = state.compare;
  if (compare === null || state.view === null) {
    return;
  }
  const seq = ++state.compareSeq;
  const by = compareByNow();
  const choices = raceChoices();
  // The activity types asked for, kept with the answer of this generation,
  // which the line under a picture says (Codex's review of the plan of R2).
  const types = typesRequest(state.counted, state.view.types);
  compare.races = racesKept(compare.races, choices);
  // Its grouping, where what it compares by changed by another way (an
  // output opened again for a new ticket).
  settleCompareGrain(by);
  const races = by === "race" ? choices.filter((race) => compare.races.includes(race.id)) : [];
  const weeks = state.compareWeeks;
  const { key, grain } = compare;
  const month = compareMonthNow();
  const years = [...compare.years];
  const payloads =
    by === "race"
      ? races.flatMap((race) => [seriesPayload([key], raceRange(race.day, weeks), "week"), seriesPayload([key], raceRange(race.day, weeks), RANGE_GRAIN)])
      : years.map((year) => seriesPayload([key], compareRange(year, month), grain));
  // What this generation asks for, which the marks that change are compared
  // with (followMarks).
  compare.asked = { by, races: races.map((race) => ({ id: race.id, day: race.day, name: race.name })) };
  state.compareLoading = true;
  render();
  try {
    const [whole, ...answers] = await Promise.all([
      callApi("/api/view/series", seriesPayload([key], "all", by === "race" ? "year" : compareValueGrain(month))),
      ...payloads.map((payload) => callApi("/api/view/series", payload)),
    ]);
    if (seq !== state.compareSeq) {
      return;
    }
    const panel = whole.panels?.[0] ?? null;
    if (!compareSeriesChoices(panel, state.language).some((choice) => choice.key === compare.series)) {
      compare.series = firstCompareSeries(panel);
    }
    state.compareAnswer =
      by === "race"
        ? {
            seq,
            key,
            by,
            weeks,
            month: null,
            grain: "week",
            years: [],
            races,
            whole,
            answers: new Map(races.map((race, index) => [race.id, answers[2 * index]])),
            wholes: new Map(races.map((race, index) => [race.id, answers[2 * index + 1]])),
            types,
          }
        : { seq, key, by, weeks: null, month, grain, years, races: [], whole, answers: new Map(years.map((year, index) => [year, answers[index]])), wholes: null, types };
    state.compareStop = null;
  } catch (error) {
    if (seq !== state.compareSeq) {
      return;
    }
    if (connectionFailure(error)) {
      // The bar says so.
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null) {
      if (await reopen()) {
        if (seq !== state.compareSeq) {
          return;
        }
        state.compareLoading = false;
        requestCompare(false);
        return;
      }
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
      state.stop = { code: error.code, detail: error.detail };
    } else {
      state.compareStop = { code: error.code, detail: error.detail };
    }
  }
  if (seq === state.compareSeq) {
    state.compareLoading = false;
  }
  render();
}

// Another item: its own lines, and the first grouping where the way changes
// with it (a running total of an item that does not add up).
function chooseCompareItem() {
  const key = ui.compareItem.value;
  if (!comparing() || key === state.compare.key || !itemsByKey(state.view.items).has(key)) {
    return;
  }
  const before = compareModeNow();
  Object.assign(state.compare, { key, series: null, about: false, calendarAbout: false });
  const mode = compareModeNow();
  if (mode !== before) {
    state.compare.grain = compareGrainFor(compareByNow(), mode, compareMonthNow());
    state.compare.cursor = null;
  }
  requestCompare();
}

// A way chosen, which is remembered: new numbers only where its first
// grouping, or the month that it uses (none for a calendar), is another.
function chooseCompareMode(mode) {
  if (!comparing() || !COMPARE_MODES.includes(mode) || compareModeFor(compareItem(), mode) !== mode) {
    return;
  }
  if (mode === "calendar" && compareByNow() === "race") {
    return;
  }
  const month = compareMonthNow();
  state.compareMode = mode;
  rememberItems(true);
  // By race day, by week whatever the way (Codex's review of the plan of M2).
  const grain = compareGrainFor(compareByNow(), compareModeNow(), compareMonthNow());
  if (!compareAsksAgain({ grain: state.compare.grain, month }, { grain, month: compareMonthNow() })) {
    render();
    return;
  }
  state.compare.grain = grain;
  state.compare.cursor = null;
  requestCompare();
}

// A month chosen (or the whole year), which is remembered, with the first
// grouping of the way over it.
function chooseCompareMonth() {
  if (!comparing()) {
    return;
  }
  const month = Number(ui.compareMonth.value);
  state.compareMonth = Number.isInteger(month) && month >= 1 && month <= 12 ? month : null;
  state.compare.grain = compareGrainFor(compareByNow(), compareModeNow(), compareMonthNow());
  state.compare.cursor = null;
  rememberItems(true);
  requestCompare();
}

function toggleCompareYear(year) {
  if (!comparing()) {
    return;
  }
  const years = toggledYears(state.compare.years, year);
  if (years !== state.compare.years) {
    state.compare.years = years;
    requestCompare();
  }
}

// What the item is compared by, which is remembered: the race days with two
// races offered at least, by week; the years with the first grouping of the
// way (stage M2 of v2.2.0).
function chooseCompareBy(by) {
  if (!comparing() || !COMPARE_BYS.includes(by) || (by === "race" && compareByFor(by, raceChoices()) !== "race")) {
    return;
  }
  const before = compareByNow();
  state.compareBy = by;
  rememberItems(true);
  if (compareByNow() === before) {
    render();
    return;
  }
  state.compare.races = racesKept(state.compare.races, raceChoices());
  settleCompareGrain(before);
  requestCompare();
}

// The weeks before a race day, which are remembered.
function chooseCompareWeeks() {
  const weeks = Number(ui.compareWeeks.value);
  if (!comparing() || !COMPARE_WEEKS.includes(weeks) || weeks === state.compareWeeks) {
    return;
  }
  state.compareWeeks = weeks;
  state.compare.cursor = null;
  rememberItems(true);
  requestCompare();
}

function toggleCompareRace(id) {
  if (!comparing()) {
    return;
  }
  const races = toggledRaces(state.compare.races, id, raceChoices());
  if (races !== state.compare.races) {
    state.compare.races = races;
    requestCompare();
  }
}

// The bar of the comparison, its stop, and the years.
function renderCompare(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const compare = viewing && comparing() ? state.compare : null;
  ui.compare.hidden = compare === null;
  if (compare === null) {
    compareContext = null;
    compared = [];
    comparedSignature = null;
    return;
  }
  const item = compareItem();
  const total = item !== null && totalItem(item);
  const mode = compareModeNow();
  // The title, with the list of the items and the buttons of what it is
  // compared by where each language puts them (stage M2 of v2.2.0).
  const [before = "", rest = ""] = t("view.compare.title_by", { item: "\u0001", by: "\u0002" }).split("\u0001");
  const [middle = "", after = ""] = rest.split("\u0002");
  setText(ui.compareBefore, before);
  setText(ui.compareMiddle, middle);
  setText(ui.compareAfter, after);
  renderCompareItems();
  const by = compareByNow();
  const race = by === "race";
  const offered = compareByFor("race", raceChoices()) === "race";
  for (const button of ui.compareBys) {
    button.disabled = button.dataset.compareBy === "race" && !offered;
    button.setAttribute("aria-pressed", String(button.dataset.compareBy === by));
  }
  ui.compareRaceNeeded.hidden = offered;
  // One row per race, by race day.
  ui.compareRowsYear.hidden = race;
  ui.compareRowsRace.hidden = !race;
  // A calendar of an item of one value a day, by year (stage N1 of v2.2.0).
  const calendar = item !== null && calendarItem(item);
  for (const button of ui.compareModes) {
    const way = button.dataset.compareMode;
    button.disabled = (way === "cumulative" && !total) || (way === "calendar" && (!calendar || race));
    button.setAttribute("aria-pressed", String(way === mode));
  }
  ui.compareAbout.hidden = total;
  ui.compareAbout.setAttribute("aria-expanded", String(compare.about && !ui.compareAbout.hidden));
  ui.compareAboutText.hidden = !compare.about || ui.compareAbout.hidden;
  ui.compareCalendarAbout.hidden = calendar;
  ui.compareCalendarAbout.setAttribute("aria-expanded", String(compare.calendarAbout && !ui.compareCalendarAbout.hidden));
  ui.compareCalendarAboutText.hidden = !compare.calendarAbout || ui.compareCalendarAbout.hidden;
  // By race day, its weeks in the place of the month, and its races in the
  // place of the years.
  ui.compareMonthField.hidden = race;
  ui.compareWeeksField.hidden = !race;
  renderCompareMonths();
  // A calendar shows whole years; the month remembered stays as it is.
  ui.compareMonth.disabled = mode === "calendar";
  renderCompareWeeks();
  renderCompareSeries();
  ui.compareTable.setAttribute("aria-pressed", String(compare.table));
  ui.compareTableChart.hidden = !compare.table || mode === "calendar";
  ui.compareTableCalendar.hidden = !compare.table || mode !== "calendar";
  ui.compareTableTable.hidden = compare.table;
  for (const node of [ui.compareYearsLabel, ui.compareYears, ui.compareUpTo]) {
    node.hidden = race;
  }
  for (const node of [ui.compareRacesLabel, ui.compareRaces, ui.compareRacesUpTo]) {
    node.hidden = !race;
  }
  if (race) {
    renderCompareRaces();
  } else {
    renderCompareYears();
  }
  setText(ui.compareLoading, state.compareLoading ? t("view.loading") : "");
  ui.compareStop.hidden = state.compareStop === null;
  if (!ui.compareStop.hidden) {
    renderStop(ui.compareStop, null, ui.compareStopLines, ui.compareStopCode, compareStopBox(state.compareStop.code, state.compareStop.detail, state.productVersion, compareMonthNow()));
  }
  // A calendar only from an answer of whole years by day (stage N1 of v2.2.0).
  const ready = state.compareAnswer !== null && state.compareAnswer.key === compare.key && state.compareStop === null && (mode !== "calendar" || calendarAnswer(state.compareAnswer));
  ui.compareStack.hidden = !ready;
  ui.compareStack.classList.toggle("waiting", state.compareLoading);
  ui.compareNote.hidden = !ready || !compare.table;
  ui.compareLegend.hidden = !ready || compare.table || mode !== "calendar";
  if (ready) {
    renderCompareBody();
  } else {
    compareContext = null;
    compared = [];
    comparedSignature = null;
  }
}

// The items of the output in the list of the bar, by the groups of the shelf.
function renderCompareItems() {
  const items = state.view?.items ?? [];
  const signature = JSON.stringify([state.view?.view ?? null, items.map((item) => item.key), state.language]);
  if (ui.compareItem.dataset.signature !== signature) {
    const groups = GROUPS.map((group) => {
      const node = element("optgroup");
      node.label = t(groupKey(group));
      for (const item of items.filter((entry) => entry.group === group)) {
        const option = element("option", "", itemName(item.key));
        option.value = item.key;
        node.append(option);
      }
      return node;
    }).filter((node) => node.children.length > 0);
    ui.compareItem.replaceChildren(...groups);
    ui.compareItem.dataset.signature = signature;
  }
  ui.compareItem.value = state.compare.key;
}

function renderCompareMonths() {
  if (ui.compareMonth.dataset.signature !== state.language) {
    const whole = element("option", "", t("view.compare.month_all"));
    whole.value = "";
    const months = Array.from({ length: 12 }, (_none, index) => {
      const option = element("option", "", describe(compareSlotName(index, "month", null, state.language)));
      option.value = String(index + 1);
      return option;
    });
    ui.compareMonth.replaceChildren(whole, ...months);
    ui.compareMonth.dataset.signature = state.language;
  }
  ui.compareMonth.value = state.compareMonth === null ? "" : String(state.compareMonth);
}

// The weeks before a race day, each from its first week to the race day.
function renderCompareWeeks() {
  if (ui.compareWeeks.dataset.signature !== state.language) {
    ui.compareWeeks.replaceChildren(
      ...COMPARE_WEEKS.map((weeks) => {
        const option = element("option", "", t("view.compare.weeks_option", { n: weeks }));
        option.value = String(weeks);
        return option;
      }),
    );
    ui.compareWeeks.dataset.signature = state.language;
  }
  ui.compareWeeks.value = String(state.compareWeeks);
}

// The lines of an item of several (VO2 Max), one of which is compared, by the
// names of the legend of its panel; no list for an item of one line.
function renderCompareSeries() {
  const answer = state.compareAnswer;
  const panel = answer !== null && answer.key === state.compare.key ? (answer.whole.panels?.[0] ?? null) : null;
  const choices = compareSeriesChoices(panel, state.language);
  ui.compareSeriesField.hidden = choices.length < 2;
  const signature = JSON.stringify([choices.map((choice) => choice.key), state.language]);
  if (ui.compareSeries.dataset.signature !== signature) {
    ui.compareSeries.replaceChildren(
      ...choices.map((choice) => {
        const option = element("option", "", describe(choice.name));
        option.value = choice.key;
        return option;
      }),
    );
    ui.compareSeries.dataset.signature = signature;
  }
  if (choices.some((choice) => choice.key === state.compare.series)) {
    ui.compareSeries.value = state.compare.series;
  }
}

// The years of the output, a pressed button each that is chosen: one at
// least, and up to six.
function renderCompareYears() {
  const years = compareYears(state.view.first_day, state.view.last_day).map((entry) => entry.year);
  const chosen = state.compare.years;
  const signature = JSON.stringify([years, chosen]);
  if (ui.compareYears.dataset.signature === signature) {
    return;
  }
  const focused = ui.compareYears.contains(document.activeElement) ? document.activeElement.dataset.year : null;
  ui.compareYears.replaceChildren(
    ...years.map((year) => {
      const button = element("button", "", String(year));
      button.type = "button";
      button.dataset.year = String(year);
      const on = chosen.includes(year);
      button.setAttribute("aria-pressed", String(on));
      button.disabled = on ? chosen.length <= 1 : chosen.length >= MAX_COMPARE_YEARS;
      return button;
    }),
  );
  ui.compareYears.dataset.signature = signature;
  if (focused) {
    ui.compareYears.querySelector(`button[data-year="${focused}"]`)?.focus();
  }
}

// The races offered, a pressed button each that is chosen: its short name
// (the head of its name and its day) to the eye, and its whole name and its
// days to the ear (Codex's review of the diff of M2). One at least, and up to
// six (stage M2 of v2.2.0).
function renderCompareRaces() {
  const races = raceChoices();
  const chosen = state.compare.races;
  const signature = JSON.stringify([races, chosen, state.language]);
  if (ui.compareRaces.dataset.signature === signature) {
    return;
  }
  const focused = ui.compareRaces.contains(document.activeElement) ? document.activeElement.dataset.race : null;
  ui.compareRaces.replaceChildren(
    ...races.map((race) => {
      const chip = raceChip(race, state.language);
      const button = element("button");
      button.type = "button";
      button.dataset.race = race.id;
      const shown = element("span", "", describe(chip.short));
      shown.setAttribute("aria-hidden", "true");
      button.append(shown, element("span", "visually-hidden", describe(chip.spoken)));
      const on = chosen.includes(race.id);
      button.setAttribute("aria-pressed", String(on));
      button.disabled = on ? chosen.length <= 1 : chosen.length >= MAX_COMPARE_RACES;
      return button;
    }),
  );
  ui.compareRaces.dataset.signature = signature;
  if (focused) {
    ui.compareRaces.querySelector(`button[data-race="${CSS.escape(focused)}"]`)?.focus();
  }
}

// The words of a key of the legend as the eye reads them, without those for
// the ear only (a race by its short name: stage L3 of v2.2.0).
function keyWords(key) {
  return [...key.childNodes]
    .filter((node) => !node.classList?.contains("visually-hidden"))
    .map((node) => node.textContent)
    .join("");
}

// A short piece of a line in the color of a year.
function yearSwatch(step) {
  const swatch = svgElement("svg", { viewBox: "0 0 22 8", "aria-hidden": "true", focusable: "false" });
  swatch.append(svgElement("line", { x1: 2, x2: 20, y1: 4, y2: 4, class: `key-line y${step}` }));
  return swatch;
}

// What a comparison says of its values: the label of its panel.
function compareKindText(context) {
  return context.mode === "cumulative" ? t("view.compare.mode.cumulative") : t(kindKey(context.item, context.grain));
}

// The years drawn: in rows, on one panel, or in a table, from the answers of
// the last generation; the way, the series, and the table change the drawing
// only.
function renderCompareBody(force = false) {
  const answer = state.compareAnswer;
  const compare = state.compare;
  const mode = compareModeNow();
  const signature = JSON.stringify([answer.seq, mode, compare.series, compare.table, state.language]);
  if (!force && signature === comparedSignature) {
    renderCompareCharts();
    return;
  }
  const focused = ui.comparePanels.contains(document.activeElement) ? (document.activeElement.dataset.plot ?? null) : null;
  // A key of the legend of one panel keeps the focus too (stage L3 of
  // v2.2.0).
  const focusedKey = ui.comparePanels.contains(document.activeElement) ? (document.activeElement.dataset.lit ?? null) : null;
  plotWatcher?.disconnect();
  const item = compareItem();
  // By race day (stage M2 of v2.2.0), the races in the form of the years.
  const race = answer.by === "race";
  const data = race
    ? raceData({ races: answer.races, weeks: answer.weeks, mode, series: compare.series, answers: answer.answers, wholes: answer.wholes, language: state.language })
    : compareData({ years: answer.years, month: answer.month, grain: answer.grain, mode, series: compare.series, answers: answer.answers, whole: answer.whole });
  // A year stood out stays while one panel draws it (stage L3 of v2.2.0).
  compare.lit = litKept(compare.lit, { by: answer.by, mode, table: compare.table, data });
  const span = race ? answer.weeks : compareSpan(answer.grain, answer.month, answer.years);
  const lines = data.map((entry) => ({
    values: entry.values.map((value) => (Number.isFinite(value) ? shown(compare.key, value) : null)),
    points: entry.points === null ? undefined : entry.points.map(([index, value]) => [index, shown(compare.key, value)]),
  }));
  compareContext = {
    key: compare.key,
    item,
    data,
    lines,
    span,
    grain: answer.grain,
    month: answer.month,
    mode,
    total: totalItem(item),
    // What it is compared by, the weeks before a race, and the names of the
    // places of its axis and of its last row: those of the races, or null for
    // those of the years.
    by: answer.by,
    weeks: answer.weeks,
    names: race ? { slotName: (slot) => raceSlotName(slot, answer.weeks), whole: raceValueMessage(item, answer.weeks) } : null,
    // One scale for every year.
    shared: extent(lines),
    slots: Array.from({ length: span + 1 }, (_none, slot) => ({ start: slot, end: slot })),
  };
  // The cross line stays where it was on the same axis; on another (a new
  // grouping or month, also while its numbers are on their way), it starts at
  // the last period of the newest year.
  const axis = JSON.stringify([answer.by, answer.grain, answer.month, answer.weeks]);
  if (compare.cursor === null || compare.cursorAxis !== axis || compare.cursor > span) {
    const newest = data[0];
    compare.cursor = newest && newest.slots.length ? newest.slots[newest.slots.length - 1].start : span;
    compare.cursorAxis = axis;
  }
  const name = itemName(compare.key);
  // A calendar: a strip a year, in the steps of one scale for every year, and
  // its legend above them (stage N1 of v2.2.0).
  const calendar = mode === "calendar";
  compareContext.calendar = calendar ? calendarSteps(compareContext) : null;
  renderCalendarLegend(compareContext);
  if (compare.table) {
    compared = [];
    ui.comparePanels.replaceChildren(buildCompareTable(compareContext, name));
  } else {
    if (calendar) {
      compared = data.map((entry, index) => buildCompareCalendar(compareContext, entry, lines[index], name));
    } else {
      compared = mode === "rows" ? data.map((entry, index) => buildCompareRow(compareContext, entry, lines[index], name)) : [buildCompareOne(compareContext, name)];
    }
    ui.comparePanels.replaceChildren(...compared.map((entry) => entry.section));
  }
  ui.compareAxis.hidden = compare.table || calendar;
  ui.compareAxis.replaceChildren();
  delete ui.compareAxis.dataset.width;
  renderCompareCharts();
  moveCompareCross(compare.cursor, false);
  for (const entry of compared) {
    if (entry.kind !== "calendar") {
      plotWatcher?.observe(entry.plot);
    }
  }
  comparedSignature = signature;
  if (focused !== null) {
    ui.comparePanels.querySelector(`[data-plot="${focused}"]`)?.focus({ preventScroll: true });
  }
  if (focusedKey !== null) {
    ui.comparePanels.querySelector(`button.key[data-lit="${CSS.escape(focusedKey)}"]`)?.focus({ preventScroll: true });
  }
}

// The name of a place of the axis of a comparison, as its table names it.
function compareSlotText(context, slot) {
  return describe(context.names === null ? compareSlotName(slot, context.grain, context.month, state.language) : context.names.slotName(slot));
}

// The name of a year, or of a race (stage M2 of v2.2.0): its name, cut short
// to its room, and its day, which always shows, so that races of one name
// are told apart.
function compareName(entry) {
  if (entry.race === undefined) {
    return [describe(entry.label)];
  }
  const [before = "", after = ""] = t("view.compare.race", { name: "\u0001", date: dateText(entry.race.day, state.language) }).split("\u0001");
  return [before, element("span", "compare-race-name", entry.race.name), after];
}

// A row of a year (or of a race): its name, the days that the output cuts,
// its value (of the year, of the month, or of the span of the race) as the
// server counts it, its reading, and its chart.
function buildCompareRow(context, entry, line, name) {
  const section = element("section", "panel-view compare-row");
  const headingId = `compare-year-${entry.id}`;
  section.setAttribute("aria-labelledby", headingId);
  const head = element("div", "panel-head");
  const heading = element("h4", "panel-name compare-year");
  heading.append(...compareName(entry));
  heading.id = headingId;
  head.append(heading);
  const note = compareNote(entry.cut, state.language);
  if (note !== null) {
    head.append(element("span", "panel-unit", describe(note)));
  }
  const words = context.by === "race" ? raceValueMessage(context.item, context.weeks, true) : compareValueMessage(context.item, context.month, state.language);
  const whole = element("span", "compare-whole", `${describe(words)} `);
  const value = entry.whole === null ? "—" : entry.whole.value === null ? t("view.no_value") : describe(valueMessage(context.key, entry.whole.value, state.language));
  whole.append(element("strong", "", value));
  head.append(whole);
  const read = element("span", "panel-read");
  read.setAttribute("aria-hidden", "true");
  head.append(read);
  section.append(head);
  const body = element("div", "panel-chart");
  const plot = element("div", "plot");
  plot.tabIndex = 0;
  plot.setAttribute("role", "img");
  plot.dataset.plot = entry.id;
  // A race says its span too, which the head of its row calls "this span"
  // (the checker's review of M2).
  plot.setAttribute(
    "aria-label",
    context.by === "race"
      ? t("view.compare.race_row_label", { race: describe(entry.label), name, span: t("view.compare.race_days", { n: context.weeks }) })
      : t("view.compare.row_label", { year: describe(entry.label), name }),
  );
  body.append(plot);
  section.append(body);
  return { section, kind: "row", plot, read, frame: null, data: [entry], lines: [line], size: null, shapes: null, scale: null, cross: null, right: PLOT_RIGHT };
}

// The years (or the races) on one panel: a line each in its color, with its
// name at its end; the legend names a race in short, and its row of the table
// in full.
function buildCompareOne(context, name) {
  const section = element("section", "panel-view compare-one");
  section.setAttribute("aria-labelledby", "compare-one-name");
  const head = element("div", "panel-head");
  const heading = element("h4", "panel-name", name);
  heading.id = "compare-one-name";
  head.append(heading, element("span", "panel-unit", t(unitKey(context.key))), element("span", "panel-kind", compareKindText(context)));
  // The keys are buttons that stand a year (or a race) out (stage L3 of
  // v2.2.0).
  const keys = element("span", "panel-keys");
  keys.setAttribute("role", "group");
  keys.setAttribute("aria-label", t(context.by === "race" ? "view.compare.lit_races" : "view.compare.lit_years"));
  const lit = state.compare.lit;
  for (const entry of context.data) {
    // A year with nothing to draw stays words; a race says its whole name and
    // its days to the ear, as its button in the bar does.
    const drawn = yearDrawn(entry);
    const key = element(drawn ? "button" : "span", "key");
    if (drawn) {
      key.type = "button";
      key.dataset.lit = entry.id;
      key.setAttribute("aria-pressed", String(lit !== null && lit.id === entry.id));
    }
    key.append(yearSwatch(entry.step));
    if (context.by === "race") {
      const chip = raceChip(entry.race, state.language);
      const shown = element("span", "", describe(chip.short));
      shown.setAttribute("aria-hidden", "true");
      key.append(shown, element("span", "visually-hidden", describe(chip.spoken)));
    } else {
      key.append(describe(entry.label));
    }
    keys.append(key);
  }
  head.append(keys);
  section.append(head);
  const body = element("div", "panel-chart");
  const plot = element("div", "plot");
  plot.tabIndex = 0;
  plot.setAttribute("role", "img");
  plot.dataset.plot = "one";
  const names = context.data.map((entry) => describe(entry.label)).join(t("view.spoken_separator"));
  plot.setAttribute(
    "aria-label",
    context.by === "race"
      ? t("view.compare.race_chart_label", { name, span: t("view.compare.race_days", { n: context.weeks }), races: names })
      : t("view.compare.chart_label", { name, years: names }),
  );
  const frame = element("div", "compare-read");
  frame.setAttribute("aria-hidden", "true");
  frame.hidden = true;
  body.append(plot, frame);
  section.append(body);
  return { section, kind: "one", plot, read: null, frame, data: context.data, lines: context.lines, size: null, shapes: null, scale: null, cross: null, right: PLOT_RIGHT, groups: null };
}

// The table of a comparison: the periods in rows, the years in columns, and
// the value of each year (or month) in the last row.
function buildCompareTable(context, name) {
  const section = element("section", "panel-view compare-table table");
  section.setAttribute("aria-labelledby", "compare-table-name");
  const head = element("div", "panel-head");
  const heading = element("h4", "panel-name", name);
  heading.id = "compare-table-name";
  const kind = compareKindText(context);
  head.append(heading, element("span", "panel-unit", t(unitKey(context.key))), element("span", "panel-kind", kind));
  section.append(head);
  const wrap = element("div", "panel-table");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  const race = context.by === "race";
  wrap.setAttribute("aria-label", race ? t("view.compare.race_table_label", { name }) : t("view.compare.table_label", { name }));
  const table = element("table", "t");
  const caption = element("caption", "visually-hidden", race ? t("view.compare.race_table_caption", { name, kind }) : t("view.compare.table_caption", { name, kind }));
  const { heads, rows, last, counts } = compareTable(context.item, context.data, context.grain, context.month, context.span, state.language, context.mode, context.names);
  const headRow = element("tr");
  heads.forEach((entry, index) => {
    const cell = element("th", index === 0 ? "" : "n", describe(entry));
    cell.scope = "col";
    headRow.append(cell);
  });
  const thead = element("thead");
  thead.append(headRow);
  const tbody = element("tbody");
  const line = (row, className = "") => {
    const tr = element("tr", className);
    const period = element("th", "", describe(row.period));
    period.scope = "row";
    tr.append(period);
    for (const cell of row.cells) {
      const text = cell.outside ? "—" : cell.value === null ? t("view.no_value") : `${describe(cell.value)}${cell.partial ? "*" : ""}`;
      tr.append(element("td", cell.value === null ? "n empty" : "n", text));
      if (counts) {
        tr.append(element("td", "n", cell.count ?? ""));
      }
    }
    return tr;
  };
  tbody.append(...rows.map((row) => line(row)), line(last, "whole"));
  table.append(caption, thead, tbody);
  wrap.append(table);
  section.append(wrap);
  return section;
}

// The name at the end of a year's line: the year (a race in short), its
// running total for that way, and the day that the output cuts it; null for
// a year without a value.
function endLabel(context, entry) {
  let last = -1;
  entry.values.forEach((value, index) => {
    if (Number.isFinite(value)) {
      last = index;
    }
  });
  if (last < 0) {
    return null;
  }
  let text = describe(entry.short);
  if (context.mode === "cumulative") {
    text = t("view.compare.end_value", { text, value: describe(valueMessage(context.key, entry.values[last], state.language)) });
  }
  const note = compareNote(entry.cut, state.language, true);
  return { index: last, text: note === null ? text : t("view.compare.end_note", { text, note: describe(note) }) };
}

// Draw the chart of a plot of a comparison at its size: a year in a row, in
// the color of the panels, with the bars cut by the output edged; or the years
// on one panel, older under newer, their names at the right in the room that
// they take; from stage L3, each year in a group of its shapes, with what it
// draws and its name kept for the pointer.
function drawComparePlot(entry, context) {
  const plot = entry.plot;
  const width = plot.clientWidth;
  const height = plot.clientHeight;
  entry.size = `${width} ${height}`;
  entry.shapes = null;
  entry.cross = null;
  entry.groups = null;
  if (width < 60 || height < 24) {
    plot.replaceChildren();
    return;
  }
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, "aria-hidden": "true", focusable: "false" });
  plot.replaceChildren(svg);
  const one = entry.kind === "one";
  const labels = one ? entry.data.map((year) => endLabel(context, year)) : [];
  let room = 0;
  for (const label of labels) {
    if (label !== null) {
      const node = svgElement("text", { class: "compare-label newest" });
      node.textContent = label.text;
      svg.append(node);
      room = Math.max(room, node.getComputedTextLength());
      node.remove();
    }
  }
  entry.right = one ? Math.max(PLOT_RIGHT, Math.min(Math.round(width * 0.4), Math.ceil(room) + 16)) : PLOT_RIGHT;
  const inner = width - (entry.right - PLOT_RIGHT);
  const shapes = entry.data.map((year, index) =>
    panelShapes({
      lines: [entry.lines[index]],
      periods: year.slots,
      start: 0,
      end: context.span,
      width: inner,
      height,
      total: context.total,
      clock: clockOf(context.key),
      shared: context.shared,
      lineOnly: one,
      running: context.mode === "cumulative",
      hits: one,
    }),
  );
  const first = shapes[0];
  if (first === undefined) {
    plot.replaceChildren();
    return;
  }
  entry.scale = first.scale;
  if (first.empty) {
    const empty = !one && entry.data[0].outside ? t("view.compare.outside") : t("view.summary.none");
    plot.replaceChildren(svg, element("span", "panel-empty", empty));
    return;
  }
  appendScale(svg, context.key, first, width - entry.right);
  // The older years first, so that the newest is on top.
  const stack = one ? svgElement("g") : svg;
  const groups = [];
  if (one) {
    svg.append(stack);
  }
  for (let index = entry.data.length - 1; index >= 0; index -= 1) {
    const color = one ? `y${entry.data[index].step}` : "c1";
    const group = one ? svgElement("g", { class: "compare-marks" }) : svg;
    appendMarks(group, shapes[index].lines[0], color, null, { outlined: !one, newest: one && index === 0 });
    if (one) {
      stack.append(group);
      groups[index] = group;
    }
  }
  const names = [];
  if (one) {
    const ends = labels.map((label, index) => (label === null ? null : { x: periodMiddle(first.scale, entry.data[index].slots[label.index]), y: shapes[index].y(entry.lines[index].values[label.index]) }));
    const shownEnds = ends.flatMap((end, index) => (end === null ? [] : [{ ...end, index }]));
    const places = labelPlaces(shownEnds.map((end) => end.y), 13, first.top + first.plotHeight);
    shownEnds.forEach((end, at) => {
      const text = svgElement("text", { class: `compare-label${end.index === 0 ? " newest" : ""}`, x: (end.x + 7).toFixed(1), y: (places[at] + 4).toFixed(1) });
      text.textContent = labels[end.index].text;
      svg.append(text);
      names[end.index] = text;
    });
  }
  const cross = svgElement("g", { class: "cross" });
  cross.setAttribute("display", "none");
  const crossLine = svgElement("line", { class: "chart-cross", y1: first.top, y2: first.top + first.plotHeight });
  cross.append(crossLine);
  const crossDots = entry.data.map((year) => {
    const dot = svgElement("circle", { class: `chart-cross-dot ${one ? `y${year.step}` : "c1"}`, r: 4.5 });
    cross.append(dot);
    return dot;
  });
  svg.append(cross);
  Object.assign(entry, { shapes, cross, crossLine, crossDots, groups: one ? groups : null, names });
  markLit(entry);
}

// Draw the plots whose size changed, the axis at the width of the plots, and
// the cross line again.
function renderCompareCharts() {
  const context = compareContext;
  if (context === null) {
    return;
  }
  let changed = false;
  for (const entry of compared) {
    if (entry.kind === "calendar") {
      // A strip of a calendar in its own size (stage N1 of v2.2.0).
      if (entry.size !== calendarSize(context)) {
        drawCompareCalendar(entry, context);
        changed = true;
      }
    } else if (entry.size !== `${entry.plot.clientWidth} ${entry.plot.clientHeight}`) {
      drawComparePlot(entry, context);
      changed = true;
    }
  }
  const first = compared[0];
  if (first !== undefined && first.kind !== "calendar") {
    const width = first.plot.clientWidth;
    const size = `${width} ${first.right}`;
    if (changed || ui.compareAxis.dataset.width !== size) {
      drawCompareAxis(context, width, first.right);
      ui.compareAxis.dataset.width = size;
    }
  }
  if (changed) {
    moveCompareCross(state.compare.cursor, false);
  }
}

// The axis under the years: the months of a year, or days of the month; under
// the races, every fourth week before them and their week, whose words end
// at the right end (stage M2 of v2.2.0).
function drawCompareAxis(context, width, right) {
  ui.compareAxis.replaceChildren();
  if (width < 60) {
    return;
  }
  const height = ui.compareAxis.clientHeight || 24;
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, "aria-hidden": "true", focusable: "false" });
  const scale = timeScale(0, context.span, PLOT_LEFT, width - right);
  const race = context.by === "race";
  const newest = Math.max(...context.data.map((entry) => entry.year));
  const ticks = race ? raceTicks(context.weeks) : compareTicks(context.grain, context.month, newest, state.language);
  ticks.forEach((tick, index) => {
    const x = scale.x(tick.at);
    svg.append(svgElement("line", { class: "axis-tick", x1: x.toFixed(1), x2: x.toFixed(1), y1: 0, y2: 5 }));
    const end = race && index === ticks.length - 1;
    const label = svgElement("text", end ? { class: "axis-text", x: (scale.x(tick.at + 1) - 3).toFixed(1), y: 16, "text-anchor": "end" } : { class: "axis-text", x: (x + 3).toFixed(1), y: 16 });
    label.textContent = race ? describe(tick.text) : tick.text;
    svg.append(label);
  });
  ui.compareAxis.append(svg);
}

// Move the cross line of the comparison to one place of its axis: the
// reading of each row, or the box of the readings of the panel, follows, and
// the values are said when the keyboard moved it.
function moveCompareCross(slot, speak, year = null) {
  const context = compareContext;
  if (context === null || slot === null || state.compare === null) {
    return;
  }
  const at = Math.max(0, Math.min(context.span, slot));
  state.compare.cursor = at;
  const readings = compareReadings(context.item, context.data, at, context.grain, context.mode, state.language);
  for (const entry of compared) {
    // A calendar frames the day in each strip (stage N1 of v2.2.0), and says
    // the day of the strip of ``year``.
    if (entry.kind === "calendar") {
      renderCalendarCursor(entry, context, at, speak && entry.data[0].year === year);
      continue;
    }
    let x = null;
    if (entry.cross !== null && entry.shapes !== null) {
      x = periodMiddle(entry.scale, { start: at, end: at });
      entry.cross.setAttribute("display", "inline");
      entry.crossLine.setAttribute("x1", x.toFixed(1));
      entry.crossLine.setAttribute("x2", x.toFixed(1));
      entry.crossDots.forEach((dot, index) => {
        const place = entry.data[index].slots.findIndex((period) => period.start === at);
        const value = place < 0 ? null : entry.lines[index].values[place];
        if (Number.isFinite(value)) {
          dot.setAttribute("cx", x.toFixed(1));
          dot.setAttribute("cy", entry.shapes[index].y(value).toFixed(1));
          dot.setAttribute("display", "inline");
        } else {
          dot.setAttribute("display", "none");
        }
      });
    }
    if (entry.kind === "row") {
      renderCompareRead(entry, context, at);
    } else if (x !== null) {
      renderCompareFrame(entry, readings, x);
    }
  }
  if (speak && context.mode === "calendar") {
    speakCalendar(context, at, year);
  } else if (speak) {
    const values = readings
      .map((reading) =>
        reading.period === null
          ? t("view.spoken_line", { line: describe(reading.label), value: describe(reading.missing) })
          : t("view.compare.spoken_year", { year: describe(reading.label), period: describe(reading.period), value: describe(reading.value ?? reading.missing) }),
      )
      .join(t("view.spoken_separator"));
    setText(ui.compareAnnouncer, t("view.spoken", { period: compareSlotText(context, at), values }));
  }
}

// The reading of a row of a year, at the top right as on a panel: its own
// period with its value and its count.
function renderCompareRead(entry, context, at) {
  const year = entry.data[0];
  const place = year.slots.findIndex((period) => period.start === at);
  const nodes = [];
  if (place < 0) {
    nodes.push(compareSlotText(context, at), element("span", "no-value", t("view.compare.outside")));
  } else {
    const reading = readout(context.item, { lines: [{ values: year.values, counts: year.counts }] }, year.periods, place, context.grain, state.language);
    nodes.push(describe(reading.period));
    if (reading.values.length) {
      nodes.push(element("strong", "", describe(reading.values[0].value)));
      if (reading.values[0].count !== null) {
        nodes.push(describe(reading.values[0].count));
      }
    } else {
      nodes.push(element("span", "no-value", t("view.no_value")));
    }
  }
  entry.read.replaceChildren(...nodes);
}

// The box of the readings of the years on one panel, beside the cross line:
// at its right where there is room, and at its left otherwise; a race by its
// short name (stage M2 of v2.2.0).
function renderCompareFrame(entry, readings, x) {
  const table = element("table");
  for (const reading of readings) {
    const row = element("tr");
    const swatch = element("td");
    swatch.append(yearSwatch(reading.step));
    row.append(swatch, element("td", "", describe(compareContext?.by === "race" ? reading.short : reading.label)), element("td", "", reading.period === null ? "" : describe(reading.period)));
    if (reading.value !== null) {
      row.append(element("td", "v", reading.count === null ? describe(reading.value) : `${describe(reading.value)} ${describe(reading.count)}`));
    } else {
      row.append(element("td", "none", describe(reading.missing)));
    }
    table.append(row);
  }
  entry.frame.replaceChildren(table);
  entry.frame.hidden = false;
  const room = entry.plot.clientWidth - entry.right;
  const width = entry.frame.offsetWidth;
  const left = x + 14 + width <= room ? x + 14 : Math.max(PLOT_LEFT, x - 14 - width);
  entry.frame.style.left = `${Math.round(left)}px`;
}

function comparePointer(event) {
  const plot = event.target.closest(".plot");
  const entry = compared.find((candidate) => candidate.plot === plot);
  if (!entry || entry.shapes === null || compareContext === null) {
    return;
  }
  const box = plot.getBoundingClientRect();
  const slot = nearestPeriod(compareContext.slots, entry.scale, event.clientX - box.left);
  if (slot !== null && slot !== state.compare.cursor) {
    moveCompareCross(slot, false);
  }
}

function compareKey(event) {
  if (compareContext === null) {
    return;
  }
  if (Object.hasOwn(CROSS_KEYS, event.key)) {
    moveCompareCross((state.compare.cursor ?? 0) + CROSS_KEYS[event.key], true);
  } else if (event.key === "Home") {
    moveCompareCross(0, true);
  } else if (event.key === "End") {
    moveCompareCross(compareContext.span, true);
  } else {
    return;
  }
  event.preventDefault();
}

// The marks of the year stood out on the chart of one panel (stage L3 of
// v2.2.0): its group of shapes drawn over the others, its name, and its dot
// on the cross line, marked, and those of the other years marked faint;
// without one, the years as they were drawn, the newest on top. The boxes of
// the names are measured as they are drawn now, a name stood out bold.
function markLit(entry) {
  if (!entry.groups) {
    return;
  }
  const lit = state.compare?.lit ?? null;
  const at = lit === null ? -1 : entry.data.findIndex((year) => year.id === lit.id);
  for (const index of topFirst(entry.groups.length, at).reverse()) {
    entry.groups[index].parentNode.append(entry.groups[index]);
  }
  entry.data.forEach((_year, index) => {
    for (const node of [entry.groups[index], entry.names[index], entry.crossDots[index]]) {
      node?.classList.toggle("lit", index === at);
      node?.classList.toggle("dim", at >= 0 && index !== at);
    }
  });
  for (const dot of entry.crossDots) {
    entry.cross.append(dot);
  }
  if (at >= 0) {
    entry.cross.append(entry.crossDots[at]);
  }
  entry.boxes = entry.names.map((name) => name.getBBox());
}

// Stand a year (or a race) out by its id, or put back the one stood out, by
// its id again or by null: the keys of the legend and the marks of the chart
// change, and nothing is drawn again, so that a key keeps the focus; the line
// after a saving goes (stage L3 of v2.2.0).
function standOut(id) {
  if (state.compare === null || compareContext === null) {
    return;
  }
  state.compare.lit = id === null ? null : litAfter(state.compare.lit, compareContext.by, id);
  for (const entry of compared) {
    if (entry.kind === "one") {
      for (const key of entry.section.querySelectorAll("button.key[data-lit]")) {
        key.setAttribute("aria-pressed", String(state.compare.lit?.id === key.dataset.lit));
      }
      markLit(entry);
    }
  }
  renderSaveNotice();
}

// A press on the chart of one panel stands out the year whose name or
// shapes are at the press, and puts it back on the one stood out; a press
// away from them changes nothing, so that the chart can take the keyboard
// (stage L3 of v2.2.0).
function compareClick(event) {
  const entry = compared.find((candidate) => candidate.kind === "one" && candidate.plot.contains(event.target));
  const svg = entry?.plot.querySelector(":scope > svg") ?? null;
  if (!entry?.groups || svg === null) {
    return;
  }
  const [width, height] = viewSize(svg);
  const place = plotPlace(event.clientX, event.clientY, svg.getBoundingClientRect(), width, height);
  const lit = state.compare.lit;
  const order = topFirst(entry.data.length, lit === null ? -1 : entry.data.findIndex((year) => year.id === lit.id));
  const at = shapeAt(
    entry.shapes.map((shape) => shape.lines[0]?.hits ?? null),
    entry.boxes,
    place.x,
    place.y,
    order,
    place.reach,
  );
  if (at !== null) {
    standOut(entry.data[at].id);
  }
}

// --- The calendar of comparing years (stage N1 of v2.2.0) ------------------

// The room of a strip of a calendar: the names of the days of the week at its
// left, of the months above it, its side (view.css .calendar-side) with the
// margins of the strip, and what a strip takes besides its squares (the
// names of the months, the padding of its row, and its line).
const CALENDAR_LEFT = 30;
const CALENDAR_TOP = 16;
const CALENDAR_SIDE = 160 + 24;
const CALENDAR_ROW = CALENDAR_TOP + 2 + 3 + 1;
// The room kept for a scroll bar of the comparison, so that its strips stay
// in it when one shows (and its size does not change their squares).
const CALENDAR_BAR = 16;

// The steps of the colors of a calendar: one scale over the values of the
// days of every year drawn (as shown, in km or minutes), from 0 for a total,
// without its days without a recorded activity, which are outlines; and how
// many of those days there are, for the note of the legend.
function calendarSteps(context) {
  const values = calendarValues(context.item, context.data, context.lines);
  return { ticks: calendarScale(values, { fromZero: context.total, clock: clockOf(context.key) }), zeroDays: calendarZeroDays(context.item, context.data) };
}

// A key of the legend: a square in a step, or the outline of a day without a
// recorded activity, and its words.
function calendarSwatch(kind, words) {
  const key = element("span", "calendar-key");
  const svg = svgElement("svg", { viewBox: "0 0 12 12", "aria-hidden": "true", focusable: "false" });
  svg.append(
    svgElement(
      "rect",
      kind === "zero" ? { class: "calendar-cell zero", x: 0.75, y: 0.75, width: 10.5, height: 10.5, rx: 2 } : { class: `calendar-cell ${kind}`, x: 0, y: 0, width: 12, height: 12, rx: 2 },
    ),
  );
  key.append(svg, words);
  return key;
}

// The legend of a calendar above its strips: what a day's value is, the
// outline of a day without a recorded activity (of a total), the steps in the
// words of the ticks of its scale, the rule of their edges with where the
// values are read, and the days without a record.
function renderCalendarLegend(context) {
  const steps = context?.calendar ?? null;
  if (steps === null) {
    ui.compareLegend.replaceChildren();
    return;
  }
  const unit = unitKey(context.key);
  const nodes = [element("span", "", unit ? t("view.compare.calendar_legend_unit", { unit: t(unit) }) : t("view.compare.calendar_legend"))];
  if (context.total) {
    nodes.push(calendarSwatch("zero", t("view.compare.calendar_zero_key")));
  }
  if (steps.ticks !== null) {
    for (const entry of calendarLegend(context.item, steps.ticks, state.language)) {
      nodes.push(calendarSwatch(`s${entry.step}`, describe(entry.words)));
    }
  }
  nodes.push(element("p", "calendar-note", t("view.compare.calendar_note")));
  if (context.total && steps.zeroDays > 0) {
    nodes.push(element("p", "calendar-note", describe(calendarZeroNote(steps.zeroDays, state.language))));
  }
  ui.compareLegend.replaceChildren(...nodes);
}

// A strip of a year: at its left its name, the days that the output cuts,
// its value as the server counts it, and the reading of the day chosen; its
// days drawn in its own size (not a .plot, which fills its panel).
function buildCompareCalendar(context, entry, line, name) {
  const section = element("section", "panel-view compare-calendar");
  const headingId = `compare-year-${entry.id}`;
  section.setAttribute("aria-labelledby", headingId);
  const side = element("div", "calendar-side");
  const heading = element("h4", "panel-name compare-year");
  heading.append(...compareName(entry));
  heading.id = headingId;
  side.append(heading);
  const note = compareNote(entry.cut, state.language);
  if (note !== null) {
    side.append(element("span", "panel-unit", describe(note)));
  }
  const whole = element("span", "compare-whole", `${describe(compareValueMessage(context.item, null, state.language))} `);
  const value = entry.whole === null ? "—" : entry.whole.value === null ? t("view.no_value") : describe(valueMessage(context.key, entry.whole.value, state.language));
  whole.append(element("strong", "", value));
  side.append(whole);
  const read = element("span", "panel-read calendar-read");
  read.setAttribute("aria-hidden", "true");
  side.append(read);
  const strip = element("div", "calendar");
  strip.tabIndex = 0;
  strip.setAttribute("role", "img");
  strip.dataset.plot = entry.id;
  strip.setAttribute("aria-label", t("view.compare.calendar_label", { year: describe(entry.label), name }));
  section.append(side, strip);
  return { section, kind: "calendar", plot: strip, read, frame: null, data: [entry], lines: [line], size: null, shapes: null, scale: null, cross: null, right: PLOT_RIGHT, pitch: null, cursor: null };
}

// The size of the squares: as the years chosen fit the room of the
// comparison, from 11 to 16 px apart; on a small screen, the strips scroll.
// The room is taken with its scroll bar, so that one showing does not change
// it.
function calendarPitch(count) {
  const box = ui.comparePanels.getBoundingClientRect();
  const byWidth = Math.floor((box.width - CALENDAR_BAR - CALENDAR_SIDE - CALENDAR_LEFT - 4) / 54);
  const byHeight = Math.floor((box.height / Math.max(1, count) - CALENDAR_ROW) / 7);
  return Math.max(11, Math.min(16, byWidth, byHeight));
}

function calendarSize(context) {
  const box = ui.comparePanels.getBoundingClientRect();
  return `${Math.round(box.width)} ${Math.round(box.height)} ${context.data.length}`;
}

// The strip of a year: the names of the months above the weeks where they
// start, the days of the week at the left (every other one on small squares),
// each day of the output in the step of its value or as an outline (nothing
// for a day without a value), and the frame of the day chosen.
function drawCompareCalendar(entry, context) {
  const year = entry.data[0];
  const pitch = calendarPitch(context.data.length);
  const width = CALENDAR_LEFT + calendarWeeks(year.year) * pitch + 4;
  const height = CALENDAR_TOP + 7 * pitch + 2;
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true", focusable: "false" });
  for (const tick of compareTicks("day", null, year.year, state.language)) {
    const day = slotDay(tick.at, year.year);
    if (day !== null) {
      const label = svgElement("text", { class: "calendar-name", x: CALENDAR_LEFT + calendarPlace(day).week * pitch, y: 11 });
      label.textContent = tick.text;
      svg.append(label);
    }
  }
  calendarWeekdays(state.language).forEach((name, row) => {
    if (pitch >= 12 || row % 2 === 0) {
      const label = svgElement("text", { class: "calendar-name", x: 2, y: (CALENDAR_TOP + row * pitch + pitch * 0.75).toFixed(1) });
      label.textContent = name;
      svg.append(label);
    }
  });
  year.periods.forEach((period, index) => {
    const cell = calendarCell(context.item, year.values[index], year.counts[index]);
    if (cell === null) {
      return;
    }
    const place = calendarPlace(period.start);
    const x = CALENDAR_LEFT + place.week * pitch;
    const y = CALENDAR_TOP + place.day * pitch;
    svg.append(
      svgElement(
        "rect",
        cell === "zero"
          ? { class: "calendar-cell zero", x: (x + 1.25).toFixed(2), y: (y + 1.25).toFixed(2), width: pitch - 4, height: pitch - 4, rx: 2 }
          : { class: `calendar-cell s${calendarStep(context.calendar.ticks, entry.lines[0].values[index])}`, x: x + 0.5, y: y + 0.5, width: pitch - 2.5, height: pitch - 2.5, rx: 2 },
      ),
    );
  });
  entry.cursor = svgElement("rect", { class: "calendar-cursor", width: pitch - 1, height: pitch - 1, rx: 3, display: "none" });
  svg.append(entry.cursor);
  entry.pitch = pitch;
  entry.plot.replaceChildren(svg);
  entry.size = calendarSize(context);
}

// The day chosen in a strip: the same day of the year as in the others (28
// February for 29 February of a common year, and the nearest day of the
// output where it does not reach it), framed, with its reading at the left.
function renderCalendarCursor(entry, context, at, reveal = false) {
  const day = calendarDay(at, entry.data[0].year, state.view.first_day, state.view.last_day);
  if (entry.cursor !== null && entry.pitch !== null) {
    if (day === null) {
      entry.cursor.setAttribute("display", "none");
    } else {
      const place = calendarPlace(day);
      entry.cursor.setAttribute("x", (CALENDAR_LEFT + place.week * entry.pitch - 0.5).toFixed(1));
      entry.cursor.setAttribute("y", (CALENDAR_TOP + place.day * entry.pitch - 0.5).toFixed(1));
      entry.cursor.setAttribute("display", "inline");
      // The day that the keys or a click chose stays in view where the
      // strips scroll (Codex's review of the diff of N1).
      if (reveal) {
        entry.cursor.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
    }
  }
  const nodes = [];
  if (day === null) {
    nodes.push(element("span", "no-value", t("view.compare.outside")));
  } else {
    const reading = calendarReading(context.item, entry.data[0], day, state.language);
    nodes.push(describe(reading.day));
    if (reading.value !== null) {
      nodes.push(element("strong", "", describe(reading.value)));
      if (reading.count !== null) {
        nodes.push(describe(reading.count));
      }
    } else {
      nodes.push(element("span", "no-value", describe(reading.missing)));
    }
  }
  entry.read.replaceChildren(...nodes);
}

// What the keyboard (and a click) says: the day chosen in the strip of the
// year, its day of the week, and its value with its count.
function speakCalendar(context, at, year) {
  const entry = compared.find((candidate) => candidate.kind === "calendar" && candidate.data[0].year === year) ?? compared.find((candidate) => candidate.kind === "calendar");
  const day = entry === undefined ? null : calendarDay(at, entry.data[0].year, state.view.first_day, state.view.last_day);
  if (day === null) {
    return;
  }
  const reading = calendarReading(context.item, entry.data[0], day, state.language);
  const value = reading.value === null ? describe(reading.missing) : reading.count === null ? describe(reading.value) : `${describe(reading.value)} ${describe(reading.count)}`;
  setText(ui.compareAnnouncer, t("view.compare.calendar_spoken", { day: describe(reading.day), value }));
}

// The day of a strip under the pointer, as a place of the shared axis, by its
// column and its row; none outside the year or the days of the output.
function calendarSlotAt(event) {
  const strip = event.target.closest?.(".calendar");
  const entry = compared.find((candidate) => candidate.plot === strip);
  if (!entry || entry.pitch === null || compareContext === null || state.view === null) {
    return null;
  }
  const box = strip.getBoundingClientRect();
  const day = calendarAt(entry.data[0].year, event.clientX - box.left - CALENDAR_LEFT, event.clientY - box.top - CALENDAR_TOP, entry.pitch);
  if (day === null || day < state.view.first_day || day > state.view.last_day) {
    return null;
  }
  return { year: entry.data[0].year, slot: daySlot(day) };
}

function calendarPointer(event) {
  const at = calendarSlotAt(event);
  if (at !== null && at.slot !== state.compare.cursor) {
    moveCompareCross(at.slot, false);
  }
}

function calendarClick(event) {
  const at = calendarSlotAt(event);
  if (at !== null) {
    moveCompareCross(at.slot, true, at.year);
  }
}

// The keys of a strip: a week to the left and to the right, a day up and
// down, and the first and last day of its year in the output; they stop at
// its ends, and the day is said.
function calendarKeyDown(event) {
  const entry = compared.find((candidate) => candidate.plot === event.target);
  if (!entry || compareContext === null || state.view === null) {
    return;
  }
  const year = entry.data[0].year;
  const slot = calendarMove(state.compare.cursor ?? 0, year, event.key, state.view.first_day, state.view.last_day);
  if (slot === null) {
    return;
  }
  moveCompareCross(slot, true, year);
  event.preventDefault();
}

// A strip that the focus comes to says its day chosen.
function calendarFocus(event) {
  const entry = compared.find((candidate) => candidate.plot === event.target);
  if (entry && compareContext !== null && state.view !== null) {
    speakCalendar(compareContext, state.compare.cursor, entry.data[0].year);
  }
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
  const answer = shownAnswer();
  const apart = viewing && comparing();
  for (const button of ui.periodButtons) {
    button.disabled = !viewing || apart;
    button.setAttribute("aria-pressed", String(viewing && state.period === button.dataset.period));
  }
  ui.rangeFrom.disabled = apart;
  ui.rangeTo.disabled = apart;
  ui.rangeRow.hidden = !viewing || state.period !== "custom";
  if (viewing) {
    for (const field of [ui.rangeFrom, ui.rangeTo]) {
      field.min = state.view.first_day ?? "";
      field.max = state.view.last_day ?? "";
    }
  }
  ui.periodBack.disabled = !viewing || apart || shiftedRange(answer?.start, answer?.end, -1, state.view?.first_day, state.view?.last_day) === null;
  ui.periodNext.disabled = !viewing || apart || shiftedRange(answer?.start, answer?.end, 1, state.view?.first_day, state.view?.last_day) === null;
  const grains = apart ? compareGrainsFor(compareByNow(), compareMonthNow(), compareModeNow()) : null;
  for (const button of ui.grainButtons) {
    button.disabled = !viewing || otherShown() || (grains !== null && !grains.includes(button.dataset.grain));
    button.setAttribute("aria-pressed", String(viewing && (grains === null ? state.grain : state.compare.grain) === button.dataset.grain));
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
  ui.filtersHint.hidden = !state.hints || !viewing || apart;
  ui.compareOff.hidden = !apart;
  // By race day, its own words of what is not used (stage M2 of v2.2.0).
  const byRace = apart && compareByNow() === "race";
  if (byRace) {
    ui.compareOff.hidden = true;
  }
  ui.compareOffRace.hidden = !byRace;
  // As a calendar, its own words too (stage N1 of v2.2.0).
  const calendar = apart && !byRace && compareModeNow() === "calendar";
  if (calendar) {
    ui.compareOff.hidden = true;
  }
  ui.compareOffCalendar.hidden = !calendar;
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
  // While comparing years or plotting two items, the items are chosen in
  // their bar.
  const viewing = live && state.view !== null && state.opening === null && !apart();
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
  ui.addItems.disabled = !viewing || apart() || state.items.length >= MAX_PANELS;
  if (apart()) {
    state.pickerOpen = false;
  }
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
  } else if (viewing && !state.items.length && !apart()) {
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
  ui.caveat.hidden = !viewing || apart();
  renderOtherViews(viewing && live && !apart());
  renderPicker(viewing);
  renderMarks(viewing && !apart(), live);
  renderRecap(viewing, live);
  setText(ui.loading, state.loading && viewing ? t("view.loading") : "");
  ui.align.disabled = !viewing;
  ui.align.checked = state.align;
  ui.seriesStop.hidden = !viewing || state.seriesStop === null || apart();
  if (!ui.seriesStop.hidden) {
    renderStop(ui.seriesStop, null, ui.seriesStopLines, ui.seriesStopCode, stopBox(state.seriesStop.code, state.seriesStop.detail, state.productVersion));
  }
  const showPanels = viewing && state.items.length > 0 && state.answer !== null && state.seriesStop === null && !apart();
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
    // The list goes with the panels (stage M3 of v2.2.0).
    closeList();
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
  const words = notice === null ? [] : settingsMessages(notice.code, notice.writing).map(describe);
  // What to tell of the file of the marks, apart from the settings (stage M1
  // of v2.2.0).
  if (state.marksNotice !== null) {
    words.push(t(MARKS_NOTICE_KEYS[state.marksNotice]));
  }
  setText(ui.settingsStatus, words.join(" "));
}

function renderHelp() {
  ui.helpPanel.hidden = !state.helpOpen;
  ui.helpButton.setAttribute("aria-expanded", String(state.helpOpen));
  document.body.classList.toggle("help-open", state.helpOpen);
}

// --- Two items plotted against each other (stage O1 of v2.2.0) ------------

// What the points show now: the answer drawn and its pair, the shapes of the
// chart for the pointer and the keys, and what they were drawn for, so that
// they are drawn again only when that changes.
let plotContext = null;

function plotting() {
  return state.plot !== null && state.view !== null;
}

// The points or a distribution in the place of the panels (stages O1 and
// P1): the other views, which have no grouping and ask for their answers with
// the period and the activity types of the page.
function otherShown() {
  return plotting() || spreading() || shoesShown();
}

// The panels give their place to a comparison of years or to another view.
function apart() {
  return comparing() || otherShown();
}

// The answer that the period and its arrows go by: that of the other view
// while it shows (Codex's reviews of the plans of O1 and P1).
function shownAnswer() {
  return plotting() ? state.plotAnswer : spreading() ? state.spreadAnswer : shoesShown() ? state.shoesAnswer : state.answer;
}

// Ask for what shows: the other view while it shows, and the panels on the
// way back, since the period and the activity types are the page's.
function requestShown() {
  if (otherShown()) {
    state.panelsStale = true;
    requestPlot();
    requestSpread();
    requestShoes();
  } else {
    requestSeries();
  }
}

// The menu of the other views in the row above the panels: Enter, Space, or
// Down on its button opens it on its first item, Esc closes it to its button,
// and Tab or a click elsewhere closes it (the checker's review of the plan of
// O1: the keys of a menu of one item as of more).
function renderOtherViews(usable) {
  ui.otherViews.disabled = !usable;
  if (!usable) {
    state.otherOpen = false;
  }
  ui.otherViews.setAttribute("aria-expanded", String(state.otherOpen));
  ui.otherMenu.hidden = !state.otherOpen;
  ui.otherPlot.disabled = plotPairOf(state.plotPair, state.view?.items) === null;
  ui.otherSpread.disabled = spreadItemOf(state.spreadItem, state.view?.items) === null;
  // The view by shoes where the output has shoes to show, or why not, under
  // its name (stage S1 of v2.2.0); an item that cannot be chosen stays in the
  // way of the keys, so that why is read (Codex's review of its diff).
  const why = shoesWhy(state.shoesAvailable);
  ui.otherShoes.setAttribute("aria-disabled", String(why !== null));
  ui.otherShoesWhy.hidden = why === null;
  setText(ui.otherShoesWhy, why === null ? "" : t(why));
}

function setOtherViews(open, focus = null) {
  state.otherOpen = open;
  render();
  if (focus === "first") {
    otherItems()[0]?.focus();
  } else if (focus === "button") {
    ui.otherViews.focus();
  }
}

function otherItems() {
  return [...ui.otherMenu.querySelectorAll('[role="menuitem"]')].filter((item) => !item.disabled);
}

function otherButtonKey(event) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    setOtherViews(true, "first");
  }
}

function otherMenuKey(event) {
  const items = otherItems();
  const at = items.indexOf(document.activeElement);
  if (event.key === "Escape") {
    event.preventDefault();
    setOtherViews(false, "button");
  } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    items[(at + (event.key === "ArrowDown" ? 1 : items.length - 1) + items.length) % items.length]?.focus();
  } else if (event.key === "Home" || event.key === "End") {
    event.preventDefault();
    (event.key === "Home" ? items[0] : items[items.length - 1])?.focus();
  } else if (event.key === "Tab") {
    // Tab goes on from the button of the menu, which closes.
    ui.otherViews.focus();
    setOtherViews(false);
  }
}

// The points of two items in the place of the panels: the pair remembered
// (or the first one), with the period and the activity types of the page.
function enterPlot() {
  const pair = state.view === null || comparing() ? null : plotPairOf(state.plotPair, state.view.items);
  if (pair === null) {
    return;
  }
  listChanged("plot");
  state.plotPair = pair;
  state.plot = { table: false, sort: { column: "when", descending: true }, chosen: null };
  state.plotAnswer = null;
  state.plotAsked = null;
  state.plotStop = null;
  state.otherOpen = false;
  state.typesOpen = false;
  state.pickerOpen = false;
  state.notesOpen = null;
  state.layoutsOpen = false;
  state.layoutSaving = false;
  state.railLayoutsOpen = false;
  render();
  ui.plotX.focus();
  requestPlot();
}

// Back to the panels as they were; answers on their way are dropped, and the
// panels ask again where the period or the activity types changed meanwhile.
function leavePlot() {
  state.plot = null;
  state.plotAnswer = null;
  state.plotAsked = null;
  state.plotStop = null;
  state.plotLoading = false;
  state.plotSeq += 1;
  render();
  ui.otherViews.focus();
  if (state.panelsStale) {
    state.panelsStale = false;
    requestSeries();
  }
}

function plotPayload() {
  return {
    view: state.view.view,
    x: state.plotPair.x,
    y: state.plotPair.y,
    period: periodRequest(state.period, state.range),
    types: typesRequest(state.counted, state.view.types),
  };
}

// Ask for the points as one generation: an answer of an older one is dropped
// when it comes; a ticket that the server no longer keeps opens the output
// again, once; an output that cannot be read stops the page, and another stop
// shows in the bar of the points (Codex's review of the plan of O1).
async function requestPlot(again = true) {
  if (!plotting()) {
    return;
  }
  const seq = ++state.plotSeq;
  state.plotLoading = true;
  render();
  const payload = plotPayload();
  try {
    const answer = await callApi("/api/view/points", payload);
    if (seq !== state.plotSeq) {
      return;
    }
    state.plotAnswer = answer;
    state.plotAsked = payload;
    state.plotStop = null;
    if (state.plot !== null) {
      state.plot.chosen = null;
    }
  } catch (error) {
    if (seq !== state.plotSeq) {
      return;
    }
    if (connectionFailure(error)) {
      // The bar says so.
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null) {
      if (await reopen()) {
        if (seq !== state.plotSeq) {
          return;
        }
        state.plotLoading = false;
        requestPlot(false);
        return;
      }
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
      state.stop = { code: error.code, detail: error.detail };
    } else {
      state.plotStop = { code: error.code, detail: error.detail };
    }
  }
  if (seq === state.plotSeq) {
    state.plotLoading = false;
  }
  render();
}

// One of the two items changed; the other stays, the pair is remembered, and
// the points are asked for again.
function choosePlotItem(axis, key) {
  if (!plotting()) {
    return;
  }
  const pair = { ...state.plotPair, [axis]: key };
  if (plotPairOf(pair, state.view.items)?.[axis] !== key) {
    render();
    return;
  }
  state.plotPair = pair;
  state.plot.chosen = null;
  state.plot.sort = plotSortAfter(state.plot.sort, ["when", "type", pair.x, pair.y]);
  rememberItems(true);
  requestPlot();
}

// The answer of the pair chosen: an answer of another pair on its way is not
// drawn, as a calendar draws only its own (Codex's review of the diff of N1).
function plotAnswerNow() {
  const answer = state.plotAnswer;
  const asked = state.plotAsked;
  return answer !== null && asked !== null && asked.x === state.plotPair.x && asked.y === state.plotPair.y ? answer : null;
}

// The items of a list: those that can be plotted; the item of the other list
// is disabled, and says why (the checker's review of the plan of O1).
function renderPlotItems(select, axis, chosen, other) {
  const items = (state.view?.items ?? []).filter(plotItem);
  const taken = axis === "x" ? "view.plot.taken_y" : "view.plot.taken_x";
  const signature = JSON.stringify([items.map((item) => item.key), chosen, other, state.language]);
  if (select.dataset.signature !== signature) {
    select.replaceChildren(
      ...items.map((item) => {
        const name = t(itemKey(item.key));
        const option = element("option", "", item.key === other ? t(taken, { name }) : name);
        option.value = item.key;
        option.disabled = item.key === other;
        return option;
      }),
    );
    select.dataset.signature = signature;
  }
  select.value = chosen;
}

// The bar of the points, its lines, and their chart or table. The words
// under the points, that no relation is shown, always show with them (the
// checker's review of the decisions of O1).
function renderPlot(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const plot = viewing && plotting() ? state.plot : null;
  ui.plot.hidden = plot === null;
  ui.plotOff.hidden = plot === null;
  if (plot === null) {
    plotContext = null;
    ui.plotBody.replaceChildren();
    return;
  }
  const [before = "", rest = ""] = t("view.plot.title", { x: "\u0001", y: "\u0002" }).split("\u0001");
  const [middle = "", after = ""] = rest.split("\u0002");
  setText(ui.plotBefore, before);
  setText(ui.plotMiddle, middle);
  setText(ui.plotAfter, after);
  renderPlotItems(ui.plotX, "x", state.plotPair.x, state.plotPair.y);
  renderPlotItems(ui.plotY, "y", state.plotPair.y, state.plotPair.x);
  const drawn = plotAnswerNow();
  ui.plotTable.disabled = drawn === null || !drawn.points.length;
  ui.plotTable.setAttribute("aria-pressed", String(plot.table));
  ui.plotTableChart.hidden = !plot.table;
  ui.plotTableTable.hidden = plot.table;
  setText(ui.plotLoading, state.plotLoading ? t("view.loading") : "");
  ui.plotStop.hidden = state.plotStop === null;
  if (!ui.plotStop.hidden) {
    renderStop(ui.plotStop, null, ui.plotStopLines, ui.plotStopCode, stopBox(state.plotStop.code, state.plotStop.detail, state.productVersion));
  }
  setText(ui.plotCount, drawn === null ? "" : describe(plotCount(drawn, state.language)));
  ui.plotCut.hidden = drawn === null || !plotCut(drawn);
  setText(ui.plotCut, ui.plotCut.hidden ? "" : t("view.plot.cut", { max: countText(drawn.limit, state.language) }));
  ui.plotNone.hidden = drawn === null || drawn.points.length > 0;
  renderPlotBody(drawn);
}

// The chart of the points or their table, drawn again only when what they
// show changes; the point chosen moves without drawing them again.
function renderPlotBody(drawn) {
  const plot = state.plot;
  if (plot === null) {
    return;
  }
  // While the points of a new request are on their way, what shows stays,
  // dimmed, so that the focus stays where it is; they are drawn in its place
  // when they come; those of the same pair only, as for a distribution
  // (Codex's review of the diff of P1).
  ui.plotBody.classList.toggle("waiting", state.plotLoading);
  if (drawn === null && state.plotLoading && plotContext !== null && plotContext.answer !== null && plotContext.pair === `${state.plotPair.x} ${state.plotPair.y}`) {
    return;
  }
  const box = ui.plotBody.getBoundingClientRect();
  const size = [Math.round(box.width), Math.round(box.height)];
  const wanted = { answer: drawn, table: plot.table, sort: JSON.stringify(plot.sort), language: state.language, size: size.join(" ") };
  if (plotContext !== null && Object.keys(wanted).every((key) => plotContext[key] === wanted[key])) {
    renderPlotChosen(false);
    return;
  }
  plotContext = { ...wanted, pair: drawn === null ? null : `${state.plotAsked.x} ${state.plotAsked.y}`, shapes: null };
  // The focus stays where it was, on the chart, the table, or a head of the
  // table, drawn again in its place (Codex's review of the diff of O1).
  const focused = ui.plotBody.contains(document.activeElement) ? document.activeElement : null;
  const column = focused?.closest('button[data-action="plot-sort"]')?.dataset.column ?? null;
  const refocus =
    column !== null ? `button[data-action="plot-sort"][data-column="${column}"]` : focused?.closest(".plot-points") ? ".plot-points" : focused?.closest(".plot-table") ? ".plot-table" : null;
  if (drawn === null || !drawn.points.length) {
    ui.plotBody.replaceChildren();
    return;
  }
  const asked = state.plotAsked;
  if (plot.table) {
    ui.plotBody.replaceChildren(buildPlotTable(drawn, asked));
  } else {
    const chart = buildPlotChart(drawn, asked);
    ui.plotBody.replaceChildren(chart.section);
    Object.assign(plotContext, chart, { x: asked.x, y: asked.y });
    // The chart takes the room that its head leaves, with the reading in it,
    // which can wrap (Codex's review of the diff of O1).
    fillPlotReading();
    const room = chart.chart.getBoundingClientRect();
    Object.assign(plotContext, drawPlotPoints(chart, drawn, asked, [room.width, room.height]), { headHeight: chart.head.getBoundingClientRect().height });
    renderPlotChosen(false);
  }
  if (refocus !== null) {
    ui.plotBody.querySelector(refocus)?.focus();
  }
}

// The name of an item at its axis, with its unit, unless its name already
// has it, as "Ground contact time (%)" has.
function axisName(key) {
  const name = t(itemKey(key));
  const unit = unitKey(key) === undefined ? null : t(unitKey(key));
  return unit === null || name.includes(`(${unit})`) || name.includes(`\uff08${unit}\uff09`) ? name : t("view.plot.axis", { name, unit });
}

// The chart: its head, with the reading of the point chosen, and its frame,
// which takes the keys and the pointer; the points are drawn in it when it is
// in the page, as large as its room (drawPlotPoints).
function buildPlotChart(drawn, asked) {
  const section = element("section", "panel-view plot-view");
  section.setAttribute("aria-labelledby", "plot-title");
  const head = element("div", "panel-head plot-head");
  const read = element("span", "panel-read plot-read");
  read.setAttribute("aria-hidden", "true");
  head.append(element("span", "spacer"), read);
  const chart = element("div", "plot-points");
  chart.tabIndex = 0;
  chart.setAttribute("role", "img");
  chart.setAttribute("aria-label", t("view.plot.label", { x: t(itemKey(asked.x)), y: t(itemKey(asked.y)) }));
  section.append(head, chart);
  return { section, head, chart, read };
}

// The ticks up at the left and across below, the names of the two items, and
// a point an activity, as the sample of OP0 drew them; a point chosen is drawn
// again on top, framed.
function drawPlotPoints(frame, drawn, asked, size) {
  const x = asked.x;
  const y = asked.y;
  // As large as its room, which a small window keeps small.
  const width = Math.max(240, Math.round(size[0]));
  const height = Math.max(120, Math.round(size[1]));
  const shapes = pointShapes(
    drawn.points.map((point) => shown(x, point.values[x])),
    drawn.points.map((point) => shown(y, point.values[y])),
    { width, height, clockX: clockOf(x), clockY: clockOf(y) },
  );
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true", focusable: "false" });
  const chosen = svgElement("circle", { class: "plot-dot plot-chosen", r: CHOSEN_RADIUS, display: "none" });
  frame.chart.append(svg);
  if (shapes === null) {
    return { chosen, shapes };
  }
  const stepUp = Math.abs(shapes.up.ticks[1] - shapes.up.ticks[0]);
  for (const tick of shapes.up.ticks) {
    const at = shapes.y(tick).toFixed(1);
    svg.append(svgElement("line", { class: "chart-grid", x1: shapes.left, x2: shapes.right, y1: at, y2: at }));
    const label = svgElement("text", { class: "chart-tick", x: shapes.left - 8, y: (Number(at) + 4).toFixed(1), "text-anchor": "end" });
    label.textContent = tickText(y, tick, stepUp, state.language);
    svg.append(label);
  }
  const stepAcross = Math.abs(shapes.across.ticks[1] - shapes.across.ticks[0]);
  shapes.across.ticks.forEach((tick, index, ticks) => {
    const at = shapes.x(tick);
    svg.append(svgElement("line", { class: "chart-grid", x1: at.toFixed(1), x2: at.toFixed(1), y1: shapes.top, y2: shapes.bottom }));
    // The words of the ticks at the ends stay inside the chart.
    const anchor = index === 0 && at - shapes.left < 24 ? "start" : index === ticks.length - 1 && shapes.right - at < 24 ? "end" : "middle";
    const label = svgElement("text", { class: "chart-tick", x: at.toFixed(1), y: shapes.bottom + 16, "text-anchor": anchor });
    label.textContent = tickText(x, tick, stepAcross, state.language);
    svg.append(label);
  });
  const upName = svgElement("text", { class: "chart-tick plot-axis", x: shapes.left, y: shapes.top - 8 });
  upName.textContent = axisName(y);
  const acrossName = svgElement("text", { class: "chart-tick plot-axis", x: shapes.right, y: height - 4, "text-anchor": "end" });
  acrossName.textContent = axisName(x);
  svg.append(upName, acrossName);
  const dots = svgElement("g", { class: "plot-dots" });
  for (const place of shapes.places) {
    // A point of a value that the page cannot place is not drawn.
    if (Number.isFinite(place.x) && Number.isFinite(place.y)) {
      dots.append(svgElement("circle", { class: "plot-dot", cx: place.x.toFixed(1), cy: place.y.toFixed(1), r: POINT_RADIUS }));
    }
  }
  svg.append(dots, chosen);
  return { chosen, shapes };
}

// The reading of the point chosen at the top right of the chart, or none;
// what it says, for the keys and a click.
function fillPlotReading() {
  const context = plotContext;
  const index = state.plot?.chosen ?? null;
  const point = index === null ? undefined : context.answer.points[index];
  if (point === undefined) {
    context.read.replaceChildren();
    return null;
  }
  const typeName = (name) => describe(typeMessage(name));
  const reading = plotReading(point, context.x, context.y, typeName, state.language, sameValues(context.answer.points, index, context.x, context.y));
  const nodes = [describe(reading.when), " ", reading.type];
  for (const value of [reading.x, reading.y]) {
    nodes.push(" ", describe(value.name), " ", element("strong", "", describe(value.value)));
  }
  if (reading.same !== null) {
    nodes.push(" ", element("span", "plot-same", describe(reading.same)));
  }
  context.read.replaceChildren(...nodes);
  return reading;
}

// The point chosen: its frame on top, and its reading at the top right of
// the chart, which the keys and a click also say (Codex's review of the plan
// of O1: the reading never hides the points). A reading of another number of
// lines leaves the chart another room, and it is drawn again.
function renderPlotChosen(speak) {
  const context = plotContext;
  if (context === null || context.answer === null || context.read === undefined || context.chosen === undefined) {
    return;
  }
  const reading = fillPlotReading();
  const index = state.plot?.chosen ?? null;
  const place = reading === null || context.shapes === null ? undefined : context.shapes.places[index];
  const placed = place !== undefined && Number.isFinite(place.x) && Number.isFinite(place.y);
  context.chosen.setAttribute("cx", placed ? place.x.toFixed(1) : "0");
  context.chosen.setAttribute("cy", placed ? place.y.toFixed(1) : "0");
  context.chosen.setAttribute("display", placed ? "inline" : "none");
  if (Math.abs(context.head.getBoundingClientRect().height - context.headHeight) > 1) {
    context.size = null;
    scheduleRedraw();
  }
  if (speak && reading !== null) {
    const spoken = t("view.plot.spoken", {
      when: describe(reading.when),
      type: reading.type,
      x: describe(reading.x.name),
      xValue: describe(reading.x.value),
      y: describe(reading.y.name),
      yValue: describe(reading.y.value),
    });
    setText(ui.plotAnnouncer, reading.same === null ? spoken : `${spoken} ${describe(reading.same)}`);
  }
}

function choosePoint(index, speak) {
  if (state.plot === null || index === null) {
    return;
  }
  state.plot.chosen = index;
  renderPlotChosen(speak);
}

// The point under the pointer, by the places drawn (Codex's review of the
// plan of O1).
function plotPointAt(event) {
  const context = plotContext;
  const svg = context?.chart?.querySelector("svg");
  if (!svg || context.shapes === null) {
    return null;
  }
  const box = svg.getBoundingClientRect();
  return nearestPoint(context.shapes.places, event.clientX - box.left, event.clientY - box.top, PLOT_REACH);
}

function pointsPointer(event) {
  if (event.target.closest(".plot-points") !== null) {
    const index = plotPointAt(event);
    if (index !== null && index !== state.plot?.chosen) {
      choosePoint(index, false);
    }
  }
}

function pointsClick(event) {
  const sort = event.target.closest('button[data-action="plot-sort"]');
  if (sort !== null && state.plot !== null) {
    state.plot.sort = listSorted(state.plot.sort, sort.dataset.column);
    render();
    ui.plotBody.querySelector(`button[data-action="plot-sort"][data-column="${sort.dataset.column}"]`)?.focus();
    return;
  }
  if (event.target.closest(".plot-points") !== null) {
    choosePoint(plotPointAt(event), true);
  }
}

// The keys of the chart: one point before or after in the order of their
// dates and times, and the first and the last; every point can be chosen,
// also where points meet.
function pointsKeyDown(event) {
  if (event.target.closest(".plot-points") === null || plotContext?.answer == null) {
    return;
  }
  const next = plotMove(state.plot?.chosen ?? null, plotContext.answer.points.length, event.key);
  if (next !== null) {
    event.preventDefault();
    choosePoint(next, true);
  }
}

// The table of the points: one row an activity plotted, newest first at
// first, ordered by its heads as the list of a period is; its rows are added
// 400 at a time, as the table of a panel's are (Codex's review of the plan of
// O1).
function buildPlotTable(drawn, asked) {
  const columns = ["when", "type", asked.x, asked.y];
  const wrap = element("div", "list-table plot-table");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", t("view.plot.table_label", { x: t(itemKey(asked.x)), y: t(itemKey(asked.y)) }));
  const table = element("table", "t");
  const caption = element("caption", "visually-hidden", t("view.plot.table_caption"));
  const head = element("thead");
  const headRow = element("tr");
  for (const column of columns) {
    const cell = element("th", column === "when" || column === "type" ? "" : "n");
    cell.scope = "col";
    const button = element("button", "list-sort", describe(listHead(column)));
    button.type = "button";
    button.dataset.action = "plot-sort";
    button.dataset.column = column;
    if (state.plot.sort.column === column) {
      cell.setAttribute("aria-sort", state.plot.sort.descending ? "descending" : "ascending");
      const arrow = element("span", "list-arrow", state.plot.sort.descending ? "\u25bc" : "\u25b2");
      arrow.setAttribute("aria-hidden", "true");
      button.append(arrow);
    }
    cell.append(button);
    headRow.append(cell);
  }
  head.append(headRow);
  const body = element("tbody");
  table.append(caption, head, body);
  wrap.append(table);
  const typeName = (name) => describe(typeMessage(name));
  const rows = sortedListRows(drawn.points, state.plot.sort, typeName, state.language);
  let shownRows = 0;
  const sentinel = element("tr");
  const more = () => {
    const part = document.createDocumentFragment();
    for (const row of rows.slice(shownRows, shownRows + TABLE_ROWS)) {
      const line = element("tr");
      for (const column of columns) {
        const text =
          column === "when"
            ? describe(plotWhen(row, state.language))
            : column === "type"
              ? typeName(row.type)
              : listValueText(column, row.values?.[column], state.language);
        const cell = element(column === "when" ? "th" : "td", column === "when" || column === "type" ? "" : "n", text ?? "\u2014");
        if (column === "when") {
          cell.scope = "row";
        }
        line.append(cell);
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

// --- The distribution of one item (stage P1 of v2.2.0) ---------------------

// What the distribution shows now, as plotContext for the points.
let spreadContext = null;

function spreading() {
  return state.spread !== null && state.view !== null;
}

// The distribution of one item in the place of the panels, as the points:
// the item remembered (or the distance), with the period and the activity
// types of the page.
function enterSpread() {
  const key = state.view === null || comparing() ? null : spreadItemOf(state.spreadItem, state.view.items);
  if (key === null) {
    return;
  }
  listChanged("spread");
  state.spreadItem = key;
  state.spread = { table: false, chosen: null };
  state.spreadAnswer = null;
  state.spreadAsked = null;
  state.spreadStop = null;
  state.otherOpen = false;
  state.typesOpen = false;
  state.pickerOpen = false;
  state.notesOpen = null;
  state.layoutsOpen = false;
  state.layoutSaving = false;
  state.railLayoutsOpen = false;
  render();
  ui.spreadItem.focus();
  requestSpread();
}

// Back to the panels as they were, as from the points.
function leaveSpread() {
  state.spread = null;
  state.spreadAnswer = null;
  state.spreadAsked = null;
  state.spreadStop = null;
  state.spreadLoading = false;
  state.spreadSeq += 1;
  render();
  ui.otherViews.focus();
  if (state.panelsStale) {
    state.panelsStale = false;
    requestSeries();
  }
}

function spreadPayload() {
  return {
    view: state.view.view,
    item: state.spreadItem,
    period: periodRequest(state.period, state.range),
    types: typesRequest(state.counted, state.view.types),
  };
}

// Ask for the ranges as one generation, as for the points (Codex's review of
// the plan of P1): an answer of an older one is dropped when it comes; a
// ticket that the server no longer keeps opens the output again, once; an
// output that cannot be read stops the page, and another stop shows in the
// bar of the distribution.
async function requestSpread(again = true) {
  if (!spreading()) {
    return;
  }
  const seq = ++state.spreadSeq;
  state.spreadLoading = true;
  render();
  const payload = spreadPayload();
  try {
    const answer = await callApi("/api/view/spread", payload);
    if (seq !== state.spreadSeq) {
      return;
    }
    state.spreadAnswer = answer;
    state.spreadAsked = payload;
    state.spreadStop = null;
    if (state.spread !== null) {
      state.spread.chosen = null;
    }
  } catch (error) {
    if (seq !== state.spreadSeq) {
      return;
    }
    if (connectionFailure(error)) {
      // The bar says so.
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null) {
      if (await reopen()) {
        if (seq !== state.spreadSeq) {
          return;
        }
        state.spreadLoading = false;
        requestSpread(false);
        return;
      }
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
      state.stop = { code: error.code, detail: error.detail };
    } else {
      state.spreadStop = { code: error.code, detail: error.detail };
    }
  }
  if (seq === state.spreadSeq) {
    state.spreadLoading = false;
  }
  render();
}

// The item of the distribution changed; it is remembered, and the ranges are
// asked for again.
function chooseSpreadItem(key) {
  if (!spreading()) {
    return;
  }
  if (spreadItemOf(key, state.view.items) !== key) {
    render();
    return;
  }
  state.spreadItem = key;
  state.spread.chosen = null;
  rememberItems(true);
  requestSpread();
}

// The answer of the item chosen: an answer of another item on its way is
// not drawn, as for the points.
function spreadAnswerNow() {
  const answer = state.spreadAnswer;
  const asked = state.spreadAsked;
  return answer !== null && asked !== null && asked.item === state.spreadItem ? answer : null;
}

// The items of the list: those of the points.
function renderSpreadItems(select, chosen) {
  const items = (state.view?.items ?? []).filter(plotItem);
  const signature = JSON.stringify([items.map((item) => item.key), chosen, state.language]);
  if (select.dataset.signature !== signature) {
    select.replaceChildren(
      ...items.map((item) => {
        const option = element("option", "", t(itemKey(item.key)));
        option.value = item.key;
        return option;
      }),
    );
    select.dataset.signature = signature;
  }
  select.value = chosen;
}

// The bar of the distribution, its lines, and its chart or table: the line
// of the numbers, the words of a wider width, and, for the pace, which way is
// faster; no words of a relation, which a distribution does not show (the
// checker's review of the plan of P1).
function renderSpread(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const spread = viewing && spreading() ? state.spread : null;
  ui.spread.hidden = spread === null;
  ui.spreadOff.hidden = spread === null;
  if (spread === null) {
    spreadContext = null;
    ui.spreadBody.replaceChildren();
    return;
  }
  const [before = "", after = ""] = t("view.spread.title", { item: "\u0001" }).split("\u0001");
  setText(ui.spreadBefore, before);
  setText(ui.spreadAfter, after);
  renderSpreadItems(ui.spreadItem, state.spreadItem);
  const drawn = spreadAnswerNow();
  ui.spreadTable.disabled = drawn === null || !drawn.counts.length;
  ui.spreadTable.setAttribute("aria-pressed", String(spread.table));
  ui.spreadTableChart.hidden = !spread.table;
  ui.spreadTableTable.hidden = spread.table;
  setText(ui.spreadLoading, state.spreadLoading ? t("view.loading") : "");
  ui.spreadStop.hidden = state.spreadStop === null;
  if (!ui.spreadStop.hidden) {
    renderStop(ui.spreadStop, null, ui.spreadStopLines, ui.spreadStopCode, stopBox(state.spreadStop.code, state.spreadStop.detail, state.productVersion));
  }
  setText(ui.spreadCount, drawn === null ? "" : describe(spreadCount(drawn, state.language)));
  const wide = drawn === null ? null : spreadWide(state.spreadAsked.item, drawn, state.language);
  ui.spreadWide.hidden = wide === null;
  setText(ui.spreadWide, wide === null ? "" : describe(wide));
  ui.spreadFaster.hidden = drawn === null || state.spreadAsked.item !== "pace";
  ui.spreadNone.hidden = drawn === null || drawn.counts.length > 0;
  renderSpreadBody(drawn);
}

// The chart of the ranges or their table, drawn again only when what they
// show changes; the range chosen moves without drawing them again.
function renderSpreadBody(drawn) {
  const spread = state.spread;
  if (spread === null) {
    return;
  }
  // While the ranges of a new request are on their way, what shows stays,
  // dimmed, so that the focus stays where it is, as for the points: those of
  // the same item only, never ranges in the units of another (Codex's review
  // of the diff of P1).
  ui.spreadBody.classList.toggle("waiting", state.spreadLoading);
  if (drawn === null && state.spreadLoading && spreadContext !== null && spreadContext.answer !== null && spreadContext.item === state.spreadItem) {
    return;
  }
  const box = ui.spreadBody.getBoundingClientRect();
  const size = [Math.round(box.width), Math.round(box.height)];
  const wanted = { answer: drawn, table: spread.table, language: state.language, size: size.join(" ") };
  if (spreadContext !== null && Object.keys(wanted).every((key) => spreadContext[key] === wanted[key])) {
    renderSpreadChosen(false);
    return;
  }
  spreadContext = { ...wanted, item: drawn === null ? null : state.spreadAsked.item, shapes: null };
  // The focus stays where it was, on the chart or the table, drawn again in
  // its place.
  const focused = ui.spreadBody.contains(document.activeElement) ? document.activeElement : null;
  const refocus = focused?.closest(".spread-bars") ? ".spread-bars" : focused?.closest(".spread-table") ? ".spread-table" : null;
  if (drawn === null || !drawn.counts.length) {
    ui.spreadBody.replaceChildren();
    return;
  }
  const key = state.spreadAsked.item;
  if (spread.table) {
    ui.spreadBody.replaceChildren(buildSpreadTable(drawn, key));
  } else {
    const chart = buildSpreadChart(key);
    ui.spreadBody.replaceChildren(chart.section);
    Object.assign(spreadContext, chart, { key });
    fillSpreadReading();
    const room = chart.chart.getBoundingClientRect();
    Object.assign(spreadContext, drawSpreadBars(chart, drawn, key, [room.width, room.height]), { headHeight: chart.head.getBoundingClientRect().height });
    renderSpreadChosen(false);
  }
  if (refocus !== null) {
    ui.spreadBody.querySelector(refocus)?.focus();
  }
}

// The chart: its head, with the reading of the range chosen, and its frame,
// which takes the keys and the pointer, as the chart of the points.
function buildSpreadChart(key) {
  const section = element("section", "panel-view plot-view");
  section.setAttribute("aria-labelledby", "spread-title");
  const head = element("div", "panel-head plot-head");
  const read = element("span", "panel-read plot-read");
  read.setAttribute("aria-hidden", "true");
  head.append(element("span", "spacer"), read);
  const chart = element("div", "plot-points spread-bars");
  chart.tabIndex = 0;
  chart.setAttribute("role", "img");
  chart.setAttribute("aria-label", t("view.spread.label", { item: t(itemKey(key)) }));
  section.append(head, chart);
  return { section, head, chart, read };
}

// The ticks of the counts up at the left, the words of the ends of the
// ranges across, the names of the count and of the item, and a bar a range
// with an activity; the range chosen framed on top.
function drawSpreadBars(frame, drawn, key, size) {
  // As large as its room, which a small window keeps small.
  const width = Math.max(240, Math.round(size[0]));
  const height = Math.max(120, Math.round(size[1]));
  const shapes = spreadShapes(drawn.counts, drawn.first, { width, height });
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, width, height, "aria-hidden": "true", focusable: "false" });
  const chosen = svgElement("rect", { class: "spread-chosen", display: "none" });
  frame.chart.append(svg);
  if (shapes === null) {
    return { chosen, shapes };
  }
  for (const tick of shapes.up.ticks) {
    const at = shapes.y(tick).toFixed(1);
    svg.append(svgElement("line", { class: "chart-grid", x1: shapes.left, x2: shapes.right, y1: at, y2: at }));
    const label = svgElement("text", { class: "chart-tick", x: shapes.left - 8, y: (Number(at) + 4).toFixed(1), "text-anchor": "end" });
    label.textContent = countText(tick, state.language);
    svg.append(label);
  }
  const bars = svgElement("g", { class: "spread-bars-drawn" });
  shapes.bars.forEach((bar, index) => {
    // A range of no activity has no bar.
    if (drawn.counts[index] > 0) {
      bars.append(
        svgElement("rect", {
          class: "spread-bar",
          x: bar.x0.toFixed(2),
          y: bar.y.toFixed(1),
          width: Math.max(0, bar.x1 - bar.x0).toFixed(2),
          height: Math.max(0, shapes.bottom - bar.y).toFixed(1),
        }),
      );
    }
  });
  svg.append(bars);
  shapes.ends.forEach((end, index, ends) => {
    const at = shapes.x(end);
    // The words of the ends at the ends stay inside the chart.
    const anchor = index === 0 && at - shapes.left < 24 ? "start" : index === ends.length - 1 && shapes.right - at < 24 ? "end" : "middle";
    const label = svgElement("text", { class: "chart-tick", x: at.toFixed(1), y: shapes.bottom + 16, "text-anchor": anchor });
    label.textContent = spreadEndWords(key, drawn, end, state.language);
    svg.append(label);
  });
  const upName = svgElement("text", { class: "chart-tick plot-axis", x: shapes.left, y: shapes.top - 8 });
  upName.textContent = t("view.spread.head_count");
  const acrossName = svgElement("text", { class: "chart-tick plot-axis", x: shapes.right, y: height - 4, "text-anchor": "end" });
  acrossName.textContent = axisName(key);
  svg.append(upName, acrossName, chosen);
  return { chosen, shapes };
}

// The reading of the range chosen at the top right of the chart, or none;
// what it says, for the keys and a click.
function fillSpreadReading() {
  const context = spreadContext;
  const index = state.spread?.chosen ?? null;
  if (index === null || context.answer === null || index >= context.answer.counts.length) {
    context.read.replaceChildren();
    return null;
  }
  const reading = spreadReading(context.key, context.answer, index, state.language);
  context.read.replaceChildren(describe(reading));
  return reading;
}

// The range chosen: its frame on top, as high as the chart and at least a
// few pixels wide where the range is narrower, and its reading at the top
// right, which the keys and a click also say; a reading of another number of
// lines leaves the chart another room, and it is drawn again.
function renderSpreadChosen(speak) {
  const context = spreadContext;
  if (context === null || context.answer === null || context.read === undefined || context.chosen === undefined) {
    return;
  }
  const reading = fillSpreadReading();
  const index = state.spread?.chosen ?? null;
  const bar = reading === null || context.shapes === null ? undefined : context.shapes.bars[index];
  if (bar === undefined) {
    context.chosen.setAttribute("display", "none");
  } else {
    const half = Math.max(SPREAD_CHOSEN_WIDTH, bar.x1 - bar.x0) / 2;
    const middle = (bar.x0 + bar.x1) / 2;
    context.chosen.setAttribute("x", (middle - half).toFixed(2));
    context.chosen.setAttribute("width", (half * 2).toFixed(2));
    context.chosen.setAttribute("y", context.shapes.top.toFixed(1));
    context.chosen.setAttribute("height", (context.shapes.bottom - context.shapes.top).toFixed(1));
    context.chosen.setAttribute("display", "inline");
  }
  if (Math.abs(context.head.getBoundingClientRect().height - context.headHeight) > 1) {
    context.size = null;
    scheduleRedraw();
  }
  if (speak && reading !== null) {
    setText(ui.spreadAnnouncer, describe(reading));
  }
}

function chooseRange(index, speak) {
  if (state.spread === null || index === null) {
    return;
  }
  state.spread.chosen = index;
  renderSpreadChosen(speak);
}

// The range under the pointer, by the places drawn.
function spreadRangeUnder(event) {
  const context = spreadContext;
  const svg = context?.chart?.querySelector("svg");
  if (!svg || context.shapes === null) {
    return null;
  }
  const box = svg.getBoundingClientRect();
  return spreadRangeAt(context.shapes, event.clientX - box.left);
}

function spreadPointer(event) {
  if (event.target.closest(".spread-bars") !== null) {
    const index = spreadRangeUnder(event);
    if (index !== null && index !== state.spread?.chosen) {
      chooseRange(index, false);
    }
  }
}

function spreadClick(event) {
  if (event.target.closest(".spread-bars") !== null) {
    chooseRange(spreadRangeUnder(event), true);
  }
}

// The keys of the chart: one range before or after, those of no activity
// among them, and the first and the last (the checker's P1-3).
function spreadKeyDown(event) {
  if (event.target.closest(".spread-bars") === null || spreadContext?.answer == null) {
    return;
  }
  const next = spreadMove(state.spread?.chosen ?? null, spreadContext.answer.counts.length, event.key);
  if (next !== null) {
    event.preventDefault();
    chooseRange(next, true);
  }
}

// The table of the ranges: a row a range in their order, those of no
// activity among them, 200 rows at most, made at once (Codex's review of the
// plan of P1).
function buildSpreadTable(drawn, key) {
  const wrap = element("div", "list-table plot-table spread-table");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", t("view.spread.table_label", { item: t(itemKey(key)) }));
  const table = element("table", "t");
  const caption = element("caption", "visually-hidden", t("view.spread.table_caption"));
  const head = element("thead");
  const headRow = element("tr");
  const rangeHead = element("th", "", axisName(key));
  rangeHead.scope = "col";
  const countHead = element("th", "n", t("view.spread.head_count"));
  countHead.scope = "col";
  headRow.append(rangeHead, countHead);
  head.append(headRow);
  const body = element("tbody");
  drawn.counts.forEach((count, index) => {
    const line = element("tr");
    const range = element("th", "", describe(spreadRange(key, drawn, index, state.language)));
    range.scope = "row";
    line.append(range, element("td", "n", countText(count, state.language)));
    body.append(line);
  });
  table.append(caption, head, body);
  wrap.append(table);
  return wrap;
}

// --- The view by shoes (stage S1 of v2.2.0) ---------------------------------

// The rows drawn of the shoes, what they draw with, and what they were drawn
// for (an answer, as a table or not, in a language).
let shoeRows = [];
let shoesContext = null;
let shoesDrawn = null;

function shoesShown() {
  return state.shoes !== null && state.view !== null;
}

// The distance of each pair of shoes by month in the place of the panels, as
// the distribution: with the period and the activity types of the page,
// where the output has shoes to show.
function enterShoes() {
  if (state.view === null || comparing() || shoesWhy(state.shoesAvailable) !== null) {
    return;
  }
  listChanged("shoes");
  state.shoes = { table: false, cursor: null };
  state.shoesAnswer = null;
  state.shoesAsked = null;
  state.shoesStop = null;
  state.otherOpen = false;
  state.typesOpen = false;
  state.pickerOpen = false;
  state.notesOpen = null;
  state.layoutsOpen = false;
  state.layoutSaving = false;
  state.railLayoutsOpen = false;
  render();
  ui.shoesTitle.focus();
  requestShoes();
}

// Back to the panels as they were, as from the distribution.
function leaveShoes() {
  state.shoes = null;
  state.shoesAnswer = null;
  state.shoesAsked = null;
  state.shoesStop = null;
  state.shoesLoading = false;
  state.shoesSeq += 1;
  render();
  ui.otherViews.focus();
  if (state.panelsStale) {
    state.panelsStale = false;
    requestSeries();
  }
}

function shoesPayload() {
  return {
    view: state.view.view,
    period: periodRequest(state.period, state.range),
    types: typesRequest(state.counted, state.view.types),
  };
}

// Ask for the shoes as one generation, as for the distribution: an answer of
// an older one is dropped when it comes; a ticket that the server no longer
// keeps opens the output again, once; an output that cannot be read stops the
// page, and another stop shows in the bar of the shoes. The answer says
// again whether the output has shoes (Codex's review of the plan of S1).
async function requestShoes(again = true) {
  if (!shoesShown()) {
    return;
  }
  const seq = ++state.shoesSeq;
  state.shoesLoading = true;
  render();
  const payload = shoesPayload();
  const asked = ++state.availableAsks;
  try {
    const answer = await callApi("/api/view/shoes", payload);
    if (seq !== state.shoesSeq) {
      return;
    }
    state.shoesAnswer = answer;
    state.shoesAsked = payload;
    state.shoesStop = null;
    if (answer.available && asked > state.availableFrom) {
      state.shoesAvailable = answer.available;
      state.availableFrom = asked;
    }
  } catch (error) {
    if (seq !== state.shoesSeq) {
      return;
    }
    if (connectionFailure(error)) {
      // The bar says so.
    } else if (error.code === "VIEW_NOT_OPEN" && again && state.target !== null) {
      if (await reopen()) {
        if (seq !== state.shoesSeq) {
          return;
        }
        state.shoesLoading = false;
        requestShoes(false);
        return;
      }
    } else if (OUTPUT_STOPS.includes(error.code)) {
      state.view = null;
      setAnswer(null);
      state.compare = null;
      state.plot = null;
      state.spread = null;
      state.shoes = null;
      state.stop = { code: error.code, detail: error.detail };
    } else {
      state.shoesStop = { code: error.code, detail: error.detail };
    }
  }
  if (seq === state.shoesSeq) {
    state.shoesLoading = false;
  }
  render();
}

// The bar of the shoes, its lines, its rows or tables, and its notes, which
// show only for a count of 1 or more (the checker's review of the counts).
function renderShoes(live) {
  const viewing = live && state.view !== null && state.opening === null;
  const shoes = viewing && shoesShown() ? state.shoes : null;
  ui.shoes.hidden = shoes === null;
  ui.shoesOff.hidden = shoes === null;
  if (shoes === null) {
    shoeRows = [];
    shoesContext = null;
    shoesDrawn = null;
    ui.shoesPanels.replaceChildren();
    ui.shoesAxis.replaceChildren();
    return;
  }
  const drawn = state.shoesAnswer;
  ui.shoesTable.disabled = drawn === null || !drawn.shoes.length;
  ui.shoesTable.setAttribute("aria-pressed", String(shoes.table));
  ui.shoesTableChart.hidden = !shoes.table;
  ui.shoesTableTable.hidden = shoes.table;
  setText(ui.shoesLoading, state.shoesLoading ? t("view.loading") : "");
  ui.shoesStop.hidden = state.shoesStop === null;
  if (!ui.shoesStop.hidden) {
    renderStop(ui.shoesStop, null, ui.shoesStopLines, ui.shoesStopCode, stopBox(state.shoesStop.code, state.shoesStop.detail, state.productVersion));
  }
  setText(ui.shoesCount, drawn === null ? "" : describe(shoesCount(drawn)));
  ui.shoesNone.hidden = drawn === null || drawn.shoes.length > 0;
  const notes = drawn === null ? [] : shoesNotes(drawn).map(describe);
  if (JSON.stringify(notes) !== ui.shoesNotes.dataset.notes) {
    ui.shoesNotes.replaceChildren(...notes.map((note) => element("p", "compare-note", note)));
    ui.shoesNotes.dataset.notes = JSON.stringify(notes);
  }
  renderShoesBody(drawn);
}

// The rows of the shoes, or their tables, built again only for another
// answer, way, or language; otherwise only the charts whose size changed.
function renderShoesBody(drawn) {
  const shoes = state.shoes;
  if (shoes === null) {
    return;
  }
  if (shoesDrawn !== null && shoesDrawn[0] === drawn && shoesDrawn[1] === shoes.table && shoesDrawn[2] === state.language) {
    renderShoesCharts();
    return;
  }
  const focused = ui.shoesPanels.contains(document.activeElement) ? (document.activeElement.dataset.plot ?? null) : null;
  plotWatcher?.disconnect();
  shoeRows = [];
  shoesContext = null;
  ui.shoesAxis.replaceChildren();
  delete ui.shoesAxis.dataset.width;
  shoesDrawn = [drawn, shoes.table, state.language];
  if (drawn === null || !drawn.shoes.length) {
    ui.shoesPanels.replaceChildren();
    ui.shoesAxis.hidden = true;
    return;
  }
  // The months of the period, once, for every pair: their days, as the time
  // axis of the panels, across the years (Codex's review of the plan of S1),
  // and one scale for all.
  const periods = periodDays(drawn.periods);
  const lines = drawn.shoes.map((shoe) => ({ values: shoe.values.map((value) => (Number.isFinite(value) ? shown("dist", value) : null)) }));
  shoesContext = { periods, lines, shared: extent(lines), start: periods[0].start, end: periods[periods.length - 1].end };
  if (shoes.cursor === null || shoes.cursor >= periods.length) {
    shoes.cursor = periods.length - 1;
  }
  if (shoes.table) {
    ui.shoesPanels.replaceChildren(...buildShoesTables(drawn));
  } else {
    shoeRows = drawn.shoes.map((shoe, index) => buildShoeRow(shoe, index));
    ui.shoesPanels.replaceChildren(...shoeRows.map((entry) => entry.section));
  }
  ui.shoesAxis.hidden = shoes.table;
  renderShoesCharts();
  moveShoesCross(shoes.cursor, null);
  for (const entry of shoeRows) {
    plotWatcher?.observe(entry.plot);
  }
  if (focused !== null) {
    ui.shoesPanels.querySelector(`[data-plot="${focused}"]`)?.focus({ preventScroll: true });
  }
}

// A row of a pair of shoes, as a row of a year: its name (cut where it is
// long, before what tells it apart), its distance in this period, its
// reading, and its chart.
function buildShoeRow(shoe, index) {
  const section = element("section", "panel-view compare-row shoe-row");
  const headingId = `shoe-${index}`;
  section.setAttribute("aria-labelledby", headingId);
  const head = element("div", "panel-head");
  const heading = element("h4", "panel-name shoe-name");
  heading.id = headingId;
  const [name, added] = shoeWords(shoe, state.language);
  heading.append(element("span", "shoe-own", describe(name)));
  if (added !== null) {
    heading.append(element("span", "shoe-added", describe(added)));
  }
  head.append(heading);
  const whole = element("span", "compare-whole", `${t("view.shoes.whole")} `);
  whole.append(element("strong", "", Number.isFinite(shoe.distance) ? describe(valueMessage("dist", shoe.distance, state.language)) : t("view.no_value")));
  head.append(whole);
  const read = element("span", "panel-read");
  read.setAttribute("aria-hidden", "true");
  head.append(read);
  section.append(head);
  const body = element("div", "panel-chart");
  const plot = element("div", "plot");
  plot.tabIndex = 0;
  plot.setAttribute("role", "img");
  plot.dataset.plot = String(index);
  plot.setAttribute("aria-label", t("view.shoes.row_label", { shoe: describe(shoeName(shoe, state.language)) }));
  body.append(plot);
  section.append(body);
  return { section, plot, read, index, size: null, shapes: null, cross: null };
}

// The chart of a row: the bars of its months, in the first color, on the
// scale of every pair; the months that a period cuts hollow, as the rows of
// the years.
function drawShoePlot(entry) {
  const context = shoesContext;
  const plot = entry.plot;
  const width = plot.clientWidth;
  const height = plot.clientHeight;
  entry.size = `${width} ${height}`;
  entry.shapes = null;
  entry.cross = null;
  if (context === null || width < 60 || height < 24) {
    plot.replaceChildren();
    return;
  }
  const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, "aria-hidden": "true", focusable: "false" });
  const shapes = panelShapes({ lines: [context.lines[entry.index]], periods: context.periods, start: context.start, end: context.end, width, height, total: true, shared: context.shared });
  entry.shapes = shapes;
  if (shapes.empty) {
    plot.replaceChildren(svg, element("span", "panel-empty", t("view.summary.none")));
    return;
  }
  appendScale(svg, "dist", shapes, width - PLOT_RIGHT);
  appendMarks(svg, shapes.lines[0], "c1", null, { outlined: true });
  const cross = svgElement("g", { class: "cross" });
  cross.setAttribute("display", "none");
  const crossLine = svgElement("line", { class: "chart-cross", y1: shapes.top, y2: shapes.top + shapes.plotHeight });
  const crossDot = svgElement("circle", { class: "chart-cross-dot c1", r: 4.5 });
  cross.append(crossLine, crossDot);
  svg.append(cross);
  plot.replaceChildren(svg);
  Object.assign(entry, { cross, crossLine, crossDot });
}

// Draw the rows whose size changed, the axis at the width of the rows, and
// the cross line again.
function renderShoesCharts() {
  if (shoesContext === null) {
    return;
  }
  let changed = false;
  for (const entry of shoeRows) {
    if (entry.size !== `${entry.plot.clientWidth} ${entry.plot.clientHeight}`) {
      drawShoePlot(entry);
      changed = true;
    }
  }
  const first = shoeRows[0];
  if (first !== undefined) {
    const width = first.plot.clientWidth;
    if (changed || ui.shoesAxis.dataset.width !== String(width)) {
      drawTimeAxis(shoesContext.start, shoesContext.end, width, ui.shoesAxis);
      ui.shoesAxis.dataset.width = String(width);
    }
  }
  if (changed && state.shoes !== null) {
    moveShoesCross(state.shoes.cursor, null);
  }
}

// Move the cross line of the shoes to one month: every row reads it, and the
// row of the keys says it (``row``, or null).
function moveShoesCross(cursor, row) {
  const context = shoesContext;
  const answer = state.shoesAnswer;
  if (context === null || answer === null || state.shoes === null || cursor === null) {
    return;
  }
  const at = Math.max(0, Math.min(context.periods.length - 1, cursor));
  state.shoes.cursor = at;
  for (const entry of shoeRows) {
    const words = describe(shoesRead(answer.periods[at], answer.shoes[entry.index].values[at], state.language));
    setText(entry.read, words);
    if (entry.index === row) {
      setText(ui.shoesAnnouncer, `${describe(shoeName(answer.shoes[entry.index], state.language))} ${words}`);
    }
    if (entry.shapes === null || entry.cross === null) {
      continue;
    }
    const x = periodMiddle(entry.shapes.scale, context.periods[at]).toFixed(1);
    entry.crossLine.setAttribute("x1", x);
    entry.crossLine.setAttribute("x2", x);
    const value = context.lines[entry.index].values[at];
    if (Number.isFinite(value)) {
      entry.crossDot.setAttribute("cx", x);
      entry.crossDot.setAttribute("cy", entry.shapes.y(value).toFixed(1));
      entry.crossDot.removeAttribute("display");
    } else {
      entry.crossDot.setAttribute("display", "none");
    }
    entry.cross.removeAttribute("display");
  }
}

// The keys of a row: Left and Right a month, Home and End the first and the
// last, as the rows of the years.
function shoesKeyDown(event) {
  const plot = event.target.closest?.("[data-plot]");
  if (plot == null || state.shoes === null || shoesContext === null) {
    return;
  }
  const last = shoesContext.periods.length - 1;
  const moves = { ArrowLeft: state.shoes.cursor - 1, ArrowRight: state.shoes.cursor + 1, Home: 0, End: last };
  if (!Object.hasOwn(moves, event.key)) {
    return;
  }
  event.preventDefault();
  moveShoesCross(moves[event.key], Number(plot.dataset.plot));
}

// The pointer over a row moves the cross line to the nearest month.
function shoesPointer(event) {
  const plot = event.target.closest?.("[data-plot]");
  const entry = plot == null ? undefined : shoeRows.find((each) => each.plot === plot);
  if (entry === undefined || entry.shapes === null || shoesContext === null || state.shoes === null) {
    return;
  }
  const at = nearestPeriod(shoesContext.periods, entry.shapes.scale, event.clientX - plot.getBoundingClientRect().left);
  if (at !== null && at !== state.shoes.cursor) {
    moveShoesCross(at, null);
  }
}

// The tables of the shoes: a row a pair, and a row a month with a column a
// pair (Codex's review of the plan of S1).
function buildShoesTables(drawn) {
  const { summary, months } = shoesTables(drawn, state.language);
  return [
    buildShoesTable("shoes-table-name", t("view.shoes.table_label"), t("view.shoes.table_caption"), summary),
    buildShoesTable("shoes-months-name", t("view.shoes.months_label"), t("view.shoes.months_caption"), months, "shoes-months"),
  ];
}

// A table of the shoes; the table by month (of the kind "shoes-months")
// keeps its months at the left while its pairs scroll by (the checker's
// review of the diff of S1).
function buildShoesTable(id, label, caption, { heads, rows }, kind = null) {
  const section = element("section", kind === null ? "panel-view compare-table table" : `panel-view compare-table table ${kind}`);
  section.setAttribute("aria-labelledby", id);
  const head = element("div", "panel-head");
  const heading = element("h4", "panel-name", label);
  heading.id = id;
  head.append(heading);
  section.append(head);
  const wrap = element("div", "panel-table");
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", label);
  const table = element("table", "t");
  const headRow = element("tr");
  heads.forEach((entry, index) => {
    const cell = element("th", index === 0 ? "" : "n", describe(entry));
    cell.scope = "col";
    headRow.append(cell);
  });
  const thead = element("thead");
  thead.append(headRow);
  const tbody = element("tbody");
  for (const row of rows) {
    const tr = element("tr");
    const first = element("th", "", describe(row[0]));
    first.scope = "row";
    tr.append(first, ...row.slice(1).map((cell) => element("td", "n", describe(cell))));
    tbody.append(tr);
  }
  table.append(element("caption", "visually-hidden", caption), thead, tbody);
  wrap.append(table);
  section.append(wrap);
  return section;
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
  renderCompare(live);
  renderPlot(live);
  renderSpread(live);
  renderShoes(live);
  // The window of the saving after every view, as it reads their charts
  // (Codex's reviews of the diff of R1 and of the plan of R2).
  renderSave(live && state.view !== null && state.opening === null);
  renderSaveNotice();
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
  listChanged("full");
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
  listChanged("full");
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
  const plot = event.target.closest(".plot");
  if (plot !== null && ui.panels.contains(plot)) {
    plotClick(event, plot);
    return;
  }
  const button = event.target.closest("button[data-action]");
  if (button === null || !ui.panels.contains(button)) {
    return;
  }
  const key = button.dataset.key;
  switch (button.dataset.action) {
    case "list-close":
      closeList(true);
      return;
    case "list-sort":
      sortList(button.dataset.column);
      return;
    case "table":
      listChanged("table");
      if (state.tables.has(key)) {
        state.tables.delete(key);
      } else {
        state.tables.add(key);
      }
      break;
    case "big":
      listChanged("big");
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
      listChanged("big");
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
    case "compare":
      listChanged("compare");
      enterCompare(key);
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
  // The marks (stage M1 of v2.2.0): whether they show is remembered with the
  // view; Escape closes a question first, and then the window; Enter in a
  // field adds or saves.
  ui.marksShown.addEventListener("change", changeMarksShown);
  window.addEventListener("resize", fitMarksWindow);
  window.addEventListener("resize", fitRecapWindow);
  window.addEventListener("resize", fitSaveWindow);
  ui.marksOpen.addEventListener("click", () => openMarks(!state.marksOpen));
  ui.marksPopClose.addEventListener("click", () => openMarks(false));
  // The summary of the panels (stage Q1 of v2.2.0).
  ui.recapOpen.addEventListener("click", () => openRecap(!state.recapOpen));
  ui.recapClose.addEventListener("click", () => openRecap(false));
  ui.recapPop.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      openRecap(false);
    }
  });
  // Saving as an image (stage R1 of v2.2.0): Escape in the window closes it.
  ui.saveOpen.addEventListener("click", () => openSave(!(state.saveOpen && state.saveFrom === "panels"), "panels"));
  // The bars of the other views (stage R2 of v2.2.0).
  for (const each of ["compare", "plot", "spread", "shoes"]) {
    saveButton(each).addEventListener("click", () => openSave(!(state.saveOpen && state.saveFrom === each), each));
  }
  ui.saveClose.addEventListener("click", () => openSave(false));
  ui.saveCancel.addEventListener("click", () => openSave(false));
  ui.saveAll.addEventListener("change", () => changeSave({ saveScope: "all" }));
  // One panel is the panel the list shows when it is chosen, which stays
  // chosen (Codex's review of the diff of R1).
  ui.saveOne.addEventListener("change", () => changeSave({ saveScope: "one", savePanel: state.savePanel ?? (ui.savePanel.value || null) }));
  ui.savePanel.addEventListener("change", () => changeSave({ saveScope: "one", savePanel: ui.savePanel.value }));
  ui.saveLight.addEventListener("change", () => changeSave({ saveColors: "light" }));
  ui.saveScreen.addEventListener("change", () => changeSave({ saveColors: "screen" }));
  ui.saveMarks.addEventListener("change", () => changeSave({ saveMarks: ui.saveMarks.checked }));
  ui.saveGo.addEventListener("click", saveImage);
  ui.savePop.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      openSave(false);
    }
  });
  ui.marksList.addEventListener("click", marksAction);
  ui.markSave.addEventListener("click", saveMark);
  ui.markCancel.addEventListener("click", () => editMark(null));
  ui.marksPop.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      if (state.markAsk !== null) {
        const asked = state.markAsk;
        state.markAsk = null;
        render();
        ui.marksList.querySelector(`[data-op="remove"][data-id="${CSS.escape(asked)}"]`)?.focus();
      } else {
        openMarks(false);
      }
    } else if (event.key === "Enter" && event.target.matches("input")) {
      event.preventDefault();
      saveMark();
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
  ui.compareItem.addEventListener("change", chooseCompareItem);
  for (const button of ui.compareModes) {
    button.addEventListener("click", () => chooseCompareMode(button.dataset.compareMode));
  }
  ui.compareAbout.addEventListener("click", () => {
    state.compare.about = !state.compare.about;
    render();
  });
  ui.compareMonth.addEventListener("change", chooseCompareMonth);
  for (const button of ui.compareBys) {
    button.addEventListener("click", () => chooseCompareBy(button.dataset.compareBy));
  }
  ui.compareWeeks.addEventListener("change", chooseCompareWeeks);
  ui.compareRaces.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-race]");
    if (button !== null) {
      toggleCompareRace(button.dataset.race);
    }
  });
  ui.compareSeries.addEventListener("change", () => {
    state.compare.series = ui.compareSeries.value;
    render();
  });
  ui.compareTable.addEventListener("click", () => {
    state.compare.table = !state.compare.table;
    render();
  });
  ui.compareBack.addEventListener("click", leaveCompare);
  // The other views and the points of two items (stage O1 of v2.2.0).
  ui.otherViews.addEventListener("click", () => setOtherViews(!state.otherOpen, state.otherOpen ? null : "first"));
  ui.otherViews.addEventListener("keydown", otherButtonKey);
  ui.otherMenu.addEventListener("keydown", otherMenuKey);
  ui.otherPlot.addEventListener("click", () => {
    setOtherViews(false);
    enterPlot();
  });
  ui.otherSpread.addEventListener("click", () => {
    setOtherViews(false);
    enterSpread();
  });
  // The view by shoes (stage S1 of v2.2.0).
  ui.otherShoes.addEventListener("click", () => {
    // An item that cannot be chosen does nothing, and the menu stays.
    if (shoesWhy(state.shoesAvailable) !== null) {
      return;
    }
    setOtherViews(false);
    enterShoes();
  });
  ui.shoesTable.addEventListener("click", () => {
    if (state.shoes !== null) {
      state.shoes.table = !state.shoes.table;
      render();
    }
  });
  ui.shoesBack.addEventListener("click", leaveShoes);
  ui.shoesPanels.addEventListener("pointermove", shoesPointer);
  ui.shoesPanels.addEventListener("keydown", shoesKeyDown);
  document.addEventListener("pointerdown", (event) => {
    if (state.otherOpen && event.target.closest(".other-views") === null) {
      setOtherViews(false);
    }
  });
  ui.plotX.addEventListener("change", () => choosePlotItem("x", ui.plotX.value));
  ui.plotY.addEventListener("change", () => choosePlotItem("y", ui.plotY.value));
  ui.plotTable.addEventListener("click", () => {
    if (state.plot !== null) {
      state.plot.table = !state.plot.table;
      render();
    }
  });
  ui.plotBack.addEventListener("click", leavePlot);
  ui.plotBody.addEventListener("pointermove", pointsPointer);
  ui.plotBody.addEventListener("click", pointsClick);
  ui.plotBody.addEventListener("keydown", pointsKeyDown);
  // The distribution of one item (stage P1 of v2.2.0).
  ui.spreadItem.addEventListener("change", () => chooseSpreadItem(ui.spreadItem.value));
  ui.spreadTable.addEventListener("click", () => {
    if (state.spread !== null) {
      state.spread.table = !state.spread.table;
      render();
    }
  });
  ui.spreadBack.addEventListener("click", leaveSpread);
  ui.spreadBody.addEventListener("pointermove", spreadPointer);
  ui.spreadBody.addEventListener("click", spreadClick);
  ui.spreadBody.addEventListener("keydown", spreadKeyDown);
  ui.compareYears.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-year]");
    if (button !== null) {
      toggleCompareYear(Number(button.dataset.year));
    }
  });
  ui.comparePanels.addEventListener("keydown", (event) => {
    // Esc puts back a year stood out, on its chart or a key of its legend
    // (stage L3 of v2.2.0); without one, the page takes it.
    if (event.key === "Escape" && state.compare?.lit && event.target.matches?.('.plot[data-plot="one"], button.key[data-lit]')) {
      event.preventDefault();
      standOut(null);
    } else if (event.target.classList?.contains("plot")) {
      compareKey(event);
    } else if (event.target.classList?.contains("calendar")) {
      calendarKeyDown(event);
    }
  });
  ui.comparePanels.addEventListener("pointermove", (event) => {
    if (event.target.closest?.(".plot")) {
      comparePointer(event);
    } else if (event.target.closest?.(".calendar")) {
      calendarPointer(event);
    }
  });
  // The strips of a calendar take a click and say the day that the focus
  // comes to (stage N1 of v2.2.0); the keys of the legend of one panel and
  // its chart stand a year out (stage L3).
  ui.comparePanels.addEventListener("click", (event) => {
    const key = event.target.closest?.("button.key[data-lit]") ?? null;
    if (key !== null) {
      standOut(key.dataset.lit);
    } else if (event.target.closest?.('.plot[data-plot="one"]')) {
      compareClick(event);
    } else if (event.target.closest?.(".calendar")) {
      calendarClick(event);
    }
  });
  ui.comparePanels.addEventListener("focusin", (event) => {
    if (event.target.classList?.contains("calendar")) {
      calendarFocus(event);
    }
  });
  ui.compareCalendarAbout.addEventListener("click", () => {
    state.compare.calendarAbout = !state.compare.calendarAbout;
    render();
  });
  ui.panels.addEventListener("click", panelAction);
  ui.panels.addEventListener("keydown", (event) => {
    if (event.target.classList?.contains("plot")) {
      plotKey(event);
    } else if (event.key === "Escape" && listBox?.contains(event.target)) {
      // The list closes by Esc, and the focus goes back to its chart (stage
      // M3 of v2.2.0).
      event.preventDefault();
      closeList(true);
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
    const watcher = new ResizeObserver(scheduleRedraw);
    watcher.observe(ui.panels);
    watcher.observe(ui.comparePanels);
    watcher.observe(ui.plotBody);
    watcher.observe(ui.spreadBody);
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
    const compare = compareToOpen(state.settings);
    state.compareMode = compare.mode;
    state.compareMonth = compare.month;
    const by = compareByToOpen(state.settings);
    state.compareBy = by.by;
    state.compareWeeks = by.weeks;
    state.plotPair = plotPairToOpen(state.settings);
    state.spreadItem = spreadItemToOpen(state.settings);
    state.wantedTypes = Array.isArray(state.settings.view_types) ? [...state.settings.view_types] : null;
    const marks = marksToOpen(state.settings);
    takeMarks(marks.marks);
    state.marksShown = marks.shown;
    state.marksNotice = marks.notice;
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
