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
  // A clock below 0 keeps its sign (Codex's review of the diff of M3); one
  // that rounds to 0 has none.
  assert.equal(view.clockSeconds(-60), "-1:00");
  assert.equal(view.clockSeconds(-3723), "-1:02:03");
  assert.equal(view.clockSeconds(-0.4), "0:00");
  assert.equal(view.clockMinutes(-65), "-1:05");
  assert.equal(view.clockMinutes(-0.3), "0:00");
  assert.equal(view.clockMinutes(59.6), "1:00");
  assert.equal(words(view.valueMessage("time", -3900, "ja"), "ja"), "-1:05");
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
  // The layouts, the period, the grouping, the activity types, and the
  // timezone are gone too (stage K2 of v2.2.0).
  const later = {
    ...settings,
    view_layouts: [{ id: "mine-1", name: "Made up", items: ["dist"] }],
    view_layouts_hidden: ["race"],
    view_layout: "mine-1",
    view_period: { from: "2024-01-01", to: "2024-12-31" },
    view_grain: "week",
    view_types: ["running"],
    timezone: "Asia/Tokyo",
    // And how one item is compared by year (stage L1).
    view_compare_mode: "overlay",
    view_compare_month: 5,
    // And what it is compared by, and the weeks before a race (stage M2).
    view_compare_by: "race",
    view_compare_weeks: 12,
    // And the marks, whether they show, and what to tell of their file
    // (stage M1).
    view_marks: [{ id: "m-0000000a", kind: "race", name: "Made up", day: "2030-04-14", end: null }],
    view_marks_shown: false,
    marks_notice: "MARKS_NOT_WRITTEN",
  };
  assert.deepEqual(view.settingsAfterForget(later), { launch: "later", store: "/x", present: false });
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

// --- Layouts (stage K2 of v2.2.0) -------------------------------------------

const BUILT_INS = [
  { id: "run", items: ["dist", "pace", "hr"] },
  { id: "sleep_hr", items: ["sleep", "sscore", "hrv", "rhr"] },
  { id: "volume", items: ["dist", "time", "count", "asc"] },
  { id: "form", items: ["cad", "sl", "vo", "gct"] },
  { id: "load", items: ["load", "acute", "chronic", "acwr"] },
  { id: "estimates", items: ["vo2", "phalf", "pfull", "endu"] },
];
const MINE = [
  { id: "u-00000001", name: "朝ラン", items: ["dist", "hr"] },
  { id: "u-00000002", name: "週末", items: ["time", "pace"] },
];

test("the cards of the layouts: the built-in ones not hidden in their order, then the person's", () => {
  const cards = view.layoutCards({ builtIns: BUILT_INS, mine: MINE, hidden: ["load", "run"], current: "u-00000002", items: ["time", "pace"], coverage: null });
  assert.deepEqual(cards.map((card) => card.id), ["sleep_hr", "volume", "form", "estimates", "u-00000001", "u-00000002"]);
  assert.deepEqual(cards.map((card) => card.builtIn), [true, true, true, true, false, false]);
  assert.equal(cards[0].nameKey, "view.layout.sleep_hr");
  assert.equal(cards[4].name, "朝ラン");
  assert.deepEqual(cards.map((card) => card.current), [false, false, false, false, false, true]);
  // An id that the page has no name for is left out; the person's names are text.
  const odd = view.layoutCards({ builtIns: [{ id: "wellness", items: ["sleep"] }, ...BUILT_INS], mine: [{ id: "u-00000003", name: "<b>x</b>", items: ["dist"] }], hidden: [], current: null, items: [], coverage: null });
  assert.equal(odd[0].id, "run");
  assert.equal(odd.at(-1).name, "<b>x</b>");
});

test("a card is changed when the items shown are others or in another order, also when the page opens again", () => {
  assert.equal(view.layoutChanged(["dist", "pace", "hr"], ["dist", "pace", "hr"]), false);
  assert.equal(view.layoutChanged(["dist", "pace", "hr"], ["dist", "hr", "pace"]), true);
  assert.equal(view.layoutChanged(["dist", "pace", "hr"], ["dist", "pace"]), true);
  assert.equal(view.layoutChanged(["dist"], ["dist", "rhr"]), true);
  // The items remembered at the next opening count as those shown.
  const cards = view.layoutCards({ builtIns: BUILT_INS, mine: [], hidden: [], current: "run", items: ["dist", "pace"], coverage: null });
  assert.deepEqual(cards.filter((card) => card.changed).map((card) => card.id), ["run"]);
  for (const language of ["en", "ja"]) {
    assert.match(words(view.layoutNotes(cards[0])[0], language), language === "ja" ? /変えた/ : /changed/i);
  }
});

test("a card counts its items with a value in the output only when some have none", () => {
  const coverage = { vo2: { months: ["2024-01"] }, phalf: { months: ["2024-02"] }, pfull: { months: ["2024-02"] }, endu: { months: [] }, dist: { months: ["2024-01"] }, pace: { months: ["2024-01"] }, hr: { months: ["2024-01"] } };
  const cards = view.layoutCards({ builtIns: BUILT_INS, mine: [], hidden: [], current: null, items: [], coverage });
  const estimates = cards.find((card) => card.id === "estimates");
  assert.deepEqual([estimates.valued, estimates.total], [3, 4]);
  assert.equal(words(view.layoutNotes(estimates)[0], "ja"), "値のある項目 3/4");
  assert.equal(words(view.layoutNotes(estimates)[0], "en"), "Items with values 3/4");
  // All with a value: nothing is said; an item missing in the bars counts as none.
  assert.equal(cards.find((card) => card.id === "run").valued, null);
  assert.equal(cards.find((card) => card.id === "form").valued, 0);
  assert.deepEqual(view.layoutNotes(cards.find((card) => card.id === "run")), []);
});

test("a remembered period opens as it was, a range of days only when it meets the output", () => {
  for (const choice of ["all", "10y", "5y", "3y", "1y"]) {
    assert.deepEqual(view.periodToOpen(choice, "2011-04-01", "2026-10-21"), { choice, range: null });
  }
  for (const odd of ["custom", "2y", null, 7, { from: "2024-01-01" }, { from: "2024-02-01", to: "2024-01-01" }, { from: "20240101", to: "20241231" }]) {
    assert.equal(view.periodToOpen(odd, "2011-04-01", "2026-10-21"), null);
  }
  // A range that meets the output in part is sent as it is: the server cuts it.
  assert.deepEqual(view.periodToOpen({ from: "2010-01-01", to: "2011-12-31" }, "2011-04-01", "2026-10-21"), { choice: "custom", range: { from: "2010-01-01", to: "2011-12-31" } });
  assert.deepEqual(view.periodToOpen({ from: "2024-02-29", to: "2024-02-29" }, "2024-02-29", "2026-10-21"), { choice: "custom", range: { from: "2024-02-29", to: "2024-02-29" } });
  // A range that does not meet it at all: all the output.
  assert.deepEqual(view.periodToOpen({ from: "2008-01-01", to: "2011-03-31" }, "2011-04-01", "2026-10-21"), { choice: "all", range: null });
  assert.deepEqual(view.periodToOpen({ from: "2024-03-01", to: "2024-03-31" }, "2020-01-01", "2024-02-29"), { choice: "all", range: null });
});

test("remembered activity types keep those of the output; none counted stays none, no name there is the first ones", () => {
  const types = [{ name: "running", running: true }, { name: "trail_running", running: true }, { name: "road_biking", running: false }];
  assert.deepEqual(view.typesToOpen(["road_biking", "running", "swimming"], types), ["running", "road_biking"]);
  assert.deepEqual(view.typesToOpen([], types), []);
  assert.equal(view.typesToOpen(["swimming"], types), null);
  assert.equal(view.typesToOpen(null, types), null);
  assert.equal(view.typesToOpen(undefined, types), null);
  assert.equal(view.grainToOpen("week"), "week");
  assert.equal(view.grainToOpen("hour"), "auto");
});

test("the remembered view is written once the person stops changing it, and at once when the app quits", async () => {
  const sent = [];
  const timers = [];
  const clock = {
    setTimer: (fire, wait) => { timers.push({ fire, wait, live: true }); return timers.length - 1; },
    clearTimer: (id) => { timers[id].live = false; },
  };
  const sender = view.laterSender((value) => { sent.push(value); }, 800, clock);
  sender.push({ grain: "week" });
  sender.push({ grain: "month" });
  sender.push({ grain: "year" });
  assert.equal(timers.filter((timer) => timer.live).length, 1);
  assert.equal(timers.at(-1).wait, 800);
  assert.deepEqual(sent, []);
  // The time passes: the timer runs out once.
  timers.at(-1).live = false;
  await timers.at(-1).fire();
  assert.deepEqual(sent, [{ grain: "year" }]);
  // Changed and quit at once: what waits is written before the app stops.
  sender.push({ layout: "run" });
  assert.equal(sender.waiting(), true);
  await sender.flush();
  assert.deepEqual(sent, [{ grain: "year" }, { layout: "run" }]);
  assert.equal(timers.filter((timer) => timer.live).length, 0);
  // Nothing waits: a flush sends nothing.
  await sender.flush();
  assert.equal(sent.length, 2);
  // The page hides: what waits is taken to be sent apart, and not sent here.
  sender.push({ period: "1y" });
  assert.deepEqual(sender.take(), { period: "1y" });
  assert.equal(sender.waiting(), false);
  assert.equal(sender.take(), null);
  assert.equal(timers.filter((timer) => timer.live).length, 0);
  assert.equal(sent.length, 2);
});

test("a dragged layout goes after each other one whose middle is above the pointer", () => {
  // Three other rows, 40 pixels high, from 100.
  const middles = [120, 160, 200];
  assert.equal(view.dropPlace(middles, 90), 0);
  assert.equal(view.dropPlace(middles, 119), 0);
  assert.equal(view.dropPlace(middles, 121), 1);
  assert.equal(view.dropPlace(middles, 199), 2);
  assert.equal(view.dropPlace(middles, 260), 3);
  // At a middle, it stays before that row.
  assert.equal(view.dropPlace(middles, 160), 1);
  assert.equal(view.dropPlace([], 50), 0);
});

// --- Comparing one item by year (stage L1 of v2.2.0) ----------------------

test("the years of an output are offered newest first, four at first and six at most", () => {
  const years = view.compareYears("2019-04-01", "2026-10-21");
  assert.deepEqual(years.map((entry) => entry.year), [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019]);
  assert.deepEqual(years[0], { year: 2026, start: "2026-01-01", end: "2026-10-21" });
  assert.deepEqual(years.at(-1), { year: 2019, start: "2019-04-01", end: "2019-12-31" });
  assert.deepEqual(view.firstCompareYears(years), [2026, 2025, 2024, 2023]);
  assert.deepEqual(view.compareYears("2026-01-05", "2026-02-01").map((entry) => entry.year), [2026]);
  for (const [first, last] of [[null, "2026-01-01"], ["2026-02-01", "2026-01-01"], ["2026-1-1", "2026-02-01"]]) {
    assert.deepEqual(view.compareYears(first, last), []);
  }
  // A year added keeps the newest first; six at most, and one at least.
  assert.deepEqual(view.toggledYears([2026, 2024], 2025), [2026, 2025, 2024]);
  assert.deepEqual(view.toggledYears([2026, 2025, 2024, 2023, 2022, 2021], 2020), [2026, 2025, 2024, 2023, 2022, 2021]);
  assert.deepEqual(view.toggledYears([2026, 2025], 2025), [2026]);
  assert.deepEqual(view.toggledYears([2026], 2026), [2026]);
});

test("a year asks for its days, or those of one month, and its value as one period", () => {
  assert.deepEqual(view.compareRange(2024, null), { from: "2024-01-01", to: "2024-12-31" });
  assert.deepEqual(view.compareRange(2024, 2), { from: "2024-02-01", to: "2024-02-29" });
  assert.deepEqual(view.compareRange(2025, 2), { from: "2025-02-01", to: "2025-02-28" });
  assert.deepEqual(view.compareRange(2025, 12), { from: "2025-12-01", to: "2025-12-31" });
  // The value of the year or of the month comes from a grouping of the
  // server, never from a new way to count (the review of the plan by Codex).
  assert.equal(view.compareValueGrain(null), "year");
  assert.equal(view.compareValueGrain(5), "month");
  assert.deepEqual(view.compareGrains(null), ["day", "week", "month"]);
  assert.deepEqual(view.compareGrains(5), ["day", "week"]);
  assert.equal(view.firstCompareGrain("rows", null), "month");
  assert.equal(view.firstCompareGrain("overlay", 5), "day");
  assert.equal(view.firstCompareGrain("cumulative", null), "day");
});

test("the periods of each year have their places on one axis, with their own days", () => {
  // Weeks from Monday, counted from the week of 1 January.
  const weeks = [
    { start: "2024-01-01", end: "2024-01-07", partial: false },
    { start: "2024-01-08", end: "2024-01-14", partial: false },
    { start: "2024-12-30", end: "2024-12-31", partial: true },
  ];
  assert.deepEqual(view.compareSlots(weeks, "week", 2024, null).map((slot) => [slot.start, slot.partial, slot.from]), [
    [0, false, "2024-01-01"],
    [1, false, "2024-01-08"],
    [52, true, "2024-12-30"],
  ]);
  // A year whose 1 January is a Sunday has 54 weeks: 2012 and 2040.
  assert.equal(view.compareSpan("week", null, [2012]), 53);
  assert.equal(view.compareSpan("week", null, [2040]), 53);
  assert.equal(view.compareSpan("week", null, [2023, 2025]), 52);
  // Days by their month and day, on a leap year: 1 March has one place.
  const march = (year) => view.compareSlots([{ start: `${year}-03-01`, end: `${year}-03-01` }], "day", year, null)[0].start;
  assert.equal(march(2024), march(2025));
  assert.equal(view.compareSlots([{ start: "2024-02-29", end: "2024-02-29" }], "day", 2024, null)[0].start, 59);
  assert.equal(march(2025), 60);
  assert.equal(view.compareSpan("day", null, [2025]), 365);
  // Months by their numbers; in one month, days by their days.
  assert.equal(view.compareSlots([{ start: "2025-07-01", end: "2025-07-31" }], "month", 2025, null)[0].start, 6);
  assert.equal(view.compareSlots([{ start: "2025-05-17", end: "2025-05-17" }], "day", 2025, 5)[0].start, 16);
  assert.equal(view.compareSpan("day", 5, [2025]), 30);
  assert.equal(view.compareSpan("month", null, [2025]), 11);
  // A short month has its own days only, never those of the next month: 29
  // February where a leap year is chosen.
  assert.equal(view.compareSpan("day", 2, [2025, 2023]), 27);
  assert.equal(view.compareSpan("day", 2, [2025, 2024]), 28);
  assert.equal(view.compareSpan("day", 4, [2025]), 29);
  assert.equal(view.compareSpan("day", 2, []), 28);
});

test("a running total goes on after a period without a value, and ends at the value of the year", () => {
  assert.deepEqual(view.runningTotal([null, 5, 0, 3]), [null, 5, 5, 8]);
  // A period without a value breaks the line, and the total goes on from what
  // it was (the checker's L1-2); nothing after the last value.
  assert.deepEqual(view.runningTotal([80, null, 60, null]), [80, null, 140, null]);
  assert.deepEqual(view.runningTotal([]), []);
  assert.deepEqual(view.runningTotal(null), []);
  // The end of the running total is the value of the year that the server
  // gives, within the error of the fractions.
  const days = [1.1, 2.2, null, 3.3, 0, 4.4];
  const end = view.runningTotal(days).filter(Number.isFinite).at(-1);
  assert.ok(Math.abs(end - 11.0) < 1e-9);
  // Only a total can be a running total; another item compares in rows.
  assert.equal(view.compareModeFor({ kind: "sum" }, "cumulative"), "cumulative");
  assert.equal(view.compareModeFor({ kind: "count" }, "cumulative"), "cumulative");
  assert.equal(view.compareModeFor({ kind: "day" }, "cumulative"), "rows");
  assert.equal(view.compareModeFor({ kind: "pace" }, "overlay"), "overlay");
  assert.equal(view.compareModeFor({ kind: "sum" }, "bars"), "rows");
});

test("the years have the steps of one color, the newest the darkest", () => {
  assert.deepEqual([...view.yearSteps([2023, 2026, 2024])], [[2026, 6], [2024, 5], [2023, 4]]);
  assert.equal(view.yearSteps([2026, 2025, 2024, 2023, 2022, 2021]).get(2021), 1);
});

test("a year is cut where its answer starts after the range or ends before it", () => {
  const range = view.compareRange(2026, null);
  assert.deepEqual(view.compareCut(range, { start: "2026-01-01", end: "2026-10-21" }), { from: null, to: "2026-10-21" });
  assert.deepEqual(view.compareCut(view.compareRange(2019, null), { start: "2019-04-01", end: "2019-12-31" }), { from: "2019-04-01", to: null });
  assert.deepEqual(view.compareCut(range, { start: "2026-01-01", end: "2026-12-31" }), { from: null, to: null });
  assert.deepEqual(view.compareCut(range, { start: null, end: null }), { from: null, to: null });
});

test("an item of several series compares one of them, that of the newest source at first", () => {
  const line = (source, sport) => ({ series: { vo2max_source_series: source, sport }, values: [] });
  const panel = { lines: [line("activity", "RUNNING"), line("activity", "CYCLING"), line("performance_metrics_daily", "CYCLING"), line("performance_metrics_daily", "RUNNING")] };
  assert.equal(view.compareSeries(panel).length, 4);
  assert.equal(view.firstCompareSeries(panel), view.seriesKey(line("performance_metrics_daily", "RUNNING")));
  // A year without that series has no line of it; another series is never used.
  const year = { lines: [line("activity", "RUNNING")] };
  assert.equal(view.compareLine(year, view.firstCompareSeries(panel)), null);
  assert.equal(view.compareLine(year, view.seriesKey(line("activity", "RUNNING"))), year.lines[0]);
  // An item of one line has nothing to choose.
  const one = { lines: [{ series: null, values: [1] }] };
  assert.deepEqual(view.compareSeries(one), []);
  assert.equal(view.firstCompareSeries(one), null);
  assert.equal(view.compareLine(one, null), one.lines[0]);
});

test("the value of a year is named as the labels of the panels name it", () => {
  assert.deepEqual(view.compareValueMessage({ kind: "sum" }, null, "ja"), { key: "view.compare.value.sum", params: {}, keyParams: { period: { key: "view.compare.whole_year", params: {}, keyParams: {} } } });
  const may = view.compareValueMessage({ kind: "day" }, 5, "ja");
  assert.equal(may.key, "view.compare.value.day");
  assert.deepEqual(may.keyParams.period, { text: "5月" });
  assert.equal(view.compareValueMessage({ kind: "obs" }, 5, "en").keyParams.period.text, "May");
});

test("the way and the month of a comparison come back from the settings when they are of their forms", () => {
  assert.deepEqual(view.compareToOpen({ view_compare_mode: "cumulative", view_compare_month: 5 }), { mode: "cumulative", month: 5 });
  assert.deepEqual(view.compareToOpen({}), { mode: "rows", month: null });
  assert.deepEqual(view.compareToOpen(null), { mode: "rows", month: null });
  for (const [mode, month] of [["bars", 0], [3, 13], [null, true], ["overlay", 5.5], ["rows", "5"]]) {
    const back = view.compareToOpen({ view_compare_mode: mode, view_compare_month: month });
    assert.equal(back.mode, mode === "overlay" ? "overlay" : "rows");
    assert.equal(back.month, null);
  }
});

// The answers of a comparison, as the server gives them: the whole output by
// year (or by month), and one answer for each year.
const answerOf = (periods, lines) => ({
  start: periods[0]?.start ?? null,
  end: periods.at(-1)?.end ?? null,
  periods,
  panels: [{ item: "dist", kind: "sum", lines }],
});
const lineOf = (values, counts = values.map((value) => (value ? 1 : 0)), extra = {}) => ({ series: null, values, counts, ...extra });

test("the value of a year, or of a month, is its period in the answer of the whole output", () => {
  const whole = answerOf(
    [
      { start: "2025-04-01", end: "2025-12-31", partial: true },
      { start: "2026-01-01", end: "2026-10-21", partial: true },
    ],
    [lineOf([1200.5, 980.25], [120, 98])],
  );
  assert.deepEqual(view.compareValue(whole, 2026, null, null), { value: 980.25, count: 98, partial: true });
  assert.equal(view.compareValue(whole, 2024, null, null), null);
  const months = answerOf(
    [
      { start: "2025-05-01", end: "2025-05-31", partial: false },
      { start: "2026-05-01", end: "2026-05-31", partial: false },
    ],
    [lineOf([180, null], [18, 0])],
  );
  assert.deepEqual(view.compareValue(months, 2025, 5, null), { value: 180, count: 18, partial: false });
  assert.deepEqual(view.compareValue(months, 2026, 5, null), { value: null, count: 0, partial: false });
  assert.equal(view.compareValue(months, 2025, 6, null), null);
  assert.equal(view.compareValue(null, 2025, 5, null), null);
});

test("the years compared are drawn newest first, with their places, totals, and cuts", () => {
  const year = (periods, values, extra) => answerOf(periods, [lineOf(values, undefined, extra)]);
  const answers = new Map([
    [2025, year([{ start: "2025-01-01", end: "2025-01-31", partial: false }, { start: "2025-02-01", end: "2025-02-28", partial: false }], [10, 5])],
    [2026, year([{ start: "2026-01-01", end: "2026-01-31", partial: false }, { start: "2026-02-01", end: "2026-02-10", partial: true }], [8, null])],
  ]);
  const whole = answerOf(
    [
      { start: "2025-01-01", end: "2025-12-31", partial: false },
      { start: "2026-01-01", end: "2026-02-10", partial: true },
    ],
    [lineOf([15, 8])],
  );
  const rows = view.compareData({ years: [2025, 2026], month: null, grain: "month", mode: "rows", series: null, answers, whole });
  assert.deepEqual(rows.map((entry) => [entry.year, entry.step]), [[2026, 6], [2025, 5]]);
  assert.deepEqual(rows[0].slots.map((slot) => [slot.start, slot.partial]), [[0, false], [1, true]]);
  assert.deepEqual(rows[0].values, [8, null]);
  assert.deepEqual(rows[0].cut, { from: null, to: "2026-02-10" });
  assert.deepEqual(rows[0].whole, { value: 8, count: 1, partial: true });
  assert.deepEqual(rows[1].cut, { from: null, to: "2025-02-28" });
  assert.equal(rows[0].outside, false);
  const running = view.compareData({ years: [2025, 2026], month: null, grain: "month", mode: "cumulative", series: null, answers, whole });
  assert.deepEqual(running[1].values, [10, 15]);
  assert.equal(running[1].values.at(-1), running[1].whole.value);
  // A month that the output does not have in a year: no period, no value.
  const empty = view.compareData({ years: [2026], month: 7, grain: "day", mode: "rows", series: null, answers: new Map([[2026, answerOf([], [])]]), whole: answerOf([], []) });
  assert.deepEqual([empty[0].outside, empty[0].values, empty[0].whole], [true, [], null]);
  // The points of the records of each day stay points, and a running total has none.
  const points = new Map([[2026, year([{ start: "2026-01-01", end: "2026-01-01", partial: false }], [50], { points: [[0, 50]] })]]);
  assert.deepEqual(view.compareData({ years: [2026], month: null, grain: "day", mode: "overlay", series: null, answers: points, whole })[0].points, [[0, 50]]);
  assert.equal(view.compareData({ years: [2026], month: null, grain: "day", mode: "cumulative", series: null, answers: points, whole })[0].points, null);
});

test("the places of the axis are named and marked as each language writes them", () => {
  assert.deepEqual(view.compareSlotName(0, "week", null, "ja"), { key: "view.compare.week_number", params: { n: 1 }, keyParams: {} });
  assert.deepEqual(view.compareSlotName(4, "month", null, "ja"), { text: "5月" });
  assert.deepEqual(view.compareSlotName(59, "day", null, "ja"), { text: "2月29日" });
  assert.deepEqual(view.compareSlotName(59, "day", null, "en"), { text: "February 29" });
  assert.deepEqual(view.compareSlotName(16, "day", 5, "ja"), { text: "5月17日" });
  // The first day of each month over a year; every seventh day over a month,
  // within its days.
  assert.deepEqual(view.compareTicks("month", null, 2026, "ja").map((tick) => tick.at), [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
  assert.deepEqual(view.compareTicks("day", null, 2026, "en").slice(1, 3), [{ at: 31, text: "Feb" }, { at: 60, text: "Mar" }]);
  // 1 January 2026 was a Thursday: three days into the week of its Monday.
  assert.ok(Math.abs(view.compareTicks("week", null, 2026, "ja")[0].at - 3 / 7) < 1e-9);
  assert.deepEqual(view.compareTicks("day", 2, 2026, "ja").map((tick) => [tick.at, tick.text]), [[0, "2/1"], [7, "2/8"], [14, "2/15"], [21, "2/22"]]);
  assert.equal(view.compareTicks("day", 2, 2024, "ja").length, 5);
});

test("a year cut by the output says until or from which day", () => {
  assert.deepEqual(view.compareNote({ from: null, to: "2026-10-21" }, "ja"), { key: "view.compare.until", params: { date: "10月21日" }, keyParams: {} });
  assert.deepEqual(view.compareNote({ from: null, to: "2026-10-21" }, "ja", true).params, { date: "10/21" });
  assert.deepEqual(view.compareNote({ from: "2019-04-01", to: null }, "en"), { key: "view.compare.since", params: { date: "April 1" }, keyParams: {} });
  assert.equal(view.compareNote({ from: "2026-04-01", to: "2026-10-21" }, "ja").key, "view.compare.between");
  assert.equal(view.compareNote({ from: null, to: null }, "ja"), null);
});

test("the readings and the table of a comparison say each year's own period, its value, and what it lacks", () => {
  const item = { key: "dist", kind: "sum", group: "act" };
  const answers = new Map([
    [2025, answerOf([{ start: "2025-01-01", end: "2025-01-05", partial: true }, { start: "2025-01-06", end: "2025-01-12", partial: false }], [lineOf([12000, null], [2, 1])])],
    [2026, answerOf([{ start: "2026-01-01", end: "2026-01-04", partial: true }], [lineOf([8000], [1])])],
  ]);
  const whole = answerOf(
    [
      { start: "2025-01-01", end: "2025-12-31", partial: false },
      { start: "2026-01-01", end: "2026-01-04", partial: true },
    ],
    [lineOf([20000, 8000], [3, 1])],
  );
  const data = view.compareData({ years: [2025, 2026], month: null, grain: "week", mode: "overlay", series: null, answers, whole });
  const readings = view.compareReadings(item, data, 1, "week", "overlay", "ja");
  // 2026 has no second week yet: outside the output; 2025's has no value.
  assert.deepEqual(readings.map((reading) => [reading.year, reading.period, reading.missing?.key ?? null]), [
    [2026, null, "view.compare.outside"],
    [2025, { text: "1/6–1/12" }, "view.compare.no_value"],
  ]);
  const first = view.compareReadings(item, data, 0, "week", "overlay", "ja");
  assert.deepEqual(first[0].period, { key: "view.period.partial", params: {}, keyParams: { period: { text: "1/1–1/4" } } });
  assert.equal(first[0].value.params.value, "8.0");
  assert.equal(first[0].count.key, "view.count.activities");
  const running = view.compareData({ years: [2025, 2026], month: null, grain: "week", mode: "cumulative", series: null, answers, whole });
  assert.equal(view.compareReadings(item, running, 0, "week", "cumulative", "ja")[1].count, null);
  // The table: the periods in rows, the value and the count of each year.
  const table = view.compareTable(item, data, "week", null, 2, "ja");
  assert.deepEqual(table.heads.map((head) => head.key), ["view.compare.period", "view.compare.year", "view.table.activities", "view.compare.year", "view.table.activities"]);
  assert.equal(table.rows.length, 3);
  assert.deepEqual(table.rows[0].cells.map((cell) => [cell.value?.params.value ?? null, cell.count, cell.partial, cell.outside]), [
    ["8.0", "1", true, false],
    ["12.0", "2", true, false],
  ]);
  assert.deepEqual(table.rows[1].cells.map((cell) => [cell.value, cell.outside]), [[null, true], [null, false]]);
  assert.deepEqual(table.rows[2].cells.map((cell) => cell.outside), [true, true]);
  assert.equal(table.last.period.key, "view.compare.value.sum");
  assert.deepEqual(table.last.cells.map((cell) => [cell.value.params.value, cell.partial]), [["8.0", true], ["20.0", false]]);
  assert.equal(table.counts, true);
  // A running total has no counts: that of a period beside a total of all
  // the periods before it would mislead.
  const totals = view.compareTable(item, running, "week", null, 2, "ja", "cumulative");
  assert.equal(totals.counts, false);
  assert.deepEqual(totals.heads.map((head) => head.key), ["view.compare.period", "view.compare.year", "view.compare.year"]);
  assert.deepEqual(totals.rows[0].cells.map((cell) => cell.count), [null, null]);
  assert.deepEqual(totals.last.cells.map((cell) => cell.count), [null, null]);
});

test("the lines of VO2 Max are offered by the names of their legend", () => {
  const line = (source, sport, first, last) => ({ series: { vo2max_source_series: source, sport }, values: [1], counts: [1], first_day: first, last_day: last });
  const panel = { lines: [line("activity", "RUNNING", "2020-01-01", "2022-01-09"), line("performance_metrics_daily", "RUNNING", "2022-01-12", "2026-10-21")] };
  const choices = view.compareSeriesChoices(panel, "ja");
  assert.deepEqual(choices.map((choice) => choice.key), panel.lines.map((entry) => view.seriesKey(entry)));
  assert.deepEqual(choices.map((choice) => choice.name.key), ["view.line.until", "view.line.from"]);
  assert.deepEqual(view.compareSeriesChoices({ lines: [lineOf([1])] }, "ja"), []);
});

test("a stop of a comparison is that of the panels, with the grouping as the next step of an answer too large", () => {
  const large = view.compareStopBox("VIEW_ANSWER_TOO_LARGE", null, "2.2.0", null);
  const panels = view.stopBox("VIEW_ANSWER_TOO_LARGE", null, "2.2.0");
  assert.deepEqual(large.heading, panels.heading);
  assert.deepEqual(large.code, panels.code);
  assert.deepEqual(large.lines.find((line) => line.key === "next.label").keyParams, { step: "view.compare.too_large_next" });
  assert.equal(large.lines.length, panels.lines.length);
  // Over one month, the grouping Month is not used: week only (the checker's L1-3).
  const may = view.compareStopBox("VIEW_ANSWER_TOO_LARGE", null, "2.2.0", 5);
  assert.deepEqual(may.lines.find((line) => line.key === "next.label").keyParams, { step: "view.compare.too_large_next_month" });
  assert.deepEqual(view.compareStopBox("OUTPUT_CHANGED", null, "2.2.0", 5), view.stopBox("OUTPUT_CHANGED", null, "2.2.0"));
});

// v2.2.0 M1: the marks of the person.
const madeUp = (id, day, end = null, kind = "race", name = `Made-up ${id}`) => ({ id, kind, name, day, end });

test("the page takes the marks, whether they show, and what to tell of their file from the settings", () => {
  const marks = [madeUp("m-0000000a", "2030-04-14"), madeUp("m-0000000b", "2030-05-02", "2030-05-20", "injury")];
  assert.deepEqual(view.marksToOpen({ view_marks: marks, view_marks_shown: false, marks_notice: "MARKS_UNREADABLE" }), {
    marks,
    shown: false,
    notice: "MARKS_UNREADABLE",
  });
  // At first they show; a mark of another form, or a notice that the page
  // does not know, is nothing.
  assert.deepEqual(view.marksToOpen({}), { marks: [], shown: true, notice: null });
  assert.deepEqual(view.marksToOpen(null), { marks: [], shown: true, notice: null });
  const others = [null, "m", { id: 1 }, { ...marks[0], kind: "trip" }, { ...marks[0], end: 3 }, { ...marks[0], name: null }];
  assert.deepEqual(view.marksToOpen({ view_marks: [...others, marks[0]], marks_notice: "SETTINGS_INVALID" }), { marks: [marks[0]], shown: true, notice: null });
  assert.deepEqual(view.marksTaken({ marks }), []);
  // The page changes no mark while their file is not used.
  assert.deepEqual(view.MARKS_LOCKED, ["MARKS_UNREADABLE", "MARKS_NEWER"]);
  assert.equal(view.MAX_MARKS, 200);
  assert.deepEqual(view.MARK_KINDS, ["race", "injury", "shoes", "other"]);
});

test("a day of a mark is a date of the calendar from 1900, as the server checks it", () => {
  // The days of the server: from 1 January 1900 to the end of years of four digits.
  for (const day of ["1900-01-01", "2032-02-29", "2030-12-31", "9999-12-31"]) {
    assert.equal(view.markDayOk(day), true, day);
  }
  for (const day of ["1899-12-31", "0099-01-01", "2030-02-29", "2030-02-30", "2030-13-01", "2030-1-01", " 2030-01-01", "10000-01-01", "", null, 20300101]) {
    assert.equal(view.markDayOk(day), false, String(day));
  }
  assert.equal(view.markDaysProblem("2030-03-10", ""), null);
  assert.equal(view.markDaysProblem("2030-03-10", "2030-03-10"), null);
  assert.equal(view.markDaysProblem("2030-03-10", "2030-03-20"), null);
  for (const [day, end] of [["2030-03-10", "2030-03-09"], ["", ""], ["2030-02-30", ""], ["2030-03-10", "2030-02-30"]]) {
    assert.equal(view.markDaysProblem(day, end), "view.marks.error.day", `${day} ${end}`);
  }
});

test("the charts say how many marks their days hold, and the top chart names ten of them", () => {
  const marks = [madeUp("m-1", "2030-01-05"), madeUp("m-2", "2030-02-01", "2030-03-15", "injury"), madeUp("m-3", "2030-06-01")];
  // A span counts where any of its days are shown.
  assert.deepEqual(view.marksWithin(marks, "2030-03-01", "2030-05-31").map((mark) => mark.id), ["m-2"]);
  assert.deepEqual(view.marksWithin(marks, "2030-01-05", "2030-01-05").map((mark) => mark.id), ["m-1"]);
  assert.deepEqual(view.marksWithin(marks, "2030-07-01", "2030-12-31"), []);
  const many = Array.from({ length: 12 }, (_, number) => madeUp(`m-${number}`, `2030-01-${String(number + 1).padStart(2, "0")}`));
  const spoken = view.spokenMarks(many);
  assert.equal(spoken.count, 12);
  assert.equal(spoken.named.length, view.SPOKEN_MARKS);
  assert.equal(view.SPOKEN_MARKS, 10);
  assert.equal(spoken.more, 2);
  assert.deepEqual(view.spokenMarks(marks), { count: 3, named: marks, more: 0 });
  assert.deepEqual(view.markDays(marks[1], "ja"), { day: "2030年2月1日", end: "2030年3月15日" });
  assert.deepEqual(view.markDays(marks[0], "en"), { day: "January 5, 2030", end: null });
});

test("every kind of mark, problem, and notice has words in both languages", () => {
  for (const language of ["en", "ja"]) {
    const messages = catalogs[language];
    for (const key of [...Object.values(view.MARK_PROBLEM_KEYS), ...Object.values(view.MARKS_NOTICE_KEYS)]) {
      assert.ok(messages[key]?.trim(), `${language} ${key}`);
    }
    for (const kind of view.MARK_KINDS) {
      assert.ok(messages[`view.marks.kind.${kind}`]?.trim(), `${language} ${kind}`);
    }
  }
});

// --- Comparing one item by race day (stage M2 of v2.2.0) -------------------

// Made-up race marks, in the order of the server (by their days): the output
// of these tests runs from Monday 5 June 2023 to Friday 8 November 2024.
const FIRST_DAY = "2023-06-05";
const LAST_DAY = "2024-11-08";
const RACE_MARKS = [
  madeUp("m-f", "2023-05-01", null, "race", "Before the output"),
  madeUp("m-d", "2023-07-02", null, "race", "Early summer race"),
  madeUp("m-g", "2024-03-01", null, "injury", "Made-up injury"),
  madeUp("m-a", "2024-04-10", null, "race", "Spring race"),
  madeUp("m-h", "2024-04-10", null, "race", "Spring race"),
  madeUp("m-c", "2024-04-13", "2024-04-14", "race", "Two-day race"),
  madeUp("m-b", "2024-11-10", null, "race", "Autumn race"),
  madeUp("m-e", "2025-06-01", null, "race", "Far after the output"),
];

test("what a comparison is compared by, and its weeks, come back from the settings when they are of their forms", () => {
  assert.deepEqual(view.compareByToOpen({}), { by: "year", weeks: 16 });
  assert.deepEqual(view.compareByToOpen(null), { by: "year", weeks: 16 });
  assert.deepEqual(view.compareByToOpen({ view_compare_by: "race", view_compare_weeks: 24 }), { by: "race", weeks: 24 });
  for (const [by, weeks] of [["Race", 10], ["races", "16"], [1, true], [null, 16.5], ["", 28]]) {
    assert.deepEqual(view.compareByToOpen({ view_compare_by: by, view_compare_weeks: weeks }), { by: "year", weeks: 16 });
  }
  assert.deepEqual(view.COMPARE_WEEKS, [8, 12, 16, 20, 24]);
  assert.equal(view.FIRST_COMPARE_WEEKS, 16);
  assert.equal(view.MAX_COMPARE_RACES, 6);
});

test("a race asks from the Monday of the week some weeks before its week to its day", () => {
  // Wednesday 10 April 2024: its week starts on Monday the 8th.
  assert.deepEqual(view.raceRange("2024-04-10", 16), { from: "2023-12-18", to: "2024-04-10" });
  // A race on a Sunday has its whole week.
  assert.deepEqual(view.raceRange("2024-04-14", 16), { from: "2023-12-18", to: "2024-04-14" });
  assert.deepEqual(view.raceRange("2024-04-13", 8), { from: "2024-02-12", to: "2024-04-13" });
  // Every race has as many weeks: the weeks before, and its own.
  assert.equal(view.raceRange("2024-04-10", 24).from, "2023-10-23");
});

test("the races offered are those whose longest span meets the output, newest first", () => {
  const races = view.compareRaces(RACE_MARKS, FIRST_DAY, LAST_DAY);
  // A race after the last day of the output is offered (its weeks so far);
  // of two on one day, the one added last comes first; a mark of a span
  // counts by its first day; no other kind, and none whose span misses.
  assert.deepEqual(races.map((race) => race.id), ["m-b", "m-c", "m-h", "m-a", "m-d"]);
  assert.deepEqual(view.compareRaces(RACE_MARKS, null, LAST_DAY), []);
  assert.deepEqual(view.compareRaces(RACE_MARKS, LAST_DAY, FIRST_DAY), []);
  assert.deepEqual(view.compareRaces("nope", FIRST_DAY, LAST_DAY), []);
  // By the longest span, 24 weeks: Sunday 6 April 2025 is offered (its 16
  // weeks start after the output), 4 May 2025 is not.
  assert.deepEqual(view.compareRaces([madeUp("m-l", "2025-04-06"), madeUp("m-m", "2025-05-04")], FIRST_DAY, LAST_DAY).map((race) => race.id), ["m-l"]);
  // The race days can be chosen with two races offered at least; what the
  // person chose stays as it is.
  assert.equal(view.compareByFor("race", races), "race");
  assert.equal(view.compareByFor("race", races.slice(0, 1)), "year");
  assert.equal(view.compareByFor("year", races), "year");
  assert.equal(view.compareByFor("race", null), "year");
});

test("the races chosen are four at first, one at least, six at most, in their order", () => {
  const races = view.compareRaces(RACE_MARKS, FIRST_DAY, LAST_DAY);
  assert.deepEqual(view.firstCompareRaces(races), ["m-b", "m-c", "m-h", "m-a"]);
  assert.deepEqual(view.toggledRaces(["m-b", "m-a"], "m-c", races), ["m-b", "m-c", "m-a"]);
  assert.deepEqual(view.toggledRaces(["m-b", "m-a"], "m-a", races), ["m-b"]);
  assert.deepEqual(view.toggledRaces(["m-b"], "m-b", races), ["m-b"]);
  assert.deepEqual(view.toggledRaces(["m-b"], "m-e", races), ["m-b"]);
  const many = Array.from({ length: 8 }, (_none, number) => madeUp(`m-${number}`, `2024-0${number + 1}-07`));
  const offered = view.compareRaces(many, "2023-06-05", "2024-11-08");
  const six = offered.slice(0, 6).map((race) => race.id);
  assert.deepEqual(view.toggledRaces(six, offered[6].id, offered), six);
  // The races kept when the marks or the output change: those still offered,
  // or the first ones.
  assert.deepEqual(view.racesKept(["m-a", "m-x", "m-b"], races), ["m-b", "m-a"]);
  assert.deepEqual(view.racesKept(["m-x"], races), ["m-b", "m-c", "m-h", "m-a"]);
  assert.deepEqual(view.racesKept(null, races), ["m-b", "m-c", "m-h", "m-a"]);
});

test("a comparison by race day goes by week, whatever its way", () => {
  for (const mode of view.COMPARE_MODES) {
    assert.equal(view.compareGrainFor("race", mode, 5), "week");
  }
  assert.deepEqual(view.compareGrainsFor("race", null), ["week"]);
  // By year, as from stage L1.
  assert.equal(view.compareGrainFor("year", "cumulative", null), "day");
  assert.equal(view.compareGrainFor("year", "rows", null), "month");
  assert.deepEqual(view.compareGrainsFor("year", 5), ["day", "week"]);
});

test("the weeks of a race are placed by their order, and marked where they are cut short", () => {
  const races = [RACE_MARKS[6], RACE_MARKS[3], madeUp("m-s", "2023-06-18", null, "race", "A race from the first days"), madeUp("m-o", "2022-01-09")];
  const week = (start, end, partial = false) => ({ start, end, partial });
  const answers = new Map([
    // Wednesday 10 April: the server cuts the week of the race at its day.
    ["m-a", answerOf([week("2024-03-25", "2024-03-31"), week("2024-04-01", "2024-04-07"), week("2024-04-08", "2024-04-10", true)], [lineOf([20000, null, 42195], [2, 0, 1])])],
    // Sunday 10 November, after the output, which ends on a Friday.
    ["m-b", answerOf([week("2024-10-21", "2024-10-27"), week("2024-10-28", "2024-11-03"), week("2024-11-04", "2024-11-08", true)], [lineOf([30000, 25000, 8000])])],
    // The output starts on Wednesday 7 June 2023.
    ["m-s", answerOf([week("2023-06-07", "2023-06-11", true), week("2023-06-12", "2023-06-18")], [lineOf([5000, 21000])])],
    ["m-o", answerOf([], [])],
  ]);
  const whole = (start, end, value, count) => answerOf([{ start, end, partial: false }], [lineOf([value], [count])]);
  const wholes = new Map([
    ["m-a", whole("2024-03-25", "2024-04-10", 62195, 3)],
    ["m-b", whole("2024-10-21", "2024-11-08", 63000, 3)],
    ["m-s", whole("2023-06-07", "2023-06-18", 26000, 2)],
    ["m-o", answerOf([], [])],
  ]);
  const data = view.raceData({ races, weeks: 2, mode: "rows", series: null, answers, wholes, language: "ja" });
  assert.deepEqual(data.map((entry) => [entry.id, entry.step]), [["m-b", 6], ["m-a", 5], ["m-s", 4], ["m-o", 3]]);
  assert.deepEqual(data.map((entry) => words(entry.label)), ["Autumn race（2024年11月10日）", "Spring race（2024年4月10日）", "A race from the first days（2023年6月18日）", "Made-up m-o（2022年1月9日）"]);
  // The short name: the head of the name, and its day (Codex's review of the
  // diff of M2).
  assert.deepEqual(data.map((entry) => words(entry.short)), ["Autumn race 2024/11/10", "Spring race 2024/4/10", "A race from the first… 2023/6/18", "Made-up m-o 2022/1/9"]);
  // The week of the race, cut at its day, is marked as a week of a year cut
  // at its ends (the checker's review of M2); the span is not cut.
  assert.deepEqual(data[1].slots.map((slot) => [slot.start, slot.partial]), [[0, false], [1, false], [2, true]]);
  assert.deepEqual(data[1].cut, { from: null, to: null });
  assert.deepEqual(data[1].whole, { value: 62195, count: 3, partial: false });
  assert.deepEqual(data[1].values, [20000, null, 42195]);
  // The output ends on a Friday before the race: that week is cut, and so is
  // the whole span.
  assert.deepEqual(data[0].slots.map((slot) => [slot.start, slot.partial]), [[0, false], [1, false], [2, true]]);
  assert.deepEqual(data[0].cut, { from: null, to: "2024-11-08" });
  assert.equal(data[0].whole.partial, true);
  // The output starts on a Wednesday: the first week that it has is cut, and
  // the week before it is outside.
  assert.deepEqual(data[2].slots.map((slot) => [slot.start, slot.partial, slot.from]), [[1, true, "2023-06-07"], [2, false, "2023-06-12"]]);
  assert.equal(data[2].whole.partial, true);
  // A race whose span the output does not have.
  assert.deepEqual([data[3].outside, data[3].whole, data[3].values], [true, null, []]);
  // A running total of the weeks; the last is the whole span where nothing is missing.
  const running = view.raceData({ races, weeks: 2, mode: "cumulative", series: null, answers, wholes, language: "ja" });
  assert.deepEqual(running[0].values, [30000, 55000, 63000]);
  assert.equal(running[0].values.at(-1), running[0].whole.value);
  assert.deepEqual(running[1].values, [20000, null, 62195]);
  // The axis and the table: the weeks before, the week of the race, and the
  // value of the span itself (the checker's M2-1).
  const item = { key: "dist", kind: "sum", group: "act" };
  const axis = { slotName: (slot) => view.raceSlotName(slot, 2), whole: view.raceValueMessage(item, 2) };
  const table = view.compareTable(item, data, "week", null, 2, "ja", "rows", axis);
  assert.deepEqual(table.heads.filter((_head, index) => index % 2 === 1).map((head) => words(head)), data.map((entry) => words(entry.label)));
  assert.deepEqual(table.rows.map((row) => words(row.period)), ["2 週前", "1 週前", "大会の週（大会の日まで）"]);
  assert.deepEqual(table.rows[0].cells.map((cell) => [cell.outside, cell.partial]), [[false, false], [false, false], [true, false], [true, false]]);
  assert.deepEqual(table.rows[1].cells.map((cell) => [cell.outside, cell.partial]), [[false, false], [false, false], [false, true], [true, false]]);
  assert.deepEqual(table.rows[2].cells.map((cell) => cell.partial), [true, true, false, false]);
  assert.equal(words(table.last.period), "2 週前から大会の日までの合計");
  assert.deepEqual(table.last.cells.map((cell) => [cell.outside, cell.partial]), [[false, true], [false, false], [false, true], [true, false]]);
  assert.equal(words(table.last.period, "en"), "Total of the days from 2 weeks before to the race day");
  // The readings name each race by its short name.
  const readings = view.compareReadings(item, data, 2, "week", "rows", "ja");
  assert.deepEqual(readings.map((reading) => [reading.id, words(reading.short), reading.missing?.key ?? null]), [
    ["m-b", "Autumn race 2024/11/10", null],
    ["m-a", "Spring race 2024/4/10", null],
    ["m-s", "A race from the first… 2023/6/18", null],
    ["m-o", "Made-up m-o 2022/1/9", "view.compare.outside"],
  ]);
});

test("the axis of the races and the value of a span are named in both languages", () => {
  assert.deepEqual(view.raceTicks(16).map((tick) => [tick.at, words(tick.text)]), [[0, "16 週前"], [4, "12 週前"], [8, "8 週前"], [12, "4 週前"], [16, "大会の週（大会の日まで）"]]);
  assert.deepEqual(view.raceTicks(8).map((tick) => [tick.at, words(tick.text, "en")]), [[0, "8 weeks before"], [4, "4 weeks before"], [8, "Race week (to the race day)"]]);
  assert.equal(words(view.raceSlotName(15, 16)), "1 週前");
  const kinds = { sum: "合計", count: "数", pace: "時間の合計 ÷ 距離の合計", tw: "時間で重みをつけた平均", max: "最大", day: "値のある日の平均", obs: "記録の平均" };
  for (const [kind, text] of Object.entries(kinds)) {
    assert.equal(words(view.raceValueMessage({ kind }, 16, true)), `この範囲の${text}`);
    assert.equal(words(view.raceValueMessage({ kind }, 16)), `16 週前から大会の日までの${text}`);
  }
  assert.equal(words(view.raceValueMessage({ kind: "sum" }, 16, true), "en"), "Total of this span");
  // The name of a race in short, and its button.
  // By columns: a character of Japanese takes two.
  assert.equal(view.shortName("1234567890123456789012"), "1234567890123456789012");
  assert.equal(view.shortName("12345678901234567890123"), "123456789012345678901…");
  assert.equal(view.shortName("𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡𝟘𝟙𝟚𝟛"), "𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡𝟘𝟙…");
  assert.equal(view.shortName("一二三四五六七八九十一"), "一二三四五六七八九十一");
  assert.equal(view.shortName("一二三四五六七八九十一二"), "一二三四五六七八九十…");
  assert.equal(view.shortName("𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋"), "𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋𠀋…");
  // The short name has the day: two races of one name in one year are told
  // apart (Codex's review of the diff of M2).
  assert.equal(words(view.raceShort(madeUp("m-y", "2026-03-15", null, "race", "春のマラソン 2026"), "ja")), "春のマラソン 2026 2026/3/15");
  assert.equal(words(view.raceShort(madeUp("m-y", "2026-03-15", null, "race", "Winter marathon 2026"), "en"), "en"), "Winter marathon 2026 3/15/2026");
  assert.equal(words(view.raceShort(madeUp("m-y", "2026-03-15", null, "race", "とても長い名前の市民マラソン 2026"), "ja")), "とても長い名前の市民… 2026/3/15");
  assert.notEqual(
    words(view.raceShort(madeUp("m-1", "2025-02-23", null, "race", "市民マラソン"), "ja")),
    words(view.raceShort(madeUp("m-2", "2025-11-23", null, "race", "市民マラソン"), "ja")),
  );
  // The button: the short name to the eye, the whole name and the days to
  // the ear, both days of a span.
  const chip = view.raceChip(RACE_MARKS[5], "ja");
  assert.deepEqual([words(chip.short), words(chip.spoken)], ["Two-day race 2024/4/13", "Two-day race、2024年4月13日から2024年4月14日まで"]);
  const one = view.raceChip(madeUp("m-l", "2024-04-10", null, "race", "とても長い名前の地方の市民マラソン大会"), "en");
  assert.deepEqual([words(one.short, "en"), words(one.spoken, "en")], ["とても長い名前の地方… 4/10/2024", "とても長い名前の地方の市民マラソン大会, April 10, 2024"]);
});

test("a comparison by race day follows the marks, the weeks, and the way, step by step", () => {
  // The person chose the race days; the races offered and the four chosen.
  let races = view.compareRaces(RACE_MARKS, FIRST_DAY, LAST_DAY);
  let chosen = view.firstCompareRaces(races);
  assert.equal(view.compareByFor("race", races), "race");
  // A race chosen is removed while its answer is on its way: it is no longer
  // chosen, and the others stay.
  const removed = RACE_MARKS.filter((mark) => mark.id !== "m-c");
  races = view.compareRaces(removed, FIRST_DAY, LAST_DAY);
  chosen = view.racesKept(chosen, races);
  assert.deepEqual(chosen, ["m-b", "m-h", "m-a"]);
  // Another race day: the race stays chosen, by its new day.
  const moved = removed.map((mark) => (mark.id === "m-a" ? { ...mark, day: "2024-05-12" } : mark));
  races = view.compareRaces(moved, FIRST_DAY, LAST_DAY);
  assert.deepEqual(view.racesKept(chosen, races), ["m-b", "m-a", "m-h"]);
  // A change of the weeks offers the same races (by the longest span); a
  // race whose shorter span misses the output is outside (its answer).
  assert.deepEqual(view.compareRaces(moved, "2024-03-25", LAST_DAY).map((race) => race.id), ["m-b", "m-a", "m-h"]);
  // A running total keeps the weeks.
  assert.equal(view.compareGrainFor("race", "cumulative", null), "week");
  // One race offered (the other tab forgot the settings, and one was added
  // again): back to the years; the choice of the person stays.
  races = view.compareRaces([RACE_MARKS[6]], FIRST_DAY, LAST_DAY);
  assert.equal(view.compareByFor("race", races), "year");
  // No marks at all.
  assert.equal(view.compareByFor("race", view.compareRaces([], FIRST_DAY, LAST_DAY)), "year");
});

// --- The list of the activities of a period (stage M3 of v2.2.0) ----------

test("the panels of the activities open the list of a period, when they are charts with values and no numbers are on their way", () => {
  const open = (key, change = {}) => view.listOpens({ item: item(key), mode: "normal", table: false, empty: false, loading: false, ...change });
  for (const key of ["dist", "pace", "hr", "asc", "gct"]) {
    assert.equal(open(key), true, key);
  }
  for (const key of ["rhr", "steps", "sleep", "vo2", "p5k"]) {
    assert.equal(open(key), false, key);
  }
  assert.equal(open("dist", { mode: "big" }), true);
  for (const change of [{ mode: "mini" }, { table: true }, { empty: true }, { loading: true }]) {
    assert.equal(open("dist", change), false, JSON.stringify(change));
  }
  assert.equal(view.listOpens({ item: undefined, mode: "normal", table: false, empty: false, loading: false }), false);
});

test("the list stays for the words, the scales, and the cross line, and closes for any other change", () => {
  const list = { key: "dist", index: 3 };
  for (const change of ["language", "align", "cursor"]) {
    assert.equal(view.listAfter(list, change), list, change);
  }
  for (const change of ["numbers", "items", "marks", "table", "big", "full", "compare", "anything else"]) {
    assert.equal(view.listAfter(list, change), null, change);
  }
  assert.equal(view.listAfter(null, "language"), null);
});

test("a head orders the list up, and down when it is pressed again", () => {
  const first = { column: "when", descending: false };
  assert.deepEqual(view.listSorted(first, "when"), { column: "when", descending: true });
  assert.deepEqual(view.listSorted({ column: "when", descending: true }, "when"), { column: "when", descending: false });
  assert.deepEqual(view.listSorted({ column: "when", descending: true }, "dist"), { column: "dist", descending: false });
});

test("the list has the columns of the server, and the item of its panel where it is none of them", () => {
  const fixed = ["when", "type", "dist", "time", "pace", "hr", "mx", "cad", "asc"];
  assert.deepEqual(view.LIST_ITEMS, fixed.slice(2));
  for (const key of [...fixed.slice(2), "count"]) {
    assert.deepEqual(view.listColumns(key), fixed, key);
  }
  for (const key of ["pow", "load", "gct", "sl"]) {
    assert.deepEqual(view.listColumns(key), [...fixed, key], key);
  }
  assert.equal(view.MAX_LIST_ROWS, 500);
});

test("the heads of the list name their columns with their short units, in both languages", () => {
  const heads = (language) => view.listColumns("gct").map((column) => words(view.listHead(column), language));
  assert.deepEqual(heads("ja"), ["日時", "種目", "距離 km", "時間", "平均ペース /km", "平均心拍 bpm", "最大心拍 bpm", "ピッチ", "総上昇量 m", "接地時間（GCT） ms"]);
  assert.deepEqual(heads("en"), [
    "Date and time",
    "Type",
    "Distance (km)",
    "Time",
    "Average pace (/km)",
    "Average heart rate (bpm)",
    "Maximum heart rate (bpm)",
    "Cadence",
    "Total ascent (m)",
    "Ground contact time (ms)",
  ]);
});

test("the values of a row are written without their units, the time of an activity to the second", () => {
  const cases = [
    ["dist", 10234.5, "10.2"],
    ["dist", 1234567, "1,234.6"],
    ["time", 45 * 60 + 23, "45:23"],
    ["time", 3600 + 2 * 60 + 3, "1:02:03"],
    ["pace", 0.3125, "5:13"],
    ["hr", 151.6, "152"],
    ["mx", 176, "176"],
    ["cad", 171.44, "171.4"],
    ["asc", 123.4, "123"],
    ["gct", 245.4, "245"],
    ["vo", 87, "8.7"],
    ["sl", 1123, "1.12"],
  ];
  for (const [key, value, text] of cases) {
    for (const language of ["ja", "en"]) {
      assert.equal(view.listValueText(key, value, language), text, `${key} ${language}`);
    }
  }
  for (const value of [null, undefined, Number.NaN]) {
    assert.equal(view.listValueText("dist", value, "ja"), null);
  }
  // A time below 0, which the output may hold, is written as it is.
  assert.equal(view.listValueText("time", -60, "ja"), "-1:00");
});

test("the date and time of an activity are written as the output has them, in the form of the language", () => {
  assert.equal(words(view.listWhen("2026-09-14T06:30:00+09:00", "ja"), "ja"), "9/14（月）6:30");
  assert.equal(words(view.listWhen("2026-09-14T06:30:00+09:00", "en"), "en"), "Mon 9/14 6:30");
  // The time of the day as it is: the offset is not taken off.
  assert.equal(words(view.listWhen("2026-09-14T23:05:12.500000-04:00", "ja"), "ja"), "9/14（月）23:05");
  assert.equal(words(view.listWhen("2026-09-15T00:10:00Z", "en"), "en"), "Tue 9/15 0:10");
  // Another form is written as it is; none is none.
  assert.deepEqual(view.listWhen("the morning", "ja"), view.plain("the morning"));
  for (const moment of [null, undefined, "", 7]) {
    assert.equal(view.listWhen(moment, "ja"), null);
  }
});

test("the list is ordered by the date and time as they show, of any timezone, and by the day where a time cannot be read", () => {
  const row = (datetime, day, extra = {}) => ({ datetime, day, type: "running", values: {}, ...extra });
  // The checker's example (M3-1): 07:00+09:00 is later on the screen than
  // 06:30+08:00, though earlier as an instant.
  const tokyo = row("2026-09-14T07:00:00+09:00", "2026-09-14");
  const manila = row("2026-09-14T06:30:00+08:00", "2026-09-14");
  const night = row("2026-09-13T22:00:00+09:00", "2026-09-13");
  const unread = row("the morning", "2026-09-14");
  const none = row(null, "2026-09-15");
  const rows = [tokyo, manila, night, unread, none];
  const name = (type) => type;
  assert.deepEqual(view.sortedListRows(rows, { column: "when", descending: false }, name, "ja"), [night, unread, manila, tokyo, none]);
  assert.deepEqual(view.sortedListRows(rows, { column: "when", descending: true }, name, "ja"), [none, tokyo, manila, unread, night]);
  assert.equal(view.listMomentKey(manila), "2026-09-14T06:30:00");
  assert.equal(view.listMomentKey(unread), "2026-09-14");
  // The same date and time: the order of the server, either way.
  const twin = row("2026-09-14T07:00:00+08:00", "2026-09-14");
  assert.deepEqual(view.sortedListRows([twin, tokyo], { column: "when", descending: false }, name, "ja"), [twin, tokyo]);
  assert.deepEqual(view.sortedListRows([twin, tokyo], { column: "when", descending: true }, name, "ja"), [twin, tokyo]);
});

test("a column orders the list by its values, rows without one last either way, and the same values by their date and time", () => {
  const row = (datetime, dist, type = "running") => ({ datetime, day: datetime.slice(0, 10), type, values: { dist } });
  const a = row("2026-09-14T07:00:00+09:00", 5000);
  const b = row("2026-09-15T07:00:00+09:00", null);
  const c = row("2026-09-16T07:00:00+09:00", 12000);
  const d = row("2026-09-13T07:00:00+09:00", 5000);
  const e = row("2026-09-17T07:00:00+09:00", 0);
  const rows = [a, b, c, d, e];
  const name = (type) => type;
  assert.deepEqual(view.sortedListRows(rows, { column: "dist", descending: false }, name, "ja"), [e, d, a, c, b]);
  assert.deepEqual(view.sortedListRows(rows, { column: "dist", descending: true }, name, "ja"), [c, d, a, e, b]);
  // The type by its name as the page writes it.
  const trail = row("2026-09-18T07:00:00+09:00", 9000, "trail_running");
  const bike = row("2026-09-12T07:00:00+09:00", 30000, "road_biking");
  const named = (type) => words(view.typeMessage(type), "en");
  assert.deepEqual(view.sortedListRows([trail, a, bike], { column: "type", descending: false }, named, "en"), [bike, a, trail]);
  assert.deepEqual(view.sortedListRows([trail, a, bike], { column: "type", descending: true }, named, "en"), [trail, a, bike]);
  // In Japanese, by the names of the page, not by the keys of Garmin.
  const japanese = (type) => words(view.typeMessage(type), "ja");
  const names = view.sortedListRows([trail, a, bike], { column: "type", descending: false }, japanese, "ja").map((entry) => japanese(entry.type));
  assert.deepEqual(names, [...names].sort((x, y) => x.localeCompare(y, "ja")));
  assert.notDeepEqual(names.map((name) => [trail, a, bike].find((entry) => japanese(entry.type) === name).type), ["road_biking", "running", "trail_running"]);
  // The rows themselves are not changed.
  assert.deepEqual(rows, [a, b, c, d, e]);
});

test("the list says its period, its panel, the value of the panel, and its limit, in both languages", () => {
  const week = { start: "2026-09-14", end: "2026-09-20", partial: false };
  const month = { start: "2026-10-01", end: "2026-10-29", partial: true };
  assert.equal(words(view.listTitle(week, "week", "ja"), "ja"), "2026年9月14日の週の練習");
  assert.equal(words(view.listTitle(week, "week", "en"), "en"), "Activities: Week of September 14, 2026");
  assert.equal(words(view.listTitle(month, "month", "ja"), "ja"), "2026年10月（途中）の練習");
  assert.equal(words(view.listTitle(month, "month", "en"), "en"), "Activities: October 2026 (partial)");
  assert.equal(words(view.listFrom("dist", 5, "ja"), "ja"), "距離の段から・5 件");
  assert.equal(words(view.listFrom("dist", 1234, "en"), "en"), "From the Distance panel · activities: 1,234");
  const line = view.listValueLine("dist", { value: 45400, count: 5 }, "ja");
  assert.deepEqual(line.strong, ["value"]);
  assert.equal(words(line, "ja"), "段の値：45.4 km（この値に数えた 5 件）");
  assert.equal(words(view.listValueLine("pace", { value: 0.3125, count: 4 }, "en"), "en"), "Value of the panel: 5:13 /km (activities counted: 4)");
  assert.equal(words(view.listValueLine("hr", { value: null, count: 0 }, "ja"), "ja"), "段の値：値なし（この値に数えた 0 件）");
  assert.equal(
    words(view.listLimitMessage(812, 500, "month", "ja"), "ja"),
    "この区切りには 812 件あります。一覧は 500 件までです。まとめ方を「週」にすると、一覧で見られます。",
  );
  assert.equal(words(view.listLimitMessage(1812, 500, "year", "en"), "en"), "This period has 1,812 activities. The list shows up to 500. Group by “Month” to list them.");
  assert.equal(words(view.listLimitMessage(612, 500, "week", "ja"), "ja"), "この区切りには 612 件あります。一覧は 500 件までです。まとめ方を「日」にすると、一覧で見られます。");
  assert.equal(words(view.listLimitMessage(501, 500, "day", "ja"), "ja"), "この日には 501 件あります。一覧は 500 件までです。");
  assert.equal(words(view.listLimitMessage(501, 500, "day", "en"), "en"), "This day has 501 activities. The list shows up to 500.");
});

// --- The calendar of comparing years (stage N1 of v2.2.0) -------------------

test("a calendar places each day by its week from the week of 1 January and its day of the week", () => {
  // 1 January 2025 was a Wednesday, in the week of Monday 30 December.
  assert.deepEqual(view.calendarPlace("2025-01-01"), { week: 0, day: 2 });
  assert.deepEqual(view.calendarPlace("2025-05-04"), { week: 17, day: 6 });
  assert.deepEqual(view.calendarPlace("2024-12-30"), { week: 52, day: 0 });
  // 53 columns, or 54 for a leap year that starts on a Sunday.
  assert.equal(view.calendarWeeks(2025), 53);
  assert.equal(view.calendarWeeks(2012), 54);
  // Every day of a leap and of a common year has its own place, and the
  // place gives the day back; a place outside the year has none.
  for (const year of [2024, 2025]) {
    const places = new Set();
    for (let count = Date.UTC(year, 0, 1) / 86400000; count <= Date.UTC(year, 11, 31) / 86400000; count += 1) {
      const iso = new Date(count * 86400000).toISOString().slice(0, 10);
      const place = view.calendarPlace(iso);
      assert.ok(place.day >= 0 && place.day <= 6 && place.week >= 0 && place.week < view.calendarWeeks(year), iso);
      assert.equal(view.calendarDate(year, place.week, place.day), iso);
      places.add(`${place.week} ${place.day}`);
    }
    assert.equal(places.size, year === 2024 ? 366 : 365);
  }
  assert.equal(view.calendarDate(2025, 0, 0), null);
  assert.equal(view.calendarDate(2025, 52, 3), null);
});

test("a calendar shows the same day of the year in every strip, or the nearest one that the output has", () => {
  const leap = view.daySlot("2024-02-29");
  assert.equal(view.slotDay(leap, 2024), "2024-02-29");
  assert.equal(view.slotDay(leap, 2025), null);
  assert.equal(view.daySlot("2025-03-01"), view.daySlot("2024-03-01"));
  // 29 February of a common year is 28 February (the checker's review of the
  // plan of N1); outside the output, the nearest day that it has.
  assert.equal(view.calendarDay(leap, 2025, "2020-01-01", "2026-10-21"), "2025-02-28");
  assert.equal(view.calendarDay(view.daySlot("2026-12-31"), 2026, "2020-01-01", "2026-10-21"), "2026-10-21");
  assert.equal(view.calendarDay(view.daySlot("2020-01-02"), 2020, "2020-03-05", "2026-10-21"), "2020-03-05");
  assert.equal(view.calendarDay(view.daySlot("2025-05-04"), 2025, "2020-01-01", "2026-10-21"), "2025-05-04");
  assert.equal(view.calendarDay(0, 2019, "2020-03-05", "2026-10-21"), null);
});

test("the keys of a calendar move a week across, a day up and down, and to the ends of its year in the output, and stop there", () => {
  const move = (day, key, first = "2020-01-01", last = "2026-10-21") => {
    const year = Number(day.slice(0, 4));
    return view.slotDay(view.calendarMove(view.daySlot(day), year, key, first, last), year);
  };
  assert.equal(move("2025-05-04", "ArrowRight"), "2025-05-11");
  assert.equal(move("2025-05-04", "ArrowLeft"), "2025-04-27");
  // Down from a Sunday goes on to the Monday of the next week.
  assert.equal(move("2025-05-04", "ArrowDown"), "2025-05-05");
  assert.equal(move("2025-05-05", "ArrowUp"), "2025-05-04");
  // A day after 28 February: 1 March in a common year, 29 February in a leap
  // one; from the place of 29 February, a common year starts at 28 February.
  assert.equal(move("2025-02-28", "ArrowDown"), "2025-03-01");
  assert.equal(move("2024-02-28", "ArrowDown"), "2024-02-29");
  assert.equal(view.slotDay(view.calendarMove(view.daySlot("2024-02-29"), 2025, "ArrowDown", "2020-01-01", "2026-10-21"), 2025), "2025-03-01");
  // Home and End: the first and last day of the year that the output has;
  // the keys stop at the ends of the year and of the output.
  assert.equal(move("2026-05-04", "Home", "2026-03-05"), "2026-03-05");
  assert.equal(move("2026-05-04", "End"), "2026-10-21");
  assert.equal(move("2026-10-20", "ArrowRight"), "2026-10-21");
  assert.equal(move("2025-01-02", "ArrowLeft"), "2025-01-01");
  assert.equal(move("2025-12-31", "ArrowDown"), "2025-12-31");
  assert.equal(move("2026-03-05", "ArrowUp", "2026-03-05"), "2026-03-05");
  // Another key, or a year without a day in the output, moves nothing.
  assert.equal(view.calendarMove(0, 2025, "PageDown", "2020-01-01", "2026-10-21"), null);
  assert.equal(view.calendarMove(0, 2019, "Home", "2020-01-01", "2026-10-21"), null);
});

test("a day of a total without a recorded activity is an outline, and a recorded 0 is a value in the first step", () => {
  const dist = ITEMS.find((item) => item.key === "dist");
  assert.equal(view.calendarCell(dist, 0, 0), "zero");
  // Activities of 0 km are recorded (Codex's review of the plan of N1).
  assert.equal(view.calendarCell(dist, 0, 2), "value");
  assert.equal(view.calendarStep([0, 10, 20, 30, 40], 0), 1);
  assert.equal(view.calendarCell(dist, 7600, 1), "value");
  assert.equal(view.calendarCell(dist, null, 0), null);
  assert.equal(view.calendarCell({ key: "count", kind: "count" }, 0, 0), "zero");
  // The 0 of a daily item is its value.
  assert.equal(view.calendarCell({ key: "sscore", kind: "day" }, 0, 0), "value");
});

test("the steps of a calendar hold their left value and spread over the six colors, in the words of the ticks", () => {
  const ticks = [0, 5, 10, 15, 20];
  assert.deepEqual([0, 4.99, 5, 9.99, 10, 15, 19.9].map((value) => view.calendarStep(ticks, value)), [1, 1, 3, 3, 4, 6, 6]);
  assert.deepEqual([0, 1, 2, 3, 4, 5, 5.5].map((value) => view.calendarStep([0, 1, 2, 3, 4, 5, 6], value)), [1, 2, 3, 4, 5, 6, 6]);
  assert.equal(view.calendarStep([0, 10], 3), view.CALENDAR_STEPS);
  const dist = ITEMS.find((item) => item.key === "dist");
  const legend = view.calendarLegend(dist, [0, 10, 20, 30, 40], "ja");
  assert.deepEqual(legend.map((entry) => entry.step), [1, 3, 4, 6]);
  assert.deepEqual(legend.map((entry) => words(entry.words, "ja")), ["10 未満", "10–20", "20–30", "30–40"]);
  assert.equal(words(view.calendarLegend(dist, [0, 10, 20], "en")[0].words, "en"), "under 10");
  // A mean has no outline: its first step is between two ticks; a clock
  // writes its ticks as a clock.
  const hr = ITEMS.find((item) => item.key === "hr");
  assert.deepEqual(view.calendarLegend(hr, [140, 150, 160], "ja").map((entry) => [entry.step, words(entry.words, "ja")]), [[1, "140–150"], [6, "150–160"]]);
  const pace = ITEMS.find((item) => item.key === "pace");
  assert.deepEqual(view.calendarLegend(pace, [300, 330, 360], "en").map((entry) => words(entry.words, "en")), ["5:00–5:30", "5:30–6:00"]);
});

test("a calendar says a day with its day of the week and its value, a day without a record, no value, or outside the output", () => {
  const dist = ITEMS.find((item) => item.key === "dist");
  const day = (iso) => ({ start: iso, end: iso, partial: false });
  const entry = { periods: [day("2025-05-04"), day("2025-05-05"), day("2025-05-06"), day("2025-05-07")], values: [7600, 0, null, 0], counts: [1, 0, 0, 2] };
  const say = (iso, language = "ja") => {
    const reading = view.calendarReading(dist, entry, iso, language);
    return [words(reading.day, language), words(reading.value, language), words(reading.count, language), words(reading.missing, language)];
  };
  assert.deepEqual(say("2025-05-04"), ["2025年5月4日（日）", "7.6 km", "1 回", ""]);
  assert.deepEqual(say("2025-05-04", "en"), ["Sun, May 4, 2025", "7.6 km", "activities: 1", ""]);
  assert.deepEqual(say("2025-05-05"), ["2025年5月5日（月）", "0.0 km（記録の無い日）", "", ""]);
  assert.deepEqual(say("2025-05-06"), ["2025年5月6日（火）", "", "", "値なし"]);
  assert.deepEqual(say("2025-05-07"), ["2025年5月7日（水）", "0.0 km", "2 回", ""]);
  assert.deepEqual(say("2025-05-08"), ["2025年5月8日（木）", "", "", "出力の外です。"]);
  // The days without a recorded activity, in the note of the legend.
  assert.equal(view.calendarZeroDays(dist, [entry, entry]), 2);
  assert.match(words(view.calendarZeroNote(2, "ja"), "ja"), /^記録の無い日（0）が 2 あります。/);
});

test("a calendar compares years by day, never an estimate of several records a day, and uses no month", () => {
  assert.equal(view.compareModeFor({ kind: "obs" }, "calendar"), "rows");
  for (const kind of ["sum", "count", "pace", "tw", "max", "day"]) {
    assert.equal(view.compareModeFor({ kind }, "calendar"), "calendar", kind);
  }
  assert.equal(view.compareModeFor(null, "calendar"), "rows");
  assert.equal(view.calendarItem({ kind: "obs" }), false);
  assert.deepEqual(view.compareGrains(5, "calendar"), ["day"]);
  assert.deepEqual(view.compareGrains(null, "calendar"), ["day"]);
  assert.deepEqual(view.compareGrains(null), ["day", "week", "month"]);
  assert.equal(view.firstCompareGrain("calendar", null), "day");
  assert.deepEqual(view.compareGrainsFor("year", 5, "calendar"), ["day"]);
  // By race day, by week whatever the way.
  assert.deepEqual(view.compareGrainsFor("race", null, "calendar"), ["week"]);
  assert.equal(view.compareGrainFor("race", "calendar", null), "week");
  // The month that it uses: none for a calendar; the month remembered stays
  // for the other ways.
  assert.equal(view.compareMonthFor("calendar", 5), null);
  assert.equal(view.compareMonthFor("rows", 5), 5);
  // The settings remember a calendar, and no other form of it.
  assert.equal(view.compareToOpen({ view_compare_mode: "calendar" }).mode, "calendar");
  assert.equal(view.compareToOpen({ view_compare_mode: "Calendar" }).mode, "rows");
});

test("a comparison asks again where its way changes its grouping or the month that it uses", () => {
  // One month by day, then a calendar: the same grouping, other days.
  assert.equal(view.compareAsksAgain({ grain: "day", month: 5 }, { grain: "day", month: view.compareMonthFor("calendar", 5) }), true);
  // Back from a calendar to the month remembered.
  assert.equal(view.compareAsksAgain({ grain: "day", month: null }, { grain: "day", month: view.compareMonthFor("rows", 5) }), true);
  // The whole year by day, then a calendar: the same numbers, drawn again.
  assert.equal(view.compareAsksAgain({ grain: "day", month: null }, { grain: "day", month: view.compareMonthFor("calendar", null) }), false);
  assert.equal(view.compareAsksAgain({ grain: "month", month: null }, { grain: "day", month: null }), true);
  assert.equal(view.compareAsksAgain({ grain: "month", month: null }, { grain: "month", month: null }), false);
});

test("a calendar finds the day under the pointer by its column and its row, and colors the days of every year on one scale", () => {
  // Squares 12 px apart: the column of a week and the row of a day.
  assert.equal(view.calendarAt(2025, 17 * 12 + 5, 6 * 12 + 11, 12), "2025-05-04");
  assert.equal(view.calendarAt(2025, 0, 2 * 12, 12), "2025-01-01");
  assert.equal(view.calendarAt(2025, 0, 0, 12), null);
  assert.equal(view.calendarAt(2025, -1, 30, 12), null);
  assert.equal(view.calendarAt(2025, 30, 7 * 12, 12), null);
  assert.equal(view.calendarAt(2025, 60 * 12, 30, 12), null);
  // The values that take a color, as shown, of every year: not a day without
  // a value nor one without a recorded activity; a recorded 0 is one.
  const dist = ITEMS.find((item) => item.key === "dist");
  const data = [
    { values: [7600, 0, null, 0], counts: [1, 0, 0, 2] },
    { values: [12000, 3000], counts: [1, 1] },
  ];
  const lines = [{ values: [7.6, 0, null, 0] }, { values: [12, 3] }];
  assert.deepEqual(view.calendarValues(dist, data, lines), [7.6, 0, 12, 3]);
  assert.deepEqual(view.calendarValues({ key: "sscore", kind: "day" }, [{ values: [0, 80], counts: [1, 1] }], [{ values: [0, 80] }]), [0, 80]);
});

test("a calendar is drawn only from an answer of whole years by day (Codex's review of the diff of N1)", () => {
  assert.equal(view.calendarAnswer({ by: "year", grain: "day", month: null }), true);
  // The answer of another way, while the new one is on its way.
  assert.equal(view.calendarAnswer({ by: "year", grain: "month", month: null }), false);
  assert.equal(view.calendarAnswer({ by: "year", grain: "day", month: 5 }), false);
  assert.equal(view.calendarAnswer({ by: "race", grain: "week", month: null }), false);
  assert.equal(view.calendarAnswer(null), false);
});

// --- Two items plotted against each other (stage O1 of v2.2.0) ------------

const COUNT_ITEM = { key: "count", group: "act", kind: "count", unit: "activity", unit_group: null, per_day: false, sleep: false, from_fit: false };

test("two items are plotted from the items of one activity, as one pair of two different ones", () => {
  // The items of the activities that one activity has a value of: not the
  // count, nor an item of the days (view/series.py point_item).
  assert.deepEqual([...ITEMS, COUNT_ITEM].filter(view.plotItem).map((entry) => entry.key), ["dist", "pace", "hr", "asc", "gct"]);
  assert.deepEqual(view.PLOT_FIRST, { x: "pace", y: "hr" });
  assert.equal(view.MAX_POINTS, 5000);
  // The pair that the settings remember, as one, never one of them alone
  // (Codex's review of the plan of O1).
  assert.deepEqual(view.plotPairToOpen({ view_plot: { x: "dist", y: "gct" } }), { x: "dist", y: "gct" });
  for (const pair of [{ x: "dist", y: "dist" }, { x: "dist" }, { x: "nope", y: "hr" }, ["dist", "hr"], "dist", null, undefined]) {
    assert.deepEqual(view.plotPairToOpen({ view_plot: pair }), { x: "pace", y: "hr" });
  }
  assert.deepEqual(view.plotPairToOpen(null), { x: "pace", y: "hr" });
  // Among the items of an output: the pair, the first pair, or none.
  assert.deepEqual(view.plotPairOf({ x: "dist", y: "gct" }, ITEMS), { x: "dist", y: "gct" });
  assert.deepEqual(view.plotPairOf({ x: "dist", y: "rhr" }, ITEMS), { x: "pace", y: "hr" });
  assert.deepEqual(view.plotPairOf({ x: "count", y: "dist" }, [...ITEMS, COUNT_ITEM]), { x: "pace", y: "hr" });
  assert.deepEqual(view.plotPairOf({ x: "hr", y: "hr" }, ITEMS), { x: "pace", y: "hr" });
  assert.equal(view.plotPairOf({ x: "dist", y: "rhr" }, ITEMS.filter((entry) => entry.key !== "hr")), null);
  // Forgetting the settings forgets the pair.
  assert.equal("view_plot" in view.settingsAfterForget({ view_plot: { x: "dist", y: "hr" } }), false);
});

test("a point says its date and time with its year, or its date only, as the output has them", () => {
  const point = { day: "2026-09-14", datetime: "2026-09-14T06:30:00+09:00", type: "running", values: { pace: 0.321, hr: 144 } };
  assert.equal(words(view.plotWhen(point, "ja"), "ja"), "2026年9月14日（月）6:30");
  assert.equal(words(view.plotWhen(point, "en"), "en"), "Mon, September 14, 2026 6:30");
  // Without a time that can be read, the day of the row (Codex's review of
  // the plan of O1); never a timezone changed.
  assert.equal(words(view.plotWhen({ ...point, datetime: null }, "ja"), "ja"), "2026年9月14日（月）");
  assert.equal(words(view.plotWhen({ ...point, datetime: "the morning" }, "en"), "en"), "Mon, September 14, 2026");
  assert.equal(words(view.plotWhen({ ...point, datetime: "2026-09-14T23:05:12-04:00" }, "ja"), "ja"), "2026年9月14日（月）23:05");
  const reading = view.plotReading(point, "pace", "hr", (name) => `T:${name}`, "ja", 2);
  assert.equal(reading.type, "T:running");
  assert.equal(words(reading.x.name, "ja"), "平均ペース");
  assert.equal(words(reading.x.value, "ja"), "5:21 /km");
  assert.equal(words(reading.y.value, "ja"), "144 bpm");
  assert.equal(words(reading.same, "ja"), "同じ値の回がほかに 2 回");
  assert.equal(view.plotReading(point, "pace", "hr", String, "ja", 0).same, null);
});

test("the point under the pointer is the nearest drawn within reach, the newest of those as near", () => {
  const places = [{ x: 10, y: 10 }, { x: 20, y: 10 }, { x: 20, y: 10 }, { x: 100, y: 100 }];
  assert.equal(view.nearestPoint(places, 11, 10, 12), 0);
  // Two points in one place: the newer, which comes later.
  assert.equal(view.nearestPoint(places, 19, 11, 12), 2);
  assert.equal(view.nearestPoint(places, 60, 60, 12), null);
  assert.equal(view.nearestPoint([], 0, 0, 12), null);
  const points = [{ values: { a: 1, b: 2 } }, { values: { a: 1, b: 2 } }, { values: { a: 1, b: 3 } }];
  assert.equal(view.sameValues(points, 0, "a", "b"), 1);
  assert.equal(view.sameValues(points, 2, "a", "b"), 0);
  assert.equal(view.sameValues(points, 9, "a", "b"), 0);
});

test("the keys move one point in the order of their dates, or to the first and the last, and stop at the ends", () => {
  assert.equal(view.plotMove(null, 5, "ArrowRight"), 4);
  assert.equal(view.plotMove(null, 5, "ArrowLeft"), 4);
  assert.equal(view.plotMove(null, 5, "Home"), 0);
  assert.equal(view.plotMove(2, 5, "ArrowLeft"), 1);
  assert.equal(view.plotMove(2, 5, "ArrowRight"), 3);
  assert.equal(view.plotMove(4, 5, "ArrowRight"), 4);
  assert.equal(view.plotMove(0, 5, "ArrowLeft"), 0);
  assert.equal(view.plotMove(1, 5, "End"), 4);
  assert.equal(view.plotMove(1, 5, "ArrowUp"), null);
  assert.equal(view.plotMove(null, 0, "End"), null);
});

test("a table of the points is never ordered by a column that it no longer has", () => {
  // Codex's review of the diff of O1: the column of an item changed goes.
  const columns = ["when", "type", "pace", "hr"];
  assert.deepEqual(view.plotSortAfter({ column: "hr", descending: false }, columns), { column: "hr", descending: false });
  assert.deepEqual(view.plotSortAfter({ column: "dist", descending: false }, columns), { column: "when", descending: true });
  assert.deepEqual(view.plotSortAfter(undefined, columns), { column: "when", descending: true });
});

test("the line under the points says their numbers only, and that the newest are kept where they are cut", () => {
  // The checker's review of the plan of O1, with the words of OP0.
  const answer = { total: 4900, with_values: 4812, missing: 88, limit: 5000, points: new Array(4812).fill(null) };
  assert.equal(words(view.plotCount(answer, "ja"), "ja"), "点：4,812 回（この期間の 4,900 回のうち、両方の値がある回。値の無い回 88）");
  assert.equal(view.plotCut(answer), false);
  const cut = { total: 6200, with_values: 6100, missing: 100, limit: 5000, points: new Array(5000).fill(null) };
  assert.equal(words(view.plotCount(cut, "ja"), "ja"), "点：5,000 回（この期間の 6,200 回のうち、両方の値がある 6,100 回の新しい回。値の無い回 100）");
  assert.equal(words(view.plotCount(cut, "en"), "en"), "Points: 5,000 (the newest of the 6,100 activities of this period with both values, of 6,200; without them: 100)");
  assert.equal(view.plotCut(cut), true);
  assert.equal(translate(catalogs, "ja", "view.plot.cut", { max: "5,000" }), "新しい 5,000 回だけを点にしています。期間をしぼると全部を出せます。");
});

test("the points are in the order of their dates and times as the server orders them", () => {
  // view/series.py _moment_key and listMomentKey are one rule: the date and
  // the time as they show, the day where the time cannot be read, and then
  // the order of the output (as the test of the server has them).
  const points = [
    { day: "2024-03-04", datetime: "2024-03-04T07:00:00+09:00", type: "running", values: { dist: 5000 } },
    { day: "2024-03-04", datetime: "2024-03-04T06:30:00+08:00", type: "running", values: { dist: 6000 } },
    { day: "2024-03-04", datetime: null, type: "running", values: { dist: 7000 } },
    { day: "2024-03-04", datetime: "not a time", type: "running", values: { dist: 8000 } },
    { day: "2024-03-03", datetime: "2024-03-03T21:00:00+09:00", type: "running", values: { dist: 9000 } },
    { day: "2024-03-04", datetime: "2024-03-04T07:00:00+09:00", type: "running", values: { dist: 4000 } },
  ];
  const sorted = view.sortedListRows(points, { column: "when", descending: false }, String, "ja");
  assert.deepEqual(sorted.map((row) => row.values.dist), [9000, 7000, 8000, 6000, 5000, 4000]);
});

test("the item of a distribution is one of the points, the distance at first, and the settings keep it", () => {
  // Stage P1 of v2.2.0: the items of the points, the distance as the sample
  // of OP0 showed it, and an item of another output gives its place.
  assert.equal(view.SPREAD_FIRST, "dist");
  assert.equal(view.spreadItemToOpen({ view_spread: "gct" }), "gct");
  for (const key of ["nope", 3, null, undefined, ["dist"]]) {
    assert.equal(view.spreadItemToOpen({ view_spread: key }), "dist");
  }
  assert.equal(view.spreadItemToOpen(null), "dist");
  assert.equal(view.spreadItemOf("gct", ITEMS), "gct");
  assert.equal(view.spreadItemOf("rhr", ITEMS), "dist");
  assert.equal(view.spreadItemOf("count", [...ITEMS, COUNT_ITEM]), "dist");
  assert.equal(view.spreadItemOf("rhr", ITEMS.filter((entry) => entry.key !== "dist")), "pace");
  assert.equal(view.spreadItemOf("dist", ITEMS.filter((entry) => !view.plotItem(entry))), null);
  assert.equal("view_spread" in view.settingsAfterForget({ view_spread: "dist" }), false);
});

test("a range is written from the numbers of the answer, in the units of the page, for every item, also wider", () => {
  // The checker's review of the plan of P1: the ends are (first + i) times
  // the width over the scale of the answer, as the page writes the values
  // of the item, at the width of the item and at 100 times it.
  const cases = [
    ["dist", { first: 10, width: 1000, scale: 1 }, "10〜11 km", "10–11 km"],
    ["dist", { first: 0, width: 100000, scale: 1 }, "0〜100 km", "0–100 km"],
    ["time", { first: 3, width: 600, scale: 1 }, "0:30〜0:40", "0:30–0:40"],
    ["time", { first: 1, width: 60000, scale: 1 }, "16:40〜33:20", "16:40–33:20"],
    ["pace", { first: 31, width: 10, scale: 1000 }, "5:10〜5:20 /km", "5:10–5:20 /km"],
    ["pace", { first: 0, width: 1000, scale: 1000 }, "0:00〜16:40 /km", "0:00–16:40 /km"],
    ["hr", { first: 29, width: 5, scale: 1 }, "145〜150 bpm", "145–150 bpm"],
    ["mx", { first: 0, width: 500, scale: 1 }, "0〜500 bpm", "0–500 bpm"],
    ["cad", { first: 34, width: 5, scale: 1 }, "170〜175", "170–175"],
    ["pow", { first: 0, width: 1000, scale: 1 }, "0〜1,000", "0–1,000"],
    ["load", { first: 10, width: 10, scale: 1 }, "100〜110", "100–110"],
    ["asc", { first: 4, width: 10, scale: 1 }, "40〜50 m", "40–50 m"],
    ["vo", { first: 17, width: 5, scale: 1 }, "8.5〜9.0 cm", "8.5–9.0 cm"],
    ["vo", { first: 0, width: 500, scale: 1 }, "0〜50 cm", "0–50 cm"],
    ["gct", { first: 24, width: 10, scale: 1 }, "240〜250 ms", "240–250 ms"],
    ["gctp", { first: 30, width: 10, scale: 10 }, "30〜31 %", "30–31%"],
    ["bal", { first: 99, width: 5, scale: 10 }, "49.5〜50.0 %", "49.5–50.0%"],
    ["vr", { first: 0, width: 500, scale: 10 }, "0〜50 %", "0–50%"],
    ["sl", { first: 24, width: 50, scale: 1 }, "1.20〜1.25 m", "1.20–1.25 m"],
    ["sl", { first: 0, width: 5000, scale: 1 }, "0〜5 m", "0–5 m"],
  ];
  for (const [key, numbers, ja, en] of cases) {
    const answer = { ...numbers, counts: [1], limit: 200, widened: false };
    assert.equal(words(view.spreadRange(key, answer, 0, "ja"), "ja"), ja, key);
    assert.equal(words(view.spreadRange(key, answer, 0, "en"), "en"), en, key);
  }
  // The words of a wider width: 10 minutes times 10 and 10 seconds a
  // kilometre times 5, as the checker asked to see them.
  const time = { first: 0, width: 6000, scale: 1, counts: [1], limit: 200, widened: true };
  assert.equal(words(view.spreadWide("time", time, "ja"), "ja"), "区切りが 200 を超えるので、幅を 1:40 にしました。");
  assert.equal(words(view.spreadWide("time", time, "en"), "en"), "As there would be more than 200 ranges, each range is 1:40 wide.");
  const pace = { first: 6, width: 50, scale: 1000, counts: [1], limit: 200, widened: true };
  assert.equal(words(view.spreadWide("pace", pace, "ja"), "ja"), "区切りが 200 を超えるので、幅を 0:50 /km にしました。");
  assert.equal(words(view.spreadWide("dist", { first: 0, width: 5000, scale: 1, counts: [1], limit: 200, widened: true }, "ja"), "ja"), "区切りが 200 を超えるので、幅を 5 km にしました。");
  assert.equal(view.spreadWide("dist", { first: 0, width: 1000, scale: 1, counts: [1], limit: 200, widened: false }, "ja"), null);
});

test("a range says its ends and its count, and an end that the page cannot write is a dash", () => {
  // The checker's P1-3: the reading and the keys say what an end means.
  const answer = { first: 10, width: 1000, scale: 1, counts: [3, 0, 42], limit: 200, widened: false };
  assert.equal(words(view.spreadReading("dist", answer, 2, "ja"), "ja"), "12 km 以上 13 km 未満：42 回");
  assert.equal(words(view.spreadReading("dist", answer, 1, "en"), "en"), "11 km or more, under 12 km: 0");
  const pace = { first: 31, width: 10, scale: 1000, counts: [5], limit: 200, widened: false };
  assert.equal(words(view.spreadReading("pace", pace, 0, "ja"), "ja"), "5:10 /km 以上 5:20 /km 未満：5 回");
  // The checker's P1-4 and Codex's review of the plan of P1: ends past 2^53
  // are not exact, and an answer of a number of more than 310 digits is
  // Infinity in the page; neither is ever written as Infinity or NaN.
  const past = { first: 2 ** 53, width: 1, scale: 1, counts: [1, 1], limit: 200, widened: false };
  const huge = JSON.parse(`{"first": 1${"0".repeat(311)}, "width": 10, "scale": 1000, "counts": [1, 2], "limit": 200, "widened": true}`);
  assert.equal(huge.first, Infinity);
  const finite = { first: 1e290, width: 1000, scale: 1, counts: [1, 1], limit: 200, widened: true };
  // A small number of a range with a very wide width, as an activity of 1e300
  // m and one of 10 km give (the partial guard of P1): its ends are numbers,
  // too large for the page to write.
  const wide = { first: 0, width: 5e297, scale: 1, counts: [1, 1], limit: 200, widened: true };
  assert.equal(words(view.spreadRange("dist", wide, 0, "ja"), "ja"), "0〜—");
  for (const [key, given] of [["dist", past], ["pace", huge], ["dist", { ...past, first: 1e297, width: 5e297 }], ["dist", finite], ["dist", wide]]) {
    for (const index of [0, 1]) {
      for (const language of ["ja", "en"]) {
        const text = [words(view.spreadRange(key, given, index, language), language), words(view.spreadReading(key, given, index, language), language), words(view.spreadWide(key, given, language), language)].join(" ");
        // Never a number of hundreds of digits: the page writes a dash for an
        // end of 1e15 or more in its units, so at most 18 digits, its
        // separators aside (an end past 2^53 may be inexact).
        assert.doesNotMatch(text.replace(/[,.\s\u202f]/g, ""), /Infinity|NaN|\d{21}/, text);
      }
    }
  }
  assert.deepEqual(view.spreadEnds(huge, 0), { left: null, right: null });
  assert.equal(words(view.spreadRange("pace", huge, 0, "ja"), "ja"), "—〜—");
  // Codex's review of the diff of P1: a number of a range past 2^53 is not
  // exact in the page (5e17 mm of the step length are the range 1e16 of 50
  // mm), and two ends that the page cannot tell apart, also of numbers below
  // it (the range 2^53 - 3 of 3 m), are never written as one value.
  const step = { first: 1e16, width: 50, scale: 1, counts: [1], limit: 200, widened: false };
  assert.equal(step.first + 1, step.first);
  assert.equal(words(view.spreadReading("sl", step, 0, "ja"), "ja"), "— 以上 — 未満：1 回");
  const meet = { first: 2 ** 53 - 3, width: 3, scale: 1, counts: [1], limit: 200, widened: false };
  assert.ok(Number.isSafeInteger(meet.first + 1) && meet.first * 3 === (meet.first + 1) * 3);
  assert.deepEqual(view.spreadEnds(meet, 0), { left: null, right: null });
  // Past 2^53 the next number of a range can be two ranges further (2^53 + 2
  // and 2^53 + 4): its ends would differ, but the right one would be wrong.
  const off = { first: 2 ** 53 + 2, width: 1, scale: 1, counts: [1], limit: 200, widened: false };
  assert.ok(off.first < off.first + 1 && off.first + 1 - off.first === 2);
  assert.deepEqual(view.spreadEnds(off, 0), { left: null, right: null });
  for (const given of [past, huge, finite, step, meet, answer, pace, { first: 2 ** 53 - 20, width: 1, scale: 1, counts: [1, 1] }]) {
    for (const index of [0, 1]) {
      const { left, right } = view.spreadEnds(given, index);
      assert.ok(left === null || right === null || left < right, JSON.stringify(given));
    }
  }
});

test("the keys move one range, those of no activity among them, and stop at the ends", () => {
  // The checker's P1-3: as the rows of the table.
  assert.equal(view.spreadMove(null, 5, "ArrowRight"), 0);
  assert.equal(view.spreadMove(null, 5, "ArrowLeft"), 4);
  assert.equal(view.spreadMove(2, 5, "ArrowLeft"), 1);
  assert.equal(view.spreadMove(2, 5, "ArrowRight"), 3);
  assert.equal(view.spreadMove(4, 5, "ArrowRight"), 4);
  assert.equal(view.spreadMove(0, 5, "ArrowLeft"), 0);
  assert.equal(view.spreadMove(3, 5, "Home"), 0);
  assert.equal(view.spreadMove(1, 5, "End"), 4);
  assert.equal(view.spreadMove(1, 5, "ArrowUp"), null);
  assert.equal(view.spreadMove(null, 0, "End"), null);
});

test("the line under the ranges says their numbers only", () => {
  const answer = { total: 3380, with_values: 3370, missing: 10, counts: [1], limit: 200 };
  assert.equal(words(view.spreadCount(answer, "ja"), "ja"), "数えた回：3,370 回（この期間の 3,380 回のうち、値がある回。値の無い回 10）");
  assert.equal(words(view.spreadCount(answer, "en"), "en"), "Counted: 3,370 (the activities of this period with a value, of 3,380; without one: 10)");
  assert.equal(translate(catalogs, "ja", "view.spread.faster_left"), "値が小さいほど速い（グラフでは左ほど速い）。");
});

// --- The summary of the panels (stage Q1 of v2.2.0) -----------------------

test("the columns of the summary name the period shown and the one of the same length before it, none for all time", () => {
  const names = (period, language) => {
    const columns = view.recapColumns(period, language);
    return [words(columns.now, language), columns.before === null ? null : words(columns.before, language)];
  };
  assert.deepEqual(names("1y", "ja"), ["この 1 年", "前の 1 年"]);
  assert.deepEqual(names("3y", "ja"), ["この 3 年", "前の 3 年"]);
  assert.deepEqual(names("5y", "en"), ["The last 5 years", "The 5 years before"]);
  assert.deepEqual(names("10y", "en"), ["The last 10 years", "The 10 years before"]);
  assert.deepEqual(names("1y", "en"), ["The last year", "The year before"]);
  assert.deepEqual(names("all", "ja"), ["全期間", null]);
  assert.deepEqual(names("all", "en"), ["All time", null]);
  // A range by its days as chosen, one day too (the checker's answer 3).
  assert.deepEqual(names({ from: "2024-01-01", to: "2024-01-31" }, "ja"), ["この期間", "その前の 31 日"]);
  assert.deepEqual(names({ from: "2024-01-01", to: "2024-01-31" }, "en"), ["This period", "The 31 days before"]);
  assert.deepEqual(names({ from: "2024-02-29", to: "2024-02-29" }, "ja"), ["この期間", "その前の 1 日"]);
  assert.deepEqual(names({ from: "2024-02-29", to: "2024-02-29" }, "en"), ["This period", "The day before"]);
  assert.deepEqual(names({ from: "2000-01-01", to: "2024-12-31" }, "en"), ["This period", "The 9,132 days before"]);
});

test("a difference is now minus before with its sign only, no sign where it reads as 0, and a dash without a value", () => {
  const difference = (key, now, before, language = "ja") => words(view.recapDifference(key, now, before, language), language);
  assert.equal(difference("dist", 12345.6, 10000), "+2.3 km");
  assert.equal(difference("dist", 10000, 10100), "−0.1 km");
  assert.equal(difference("dist", 10000, 10000), "0.0 km");
  // Small differences either way read as 0, never −0.0 (Codex's review of
  // the plan of Q1, 6).
  assert.equal(difference("dist", 10000, 10000.04), "0.0 km");
  assert.equal(difference("dist", 10000.04, 10000), "0.0 km");
  assert.equal(difference("dist", 10000, 10049.9), "0.0 km");
  assert.equal(difference("dist", 10000, 10050), "−0.1 km");
  assert.equal(difference("count", 12, 10), "+2 回");
  assert.equal(difference("count", 12, 10, "en"), "+2");
  assert.equal(difference("count", 5, 5), "0 回");
  assert.equal(difference("hr", 151.6, 150), "+2 bpm");
  // A pace and a time as a clock, both signs rounded alike: half a minute
  // is a minute either way.
  assert.equal(difference("pace", 0.3, 0.305), "−0:05 /km");
  assert.equal(difference("pace", 0.305, 0.3), "+0:05 /km");
  assert.equal(difference("time", 3630, 3600), "+0:01");
  assert.equal(difference("time", 3600, 3630), "−0:01");
  assert.equal(difference("time", 3610, 3600), "0:00");
  assert.equal(difference("time", 3600, 3610), "0:00");
  // A value of 0 is a value: 0 km before is a difference.
  assert.equal(difference("dist", 5000, 0), "+5.0 km");
  // The two values as the table writes them are subtracted (stage Q1):
  // 49.0 and 49.0 are 0.0 apart, 0.15 km is written 0.2 km, and 1.325 m is
  // written 1.33 m by the numbers of the language, where toFixed gives 1.32.
  assert.equal(difference("vo2", 49.04, 48.96), "0.0");
  assert.equal(difference("dist", 150, 0), "+0.2 km");
  assert.equal(difference("sl", 1325, 1300), "+0.03 m");
  assert.equal(difference("hr", 150.5, 150.4), "+1 bpm");
  // A clock rounds as it is written, below 0 too: -30 seconds is 0:00 as 0
  // is, and -90 seconds is -0:01 (Codex's review of the diff of Q1).
  assert.equal(words(view.valueMessage("time", -30, "ja"), "ja"), "0:00");
  assert.equal(difference("time", -30, 0), "0:00");
  assert.equal(difference("time", -90, 0), "\u22120:01");
  for (const [now, before] of [[null, 1], [1, null], [Number.NaN, 1], [undefined, undefined]]) {
    assert.equal(difference("dist", now, before), "—");
  }
});

test("a period that the output cuts says where, from, to, or both, and a period held whole says nothing", () => {
  const partial = (chosen, start, end, language = "ja") => words(view.recapPartial(chosen, start, end, language), language);
  assert.equal(partial({ start: "2023-03-01", end: "2024-02-29" }, "2023-05-01", "2024-02-29"), "（途中：2023年5月1日から）");
  assert.equal(partial({ start: "2024-01-15", end: "2024-02-10" }, "2024-01-15", "2024-01-31"), "（途中：2024年1月31日まで）");
  assert.equal(partial({ start: "2023-12-01", end: "2024-02-10" }, "2024-01-01", "2024-01-31"), "（途中：2024年1月1日から2024年1月31日まで）");
  assert.equal(partial({ start: "2023-12-01", end: "2024-02-10" }, "2024-01-01", "2024-01-31", "en"), " (cut: from January 1, 2024 to January 31, 2024)");
  assert.equal(partial({ start: "2023-05-01", end: "2024-02-29" }, "2023-06-01", "2024-02-29", "en"), " (cut: from June 1, 2023)");
  // An end before the calendar is null, and cut.
  assert.equal(partial({ start: null, end: "0001-02-28" }, "0001-01-01", "0001-02-28"), "（途中：1年1月1日から）");
  assert.equal(view.recapPartial({ start: "2024-01-01", end: "2024-01-31" }, "2024-01-01", "2024-01-31", "ja"), null);
  assert.equal(view.recapPartial({ start: "2023-01-01", end: "2023-12-31" }, null, null, "ja"), null);
});

test("the line of the days says what the two periods count, as the output cuts them", () => {
  const days = (answer, period, language = "ja") => words(view.recapDays(answer, view.recapColumns(period, language), language), language);
  const answer = { start: "2023-03-01", end: "2024-02-29", previous: { start: "2022-03-01", end: "2023-02-28" } };
  assert.equal(days(answer, "1y"), "この 1 年：2023年3月1日〜2024年2月29日／前の 1 年：2022年3月1日〜2023年2月28日");
  assert.equal(days(answer, "1y", "en"), "The last year: March 1, 2023–February 29, 2024; The year before: March 1, 2022–February 28, 2023");
  const outside = { start: "2024-01-01", end: "2024-01-31", previous: { start: null, end: null } };
  assert.equal(days(outside, { from: "2024-01-01", to: "2024-01-31" }), "この期間：2024年1月1日〜2024年1月31日／その前の 31 日：出力の外");
  assert.equal(days({ start: "2020-01-01", end: "2024-02-29", previous: null }, "all"), "全期間：2020年1月1日〜2024年2月29日");
  assert.equal(view.recapDays({ start: null, end: null, previous: null }, view.recapColumns("1y", "ja"), "ja"), null);
});

test("an item has a row for each series of the two periods, in the order of the server, named as one panel", () => {
  const line = (source, sport, first, last, value) => ({
    series: { vo2max_source_series: source, sport },
    values: [value],
    counts: [value === null ? 0 : 1],
    first_day: first,
    last_day: last,
  });
  const empty = { series: null, values: [null], counts: [0] };
  const shape = (rows, language = "ja") =>
    rows.map((row) => [row.name === null ? null : words(row.name, language), row.now?.values[0] ?? null, row.before?.values[0] ?? null]);
  const old = (value) => line("activity_vo2max_daily", "RUNNING", "2011-04-01", "2022-01-09", value);
  const fresh = (value) => line("performance_metrics_daily", "RUNNING", "2022-01-12", "2026-10-18", value);
  // A series of the period before only, an old source, comes first and is
  // named "until" (Codex's review of the plan of Q1, 1); the panel of now
  // has one line and no name.
  assert.deepEqual(shape(view.recapRows({ lines: [fresh(50)] }, { lines: [old(47), fresh(48)] }, "ja")), [
    ["〜2022年1月9日", null, 47],
    ["2022年1月12日〜", 50, 48],
  ]);
  // A series of now only; the line without a series of the server is left
  // out where there is a series.
  assert.deepEqual(shape(view.recapRows({ lines: [fresh(50)] }, { lines: [empty] }, "ja")), [[null, 50, null]]);
  assert.deepEqual(shape(view.recapRows({ lines: [empty] }, { lines: [old(47)] }, "en"), "en"), [[null, null, 47]]);
  // VO2 Max without a value in both periods keeps its row (Codex's 2).
  assert.deepEqual(shape(view.recapRows({ lines: [empty] }, { lines: [empty] }, "ja")), [[null, null, null]]);
  assert.deepEqual(shape(view.recapRows({ lines: [] }, null, "ja")), [[null, null, null]]);
  // An item of one line, 0 of an activity item a value of its row.
  const dist = (value) => ({ series: null, values: [value], counts: [value ? 3 : 0] });
  assert.deepEqual(shape(view.recapRows({ lines: [dist(12000)] }, { lines: [dist(0)] }, "ja")), [[null, 12000, 0]]);
  assert.deepEqual(shape(view.recapRows({ lines: [dist(12000)] }, null, "ja")), [[null, 12000, null]]);
  // The first day first: a source that starts earlier is the first line
  // and is named "until", whatever the order of the names (the partial guard
  // of Q1: the sources of Garmin sort the same way by both).
  const zold = line("z_source", "RUNNING", "2011-04-01", "2022-01-09", 40);
  const anew = line("a_source", "RUNNING", "2022-01-12", "2026-10-18", 50);
  assert.deepEqual(shape(view.recapRows({ lines: [anew] }, { lines: [anew, zold] }, "ja")), [
    ["〜2022年1月9日", null, 40],
    ["2022年1月12日〜", 50, 50],
  ]);
  // The same first day: the source "x" before "x y", as the server orders
  // the tuple, not as the keys sort as texts (the checker's Q1-8).
  const x = (source, value) => line(source, "RUNNING", "2020-01-01", "2020-12-31", value);
  assert.deepEqual(
    view.recapRows({ lines: [x("x y", 2), x("x", 1)] }, null, "ja").map((row) => row.now.series.vo2max_source_series),
    ["x", "x y"],
  );
  // The sports of one series, by the sport.
  const sports = view.recapRows({ lines: [fresh(50)] }, { lines: [line("performance_metrics_daily", "CYCLING", "2022-01-12", "2026-10-18", 45), fresh(48)] }, "en");
  assert.deepEqual(shape(sports, "en"), [
    ["Cycling", null, 45],
    ["Running", 50, 48],
  ]);
});

// --- Saving as an image (stage R1 of v2.2.0) -------------------------------

test("a saved picture writes the styles of the page as attributes of SVG, tabular figures as font-variant", () => {
  assert.deepEqual(
    view.SAVE_ATTRIBUTES.find(([property]) => property === "font-variant-numeric"),
    ["font-variant-numeric", "font-variant"],
  );
  // The outline of the names of the marks is drawn under the letters
  // (the checker's R1-1).
  assert.deepEqual(view.SAVE_ATTRIBUTES.find(([property]) => property === "paint-order"), ["paint-order", "paint-order"]);
  // Every attribute is one that SVG has; font-family is written once, on the
  // outer element, and display never.
  const svg = new Set(["fill", "stroke", "stroke-width", "stroke-dasharray", "stroke-linecap", "stroke-linejoin", "opacity", "fill-opacity", "stroke-opacity", "font-size", "font-weight", "font-variant", "paint-order"]);
  assert.deepEqual(view.SAVE_ATTRIBUTES.map(([, attribute]) => attribute).filter((attribute) => !svg.has(attribute)), []);
  assert.equal(view.SAVE_ATTRIBUTES.some(([property]) => ["font-family", "display"].includes(property)), false);
  const outer = { fill: "rgb(0, 0, 0)", stroke: "none", "stroke-width": "1px", opacity: "1", "font-size": "14px", "font-variant-numeric": "normal", "paint-order": "normal" };
  assert.deepEqual(
    view.savedAttributes(outer).map(([attribute]) => attribute),
    ["fill", "stroke", "stroke-width", "opacity", "font-size", "font-variant", "paint-order"],
  );
  // Inside, what differs from the shape around it only.
  const name = { ...outer, fill: "rgb(86, 96, 112)", stroke: "rgb(255, 255, 255)", "stroke-width": "4px", "font-size": "11px", "paint-order": "stroke" };
  assert.deepEqual(view.savedAttributes(name, outer), [
    ["fill", "rgb(86, 96, 112)"],
    ["stroke", "rgb(255, 255, 255)"],
    ["stroke-width", "4px"],
    ["font-size", "11px"],
    ["paint-order", "stroke"],
  ]);
  assert.deepEqual(view.savedAttributes({ ...outer, "font-variant-numeric": "tabular-nums" }, outer), [["font-variant", "tabular-nums"]]);
  // Opacity is not taken from the shape around: written where it is not 1.
  const faded = { ...outer, opacity: "0.5" };
  assert.deepEqual(view.savedAttributes(faded, faded), [["opacity", "0.5"]]);
  assert.deepEqual(view.savedAttributes(outer, faded), []);
  // One that the shape has as an attribute of its own is written even where
  // it is the same as around it, as the page may override it by a style, as
  // forced colors do the dash of the lines of the years (the checker's review
  // of the diff of R1, (a)).
  const line = { ...outer, "stroke-dasharray": "none" };
  assert.deepEqual(view.savedAttributes(line, line), []);
  assert.deepEqual(view.savedAttributes(line, line, ["stroke-dasharray"]), [["stroke-dasharray", "none"]]);
  assert.deepEqual(view.savedAttributes(outer, outer, ["opacity", "stroke-width"]), [
    ["stroke-width", "1px"],
    ["opacity", "1"],
  ]);
  assert.deepEqual(view.savedAttributes(outer, outer, ["font-variant"]), [["font-variant", "normal"]]);
});

test("a saved picture leaves out the cross line and the frame of the list, and the marks unless they go in", () => {
  assert.deepEqual(view.SAVE_LEFT_OUT, [".cross", ".list-frame"]);
  assert.deepEqual(view.SAVE_MARKS, [".day-band", ".day-mark", ".day-mark-name"]);
});

test("the days of a saved picture are those of the answer, not the ends of the weeks of its panels (periods[0].start)", () => {
  const answer = { start: "2025-10-22", end: "2026-10-21", periods: [{ start: "2025-10-20", end: "2025-10-26" }, { start: "2026-10-19", end: "2026-10-25" }] };
  assert.deepEqual(view.saveDays(answer), { start: "2025-10-22", end: "2026-10-21" });
  assert.equal(view.saveDays({ start: null, end: null, periods: [] }), null);
  assert.equal(view.saveDays(null), null);
});

test("the name of a saved picture has the days and the keys of the panels only, nothing of the person's own", () => {
  assert.equal(view.saveFileName("2025-10-22", "2026-10-21", ["dist", "pace", "hr"]), "garmin-view_2025-10-22_2026-10-21_dist-pace-hr.svg");
  // Not a key of an item, such as a name of a mark or a place: no name.
  for (const keys of [["dist", "けが"], ["dist", "../x"], ["Dist"], []]) {
    assert.equal(view.saveFileName("2025-10-22", "2026-10-21", keys), null, JSON.stringify(keys));
  }
  for (const [start, end] of [["2025年", "2026-10-21"], [null, "2026-10-21"], ["2025-10-22", undefined]]) {
    assert.equal(view.saveFileName(start, end, ["dist"]), null, `${start} ${end}`);
  }
});

test("a picture copies the panels in the order shown, the panel made big first, and charts only", () => {
  // The order shown has the panel made big first (shownPanels), and the
  // panels shown as tables are left out.
  assert.deepEqual(view.savedPanels(["hr", "dist", "pace"], ["pace"], "all", "dist"), ["hr", "dist"]);
  assert.deepEqual(view.savedPanels(["hr", "dist", "pace"], [], "one", "dist"), ["dist"]);
  assert.deepEqual(view.savedPanels(["hr", "dist", "pace"], ["dist"], "one", "dist"), []);
  assert.deepEqual(view.savedPanels(["hr", "dist"], [], "one", "vo2"), []);
});

test("a picture can be saved only with an answer not on its way, no stop of the panels, and a chart", () => {
  const ready = { viewing: true, apart: false, full: false, items: 2, answer: {}, loading: false, stopped: false, charts: 1 };
  assert.equal(view.saveShowable(ready), true);
  for (const [name, value] of [["viewing", false], ["apart", true], ["full", true], ["items", 0], ["answer", null], ["loading", true], ["stopped", true], ["charts", 0]]) {
    assert.equal(view.saveShowable({ ...ready, [name]: value }), false, name);
  }
});

test("the line under a picture says the period, the grain of the answer, the types counted, and the version", () => {
  const types = [
    { name: "running", count: 10, running: true },
    { name: "trail_running", count: 2, running: true },
    { name: "cycling", count: 5, running: false },
  ];
  const pieces = (options, language = "ja") => view.saveFooter({ start: "2025-10-22", end: "2026-10-21", grain: "week", answerTypes: null, types, version: "2.2.0", language, ...options }).map((piece) => words(piece, language));
  assert.deepEqual(pieces({}), ["期間 2025年10月22日〜2026年10月21日", "まとめ方 週", "数える種目 ランニングの種目すべて（2 つ）", "Garmin Running Data Normalizer 2.2.0"]);
  assert.deepEqual(pieces({}, "en"), ["Period October 22, 2025–October 21, 2026", "Group by Week", "Activity types counted: All running types (2)", "Garmin Running Data Normalizer 2.2.0"]);
  // The types that the answer counts, the grain of the answer, no version.
  assert.deepEqual(pieces({ answerTypes: ["cycling"], grain: "day", version: null }), ["期間 2025年10月22日〜2026年10月21日", "まとめ方 日", "数える種目 1 つの種目", "Garmin Running Data Normalizer"]);
  // An output without activities (Codex's review of the plan of R1).
  assert.equal(pieces({ types: [] })[2], "数える種目 アクティビティの記録がありません");
});

test("the lines of a picture put each piece where it fits after the gap, and cut a piece wider than the width after a space", () => {
  const measure = (text) => text.length * 10;
  const shape = (lines) => lines.map((line) => line.map((piece) => [piece.text, piece.x]));
  assert.deepEqual(shape(view.saveLines([{ text: "abc" }, { text: "de" }], 100, 5, measure)), [[["abc", 0], ["de", 35]]]);
  assert.deepEqual(shape(view.saveLines([{ text: "abcdefg" }, { text: "hijk" }], 100, 5, measure)), [[["abcdefg", 0]], [["hijk", 0]]]);
  assert.deepEqual(shape(view.saveLines([{ text: "ab cd efgh ij" }], 70, 5, measure)), [[["ab cd", 0]], [["efgh ij", 0]]]);
  // Japanese has no space: cut after the last letter that fits.
  assert.deepEqual(shape(view.saveLines([{ text: "印の名前がとても長い" }], 50, 5, measure)), [[["印の名前が", 0]], [["とても長い", 0]]]);
  // Never inside a pair of the letters of UTF-16, at least one letter.
  assert.deepEqual(shape(view.saveLines([{ text: "😀😀😀" }], 30, 5, measure)), [[["😀", 0]], [["😀", 0]], [["😀", 0]]]);
  assert.deepEqual(shape(view.saveLines([{ text: "abc" }], 5, 5, measure)), [[["a", 0]], [["b", 0]], [["c", 0]]]);
  // The measure has the piece: a name in bold is wider.
  const bold = (text, piece) => text.length * (piece.bold ? 20 : 10);
  assert.deepEqual(shape(view.saveLines([{ text: "ab", bold: true }, { text: "cd" }], 70, 5, bold)), [[["ab", 0], ["cd", 45]]]);
  assert.deepEqual(shape(view.saveLines([{ text: "abc", bold: true }, { text: "cd" }], 70, 5, bold)), [[["abc", 0]], [["cd", 0]]]);
});

test("the line after a saving goes with the output, the period, the types, the items, and the language", () => {
  const base = { ticket: "t1", period: "1y", types: null, items: ["dist"], language: "ja" };
  const key = view.saveNoticeKey(base);
  assert.equal(view.saveNoticeKey({ ...base }), key);
  for (const [name, value] of [["ticket", "t2"], ["period", "3y"], ["types", ["running"]], ["items", ["dist", "hr"]], ["language", "en"]]) {
    assert.notEqual(view.saveNoticeKey({ ...base, [name]: value }), key, name);
  }
});

test("the frame of a picture grows to what its parts show out of their frames, with the room of the outlines", () => {
  // Nothing out: the width and the height of the parts.
  assert.deepEqual(view.saveFrame([], 1200, 500), { x: 0, y: 0, width: 1200, height: 500 });
  assert.deepEqual(view.saveFrame([{ left: 8, top: 8, right: 1192, bottom: 480 }], 1200, 500), { x: 0, y: 0, width: 1200, height: 500 });
  // A label at the end of the time axis, and one at the start (Codex's
  // review of the diff of R1).
  assert.deepEqual(view.saveFrame([{ left: 1180, top: 470, right: 1210.2, bottom: 484 }], 1200, 500), { x: 0, y: 0, width: 1215, height: 500 });
  assert.deepEqual(view.saveFrame([{ left: -3, top: 2, right: 40, bottom: 12 }], 1200, 500), { x: -7, y: -2, width: 1207, height: 502 });
  assert.deepEqual(view.saveFrame([{ left: 8, top: 490, right: 100, bottom: 503 }], 1200, 500, 0), { x: 0, y: 0, width: 1200, height: 503 });
});

// --- Saving the other views as an image (stage R2 of v2.2.0) ---------------

test("the window of the saving shows by the view of its button, and another view saves its answer drawn as a chart", () => {
  // The panels as in R1: panels, and not the graphs only.
  const panels = { viewing: true, from: "panels", view: "panels", items: 2, full: false };
  assert.equal(view.saveWindowShows(panels), true);
  for (const [name, value] of [["viewing", false], ["items", 0], ["full", true], ["from", "compare"], ["view", "plot"]]) {
    assert.equal(view.saveWindowShows({ ...panels, [name]: value }), false, name);
  }
  // Another view shows the window from its own button only, also while it
  // cannot save yet, which the window says (Codex's review of the plan of R2).
  for (const each of ["compare", "plot", "spread"]) {
    assert.equal(view.saveWindowShows({ viewing: true, from: each, view: each, items: 0, full: false }), true, each);
    assert.equal(view.saveWindowShows({ viewing: true, from: "panels", view: each, items: 2, full: false }), false, each);
    assert.equal(view.saveWindowShows({ viewing: true, from: each, view: "panels", items: 2, full: false }), false, each);
    assert.equal(view.saveWindowShows({ viewing: false, from: each, view: each, items: 2, full: false }), false, each);
  }
  const ready = { answer: {}, loading: false, stopped: false, table: false, charts: 1 };
  assert.equal(view.saveViewReady(ready), true);
  for (const [name, value] of [["answer", null], ["answer", undefined], ["loading", true], ["stopped", true], ["table", true], ["charts", 0]]) {
    assert.equal(view.saveViewReady({ ...ready, [name]: value }), false, `${name} ${value}`);
  }
});

test("the window says why a picture cannot be saved: a table, a stop, no values, or no room to draw", () => {
  const ready = { table: false, stopped: false, loading: false, answer: {}, empty: false, drawn: 2, parts: 2 };
  assert.equal(view.saveProblem(ready), null);
  assert.equal(view.saveProblem({ ...ready, table: true }), "view.save.table");
  assert.equal(view.saveProblem({ ...ready, stopped: true }), "view.save.stopped");
  assert.equal(view.saveProblem({ ...ready, empty: true }), "view.save.empty");
  assert.equal(view.saveProblem({ ...ready, drawn: 1 }), "view.save.undrawn");
  // A table first, then a stop; nothing while an answer is on its way, or
  // before the first one, which the window says by itself.
  assert.equal(view.saveProblem({ ...ready, table: true, stopped: true, empty: true, drawn: 0 }), "view.save.table");
  assert.equal(view.saveProblem({ ...ready, stopped: true, drawn: 0 }), "view.save.stopped");
  assert.equal(view.saveProblem({ ...ready, loading: true, drawn: 0 }), null);
  assert.equal(view.saveProblem({ ...ready, answer: null, drawn: 0 }), null);
  assert.equal(view.saveProblem({ ...ready, empty: true, drawn: 0 }), "view.save.empty");
  // No part to draw is not a chart without room (all the panels as tables).
  assert.equal(view.saveProblem({ ...ready, drawn: 0, parts: 0 }), null);
  assert.equal(view.saveProblem({}), null);
});

test("a picture of another view leaves out the cross, the frame of the day chosen, and the point or the range chosen", () => {
  assert.deepEqual(view.SAVE_LEFT_OUT_VIEWS, { compare: [".cross", ".calendar-cursor"], plot: [".plot-chosen"], spread: [".spread-chosen"] });
});

test("the name of a picture of another view has the years or the race days, the period, and the keys, nothing of the person's own", () => {
  // The years as they were chosen, which can skip some, never as a range,
  // oldest first (the checker's R2-2).
  assert.equal(view.saveViewFileName("compare", { key: "dist", years: [2025, 2018, 2022] }), "garmin-compare_2018-2022-2025_dist.svg");
  // The days of the races, never their names (the checker's answer 2).
  assert.equal(view.saveViewFileName("compare", { key: "dist", days: ["2026-03-15", "2025-11-02"] }), "garmin-compare-races_2025-11-02_2026-03-15_dist.svg");
  assert.equal(view.saveViewFileName("plot", { keys: ["pace", "hr"], start: "2025-10-22", end: "2026-10-21" }), "garmin-plot_2025-10-22_2026-10-21_pace-hr.svg");
  assert.equal(view.saveViewFileName("spread", { key: "pace", start: "2025-10-22", end: "2026-10-21" }), "garmin-spread_2025-10-22_2026-10-21_pace.svg");
  // No name where a part is not of its form, as for the panels.
  for (const [kind, options] of [
    ["compare", { key: "dist", days: ["合成の大会 1"] }],
    ["compare", { key: "dist", days: ["2025-11-02", "2025/11/03"] }],
    ["compare", { key: "dist", years: ["25"] }],
    ["compare", { key: "dist" }],
    ["compare", { key: "Dist", years: [2025] }],
    ["compare", { key: null, years: [2025] }],
    ["compare", { key: "null", years: [] }],
    ["plot", { keys: ["pace", null], start: "2025-10-22", end: "2026-10-21" }],
    ["plot", { keys: ["pace", "../x"], start: "2025-10-22", end: "2026-10-21" }],
    ["plot", { keys: [], start: "2025-10-22", end: "2026-10-21" }],
    ["spread", { key: "dist", start: "2025年", end: "2026-10-21" }],
    ["spread", { key: "dist", start: null, end: "2026-10-21" }],
    ["spread", { key: "けが", start: "2025-10-22", end: "2026-10-21" }],
    ["panels", { key: "dist", start: "2025-10-22", end: "2026-10-21" }],
  ]) {
    assert.equal(view.saveViewFileName(kind, options), null, `${kind} ${JSON.stringify(options)}`);
  }
});

test("the width of a range is written in the unit of its item, as the page writes a wider one", () => {
  for (const [key, answer, ja, en] of [
    ["dist", { first: 0, width: 1000, scale: 1 }, "1 km", "1 km"],
    ["pace", { first: 6, width: 10, scale: 1000 }, "0:10 /km", "0:10 /km"],
    ["time", { first: 0, width: 6000, scale: 1 }, "1:40", "1:40"],
  ]) {
    assert.equal(words(view.spreadWidthValue(key, answer, "ja"), "ja"), ja, key);
    assert.equal(words(view.spreadWidthValue(key, answer, "en"), "en"), en, key);
  }
  // The words of a wider width are those of the width (Codex's review of the
  // plan of R2: one way to write it).
  const wide = { first: 0, width: 5000, scale: 1, counts: [1], limit: 200, widened: true };
  assert.equal(words(view.spreadWide("dist", wide, "ja"), "ja"), `区切りが 200 を超えるので、幅を ${words(view.spreadWidthValue("dist", wide, "ja"), "ja")} にしました。`);
});

test("the line under a picture of another view says the years or the race days compared, the period, the width of a range, the types, and the version", () => {
  const types = [
    { name: "running", count: 10, running: true },
    { name: "trail_running", count: 2, running: true },
    { name: "cycling", count: 5, running: false },
  ];
  const pieces = (kind, options, language = "ja") =>
    view
      .saveViewFooter(kind, { answerTypes: null, types, version: "2.2.0", language, separator: language === "ja" ? "、" : ", ", daysSeparator: language === "ja" ? "、" : "; ", ...options })
      .map((piece) => words(piece, language));
  // The years as they were chosen, oldest first, with the grain of their
  // answer (the checker's R2-2).
  assert.deepEqual(pieces("compare", { years: [2025, 2018, 2022], grain: "week" }), [
    "くらべた年 2018、2022、2025",
    "まとめ方 週",
    "数える種目 ランニングの種目すべて（2 つ）",
    "Garmin Running Data Normalizer 2.2.0",
  ]);
  assert.deepEqual(pieces("compare", { years: [2026, 2025], grain: "day" }, "en"), [
    "Years compared: 2025, 2026",
    "Group by Day",
    "Activity types counted: All running types (2)",
    "Garmin Running Data Normalizer 2.2.0",
  ]);
  // The days of the races, never their names; their weeks are in the title.
  assert.deepEqual(pieces("compare", { days: ["2026-03-15", "2025-11-02"] }), [
    "くらべた大会の日 2025年11月2日、2026年3月15日",
    "数える種目 ランニングの種目すべて（2 つ）",
    "Garmin Running Data Normalizer 2.2.0",
  ]);
  // In English the days of the races are parted by semicolons, as their words
  // have commas.
  assert.equal(pieces("compare", { days: ["2026-03-15", "2025-11-02"] }, "en")[0], "Race days compared: November 2, 2025; March 15, 2026");
  // The period of the points, with the types that the view asked for.
  assert.deepEqual(pieces("plot", { start: "2025-10-22", end: "2026-10-21", answerTypes: ["cycling"] }), [
    "期間 2025年10月22日〜2026年10月21日",
    "数える種目 1 つの種目",
    "Garmin Running Data Normalizer 2.2.0",
  ]);
  // The width of a range in the unit of its item (Codex's review of the plan
  // of R2), also where it is not wider.
  const range = { first: 0, width: 1000, scale: 1, counts: [1], limit: 200, widened: false };
  assert.deepEqual(pieces("spread", { start: "2025-10-22", end: "2026-10-21", key: "dist", answer: range }), [
    "期間 2025年10月22日〜2026年10月21日",
    "区切りの幅 1 km",
    "数える種目 ランニングの種目すべて（2 つ）",
    "Garmin Running Data Normalizer 2.2.0",
  ]);
  assert.equal(pieces("spread", { start: "2025-10-22", end: "2026-10-21", key: "pace", answer: { first: 6, width: 10, scale: 1000 } }, "en")[1], "Width of a range: 0:10 /km");
  // An output without activities, and no version.
  assert.deepEqual(pieces("plot", { start: "2025-10-22", end: "2026-10-21", types: [], version: null }).slice(1), ["数える種目 アクティビティの記録がありません", "Garmin Running Data Normalizer"]);
});

test("the line after a saving of another view goes with what it shows too, and that of the panels with the key of R1", () => {
  const base = { ticket: "t1", period: "1y", types: null, items: ["dist"], language: "ja" };
  // The panels keep the key of R1, whatever else is given, so that a panel
  // made big keeps the line (the checker's review of the handling of Codex's
  // review of the plan of R2).
  assert.equal(view.saveNoticeKey({ ...base, view: "panels", content: ["x"] }), view.saveNoticeKey(base));
  const compare = { ...base, view: "compare", content: ["dist", "year", [2026, 2025], "rows", null, 24, null] };
  const key = view.saveNoticeKey(compare);
  assert.notEqual(key, view.saveNoticeKey(base));
  assert.equal(view.saveNoticeKey({ ...compare }), key);
  for (const content of [
    ["hr", "year", [2026, 2025], "rows", null, 24, null],
    ["dist", "race", ["r1", "r2"], "rows", null, 24, null],
    ["dist", "year", [2026], "rows", null, 24, null],
    ["dist", "year", [2026, 2025], "calendar", null, 24, null],
    ["dist", "year", [2026, 2025], "rows", 3, 24, null],
    ["dist", "year", [2026, 2025], "rows", null, 12, null],
    ["dist", "year", [2026, 2025], "rows", null, 24, "max"],
  ]) {
    assert.notEqual(view.saveNoticeKey({ ...compare, content }), key, JSON.stringify(content));
  }
  for (const [name, value] of [["ticket", "t2"], ["period", "3y"], ["types", ["running"]], ["language", "en"]]) {
    assert.notEqual(view.saveNoticeKey({ ...compare, [name]: value }), key, name);
  }
  assert.notEqual(view.saveNoticeKey({ ...base, view: "plot", content: ["pace", "hr"] }), view.saveNoticeKey({ ...base, view: "plot", content: ["pace", "cad"] }));
  assert.notEqual(view.saveNoticeKey({ ...base, view: "spread", content: ["pace"] }), view.saveNoticeKey({ ...base, view: "plot", content: ["pace"] }));
});

test("the names of the files in the guides are those that the page gives (stage R3)", () => {
  // Codex's review of the plan of R3: the examples of the section of saving
  // as an image, from the inputs of the tests above, in both guides.
  const names = [view.saveFileName("2025-10-22", "2026-10-21", ["dist", "pace", "hr"]), view.saveViewFileName("compare", { key: "dist", years: [2025, 2018, 2022] })];
  for (const guide of ["gui_guide.md", "gui_guide.ja.md"]) {
    const text = readFileSync(new URL(`../../docs/${guide}`, import.meta.url), "utf8");
    assert.deepEqual([...text.matchAll(/`(garmin-[^`]*\.svg)`/g)].map((match) => match[1]), names, guide);
  }
});

test("a year stood out stays while one panel draws it, and a press on it again puts it back (stage L3 of v2.2.0)", () => {
  // A press stands a year out; on it again, back; on another, that one. A race
  // goes by its own id, apart from a year.
  assert.deepEqual(view.litAfter(null, "year", "2026"), { by: "year", id: "2026" });
  assert.equal(view.litAfter({ by: "year", id: "2026" }, "year", "2026"), null);
  assert.deepEqual(view.litAfter({ by: "year", id: "2026" }, "year", "2025"), { by: "year", id: "2025" });
  assert.deepEqual(view.litAfter({ by: "year", id: "2026" }, "race", "2026"), { by: "race", id: "2026" });
  // The years as compareData makes them: a value, none, the points of its
  // records, and none of them.
  const entry = (id, values, points = null) => ({ id, values, points });
  const data = [entry("2026", [1, null]), entry("2025", [null, null]), entry("2024", [null], [[0, 50]]), entry("2023", [null], [])];
  const lit = { by: "year", id: "2026" };
  const kept = (id, change = {}) => view.litKept({ by: "year", id }, { by: "year", mode: "overlay", table: false, data, ...change });
  assert.deepEqual(kept("2026"), lit);
  assert.deepEqual(kept("2026", { mode: "cumulative" }), lit);
  assert.deepEqual(kept("2024"), { by: "year", id: "2024" });
  // Back where the way, the table, or what it is compared by changed, where
  // the year went (the years, the month, the item), and where it has no shape
  // left to draw (another line compared).
  for (const change of [{ mode: "rows" }, { mode: "calendar" }, { table: true }, { by: "race" }, { data: data.slice(1) }]) {
    assert.equal(kept("2026", change), null, JSON.stringify(change));
  }
  assert.equal(kept("2025"), null);
  assert.equal(kept("2023"), null);
  assert.equal(view.litKept(null, { by: "year", mode: "overlay", table: false, data }), null);
  // What a year draws, which its key and a year kept go by (Codex's review of
  // the diff of L3, 1).
  assert.deepEqual(
    data.map((each) => view.yearDrawn(each)),
    [true, false, true, false],
  );
  // A year of compareData without an answer draws nothing.
  const none = view.compareData({ years: [2026], month: null, grain: "month", mode: "overlay", series: null, answers: new Map(), whole: null });
  assert.equal(view.litKept(lit, { by: "year", mode: "overlay", table: false, data: none }), null);
});
