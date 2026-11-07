// The laps of an activity on the view page (stage X10 of v2.3.0): how the
// page takes the answer of /api/view/laps, and how it counts the summary and
// the rows of the window, as pure functions of view_flow.mjs.
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
  if (typeof message.text === "string") {
    return message.text;
  }
  const params = { ...message.params };
  for (const [name, key] of Object.entries(message.keyParams ?? {})) {
    params[name] = typeof key === "string" ? translate(catalogs, language, key) : words(key, language);
  }
  return translate(catalogs, language, message.key, params);
}

const lap = (kind, timer, distance, heart, cadence = 88, maximum = heart === null ? null : heart + 7) => ({
  kind,
  elapsed_s: timer,
  timer_s: timer,
  distance_m: distance,
  avg_heart_rate: heart,
  max_heart_rate: maximum,
  avg_cadence: cadence,
  avg_speed: timer && distance ? distance / timer : 0,
});

// A run of intervals with rests standing (no distance), as the samples of X10.
const STANDING = [
  lap("warmup", 600, 1700, 130),
  ...Array.from({ length: 4 }, () => [lap("active", 80, 400, 170, 94), lap("rest", 60, 0, 118, null)]).flat(),
  lap("cooldown", 540, 1400, 126),
];

const answerOf = (laps) => ({
  status: "laps",
  laps,
  counts: { laps: laps.length, unknown_kind: laps.filter((one) => one?.kind === "unknown").length },
  read: 3,
  output: {},
});

test("the kinds and the reasons are those of the server", () => {
  assert.deepEqual(view.LAP_KINDS, ["warmup", "active", "interval", "recovery", "rest", "cooldown", "unknown"]);
  assert.equal(view.LAP_REASONS.length, 13);
  assert.deepEqual(view.LAP_REASONS.slice(-2), ["read_stale", "busy"]);
  // The list tells two of them, in the order in which the server looks.
  assert.deepEqual(view.LIST_LAP_REASONS, ["key_shared", "not_from_store"]);
  for (const reason of view.LIST_LAP_REASONS) {
    assert.ok(view.LAP_REASONS.includes(reason));
  }
});

test("an answer of the laps is taken in its form only", () => {
  assert.deepEqual(view.lapsTaken(answerOf(STANDING)), { laps: STANDING });
  assert.deepEqual(view.lapsTaken(answerOf([])), { laps: [] });
  for (const reason of view.LAP_REASONS) {
    assert.deepEqual(view.lapsTaken({ status: "unavailable", reason, read: 3, output: {} }), { reason });
  }
  const bad = [
    null,
    "laps",
    [],
    { status: "unavailable", reason: "elsewhere" },
    { status: "unavailable" },
    { status: "other", laps: [] },
    { ...answerOf(STANDING), laps: "laps" },
    { ...answerOf(STANDING), counts: { laps: STANDING.length + 1, unknown_kind: 0 } },
    { ...answerOf(STANDING), counts: { laps: STANDING.length, unknown_kind: 1 } },
    { ...answerOf(STANDING), counts: null },
    answerOf([{ ...STANDING[0], kind: "other" }]),
    answerOf([{ ...STANDING[0], kind: null }]),
    answerOf([{ ...STANDING[0], timer_s: -1 }]),
    answerOf([{ ...STANDING[0], timer_s: "600" }]),
    answerOf([{ ...STANDING[0], distance_m: Number.NaN }]),
    answerOf([{ ...STANDING[0], max_heart_rate: Number.POSITIVE_INFINITY }]),
    answerOf([{ ...STANDING[0], avg_cadence: true }]),
    answerOf([Object.fromEntries(Object.entries(STANDING[0]).filter(([name]) => name !== "max_heart_rate"))]),
    answerOf([null]),
  ];
  for (const answer of bad) {
    assert.equal(view.lapsTaken(answer), null, JSON.stringify(answer));
  }
});

test("the summary has a row for each kind in the order of a workout, then all the laps", () => {
  const rows = view.lapsSummary(STANDING);
  assert.deepEqual(
    rows.map((row) => [row.kind, row.laps]),
    [
      ["warmup", 1],
      ["active", 4],
      ["rest", 4],
      ["cooldown", 1],
      [null, 10],
    ],
  );
  const [warmup, active, rest, cooldown, all] = rows;
  assert.deepEqual([warmup.time, warmup.distance, warmup.heart], [600, 1700, 130]);
  assert.equal(warmup.pace, 600 / 1700);
  assert.deepEqual([active.time, active.distance, active.pace, active.heart], [320, 1600, 0.2, 170]);
  // The rests standing have no distance: no pace, and their heart rate counts.
  assert.deepEqual([rest.time, rest.distance, rest.pace, rest.heart], [240, 0, null, 118]);
  assert.equal(cooldown.pace, 540 / 1400);
  // All the laps: the time of every lap; the pace of the laps with a distance
  // only (the total time over the total distance); the heart rate weighted by
  // the time of each lap.
  assert.equal(all.time, 600 + 320 + 240 + 540);
  assert.equal(all.distance, 1700 + 1600 + 1400);
  assert.equal(all.pace, (600 + 320 + 540) / (1700 + 1600 + 1400));
  assert.equal(all.heart, (600 * 130 + 320 * 170 + 240 * 118 + 540 * 126) / (600 + 320 + 240 + 540));
});

test("values that the laps do not have are left out, not taken as 0", () => {
  const laps = [lap("active", 300, 1000, null), lap("active", null, 1000, 150), lap("active", 300, null, 160)];
  const [active, all] = view.lapsSummary(laps);
  assert.deepEqual(all, { ...active, kind: null });
  assert.equal(active.time, 600);
  assert.equal(active.distance, 2000);
  // Only the first lap has both a time and a distance; only the last both a
  // time and a heart rate.
  assert.equal(active.pace, 300 / 1000);
  assert.equal(active.heart, 160);
  const none = view.lapsSummary([lap("unknown", null, null, null)]);
  assert.deepEqual(none[0], { kind: "unknown", laps: 1, time: null, distance: null, pace: null, heart: null });
  assert.deepEqual(view.lapsSummary([]), [{ kind: null, laps: 0, time: null, distance: null, pace: null, heart: null }]);
});

test("the rows of the laps, with the cadence of a running activity", () => {
  const rows = view.lapRows(STANDING.slice(0, 3), 2);
  assert.deepEqual(rows[0], { number: 1, kind: "warmup", time: 600, distance: 1700, pace: 600 / 1700, heart: 130, max: 137, cadence: 176 });
  assert.deepEqual(rows[1], { number: 2, kind: "active", time: 80, distance: 400, pace: 0.2, heart: 170, max: 177, cadence: 188 });
  // A rest standing: no pace; a lap without a cadence has none.
  assert.deepEqual(rows[2], { number: 3, kind: "rest", time: 60, distance: 0, pace: null, heart: 118, max: 125, cadence: null });
  // No cadence for an activity that is not of a running type.
  assert.ok(view.lapRows(STANDING, null).every((row) => row.cadence === null));
  assert.deepEqual(view.lapRows([], 2), []);
});

test("the notes under the summary", () => {
  assert.deepEqual(view.lapsNotes(STANDING), { unknown: 0, unpaced: 4, one: null });
  const plain = Array.from({ length: 10 }, () => lap("active", 300, 1000, 150));
  assert.deepEqual(view.lapsNotes(plain), { unknown: 0, unpaced: 0, one: "active" });
  // One lap is not said to be of one kind; laps of no known kind are counted.
  assert.deepEqual(view.lapsNotes([lap("active", 3000, 10000, 150)]), { unknown: 0, unpaced: 0, one: null });
  assert.deepEqual(view.lapsNotes([lap("unknown", 300, 1000, 150), lap("unknown", 300, null, 150)]), { unknown: 2, unpaced: 1, one: null });
});

test("the lines under the summary say the counts with their words for one", () => {
  assert.deepEqual(view.lapsNoteMessages(STANDING, "en"), [{ key: "view.laps.no_distance", params: { n: "4" }, keyParams: {} }]);
  assert.deepEqual(view.lapsNoteMessages([lap("active", 300, 1000, 150), lap("rest", 60, 0, 120)], "en"), [
    { key: "view.laps.no_distance_one", params: { n: "1" }, keyParams: {} },
  ]);
  const plain = Array.from({ length: 3 }, () => lap("interval", 300, 1000, 150));
  assert.deepEqual(view.lapsNoteMessages(plain, "ja"), [
    { key: "view.laps.one_kind", params: {}, keyParams: { kind: { key: "view.laps.kind.interval", params: {}, keyParams: {} } } },
  ]);
  const unknown = [...Array.from({ length: 1200 }, () => lap("unknown", 60, 200, 140)), lap("active", 60, 200, 150)];
  assert.deepEqual(view.lapsNoteMessages(unknown, "en"), [{ key: "view.laps.unknown_note", params: { n: "1,200" }, keyParams: {} }]);
  assert.deepEqual(view.lapsNoteMessages([lap("unknown", 60, 200, 140), lap("active", 60, 200, 150)], "en"), [
    { key: "view.laps.unknown_note_one", params: { n: "1" }, keyParams: {} },
  ]);
  assert.deepEqual(view.lapsNoteMessages([], "en"), []);
  // The heads of the tables are words of keys of their own.
  assert.deepEqual(Object.keys(view.LAP_HEAD_KEYS), ["kind", "laps", "number", "time", "distance", "avg_pace", "pace", "heart", "max", "cadence"]);
  assert.deepEqual(Object.keys(view.LAP_KIND_KEYS), view.LAP_KINDS);
  assert.deepEqual(Object.keys(view.LAP_REASON_KEYS), view.LAP_REASONS.filter((reason) => reason !== "read_stale"));
  assert.equal(view.LAP_CADENCE_FACTOR, 2);
});

test("the values of the laps as the window writes them", () => {
  assert.equal(view.lapText("time", 84, "ja"), "1:24");
  assert.equal(view.lapText("time", 3727, "en"), "1:02:07");
  assert.equal(view.lapText("pace", 0.2, "ja"), "3:20");
  assert.equal(view.lapText("pace", 600 / 1700, "en"), "5:53");
  assert.equal(view.lapText("distance", 400, "ja"), "0.40 km");
  assert.equal(view.lapText("distance", 12345, "en"), "12.35 km");
  assert.equal(view.lapText("heart", 142.6, "ja"), "143");
  assert.equal(view.lapText("cadence", 176, "en"), "176");
  for (const value of [null, undefined, Number.NaN, Number.POSITIVE_INFINITY]) {
    assert.equal(view.lapText("time", value, "ja"), null);
  }
});

test("the page writes the cadence in steps a minute, twice the value of one foot that Garmin records", () => {
  // The person's choice (「1 歩数にそろえる」): everywhere on the page, through
  // the factor of the item; the server's values stay as recorded.
  assert.deepEqual(view.ITEM_FORMATS.cad, { unit: "spm", factor: 2, digits: 0 });
  assert.equal(view.shown("cad", 85.5), 171);
  assert.equal(view.listValueText("cad", 85.5, "ja"), "171");
  assert.equal(words(view.valueMessage("cad", 85.5, "ja"), "ja"), "171 歩/分");
  assert.equal(words(view.valueMessage("cad", 85.5, "en"), "en"), "171 spm");
  assert.equal(words(view.recapDifference("cad", 85.5, 85.0, "ja"), "ja"), "+1 歩/分");
  assert.equal(words(view.recapDifference("cad", 85.5, 85.0, "en"), "en"), "+1 spm");
  assert.equal(words(view.listHead("cad"), "ja"), "ピッチ 歩/分");
  const answer = { first: 16, width: 5, scale: 1, counts: [1], limit: 200, widened: false };
  assert.equal(words(view.spreadRange("cad", answer, 0, "ja"), "ja"), "160〜170 歩/分");
  assert.equal(words(view.spreadRange("cad", answer, 0, "en"), "en"), "160–170 spm");
  // The laps of a running activity: the cadence of the FIT file, of one foot,
  // doubled the same way, so that a lap and the list agree.
  assert.equal(view.lapText("cadence", view.lapRows([lap("active", 300, 1000, 150, 85.5)], view.LAP_CADENCE_FACTOR)[0].cadence, "ja"), "171");
});
