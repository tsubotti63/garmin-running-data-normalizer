// The rules of the view page (stage G3b): what it says before an output is
// open and when one cannot be shown, how it writes the numbers of the server,
// and what the item shelf, the panels, and the tables show, as plain
// functions that the node tests check. The numbers come from the server
// (view/ of the package), which makes them once for an output; the page only
// writes them. Message keys appear only as literal strings, so that tests can
// check them against the catalogs. A message is a key with its parameters, or
// a text of the output itself, such as a name, which the page never
// translates.

import { errorMessages } from "./flow.mjs";

export const MAX_PANELS = 6;
export const PERIODS = ["all", "10y", "5y", "3y", "1y", "custom"];
export const GRAINS = ["auto", "day", "week", "month", "year"];
export const GROUPS = ["act", "fit", "body", "est"];
export const SHELF_STATES = ["open", "closed"];
// The items of the first time that the page opens an output (FIRST_ITEMS of
// view/items.py), for the words before an output is open.
export const FIRST_KEYS = ["dist", "rhr", "vo2"];
// The names of the built-in layouts (BUILT_IN_LAYOUTS of gui/layouts.py, stage
// K1 of v2.2.0), which the server reads from the same catalogs to keep the
// names of the person's layouts apart from them.
export const LAYOUT_NAME_KEYS = {
  run: "view.layout.run",
  sleep_hr: "view.layout.sleep_hr",
  volume: "view.layout.volume",
  form: "view.layout.form",
  load: "view.layout.load",
  estimates: "view.layout.estimates",
};

const GRAIN_KEYS = {
  day: "view.grain.day",
  week: "view.grain.week",
  month: "view.grain.month",
  year: "view.grain.year",
};

// The grains as nouns of a count: "Months with records: 12".
const GRAIN_COUNT_KEYS = {
  day: "view.grains.day",
  week: "view.grains.week",
  month: "view.grains.month",
  year: "view.grains.year",
};

const GROUP_KEYS = {
  act: "view.group.act",
  fit: "view.group.fit",
  body: "view.group.body",
  est: "view.group.est",
};

// The names of the items of the server's table (view/items.py), which are
// words of the page.
const ITEM_KEYS = {
  dist: "view.item.dist",
  time: "view.item.time",
  count: "view.item.count",
  pace: "view.item.pace",
  hr: "view.item.hr",
  mx: "view.item.mx",
  cad: "view.item.cad",
  pow: "view.item.pow",
  load: "view.item.load",
  asc: "view.item.asc",
  vo: "view.item.vo",
  gct: "view.item.gct",
  gctp: "view.item.gctp",
  bal: "view.item.bal",
  vr: "view.item.vr",
  sl: "view.item.sl",
  rhr: "view.item.rhr",
  steps: "view.item.steps",
  stress: "view.item.stress",
  bbc: "view.item.bbc",
  bbd: "view.item.bbd",
  sleep: "view.item.sleep",
  deep: "view.item.deep",
  light: "view.item.light",
  rem: "view.item.rem",
  sscore: "view.item.sscore",
  hrv: "view.item.hrv",
  vo2: "view.item.vo2",
  p5k: "view.item.p5k",
  p10k: "view.item.p10k",
  phalf: "view.item.phalf",
  pfull: "view.item.pfull",
  tr: "view.item.tr",
  acute: "view.item.acute",
  chronic: "view.item.chronic",
  acwr: "view.item.acwr",
  endu: "view.item.endu",
  hill: "view.item.hill",
};

// How the page writes each item: its unit on the page, the factor from the
// unit of the server's table, and the digits after the point. A clock writes
// minutes as hours and minutes ("hm"), and seconds as hours, minutes, and
// seconds ("hms") or as minutes and seconds per kilometre ("pace").
export const ITEM_FORMATS = {
  dist: { unit: "km", factor: 0.001, digits: 1 },
  time: { unit: "hm", factor: 1 / 60, digits: 0 },
  count: { unit: "count", factor: 1, digits: 0 },
  pace: { unit: "pace", factor: 1000, digits: 0 },
  hr: { unit: "bpm", factor: 1, digits: 0 },
  mx: { unit: "bpm", factor: 1, digits: 0 },
  cad: { unit: "raw", factor: 1, digits: 1 },
  pow: { unit: "raw", factor: 1, digits: 0 },
  load: { unit: "raw", factor: 1, digits: 0 },
  asc: { unit: "m", factor: 1, digits: 0 },
  vo: { unit: "cm", factor: 0.1, digits: 1 },
  gct: { unit: "ms", factor: 1, digits: 0 },
  gctp: { unit: "pct", factor: 1, digits: 1 },
  bal: { unit: "pct_fit", factor: 1, digits: 1 },
  vr: { unit: "pct", factor: 1, digits: 1 },
  sl: { unit: "m", factor: 0.001, digits: 2 },
  rhr: { unit: "bpm", factor: 1, digits: 1 },
  steps: { unit: "raw", factor: 1, digits: 0 },
  stress: { unit: "raw", factor: 1, digits: 0 },
  bbc: { unit: "raw", factor: 1, digits: 0 },
  bbd: { unit: "raw", factor: 1, digits: 0 },
  sleep: { unit: "hm", factor: 1, digits: 0 },
  deep: { unit: "min", factor: 1, digits: 0 },
  light: { unit: "min", factor: 1, digits: 0 },
  rem: { unit: "min", factor: 1, digits: 0 },
  sscore: { unit: "raw", factor: 1, digits: 0 },
  hrv: { unit: "raw", factor: 1, digits: 0 },
  vo2: { unit: "raw", factor: 1, digits: 1 },
  p5k: { unit: "hms", factor: 1, digits: 0 },
  p10k: { unit: "hms", factor: 1, digits: 0 },
  phalf: { unit: "hms", factor: 1, digits: 0 },
  pfull: { unit: "hms", factor: 1, digits: 0 },
  tr: { unit: "raw", factor: 1, digits: 0 },
  acute: { unit: "raw", factor: 1, digits: 0 },
  chronic: { unit: "raw", factor: 1, digits: 0 },
  acwr: { unit: "raw", factor: 1, digits: 2 },
  endu: { unit: "raw", factor: 1, digits: 0 },
  hill: { unit: "raw", factor: 1, digits: 0 },
};

const UNIT_KEYS = {
  km: "view.unit.km",
  hm: "view.unit.hm",
  count: "view.unit.count",
  pace: "view.unit.pace",
  bpm: "view.unit.bpm",
  raw: "view.unit.raw",
  m: "view.unit.m",
  cm: "view.unit.cm",
  ms: "view.unit.ms",
  pct: "view.unit.pct",
  pct_fit: "view.unit.pct_fit",
  min: "view.unit.min",
  hms: "view.unit.hms",
};

// A value with its unit; the values as Garmin gives them and the clocks have
// none.
const VALUE_KEYS = {
  km: "view.value.km",
  count: "view.value.count",
  pace: "view.value.pace",
  bpm: "view.value.bpm",
  m: "view.value.m",
  cm: "view.value.cm",
  ms: "view.value.ms",
  pct: "view.value.pct",
  pct_fit: "view.value.pct",
  min: "view.value.min",
};

// The clock of the scale of each unit of a clock, for steps such as 0:30.
const CLOCKS = { hm: "minute", hms: "second", pace: "second" };

const KIND_KEYS = {
  sum: "view.kind.sum",
  count: "view.kind.count",
  pace: "view.kind.pace",
  tw: "view.kind.tw",
  max: "view.kind.max",
};

const COUNT_KEYS = {
  activities: "view.count.activities",
  days: "view.count.days",
  records: "view.count.records",
};

const COUNT_HEAD_KEYS = {
  activities: "view.table.activities",
  days: "view.table.days",
  records: "view.table.records",
};

// The activity types of Garmin that the page names in its words; any other
// is written as the output has it.
const TYPE_KEYS = {
  running: "view.type.running",
  treadmill_running: "view.type.treadmill_running",
  trail_running: "view.type.trail_running",
  track_running: "view.type.track_running",
  indoor_running: "view.type.indoor_running",
  virtual_run: "view.type.virtual_run",
  cycling: "view.type.cycling",
  road_biking: "view.type.road_biking",
  mountain_biking: "view.type.mountain_biking",
  indoor_cycling: "view.type.indoor_cycling",
  walking: "view.type.walking",
  hiking: "view.type.hiking",
  lap_swimming: "view.type.lap_swimming",
  open_water_swimming: "view.type.open_water_swimming",
  strength_training: "view.type.strength_training",
};

const SPORT_KEYS = {
  RUNNING: "view.sport.running",
  CYCLING: "view.sport.cycling",
};

// The two series of VO2max that the normalization writes (normalizers/
// vo2max.py): from the records of the activities, and from MaxMet.
const VO2_ACTIVITY = "activity_vo2max_daily";
const VO2_MAXMET = "performance_metrics_daily";
// The dashes of the lines of a panel by their sports, running solid; and a
// dash for any other sport.
const DASHES = { RUNNING: null, CYCLING: "6 4", "": "2 3" };
const OTHER_DASH = "8 3 2 3";
const PREDICTIONS = ["p5k", "p10k", "phalf", "pfull"];

function message(key, params = {}, keyParams = {}) {
  return { key, params, keyParams };
}

// A text of the output itself, such as the name of a folder.
export function plain(text) {
  return { text: String(text) };
}

// --- Numbers and dates ---------------------------------------------------

const numberFormats = new Map();
const dateFormats = new Map();

function numberFormat(language, digits) {
  const name = `${language} ${digits}`;
  if (!numberFormats.has(name)) {
    numberFormats.set(name, new Intl.NumberFormat(language, { minimumFractionDigits: digits, maximumFractionDigits: digits }));
  }
  return numberFormats.get(name);
}

// A whole number as the language writes it, such as 1,234.
export function countText(value, language) {
  return numberFormat(language, 0).format(value);
}

function twoDigits(value) {
  return String(value).padStart(2, "0");
}

// Minutes as hours and minutes: 1:05; below 0 with its sign, -1:05 (Codex's
// review of the diff of M3: a time below 0 was written as a long one).
export function clockMinutes(minutes) {
  const whole = Math.round(minutes);
  if (whole < 0) {
    return `-${clockMinutes(-whole)}`;
  }
  const hours = Math.floor(whole / 60);
  return `${hours}:${twoDigits(whole - hours * 60)}`;
}

// Seconds as hours, minutes, and seconds, or minutes and seconds under an
// hour: 1:02:03, 21:05; below 0 with its sign, -1:00.
export function clockSeconds(seconds) {
  const whole = Math.round(seconds);
  if (whole < 0) {
    return `-${clockSeconds(-whole)}`;
  }
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole - hours * 3600) / 60);
  const rest = whole - hours * 3600 - minutes * 60;
  return hours > 0 ? `${hours}:${twoDigits(minutes)}:${twoDigits(rest)}` : `${minutes}:${twoDigits(rest)}`;
}

// The value of the server as the page shows it, in km, in minutes, and so on.
export function shown(key, value) {
  return Number.isFinite(value) ? value * ITEM_FORMATS[key].factor : value;
}

// The clock of the scale of an item, or null for numbers.
export function clockOf(key) {
  return CLOCKS[ITEM_FORMATS[key].unit] ?? null;
}

function shownText(key, value, language, digits = ITEM_FORMATS[key].digits) {
  const unit = ITEM_FORMATS[key].unit;
  if (unit === "hm") {
    return clockMinutes(value);
  }
  if (unit === "hms" || unit === "pace") {
    return clockSeconds(value);
  }
  return numberFormat(language, digits).format(value);
}

// A value of the server with its unit, as a message.
export function valueMessage(key, value, language) {
  const unit = ITEM_FORMATS[key].unit;
  const text = shownText(key, shown(key, value), language);
  return Object.hasOwn(VALUE_KEYS, unit) ? message(VALUE_KEYS[unit], { value: text }) : plain(text);
}

// A tick of the scale of a panel: a value as the page shows it, with as many
// digits as the step of the ticks needs and without its unit, which the
// heading of the panel names.
export function tickText(key, value, step, language) {
  const digits = step > 0 && step < 1 ? Math.min(3, Math.ceil(-Math.log10(step) - 1e-9)) : 0;
  return shownText(key, value, language, digits);
}

export function unitKey(key) {
  return UNIT_KEYS[ITEM_FORMATS[key].unit];
}

export function itemKey(key) {
  return ITEM_KEYS[key];
}

export function groupKey(group) {
  return GROUP_KEYS[group];
}

export function grainKey(grain) {
  return GRAIN_KEYS[grain];
}

function dateFormat(language, kind) {
  const name = `${language} ${kind}`;
  if (!dateFormats.has(name)) {
    const options = {
      day: { year: "numeric", month: "long", day: "numeric" },
      month: { year: "numeric", month: "long" },
      year: { year: "numeric" },
      tick_year: { year: "numeric" },
      tick_month_year: { year: "numeric", month: "short" },
      tick_month: { month: "short" },
      tick_day: { month: "numeric", day: "numeric" },
      month_name: { month: "long" },
      month_day: { month: "long", day: "numeric" },
      numeric_day: { year: "numeric", month: "numeric", day: "numeric" },
      list_day: { month: "numeric", day: "numeric" },
      weekday: { weekday: "short" },
    }[kind];
    dateFormats.set(name, new Intl.DateTimeFormat(language, { ...options, timeZone: "UTC" }));
  }
  return dateFormats.get(name);
}

// A day of the output at midnight UTC; a year below 100 is that year, which
// Date.UTC would read as 1900 and later (stage Q1: the summary writes the
// first days of the calendar).
function utcDate(iso) {
  const [year, month, day] = String(iso).split("-").map(Number);
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  return date;
}

// A day as the language writes it: 2026年10月26日, October 26, 2026.
export function dateText(iso, language) {
  return dateFormat(language, "day").format(utcDate(iso));
}

// The name of a period of the answer: a day, the week from its Monday, a
// month, or a year, marked when the period cuts it.
export function periodMessage(period, grain, language, { mark = true } = {}) {
  const date = utcDate(period.start);
  let name;
  if (grain === "week") {
    const monday = new Date(date.getTime() - ((date.getUTCDay() + 6) % 7) * 86400000);
    name = message("view.period.week", { date: dateFormat(language, "day").format(monday) });
  } else {
    name = plain(dateFormat(language, grain === "day" ? "day" : grain === "month" ? "month" : "year").format(date));
  }
  return mark && period.partial ? message("view.period.partial", {}, { period: name }) : name;
}

// The words of a tick of the time axis (view_chart.mjs timeTicks).
export function timeTickText(tick, language) {
  const date = new Date(tick.day * 86400000);
  if (tick.kind === "year") {
    return String(date.getUTCFullYear());
  }
  return dateFormat(language, `tick_${tick.kind}`).format(date);
}

// --- The items -------------------------------------------------------------

// The items of the server's table by their keys.
export function itemsByKey(items) {
  return new Map((Array.isArray(items) ? items : []).map((item) => [item.key, item]));
}

function isActivityItem(item) {
  return item.group === "act" || item.group === "fit";
}

function isTotal(item) {
  return item.kind === "sum" || item.kind === "count";
}

// Whether the bars of a total start at 0; a total is drawn from 0.
export function totalItem(item) {
  return isTotal(item);
}

function countKind(item) {
  return isActivityItem(item) ? "activities" : item.kind === "obs" ? "records" : "days";
}

// What the value of a period of an item is, for the label of its panel.
export function kindKey(item, grain) {
  if (Object.hasOwn(KIND_KEYS, item.kind)) {
    return KIND_KEYS[item.kind];
  }
  if (item.kind === "day") {
    return grain === "day" ? "view.kind.day" : item.per_day ? "view.kind.day_mean_per_day" : "view.kind.day_mean";
  }
  return grain === "day" ? "view.kind.obs_points" : "view.kind.obs_mean";
}

// The count beside a value: the activities, the days with a value, or the
// records of the period. A daily item has one day in a day, so it says none.
export function countMessage(item, count, grain, language) {
  const kind = countKind(item);
  if (kind === "days" && grain === "day") {
    return null;
  }
  return message(COUNT_KEYS[kind], { n: countText(count, language) });
}

export function countHeadKey(item) {
  return COUNT_HEAD_KEYS[countKind(item)];
}

// The items that the settings remember (stage G3b), known and once each, up to
// six; null when there are none.
export function rememberedItems(settings, items) {
  const known = itemsByKey(items);
  const names = Array.isArray(settings?.view_items) ? settings.view_items : null;
  if (names === null) {
    return null;
  }
  const kept = [...new Set(names.filter((name) => typeof name === "string" && known.has(name)))].slice(0, MAX_PANELS);
  return kept.length ? kept : null;
}

// The items that the settings remember, by the names that the page knows,
// before an output and its table of the items are open.
export function rememberedKeys(settings) {
  const names = Array.isArray(settings?.view_items) ? settings.view_items : [];
  return [...new Set(names.filter((name) => typeof name === "string" && Object.hasOwn(ITEM_KEYS, name)))].slice(0, MAX_PANELS);
}

// Whether the settings remember the items: then the page is in a later
// launch.
export function itemsRemembered(settings) {
  return rememberedKeys(settings).length > 0;
}

// What the page keeps of the settings after the other tab forgot them: no
// items, no shelf, no tips, no colors, no layouts, and no period, grouping,
// activity types, or timezone (stage K2 of v2.2.0), no marks (stage M1), and
// no two items plotted (stage O1) nor item of a distribution (stage P1), as the files have none now. The page keeps showing what it shows, but the
// marks, which are gone.
export function settingsAfterForget(settings) {
  const kept = { ...(settings ?? {}) };
  for (const name of [
    "view_items",
    "view_shelf",
    "hints",
    "theme",
    "view_layouts",
    "view_layouts_hidden",
    "view_layout",
    "view_period",
    "view_grain",
    "view_types",
    "timezone",
    "view_compare_mode",
    "view_compare_month",
    "view_compare_by",
    "view_compare_weeks",
    "view_marks_shown",
    "view_plot",
    "view_spread",
    "view_marks",
    "marks_notice",
  ]) {
    delete kept[name];
  }
  return { ...kept, present: false };
}

// The shelf as the settings remember it: open at first.
export function shelfOpen(settings) {
  return settings?.view_shelf !== "closed";
}

// Whether the tips show: as the person last switched them, on either page;
// otherwise on until the view page remembers its items, and off from then on
// (the mockup v2: the first time, and later).
export function viewHintsShown(settings) {
  return typeof settings?.hints === "boolean" ? settings.hints : !itemsRemembered(settings);
}

// The items of an output that the page opens: those shown now, those that
// the settings remember, or the first ones of the output.
export function itemsToOpen(current, remembered, first, items) {
  const known = itemsByKey(items);
  for (const list of [current, remembered, first]) {
    const kept = Array.isArray(list) ? [...new Set(list.filter((key) => known.has(key)))].slice(0, MAX_PANELS) : [];
    if (kept.length) {
      return kept;
    }
  }
  return [];
}

// The items with one more, or one fewer: up to six, in the order chosen.
export function toggledItems(items, key) {
  if (items.includes(key)) {
    return items.filter((item) => item !== key);
  }
  return items.length < MAX_PANELS ? [...items, key] : items;
}

// The items with one moved up (-1) or down (+1).
export function movedItems(items, key, direction) {
  const from = items.indexOf(key);
  const to = from + direction;
  if (from < 0 || to < 0 || to >= items.length) {
    return items;
  }
  const moved = [...items];
  [moved[from], moved[to]] = [moved[to], moved[from]];
  return moved;
}

// The rows of the item shelf: the groups, each with its items, those that a
// search finds, whether each is chosen and can be checked, and its months
// with a value. ``name`` gives the name of an item in the language shown.
export function shelfGroups(items, chosen, coverage, query, name, folded = {}) {
  const words = String(query ?? "").trim().toLowerCase();
  const full = chosen.length >= MAX_PANELS;
  return GROUPS.map((group) => {
    const members = items.filter((item) => item.group === group);
    const rows = members
      .filter((item) => words === "" || name(item.key).toLowerCase().includes(words))
      .map((item) => ({
        key: item.key,
        chosen: chosen.includes(item.key),
        disabled: !chosen.includes(item.key) && full,
        months: coverage?.[item.key]?.months ?? [],
      }));
    return {
      group,
      open: folded[group] !== true,
      chosen: members.filter((item) => chosen.includes(item.key)).length,
      rows,
    };
  });
}

// A month ("2026-10", or the month of a day) counted in months.
export function monthIndex(text) {
  return Number(String(text).slice(0, 4)) * 12 + Number(String(text).slice(5, 7)) - 1;
}

// The runs of months with a value, as [first, length] counted in months
// from ``firstMonth`` (monthIndex), for the bar of an item on the shelf.
export function coverageRuns(months, firstMonth) {
  const indexes = [...new Set(months.map((month) => monthIndex(month) - firstMonth))].sort((a, b) => a - b);
  const runs = [];
  for (const index of indexes) {
    const last = runs[runs.length - 1];
    if (last && last[0] + last[1] === index) {
      last[1] += 1;
    } else {
      runs.push([index, 1]);
    }
  }
  return runs;
}

// --- Activity types --------------------------------------------------------

// The name of an activity type: in the words of the page when it knows it,
// "no activity type" for none, and otherwise as the output has it.
export function typeMessage(name) {
  if (name === "") {
    return message("view.type.none");
  }
  return Object.hasOwn(TYPE_KEYS, name) ? message(TYPE_KEYS[name]) : plain(name);
}

// The types that the page counts at first: the running types, as the server
// counts them without a choice.
export function defaultTypes(types) {
  return (Array.isArray(types) ? types : []).filter((entry) => entry.running === true).map((entry) => entry.name);
}

// The types to send: null for the types that the server counts at first.
export function typesRequest(counted, types) {
  const first = defaultTypes(types);
  return counted.length === first.length && first.every((name) => counted.includes(name)) ? null : [...counted];
}

// The types with one more or one fewer; the last one stays.
export function toggledTypes(counted, name, types) {
  const order = (Array.isArray(types) ? types : []).map((entry) => entry.name);
  const next = counted.includes(name) ? counted.filter((other) => other !== name) : [...counted, name];
  if (!next.length) {
    return counted;
  }
  return order.filter((other) => next.includes(other));
}

// The words of the field of the types.
export function typesSummary(counted, types) {
  if (!Array.isArray(types) || !types.length) {
    return message("view.types.no_activities");
  }
  const first = defaultTypes(types);
  if (first.length && counted.length === first.length && first.every((name) => counted.includes(name))) {
    return message("view.types.running_all", { n: first.length });
  }
  return message("view.types.some", { n: counted.length });
}

// --- Periods ---------------------------------------------------------------

// The period to ask for: a choice of the bar, or a range of two days.
export function periodRequest(choice, range) {
  if (choice === "custom") {
    return range ? { from: range.from, to: range.to } : "all";
  }
  return PERIODS.includes(choice) ? choice : "all";
}

function addDays(iso, days) {
  return new Date(utcDate(iso).getTime() + days * 86400000).toISOString().slice(0, 10);
}

function daysBetween(first, last) {
  return Math.round((utcDate(last).getTime() - utcDate(first).getTime()) / 86400000);
}

// The period of the same length before (-1) or after (+1) the one shown,
// kept within the days of the output; null at its end.
export function shiftedRange(start, end, direction, firstDay, lastDay) {
  if (!start || !end || !firstDay || !lastDay) {
    return null;
  }
  const length = daysBetween(start, end);
  if ((direction < 0 && start <= firstDay) || (direction > 0 && end >= lastDay)) {
    return null;
  }
  let from = addDays(start, direction * (length + 1));
  let to = addDays(from, length);
  if (from < firstDay) {
    from = firstDay;
    to = addDays(from, length);
  }
  if (to > lastDay) {
    to = lastDay;
    from = addDays(to, -length);
    if (from < firstDay) {
      from = firstDay;
    }
  }
  return { from, to };
}

// What is wrong with a range that was typed: a day missing, outside the
// output, or a start after the end; null when it can be asked for.
export function rangeProblem(from, to, firstDay, lastDay) {
  const day = /^\d{4}-\d{2}-\d{2}$/;
  if (!day.test(String(from)) || !day.test(String(to))) {
    return "view.range.missing";
  }
  if (from > to) {
    return "view.range.order";
  }
  if ((lastDay && from > lastDay) || (firstDay && to < firstDay)) {
    return "view.range.outside";
  }
  return null;
}

// The range that a drag on the overview chose, from two days of the overview,
// in either order; null for a drag shorter than a week, which is a click.
export function draggedRange(firstDay, secondDay) {
  const from = Math.min(firstDay, secondDay);
  const to = Math.max(firstDay, secondDay);
  return to - from < 7 ? null : { from, to };
}

// Which edge of the frame of the overview a pointer at x is on: "from" or
// "to", the nearer one where it is within reach of both, and null where it is
// farther than reach from both (a new period).
export function overviewGrip(x, from, to, reach = 8) {
  const fromFar = Math.abs(x - from);
  const toFar = Math.abs(x - to);
  if (Math.min(fromFar, toFar) > reach) {
    return null;
  }
  return fromFar < toFar ? "from" : "to";
}

// The period that a drag on the overview shows as it moves, within the days
// of the overview: from the day where it started to the day of the pointer,
// or the period of the frame with the dragged edge moved as far as the
// pointer moved, so that a press that does not move keeps the period, never
// shorter than a week (as draggedRange).
export function brushedRange(drag, day, firstDay, lastDay) {
  const moved = day - drag.start;
  let range;
  if (drag.grip === "from") {
    range = { from: Math.min(drag.range.from + moved, drag.range.to - 7), to: drag.range.to };
  } else if (drag.grip === "to") {
    range = { from: drag.range.from, to: Math.max(drag.range.to + moved, drag.range.from + 7) };
  } else {
    range = { from: Math.min(drag.start, day), to: Math.max(drag.start, day) };
  }
  return { from: Math.max(firstDay, range.from), to: Math.min(lastDay, range.to) };
}

// The grouping that "Auto" takes for a period, as the server takes it.
export function autoGrainOf(start, end) {
  if (!start || !end) {
    return null;
  }
  const first = utcDate(start);
  const yearsLater = (years) => {
    const date = new Date(Date.UTC(first.getUTCFullYear() + years, first.getUTCMonth(), first.getUTCDate()));
    // 29 February, in a year without it.
    return date.getUTCMonth() === first.getUTCMonth() ? date : new Date(Date.UTC(first.getUTCFullYear() + years, first.getUTCMonth(), 28));
  };
  const last = utcDate(end);
  if (last >= yearsLater(3)) {
    return "month";
  }
  return last >= yearsLater(1) ? "week" : "day";
}

// --- A panel ---------------------------------------------------------------

// The second line and the readings of a panel with more than one line take
// the lowest, the highest, and the latest value over all its lines.
export function panelSummary(item, panel) {
  const summaries = (panel?.lines ?? []).map((line) => line.summary).filter(Boolean);
  const pick = (name, better) =>
    summaries.map((summary) => summary[name]).filter(Boolean).reduce((best, entry) => (best === null || better(entry, best) ? entry : best), null);
  const total = isTotal(item);
  return {
    total,
    withRecords: total ? (summaries[0]?.periods_with_records ?? 0) : null,
    withoutRecords: total ? (summaries[0]?.periods_without_records ?? 0) : 0,
    withValue: panel?.periods_with_value ?? 0,
    lowest: pick("lowest", (entry, best) => entry.value < best.value || (entry.value === best.value && entry.period < best.period)),
    highest: pick("highest", (entry, best) => entry.value > best.value || (entry.value === best.value && entry.period < best.period)),
    latest: pick("latest", (entry, best) => entry.period > best.period),
  };
}

// The second line of a panel: the periods with records or with a value,
// those of 0, and the lowest, the highest, and the latest value with their
// periods. The numbers are strong.
export function summaryMessages(item, panel, periods, grain, language) {
  const summary = panelSummary(item, panel);
  const grains = GRAIN_COUNT_KEYS[grain];
  const parts = [];
  const zero =
    summary.total && summary.withoutRecords > 0
      ? { ...message("view.summary.without_records", { n: countText(summary.withoutRecords, language) }, { grain: grains }), strong: ["n"] }
      : null;
  if ((summary.total ? summary.withRecords : summary.withValue) === 0) {
    return zero === null ? [message("view.summary.none")] : [message("view.summary.none"), zero];
  }
  parts.push({
    ...message(
      summary.total ? "view.summary.with_records" : "view.summary.with_value",
      { n: countText(summary.total ? summary.withRecords : summary.withValue, language) },
      { grain: grains },
    ),
    strong: ["n"],
  });
  if (zero !== null) {
    parts.push(zero);
  }
  for (const [name, key] of [
    ["lowest", "view.summary.lowest"],
    ["highest", "view.summary.highest"],
    ["latest", "view.summary.latest"],
  ]) {
    const entry = summary[name];
    if (entry !== null && periods[entry.period] !== undefined) {
      parts.push({
        ...message(key, {}, { value: valueMessage(item.key, entry.value, language), period: periodMessage(periods[entry.period], grain, language) }),
        strong: ["value"],
      });
    }
  }
  return parts;
}

function seriesOf(line) {
  const series = line?.series;
  return series !== null && typeof series === "object" ? series : null;
}

// The sources and the sports of the lines of a panel, in the order of their
// first days, which is the order of the lines; the sports start with running.
function seriesParts(panel) {
  const lines = panel?.lines ?? [];
  const sources = [];
  const sports = [];
  for (const line of lines) {
    const series = seriesOf(line);
    if (series === null) {
      continue;
    }
    const source = String(series.vo2max_source_series ?? "");
    const sport = String(series.sport ?? "");
    if (!sources.includes(source)) {
      sources.push(source);
    }
    if (!sports.includes(sport)) {
      sports.push(sport);
    }
  }
  sports.sort((a, b) => (a === "RUNNING" ? -1 : b === "RUNNING" ? 1 : 0));
  return { sources, sports };
}

// The color (1 or 2) and the dash of each line of a panel: the series of
// VO2 Max by color, that of the activities in violet and that of MaxMet in
// orange, and the sports by dash, running solid (the rules of the charts of
// stage G3b). Both follow the series and the sport by their names, never
// their order, so that a period with one series does not paint it again.
export function lineStyles(panel) {
  const { sources } = seriesParts(panel);
  const others = sources.filter((source) => source !== VO2_ACTIVITY && source !== VO2_MAXMET);
  return (panel?.lines ?? []).map((line) => {
    const series = seriesOf(line);
    if (series === null) {
      return { color: 1, dash: null };
    }
    const source = String(series.vo2max_source_series ?? "");
    const sport = String(series.sport ?? "");
    const color = source === VO2_MAXMET || (source !== VO2_ACTIVITY && others.indexOf(source) > 0) ? 2 : 1;
    return { color, dash: Object.hasOwn(DASHES, sport) ? DASHES[sport] : OTHER_DASH };
  });
}

function sportMessage(sport) {
  if (sport === "") {
    return message("view.sport.none");
  }
  return Object.hasOwn(SPORT_KEYS, sport) ? message(SPORT_KEYS[sport]) : plain(sport);
}

// The names of the lines of a panel with more than one, for its legend and
// its table: a series of VO2max by the days that it covers, "until" the last
// day of the first and "from" the first day of a later one, and the sport
// where there are two or more. Null for a panel of one line.
export function lineNames(panel, language) {
  const lines = panel?.lines ?? [];
  if (lines.length < 2) {
    return lines.map(() => null);
  }
  const { sources, sports } = seriesParts(panel);
  const bounds = new Map();
  for (const line of lines) {
    const series = seriesOf(line);
    if (series === null) {
      continue;
    }
    const source = String(series.vo2max_source_series ?? "");
    const known = bounds.get(source) ?? { first: null, last: null };
    if (typeof line.first_day === "string" && (known.first === null || line.first_day < known.first)) {
      known.first = line.first_day;
    }
    if (typeof line.last_day === "string" && (known.last === null || line.last_day > known.last)) {
      known.last = line.last_day;
    }
    bounds.set(source, known);
  }
  return lines.map((line) => {
    const series = seriesOf(line);
    if (series === null) {
      return null;
    }
    const source = String(series.vo2max_source_series ?? "");
    const range = bounds.get(source);
    let name = null;
    if (sources.length > 1) {
      name =
        sources.indexOf(source) === 0
          ? message("view.line.until", { date: range.last ? dateText(range.last, language) : "" })
          : message("view.line.from", { date: range.first ? dateText(range.first, language) : "" });
    }
    if (sports.length > 1) {
      const sport = sportMessage(String(series.sport ?? ""));
      name = name === null ? sport : message("view.line.series_sport", {}, { series: name, sport });
    }
    return name ?? plain(source);
  });
}

// What the panel says at its top right for one period: the period, and for
// each line its value and its count, or that it has no value.
export function readout(item, panel, periods, index, grain, language) {
  const period = periods[index];
  if (period === undefined) {
    return null;
  }
  const values = (panel?.lines ?? []).flatMap((line, number) => {
    const value = line.values?.[index];
    if (!Number.isFinite(value)) {
      return [];
    }
    return [{ line: number, value: valueMessage(item.key, value, language), count: countMessage(item, line.counts?.[index] ?? 0, grain, language) }];
  });
  return { period: periodMessage(period, grain, language), values };
}

// The notes of a panel ("About this panel"): what is left out of its numbers
// and why, and what its values are, as the server counted them. A note may
// open a part of the help.
export function panelNotes(item, panel, periods, grain, language) {
  const left = panel?.left_out ?? {};
  const count = (name) => (Number.isInteger(left[name]) ? left[name] : 0);
  const n = (value) => countText(value, language);
  const notes = [];
  const summary = panelSummary(item, panel);
  if (summary.total && summary.withoutRecords > 0) {
    notes.push({ ...message("view.note.zero", { n: n(summary.withoutRecords) }, { grain: GRAIN_COUNT_KEYS[grain] }), help: "zero" });
  }
  if (isActivityItem(item)) {
    if (count("disagree") > 0) {
      notes.push(message("view.note.activity_disagree", { n: n(count("disagree")) }));
    }
    if (count("no_value") > 0) {
      notes.push(message(item.from_fit ? "view.note.fit_missing" : "view.note.activity_missing", { n: n(count("no_value")) }));
    }
    if (count("no_duration") > 0) {
      notes.push(message("view.note.no_duration", { n: n(count("no_duration")) }));
    }
  } else if (count("disagree") > 0) {
    notes.push(message(item.kind === "obs" ? "view.note.record_disagree" : "view.note.day_disagree", { n: n(count("disagree")) }));
  }
  if (item.kind === "tw" || item.kind === "pace") {
    notes.push({ ...message("view.note.calculated"), help: "calculated" });
  }
  if (item.kind === "pace" || PREDICTIONS.includes(item.key)) {
    notes.push(message("view.note.faster_lower"));
  }
  if (item.sleep) {
    const review = count("sleep_review_days");
    const other = count("sleep_other_days");
    if (review + other > 0) {
      notes.push(message("view.note.sleep_unused", { n: n(review + other), review: n(review), other: n(other) }));
    }
  }
  if (item.key === "hrv") {
    notes.push(message("view.note.hrv_reference"));
  }
  if (item.kind === "obs" && count("days_with_several_records") > 0) {
    notes.push({
      ...message(grain === "day" ? "view.note.several_points" : "view.note.several_mean", { n: n(count("days_with_several_records")) }),
      help: "records",
    });
  }
  if (item.key === "vo2") {
    const { sources } = seriesParts(panel);
    if (sources.includes(VO2_ACTIVITY) && sources.includes(VO2_MAXMET)) {
      const lines = panel.lines.filter((line) => seriesOf(line) !== null);
      const of = (source) => lines.filter((line) => seriesOf(line).vo2max_source_series === source);
      const until = of(VO2_ACTIVITY).map((line) => line.last_day).filter(Boolean).sort().pop();
      const from = of(VO2_MAXMET).map((line) => line.first_day).filter(Boolean).sort()[0];
      if (until && from) {
        notes.push(message("view.note.vo2_series", { until: dateText(until, language), from: dateText(from, language) }));
      }
    }
  }
  if (PREDICTIONS.includes(item.key)) {
    notes.push(message("view.note.prediction"));
  }
  if (periods.some((period) => period.partial)) {
    notes.push(message("view.note.partial"));
  }
  if (count("after_today") > 0) {
    notes.push(message("view.note.after_today", { n: n(count("after_today")) }));
  }
  if (count("no_date") > 0) {
    notes.push(message("view.note.no_date", { n: n(count("no_date")) }));
  }
  return notes;
}

// The table of a panel: a row for every period, newest first, with the value
// and the count of each line; a period without a value says so.
export function tableRows(item, panel, periods, grain, language) {
  const lines = panel?.lines ?? [];
  const rows = [];
  for (let index = periods.length - 1; index >= 0; index -= 1) {
    rows.push({
      period: periodMessage(periods[index], grain, language),
      cells: lines.map((line) => {
        const value = line.values?.[index];
        return {
          value: Number.isFinite(value) ? valueMessage(item.key, value, language) : null,
          count: countText(line.counts?.[index] ?? 0, language),
        };
      }),
    });
  }
  return rows;
}

// The heads of the columns of a table: the period, then for each line its
// value and its count.
export function tableHeads(item, panel, grain, language) {
  const names = lineNames(panel, language);
  const heads = [message("view.table.period", {}, { grain: GRAIN_KEYS[grain] })];
  names.forEach((name) => {
    heads.push(name === null ? message("view.table.value") : message("view.table.value_of", {}, { series: name }));
    heads.push(message(countHeadKey(item)));
  });
  return heads;
}

// --- The page --------------------------------------------------------------

// What the page offers before an output is open: the latest output, which is
// the output of this launch's run or else the newest earlier one, with the
// items remembered; or the first steps.
export function startChoice({ runOutput, earlier, remembered }) {
  const latest = runOutput ?? earlier?.[0] ?? null;
  if (latest === null) {
    return { kind: "first", latest: null };
  }
  return { kind: remembered ? "remembered" : "latest", latest };
}

// The line of what to do next at the top: its kind (the color of its bar),
// its label, and its words.
export function viewBar(state) {
  if (state.stopped) {
    return { kind: "none", label: message("view.bar.stopped"), text: message("next_line.stopped") };
  }
  if (state.view !== null && state.view !== undefined) {
    return {
      kind: "done",
      label: message("view.bar.viewing"),
      text: message("view.bar.viewing_text", { version: state.view.version }, { name: plain(state.view.name) }),
    };
  }
  if (state.opening !== null && state.opening !== undefined) {
    return { kind: "current", label: message("view.bar.opening"), text: plain(state.opening) };
  }
  if (state.stop !== null && state.stop !== undefined) {
    const other = state.stop.code === "OUTPUT_OTHER_VERSION" || state.stop.code === "SERIES_OUTPUT_OTHER_VERSION";
    return { kind: "error", label: message("view.bar.cannot"), text: message(other ? "view.bar.other_version" : "view.bar.not_opened") };
  }
  return {
    kind: "current",
    label: message("view.bar.next"),
    text: message(state.choice?.kind === "first" ? "view.bar.choose_first" : "view.bar.choose_latest"),
  };
}

// The view page writes three stops in words of its own, which say what it
// reads (the plan of stage G3b); the others are those of the normalization
// page.
const VIEW_STOP_KEYS = {
  OUTPUT_NOT_AVAILABLE: ["view.stop.not_available", "stop_next.output_where"],
  OUTPUT_CHANGED: ["view.stop.changed", "view.stop_next.changed"],
  HANDOFF_INVALID: ["view.stop.handoff_invalid", "stop_next.handoff_invalid"],
};

// The box of a stop: its heading, its lines, the code to quote, and whether
// it offers to normalize again. An output of another version, of 2.0 or of
// 1.3, says the same; only its code differs.
export function stopBox(code, detail, current) {
  const version = typeof detail?.version === "string" && detail.version !== "" ? detail.version : null;
  const codeLine =
    typeof code === "string" && code !== ""
      ? version === null
        ? message("view.stop.code", { code })
        : message("view.stop.code_version", { code, version })
      : null;
  if (code === "OUTPUT_OTHER_VERSION" || code === "SERIES_OUTPUT_OTHER_VERSION") {
    return {
      heading: message("view.stop.other_version_heading"),
      lines: [
        version === null
          ? message("view.stop.other_version_why_unknown", { current: current ?? "" })
          : message("view.stop.other_version_why", { version, current: current ?? "" }),
        // The button of the normalization page that normalizes the
        // Snapshots again, in its own words.
        message("view.stop.other_version_next", {}, { button: "rerun.button" }),
      ],
      code: codeLine,
      normalize: true,
    };
  }
  if (Object.hasOwn(VIEW_STOP_KEYS, code)) {
    const [what, next] = VIEW_STOP_KEYS[code];
    return {
      heading: message("view.stop.heading"),
      lines: [message(what), message("next.label", {}, { step: next })],
      code: codeLine,
      normalize: false,
    };
  }
  // The words of the normalization page, without its code line, which the
  // box writes itself.
  const lines = errorMessages(code, null).filter((line) => line.key !== "error.code");
  return { heading: message("view.stop.heading"), lines, code: codeLine, normalize: false };
}

// The names of items as a list of the language: 距離、安静時心拍、VO2 Max.
export function itemListMessage(keys, name, language) {
  const names = keys.map((key) => name(key));
  const list = new Intl.ListFormat(language, { style: "long", type: "conjunction" });
  return plain(list.format(names));
}

// --- Layouts (stage K2 of v2.2.0) -------------------------------------------

// Whether the items shown are other than those of a layout: other items, or
// the same ones in another order.
export function layoutChanged(layoutItems, items) {
  const first = Array.isArray(layoutItems) ? layoutItems : [];
  const second = Array.isArray(items) ? items : [];
  return first.length !== second.length || first.some((key, index) => key !== second[index]);
}

// The cards of the layouts above the item shelf: the built-in layouts that
// are not hidden, in their order, then the person's in the order that they
// keep. Each says whether it is the one used last, whether the items shown
// are other than its own since, and how many of its items have a value in
// the output (from the bars of the item shelf), when not all of them do.
export function layoutCards({ builtIns, mine, hidden, current, items, coverage }) {
  const hiddenIds = new Set(Array.isArray(hidden) ? hidden : []);
  const valued = (keys) => (coverage ? keys.filter((key) => (coverage[key]?.months ?? []).length > 0).length : null);
  const card = (layout, builtIn) => {
    const keys = Array.isArray(layout.items) ? [...layout.items] : [];
    const isCurrent = layout.id === current;
    const count = valued(keys);
    return {
      id: layout.id,
      builtIn,
      nameKey: builtIn ? LAYOUT_NAME_KEYS[layout.id] : null,
      name: builtIn ? null : String(layout.name ?? ""),
      items: keys,
      current: isCurrent,
      changed: isCurrent && layoutChanged(keys, items),
      valued: count !== null && count < keys.length ? count : null,
      total: keys.length,
    };
  };
  const cards = [];
  for (const layout of Array.isArray(builtIns) ? builtIns : []) {
    if (Object.hasOwn(LAYOUT_NAME_KEYS, layout?.id) && !hiddenIds.has(layout.id)) {
      cards.push(card(layout, true));
    }
  }
  for (const layout of Array.isArray(mine) ? mine : []) {
    if (typeof layout?.id === "string") {
      cards.push(card(layout, false));
    }
  }
  return cards;
}

// The words under the name of a card: "(changed)" and the items with a value.
export function layoutNotes(card) {
  const notes = [];
  if (card.changed) {
    notes.push(message("view.layouts.changed"));
  }
  if (card.valued !== null) {
    notes.push(message("view.layouts.valued", { n: card.valued, m: card.total }));
  }
  return notes;
}

// The place of a layout dragged among the others: after each of them whose
// middle is above the pointer, so that the place does not jump back and forth
// at a border.
export function dropPlace(middles, y) {
  return middles.filter((middle) => middle < y).length;
}

// The period that a remembered one asks of an output that opens: a period of
// the last years as it is; a range of days as it is when it meets the days
// of the output (the server cuts it to them, as it does now), and all the
// output when it does not; otherwise none.
export function periodToOpen(period, firstDay, lastDay) {
  if (typeof period === "string") {
    return PERIODS.includes(period) && period !== "custom" ? { choice: period, range: null } : null;
  }
  const from = period?.from;
  const to = period?.to;
  const day = /^\d{4}-\d{2}-\d{2}$/;
  if (typeof from !== "string" || typeof to !== "string" || !day.test(from) || !day.test(to) || from > to) {
    return null;
  }
  if (firstDay && lastDay && (to < firstDay || from > lastDay)) {
    return { choice: "all", range: null };
  }
  return { choice: "custom", range: { from, to } };
}

// The activity types that a remembered choice counts in an output that
// opens: those of the output, in the order of the output; no types ([]) as
// it is; and null (the types counted at first) when none of the names is
// there or nothing is remembered.
export function typesToOpen(remembered, types) {
  if (!Array.isArray(remembered)) {
    return null;
  }
  if (!remembered.length) {
    return [];
  }
  const names = (Array.isArray(types) ? types : []).map((entry) => entry.name);
  const kept = names.filter((name) => remembered.includes(name));
  return kept.length ? kept : null;
}

// The grouping that a remembered one gives: one of the grain choices, or auto.
export function grainToOpen(grain) {
  return GRAINS.includes(grain) ? grain : "auto";
}

// A sender that waits for the person to stop changing: the last value is
// sent once, after the wait without another change; a flush sends what
// waits at once (when the app quits) and tells when it is sent, and a take
// gives what waits without sending it (when the page hides, to send it in a
// request that outlives the page). The timer functions are given, so that
// the tests move the time.
export function laterSender(send, wait, { setTimer = setTimeout, clearTimer = clearTimeout } = {}) {
  let pending = null;
  let timer = null;
  const fire = () => {
    timer = null;
    const value = pending;
    pending = null;
    return value === null ? Promise.resolve() : Promise.resolve(send(value));
  };
  return {
    push(value) {
      pending = value;
      if (timer !== null) {
        clearTimer(timer);
      }
      timer = setTimer(fire, wait);
    },
    flush() {
      if (timer !== null) {
        clearTimer(timer);
        timer = null;
      }
      return fire();
    },
    take() {
      if (timer !== null) {
        clearTimer(timer);
        timer = null;
      }
      const value = pending;
      pending = null;
      return value;
    },
    waiting() {
      return pending !== null;
    },
  };
}

// --- Comparing one item by year (stage L1 of v2.2.0) ----------------------

// The ways to compare: the years in rows, laid over one another, or added up
// from the first day of the year (or of the month); from stage N1, also as a
// calendar of the days of each year.
export const COMPARE_MODES = ["rows", "overlay", "cumulative", "calendar"];
export const MAX_COMPARE_YEARS = 6;
export const FIRST_COMPARE_YEARS = 4;
// A leap year, so that 29 February has its place on the axis of the days.
const LEAP_BASE = 2024;

const two = (n) => String(n).padStart(2, "0");
const dayCount = (iso) => Math.round(Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10))) / 86400000);
const lastOfMonth = (year, month) => new Date(Date.UTC(year, month, 0)).getUTCDate();
// The Monday of the week of a day, as a count of days (1 January 1970 was a
// Thursday).
const mondayOf = (iso) => {
  const day = dayCount(iso);
  return day - ((((day + 3) % 7) + 7) % 7);
};

// The years of an output, newest first, each with its days in the output.
export function compareYears(firstDay, lastDay) {
  const day = /^\d{4}-\d{2}-\d{2}$/;
  if (typeof firstDay !== "string" || typeof lastDay !== "string" || !day.test(firstDay) || !day.test(lastDay) || firstDay > lastDay) {
    return [];
  }
  const years = [];
  for (let year = Number(lastDay.slice(0, 4)); year >= Number(firstDay.slice(0, 4)); year -= 1) {
    years.push({
      year,
      start: year === Number(firstDay.slice(0, 4)) ? firstDay : `${year}-01-01`,
      end: year === Number(lastDay.slice(0, 4)) ? lastDay : `${year}-12-31`,
    });
  }
  return years;
}

// The years chosen at first: the newest ones, up to FIRST_COMPARE_YEARS.
export function firstCompareYears(years) {
  return years.slice(0, FIRST_COMPARE_YEARS).map((entry) => entry.year);
}

// A year added or taken away: newest first, one at least, six at most.
export function toggledYears(chosen, year) {
  if (chosen.includes(year)) {
    return chosen.length > 1 ? chosen.filter((entry) => entry !== year) : chosen;
  }
  return chosen.length >= MAX_COMPARE_YEARS ? chosen : [...chosen, year].sort((a, b) => b - a);
}

// The days that a year asks for: the whole year, or one month of it.
export function compareRange(year, month) {
  if (month) {
    return { from: `${year}-${two(month)}-01`, to: `${year}-${two(month)}-${two(lastOfMonth(year, month))}` };
  }
  return { from: `${year}-01-01`, to: `${year}-12-31` };
}

// The grouping that gives the value of the whole year, or of the month, as
// one period of the server (never a new way to count).
export function compareValueGrain(month) {
  return month ? "month" : "year";
}

// The groupings of a comparison, and the one at first: by month over a year,
// by day over a month; a running total goes by day, and a calendar by day
// only (stage N1 of v2.2.0).
export function compareGrains(month, mode = "rows") {
  if (mode === "calendar") {
    return ["day"];
  }
  return month ? ["day", "week"] : ["day", "week", "month"];
}

export function firstCompareGrain(mode, month) {
  return mode === "cumulative" || mode === "calendar" || month ? "day" : "month";
}

// The month that a comparison uses: none while it is a calendar, which shows
// whole years; the month remembered stays as it is for the other ways
// (Codex's review of the plan of N1).
export function compareMonthFor(mode, month) {
  return mode === "calendar" ? null : month;
}

// Whether a comparison asks for its numbers again when its way changes: where
// its grouping, or the month that it uses, is another (Codex's review of the
// plan of N1: a month chosen and a calendar ask for other days).
export function compareAsksAgain(before, after) {
  return before.grain !== after.grain || before.month !== after.month;
}

// Where each period of a year is on the shared axis: a week by its order from
// the week of the first day (Monday weeks, so that a year may have 54), a day
// by its month and day (on a leap year), a month by its number; in one month,
// a day by its day. The days of the period stay with it, for its readings.
export function compareSlots(periods, grain, year, month) {
  const first = compareRange(year, month).from;
  const monday = mondayOf;
  return (Array.isArray(periods) ? periods : []).map((period) => {
    let slot;
    if (grain === "day") {
      slot = month ? Number(period.start.slice(8, 10)) - 1 : dayCount(`${LEAP_BASE}${period.start.slice(4)}`) - dayCount(`${LEAP_BASE}-01-01`);
    } else if (grain === "month") {
      slot = month ? 0 : Number(period.start.slice(5, 7)) - 1;
    } else {
      slot = (monday(period.start) - monday(first)) / 7;
    }
    return { start: slot, end: slot, partial: period.partial === true, from: period.start, to: period.end };
  });
}

// The last place on the shared axis of the years chosen.
export function compareSpan(grain, month, years) {
  if (grain === "day") {
    if (!month) {
      return 365;
    }
    return Math.max(...(years.length ? years : [LEAP_BASE]).map((year) => lastOfMonth(year, month))) - 1;
  }
  if (grain === "month") {
    return month ? 0 : 11;
  }
  return Math.max(0, ...years.map((year) => {
    const range = compareRange(year, month);
    return (mondayOf(range.to) - mondayOf(range.from)) / 7;
  }));
}

// A running total of the values of a year: a period without a record (0)
// adds nothing and keeps the line; a period without a value (null) breaks the
// line there, and the total goes on from what it was after it (the checker's
// L1-2); before the first value and after the last, there is none.
export function runningTotal(values) {
  let total = 0;
  return (Array.isArray(values) ? values : []).map((value) => {
    if (!Number.isFinite(value)) {
      return null;
    }
    total += value;
    return total;
  });
}

// The way of a comparison for an item: a running total only of a total, and
// a calendar only of an item of one value a day (not of the records of an
// estimate, of which a day may have several).
export function compareModeFor(item, mode) {
  if (!COMPARE_MODES.includes(mode)) {
    return "rows";
  }
  if (mode === "cumulative" && !isTotal(item ?? {})) {
    return "rows";
  }
  return mode === "calendar" && !calendarItem(item) ? "rows" : mode;
}

export function calendarItem(item) {
  return typeof item?.kind === "string" && item.kind !== "obs";
}

// The step of the color of each year chosen, 1 to 6: the newest the 6th.
export function yearSteps(years) {
  const sorted = [...years].sort((a, b) => b - a);
  return new Map(sorted.map((year, index) => [year, MAX_COMPARE_YEARS - index]));
}

// Whether the answer of a year is cut by the days of the output: the days
// that it starts after the range asked for, and that it ends before it, by the
// periods of the answer (never by the first and last days of the output).
export function compareCut(range, answer) {
  const start = typeof answer?.start === "string" ? answer.start : null;
  const end = typeof answer?.end === "string" ? answer.end : null;
  return {
    from: start !== null && start > range.from ? start : null,
    to: end !== null && end < range.to ? end : null,
  };
}

// The series of an item with several lines (VO2 Max: the source and the
// sport), by a key of their names; "" for an item of one line.
export function seriesKey(line) {
  const series = seriesOf(line);
  return series === null ? "" : JSON.stringify([String(series.vo2max_source_series ?? ""), String(series.sport ?? "")]);
}

// The series that a comparison can choose, in the order of the lines of a
// panel of the whole output; none for an item of one line.
export function compareSeries(panel) {
  const lines = Array.isArray(panel?.lines) ? panel.lines : [];
  if (lines.length < 2) {
    return [];
  }
  return lines.map((line, index) => ({ key: seriesKey(line), index }));
}

// The series chosen at first: that of the newest source, running if it has
// it; null for an item of one line.
export function firstCompareSeries(panel) {
  const lines = Array.isArray(panel?.lines) ? panel.lines : [];
  if (lines.length < 2) {
    return null;
  }
  const newest = String(seriesOf(lines[lines.length - 1])?.vo2max_source_series ?? "");
  const running = lines.find((line) => String(seriesOf(line)?.vo2max_source_series ?? "") === newest && String(seriesOf(line)?.sport ?? "") === "RUNNING");
  return seriesKey(running ?? lines[lines.length - 1]);
}

// The line of a year's panel for the series chosen: the only line of an item
// of one line, and none when the year has no line of that series.
export function compareLine(panel, key) {
  const lines = Array.isArray(panel?.lines) ? panel.lines : [];
  if (key === null || key === undefined) {
    return lines[0] ?? null;
  }
  return lines.find((line) => seriesKey(line) === key) ?? null;
}

// The words of the value of a year (or of a month), by the kind of the item,
// as the labels of the panels of 2.1.0 say them.
const COMPARE_VALUE_KEYS = {
  sum: "view.compare.value.sum",
  count: "view.compare.value.count",
  pace: "view.compare.value.pace",
  tw: "view.compare.value.tw",
  max: "view.compare.value.max",
  day: "view.compare.value.day",
  obs: "view.compare.value.obs",
};

export function compareValueMessage(item, month, language) {
  const key = Object.hasOwn(COMPARE_VALUE_KEYS, item?.kind) ? COMPARE_VALUE_KEYS[item.kind] : COMPARE_VALUE_KEYS.day;
  const period = month
    ? plain(new Intl.DateTimeFormat(language, { month: "long", timeZone: "UTC" }).format(new Date(Date.UTC(LEAP_BASE, month - 1, 1))))
    : message("view.compare.whole_year");
  return message(key, {}, { period });
}

// The box of a stop of a comparison: that of the panels, but for an answer
// too large, its next step is the grouping, as the period is not used while
// comparing: week or month over a year, and week over one month, where month
// is not used (the checker's L1-3).
export function compareStopBox(code, detail, current, month = null) {
  const box = stopBox(code, detail, current);
  if (code !== "VIEW_ANSWER_TOO_LARGE") {
    return box;
  }
  const step = month ? "view.compare.too_large_next_month" : "view.compare.too_large_next";
  return { ...box, lines: box.lines.map((line) => (line.key === "next.label" ? message("next.label", {}, { step }) : line)) };
}

// The way and the month of a comparison as the settings remember them: one
// row per year and the whole year where they remember none, or another form.
export function compareToOpen(settings) {
  const mode = settings?.view_compare_mode;
  const month = settings?.view_compare_month;
  return {
    mode: COMPARE_MODES.includes(mode) ? mode : "rows",
    month: Number.isInteger(month) && month >= 1 && month <= 12 ? month : null,
  };
}

// The value of a year (or of a month of it) in the answer of the whole output
// grouped by year (or by month): the value of the series chosen, its count,
// and whether the output cuts it; null where the output has none of it.
export function compareValue(answer, year, month, series) {
  const periods = Array.isArray(answer?.periods) ? answer.periods : [];
  const prefix = month ? `${year}-${two(month)}-` : `${year}-`;
  const index = periods.findIndex((period) => typeof period?.start === "string" && period.start.startsWith(prefix));
  if (index < 0) {
    return null;
  }
  const line = compareLine(answer.panels?.[0], series);
  const value = line?.values?.[index];
  const count = line?.counts?.[index];
  return {
    value: Number.isFinite(value) ? value : null,
    count: Number.isInteger(count) ? count : 0,
    partial: periods[index].partial === true,
  };
}

// The years of a comparison as they are drawn, newest first: the step of the
// color of each, the periods of its answer and their places on the shared
// axis, the values of the series chosen (a running total for that way), its
// counts and the points of its records, the days that the output cuts, and
// the value of the year (or of the month). From stage M2, each has the names
// that the drawing uses for a year as for a race: its id, its name, and the
// short one at the end of its line.
export function compareData({ years, month, grain, mode, series, answers, whole }) {
  const steps = yearSteps(years);
  return [...years].sort((a, b) => b - a).map((year) => {
    const answer = answers?.get(year) ?? null;
    const periods = Array.isArray(answer?.periods) ? answer.periods : [];
    const line = compareLine(answer?.panels?.[0], series);
    const values = periods.map((_period, index) => (Number.isFinite(line?.values?.[index]) ? line.values[index] : null));
    const range = compareRange(year, month);
    return {
      year,
      id: String(year),
      label: message("view.compare.year", { year: String(year) }),
      short: plain(String(year)),
      step: steps.get(year),
      range,
      periods,
      slots: compareSlots(periods, grain, year, month),
      values: mode === "cumulative" ? runningTotal(values) : values,
      counts: periods.map((_period, index) => (Number.isInteger(line?.counts?.[index]) ? line.counts[index] : 0)),
      points: mode !== "cumulative" && Array.isArray(line?.points) ? line.points : null,
      cut: compareCut(range, answer),
      whole: compareValue(whole, year, month, series),
      outside: periods.length === 0,
    };
  });
}

// The series that a comparison offers, by the names of the legend of 2.1.0.
export function compareSeriesChoices(panel, language) {
  const names = lineNames(panel, language);
  return compareSeries(panel).map((entry) => ({ key: entry.key, name: names[entry.index] }));
}

// The name of a place on the shared axis, for the rows of the table and for
// what the keyboard says: a month, a day by its month and day, or a week by
// its order in the year (or in the month).
export function compareSlotName(slot, grain, month, language) {
  if (grain === "week") {
    return message("view.compare.week_number", { n: slot + 1 });
  }
  if (grain === "month") {
    return plain(dateFormat(language, "month_name").format(new Date(Date.UTC(LEAP_BASE, (month || slot + 1) - 1, 1))));
  }
  const day = month ? new Date(Date.UTC(LEAP_BASE, month - 1, slot + 1)) : new Date(Date.UTC(LEAP_BASE, 0, slot + 1));
  return plain(dateFormat(language, "month_day").format(day));
}

// Where the axis under the years compared is marked, as places on it: the
// first day of each month over a year, and every seventh day from the first
// over a month; by week, the day in its week among the weeks of ``year``.
export function compareTicks(grain, month, year, language) {
  const days = month
    ? [1, 8, 15, 22, 29].filter((day) => day <= lastOfMonth(year, month)).map((day) => `${year}-${two(month)}-${two(day)}`)
    : Array.from({ length: 12 }, (_none, index) => `${year}-${two(index + 1)}-01`);
  const first = compareRange(year, month).from;
  return days.map((iso) => {
    let at;
    if (grain === "week") {
      at = (dayCount(iso) - mondayOf(first)) / 7;
    } else if (grain === "day") {
      at = month ? Number(iso.slice(8, 10)) - 1 : dayCount(`${LEAP_BASE}${iso.slice(4)}`) - dayCount(`${LEAP_BASE}-01-01`);
    } else {
      at = Number(iso.slice(5, 7)) - 1;
    }
    return { at, text: dateFormat(language, month ? "tick_day" : "tick_month").format(utcDate(iso)) };
  });
}

// What the heading of a year (long) or the end of its line (short) says of
// the days that the output cuts: until its last day, from its first, or both.
export function compareNote(cut, language, short = false) {
  const text = (iso) => dateFormat(language, short ? "tick_day" : "month_day").format(utcDate(iso));
  if (cut?.from && cut?.to) {
    return message("view.compare.between", { from: text(cut.from), to: text(cut.to) });
  }
  if (cut?.to) {
    return message("view.compare.until", { date: text(cut.to) });
  }
  if (cut?.from) {
    return message("view.compare.since", { date: text(cut.from) });
  }
  return null;
}

// A period of a year in the box of the readings, short: its days for a week,
// its name for a month, its day for a day, marked when it is cut.
function compareWhen(period, grain, language) {
  const short = (iso) => dateFormat(language, "tick_day").format(utcDate(iso));
  let name;
  if (grain === "week") {
    name = plain(`${short(period.start)}\u2013${short(period.end)}`);
  } else if (grain === "month") {
    name = plain(dateFormat(language, "month_name").format(utcDate(period.start)));
  } else {
    name = plain(short(period.start));
  }
  return period.partial ? message("view.period.partial", {}, { period: name }) : name;
}

// What the box of the readings says at a place of the shared axis, a line a
// year (newest first): its own period there and its value (the running total
// for that way) with its count, that it has no value there (where its line
// breaks), or that the output has no such period of it.
export function compareReadings(item, data, slot, grain, mode, language) {
  return data.map((entry) => {
    const names = { year: entry.year, id: entry.id, label: entry.label, short: entry.short };
    const index = entry.slots.findIndex((place) => place.start === slot);
    if (index < 0) {
      return { ...names, step: entry.step, period: null, value: null, count: null, missing: message("view.compare.outside") };
    }
    const value = entry.values[index];
    const has = Number.isFinite(value);
    return {
      ...names,
      step: entry.step,
      period: compareWhen(entry.periods[index], grain, language),
      value: has ? valueMessage(item.key, value, language) : null,
      count: has && mode !== "cumulative" ? countMessage(item, entry.counts[index], grain, language) : null,
      missing: has ? null : message("view.compare.no_value"),
    };
  });
}

// The table of a comparison: a row for each place of the shared axis, from
// the first, with the value and the count of each year (newest first); a
// period without a value says so, and a place that the year does not have
// (outside the output, or a week or a day that the year lacks) is outside;
// the last row holds the value of the year (or of the month). A running
// total has no counts, as in its readings. A comparison by race day gives the
// names of its places and of its last row (``axis``, stage M2).
export function compareTable(item, data, grain, month, span, language, mode = "rows", axis = null) {
  const counts = mode !== "cumulative";
  const heads = [message("view.compare.period")];
  for (const entry of data) {
    heads.push(entry.label);
    if (counts) {
      heads.push(message(countHeadKey(item)));
    }
  }
  const outside = { value: null, count: null, outside: true, partial: false };
  const rows = [];
  for (let slot = 0; slot <= span; slot += 1) {
    rows.push({
      period: axis === null ? compareSlotName(slot, grain, month, language) : axis.slotName(slot),
      cells: data.map((entry) => {
        const index = entry.slots.findIndex((place) => place.start === slot);
        if (index < 0) {
          return outside;
        }
        const value = entry.values[index];
        return {
          value: Number.isFinite(value) ? valueMessage(item.key, value, language) : null,
          count: counts ? countText(entry.counts[index], language) : null,
          outside: false,
          partial: entry.periods[index].partial === true,
        };
      }),
    });
  }
  const last = {
    period: axis === null ? compareValueMessage(item, month, language) : axis.whole,
    cells: data.map((entry) =>
      entry.whole === null
        ? outside
        : {
            value: entry.whole.value === null ? null : valueMessage(item.key, entry.whole.value, language),
            count: counts ? countText(entry.whole.count, language) : null,
            outside: false,
            partial: entry.whole.partial,
          },
    ),
  };
  return { heads, rows, last, counts };
}

// --- The calendar of comparing years (stage N1 of v2.2.0) ------------------

// The steps of the colors of a calendar: the six of the years.
export const CALENDAR_STEPS = 6;
// The keys of a calendar: a week to the left and to the right, a day up and
// down (Codex's review of the plan of N1).
const CALENDAR_KEYS = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1 };

// The place of a day in the calendar of its year: its column, the week by its
// order from the week of 1 January (Monday weeks, as the weeks of a year are
// counted), and its row, the day of the week from Monday (0) to Sunday (6).
export function calendarPlace(iso) {
  const day = dayCount(iso);
  return { week: (mondayOf(iso) - mondayOf(`${iso.slice(0, 4)}-01-01`)) / 7, day: (((day + 3) % 7) + 7) % 7 };
}

// The columns of the calendar of a year: 53, or 54.
export function calendarWeeks(year) {
  return (mondayOf(`${year}-12-31`) - mondayOf(`${year}-01-01`)) / 7 + 1;
}

// The day at a place of the calendar of a year (its column and its row), or
// null where the place is outside the year.
export function calendarDate(year, week, day) {
  const iso = isoOf(mondayOf(`${year}-01-01`) + week * 7 + day);
  return iso.slice(0, 4) === String(year) ? iso : null;
}

// The day under a point of the squares of the calendar of a year, by its
// column and its row (``x`` and ``y`` from the corner of the squares, which
// are ``pitch`` apart), or null outside them and outside the year.
export function calendarAt(year, x, y, pitch) {
  const week = Math.floor(x / pitch);
  const day = Math.floor(y / pitch);
  return week < 0 || day < 0 || day > 6 ? null : calendarDate(year, week, day);
}

// The names of the days of the week, from Monday, short (1 January 2024 was a
// Monday).
export function calendarWeekdays(language) {
  return Array.from({ length: 7 }, (_none, day) => dateFormat(language, "weekday").format(utcDate(`2024-01-0${day + 1}`)));
}

// The place of a day on the axis of the days of the years compared (a leap
// year), and the day of a place in a year: none for 29 February of a common
// year.
export function daySlot(iso) {
  return dayCount(`${LEAP_BASE}${iso.slice(4)}`) - dayCount(`${LEAP_BASE}-01-01`);
}

export function slotDay(slot, year) {
  const base = isoOf(dayCount(`${LEAP_BASE}-01-01`) + slot);
  return base.slice(5) === "02-29" && lastOfMonth(year, 2) === 28 ? null : `${year}${base.slice(4)}`;
}

// The days of a year that the output has: from its first day (or 1 January)
// to its last (or 31 December); null where it has none of them.
function calendarSpan(year, firstDay, lastDay) {
  const from = `${year}-01-01` > firstDay ? `${year}-01-01` : firstDay;
  const to = `${year}-12-31` < lastDay ? `${year}-12-31` : lastDay;
  return from <= to ? { from, to } : null;
}

// The day of a year that a calendar shows for a place of the shared axis: its
// own day, 28 February for 29 February of a common year, and the nearest day
// that the output has where it does not reach it; null without a day of the
// year in the output.
export function calendarDay(slot, year, firstDay, lastDay) {
  const span = calendarSpan(year, firstDay, lastDay);
  if (span === null) {
    return null;
  }
  const day = slotDay(slot, year) ?? `${year}-02-28`;
  return day < span.from ? span.from : day > span.to ? span.to : day;
}

// The place that a key of a calendar moves to, in the days of the year of its
// strip that the output has: a week, a day, or the first or last of them;
// it stops at their ends. Null for another key.
export function calendarMove(slot, year, key, firstDay, lastDay) {
  const span = calendarSpan(year, firstDay, lastDay);
  const day = calendarDay(slot, year, firstDay, lastDay);
  if (span === null || day === null) {
    return null;
  }
  let next;
  if (key === "Home") {
    next = span.from;
  } else if (key === "End") {
    next = span.to;
  } else if (Object.hasOwn(CALENDAR_KEYS, key)) {
    next = isoOf(Math.max(dayCount(span.from), Math.min(dayCount(span.to), dayCount(day) + CALENDAR_KEYS[key])));
  } else {
    return null;
  }
  return daySlot(next);
}

// What a day of a calendar draws: its value in a step, the outline of a day
// of a total without a recorded activity (0 counted from no record), or
// nothing (no value). A recorded 0, of activities of 0 km, is a value
// (Codex's review of the plan of N1).
export function calendarCell(item, value, count) {
  if (!Number.isFinite(value)) {
    return null;
  }
  return isTotal(item ?? {}) && value === 0 && count === 0 ? "zero" : "value";
}

// The step of the color of a value among the ticks of its scale (view_chart.mjs
// calendarScale), 1 to 6: each step holds its left tick and not its right
// one, and fewer steps than six spread over the six colors (four take the
// 1st, 3rd, 4th, and 6th).
export function calendarStep(ticks, value) {
  const steps = ticks.length - 1;
  if (steps <= 1) {
    return CALENDAR_STEPS;
  }
  const found = ticks.findIndex((tick, at) => at > 0 && value < tick);
  const index = found < 0 ? steps - 1 : found - 1;
  return Math.round(1 + (index * (CALENDAR_STEPS - 1)) / (steps - 1));
}

// The steps of the legend of a calendar, in the words of the ticks of a
// scale: below the first tick for a total, whose 0 without a record is an
// outline of its own, then from one tick to the next.
export function calendarLegend(item, ticks, language) {
  const step = Math.abs(ticks[1] - ticks[0]);
  const text = (value) => tickText(item.key, value, step, language);
  return ticks.slice(1).map((upper, index) => ({
    step: calendarStep(ticks, ticks[index]),
    words:
      index === 0 && isTotal(item)
        ? message("view.compare.calendar_under", { value: text(upper) })
        : message("view.compare.calendar_between", { from: text(ticks[index]), to: text(upper) }),
  }));
}

// What a calendar says of a day of a year: its date and day of the week, and
// its value with its count as a panel says them, that it is a day without a
// recorded activity, that it has no value, or that the output does not have
// it.
export function calendarReading(item, entry, day, language) {
  const date = utcDate(day);
  const name = message("view.compare.calendar_day", { date: dateFormat(language, "day").format(date), weekday: dateFormat(language, "weekday").format(date) });
  const index = entry.periods.findIndex((period) => period?.start === day);
  if (index < 0) {
    return { day: name, value: null, count: null, missing: message("view.compare.outside") };
  }
  const value = entry.values[index];
  const count = entry.counts[index];
  const cell = calendarCell(item, value, count);
  if (cell === null) {
    return { day: name, value: null, count: null, missing: message("view.no_value") };
  }
  return {
    day: name,
    value: cell === "zero" ? message("view.compare.calendar_zero", {}, { value: valueMessage(item.key, value, language) }) : valueMessage(item.key, value, language),
    count: cell === "zero" ? null : countMessage(item, count, "day", language),
    missing: null,
  };
}

// The values of the days that take a color, as the page shows them
// (``lines``, in km or minutes), of every year drawn, so that one scale holds
// them all: not the days without a value, nor those of a total without a
// recorded activity, which are outlines.
export function calendarValues(item, data, lines) {
  return data.flatMap((entry, index) => entry.values.flatMap((value, at) => (calendarCell(item, value, entry.counts[at]) === "value" ? [lines[index].values[at]] : [])));
}

// Whether the answer of a comparison can be drawn as a calendar: of the
// years, by day, and of whole years. While the answer of another way is still
// the last one (its numbers on their way), the calendar is not drawn from it
// (Codex's review of the diff of N1).
export function calendarAnswer(answer) {
  return answer?.by === "year" && answer.grain === "day" && answer.month === null;
}

// The days of the years drawn that a total has without a recorded activity,
// for the note under the legend.
export function calendarZeroDays(item, data) {
  return data.reduce((sum, entry) => sum + entry.values.filter((value, index) => calendarCell(item, value, entry.counts[index]) === "zero").length, 0);
}

// The note of those days, as a panel says it of the days of its period.
export function calendarZeroNote(count, language) {
  return message("view.note.zero", { n: countText(count, language) }, { grain: GRAIN_COUNT_KEYS.day });
}

// --- Comparing one item by race day (stage M2 of v2.2.0) -------------------

// What a comparison compares by: the years, or the race marks, each from some
// weeks before its day to the day; the weeks that it can take, and those at
// first.
export const COMPARE_BYS = ["year", "race"];
export const COMPARE_WEEKS = [8, 12, 16, 20, 24];
export const FIRST_COMPARE_WEEKS = 16;
export const MAX_COMPARE_RACES = MAX_COMPARE_YEARS;
// The grouping of the server that gives the value of the whole span of a race
// as one period (view/series.py RANGE_GRAIN), for the requests of a
// comparison only.
export const RANGE_GRAIN = "range";
// The races offered are those whose longest span meets the days of the
// output, so that a change of the weeks keeps them (Codex's review of the
// plan of M2); a shorter span outside the output is outside, as a year is.
const LONGEST_WEEKS = COMPARE_WEEKS[COMPARE_WEEKS.length - 1];
// The room of the name of a race where its whole name has no room (on its
// button, in the legend, at the end of its line, and in the box of the
// readings), in columns: a character of Chinese, Japanese, or Korean takes
// two, as in a font of one width.
const SHORT_RACE_NAME = 22;
const WIDE = /[\u1100-\u115f\u2e80-\u303e\u3041-\u33ff\u3400-\u4dbf\u4e00-\u9fff\ua000-\ua4cf\uac00-\ud7a3\uf900-\ufaff\ufe30-\ufe4f\uff00-\uff60\uffe0-\uffe6]|[\u{20000}-\u{3fffd}]/u;
const columns = (character) => (WIDE.test(character) ? 2 : 1);
const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
const isoOf = (count) => new Date(count * 86400000).toISOString().slice(0, 10);

// What a comparison compares by, and its weeks, as the settings remember
// them: the years and 16 weeks where they remember none, or another form.
export function compareByToOpen(settings) {
  const by = settings?.view_compare_by;
  const weeks = settings?.view_compare_weeks;
  return {
    by: COMPARE_BYS.includes(by) ? by : "year",
    weeks: COMPARE_WEEKS.includes(weeks) ? weeks : FIRST_COMPARE_WEEKS,
  };
}

// The days that a race asks for: from the Monday of the week ``weeks`` weeks
// before the week of its day, to its day (the first day of a mark of a span:
// the checker's M2-2), so that every race has as many weeks.
export function raceRange(day, weeks) {
  return { from: isoOf(mondayOf(day) - weeks * 7), to: day };
}

// The race marks that a comparison offers, newest first (of one day, the one
// added last first): those whose longest span meets the days of the output,
// a race after its last day too (the weeks before it so far).
export function compareRaces(marks, firstDay, lastDay) {
  if (typeof firstDay !== "string" || typeof lastDay !== "string" || !ISO_DAY.test(firstDay) || !ISO_DAY.test(lastDay) || firstDay > lastDay) {
    return [];
  }
  return (Array.isArray(marks) ? marks : [])
    .map((mark, index) => ({ mark, index }))
    .filter(({ mark }) => mark?.kind === "race" && typeof mark.day === "string" && ISO_DAY.test(mark.day))
    .filter(({ mark }) => mark.day >= firstDay && raceRange(mark.day, LONGEST_WEEKS).from <= lastDay)
    .sort((a, b) => (a.mark.day === b.mark.day ? b.index - a.index : a.mark.day < b.mark.day ? 1 : -1))
    .map(({ mark }) => mark);
}

// What a comparison compares by now: the race days only where the person
// chose them and two races at least are offered; the choice stays as it is.
export function compareByFor(by, races) {
  return by === "race" && Array.isArray(races) && races.length >= 2 ? "race" : "year";
}

// The races chosen at first: the newest ones, up to four.
export function firstCompareRaces(races) {
  return races.slice(0, FIRST_COMPARE_YEARS).map((race) => race.id);
}

// The races chosen that are still offered, in their order; the first ones
// where none is (a mark changed, removed, or forgotten, or another output).
export function racesKept(chosen, races) {
  const kept = races.map((race) => race.id).filter((id) => Array.isArray(chosen) && chosen.includes(id));
  return kept.length ? kept : firstCompareRaces(races);
}

// A race added or taken away: in the order of the races, one at least, six
// at most.
export function toggledRaces(chosen, id, races) {
  if (chosen.includes(id)) {
    return chosen.length > 1 ? chosen.filter((entry) => entry !== id) : chosen;
  }
  if (chosen.length >= MAX_COMPARE_RACES || !races.some((race) => race.id === id)) {
    return chosen;
  }
  const next = [...chosen, id];
  return races.map((race) => race.id).filter((entry) => next.includes(entry));
}

// The grouping of a comparison, and those that it can take: by week only by
// race day, also while its way is a running total (Codex's review of the plan
// of M2); by year, as from stage L1.
export function compareGrainFor(by, mode, month) {
  return by === "race" ? "week" : firstCompareGrain(mode, month);
}

export function compareGrainsFor(by, month, mode = "rows") {
  return by === "race" ? ["week"] : compareGrains(month, mode);
}

// The value of the whole span of a race in its answer of one period, of the
// series chosen, and whether the output cuts the span; null outside it.
export function raceValue(answer, series, cut) {
  const periods = Array.isArray(answer?.periods) ? answer.periods : [];
  if (!periods.length) {
    return null;
  }
  const line = compareLine(answer.panels?.[0], series);
  const value = line?.values?.[0];
  const count = line?.counts?.[0];
  return {
    value: Number.isFinite(value) ? value : null,
    count: Number.isInteger(count) ? count : 0,
    partial: cut?.from != null || cut?.to != null,
  };
}

// The head of a long name: at most ``size`` columns, the last "…".
export function shortName(name, size = SHORT_RACE_NAME) {
  const characters = Array.from(String(name));
  if (characters.reduce((sum, character) => sum + columns(character), 0) <= size) {
    return String(name);
  }
  const kept = [];
  let used = 1;
  for (const character of characters) {
    if (used + columns(character) > size) {
      break;
    }
    used += columns(character);
    kept.push(character);
  }
  return `${kept.join("")}…`;
}

// The short name of a race: the head of its name and its day, so that races
// of one name in one year are told apart (Codex's review of the diff of M2).
export function raceShort(race, language) {
  return message("view.compare.race_short", { name: shortName(race.name), date: dateFormat(language, "numeric_day").format(utcDate(race.day)) });
}

// The races of a comparison as they are drawn, in their order (newest first),
// in the form of the years (compareData): the step of the color of each, its
// weeks by their order from the first (0) to the week of the race (``weeks``),
// the days that the output cuts, and the value of its whole span. A week cut
// short is marked as the server marks it, the week of the race cut at its day
// as a week of a year at its ends (the checker's review of M2).
export function raceData({ races, weeks, mode, series, answers, wholes, language }) {
  return races.map((race, index) => {
    const answer = answers?.get(race.id) ?? null;
    const range = raceRange(race.day, weeks);
    const cut = compareCut(range, answer);
    const periods = Array.isArray(answer?.periods) ? answer.periods : [];
    const line = compareLine(answer?.panels?.[0], series);
    const values = periods.map((_period, at) => (Number.isFinite(line?.values?.[at]) ? line.values[at] : null));
    const first = mondayOf(range.from);
    return {
      year: Number(race.day.slice(0, 4)),
      id: race.id,
      label: message("view.compare.race", { name: race.name, date: dateText(race.day, language) }),
      short: raceShort(race, language),
      race,
      step: MAX_COMPARE_RACES - index,
      range,
      periods,
      slots: periods.map((period) => {
        const slot = (mondayOf(period.start) - first) / 7;
        return { start: slot, end: slot, partial: period.partial, from: period.start, to: period.end };
      }),
      values: mode === "cumulative" ? runningTotal(values) : values,
      counts: periods.map((_period, at) => (Number.isInteger(line?.counts?.[at]) ? line.counts[at] : 0)),
      points: mode !== "cumulative" && Array.isArray(line?.points) ? line.points : null,
      cut,
      whole: raceValue(wholes?.get(race.id) ?? null, series, cut),
      outside: periods.length === 0,
    };
  });
}

// The name of a place of the axis of the races: the weeks before the week of
// the race, and that week.
export function raceSlotName(slot, weeks) {
  return slot >= weeks ? message("view.compare.race_week") : message("view.compare.weeks_before", { n: weeks - slot });
}

// Where the axis under the races is marked: every fourth week before the
// race, and the week of the race.
export function raceTicks(weeks) {
  const ticks = [];
  for (let n = weeks; n >= 4; n -= 4) {
    ticks.push({ at: weeks - n, text: message("view.compare.weeks_before", { n }) });
  }
  ticks.push({ at: weeks, text: message("view.compare.race_week") });
  return ticks;
}

// The words of the value of the whole span of a race, by the kind of the
// item: short at the head of its row (this span), and in the last row of the
// table, the span itself (the checker's M2-1).
export function raceValueMessage(item, weeks, short = false) {
  const key = Object.hasOwn(COMPARE_VALUE_KEYS, item?.kind) ? COMPARE_VALUE_KEYS[item.kind] : COMPARE_VALUE_KEYS.day;
  const period = short ? message("view.compare.this_span") : message("view.compare.race_days", { n: weeks });
  return message(key, {}, { period });
}

// What the button of a race shows, its short name, and what the ear hears:
// its whole name and its days, the last day of a mark of a span too (the
// checker's M2-2), as the marks are said.
export function raceChip(race, language) {
  const days = markDays(race, language);
  return {
    short: raceShort(race, language),
    spoken:
      days.end === null
        ? message("view.marks.spoken_mark", { name: race.name, day: days.day })
        : message("view.marks.spoken_span", { name: race.name, day: days.day, end: days.end }),
  };
}


// --- The marks of the person (stage M1 of v2.2.0) --------------------------

export const MARK_KINDS = ["race", "injury", "shoes", "other"];
// The marks that the server keeps at most (gui/marks.py, MAX_MARKS).
export const MAX_MARKS = 200;
// The first day of a mark: the page counts its days with Date.UTC, which reads
// a year below 100 as one of the 1900s (gui/marks.py, FIRST_MARK_DAY).
export const FIRST_MARK_DAY = "1900-01-01";
// How many marks the label of the top chart names; it counts the rest.
export const SPOKEN_MARKS = 10;
// A file of the marks that is not used is never written over: the page does
// not change the marks while it is so.
export const MARKS_LOCKED = ["MARKS_UNREADABLE", "MARKS_NEWER"];
export const MARKS_NOTICE_KEYS = {
  MARKS_UNREADABLE: "view.marks.notice.unreadable",
  MARKS_NEWER: "view.marks.notice.newer",
  MARKS_NOT_WRITTEN: "view.marks.notice.not_written",
};
// What the window of the marks says of a change that cannot be made.
export const MARK_PROBLEM_KEYS = {
  MARK_NAME_INVALID: "view.marks.error.name",
  MARK_DAY_INVALID: "view.marks.error.day",
  MARK_NOT_FOUND: "view.marks.error.not_found",
  MARKS_FULL: "view.marks.error.full",
};

const MARK_DAY = /^\d{4}-\d{2}-\d{2}$/;

function markOk(mark) {
  return (
    mark !== null &&
    typeof mark === "object" &&
    typeof mark.id === "string" &&
    MARK_KINDS.includes(mark.kind) &&
    typeof mark.name === "string" &&
    typeof mark.day === "string" &&
    (mark.end === null || typeof mark.end === "string")
  );
}

// The marks of a list that the server gave, in its order (that of their
// days); anything else is no mark.
export function marksTaken(value) {
  return Array.isArray(value) ? value.filter(markOk) : [];
}

// What the page knows of the marks when it starts: the marks, whether they
// show (at first they do), and what to tell of their file.
export function marksToOpen(settings) {
  const notice = settings?.marks_notice;
  return {
    marks: marksTaken(settings?.view_marks),
    shown: settings?.view_marks_shown !== false,
    notice: typeof notice === "string" && Object.hasOwn(MARKS_NOTICE_KEYS, notice) ? notice : null,
  };
}

// Whether a day typed is one that a mark can have, as the server checks it:
// a date of the calendar, from FIRST_MARK_DAY.
export function markDayOk(value) {
  if (typeof value !== "string" || !MARK_DAY.test(value) || value < FIRST_MARK_DAY) {
    return false;
  }
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

// The problem of the days typed for a mark, or null: the last day of a span
// is not before its first, and with no last day the mark is of one day.
export function markDaysProblem(day, end) {
  if (!markDayOk(day) || (end !== "" && end !== null && (!markDayOk(end) || end < day))) {
    return "view.marks.error.day";
  }
  return null;
}

// The marks whose days meet the days from ``start`` to ``end`` (ISO dates).
export function marksWithin(marks, start, end) {
  return marks.filter((mark) => mark.day <= end && (mark.end ?? mark.day) >= start);
}

// What the label of the top chart says of the marks of its days: how many,
// the first SPOKEN_MARKS by name and day, and how many more; the labels of
// the other charts say how many only.
export function spokenMarks(marks) {
  return { count: marks.length, named: marks.slice(0, SPOKEN_MARKS), more: Math.max(0, marks.length - SPOKEN_MARKS) };
}

// The days of a mark as the language writes them: its day, and the last day
// of a span.
export function markDays(mark, language) {
  return { day: dateText(mark.day, language), end: mark.end ? dateText(mark.end, language) : null };
}

// --- The list of the activities of a period (stage M3 of v2.2.0) ----------

// The columns of the list after the date and time and the activity type, as
// the server sends them (view/series.py LIST_ITEMS); the item of the panel is
// one more column when it is none of them (Codex's review of the plan of M3).
export const LIST_ITEMS = ["dist", "time", "pace", "hr", "mx", "cad", "asc"];
// The rows of one list at most (view/series.py MAX_LIST_ROWS).
export const MAX_LIST_ROWS = 500;
// The finer grouping that lists a period of more activities than that.
const FINER_GRAINS = { year: "month", month: "week", week: "day" };
// The short unit of a column, which its head names; the clocks and the values
// as Garmin gives them have none.
const LIST_UNIT_KEYS = {
  km: "view.unit.km",
  pace: "view.list.unit_pace",
  bpm: "view.unit.bpm",
  m: "view.unit.m",
  cm: "view.unit.cm",
  ms: "view.unit.ms",
  pct: "view.unit.pct",
  pct_fit: "view.unit.pct",
};
// The local date and time of an activity as the output writes it
// (common/time.py): the date, and the time of the day before its offset.
const LOCAL_MOMENT = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(?::\d{2}(?:\.\d+)?)?/;
// What keeps the list open: the words, the scales, and the cross line, which
// moves to see another period; any other change of what the panels count or
// show closes it (the checker's review of the plan of M3).
const LIST_KEPT = ["language", "align", "cursor"];

// Whether a panel opens the list of the activities of its periods: a panel of
// an item of the activities (training and running form), drawn as a chart
// with values, not as a low strip or a table, and not while new numbers are
// on their way, as its chart is of the answer before (Codex's review of the
// plan of M3).
export function listOpens({ item, mode, table, empty, loading }) {
  return item !== null && item !== undefined && isActivityItem(item) && mode !== "mini" && !table && !empty && !loading;
}

// The list after a change of the page: kept or closed (null).
export function listAfter(list, change) {
  return list !== null && LIST_KEPT.includes(change) ? list : null;
}

// The order of the list after a head is pressed: the other way for the column
// of the order, and up for another.
export function listSorted(sort, column) {
  return sort.column === column ? { column, descending: !sort.descending } : { column, descending: false };
}

// The columns of the list of the panel of an item.
export function listColumns(key) {
  return ["when", "type", ...LIST_ITEMS, ...(LIST_ITEMS.includes(key) || key === "count" ? [] : [key])];
}

// The head of a column: its name, with the short unit of its values.
export function listHead(column) {
  if (column === "when") {
    return message("view.list.when");
  }
  if (column === "type") {
    return message("view.list.type");
  }
  const unit = LIST_UNIT_KEYS[ITEM_FORMATS[column].unit];
  return unit === undefined ? message(ITEM_KEYS[column]) : message("view.list.head", {}, { name: ITEM_KEYS[column], unit });
}

// A value of a row as the list writes it, without the unit that the head of
// its column names; the time of an activity in hours, minutes, and seconds.
// Null for none.
export function listValueText(key, value, language) {
  if (!Number.isFinite(value)) {
    return null;
  }
  return key === "time" ? clockSeconds(value) : shownText(key, shown(key, value), language);
}

// The local date and time of an activity as the list writes it: its date and
// its time of the day as the output has them, in the form of the language
// (9/14（月）6:30, Mon 9/14 6:30), without changing its timezone; the text as
// it is in another form; null without one.
export function listWhen(moment, language) {
  if (typeof moment !== "string" || moment === "") {
    return null;
  }
  const found = LOCAL_MOMENT.exec(moment);
  if (found === null) {
    return plain(moment);
  }
  const day = utcDate(found[1]);
  return message("view.list.moment", {
    date: dateFormat(language, "list_day").format(day),
    weekday: dateFormat(language, "weekday").format(day),
    time: `${Number(found[2])}:${found[3]}`,
  });
}

// What the list orders the date and time by: the date and the time of the day
// as they show, before the offset, so that the times read in their order where
// activities of other timezones are among them (the checker's review of the
// decisions of M3); the day of the row where its time cannot be read.
export function listMomentKey(row) {
  const found = typeof row.datetime === "string" ? LOCAL_MOMENT.exec(row.datetime) : null;
  return found === null ? row.day : found[0];
}

// The rows of the list in the order of a column, up or down: rows without a
// value last either way, and rows of the same value by their date and time,
// then in the order of the server. ``typeName`` gives the name of an activity
// type as the page writes it.
export function sortedListRows(rows, { column, descending }, typeName, language) {
  const keyOf = (row) => (column === "when" ? listMomentKey(row) : column === "type" ? typeName(row.type) : row.values?.[column]);
  const none = (key) => key === null || key === undefined || (typeof key === "number" && !Number.isFinite(key));
  const compared = (a, b) => {
    if (typeof a === "number") {
      return a - b;
    }
    if (column === "type") {
      return a.localeCompare(b, language);
    }
    return a < b ? -1 : a > b ? 1 : 0;
  };
  const order = rows.map((row, index) => ({ row, index, key: keyOf(row), moment: listMomentKey(row) }));
  order.sort((a, b) => {
    const noneA = none(a.key);
    const noneB = none(b.key);
    if (noneA !== noneB) {
      return noneA ? 1 : -1;
    }
    if (!noneA) {
      const by = compared(a.key, b.key);
      if (by !== 0) {
        return descending ? -by : by;
      }
    }
    if (column !== "when" && a.moment !== b.moment) {
      return a.moment < b.moment ? -1 : 1;
    }
    return a.index - b.index;
  });
  return order.map((entry) => entry.row);
}

// The heading of the list: its period, as the reading of its panel names it.
export function listTitle(period, grain, language) {
  return message("view.list.title", {}, { period: periodMessage(period, grain, language) });
}

// Which panel the list is of, and how many activities it has.
export function listFrom(key, total, language) {
  return message("view.list.from", { n: countText(total, language) }, { name: ITEM_KEYS[key] });
}

// The line under the list: the value of the panel for the period and how many
// activities it counted, as the server made them for the panel; the list does
// not count them again (Codex's review of the plan of M3, and the checker's).
export function listValueLine(key, value, language) {
  const shownValue = Number.isFinite(value?.value) ? valueMessage(key, value.value, language) : message("view.no_value");
  return { ...message("view.list.value", { n: countText(value?.count ?? 0, language) }, { value: shownValue }), strong: ["value"] };
}

// What the list says of a period of more activities than it shows: how many,
// and the finer grouping that lists them; of a day, only how many.
export function listLimitMessage(total, limit, grain, language) {
  const params = { n: countText(total, language), max: countText(limit, language) };
  return Object.hasOwn(FINER_GRAINS, grain)
    ? message("view.list.limit", params, { grain: GRAIN_KEYS[FINER_GRAINS[grain]] })
    : message("view.list.limit_day", params);
}

// --- Two items plotted against each other (stage O1 of v2.2.0) ------------

// The newest points that the server gives at most (view/series.py
// MAX_POINTS), and the two items at first (the sample of OP0).
export const MAX_POINTS = 5000;
export const PLOT_FIRST = Object.freeze({ x: "pace", y: "hr" });

// Whether an item can be plotted: one of the activities that one activity
// has a value of, which the count is not (view/series.py point_item).
export function plotItem(item) {
  return typeof item?.key === "string" && isActivityItem(item) && item.kind !== "count";
}

// The two items that the settings remember, as one pair of two different
// names; the first pair where they remember none, or another form (Codex's
// review of the plan of O1: never one of them alone). The table of the items
// checks them when an output is open (plotPairOf).
export function plotPairToOpen(settings) {
  const pair = settings?.view_plot;
  const named = (key) => typeof key === "string" && Object.hasOwn(ITEM_KEYS, key);
  return pair !== null && typeof pair === "object" && named(pair.x) && named(pair.y) && pair.x !== pair.y ? { x: pair.x, y: pair.y } : { ...PLOT_FIRST };
}

// The pair to plot among the items of an output: the pair as it is where
// both can be plotted, otherwise the first pair, and null where an output
// has neither.
export function plotPairOf(pair, items) {
  const known = itemsByKey(items);
  const can = (key) => plotItem(known.get(key));
  if (can(pair?.x) && can(pair?.y) && pair.x !== pair.y) {
    return { x: pair.x, y: pair.y };
  }
  return can(PLOT_FIRST.x) && can(PLOT_FIRST.y) ? { ...PLOT_FIRST } : null;
}

// The local date and time of a point as the reading and the table write it:
// with its year, since the points span years, as the output has it without
// changing its timezone, and its date only where its time cannot be read
// (Codex's review of the plan of O1).
export function plotWhen(point, language) {
  const found = typeof point?.datetime === "string" ? LOCAL_MOMENT.exec(point.datetime) : null;
  const day = utcDate(found === null ? point.day : found[1]);
  const parts = { date: dateFormat(language, "day").format(day), weekday: dateFormat(language, "weekday").format(day) };
  return found === null ? message("view.compare.calendar_day", parts) : message("view.plot.when", { ...parts, time: `${Number(found[2])}:${found[3]}` });
}

// The point under the pointer: the nearest of the places drawn (in pixels)
// within ``reach``, the newest of those as near (the points come oldest
// first); none farther (Codex's review of the plan of O1).
export function nearestPoint(places, x, y, reach) {
  let found = null;
  let nearest = reach * reach;
  places.forEach((place, index) => {
    const distance = (place.x - x) ** 2 + (place.y - y) ** 2;
    if (distance <= nearest) {
      found = index;
      nearest = distance;
    }
  });
  return found;
}

// How many other points have the same two values as one: they are drawn in
// the same place, and the keys reach every one of them.
export function sameValues(points, index, x, y) {
  const point = points[index];
  return point === undefined ? 0 : points.filter((other, at) => at !== index && other.values[x] === point.values[x] && other.values[y] === point.values[y]).length;
}

// The point that a key moves to among ``count`` points in the order of their
// date and time: the one before or after, the first or the last, stopping at
// the ends; from none chosen, the newest (or the first for Home). Null for
// another key.
export function plotMove(index, count, key) {
  if (!count) {
    return null;
  }
  if (key === "Home") {
    return 0;
  }
  if (key === "End") {
    return count - 1;
  }
  if (key !== "ArrowLeft" && key !== "ArrowRight") {
    return null;
  }
  if (index === null || index === undefined || index < 0 || index >= count) {
    return count - 1;
  }
  return Math.max(0, Math.min(count - 1, index + (key === "ArrowRight" ? 1 : -1)));
}

// The line under the points, in numbers only (the checker's review of the
// plan of O1): the points, the activities of the period, and those without
// both values; where the newest are kept, also how many have both values.
export function plotCount(answer, language) {
  const params = {
    points: countText(answer.points.length, language),
    total: countText(answer.total, language),
    with: countText(answer.with_values, language),
    missing: countText(answer.missing, language),
  };
  return message(answer.points.length < answer.with_values ? "view.plot.count_cut" : "view.plot.count", params);
}

// Whether the points are the newest only, and the words that say so (OP0).
export function plotCut(answer) {
  return Array.isArray(answer?.points) && answer.points.length < answer.with_values;
}

// The order of the table of the points with its columns: as it is, or the
// newest first where its column went with an item changed (Codex's review of
// the diff of O1).
export function plotSortAfter(sort, columns) {
  return columns.includes(sort?.column) ? sort : { column: "when", descending: true };
}

// What a point says: its date and time, its activity type, and its two
// values, as the reading and the keyboard give them.
export function plotReading(point, x, y, typeName, language, same = 0) {
  return {
    when: plotWhen(point, language),
    type: typeName(point.type),
    x: { name: message(ITEM_KEYS[x]), value: valueMessage(x, point.values[x], language) },
    y: { name: message(ITEM_KEYS[y]), value: valueMessage(y, point.values[y], language) },
    same: same > 0 ? message("view.plot.same", { n: countText(same, language) }) : null,
  };
}

// --- The distribution of one item (stage P1 of v2.2.0) ---------------------

// The item of the distribution first shown, as the sample of OP0 showed it.
export const SPREAD_FIRST = "dist";

// The item that the settings remember, by the rule of an item of the points;
// the first one where they remember none, or another form. The table of the
// items checks it when an output is open (spreadItemOf).
export function spreadItemToOpen(settings) {
  const key = settings?.view_spread;
  return typeof key === "string" && Object.hasOwn(ITEM_KEYS, key) ? key : SPREAD_FIRST;
}

// The item of the distribution among the items of an output: the item as it
// is where it can be counted, otherwise the distance, otherwise the first
// that can, and null where an output has none (the checker's review of the
// plan of P1, as plotPairOf).
export function spreadItemOf(key, items) {
  const known = itemsByKey(items);
  if (plotItem(known.get(key))) {
    return key;
  }
  if (plotItem(known.get(SPREAD_FIRST))) {
    return SPREAD_FIRST;
  }
  return (Array.isArray(items) ? items : []).find(plotItem)?.key ?? null;
}

// The end of the range ``number`` in the units of the output, or null where
// the page cannot write it: a number of a range past 2^53 is not exact in the
// page, so that two ends could be one value (Codex's review of the diff of
// P1), and an end that is not a number, as a value too large for the page.
function spreadEnd(answer, number) {
  const value = (number * answer.width) / answer.scale;
  return Number.isSafeInteger(number) && Number.isFinite(value) ? value : null;
}

// The left and the right end of the range ``index`` of an answer, in the
// units of the output, from the numbers of the answer only, so that the page
// keeps no width of its own (the checker's review of the plan of P1); none
// where the page cannot tell them apart, so that a range is never from a
// value to the same value.
export function spreadEnds(answer, index) {
  const left = spreadEnd(answer, answer.first + index);
  const right = spreadEnd(answer, answer.first + index + 1);
  return left !== null && right !== null && !(left < right) ? { left: null, right: null } : { left, right };
}

// The words of an end as the page shows the values of the item, with as many
// digits as the width of the ranges needs, as a tick has them; a dash where
// the page cannot write it, a value too large for it (Codex's review of the
// plan of P1: never Infinity, NaN, or a number of hundreds of digits).
function spreadEndText(key, value, step, language) {
  const shownValue = value === null ? null : shown(key, value);
  if (shownValue === null || !Number.isFinite(shownValue) || Math.abs(shownValue) >= 1e15) {
    return "\u2014";
  }
  return tickText(key, shownValue, shown(key, step), language);
}

// An end with the unit of its item, as a value is written; a clock has none.
function spreadEndValue(key, value, step, language) {
  const text = spreadEndText(key, value, step, language);
  const unit = ITEM_FORMATS[key].unit;
  return text !== "\u2014" && Object.hasOwn(VALUE_KEYS, unit) ? message(VALUE_KEYS[unit], { value: text }) : plain(text);
}

// A range in its short form, as the ends across and the table write it:
// 10〜11 km, 5:10〜5:20 /km (the checker's P1-3).
export function spreadRange(key, answer, index, language) {
  const { left, right } = spreadEnds(answer, index);
  const step = answer.width / answer.scale;
  return message("view.spread.range", { from: spreadEndText(key, left, step, language) }, { to: spreadEndValue(key, right, step, language) });
}

// The words of the end of a range across.
export function spreadEndWords(key, answer, end, language) {
  return spreadEndText(key, spreadEnd(answer, answer.first + end), answer.width / answer.scale, language);
}

// A range with its count, as the reading and the keys say it, with the
// meaning of its ends: 10 km or more and less than 11 km (the checker's P1-3).
export function spreadReading(key, answer, index, language) {
  const { left, right } = spreadEnds(answer, index);
  const step = answer.width / answer.scale;
  return message(
    "view.spread.reading",
    {},
    {
      from: spreadEndValue(key, left, step, language),
      to: spreadEndValue(key, right, step, language),
      n: message("view.value.count", { value: countText(answer.counts[index], language) }),
    },
  );
}

// The line under the ranges, in numbers only.
export function spreadCount(answer, language) {
  return message("view.spread.count", {
    total: countText(answer.total, language),
    with: countText(answer.with_values, language),
    missing: countText(answer.missing, language),
  });
}

// The width of a range in the unit and the form of its item: what the page
// says where it is wider than that of the item (OP-1 of v2.2.0), and what the
// line under a picture says always (Codex's review of the plan of R2).
export function spreadWidthValue(key, answer, language) {
  const step = answer.width / answer.scale;
  return spreadEndValue(key, Number.isFinite(step) ? step : null, step, language);
}

// The words of a wider width than that of the item (OP-1 of v2.2.0), or null.
export function spreadWide(key, answer, language) {
  if (!answer?.widened) {
    return null;
  }
  return message("view.spread.wide", { max: countText(answer.limit, language) }, { width: spreadWidthValue(key, answer, language) });
}

// The range that a key moves to among ``count`` ranges, those of 0 among
// them, as the rows of the table: the one before or after, stopping at the
// ends, the first or the last; from none chosen, the first for the right and
// the last for the left. Null for another key (the checker's P1-3).
export function spreadMove(index, count, key) {
  if (!count) {
    return null;
  }
  if (key === "Home") {
    return 0;
  }
  if (key === "End") {
    return count - 1;
  }
  if (key !== "ArrowLeft" && key !== "ArrowRight") {
    return null;
  }
  if (index === null || index === undefined || index < 0 || index >= count) {
    return key === "ArrowRight" ? 0 : count - 1;
  }
  return Math.max(0, Math.min(count - 1, index + (key === "ArrowRight" ? 1 : -1)));
}

// --- The summary of the panels (stage Q1 of v2.2.0) -----------------------

// The names of the columns of the summary for a period of the page: the
// period shown and the one of the same length just before it (none for all
// time), a range by its number of days.
const RECAP_NOW_KEYS = {
  "1y": "view.recap.now.years1",
  "3y": "view.recap.now.years3",
  "5y": "view.recap.now.years5",
  "10y": "view.recap.now.years10",
};
const RECAP_BEFORE_KEYS = {
  "1y": "view.recap.before.years1",
  "3y": "view.recap.before.years3",
  "5y": "view.recap.before.years5",
  "10y": "view.recap.before.years10",
};

export function recapColumns(period, language) {
  if (period !== null && typeof period === "object" && typeof period.from === "string" && typeof period.to === "string") {
    const days = daysBetween(period.from, period.to) + 1;
    return {
      now: message("view.recap.now.custom"),
      before: days === 1 ? message("view.recap.before.day") : message("view.recap.before.days", { n: countText(days, language) }),
    };
  }
  if (Object.hasOwn(RECAP_NOW_KEYS, period)) {
    return { now: message(RECAP_NOW_KEYS[period]), before: message(RECAP_BEFORE_KEYS[period]) };
  }
  return { now: message("view.recap.all"), before: null };
}

// A value as the page writes it, rounded as its text is: a clock as
// clockMinutes and clockSeconds round it (-30 seconds is 0:00, Codex's review
// of the diff of Q1), and a number by the same format as its text, which
// rounds 1.325 to 1.33 where toFixed gives 1.32.
function roundedShown(key, value) {
  const number = shown(key, value);
  if (clockOf(key) !== null) {
    return Math.round(number);
  }
  return Number(numberFormat("en", ITEM_FORMATS[key].digits).format(number).replaceAll(",", ""));
}

// The difference "now − before" of two values of an item as a number with
// its sign only, as the panels write a value (no arrow, no color, no word of
// a direction): the two values as the table writes them are subtracted, so
// that the difference is that of the two numbers read (stage Q1: 49.0 and
// 49.0 are never +0.1 apart); the value of the difference without its sign
// is written first, and a sign is put before it only where it does not read
// as 0, so that −0.0 never shows and a clock rounds both signs alike (Codex's
// review of the plan of Q1). A dash where a value is missing.
export function recapDifference(key, now, before, language) {
  if (!Number.isFinite(now) || !Number.isFinite(before)) {
    return plain("—");
  }
  const difference = roundedShown(key, now) - roundedShown(key, before);
  const text = shownText(key, Math.abs(difference), language);
  const signed = text === shownText(key, 0, language) ? text : `${difference > 0 ? "+" : "−"}${text}`;
  const unit = ITEM_FORMATS[key].unit;
  return Object.hasOwn(VALUE_KEYS, unit) ? message(VALUE_KEYS[unit], { value: signed }) : plain(signed);
}

// The words of a period that the output cuts (the checker's Q1-5): from the
// first day of the output, to its last day, or both; null for a period that
// the output holds whole. ``chosen`` is the period as chosen, an end of it
// null before the calendar; ``start`` and ``end`` the days of the output in it.
export function recapPartial(chosen, start, end, language) {
  if (typeof start !== "string" || typeof end !== "string") {
    return null;
  }
  const from = typeof chosen?.start !== "string" || chosen.start < start;
  const to = typeof chosen?.end !== "string" || chosen.end > end;
  if (from && to) {
    return message("view.recap.partial_both", { from: dateText(start, language), to: dateText(end, language) });
  }
  if (from) {
    return message("view.recap.partial_from", { date: dateText(start, language) });
  }
  if (to) {
    return message("view.recap.partial_to", { date: dateText(end, language) });
  }
  return null;
}

// The order of the lines of the server: the first day of the series in the
// whole output, then its source and its sport, each compared as text (the
// checker's Q1-8: the key of a line, a JSON text, sorts otherwise).
function lineOrder(a, b) {
  const first = (line) => String(line.first_day ?? "");
  const parts = (line) => {
    const series = seriesOf(line) ?? {};
    return [String(series.vo2max_source_series ?? ""), String(series.sport ?? "")];
  };
  for (const [x, y] of [[first(a), first(b)], ...parts(a).map((part, index) => [part, parts(b)[index]])]) {
    if (x !== y) {
      return x < y ? -1 : 1;
    }
  }
  return 0;
}

// The rows of an item in the summary (the checker's Q1-4 and Codex's review
// of the plan of Q1): a row for each series of the two periods, matched by
// its key, in the order of the server, named as one panel of them all; a
// line without a series is left out only where there is a series, as the
// server gives one where no series has a value; an item has a row at least.
// Each row holds the line of each period, or null where it has none.
export function recapRows(nowPanel, beforePanel, language) {
  const now = Array.isArray(nowPanel?.lines) ? nowPanel.lines : [];
  const before = Array.isArray(beforePanel?.lines) ? beforePanel.lines : [];
  const series = [...now, ...before].some((line) => seriesOf(line) !== null);
  const rows = new Map();
  for (const [side, lines] of [["now", now], ["before", before]]) {
    for (const line of lines) {
      if (series && seriesOf(line) === null) {
        continue;
      }
      const key = seriesKey(line);
      const row = rows.get(key) ?? { line, now: null, before: null };
      row[side] = line;
      rows.set(key, row);
    }
  }
  let ordered = [...rows.values()];
  if (series) {
    ordered.sort((a, b) => lineOrder(a.line, b.line));
  }
  if (!ordered.length) {
    ordered = [{ line: now[0] ?? before[0] ?? { series: null }, now: now[0] ?? null, before: before[0] ?? null }];
  }
  const names = lineNames({ lines: ordered.map((row) => row.line) }, language);
  return ordered.map((row, index) => ({ name: names[index], now: row.now, before: row.before }));
}

// The days that the two periods count, as the output cuts them, so that one
// sees what the summary compares (Codex's review of the plan of Q1: ‹ moves
// otherwise at the ends of the output and around 29 February).
export function recapDays(answer, columns, language) {
  if (typeof answer?.start !== "string" || typeof answer?.end !== "string") {
    return null;
  }
  const days = (start, end) => message("view.recap.span", { from: dateText(start, language), to: dateText(end, language) });
  const now = days(answer.start, answer.end);
  if (columns.before === null || !answer.previous) {
    return message("view.recap.days_one", {}, { now: columns.now, nowDays: now });
  }
  const previous = answer.previous;
  const before = typeof previous.start === "string" && typeof previous.end === "string" ? days(previous.start, previous.end) : message("view.recap.outside");
  return message("view.recap.days", {}, { now: columns.now, nowDays: now, before: columns.before, beforeDays: before });
}

// --- Saving as an image (stage R1 of v2.2.0) ------------------------------

// The properties of the styles of the page that a saved picture carries, each
// as the attribute of SVG that says the same: the colors and the lines of its
// shapes, and the sizes and forms of its letters. SVG has no attribute
// font-variant-numeric, and its font-variant takes the same value (Codex's
// review of the plan of R1); display is not written, as what does not show
// is left out; the font is written once, on the outer element.
export const SAVE_ATTRIBUTES = [
  ["fill", "fill"],
  ["stroke", "stroke"],
  ["stroke-width", "stroke-width"],
  ["stroke-dasharray", "stroke-dasharray"],
  ["stroke-linecap", "stroke-linecap"],
  ["stroke-linejoin", "stroke-linejoin"],
  ["opacity", "opacity"],
  ["fill-opacity", "fill-opacity"],
  ["stroke-opacity", "stroke-opacity"],
  ["font-size", "font-size"],
  ["font-weight", "font-weight"],
  ["font-variant-numeric", "font-variant"],
  ["paint-order", "paint-order"],
];
// The one of those that a shape does not take from the shape around it, with
// its first value.
const SAVE_NOT_INHERITED = { opacity: "1" };

// What a picture leaves out of the charts of the page: the cross line and the
// frame of the period of the list, and the marks unless the person puts them
// in (the plan of R1).
export const SAVE_LEFT_OUT = [".cross", ".list-frame"];
export const SAVE_MARKS = [".day-band", ".day-mark", ".day-mark-name"];

// The attributes that a shape of a picture takes from the styles computed for
// it in the page: all of them on the outer element; on the others, those that
// differ from the shape around them, or for opacity from its first value, so
// that the file stays small and shows the same. One that the shape has as an
// attribute of its own (``own``, as a chart draws a dash or a width) is
// written even so, as the page may override it by a style that the file does
// not keep (the checker's review of the diff of R1, (a)).
export function savedAttributes(computed, around = null, own = []) {
  const attributes = [];
  for (const [property, attribute] of SAVE_ATTRIBUTES) {
    const value = computed[property];
    if (typeof value !== "string" || value === "") {
      continue;
    }
    if (around !== null && !own.includes(attribute) && value === (Object.hasOwn(SAVE_NOT_INHERITED, property) ? SAVE_NOT_INHERITED[property] : around[property])) {
      continue;
    }
    attributes.push([attribute, value]);
  }
  return attributes;
}

const ITEM_KEY = /^[a-z0-9]+$/;

// The days of a saved picture: those of the answer, the period shown as ‹ ›
// move it, not the ends of the weeks or months of its panels (the checker's
// review of the plan of R1).
export function saveDays(answer) {
  return typeof answer?.start === "string" && typeof answer?.end === "string" ? { start: answer.start, end: answer.end } : null;
}

// The name of a saved picture: the days of the period shown (those of the
// answer, which ‹ › move, not the ends of its weeks or months) and the keys of
// the items of its panels in the order shown; nothing of the person's own,
// such as the folder of the output or the names of marks and layouts. Null
// where it cannot be made.
export function saveFileName(start, end, keys) {
  if (!ISO_DAY.test(String(start)) || !ISO_DAY.test(String(end)) || !keys.length || !keys.every((key) => ITEM_KEY.test(String(key)))) {
    return null;
  }
  return `garmin-view_${start}_${end}_${keys.join("-")}.svg`;
}

// The panels that a picture copies, in the order shown (the panel made big
// first: Codex's review of the plan of R1): those drawn as charts, or of them
// the one chosen, where only one is saved.
export function savedPanels(shown, tables, scope, chosen) {
  const charts = shown.filter((key) => !tables.includes(key));
  if (scope === "one") {
    return charts.includes(chosen) ? [chosen] : [];
  }
  return charts;
}

// Whether a picture can be saved: where the summary can show, and with an
// answer of the panels that is not on its way, no stop of the panels, and a
// chart to copy, as the answer on its way keeps the charts of the one before
// (Codex's review of the plan of R1).
export function saveShowable({ viewing, apart, full, items, answer, loading, stopped, charts }) {
  return Boolean(viewing && !apart && !full && items > 0 && answer !== null && answer !== undefined && !loading && !stopped && charts > 0);
}

// The pieces of the line under a picture: the period shown, the grain of the
// answer (not "auto"), the activity types that the answer counts as the field
// of the types says them (also an output without activities), and the name
// and version of the app; the page puts its separator between them.
export function saveFooter({ start, end, grain, answerTypes, types, version, language }) {
  const counted = Array.isArray(answerTypes) ? answerTypes : defaultTypes(types);
  return [
    message("view.save.period", { from: dateText(start, language), to: dateText(end, language) }),
    message("view.save.grain", {}, { grain: GRAIN_KEYS[grain] }),
    message("view.save.types", {}, { types: typesSummary(counted, types) }),
    typeof version === "string" && version !== "" ? message("view.save.app", { version }, { app: "app.title" }) : message("app.title"),
  ];
}

// The lines of a row of pieces of text in a width (a heading with its keys,
// or the line under a picture), as SVG does not wrap its text (Codex's review
// of the plan of R1): each piece follows the one before after the gap where
// it fits, and starts a new line where it does not; a piece wider than the
// width is cut where it fits, after a space where it has one. ``measure``
// gives the width of a text of a piece.
export function saveLines(pieces, width, gap, measure) {
  const lines = [];
  let line = [];
  let end = 0;
  const close = () => {
    if (line.length) {
      lines.push(line);
    }
    line = [];
    end = 0;
  };
  for (const piece of pieces) {
    let rest = String(piece.text);
    while (rest !== "") {
      const start = line.length ? end + gap : 0;
      const size = measure(rest, piece);
      if (start + size <= width) {
        line.push({ ...piece, text: rest, x: start, width: size });
        end = start + size;
        break;
      }
      if (line.length) {
        close();
        continue;
      }
      const cut = cutText(rest, width, (text) => measure(text, piece));
      const text = rest.slice(0, cut);
      line.push({ ...piece, text, x: 0, width: measure(text, piece) });
      close();
      rest = rest.slice(cut).replace(/^\s+/u, "");
    }
  }
  close();
  return lines;
}

// Where a text wider than the width is cut: after the last space before the
// letters that fit, or else after the last letter that fits, at least one
// letter, never inside a pair of the letters of UTF-16.
function cutText(text, width, measure) {
  const letters = Array.from(text);
  let fits = letters[0].length;
  let length = 0;
  for (const letter of letters) {
    length += letter.length;
    if (measure(text.slice(0, length)) > width) {
      break;
    }
    fits = length;
  }
  const space = text.lastIndexOf(" ", fits - 1);
  return space > 0 ? space : fits;
}

// The frame of a picture: its width and the height of its parts, grown to
// hold what they show out of their own frames, such as a label at the end of
// the time axis, with the room of the outlines of the words (Codex's review
// of the diff of R1). ``boxes`` are the edges of what the picture draws.
export function saveFrame(boxes, width, height, pad = 4) {
  let left = 0;
  let top = 0;
  let right = width;
  let bottom = height;
  for (const box of boxes) {
    left = Math.min(left, box.left - pad);
    top = Math.min(top, box.top - pad);
    right = Math.max(right, box.right + pad);
    bottom = Math.max(bottom, box.bottom + pad);
  }
  const x = Math.floor(left);
  const y = Math.floor(top);
  return { x, y, width: Math.ceil(right) - x, height: Math.ceil(bottom) - y };
}

// What the line after a saving is said of: the output, the period, the types,
// the items of the panels, and the language. A change of any of them takes
// the line away; a drawing again does not (the checker's review of the plan
// of R1).
export function saveNoticeKey({ ticket, period, types, items, language, view = "panels", content = null }) {
  const key = [ticket ?? null, period ?? null, types ?? null, items ?? [], language ?? null];
  // Another view adds what it shows (stage R2 of v2.2.0); the panels keep
  // the key of R1, which a panel made big does not change (the checker's
  // review of the handling of Codex's review of the plan of R2).
  return JSON.stringify(view === "panels" ? key : [...key, view, content ?? null]);
}

// --- Saving the other views as an image (stage R2 of v2.2.0) ---------------

// What a picture of another view leaves out (the checker's answer 4 of the
// plan of R2): the cross line and the frame of the day chosen of a
// comparison, and the point or the range chosen, which lie on top of the
// points and the bars, so that those stay.
export const SAVE_LEFT_OUT_VIEWS = {
  compare: [".cross", ".calendar-cursor"],
  plot: [".plot-chosen"],
  spread: [".spread-chosen"],
};

// Whether the window of the saving shows (Codex's review of the plan of R2,
// apart from whether it can save): an output shown and the view of the
// button that opened it showing; for the panels, as in R1, panels and not
// the graphs only. A view that cannot save yet shows the window with why.
export function saveWindowShows({ viewing, from, view, items, full }) {
  return Boolean(viewing && from === view && (view !== "panels" || (items > 0 && !full)));
}

// Whether another view can be saved now: its answer drawn, not on its way,
// no stop, not shown as a table, and its charts to copy (Codex's review of
// the plan of R2).
export function saveViewReady({ answer, loading, stopped, table, charts }) {
  return Boolean(answer !== null && answer !== undefined && !loading && !stopped && !table && charts > 0);
}

// Why a picture cannot be saved now, which the window says (Codex's review of
// the diff of R2): a view shown as a table, numbers that stopped loading, an
// answer without values to draw, or a chart without room to be drawn; none
// while an answer is on its way, which the window says by itself.
export function saveProblem({ table = false, stopped = false, loading = false, answer = null, empty = false, drawn = 0, parts = 0 }) {
  if (table) {
    return "view.save.table";
  }
  if (stopped) {
    return "view.save.stopped";
  }
  if (loading || answer === null || answer === undefined) {
    return null;
  }
  if (empty) {
    return "view.save.empty";
  }
  return drawn < parts ? "view.save.undrawn" : null;
}

// The name of the file of a picture of another view (the checker's R2-2 and
// answer 2): the years compared, oldest first, as they were chosen, which can
// skip some, or the days of the races compared, never their names; the
// period of the points or of the ranges; and the keys of the items. None
// where any of them is not of its form, as for the panels (saveFileName).
export function saveViewFileName(view, { key = null, keys = [], years = [], days = [], start = null, end = null } = {}) {
  const items = view === "plot" ? keys : [key];
  if (!items.length || !items.every((each) => typeof each === "string" && ITEM_KEY.test(each))) {
    return null;
  }
  if (view === "compare") {
    if (years.length) {
      const sorted = years.map(String).sort();
      return sorted.every((year) => /^\d{4}$/.test(year)) ? `garmin-compare_${sorted.join("-")}_${key}.svg` : null;
    }
    const sorted = days.map(String).sort();
    return sorted.length && sorted.every((day) => ISO_DAY.test(day)) ? `garmin-compare-races_${sorted.join("_")}_${key}.svg` : null;
  }
  if (!ISO_DAY.test(String(start)) || !ISO_DAY.test(String(end))) {
    return null;
  }
  if (view === "plot") {
    return `garmin-plot_${start}_${end}_${items.join("-")}.svg`;
  }
  return view === "spread" ? `garmin-spread_${start}_${end}_${key}.svg` : null;
}

// The pieces of the line under a picture of another view (the checker's R2-2
// and answer 2): the years compared, oldest first, with the grain of their
// answer, or the days of the races compared; the period of the points or of
// the ranges, and for the ranges their width in the unit of the item
// (Codex's review of the plan of R2); then the activity types that the view
// asked for and the name and version of the app, as under the panels
// (saveFooter). ``separator`` is that of a list in the language, and
// ``daysSeparator`` that of a list of days, whose English words have commas.
export function saveViewFooter(view, { years = [], days = [], grain = null, start = null, end = null, key = null, answer = null, answerTypes, types, version, language, separator, daysSeparator = separator }) {
  const counted = Array.isArray(answerTypes) ? answerTypes : defaultTypes(types);
  const kinds = message("view.save.types", {}, { types: typesSummary(counted, types) });
  const app = typeof version === "string" && version !== "" ? message("view.save.app", { version }, { app: "app.title" }) : message("app.title");
  if (view === "compare") {
    return years.length
      ? [message("view.save.compare_years", { years: years.map(String).sort().join(separator) }), message("view.save.grain", {}, { grain: GRAIN_KEYS[grain] }), kinds, app]
      : [message("view.save.compare_races", { days: days.map(String).sort().map((day) => dateText(day, language)).join(daysSeparator) }), kinds, app];
  }
  const period = message("view.save.period", { from: dateText(start, language), to: dateText(end, language) });
  return view === "spread" ? [period, message("view.save.width", {}, { width: spreadWidthValue(key, answer, language) }), kinds, app] : [period, kinds, app];
}
