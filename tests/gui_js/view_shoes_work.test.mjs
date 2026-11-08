// The work laps of the shoes on the view page (stage X11 of v2.3.0): how the
// page takes the answers of /api/view/shoes/work, adds their sums up, and
// writes the table and the lines of the work laps, as pure functions of
// view_flow.mjs.
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

const lap = (kind, timer, distance, heart) => ({ kind, elapsed_s: timer, timer_s: timer, distance_m: distance, avg_heart_rate: heart, max_heart_rate: heart, avg_cadence: null, avg_speed: null });

// The sums of the work laps of activities, as gui/shoe_work.py adds them
// (its _add): the server's rule, written again to hold the page's, in whole
// milliseconds and centimetres (Codex's eighth read of the diff of X11).
const ms = (seconds) => Math.round(seconds * 1000);
const cm = (metres) => Math.round(metres * 100);

function sums(activities) {
  const total = view.workEmpty();
  for (const laps of activities) {
    if (!laps.length) {
      total.not_counted.no_laps = (total.not_counted.no_laps ?? 0) + 1;
      continue;
    }
    const work = laps.filter((one) => one.kind === "active" || one.kind === "interval");
    const unknown = laps.filter((one) => one.kind === "unknown").length;
    if (!work.length) {
      if (unknown) {
        total.not_counted.unknown_kinds = (total.not_counted.unknown_kinds ?? 0) + 1;
      } else {
        total.counted += 1;
        total.no_work += 1;
      }
      continue;
    }
    total.counted += 1;
    if (unknown) {
      total.unknown_left += 1;
      total.unknown_laps += unknown;
    }
    const timed = work.filter((one) => one.timer_s !== null);
    const measured = work.filter((one) => one.distance_m !== null);
    const paced = work.filter((one) => one.timer_s !== null && one.distance_m !== null && cm(one.distance_m) > 0);
    const hearts = work.filter((one) => one.timer_s !== null && ms(one.timer_s) > 0 && one.avg_heart_rate !== null);
    total.laps += work.length;
    total.time_ms += timed.reduce((sum, one) => sum + ms(one.timer_s), 0);
    total.time_laps += timed.length;
    total.distance_cm += measured.reduce((sum, one) => sum + cm(one.distance_m), 0);
    total.distance_laps += measured.length;
    total.paced_time_ms += paced.reduce((sum, one) => sum + ms(one.timer_s), 0);
    total.paced_distance_cm += paced.reduce((sum, one) => sum + cm(one.distance_m), 0);
    total.heart_bpm_ms += hearts.reduce((sum, one) => sum + Math.round(one.avg_heart_rate) * ms(one.timer_s), 0);
    total.heart_time_ms += hearts.reduce((sum, one) => sum + ms(one.timer_s), 0);
    if (!paced.length) {
      total.no_pace += 1;
    }
  }
  return total;
}

const ACTIVITIES = [
  [lap("warmup", 600, 1500, 130), lap("interval", 80, 400, 170), lap("recovery", 90, 200, 140), lap("interval", 82, 400, 172), lap("cooldown", 500, 1400, 128)],
  [lap("active", 300, 1000, 150), lap("active", 310, 1000, null), lap("unknown", 300, 1000, 149)],
  [lap("interval", 60, 0, 165), lap("rest", 60, 0, 120)],
  [lap("rest", 60, 0, 118)],
  [lap("unknown", 300, 1000, 140)],
  [],
];

test("the values of the sums are those of the window of the laps", () => {
  const total = sums(ACTIVITIES);
  const values = view.workValues(total);
  // lapTotals of the work laps of the counted activities, as the window counts them.
  const work = ACTIVITIES.flatMap((laps) => (laps.some((one) => one.kind === "active" || one.kind === "interval") ? laps.filter((one) => one.kind === "active" || one.kind === "interval") : []));
  const all = view.lapsSummary(work).at(-1);
  assert.equal(values.distance, all.distance);
  assert.equal(values.time, all.time);
  // Of the whole numbers: the same value but for the last bits.
  assert.ok(Math.abs(values.pace - all.pace) < 1e-12, `${values.pace} ${all.pace}`);
  assert.ok(Math.abs(values.heart - all.heart) < 1e-9, `${values.heart} ${all.heart}`);
  for (const name of view.WORK_SUMS) {
    assert.ok(Number.isSafeInteger(total[name]), name);
  }
  assert.equal(values.counted, 4);
  assert.equal(values.notCounted, 2);
  assert.deepEqual(total.not_counted, { unknown_kinds: 1, no_laps: 1 });
  assert.equal(total.no_work, 1);
  assert.equal(total.unknown_left, 1);
  assert.equal(total.unknown_laps, 1);
  assert.equal(total.no_pace, 1);
});

test("the sums of the requests add up to those of one", () => {
  const whole = sums(ACTIVITIES);
  const parts = [ACTIVITIES.slice(0, 2), ACTIVITIES.slice(2, 3), ACTIVITIES.slice(3)].map(sums);
  const added = parts.reduce((total, part) => view.workAdd(total, part), view.workEmpty());
  assert.deepEqual(view.workValues(added), view.workValues(whole));
  assert.deepEqual(added.not_counted, whole.not_counted);
  for (const name of [...view.WORK_SUMS, ...view.WORK_RUN_COUNTS]) {
    assert.equal(added[name], whole[name], name);
  }
  // Sums past the whole numbers that a number holds exactly: none (Codex's
  // ninth read of the diff of X11).
  assert.equal(view.workAdd({ ...view.workEmpty(), laps: Number.MAX_SAFE_INTEGER }, { ...view.workEmpty(), laps: 1 }), null);
  assert.equal(view.workAdd({ ...view.workEmpty(), not_counted: { no_laps: Number.MAX_SAFE_INTEGER } }, { ...view.workEmpty(), not_counted: { no_laps: 1 } }), null);
  // A reason in two requests adds up (the guard of X11, FW6).
  const twice = view.workAdd(view.workAdd(view.workEmpty(), whole), whole);
  assert.deepEqual(twice.not_counted, { unknown_kinds: 2, no_laps: 2 });
  // Nothing at all: none of the values.
  assert.deepEqual(view.workValues(view.workEmpty()), { distance: null, time: null, pace: null, heart: null, counted: 0, notCounted: 0 });
});

test("the values do not depend on where the requests end", () => {
  // Codex's eighth read of the diff of X11: 100 activities of a lap of
  // 300.6 s and 1,200 m, as one request and as two of 50; in seconds and
  // metres the sums differed in their last bits, and the average pace by a
  // second.
  const many = Array.from({ length: 100 }, () => [lap("interval", 300.6, 1200, 150)]);
  const whole = sums(many);
  const added = [many.slice(0, 50), many.slice(50)].map(sums).reduce((total, part) => view.workAdd(total, part), view.workEmpty());
  assert.deepEqual(added, whole);
  assert.equal(whole.paced_time_ms, 30060000);
  assert.equal(view.lapText("pace", view.workValues(added).pace, "ja"), view.lapText("pace", view.workValues(whole).pace, "ja"));
  assert.equal(view.lapText("pace", view.workValues(whole).pace, "en"), view.lapText("pace", 300.6 / 1200, "en"));
});

const answer = (fields = {}) => ({
  status: "work",
  runs: 5,
  from: 0,
  next: 3,
  pairs: [sums(ACTIVITIES.slice(0, 2)), sums(ACTIVITIES.slice(2, 3))],
  counts: { ...sums(ACTIVITIES.slice(0, 3)), two_pairs: 0 },
  read: 4,
  output: {},
  ...fields,
});

test("an answer of the work laps is taken as the page takes it", () => {
  const taken = view.workTaken(answer(), 2);
  assert.equal(taken.runs, 5);
  assert.equal(taken.next, 3);
  assert.equal(taken.pairs.length, 2);
  assert.deepEqual(view.workTaken(answer({ next: null }), 2).next, null);
  for (const reason of view.WORK_UNAVAILABLE) {
    assert.deepEqual(view.workTaken({ status: "unavailable", reason }, 2), { reason });
  }
  // Answers of another form: a stop.
  const bad = [
    null,
    { status: "unavailable", reason: "another" },
    answer({ status: "laps" }),
    answer({ runs: -1 }),
    answer({ from: 1.5 }),
    answer({ next: 0 }),
    answer({ next: 5 }),
    answer({ pairs: [sums(ACTIVITIES)] }),
    answer({ pairs: [{ ...sums(ACTIVITIES), laps: -1 }, sums([])] }),
    answer({ pairs: [{ ...sums(ACTIVITIES), counted: 1.5 }, sums([])] }),
    answer({ pairs: [{ ...sums(ACTIVITIES), not_counted: { another: 1 } }, sums([])] }),
    answer({ pairs: [{ ...sums(ACTIVITIES), time_ms: Number.NaN }, sums([])] }),
    answer({ pairs: [{ ...sums(ACTIVITIES), distance_cm: 2.5 }, sums([])] }),
    answer({ counts: sums(ACTIVITIES) }),
  ];
  for (const one of bad) {
    assert.equal(view.workTaken(one, 2), null, JSON.stringify(one)?.slice(0, 80));
  }
});

const shoesAnswer = {
  shoes: [
    { name: "Made-up road", day: "2025-01-01", number: null },
    { name: "", day: null, number: 2 },
  ],
  work: { runs: 5, known: 1, limit: 5000, reason: null },
};

test("the table of the work laps has a row a pair, in the order of the view", () => {
  // The sums of each pair, as the page keeps them (its counting's sums).
  const { heads, rows } = view.shoesWorkTable(shoesAnswer, [sums(ACTIVITIES.slice(0, 2)), sums([[lap("rest", 60, 0, 118)]])], "ja");
  assert.deepEqual(heads.map((head) => words(head)), ["靴", "疾走区間の距離", "時間", "平均ペース", "平均心拍", "数えたラン", "数えられなかったラン"]);
  assert.equal(rows.length, 2);
  assert.equal(words(rows[0][0]), "Made-up road（使い始め 2025年1月1日）");
  assert.equal(words(rows[0][1]), "2.8 km");
  assert.equal(words(rows[0][5]), "2");
  assert.equal(words(rows[0][6]), "0");
  // A pair with no work lap: no values, and its activity counted.
  assert.deepEqual(rows[1].slice(1, 5).map((cell) => words(cell)), ["—", "—", "—", "—"]);
  assert.equal(words(rows[1][5]), "1");
  assert.deepEqual(heads.map((head) => words(head, "en")), ["Shoes", "Work distance", "Time", "Avg pace", "Avg HR", "Runs counted", "Not counted"]);
});

test("the lines of the work laps say the counts and why, in the order of the reasons", () => {
  const counts = { ...sums(ACTIVITIES), two_pairs: 2, not_counted: { no_laps: 1, fit_missing: 2, unknown_kinds: 1 } };
  const lines = view.shoesWorkLines(counts);
  assert.equal(words(lines.shown), "いちばん上の表は、疾走区間（ラン・インターバル）だけの値です。その下の 2 つの表は、今までどおりです。");
  assert.equal(lines.counted.key, "view.shoes.work.counted");
  assert.deepEqual(lines.counted.params, { n: 4, m: 4 });
  assert.deepEqual(lines.counted.reasons.map((reason) => words(reason)), ["区間の種類が分からない 1", "ラップが無い 1", "FIT が無い 2"]);
  assert.deepEqual(lines.counted.reasons.map((reason) => words(reason, "en")), ["laps of unknown kind: 1", "no laps: 1", "no FIT file: 2"]);
  assert.deepEqual(lines.more.map((line) => line.key), [
    "view.shoes.work.unknown_left",
    "view.shoes.work.no_work",
    "view.shoes.work.no_pace",
    "view.shoes.work.two_pairs",
    "view.shoes.work.all_work",
    "view.shoes.work.not_drawn",
    "view.shoes.work.kinds",
  ]);
  const all = view.shoesWorkLines({ ...view.workEmpty([...view.WORK_SUMS, ...view.WORK_RUN_COUNTS, "two_pairs"]), counted: 3 });
  assert.equal(all.counted.key, "view.shoes.work.counted_all");
  assert.deepEqual(all.counted.reasons, []);
  assert.deepEqual(all.more.map((line) => line.key), ["view.shoes.work.all_work", "view.shoes.work.not_drawn", "view.shoes.work.kinds"]);
});

test("what the bar says before it reads, or why it cannot", () => {
  assert.equal(words(view.shoesWorkBefore(shoesAnswer.work).line), "読む候補のラン 4 回（先に分かる読めないラン 1 回を除く）の FIT を、保管場所から読みます。時間がかかることがあります。");
  assert.equal(words(view.shoesWorkBefore({ ...shoesAnswer.work, known: 0 }).line), "読む候補のラン 5 回の FIT を、保管場所から読みます。時間がかかることがあります。");
  assert.deepEqual(view.shoesWorkBefore({ ...shoesAnswer.work, reason: "not_from_store" }), { why: "view.shoes.work.whole.not_from_store" });
  assert.deepEqual(view.shoesWorkBefore({ ...shoesAnswer.work, runs: 5001 }), { why: "view.shoes.work.whole.too_many", params: { n: 5001, max: 5000 } });
  // As many as the limit are read.
  assert.equal(view.shoesWorkBefore({ ...shoesAnswer.work, runs: 5000 }).line.params.n, 4999);
  assert.deepEqual(view.shoesWorkBefore({ ...shoesAnswer.work, runs: 1, known: 1 }), { why: "view.shoes.work.none" });
  assert.deepEqual(view.shoesWorkBefore(undefined), { why: "view.shoes.work.none" });
  assert.deepEqual(view.shoesWorkBefore({ runs: "5", known: 0, limit: 5000 }), { why: "view.shoes.work.none" });
});

test("every reason has its words in both languages", () => {
  assert.deepEqual(Object.keys(view.WORK_REASON_KEYS), view.WORK_NOT_COUNTED);
  assert.deepEqual(Object.keys(view.WORK_WHOLE_KEYS), view.WORK_UNAVAILABLE);
  for (const key of [...Object.values(view.WORK_REASON_KEYS), ...Object.values(view.WORK_WHOLE_KEYS)]) {
    for (const language of ["ja", "en"]) {
      assert.ok(Object.hasOwn(catalogs[language], key), `${language} ${key}`);
    }
  }
});
