// view_flow.mjs (stage G3b): the rules of the view page, as plain functions:
// how it writes the numbers of the server, the item shelf, the panels, the
// tables, and what it says before an output is open and when one cannot be
// shown. The catalogs are those of the page, so that the words checked are
// the words shown.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { translate } from "../../src/garmin_running_data_normalizer/gui/static/i18n.mjs";
import * as view from "../../src/garmin_running_data_normalizer/gui/static/view_flow.mjs";

const catalogs = Object.fromEntries(
  ["en", "ja"].map((language) => [
    language,
    JSON.parse(readFileSync(new URL(`../../src/garmin_running_data_normalizer/gui/static/i18n/${language}.json`, import.meta.url), "utf8")),
  ]),
);

// The words of a message, as the page writes them (view.mjs describe).
function words(message, language = "ja") {
  if (message === null || message === undefined) {
    return "";
  }
  if (typeof message.text === "string") {
    return message.text;
  }
  const params = { ...message.params };
  for (const [name, key] of Object.entries(message.keyParams ?? {})) {
    params[name] = typeof key === "string" ? translate(catalogs, language, key) : words(key, language);
  }
  return translate(catalogs, language, message.key, params);
}

// The server's table of the items (view/items.py), as the open answer has it.
const ITEMS = [
  { key: "dist", group: "act", kind: "sum", unit: "metre", unit_group: null, per_day: false, sleep: false, from_fit: false },
  { key: "pace", group: "act", kind: "pace", unit: "second_per_metre", unit_group: null, per_day: false, sleep: false, from_fit: false },
  { key: "hr", group: "act", kind: "tw", unit: "beats_per_minute", unit_group: "bpm", per_day: false, sleep: false, from_fit: false },
  { key: "asc", group: "act", kind: "sum", unit: "metre", unit_group: null, per_day: false, sleep: false, from_fit: true },
  { key: "gct", group: "fit", kind: "tw", unit: "millisecond", unit_group: null, per_day: false, sleep: false, from_fit: true },
  { key: "rhr", group: "body", kind: "day", unit: "beats_per_minute", unit_group: "bpm", per_day: false, sleep: false, from_fit: false },
  { key: "steps", group: "body", kind: "day", unit: null, unit_group: null, per_day: true, sleep: false, from_fit: false },
  { key: "sleep", group: "body", kind: "day", unit: "minute", unit_group: null, per_day: false, sleep: true, from_fit: false },
  { key: "hrv", group: "body", kind: "day", unit: null, unit_group: null, per_day: false, sleep: false, from_fit: false },
  { key: "vo2", group: "est", kind: "obs", unit: null, unit_group: null, per_day: false, sleep: false, from_fit: false },
  { key: "p5k", group: "est", kind: "obs", unit: "second", unit_group: null, per_day: false, sleep: false, from_fit: false },
];
const item = (key) => ITEMS.find((entry) => entry.key === key);

test("values are written in the units of the page, in each language", () => {
  const cases = [
    ["dist", 12345.6, "12.3 km", "12.3 km"],
    ["dist", 1234567, "1,234.6 km", "1,234.6 km"],
    ["time", 3 * 3600 + 5 * 60 + 29, "3:05", "3:05"],
    ["time", 59 * 60 + 40, "1:00", "1:00"],
    ["count", 12, "12 回", "12"],
    ["pace", 0.3125, "5:13 /km", "5:13 /km"],
    ["hr", 151.6, "152 bpm", "152 bpm"],
    ["rhr", 48.25, "48.3 bpm", "48.3 bpm"],
    ["cad", 172.04, "172.0", "172.0"],
    ["asc", 120.4, "120 m", "120 m"],
    ["vo", 91.4, "9.1 cm", "9.1 cm"],
    ["gct", 247.6, "248 ms", "248 ms"],
    ["gctp", 33.62, "33.6 %", "33.6%"],
    ["bal", 49.84, "49.8 %", "49.8%"],
    ["sl", 1180, "1.18 m", "1.18 m"],
    ["sleep", 6 * 60 + 59.6, "7:00", "7:00"],
    ["deep", 72.4, "72 分", "72 min"],
    ["p5k", 20 * 60 + 14, "20:14", "20:14"],
    ["pfull", 3 * 3600 + 2 * 60 + 5, "3:02:05", "3:02:05"],
    ["acwr", 1.1, "1.10", "1.10"],
    ["steps", 10234.4, "10,234", "10,234"],
  ];
  for (const [key, value, ja, en] of cases) {
    assert.equal(words(view.valueMessage(key, value, "ja"), "ja"), ja, key);
    assert.equal(words(view.valueMessage(key, value, "en"), "en"), en, key);
  }
  assert.equal(view.clockMinutes(0), "0:00");
  assert.equal(view.clockSeconds(59.6), "1:00");
  assert.equal(view.clockSeconds(3600), "1:00:00");
  // The units beside the names, and the values as the scale shows them.
  assert.equal(translate(catalogs, "ja", view.unitKey("pace")), "分:秒/km");
  assert.equal(translate(catalogs, "en", view.unitKey("bal")), "%, FIT value as is");
  assert.equal(view.shown("dist", 5000), 5);
  assert.equal(view.shown("time", 3600), 60);
  assert.equal(view.shown("pace", 0.3), 300);
  assert.equal(view.shown("dist", null), null);
  assert.equal(view.clockOf("time"), "minute");
  assert.equal(view.clockOf("pace"), "second");
  assert.equal(view.clockOf("p5k"), "second");
  assert.equal(view.clockOf("dist"), null);
  assert.equal(view.tickText("dist", 47.5, 0.5, "en"), "47.5");
  assert.equal(view.tickText("dist", 200, 100, "en"), "200");
  assert.equal(view.tickText("vo2", 52.25, 0.05, "en"), "52.25");
  assert.equal(view.tickText("p5k", 1230, 30, "en"), "20:30");
});

test("periods are named by their day, the Monday of their week, their month, or their year", () => {
  const period = { start: "2026-10-21", end: "2026-10-21", partial: false };
  assert.equal(words(view.periodMessage(period, "day", "ja"), "ja"), "2026年10月21日");
  assert.equal(words(view.periodMessage(period, "day", "en"), "en"), "October 21, 2026");
  // A week cut at its start is named by its Monday.
  const week = { start: "2026-10-21", end: "2026-10-25", partial: true };
  assert.equal(words(view.periodMessage(week, "week", "ja"), "ja"), "2026年10月19日の週（途中）");
  assert.equal(words(view.periodMessage(week, "week", "en"), "en"), "Week of October 19, 2026 (partial)");
  assert.equal(words(view.periodMessage(week, "week", "en", { mark: false }), "en"), "Week of October 19, 2026");
  const month = { start: "2026-10-01", end: "2026-10-21", partial: true };
  assert.equal(words(view.periodMessage(month, "month", "ja"), "ja"), "2026年10月（途中）");
  assert.equal(words(view.periodMessage(month, "month", "en"), "en"), "October 2026 (partial)");
  const year = { start: "2025-01-01", end: "2025-12-31", partial: false };
  assert.equal(words(view.periodMessage(year, "year", "ja"), "ja"), "2025年");
  assert.equal(words(view.periodMessage(year, "year", "en"), "en"), "2025");
  // The ticks of the time axis.
  const day = Math.round(Date.UTC(2026, 0, 1) / 86400000);
  assert.equal(view.timeTickText({ day, kind: "year" }, "ja"), "2026");
  assert.equal(view.timeTickText({ day, kind: "month_year" }, "ja"), "2026年1月");
  assert.equal(view.timeTickText({ day, kind: "month" }, "en"), "Jan");
  assert.equal(view.timeTickText({ day, kind: "day" }, "ja"), "1/1");
});

test("a panel says what its value of a period is", () => {
  assert.equal(view.kindKey(item("dist"), "month"), "view.kind.sum");
  assert.equal(view.kindKey({ kind: "count" }, "month"), "view.kind.count");
  assert.equal(view.kindKey(item("pace"), "month"), "view.kind.pace");
  assert.equal(view.kindKey(item("hr"), "month"), "view.kind.tw");
  assert.equal(view.kindKey({ kind: "max" }, "day"), "view.kind.max");
  assert.equal(view.kindKey(item("rhr"), "day"), "view.kind.day");
  assert.equal(view.kindKey(item("rhr"), "week"), "view.kind.day_mean");
  assert.equal(view.kindKey(item("steps"), "month"), "view.kind.day_mean_per_day");
  assert.equal(view.kindKey(item("vo2"), "day"), "view.kind.obs_points");
  assert.equal(view.kindKey(item("vo2"), "year"), "view.kind.obs_mean");
  // The count beside a value; a daily item has no count in a day.
  assert.equal(words(view.countMessage(item("dist"), 3, "month", "ja"), "ja"), "3 回");
  assert.equal(words(view.countMessage(item("gct"), 1234, "month", "en"), "en"), "activities: 1,234");
  assert.equal(words(view.countMessage(item("rhr"), 20, "month", "ja"), "ja"), "値のあった日 20");
  assert.equal(view.countMessage(item("rhr"), 1, "day", "ja"), null);
  assert.equal(words(view.countMessage(item("vo2"), 2, "day", "en"), "en"), "records: 2");
  assert.equal(view.countHeadKey(item("p5k")), "view.table.records");
});

test("the items that the settings remember are known names, once each, up to six", () => {
  assert.deepEqual(view.rememberedItems({ view_items: ["vo2", "nope", "dist", "vo2", 7] }, ITEMS), ["vo2", "dist"]);
  assert.equal(view.rememberedItems({ view_items: [] }, ITEMS), null);
  assert.equal(view.rememberedItems({ view_items: "dist" }, ITEMS), null);
  assert.equal(view.rememberedItems({}, ITEMS), null);
  assert.deepEqual(
    view.rememberedKeys({ view_items: ["dist", "time", "count", "pace", "hr", "mx", "cad", "hill", "dist"] }),
    ["dist", "time", "count", "pace", "hr", "mx"],
  );
  assert.equal(view.itemsRemembered({ view_items: ["nope"] }), false);
  assert.equal(view.itemsRemembered({ view_items: ["hill"] }), true);
  // The tips: as last switched, on either page; else on until the items are
  // remembered.
  assert.equal(view.viewHintsShown({ hints: false }), false);
  assert.equal(view.viewHintsShown({ hints: true, view_items: ["dist"] }), true);
  assert.equal(view.viewHintsShown({ hints: null, view_items: ["dist"] }), false);
  assert.equal(view.viewHintsShown({}), true);
  // The shelf is open unless it was folded.
  assert.equal(view.shelfOpen({ view_shelf: "closed" }), false);
  assert.equal(view.shelfOpen({ view_shelf: "open" }), true);
  assert.equal(view.shelfOpen({}), true);
});

test("after the other tab forgot the settings, the page remembers none of them", () => {
  const settings = { launch: "later", store: "/x", hints: false, theme: "dark", view_items: ["dist"], view_shelf: "closed", present: true };
  const forgotten = view.settingsAfterForget(settings);
  assert.deepEqual(forgotten, { launch: "later", store: "/x", present: false });
  assert.equal(view.itemsRemembered(forgotten), false);
  assert.equal(view.shelfOpen(forgotten), true);
  assert.equal(view.viewHintsShown(forgotten), true);
  assert.deepEqual(view.settingsAfterForget(null), { present: false });
  // The settings given are not changed.
  assert.deepEqual(settings.view_items, ["dist"]);
});

test("an output opens with the items shown, else those remembered, else its first items", () => {
  assert.deepEqual(view.itemsToOpen(["hr"], ["dist"], ["rhr"], ITEMS), ["hr"]);
  assert.deepEqual(view.itemsToOpen(null, ["dist", "nope"], ["rhr"], ITEMS), ["dist"]);
  assert.deepEqual(view.itemsToOpen(null, null, ["rhr", "vo2"], ITEMS), ["rhr", "vo2"]);
  assert.deepEqual(view.itemsToOpen([], ["nope"], [], ITEMS), []);
  assert.deepEqual(view.FIRST_KEYS, ["dist", "rhr", "vo2"]);
  // Up to six panels, in the order chosen; moving stops at the ends.
  const six = ["dist", "pace", "hr", "asc", "gct", "rhr"];
  assert.deepEqual(view.toggledItems(six, "vo2"), six);
  assert.deepEqual(view.toggledItems(six, "hr"), ["dist", "pace", "asc", "gct", "rhr"]);
  assert.deepEqual(view.toggledItems(["dist"], "vo2"), ["dist", "vo2"]);
  assert.deepEqual(view.movedItems(["a", "b", "c"], "b", -1), ["b", "a", "c"]);
  assert.deepEqual(view.movedItems(["a", "b", "c"], "c", 1), ["a", "b", "c"]);
  assert.deepEqual(view.movedItems(["a", "b", "c"], "x", 1), ["a", "b", "c"]);
});

test("the shelf finds items by the names shown, and stops at six", () => {
  const names = { dist: "Distance", pace: "Average pace", hr: "Average heart rate", rhr: "Resting heart rate", vo2: "VO2 Max" };
  const name = (key) => names[key] ?? key;
  const coverage = { dist: { months: ["2025-01", "2025-02"] } };
  const groups = view.shelfGroups(ITEMS, ["dist"], coverage, "  HEART ", name, { body: true });
  assert.deepEqual(groups.map((group) => group.group), ["act", "fit", "body", "est"]);
  assert.deepEqual(groups[0].rows.map((row) => row.key), ["hr"]);
  assert.equal(groups[0].chosen, 1);
  assert.deepEqual(groups[2].rows.map((row) => row.key), ["rhr"]);
  assert.equal(groups[2].open, false);
  const full = view.shelfGroups(ITEMS, ["dist", "pace", "hr", "asc", "gct", "rhr"], coverage, "", name);
  const rows = full.flatMap((group) => group.rows);
  assert.deepEqual(rows.filter((row) => row.disabled).map((row) => row.key), ["steps", "sleep", "hrv", "vo2", "p5k"]);
  assert.deepEqual(rows.find((row) => row.key === "dist").months, ["2025-01", "2025-02"]);
  // The bars of the shelf: runs of months from the first month of the output.
  assert.equal(view.monthIndex("2025-03") - view.monthIndex("2024-12"), 3);
  assert.equal(view.monthIndex("2025-03-17"), view.monthIndex("2025-03"));
  assert.deepEqual(view.coverageRuns(["2025-01", "2025-02", "2025-04", "2025-02"], view.monthIndex("2024-12")), [
    [1, 2],
    [4, 1],
  ]);
});

test("the activity types: in the words of the page, the running ones first, never none", () => {
  const types = [
    { name: "running", count: 900, running: true },
    { name: "road_biking", count: 40, running: false },
    { name: "trail_running", count: 30, running: true },
    { name: "paddling", count: 3, running: false },
    { name: "", count: 2, running: false },
  ];
  assert.equal(words(view.typeMessage("trail_running"), "ja"), "トレイルラン");
  assert.equal(words(view.typeMessage("paddling"), "ja"), "paddling");
  assert.equal(words(view.typeMessage(""), "en"), "No activity type");
  assert.deepEqual(view.defaultTypes(types), ["running", "trail_running"]);
  assert.equal(view.typesRequest(["trail_running", "running"], types), null);
  assert.deepEqual(view.typesRequest(["running"], types), ["running"]);
  assert.deepEqual(view.toggledTypes(["running"], "", types), ["running", ""]);
  assert.deepEqual(view.toggledTypes(["trail_running", "running"], "road_biking", types), ["running", "road_biking", "trail_running"]);
  assert.deepEqual(view.toggledTypes(["running"], "running", types), ["running"]);
  assert.equal(words(view.typesSummary(["running", "trail_running"], types), "ja"), "ランニングの種目すべて（2 つ）");
  assert.equal(words(view.typesSummary(["running"], types), "en"), "Types chosen: 1");
  assert.equal(words(view.typesSummary([], []), "ja"), "アクティビティの記録がありません");
});

test("a period is a choice, a range, the same length before or after, or a drag", () => {
  assert.equal(view.periodRequest("5y", null), "5y");
  assert.deepEqual(view.periodRequest("custom", { from: "2020-01-01", to: "2020-12-31" }), { from: "2020-01-01", to: "2020-12-31" });
  assert.equal(view.periodRequest("custom", null), "all");
  assert.equal(view.periodRequest("2y", null), "all");
  // The same length, within the days of the output.
  assert.deepEqual(view.shiftedRange("2020-01-01", "2020-01-31", -1, "2019-12-15", "2026-10-21"), { from: "2019-12-15", to: "2020-01-14" });
  assert.deepEqual(view.shiftedRange("2020-01-01", "2020-01-31", 1, "2011-04-01", "2026-10-21"), { from: "2020-02-01", to: "2020-03-02" });
  assert.deepEqual(view.shiftedRange("2026-09-01", "2026-09-30", 1, "2011-04-01", "2026-10-21"), { from: "2026-09-22", to: "2026-10-21" });
  assert.equal(view.shiftedRange("2011-04-01", "2026-10-21", -1, "2011-04-01", "2026-10-21"), null);
  assert.equal(view.shiftedRange("2011-04-01", "2026-10-21", 1, "2011-04-01", "2026-10-21"), null);
  assert.equal(view.shiftedRange(null, null, 1, "2011-04-01", "2026-10-21"), null);
  // What is wrong with a range that was typed.
  assert.equal(view.rangeProblem("", "2020-01-01", "2011-04-01", "2026-10-21"), "view.range.missing");
  assert.equal(view.rangeProblem("2021-01-01", "2020-01-01", "2011-04-01", "2026-10-21"), "view.range.order");
  assert.equal(view.rangeProblem("2027-01-01", "2027-02-01", "2011-04-01", "2026-10-21"), "view.range.outside");
  assert.equal(view.rangeProblem("2020-01-01", "2020-01-01", "2011-04-01", "2026-10-21"), null);
  // A drag of less than a week is a click.
  assert.equal(view.draggedRange(100, 105), null);
  assert.deepEqual(view.draggedRange(300, 100), { from: 100, to: 300 });
  // "Auto" as the server takes it.
  assert.equal(view.autoGrainOf("2020-01-01", "2022-12-31"), "week");
  assert.equal(view.autoGrainOf("2020-01-01", "2023-01-01"), "month");
  assert.equal(view.autoGrainOf("2020-01-01", "2020-12-31"), "day");
  assert.equal(view.autoGrainOf("2020-02-29", "2021-02-28"), "week");
  assert.equal(view.autoGrainOf(null, "2021-02-28"), null);
});

test("a drag on the overview moves an edge of its frame, or draws a new period", () => {
  // The edge under the pointer, within 8 pixels; the nearer one where both
  // are, and the later one at the middle.
  assert.equal(view.overviewGrip(103, 100, 400), "from");
  assert.equal(view.overviewGrip(392, 100, 400), "to");
  assert.equal(view.overviewGrip(109, 100, 400), null);
  assert.equal(view.overviewGrip(250, 100, 400), null);
  assert.equal(view.overviewGrip(104, 100, 110), "from");
  assert.equal(view.overviewGrip(106, 100, 110), "to");
  assert.equal(view.overviewGrip(105, 100, 110), "to");
  // A frame of all the time: its edges are the ends of the overview.
  assert.equal(view.overviewGrip(0, 0, 900), "from");
  assert.equal(view.overviewGrip(900, 0, 900), "to");
  // A new period follows the pointer from where the drag started, either
  // way, shorter than a week too while it moves (draggedRange decides).
  const frame = { from: 1000, to: 2000 };
  assert.deepEqual(view.brushedRange({ grip: null, start: 1500, range: frame }, 1200, 0, 5000), { from: 1200, to: 1500 });
  assert.deepEqual(view.brushedRange({ grip: null, start: 1500, range: frame }, 1503, 0, 5000), { from: 1500, to: 1503 });
  // An edge moves as far as the pointer moved, from a press beside it too:
  // a press that does not move keeps the period.
  assert.deepEqual(view.brushedRange({ grip: "from", start: 1003, range: frame }, 1003, 0, 5000), { from: 1000, to: 2000 });
  assert.deepEqual(view.brushedRange({ grip: "from", start: 1003, range: frame }, 903, 0, 5000), { from: 900, to: 2000 });
  assert.deepEqual(view.brushedRange({ grip: "to", start: 1995, range: frame }, 1995, 0, 5000), { from: 1000, to: 2000 });
  assert.deepEqual(view.brushedRange({ grip: "to", start: 1995, range: frame }, 2095, 0, 5000), { from: 1000, to: 2100 });
  // An edge moves alone, and stops a week before the other.
  assert.deepEqual(view.brushedRange({ grip: "from", start: 1000, range: frame }, 800, 0, 5000), { from: 800, to: 2000 });
  assert.deepEqual(view.brushedRange({ grip: "from", start: 1000, range: frame }, 1999, 0, 5000), { from: 1993, to: 2000 });
  assert.deepEqual(view.brushedRange({ grip: "to", start: 2000, range: frame }, 2600, 0, 5000), { from: 1000, to: 2600 });
  assert.deepEqual(view.brushedRange({ grip: "to", start: 2000, range: frame }, 900, 0, 5000), { from: 1000, to: 1007 });
  // Within the days of the overview.
  assert.deepEqual(view.brushedRange({ grip: "to", start: 4998, range: { from: 4995, to: 4998 } }, 4990, 0, 5000), { from: 4995, to: 5000 });
  assert.deepEqual(view.brushedRange({ grip: "from", start: 2, range: { from: 2, to: 5 } }, 10, 0, 5000), { from: 0, to: 5 });
});

// A panel of one line, as the server answers it.
function panelOf(values, counts, summary, extra = {}) {
  return {
    item: "dist",
    kind: "sum",
    lines: [{ series: null, values, counts, summary }],
    left_out: {},
    periods_with_value: values.filter((value) => value !== null).length,
    ...extra,
  };
}

const MONTHS = [
  { start: "2026-07-15", end: "2026-07-31", partial: true },
  { start: "2026-08-01", end: "2026-08-31", partial: false },
  { start: "2026-09-01", end: "2026-09-30", partial: false },
  { start: "2026-10-01", end: "2026-10-21", partial: true },
];

test("the second line of a panel counts its periods and names its lowest, highest, and latest", () => {
  const panel = panelOf([12000, 0, 180200, 108100], [1, 0, 18, 11], {
    periods_with_records: 3,
    periods_without_records: 1,
    periods_with_value: 4,
    lowest: { value: 12000, period: 0 },
    highest: { value: 180200, period: 2 },
    latest: { value: 108100, period: 3 },
  });
  const parts = view.summaryMessages(item("dist"), panel, MONTHS, "month", "ja");
  assert.deepEqual(parts.map((part) => words(part, "ja")), [
    "記録のある月 3",
    "記録の無い月 1",
    "最小 12.0 km（2026年7月（途中））",
    "最大 180.2 km（2026年9月）",
    "最後 108.1 km（2026年10月（途中））",
  ]);
  assert.deepEqual(parts.map((part) => part.strong), [["n"], ["n"], ["value"], ["value"], ["value"]]);
  assert.equal(words(parts[0], "en"), "Months with records: 3");
  // No record in the period, but periods of 0.
  const zero = panelOf([0, 0], [0, 0], { periods_with_records: 0, periods_without_records: 2, periods_with_value: 2, lowest: null, highest: null, latest: null });
  assert.deepEqual(view.summaryMessages(item("dist"), zero, MONTHS, "month", "ja").map((part) => words(part, "ja")), [
    "この期間には値がありません。",
    "記録の無い月 2",
  ]);
  // The lowest, the highest, and the latest over all the lines.
  const two = {
    lines: [
      { values: [50, null], counts: [1, 0], summary: { periods_with_value: 1, lowest: { value: 50, period: 0 }, highest: { value: 50, period: 0 }, latest: { value: 50, period: 0 } } },
      { values: [null, 47], counts: [0, 2], summary: { periods_with_value: 1, lowest: { value: 47, period: 1 }, highest: { value: 47, period: 1 }, latest: { value: 47, period: 1 } } },
    ],
    periods_with_value: 2,
  };
  const summary = view.panelSummary(item("vo2"), two);
  assert.deepEqual([summary.withValue, summary.lowest.value, summary.highest.value, summary.latest.value], [2, 47, 50, 47]);
});

test("the lines of VO2 Max: the series by color and name, the sports by dash", () => {
  const line = (source, sport, first, last) => ({
    series: { vo2max_source_series: source, sport },
    values: [1],
    counts: [1],
    first_day: first,
    last_day: last,
  });
  const panel = {
    lines: [
      line("activity_vo2max_daily", "RUNNING", "2011-04-01", "2022-01-09"),
      line("performance_metrics_daily", "CYCLING", "2022-01-12", "2026-10-18"),
      line("performance_metrics_daily", "RUNNING", "2022-01-12", "2026-10-18"),
    ],
  };
  assert.deepEqual(view.lineStyles(panel), [
    { color: 1, dash: null },
    { color: 2, dash: "6 4" },
    { color: 2, dash: null },
  ]);
  assert.deepEqual(view.lineNames(panel, "ja").map((name) => words(name, "ja")), [
    "〜2022年1月9日・ランニング",
    "2022年1月12日〜・自転車",
    "2022年1月12日〜・ランニング",
  ]);
  assert.equal(words(view.lineNames(panel, "en")[0], "en"), "Until January 9, 2022 (Running)");
  // One series of one sport has no name; one line has none.
  const single = { lines: [line("performance_metrics_daily", "RUNNING", "2022-01-12", "2026-10-18"), line("performance_metrics_daily", "", "2022-01-12", "2026-10-18")] };
  assert.deepEqual(view.lineNames(single, "en").map((name) => words(name, "en")), ["Running", "No sport"]);
  assert.deepEqual(view.lineNames({ lines: [{ series: null }] }, "en"), [null]);
  assert.deepEqual(view.lineStyles({ lines: [{ series: null }] }), [{ color: 1, dash: null }]);
  // The colors and the dashes follow the series and the sports by their
  // names: a period with the series of MaxMet only keeps its orange.
  assert.deepEqual(view.lineStyles(single), [
    { color: 2, dash: null },
    { color: 2, dash: "2 3" },
  ]);
  assert.deepEqual(view.lineStyles({ lines: [line("activity_vo2max_daily", "PADDLING", "2011-04-01", "2022-01-09")] }), [{ color: 1, dash: "8 3 2 3" }]);
});

test("the readings at the top right: the period, and each value with its count", () => {
  const panel = panelOf([12000, null, 180200, 108100], [1, 0, 18, 11], null);
  const reading = view.readout(item("dist"), panel, MONTHS, 3, "month", "ja");
  assert.equal(words(reading.period, "ja"), "2026年10月（途中）");
  assert.deepEqual(reading.values.map((value) => [value.line, words(value.value, "ja"), words(value.count, "ja")]), [[0, "108.1 km", "11 回"]]);
  assert.deepEqual(view.readout(item("dist"), panel, MONTHS, 1, "month", "ja").values, []);
  assert.equal(view.readout(item("dist"), panel, MONTHS, 9, "month", "ja"), null);
});

test("the notes of a panel say what is left out and what the values are", () => {
  const keys = (key, left, grain = "month", extra = {}) =>
    view.panelNotes(item(key), { ...panelOf([1, 0], [1, 0], { periods_with_records: 1, periods_without_records: 1 }), left_out: left, ...extra }, MONTHS.slice(1, 3), grain, "ja").map((note) => [note.key, note.help ?? null]);
  assert.deepEqual(keys("dist", { disagree: 2, no_value: 3, after_today: 1, no_date: 4 }), [
    ["view.note.zero", "zero"],
    ["view.note.activity_disagree", null],
    ["view.note.activity_missing", null],
    ["view.note.after_today", null],
    ["view.note.no_date", null],
  ]);
  assert.deepEqual(keys("asc", { no_value: 3 }).map(([key]) => key), ["view.note.zero", "view.note.fit_missing"]);
  // Only a total has periods of 0.
  assert.deepEqual(keys("hr", { no_duration: 2 }).map(([key]) => key), ["view.note.no_duration", "view.note.calculated"]);
  assert.deepEqual(keys("pace", {}).map(([key, help]) => [key, help]), [
    ["view.note.calculated", "calculated"],
    ["view.note.faster_lower", null],
  ]);
  assert.deepEqual(keys("sleep", { sleep_review_days: 2, sleep_other_days: 1, disagree: 1 }).map(([key]) => key), ["view.note.day_disagree", "view.note.sleep_unused"]);
  assert.deepEqual(keys("hrv", {}).map(([key]) => key), ["view.note.hrv_reference"]);
  assert.deepEqual(keys("vo2", { days_with_several_records: 3 }, "day").map(([key, help]) => [key, help]), [["view.note.several_points", "records"]]);
  assert.deepEqual(keys("p5k", { days_with_several_records: 3, disagree: 1 }).map(([key]) => key), [
    "view.note.record_disagree",
    "view.note.faster_lower",
    "view.note.several_mean",
    "view.note.prediction",
  ]);
  const sleep = view.panelNotes(item("sleep"), { ...panelOf([1], [1], null), left_out: { sleep_review_days: 2, sleep_other_days: 1 } }, MONTHS, "month", "ja");
  assert.equal(words(sleep[0], "ja"), "使わなかった日 3（確かめが要る睡眠 2・除いた睡眠 1）。");
  assert.equal(words(sleep[1], "ja"), translate(catalogs, "ja", "view.note.partial"));
  // The two series of VO2 Max, by the days of their lines.
  const vo2 = {
    lines: [
      { series: { vo2max_source_series: "activity_vo2max_daily", sport: "RUNNING" }, values: [1], counts: [1], first_day: "2011-04-01", last_day: "2022-01-09" },
      { series: { vo2max_source_series: "performance_metrics_daily", sport: "RUNNING" }, values: [1], counts: [1], first_day: "2022-01-12", last_day: "2026-10-18" },
    ],
    left_out: {},
    periods_with_value: 1,
  };
  const notes = view.panelNotes(item("vo2"), vo2, MONTHS.slice(1, 2), "month", "ja");
  assert.equal(words(notes[0], "ja"), "2 つの系列は混ぜません。2022年1月9日 までは活動の記録から、2022年1月12日 からは MaxMet の記録からの値で、値の幅の違いはこのアプリでは説明しません。");
});

test("a table has every period, newest first, with each line's value and count", () => {
  const panel = panelOf([12000, null, 180200, 108100], [1, 0, 18, 11], null);
  const rows = view.tableRows(item("dist"), panel, MONTHS, "month", "ja");
  assert.deepEqual(rows.map((row) => [words(row.period, "ja"), row.cells.map((cell) => [cell.value === null ? null : words(cell.value, "ja"), cell.count])]), [
    ["2026年10月（途中）", [["108.1 km", "11"]]],
    ["2026年9月", [["180.2 km", "18"]]],
    ["2026年8月", [[null, "0"]]],
    ["2026年7月（途中）", [["12.0 km", "1"]]],
  ]);
  assert.deepEqual(view.tableHeads(item("dist"), panel, "month", "ja").map((head) => words(head, "ja")), ["月（新しい順）", "値", "回数"]);
});

test("before an output is open, the page offers the latest one, with the items remembered", () => {
  const run = { path: "/x/run", name: "run" };
  const earlier = [{ index: 0, name: "older", path: "/x/older" }];
  assert.deepEqual(view.startChoice({ runOutput: run, earlier, remembered: true }), { kind: "remembered", latest: run });
  assert.deepEqual(view.startChoice({ runOutput: null, earlier, remembered: false }), { kind: "latest", latest: earlier[0] });
  assert.deepEqual(view.startChoice({ runOutput: null, earlier: [], remembered: true }), { kind: "first", latest: null });
  // The line of what to do next.
  const bar = (state) => {
    const shown = view.viewBar(state);
    return [shown.kind, words(shown.label, "ja"), words(shown.text, "ja")];
  };
  assert.deepEqual(bar({ choice: { kind: "first" } }), ["current", "次にすること：", "見る出力を選んでください。正規化した出力のフォルダーです。"]);
  assert.deepEqual(bar({ choice: { kind: "latest" } }), ["current", "次にすること：", "最近の出力を開くか、ほかの出力を選んでください。"]);
  assert.deepEqual(bar({ opening: "garmin-run-all-20261021-0930" }), ["current", "開いています：", "garmin-run-all-20261021-0930"]);
  assert.deepEqual(bar({ view: { name: "out", version: "2.1.0" } }), ["done", "見ている出力：", "out（バージョン 2.1.0）"]);
  assert.equal(bar({ stop: { code: "SERIES_OUTPUT_OTHER_VERSION" } })[0], "error");
  assert.equal(bar({ stop: { code: "OUTPUT_OTHER_VERSION" } })[2], translate(catalogs, "ja", "view.bar.other_version"));
  assert.equal(bar({ stop: { code: "OUTPUT_CHANGED" } })[2], translate(catalogs, "ja", "view.bar.not_opened"));
  assert.equal(bar({ stopped: true, view: { name: "out", version: "2.1.0" } })[0], "none");
});

test("a stop says what happened, what to do, and its code; another version offers to normalize again", () => {
  const box = (code, detail = null) => {
    const shown = view.stopBox(code, detail, "2.1.0");
    return [words(shown.heading, "ja"), shown.lines.map((line) => words(line, "ja")), words(shown.code, "ja"), shown.normalize];
  };
  const [heading, lines, code, normalize] = box("OUTPUT_OTHER_VERSION", { version: "2.0.1" });
  assert.equal(heading, "この出力は、このバージョンでは見られません");
  assert.match(lines[0], /^バージョン 2\.0\.1 で作った出力です。.*このバージョン（2\.1\.0）が作った出力だけを見ます。$/);
  assert.equal(lines[1], "正規化のページの「既存のスナップショットだけで正規化し直す」で、正規化し直してください。スナップショットを使わずに正規化した出力なら、もとのエクスポートをもう一度正規化します。");
  assert.equal(code, "問い合わせ用のコード：OUTPUT_OTHER_VERSION（2.0.1）");
  assert.equal(normalize, true);
  // An output of 1.3 says the same, with its own code.
  const legacy = box("SERIES_OUTPUT_OTHER_VERSION", { version: "1.3.3" });
  assert.deepEqual(legacy[1], box("OUTPUT_OTHER_VERSION", { version: "1.3.3" })[1]);
  assert.equal(legacy[2], "問い合わせ用のコード：SERIES_OUTPUT_OTHER_VERSION（1.3.3）");
  assert.match(box("OUTPUT_OTHER_VERSION")[1][0], /^このアプリの別のバージョンで作った出力です。/);
  // The three stops in the words of the view page.
  assert.deepEqual(box("OUTPUT_CHANGED").slice(0, 3), [
    "出力を開けませんでした",
    ["出力が、確かめたあとに変わったか、壊れています。", "次にすること：少し待ってから、出力を選び直してください。続くときは、新しいフォルダーにもう一度正規化してください。"],
    "問い合わせ用のコード：OUTPUT_CHANGED",
  ]);
  assert.equal(box("OUTPUT_NOT_AVAILABLE")[1][0], "出力のフォルダーか、読むファイルが見つかりません。または、大きすぎて読めません。");
  assert.equal(box("HANDOFF_INVALID")[1][0], "出力が確かめに通りませんでした。正規化の出力でないか、変わったか、壊れています。");
  // The others in the words of the normalization page, without its own code
  // line; an error without a code says that something went wrong.
  assert.deepEqual(box("VIEW_ANSWER_TOO_LARGE")[1], [translate(catalogs, "ja", "stop.view_answer_too_large"), "次にすること：期間を短くするか、まとめ方を週か月にしてください。"]);
  const unknown = box(null);
  assert.equal(unknown[1][0], translate(catalogs, "ja", "error.unknown"));
  assert.equal(unknown[2], "");
  assert.equal(unknown[3], false);
});

test("the items are listed in the words of the language", () => {
  const name = (key) => translate(catalogs, "ja", `view.item.${key}`);
  assert.equal(words(view.itemListMessage(view.FIRST_KEYS, name, "ja"), "ja"), "距離、安静時心拍数、VO2 Max");
  const english = (key) => translate(catalogs, "en", `view.item.${key}`);
  assert.equal(words(view.itemListMessage(view.FIRST_KEYS, english, "en"), "en"), "Distance, Resting heart rate, and VO2 Max");
});
