// view_chart.mjs (stage G3b): the shapes of the charts of the view page, as the
// data of SVG paths: the time scale, the scale of the values and its ticks,
// bars, lines broken where a period has no value, the dots of 0, the points
// of the records, and the time axis.
import assert from "node:assert/strict";
import { test } from "node:test";

import * as chart from "../../src/garmin_running_data_normalizer/gui/static/view_chart.mjs";

const day = (iso) => chart.dayNumber(iso);

// Months of a year as the server gives them, as counts of days.
function months(year, count, { cutFirst = false, cutLast = false } = {}) {
  const periods = [];
  for (let month = 0; month < count; month += 1) {
    const start = Math.round(Date.UTC(year, month, 1) / 86400000);
    const end = Math.round(Date.UTC(year, month + 1, 1) / 86400000) - 1;
    periods.push({ start, end, partial: (cutFirst && month === 0) || (cutLast && month === count - 1) });
  }
  return periods;
}

test("days are counted from 1970 and back", () => {
  assert.equal(day("1970-01-01"), 0);
  assert.equal(day("2026-10-26") - day("2026-10-01"), 25);
  assert.equal(chart.isoDate(day("2024-02-29")), "2024-02-29");
  assert.deepEqual(chart.periodDays([{ start: "2026-01-01", end: "2026-01-31", partial: true }]), [
    { start: day("2026-01-01"), end: day("2026-01-31"), partial: true },
  ]);
});

test("the time scale gives each period its days, and finds the period nearest to a point", () => {
  const periods = months(2026, 3);
  const scale = chart.timeScale(periods[0].start, periods[2].end, 58, 958);
  assert.equal(scale.x(periods[0].start), 58);
  assert.equal(scale.x(periods[2].end + 1), 958);
  assert.equal(Math.round(scale.day(958)), periods[2].end + 1);
  const middles = periods.map((period) => chart.periodMiddle(scale, period));
  assert.ok(middles[0] < middles[1] && middles[1] < middles[2]);
  assert.equal(chart.nearestPeriod(periods, scale, 0), 0);
  assert.equal(chart.nearestPeriod(periods, scale, middles[1] + 1), 1);
  assert.equal(chart.nearestPeriod(periods, scale, 5000), 2);
  assert.equal(chart.nearestPeriod([], scale, 10), null);
});

test("the scale of values goes out to whole steps, from 0 for a total", () => {
  assert.equal(chart.niceStep(10, 3), 5);
  assert.equal(chart.niceStep(0.9, 3), 0.2);
  assert.equal(chart.niceStep(0, 3), 1);
  // Steps of a clock for minutes and seconds.
  assert.equal(chart.niceStep(240, 3, "minute"), 60);
  assert.equal(chart.niceStep(100, 3, "second"), 30);
  const total = chart.valueScale(12, 227.7, { fromZero: true, count: 3 });
  assert.equal(total.lo, 0);
  assert.ok(total.hi >= 227.7 * 1.04);
  assert.deepEqual(total.ticks, [0, 100, 200, 300]);
  const mean = chart.valueScale(46.4, 55.1, { count: 3 });
  assert.ok(mean.lo <= 46.4 && mean.hi >= 55.1);
  assert.ok(mean.ticks.length >= 2);
  // One value only, and nothing above 0.
  assert.deepEqual(chart.valueScale(50, 50, { count: 3 }).ticks.length >= 2, true);
  assert.deepEqual(chart.valueScale(0, 0, { fromZero: true, count: 2 }), { lo: 0, hi: 1, ticks: [0, 0.5, 1] });
  assert.equal(chart.tickCount(60), 2);
  assert.equal(chart.tickCount(150), 3);
  assert.equal(chart.tickCount(300), 5);
  // Ticks closer than 16 px are thinned, keeping two at least.
  assert.deepEqual(chart.thinTicks([0, 1, 2, 3, 4], (value) => value * 10), [0, 2, 4]);
  assert.deepEqual(chart.thinTicks([0, 1], (value) => value), [0, 1]);
});

test("panels of the same unit share one scale only when asked, and only two or more", () => {
  const panels = [
    { key: "hr", unitGroup: "bpm", extent: [140, 160] },
    { key: "rhr", unitGroup: "bpm", extent: [45, 55] },
    { key: "deep", unitGroup: "sleepst", extent: [60, 90] },
    // Items without a unit group never share a scale, also when two are shown.
    { key: "dist", unitGroup: null, extent: [0, 200] },
    { key: "steps", unitGroup: null, extent: [5000, 15000] },
  ];
  assert.equal(chart.sharedExtents(panels, false).size, 0);
  const shared = chart.sharedExtents(panels, true);
  assert.deepEqual([...shared.entries()], [
    ["hr", [45, 160]],
    ["rhr", [45, 160]],
  ]);
  assert.deepEqual(chart.extent([{ values: [null, 3, 1] }, { values: [], points: [[0, 7]] }]), [1, 7]);
  assert.equal(chart.extent([{ values: [null] }]), null);
});

test("bars of a total: at most 24 px wide with a gap, round at the end of the data, the cut periods apart", () => {
  const periods = months(2026, 4, { cutLast: true });
  const scale = chart.timeScale(periods[0].start, periods[3].end, 0, 400);
  const y = (value) => 100 - value;
  const { full, partial } = chart.barPaths([50, 0, null, 30], periods, scale, y, 100);
  const bars = full.split("Z").filter(Boolean);
  assert.equal(bars.length, 1);
  assert.equal(partial.split("Z").filter(Boolean).length, 1);
  // The first bar: from the baseline at 100 up to 50, 24 px wide, round at
  // its top by 4 px.
  const shape = bars[0].match(/^M([\d.]+) 100V54Q[\d.]+ 50 [\d.]+ 50H[\d.]+Q([\d.]+) 50 [\d.]+ 54V100$/);
  assert.ok(shape, bars[0]);
  assert.equal(Math.round(Number(shape[2]) - Number(shape[1])), 24);
  // Narrow periods: one pixel at least, with a gap of 2 px.
  const many = months(2026, 12);
  const narrow = chart.timeScale(many[0].start, many[11].end, 0, 36);
  const thin = chart.barPaths(Array(12).fill(5), many, narrow, y, 100).full.split("Z").filter(Boolean);
  assert.equal(thin.length, 12);
  // Dots of 0 sit on the baseline, as wide as a period allows.
  assert.equal((chart.zeroPath([50, 0, null, 0], periods, scale, 100).match(/M/g) ?? []).length, 2);
  assert.equal(chart.zeroPath([50, null], periods, scale, 100), "");
});

test("a line is broken where a period has no value, and for a total where it is 0", () => {
  const periods = months(2026, 6);
  const scale = chart.timeScale(periods[0].start, periods[5].end, 0, 600);
  const y = (value) => 100 - value;
  const drawn = chart.linePath([10, 20, null, 30, null, 40], periods, scale, y);
  assert.equal((drawn.path.match(/M/g) ?? []).length, 3);
  assert.equal((drawn.path.match(/L/g) ?? []).length, 1);
  // The points between two breaks stand alone.
  assert.equal(drawn.alone.length, 2);
  const total = chart.linePath([10, 0, 30, 0, 50, 60], periods, scale, y, { breakAtZero: true });
  assert.equal((total.path.match(/M/g) ?? []).length, 3);
  assert.equal(total.alone.length, 2);
  // Points are dots of a stroke with round caps.
  assert.equal(chart.dotsPath([[1, 2], [3.04, 4]]), "M1 2h0.01M3 4h0.01");
});

test("a panel draws bars, a line, or points, with ticks and a baseline for a total", () => {
  const periods = months(2026, 12);
  const base = { periods, start: periods[0].start, end: periods[11].end, width: 1000, height: 160 };
  const bars = chart.panelShapes({ ...base, total: true, lines: [{ values: Array(12).fill(1000) }] });
  assert.ok(bars.lines[0].bars.full);
  assert.equal(bars.lines[0].line, null);
  assert.ok(bars.base !== null);
  assert.ok(bars.ticks.length >= 2);
  assert.equal(bars.ticks[0].value, 0);
  // A short line has markers; a long one does not.
  const line = chart.panelShapes({ ...base, lines: [{ values: [1, 2, 3, null, 5, 6, 7, 8, 9, 10, 11, 12] }] });
  assert.equal(line.lines[0].bars, null);
  assert.ok(line.lines[0].line.startsWith("M"));
  assert.ok(line.lines[0].markers);
  assert.equal(line.base, null);
  // The records of each day are points: markers up to 500, dots above.
  const few = chart.panelShapes({ ...base, lines: [{ values: Array(12).fill(null), points: [[0, 5], [0, 6], [3, 7]] }] });
  assert.equal(few.lines[0].pointRadius, chart.MARKER_RADIUS);
  assert.equal((few.lines[0].points.match(/M/g) ?? []).length, 3);
  const points = Array.from({ length: 600 }, (_value, index) => [index % 12, index]);
  assert.equal(chart.panelShapes({ ...base, lines: [{ values: Array(12).fill(null), points }] }).lines[0].pointRadius, 1.6);
  // A total of more than 220 periods is a line, broken at 0, with its dots.
  const days = Array.from({ length: 300 }, (_value, index) => ({ start: index, end: index, partial: false }));
  const daily = chart.panelShapes({ periods: days, start: 0, end: 299, width: 1000, height: 160, total: true, lines: [{ values: days.map((_period, index) => (index % 3 ? 0 : 5)) }] });
  assert.equal(daily.lines[0].bars, null);
  assert.ok(daily.lines[0].zero);
  // Nothing to draw, and a scale shared with other panels.
  assert.equal(chart.panelShapes({ ...base, lines: [{ values: Array(12).fill(null) }] }).empty, true);
  const shared = chart.panelShapes({ ...base, lines: [{ values: Array(12).fill(50) }], shared: [0, 200] });
  assert.ok(shared.ticks[shared.ticks.length - 1].value >= 200);
});

test("the time axis marks years, months, or Mondays by the span", () => {
  const start = day("2011-04-01");
  const end = day("2026-10-21");
  const years = chart.timeTicks(start, end, 1400);
  assert.deepEqual(years.slice(0, 2).map((tick) => [chart.isoDate(tick.day), tick.kind]), [
    ["2012-01-01", "year"],
    ["2013-01-01", "year"],
  ]);
  // Every other year where they would crowd.
  const crowded = chart.timeTicks(start, end, 500);
  assert.ok(crowded.every((tick) => new Date(tick.day * 86400000).getUTCFullYear() % 2 === 0));
  const monthsTicks = chart.timeTicks(day("2025-11-15"), day("2026-10-21"), 1400);
  assert.deepEqual(monthsTicks.slice(0, 3).map((tick) => [chart.isoDate(tick.day), tick.kind]), [
    ["2025-12-01", "month_year"],
    ["2026-01-01", "month_year"],
    ["2026-02-01", "month"],
  ]);
  const mondays = chart.timeTicks(day("2026-10-01"), day("2026-10-21"), 1400);
  assert.deepEqual(mondays.map((tick) => chart.isoDate(tick.day)), ["2026-10-05", "2026-10-12", "2026-10-19"]);
});

test("the overview draws the whole output and frames the period shown", () => {
  const periods = months(2026, 12);
  const shapes = chart.overviewShapes({
    values: Array(12).fill(10),
    periods,
    width: 1200,
    height: 44,
    total: true,
    start: periods[3].start,
    end: periods[5].end,
  });
  assert.equal((shapes.marks.match(/Z/g) ?? []).length, 12);
  const scale = chart.timeScale(periods[0].start, periods[11].end, 0, 1200);
  assert.equal(shapes.frame.from, scale.x(periods[3].start));
  assert.equal(shapes.frame.to, scale.x(periods[5].end + 1));
  const line = chart.overviewShapes({ values: [1, null, 3], periods: periods.slice(0, 3), width: 300, height: 44, start: periods[0].start, end: periods[2].end });
  assert.equal((line.marks.match(/M/g) ?? []).length, 2);
});

test("years laid over one another are lines, and a running total is a line from 0 that 0 does not break", () => {
  // Stage L1 of v2.2.0: the places of the shared axis of a comparison.
  const slots = Array.from({ length: 12 }, (_value, index) => ({ start: index, end: index, partial: false }));
  const base = { periods: slots, start: 0, end: 11, width: 1000, height: 160, total: true };
  const values = [100, 0, 50, 0, 0, 80, 90, 0, 70, 60, 50, 40];
  // A total laid over the other years: a line, broken at 0, with its dots.
  const over = chart.panelShapes({ ...base, lineOnly: true, lines: [{ values }] });
  assert.equal(over.lines[0].bars, null);
  assert.equal((over.lines[0].line.match(/M/g) ?? []).length, 4);
  assert.ok(over.lines[0].zero);
  assert.equal(over.ticks[0].value, 0);
  // A running total: one line from 0, never broken at 0, without dots of 0.
  const running = chart.panelShapes({ ...base, running: true, lines: [{ values: [0, 0, 5, 5, null, 9] }], periods: slots.slice(0, 6), end: 5 });
  assert.equal(running.lines[0].bars, null);
  assert.equal(running.lines[0].zero, "");
  assert.equal((running.lines[0].line.match(/M/g) ?? []).length, 2);
  assert.ok(running.base !== null);
  assert.equal(running.ticks[0].value, 0);
  // The marks of 2.1.0 stay: bars for a total of twelve periods.
  assert.ok(chart.panelShapes({ ...base, lines: [{ values }] }).lines[0].bars.full);
});

test("the names at the ends of the lines move apart and stay in the plot", () => {
  // Each at the end of its line where there is room.
  assert.deepEqual(chart.labelPlaces([10, 50, 90], 13, 200), [10, 50, 90]);
  // Two that meet: the lower moves down; the order of the lines stays.
  assert.deepEqual(chart.labelPlaces([50, 45, 100], 13, 200), [58, 45, 100]);
  // At the bottom of the plot, they move up again.
  assert.deepEqual(chart.labelPlaces([195, 198, 199], 13, 200), [174, 187, 200]);
  assert.deepEqual(chart.labelPlaces([], 13, 200), []);
});

// v2.2.0 M1: the marks of the person on a chart.
const mark = (id, dayOf, end = null, kind = "race", name = `Made-up ${id}`) => ({ id, kind, name, day: dayOf, end });

test("a mark of one day is a line in the middle of its day, and a span a band of its days", () => {
  const start = day("2030-03-01");
  const end = day("2030-03-31");
  const scale = chart.timeScale(start, end, 58, 558);
  const shapes = chart.markShapes(
    [mark("a", "2030-03-10"), mark("b", "2030-03-20", "2030-03-22", "injury"), mark("c", "2030-04-01"), mark("d", "2030-02-28")],
    start,
    end,
    58,
    558,
  );
  assert.deepEqual(shapes.map((shape) => shape.mark.id), ["a", "b"]);
  // The middle of the day, where the value of a day is drawn.
  assert.equal(shapes[0].x, scale.x(day("2030-03-10") + 0.5));
  assert.equal(shapes[0].band, null);
  // From the start of its first day to the end of its last.
  assert.equal(shapes[1].x, scale.x(day("2030-03-20")));
  const width = scale.x(day("2030-03-23")) - scale.x(day("2030-03-20"));
  assert.deepEqual(shapes[1].band, { from: shapes[1].x, width, end: scale.x(day("2030-03-23")), starts: true, ends: true });
});

test("a span that goes on beyond the days shown is cut, without its edge there", () => {
  const start = day("2030-03-01");
  const end = day("2030-03-31");
  const scale = chart.timeScale(start, end, 0, 310);
  const [before, after, around] = chart.markShapes(
    [mark("a", "2030-02-20", "2030-03-05", "injury"), mark("b", "2030-03-28", "2030-04-10", "other"), mark("c", "2030-01-01", "2030-12-31", "shoes")],
    start,
    end,
    0,
    310,
  );
  assert.deepEqual([before.x, before.band.starts, before.band.ends], [0, false, true]);
  assert.equal(before.band.width, scale.x(day("2030-03-06")));
  assert.equal(before.band.end, scale.x(day("2030-03-06")));
  assert.deepEqual([after.band.starts, after.band.ends], [true, false]);
  assert.equal(after.band.end, 310);
  assert.deepEqual([around.x, around.band.width, around.band.starts, around.band.ends], [0, 310, false, false]);
  // A band stays visible when its days are narrow, 2 px wide, but its last
  // edge stays at the end of its last day (the review by Codex).
  const long = chart.timeScale(start, end + 3650, 0, 100);
  const [narrow] = chart.markShapes([mark("e", "2030-03-02", "2030-03-03")], start, end + 3650, 0, 100);
  assert.equal(narrow.band.width, 2);
  assert.equal(narrow.band.end, long.x(day("2030-03-04")));
  assert.ok(narrow.band.end < narrow.x + 2);
  // A narrow band at the right end stays inside the chart.
  const [last] = chart.markShapes([mark("f", "2030-03-30", "2030-03-31")], start - 3650, end, 0, 100);
  assert.ok(last.band.from + last.band.width <= 100);
  assert.equal(last.band.from, 98);
});

test("names that would meet show how many marks they are, and the others keep their names", () => {
  const measure = (text) => text.length * 6;
  const crowded = (n) => `${n} marks`;
  const shapes = [
    { mark: mark("a", "2030-01-01", null, "race", "Spring"), x: 100 },
    { mark: mark("b", "2030-01-02", null, "shoes", "Shoes"), x: 110 },
    { mark: mark("c", "2030-01-03", null, "other", "Camp"), x: 300 },
  ];
  const labels = chart.markLabels(shapes, measure, crowded, 58, 600);
  assert.deepEqual(labels.map((label) => [label.x, label.text, label.marks.map((one) => one.id)]), [
    [104, "2 marks", ["a", "b"]],
    [304, "Camp", ["c"]],
  ]);
  // The names join from the left: a name after a group is compared with the
  // words of the group ("2 marks"), not with the names in it, so that three
  // names that meet one after another are not all joined.
  const chain = chart.markLabels(
    [
      { mark: mark("a", "2030-01-01", null, "race", "A long one"), x: 96 },
      { mark: mark("b", "2030-01-02", null, "race", "Bbbbb"), x: 146 },
      { mark: mark("c", "2030-01-03", null, "race", "C"), x: 172 },
    ],
    measure,
    crowded,
    58,
    600,
  );
  assert.deepEqual(chain.map((label) => [label.x, label.text]), [[100, "2 marks"], [176, "C"]]);
  // Two marks of one day never part, whatever the period.
  const sameDay = chart.markLabels([{ mark: mark("a", "2030-01-01"), x: 200 }, { mark: mark("b", "2030-01-01"), x: 200 }], measure, crowded, 58, 600);
  assert.deepEqual(sameDay.map((label) => label.text), ["2 marks"]);
  // A name past the right end ends there, and joins the one before when they meet then.
  const right = chart.markLabels([{ mark: mark("a", "2030-01-01", null, "race", "A first name"), x: 500 }, { mark: mark("b", "2030-01-02", null, "race", "A long name"), x: 590 }], measure, crowded, 58, 600);
  assert.deepEqual(right.map((label) => [label.x, label.text]), [[504, "2 marks"]]);
  const apart = chart.markLabels([{ mark: mark("a", "2030-01-01", null, "race", "A"), x: 500 }, { mark: mark("b", "2030-01-02", null, "race", "A long name"), x: 590 }], measure, crowded, 58, 600);
  assert.deepEqual(apart.map((label) => [label.x, label.text]), [[504, "A"], [534, "A long name"]]);
  const alone = chart.markLabels([{ mark: mark("a", "2030-01-01", null, "race", "A long name"), x: 590 }], measure, crowded, 58, 600);
  assert.deepEqual(alone.map((label) => [label.x, label.text]), [[600 - 66, "A long name"]]);
  assert.deepEqual(chart.markLabels([], measure, crowded, 58, 600), []);
  // A name longer than the chart is cut, by characters, with "…" (the review
  // by Codex).
  const narrow = chart.markLabels([{ mark: mark("a", "2030-01-01", null, "race", "\u{1F3C3}".repeat(20)), x: 10 }], (text) => Array.from(text).length * 6, crowded, 0, 60);
  assert.deepEqual(narrow.map((label) => [label.x, label.text]), [[0, `${"\u{1F3C3}".repeat(9)}…`]]);
});

test("the steps of a calendar are one to six, from the ticks of a scale (stage N1 of v2.2.0)", () => {
  // Codex's review of the plan of N1: up to 13 from 0, five ticks give seven
  // steps of 2; the calendar takes those of four, three steps of 5.
  assert.equal(chart.valueScale(0.5, 13, { fromZero: true, count: 5 }).ticks.length - 1, 7);
  assert.deepEqual(chart.calendarScale([0.5, 13], { fromZero: true }), [0, 5, 10, 15]);
  assert.deepEqual(chart.calendarScale([0.2, 999], { fromZero: true }), [0, 200, 400, 600, 800, 1000, 1200]);
  assert.deepEqual(chart.calendarScale([7, 7]), [6.6, 6.8, 7, 7.2, 7.4]);
  for (const [values, options] of [
    [[0.5, 13], { fromZero: true }],
    [[3, 91], { fromZero: true }],
    [[61, 64], {}],
    [[0, 0.4], { fromZero: true }],
    [[290, 410], { clock: "second" }],
    [[25, 340], { fromZero: true, clock: "minute" }],
  ]) {
    const ticks = chart.calendarScale(values, options);
    assert.ok(ticks.length - 1 >= 1 && ticks.length - 1 <= 6, JSON.stringify(values));
    assert.ok(ticks[0] <= Math.min(...values) && ticks[ticks.length - 1] > Math.max(...values), JSON.stringify(values));
  }
  assert.equal(chart.calendarScale([]), null);
  assert.equal(chart.calendarScale([null, Number.NaN]), null);
  // Steps twice as wide from the same first tick, until there are six at most.
  assert.deepEqual(chart.coarserTicks([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 6), [0, 2, 4, 6, 8, 10]);
  assert.deepEqual(chart.coarserTicks([0, 2, 4, 6, 8, 10, 12, 14], 6), [0, 4, 8, 12, 16]);
  assert.deepEqual(chart.coarserTicks([0, 5, 10], 6), [0, 5, 10]);
});
