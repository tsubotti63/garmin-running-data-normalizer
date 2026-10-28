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

// Minutes as hours and minutes: 1:05.
export function clockMinutes(minutes) {
  let hours = Math.floor(minutes / 60);
  let rest = Math.round(minutes - hours * 60);
  if (rest === 60) {
    hours += 1;
    rest = 0;
  }
  return `${hours}:${twoDigits(rest)}`;
}

// Seconds as hours, minutes, and seconds, or minutes and seconds under an
// hour: 1:02:03, 21:05.
export function clockSeconds(seconds) {
  const whole = Math.round(seconds);
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
    }[kind];
    dateFormats.set(name, new Intl.DateTimeFormat(language, { ...options, timeZone: "UTC" }));
  }
  return dateFormats.get(name);
}

function utcDate(iso) {
  const [year, month, day] = String(iso).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
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
// items, no shelf, no tips, and no colors, as the file has none now. The
// page keeps showing what it shows.
export function settingsAfterForget(settings) {
  const kept = { ...(settings ?? {}) };
  for (const name of ["view_items", "view_shelf", "hints", "theme"]) {
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
