// Where a window of the right column of the view page goes (stage X12d1 of
// v2.3.0): popPlace of view_flow.mjs, from the box of the window as its
// rules place it, the box of the column inside its padding, the top of the
// bar at the bottom of the page, and the height of what the window holds.
// The numbers are those that the real page measured in a narrow window: the
// column inside its padding from 396 at 1000 pixels of the page, its top at
// 249, and the bar at 642.
import assert from "node:assert/strict";
import { test } from "node:test";

import { POP_GAP, POP_ROOM, popPlace } from "../../src/garmin_running_data_normalizer/gui/static/view_flow.mjs";

const column = { left: 396, right: 984, top: 249 };

test("the room kept under a window and above the bar are those of the stages before", () => {
  assert.equal(POP_ROOM, 240);
  assert.equal(POP_GAP, 12);
});

test("a window inside a wide column does not move, and reaches down to the bar as before", () => {
  const wide = { left: 396, right: 1454, top: 249 };
  const pop = { left: 798, right: 1438, top: 306 };
  assert.deepEqual(popPlace(pop, wide, 642, 400), { dx: 0, dy: 0, maxHeight: Math.floor(642 - 306 - 12) });
});

test("the window of the saving, which the page places inside the column itself, does not move twice", () => {
  // fitSaveWindow keeps the window inside the column, its width no larger
  // than the column; popPlace then finds nothing to move (the checker's
  // review of the plan of X12d1, 1).
  const pop = { left: 396, right: 984, top: 300 };
  const place = popPlace(pop, column, 642, 300);
  assert.equal(place.dx, 0);
  assert.equal(place.dy, 0);
});

test("a window that goes out of the left of the column moves right, back into it", () => {
  // The window of the laps at 1000 pixels: its left was cut by 36 pixels.
  const pop = { left: 360, right: 984, top: 332 };
  const place = popPlace(pop, column, 618, 273);
  assert.equal(place.dx, 36);
  assert.equal(place.dy, 0);
  assert.equal(place.maxHeight, 618 - 332 - 12);
});

test("a window that goes out of the right of the column moves left, but never out of its left", () => {
  // The picker of the items is placed at the left of its button.
  assert.equal(popPlace({ left: 700, right: 1100, top: 300 }, column, 642, 200).dx, 984 - 1100);
  // As wide as the column: it moves to the left of the column, no further.
  assert.equal(popPlace({ left: 500, right: 1088, top: 300 }, column, 642, 200).dx, 396 - 500);
});

test("a window wider than the column by a rounding of its width keeps its left at the column's", () => {
  // The width that fitPop gives is a whole number of pixels, the box of the
  // window may be a fraction wider: its left stays in the column.
  assert.equal(popPlace({ left: 500, right: 1090, top: 300 }, column, 642, 200).dx, 396 - 500);
});

test("a window with little room under it moves up inside the column, as far as it needs", () => {
  // At 640 pixels: the window under the row at 535, the bar at 607, the top
  // of the column at 320; 60 pixels were left.
  const narrow = { left: 396, right: 624, top: 320 };
  const place = popPlace({ left: 396, right: 624, top: 535 }, narrow, 607, 500);
  assert.equal(place.dy, POP_ROOM - (607 - 535 - POP_GAP));
  assert.equal(place.maxHeight, POP_ROOM);
  // What it holds is shorter than the room: it moves up only for that.
  const short = popPlace({ left: 396, right: 624, top: 535 }, narrow, 607, 152);
  assert.equal(short.dy, 152 - (607 - 535 - POP_GAP));
  assert.equal(short.maxHeight, 152);
});

test("a window moves up no higher than the top of the column", () => {
  const low = { left: 396, right: 624, top: 500 };
  const place = popPlace({ left: 396, right: 624, top: 560 }, low, 607, 400);
  assert.equal(place.dy, 60);
  assert.equal(place.maxHeight, Math.floor(607 - 500 - POP_GAP));
});

test("a window with room enough, or one that holds nothing yet, does not move up", () => {
  assert.equal(popPlace({ left: 400, right: 900, top: 300 }, column, 642, 400).dy, 0);
  assert.equal(popPlace({ left: 400, right: 900, top: 535 }, { ...column, top: 320 }, 607, 0).dy, 0);
});

test("a floor above the top of the window leaves no height, never a negative one", () => {
  const place = popPlace({ left: 400, right: 900, top: 700 }, { ...column, top: 700 }, 650, 300);
  assert.equal(place.dy, 0);
  assert.equal(place.maxHeight, 0);
});
