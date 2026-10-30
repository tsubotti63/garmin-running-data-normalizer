// The shapes of the charts of the view page (stage G3b): the time scale, the
// scale of the values and its ticks, and the marks of a panel as the data of
// SVG paths, as plain functions that the node tests check; view.mjs puts them
// in SVG elements. Each kind of mark of a line is one path, so that a panel of
// fifteen years by day stays a few elements.
//
// The marks follow the mockup v2 and the rules of the charts of stage G3b:
// bars up to 24 px wide with a gap of 2 px and round at the end of the data
// only, lines of 2 px broken where a period has no value, a point that stands
// alone drawn as a marker, a hollow dot for a total of 0, and markers of 8 px
// with a ring of the color of the surface.

const DAY_MS = 86400000;
// The margins of the plot of every panel, which the time axis and the
// overview share: the ticks of the values are at the left.
export const PLOT_LEFT = 58;
export const PLOT_RIGHT = 16;
export const PLOT_TOP = 8;
export const PLOT_BOTTOM = 5;
// A total is drawn as bars up to this many periods, and as a line above.
export const MAX_BARS = 220;
// Up to this many points, a point is a marker of 8 px with a ring; above,
// a small dot of the data.
export const MAX_MARKERS = 500;
// The markers on every point of a short line.
const MAX_LINE_MARKERS = 40;
export const MARKER_RADIUS = 4;
const DOT_RADIUS = 1.6;
const BAR_WIDTH = 24;
const BAR_GAP = 2;
const BAR_ROUND = 4;
// Ticks of values closer than this are thinned.
const TICK_GAP = 16;

// Steps of the scale of values: decimal steps for numbers, and the steps of
// a clock for values in minutes and in seconds.
const CLOCK_STEPS = {
  minute: [1, 2, 5, 10, 15, 30, 60, 120, 180, 300, 600, 1200, 1800, 3000, 6000, 12000, 30000, 60000],
  second: [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 18000, 36000, 72000, 180000],
};

// The day of an ISO date ("2026-10-26") as a count of days, and back.
export function dayNumber(iso) {
  const [year, month, day] = String(iso).split("-").map(Number);
  return Math.round(Date.UTC(year, month - 1, day) / DAY_MS);
}

export function isoDate(day) {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

// The periods of an answer of the server as counts of days.
export function periodDays(periods) {
  return periods.map((period) => ({
    start: dayNumber(period.start),
    end: dayNumber(period.end),
    partial: period.partial === true,
  }));
}

// The x of the days from start to end, between left and right: each period
// takes the width from its first day to the end of its last.
export function timeScale(start, end, left, right) {
  const span = end + 1 - start;
  const width = right - left;
  return {
    x: (day) => left + ((day - start) / span) * width,
    day: (x) => start + ((x - left) / width) * span,
  };
}

// The middle of a period, where its point and the cross line are.
export function periodMiddle(scale, period) {
  return scale.x((period.start + period.end + 1) / 2);
}

// The period whose middle is nearest to x.
export function nearestPeriod(periods, scale, x) {
  let low = 0;
  let high = periods.length - 1;
  if (high < 0) {
    return null;
  }
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (periodMiddle(scale, periods[middle]) < x) {
      low = middle + 1;
    } else {
      high = middle;
    }
  }
  if (low > 0 && Math.abs(periodMiddle(scale, periods[low - 1]) - x) <= Math.abs(periodMiddle(scale, periods[low]) - x)) {
    return low - 1;
  }
  return low;
}

function decimalStep(raw) {
  if (!(raw > 0) || !Number.isFinite(raw)) {
    return 1;
  }
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / magnitude;
  return (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * magnitude;
}

// A step that gives about ``count`` steps over ``span``: a step of the clock
// for minutes and seconds, so that the ticks read 0:30, 1:00, and so on.
export function niceStep(span, count, clock = null) {
  const raw = span / count;
  const steps = CLOCK_STEPS[clock];
  if (steps !== undefined && raw > 0) {
    const step = steps.find((candidate) => candidate >= raw * 0.75);
    if (step !== undefined) {
      return step;
    }
  }
  return decimalStep(raw);
}

// The scale of a panel from its lowest to its highest value: from 0 for a
// total, with room above and below for the others, out to whole steps on both
// ends, with two ticks at least.
export function valueScale(low, high, { fromZero = false, count = 3, clock = null } = {}) {
  // A value that is not a number, such as a pace too large for the units of
  // the page, takes no part (Codex's review of the diff of O1).
  let lo = Number.isFinite(low) ? low : Number.isFinite(high) ? high : 0;
  let hi = Number.isFinite(high) ? high : lo;
  if (fromZero) {
    lo = 0;
    hi = hi > 0 ? hi * 1.04 : 1;
  } else {
    const pad = (hi - lo) * 0.06 || Math.abs(hi) * 0.05 || 1;
    lo -= pad;
    hi += pad;
  }
  const step = niceStep(hi - lo, count, clock);
  const first = fromZero ? 0 : Math.floor(lo / step) * step;
  let last = Math.ceil(hi / step) * step;
  if (last <= first) {
    last = first + step;
  }
  const ticks = [];
  for (let value = first; value <= last + step * 1e-6 && ticks.length <= MAX_TICKS; value += step) {
    ticks.push(Number(value.toFixed(10)));
  }
  return { lo: first, hi: last, ticks: ticks.length > 1 ? ticks : [first, first + step] };
}

// The ticks of the steps of the colors of a calendar (stage N1 of v2.2.0):
// those of a scale over the values shown, as a panel makes them (from 0 for
// a total), with one to six steps between them (Codex's review of the plan
// of N1: the count of a scale is only a guide). None without a value.
export function calendarScale(values, { fromZero = false, clock = null } = {}) {
  const shown = (Array.isArray(values) ? values : []).filter(Number.isFinite);
  if (!shown.length) {
    return null;
  }
  const low = Math.min(...shown);
  const high = Math.max(...shown);
  for (const count of [5, 4, 3]) {
    const { ticks } = valueScale(low, high, { fromZero, count, clock });
    if (ticks.length - 1 <= 6) {
      return ticks;
    }
  }
  return coarserTicks(valueScale(low, high, { fromZero, count: 3, clock }).ticks, 6);
}

// Ticks of steps twice as wide, from the same first tick, until there are
// ``steps`` steps at most; the last tick stays at or above the last one.
export function coarserTicks(ticks, steps) {
  let kept = ticks;
  while (kept.length - 1 > steps) {
    const step = (kept[1] - kept[0]) * 2;
    const count = Math.ceil((kept[kept.length - 1] - kept[0]) / step - 1e-9);
    const first = kept[0];
    kept = Array.from({ length: count + 1 }, (_none, index) => Number((first + index * step).toFixed(10)));
  }
  return kept;
}

// The number of ticks for the height of a plot: two on a low strip, five on
// a tall panel.
export function tickCount(height) {
  return height < 80 ? 2 : height > 260 ? 5 : 3;
}

// Every other tick, until they are 16 px apart.
export function thinTicks(ticks, y) {
  let kept = ticks;
  while (kept.length > 2 && Math.abs(y(kept[0]) - y(kept[1])) < TICK_GAP) {
    kept = kept.filter((_tick, index) => index % 2 === 0);
  }
  return kept;
}

// The lowest and the highest value of the lines of a panel, with their
// points, or null when there is none.
export function extent(lines) {
  let low = Infinity;
  let high = -Infinity;
  for (const line of lines) {
    for (const value of line.values) {
      if (Number.isFinite(value)) {
        low = Math.min(low, value);
        high = Math.max(high, value);
      }
    }
    for (const [, value] of line.points ?? []) {
      if (Number.isFinite(value)) {
        low = Math.min(low, value);
        high = Math.max(high, value);
      }
    }
  }
  return low === Infinity ? null : [low, high];
}

// The panels that share one scale: those whose items have the same unit
// group, when the person asked for it and two or more of them are shown.
export function sharedExtents(panels, align) {
  const shared = new Map();
  if (!align) {
    return shared;
  }
  const groups = new Map();
  for (const panel of panels) {
    if (panel.unitGroup && panel.extent !== null) {
      groups.set(panel.unitGroup, [...(groups.get(panel.unitGroup) ?? []), panel]);
    }
  }
  for (const members of groups.values()) {
    if (members.length < 2) {
      continue;
    }
    const low = Math.min(...members.map((panel) => panel.extent[0]));
    const high = Math.max(...members.map((panel) => panel.extent[1]));
    for (const panel of members) {
      shared.set(panel.key, [low, high]);
    }
  }
  return shared;
}

const round = (value) => Math.round(value * 10) / 10;

// A circle as path data, drawn with a stroke.
function circle(x, y, radius) {
  const r = round(radius);
  return `M${round(x - radius)} ${round(y)}a${r} ${r} 0 1 0 ${round(2 * radius)} 0a${r} ${r} 0 1 0 ${round(-2 * radius)} 0`;
}

// Points as path data: a stroke with round caps on a segment of no length
// draws a dot as wide as the stroke.
export function dotsPath(points) {
  return points.map(([x, y]) => `M${round(x)} ${round(y)}h0.01`).join("");
}

// The bars of a total: from the baseline up to each value, at most 24 px
// wide with a gap of 2 px, round at the end of the data only; the bars of the
// periods cut by the period apart, as they are lighter. A period of 0 has no
// bar: its dot is drawn apart.
export function barPaths(values, periods, scale, y, base) {
  let full = "";
  let partial = "";
  values.forEach((value, index) => {
    if (!Number.isFinite(value) || value <= 0) {
      return;
    }
    const period = periods[index];
    const x0 = scale.x(period.start);
    const x1 = scale.x(period.end + 1);
    const width = Math.max(1, Math.min(BAR_WIDTH, x1 - x0 - BAR_GAP));
    const middle = (x0 + x1) / 2;
    const left = round(middle - width / 2);
    const right = round(middle + width / 2);
    const top = round(y(value));
    const radius = round(Math.max(0, Math.min(BAR_ROUND, width / 2, base - top)));
    const bottom = round(base);
    const bar =
      `M${left} ${bottom}V${round(top + radius)}Q${left} ${top} ${round(left + radius)} ${top}` +
      `H${round(right - radius)}Q${right} ${top} ${right} ${round(top + radius)}V${bottom}Z`;
    if (period.partial) {
      partial += bar;
    } else {
      full += bar;
    }
  });
  return { full, partial };
}

// The hollow dots of the periods of 0 of a total, on the baseline, as wide as
// a period allows, from 2 px to the 4 px of a marker.
export function zeroPath(values, periods, scale, base) {
  let path = "";
  values.forEach((value, index) => {
    if (value !== 0) {
      return;
    }
    const period = periods[index];
    const room = (scale.x(period.end + 1) - scale.x(period.start)) / 2 - 1;
    const radius = Math.max(2, Math.min(MARKER_RADIUS, room));
    path += circle(periodMiddle(scale, period), base - radius - 0.5, radius);
  });
  return path;
}

// A line through the middles of the periods with a value, broken where a
// period has none, and, for a total, where it is 0, which its dot shows. The
// points between two breaks stand alone, and are drawn as points.
export function linePath(values, periods, scale, y, { breakAtZero = false } = {}) {
  const drawn = (value) => Number.isFinite(value) && !(breakAtZero && value === 0);
  let path = "";
  let pen = false;
  const alone = [];
  values.forEach((value, index) => {
    if (!drawn(value)) {
      pen = false;
      return;
    }
    const x = periodMiddle(scale, periods[index]);
    const yValue = y(value);
    path += `${pen ? "L" : "M"}${round(x)} ${round(yValue)}`;
    pen = true;
    if (!drawn(values[index - 1]) && !drawn(values[index + 1])) {
      alone.push([x, yValue]);
    }
  });
  return { path, alone };
}

// The places of the labels at the ends of the lines of the years compared
// (stage L1 of v2.2.0), from the ends of the lines (their y): each at the
// end of its line, moved down where it would meet the one above it, and up
// again where the lowest would leave the plot at ``bottom``.
export function labelPlaces(ends, gap, bottom) {
  const order = ends.map((end, index) => ({ end, index })).sort((a, b) => a.end - b.end || a.index - b.index);
  const placed = new Array(ends.length);
  let last = -Infinity;
  for (const { end, index } of order) {
    placed[index] = Math.max(end, last + gap);
    last = placed[index];
  }
  let limit = bottom;
  for (let at = order.length - 1; at >= 0; at -= 1) {
    const index = order[at].index;
    placed[index] = Math.min(placed[index], limit);
    limit = placed[index] - gap;
  }
  return placed;
}

// The marks of one panel: the ticks of its values, the baseline of a total,
// and for each line its bars or its line, its points that stand alone, the
// markers of a short line, the points of the records of each day, and the
// dots of 0. ``lines`` hold the values as the page shows them (in km, in
// minutes, and so on); ``total`` draws from 0; ``clock`` gives the steps of
// a clock; ``shared`` is the scale that the panel shares, if any. From stage
// L1 of v2.2.0, the years compared: ``lineOnly`` draws a total as a line
// (the years laid over one another), and ``running`` a running total, a line
// from 0 that a period of 0 does not break and that has no dots of 0.
export function panelShapes({ lines, periods, start, end, width, height, total = false, clock = null, shared = null, lineOnly = false, running = false }) {
  const scale = timeScale(start, end, PLOT_LEFT, width - PLOT_RIGHT);
  const top = PLOT_TOP;
  const plotHeight = Math.max(1, height - PLOT_TOP - PLOT_BOTTOM);
  const range = shared ?? extent(lines);
  if (range === null) {
    return { scale, empty: true, ticks: [], lines: [], base: null, y: () => top + plotHeight };
  }
  const fromZero = total || running;
  const scaleOfValues = valueScale(range[0], range[1], { fromZero, count: tickCount(plotHeight), clock });
  const y = (value) => top + plotHeight - ((value - scaleOfValues.lo) / (scaleOfValues.hi - scaleOfValues.lo)) * plotHeight;
  const ticks = thinTicks(scaleOfValues.ticks, y)
    .map((value) => ({ value, y: y(value) }))
    .filter((tick) => tick.y >= top - 1 && tick.y <= top + plotHeight + 1);
  const base = fromZero ? y(Math.max(scaleOfValues.lo, 0)) : null;
  // The periods of 0 of a total: a dot each, where its line breaks.
  const zeros = total && !running;
  const bars = zeros && !lineOnly && periods.length <= MAX_BARS;
  const big = periods.length > MAX_MARKERS;
  const shapes = lines.map((line) => {
    const shape = { bars: null, line: null, alone: "", markers: "", points: "", pointRadius: 0, zero: "" };
    if (line.points !== undefined && line.points !== null) {
      // The records of each day, every one a point.
      const many = line.points.length > MAX_MARKERS || plotHeight < 70;
      shape.points = dotsPath(line.points.map(([index, value]) => [periodMiddle(scale, periods[index]), y(value)]));
      shape.pointRadius = many ? DOT_RADIUS : MARKER_RADIUS;
      return shape;
    }
    if (bars) {
      shape.bars = barPaths(line.values, periods, scale, y, base);
    } else {
      const drawn = linePath(line.values, periods, scale, y, { breakAtZero: zeros });
      shape.line = drawn.path;
      shape.alone = dotsPath(drawn.alone);
      shape.aloneRadius = big ? DOT_RADIUS + 0.4 : MARKER_RADIUS;
      if (periods.length <= MAX_LINE_MARKERS && plotHeight >= 70) {
        shape.markers = dotsPath(
          line.values.flatMap((value, index) =>
            Number.isFinite(value) && !(zeros && value === 0) ? [[periodMiddle(scale, periods[index]), y(value)]] : [],
          ),
        );
      }
    }
    if (zeros) {
      shape.zero = zeroPath(line.values, periods, scale, base);
    }
    return shape;
  });
  return { scale, empty: false, ticks, base, y, lines: shapes, top, plotHeight };
}

// Where the time axis is marked: every year (every other year where they
// would crowd) for a span over two years, every month for a shorter one, and
// every Monday under two months.
export function timeTicks(start, end, plotWidth) {
  const span = end + 1 - start;
  const ticks = [];
  const first = new Date(start * DAY_MS);
  const last = new Date(end * DAY_MS);
  if (span > 2 * 366) {
    const years = last.getUTCFullYear() - first.getUTCFullYear() + 1;
    const every = plotWidth / years < 54 ? 2 : 1;
    for (let year = first.getUTCFullYear(); year <= last.getUTCFullYear(); year += 1) {
      const day = Math.round(Date.UTC(year, 0, 1) / DAY_MS);
      if (day >= start && day <= end && year % every === 0) {
        ticks.push({ day, kind: "year" });
      }
    }
    return ticks;
  }
  if (span > 62) {
    let month = Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), 1);
    let named = false;
    while (month <= end * DAY_MS) {
      const day = Math.round(month / DAY_MS);
      const date = new Date(month);
      if (day >= start) {
        // The first tick and every January name the year.
        ticks.push({ day, kind: date.getUTCMonth() === 0 || !named ? "month_year" : "month" });
        named = true;
      }
      month = Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1);
    }
    return ticks;
  }
  for (let day = start; day <= end; day += 1) {
    // 1 January 1970 was a Thursday.
    if ((((day + 3) % 7) + 7) % 7 === 0) {
      ticks.push({ day, kind: "day" });
    }
  }
  return ticks;
}

// The overview under the panels: the whole output by month, the bars or the
// line of one item, and the frame of the period shown, with the parts
// outside it dimmed.
export function overviewShapes({ values, periods, width, height, total = false, start, end }) {
  const first = periods.length ? periods[0].start : start;
  const last = periods.length ? periods[periods.length - 1].end : end;
  const scale = timeScale(first, last, 0, width);
  const base = height - 14;
  const finite = values.filter((value) => Number.isFinite(value));
  const high = finite.length ? Math.max(...finite) : 1;
  const low = total || !finite.length ? 0 : Math.min(...finite);
  const y = (value) => base - ((value - low) / (high - low || 1)) * (base - 6);
  let marks = "";
  if (total) {
    values.forEach((value, index) => {
      if (Number.isFinite(value) && value > 0) {
        const period = periods[index];
        const x0 = scale.x(period.start);
        const x1 = scale.x(period.end + 1);
        const top = y(value);
        marks += `M${round(x0 + 0.5)} ${round(base)}V${round(top)}H${round(Math.max(x0 + 1.1, x1 - 0.5))}V${round(base)}Z`;
      }
    });
  } else {
    marks = linePath(values, periods, scale, y).path;
  }
  const from = scale.x(start);
  const to = scale.x(end + 1);
  return { scale, base, marks, total, frame: { from, to }, first, last };
}

// The marks of the person on a chart (stage M1 of v2.2.0), from the day
// ``start`` to the day ``end`` (day numbers, both shown) between ``left`` and
// ``right``: a mark of one day is a line in the middle of its day, where the
// value of a day is; a span is a band from the start of its first day (x) to
// the end of its last (``band.end``), cut where it goes on beyond the days
// shown, so that only its own start and end have an edge. A band of a few
// days on a long period is drawn 2 px wide (from ``band.from``), inside the
// chart, but its edges stay at its days. The marks outside the days shown are
// left out.
export function markShapes(marks, start, end, left, right) {
  const scale = timeScale(start, end, left, right);
  const shapes = [];
  for (const mark of marks) {
    const first = dayNumber(mark.day);
    const last = mark.end ? dayNumber(mark.end) : first;
    if (!Number.isFinite(first) || !Number.isFinite(last) || last < start || first > end) {
      continue;
    }
    if (!mark.end) {
      shapes.push({ mark, x: scale.x(first + 0.5), band: null });
      continue;
    }
    const x = scale.x(Math.max(first, start));
    const to = scale.x(Math.min(last, end) + 1);
    const width = Math.max(2, to - x);
    shapes.push({ mark, x, band: { from: Math.max(left, Math.min(x, right - width)), width, end: to, starts: first >= start, ends: last <= end } });
  }
  return shapes;
}

// The names of the marks on the top chart, from left to right, each just
// after its line or the start of its band: a name that would meet the name
// before it joins it, and a group of more than one mark shows how many it
// holds (``crowded(n)``) in place of the names. ``measure`` gives the width
// of a text; the names stay between ``left`` and ``right``, and one longer
// than that is cut, with "…".
export function markLabels(shapes, measure, crowded, left, right, gap = 6) {
  const groups = [];
  const join = (group, marks) => {
    group.marks.push(...marks);
    group.text = crowded(group.marks.length);
    group.width = measure(group.text);
  };
  for (const shape of [...shapes].sort((a, b) => a.x - b.x)) {
    const x = shape.x + 4;
    const last = groups[groups.length - 1];
    if (last !== undefined && x < last.x + last.width + gap) {
      join(last, [shape.mark]);
    } else {
      groups.push({ x, marks: [shape.mark], text: shape.mark.name, width: measure(shape.mark.name) });
    }
  }
  // A name that would go past the right end ends there, and joins the group
  // before it where they meet then.
  for (let index = groups.length - 1; index >= 0; index -= 1) {
    const group = groups[index];
    if (group.x + group.width > right) {
      group.x = Math.max(left, right - group.width);
    }
    const before = groups[index - 1];
    if (before !== undefined && group.x < before.x + before.width + gap) {
      join(before, group.marks);
      groups.splice(index, 1);
    }
  }
  const room = right - left;
  for (const group of groups) {
    if (group.width > room) {
      // By characters, not by halves of a pair of UTF-16 units.
      const characters = Array.from(group.text);
      while (characters.length > 1 && measure(`${characters.join("")}…`) > room) {
        characters.pop();
      }
      group.text = `${characters.join("")}…`;
      group.x = left;
    }
  }
  return groups.map(({ x, marks, text }) => ({ x, marks, text }));
}

// --- Two items plotted against each other (stage O1 of v2.2.0) ------------

// The room of a plot of points: the ticks of the values up at the left, as a
// panel has them, the name of the item up above the plot, and the ticks and
// the name of the item across below it.
export const POINTS_TOP = 22;
export const POINTS_BOTTOM = 40;
export const POINT_RADIUS = 3.5;
export const CHOSEN_RADIUS = 5;
// A tick across every this many pixels at least, so that the words of the
// ticks, clocks among them, never meet (Codex's review of the plan of O1).
export const ACROSS_TICK_GAP = 90;
// No scale has more ticks than this, whatever its values.
const MAX_TICKS = 200;

// The number of the ticks across for the width of a plot: one every 90 px or
// so, two at least and six at most.
export function acrossTickCount(width) {
  return Math.max(2, Math.min(6, Math.floor(width / ACROSS_TICK_GAP)));
}

// Every other tick across, until the ticks are far enough apart for their
// words (the ticks up need 16 px only: thinTicks).
export function thinAcross(ticks, x) {
  let kept = ticks;
  while (kept.length > 2 && Math.abs(x(kept[1]) - x(kept[0])) < ACROSS_TICK_GAP * 0.7) {
    kept = kept.filter((_tick, index) => index % 2 === 0);
  }
  return kept;
}

// The places of the points of two items in a plot of ``width`` by ``height``,
// from their values as the page shows them (``xs`` across, ``ys`` up): a
// scale for each over its values, never from 0, so that the points spread
// (the checker's review of the plan of O1: the ticks say where a scale
// starts), in the clock of its unit; and the place of every point. Null
// without a point.
export function pointShapes(xs, ys, { width, height, clockX = null, clockY = null }) {
  // The scales go over the values that are numbers only; a point of
  // another value is not drawn.
  const shownX = xs.filter(Number.isFinite);
  const shownY = ys.filter(Number.isFinite);
  if (!shownX.length || !shownY.length || xs.length !== ys.length) {
    return null;
  }
  const left = PLOT_LEFT;
  const right = Math.max(left + 1, width - PLOT_RIGHT);
  const top = POINTS_TOP;
  const bottom = Math.max(top + 1, height - POINTS_BOTTOM);
  const across = valueScale(Math.min(...shownX), Math.max(...shownX), { count: acrossTickCount(right - left), clock: clockX });
  const up = valueScale(Math.min(...shownY), Math.max(...shownY), { count: tickCount(bottom - top), clock: clockY });
  const x = (value) => left + ((value - across.lo) / (across.hi - across.lo)) * (right - left);
  const y = (value) => bottom - ((value - up.lo) / (up.hi - up.lo)) * (bottom - top);
  return {
    left,
    right,
    top,
    bottom,
    across: { ...across, ticks: thinAcross(across.ticks, x) },
    up: { ...up, ticks: thinTicks(up.ticks, y) },
    x,
    y,
    places: xs.map((value, index) => ({ x: x(value), y: y(ys[index]) })),
  };
}
