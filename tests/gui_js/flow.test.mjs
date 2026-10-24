import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

import {
  ACTIVE_STATES,
  FINISHED_STATES,
  TERMINAL_STATES,
  announcement,
  boxStates,
  connectionMessages,
  controls,
  defaultOutputName,
  errorMessages,
  familyRows,
  findingMessages,
  formatElapsed,
  isValidOutputName,
  nextOutputName,
  outputCheckMessages,
  shouldFocusResult,
  progressMessage,
  stalledSeconds,
} from "../../src/garmin_running_data_normalizer/gui/static/flow.mjs";
// Read through the module, so that a test of a function that a version lacks
// fails on its own.
import * as flow from "../../src/garmin_running_data_normalizer/gui/static/flow.mjs";

// A message as [key, params, keyParams], for compact comparisons.
const shape = (message) => [message.key, message.params, message.keyParams];

// A page whose four boxes are set: the export is checked, and the second
// and third boxes are confirmed.
const READY = {
  connected: true,
  runState: "idle",
  starting: false,
  checking: false,
  checkedReady: true,
  exportReady: true,
  exportProblem: false,
  snapshotDecided: true,
  outputDecided: true,
  inputPath: "/path/to/export",
  outputParent: "/path/to",
  outputName: "garmin-run-all-20261010-0705",
  timezone: "Asia/Tokyo",
};
// The controls of a view, with the states of its boxes.
const enabled = (view) => controls(view, boxStates(view));

test("run states are either active or terminal", () => {
  assert.deepEqual(ACTIVE_STATES, ["running", "cancelling"]);
  assert.deepEqual(TERMINAL_STATES, ["finished", "finished_after_cancel", "cancelled", "failed"]);
  assert.deepEqual(FINISHED_STATES, ["finished", "finished_after_cancel"]);
});

test("a checked export with confirmed boxes can start a run", () => {
  assert.deepEqual(enabled(READY), {
    form: true,
    choose: true,
    browse: true,
    check: true,
    decideSnapshot: false,
    decideOutput: false,
    start: true,
    cancel: false,
    quit: true,
    hints: true,
    outputActions: false,
    forget: false,
  });
});

test("nothing works without a connection", () => {
  const off = enabled({ ...READY, connected: false });
  assert.ok(Object.values(off).every((value) => value === false));
});

test("nothing works while the server stops after Quit, and the tips switch needs the server", () => {
  // v2.0.1 F2: between the answer to the question of Quit and the server's
  // answer, as without a connection; the tips switch remembers its choice on
  // the server, so it is off without one (it showed a lost connection after
  // Quit), while the language and the help panel are no controls of the page.
  const quitting = enabled({ ...READY, quitting: true });
  assert.ok(Object.values(quitting).every((value) => value === false));
  assert.equal(enabled({ ...READY, connected: false, settingsPresent: true }).hints, false);
  assert.equal(enabled(READY).hints, true);
  assert.equal(enabled({ ...READY, runState: "running" }).hints, true);
});

test("a running job can only be cancelled", () => {
  assert.deepEqual(enabled({ ...READY, runState: "running" }), {
    form: false,
    choose: false,
    browse: false,
    check: false,
    decideSnapshot: false,
    decideOutput: false,
    start: false,
    cancel: true,
    quit: false,
    hints: true,
    outputActions: false,
    forget: false,
  });
  const cancelling = enabled({ ...READY, runState: "cancelling" });
  assert.equal(cancelling.cancel, false);
  assert.equal(cancelling.quit, false);
  assert.equal(enabled({ ...READY, starting: true }).start, false);
});

test("a run needs a current successful check, confirmed boxes, and a complete form", () => {
  assert.equal(enabled({ ...READY, checkedReady: false, exportReady: false }).start, false);
  assert.equal(enabled({ ...READY, checking: true }).start, false);
  assert.equal(enabled({ ...READY, checking: true }).check, false);
  assert.equal(enabled({ ...READY, outputParent: "  " }).start, false);
  assert.equal(enabled({ ...READY, timezone: "" }).start, false);
  assert.equal(enabled({ ...READY, outputName: ".hidden" }).start, false);
  assert.equal(enabled({ ...READY, inputPath: "" }).check, false);
  assert.equal(enabled({ ...READY, snapshotDecided: false }).start, false);
  assert.equal(enabled({ ...READY, outputDecided: false }).start, false);
  // A run starts again after any end, with the same confirmed boxes.
  for (const state of TERMINAL_STATES) {
    assert.equal(enabled({ ...READY, runState: state }).start, true, state);
  }
});

test("while a dialog to choose is open, only the fields can change", () => {
  // Stage B3a: one dialog at a time; the page waits for its answer.
  const choosing = enabled({ ...READY, choosing: true });
  assert.equal(choosing.form, true);
  assert.equal(choosing.choose, false);
  assert.equal(choosing.browse, false);
  assert.equal(choosing.check, false);
  assert.equal(choosing.start, false);
  assert.equal(choosing.quit, true);
  assert.equal(enabled({ ...READY, checking: true }).choose, false);
  assert.equal(enabled({ ...READY, runState: "finished", outputBusy: true }).choose, false);
  assert.equal(enabled({ ...READY, inputPath: "" }).choose, true);
});

test("a box is confirmed with its button while it is the current one", () => {
  const second = { ...READY, snapshotDecided: false, outputDecided: false };
  assert.equal(enabled(second).decideSnapshot, true);
  assert.equal(enabled(second).decideOutput, false);
  const third = { ...READY, outputDecided: false };
  assert.equal(enabled(third).decideSnapshot, false);
  assert.equal(enabled(third).decideOutput, true);
  // The third box needs a usable name before it can be confirmed.
  assert.equal(enabled({ ...third, outputName: "a/b" }).decideOutput, false);
  assert.equal(enabled({ ...third, checking: true }).decideOutput, false);
});

test("the remembered settings are forgotten only when there is a file of them", () => {
  // Stage C1: never without a file, without a connection, while a run is
  // active, or while the page is forgetting them.
  const present = { ...READY, settingsPresent: true };
  assert.equal(enabled(present).forget, true);
  assert.equal(enabled(READY).forget, false);
  assert.equal(enabled({ ...present, connected: false }).forget, false);
  assert.equal(enabled({ ...present, runState: "running" }).forget, false);
  assert.equal(enabled({ ...present, runState: "cancelling" }).forget, false);
  assert.equal(enabled({ ...present, starting: true }).forget, false);
  assert.equal(enabled({ ...present, forgetBusy: true }).forget, false);
  for (const state of TERMINAL_STATES) {
    assert.equal(enabled({ ...present, runState: state }).forget, true, state);
  }
});

test("a run that made its output leaves a file of the settings to forget", () => {
  // Stage C1: the page learns it when the run ends, without opening again.
  const after = flow.settingsPresentAfterRun;
  assert.equal(after(false, { state: "finished", settings_notice: null }), true);
  assert.equal(after(false, { state: "finished_after_cancel", settings_notice: null }), true);
  assert.equal(after(false, { state: "finished", settings_notice: "SETTINGS_NOT_WRITTEN" }), false);
  assert.equal(after(false, { state: "failed", settings_notice: null }), false);
  assert.equal(after(false, { state: "cancelled", settings_notice: null }), false);
  assert.equal(after(false, undefined), false);
  // A file that was there stays there.
  assert.equal(after(true, { state: "failed" }), true);
  assert.equal(after(true, { state: "finished", settings_notice: "SETTINGS_NEWER" }), true);
});

test("the page tells what forgetting the settings did, and whether a file is left", () => {
  // Stage C1: the server says "forgotten" when no file is left, and whether
  // there was one.
  assert.deepEqual(flow.forgetOutcome({ forgotten: true, had_settings: true, notice: null }), {
    key: "forget.done",
    notice: null,
    present: false,
  });
  assert.deepEqual(flow.forgetOutcome({ forgotten: true, had_settings: false, notice: null }), {
    key: "forget.nothing",
    notice: null,
    present: false,
  });
  for (const answer of [{ forgotten: false, had_settings: true, notice: "SETTINGS_NOT_REMOVED" }, null, {}]) {
    assert.deepEqual(flow.forgetOutcome(answer), { key: null, notice: "SETTINGS_NOT_REMOVED", present: true });
  }
  // When the page starts, from the settings that the server read.
  assert.equal(flow.launchSettings({ settings: { launch: "first", present: true } }).present, true);
  assert.equal(flow.launchSettings({ settings: { launch: "later", store: "/s", present: false } }).present, false);
  assert.equal(flow.launchSettings({ settings: { launch: "first" } }).present, false);
  assert.equal(flow.launchSettings({}).present, false);
});

test("one button at most is filled with the accent color, and it is the next step", () => {
  // Stage C1: after a run that made its output, until a box changes, the
  // button that shows it; otherwise the confirmation of the current box that
  // shows, and then Normalize.
  const primary = (view) => flow.primaryControl(view, boxStates(view), enabled(view));
  const second = { ...READY, snapshotDecided: false, outputDecided: false };
  const third = { ...READY, outputDecided: false };
  assert.equal(primary(second), "snapshotDecide");
  assert.equal(primary(third), "outputDecide");
  assert.equal(primary(READY), "start");
  assert.equal(primary({ ...READY, runState: "running" }), null);
  assert.equal(primary({ ...READY, connected: false }), null);
  for (const state of FINISHED_STATES) {
    assert.equal(primary({ ...READY, runState: state }), "openFolder", state);
    // Normalize can start again, but the output is the next step.
    assert.equal(enabled({ ...READY, runState: state }).start, true, state);
    // A change after the run brings back the next step of the boxes.
    assert.equal(primary({ ...third, runState: state, editedSinceRun: true }), "outputDecide", state);
    assert.equal(primary({ ...READY, runState: state, editedSinceRun: true }), "start", state);
    // A button that cannot be pressed is not filled.
    assert.equal(primary({ ...READY, runState: state, outputBusy: true }), null, state);
    assert.equal(primary({ ...READY, runState: state, connected: false }), null, state);
  }
  assert.equal(primary({ ...READY, runState: "failed" }), "start");
  // A button that its box hides is never the one filled, whatever the page
  // enables; the next shown step is.
  const allOn = { decideSnapshot: true, decideOutput: true, start: true };
  assert.equal(flow.primaryControl({ snapshotAuto: true }, { snapshot: "current", output: "current" }, allOn), "outputDecide");
  assert.equal(flow.primaryControl({ outputAuto: true }, { snapshot: "done", output: "current" }, allOn), "start");
  assert.equal(flow.primaryControl({}, { snapshot: "done", output: "done" }, allOn), "start");
  // Every view of a grid: the button is one that the page enables and shows.
  const flags = [
    "connected",
    "starting",
    "checking",
    "checkedReady",
    "exportReady",
    "snapshotDecided",
    "outputDecided",
    "snapshotAuto",
    "outputAuto",
    "outputBusy",
    "choosing",
    "editedSinceRun",
  ];
  const runStates = ["idle", ...ACTIVE_STATES, ...TERMINAL_STATES];
  let views = 0;
  for (const runState of runStates) {
    for (let bits = 0; bits < 2 ** flags.length; bits++) {
      const view = { ...READY, runState };
      flags.forEach((flag, index) => {
        view[flag] = Boolean(bits & (1 << index));
      });
      const states = boxStates(view);
      const on = controls(view, states);
      const shows = (box, auto) => !flow.decideHidden(states[box], auto);
      const chosen = flow.primaryControl(view, states, on);
      const where = JSON.stringify(view);
      const outputNext = FINISHED_STATES.includes(runState) && !view.editedSinceRun;
      if (outputNext) {
        assert.equal(chosen, on.outputActions ? "openFolder" : null, where);
      } else if (on.decideSnapshot && shows("snapshot", view.snapshotAuto)) {
        assert.equal(chosen, "snapshotDecide", where);
      } else if (on.decideOutput && shows("output", view.outputAuto)) {
        assert.equal(chosen, "outputDecide", where);
      } else {
        assert.equal(chosen, on.start ? "start" : null, where);
      }
      // The button that shows the output is filled only while it shows and
      // can be pressed; so is every other one.
      if (chosen === "openFolder") {
        assert.ok(FINISHED_STATES.includes(runState) && on.outputActions, where);
      }
      if (chosen === "start") {
        assert.ok(on.start, where);
      }
      if (chosen === "snapshotDecide") {
        assert.equal(states.snapshot, "current", where);
      }
      if (chosen === "outputDecide") {
        assert.equal(states.output, "current", where);
      }
      views += 1;
    }
  }
  assert.equal(views, runStates.length * 2 ** flags.length);
});

test("only a finished output can be checked, opened, or bundled", () => {
  for (const state of FINISHED_STATES) {
    assert.equal(enabled({ ...READY, runState: state }).outputActions, true, state);
  }
  for (const state of ["idle", "running", "cancelling", "cancelled", "failed"]) {
    assert.equal(enabled({ ...READY, runState: state }).outputActions, false, state);
  }
  const finished = { ...READY, runState: "finished" };
  assert.equal(enabled({ ...finished, connected: false }).outputActions, false);
  assert.equal(enabled({ ...finished, starting: true }).outputActions, false);
  assert.equal(enabled({ ...finished, checking: true }).outputActions, false);
  const busy = enabled({ ...finished, outputBusy: true });
  assert.equal(busy.outputActions, false);
  assert.equal(busy.start, false);
  assert.equal(busy.quit, false);
});

test("output names follow the server's rules", () => {
  for (const name of [
    "garmin-run-all-20261010-0705", "My output", "run.v2",
    "x".repeat(200), "あ".repeat(66), "\u{1F3C3}".repeat(50), `${"a".repeat(197)}あ`,
  ]) {
    assert.equal(isValidOutputName(name), true, name);
  }
  for (const name of [
    "", ".", "..", ".hidden", "a/b", "a\\b", "CON", "con.txt", "Nul", "name.", "name ",
    "a:b", "a*b", "a?b", 'a"b', "a<b", "a|b", "tab\tname", "x".repeat(256), null, 7,
    "x".repeat(201), "あ".repeat(67), "\u{1F3C3}".repeat(51), `${"a".repeat(198)}あ`,
    "\uD800", "a\uDC80b",
  ]) {
    assert.equal(isValidOutputName(name), false, String(name));
  }
});

test("the proposed output name uses the local date and time", () => {
  assert.equal(defaultOutputName(new Date(2026, 9, 10, 7, 5)), "garmin-run-all-20261010-0705");
  assert.equal(defaultOutputName(new Date(2026, 0, 2, 23, 59)), "garmin-run-all-20260102-2359");
});

test("the name proposed after a run differs from the one just used", () => {
  const sameMinute = new Date(2026, 9, 11, 10, 32, 50);
  const nextMinute = new Date(2026, 9, 11, 10, 33);
  assert.equal(nextOutputName("garmin-run-all-20261011-1032", nextMinute), "garmin-run-all-20261011-1033");
  assert.equal(nextOutputName("garmin-run-all-20261011-1032", sameMinute), "garmin-run-all-20261011-1032-2");
  assert.equal(nextOutputName("garmin-run-all-20261011-1032-2", sameMinute), "garmin-run-all-20261011-1032-3");
  assert.equal(nextOutputName("garmin-run-all-20261011-1032-x", sameMinute), "garmin-run-all-20261011-1032-2");
  assert.equal(nextOutputName("My output", sameMinute), "garmin-run-all-20261011-1032");
});

test("elapsed time is shown in minutes and seconds, then hours", () => {
  assert.equal(formatElapsed(0), "0:00");
  assert.equal(formatElapsed(65.9), "1:05");
  assert.equal(formatElapsed(3725), "1:02:05");
  assert.equal(formatElapsed(-4), "0:00");
  assert.equal(formatElapsed(undefined), "0:00");
});

test("a run without progress for 30 seconds is reported as stalled", () => {
  assert.equal(stalledSeconds({ state: "running", seconds_since_progress: 31.6 }), 31);
  assert.equal(stalledSeconds({ state: "running", seconds_since_progress: 29.9 }), null);
  assert.equal(stalledSeconds({ state: "cancelling", seconds_since_progress: 99 }), null);
  assert.equal(stalledSeconds({ state: "running", seconds_since_progress: null }), null);
});

test("progress events become messages", () => {
  assert.deepEqual(progressMessage({ stage: "discovering" }), {
    key: "progress.discovering",
    params: {},
    keyParams: {},
  });
  assert.deepEqual(progressMessage({ stage: "normalizing", step: "fit" }), {
    key: "progress.normalizing",
    params: {},
    keyParams: { step: "step.fit" },
  });
  assert.deepEqual(progressMessage({ stage: "reading_fit", done: 2, total: 9 }), {
    key: "progress.reading_fit",
    params: { done: 2, total: 9 },
    keyParams: {},
  });
  for (const progress of [undefined, {}, { stage: "unknown" }, { stage: "normalizing", step: "x" }]) {
    assert.equal(progressMessage(progress).key, "progress.starting");
  }
  assert.equal(progressMessage({ stage: "toString" }).key, "progress.starting");
});

test("an error shows what happened, the next step, and its code", () => {
  assert.deepEqual(errorMessages("OUTPUT_EXISTS").map(shape), [
    ["stop.output_exists", {}, {}],
    ["next.label", {}, { step: "stop_next.output_exists" }],
    ["error.code", { code: "OUTPUT_EXISTS" }, {}],
  ]);
  assert.deepEqual(errorMessages("RUN_ALL_FAILED").map(shape), [
    ["stop.run_all_failed", {}, {}],
    ["next.label", {}, { step: "stop_next.run_again" }],
    ["error.code", { code: "RUN_ALL_FAILED" }, {}],
  ]);
  for (const code of ["NOT_A_CODE", "__proto__", "toString"]) {
    assert.deepEqual(errorMessages(code).map(shape), [
      ["error.unknown", {}, {}],
      ["next.label", {}, { step: "next.reload_page" }],
      ["error.code", { code }, {}],
    ]);
  }
  for (const code of [null, undefined, ""]) {
    assert.deepEqual(errorMessages(code).map((message) => message.key), ["error.unknown", "next.label"]);
  }
});

test("a folder or file that cannot be opened is named after the error", () => {
  // The first box shows a failed run's stop with its detail (stage B1a).
  assert.deepEqual(
    errorMessages("INPUT_NOT_READABLE", { place: "DI_CONNECT/DI-Connect-Fitness", more: 2 }).map(shape),
    [
      ["stop.input_not_readable", {}, {}],
      ["error.place", { place: "DI_CONNECT/DI-Connect-Fitness" }, {}],
      ["error.place_more", { more: 2 }, {}],
      ["next.label", {}, { step: "stop_next.input_not_readable" }],
      ["error.code", { code: "INPUT_NOT_READABLE" }, {}],
    ],
  );
  assert.deepEqual(
    errorMessages("INPUT_NOT_READABLE", { place: "", more: 0 }).map((message) => message.key),
    ["stop.input_not_readable", "error.place_input_itself", "next.label", "error.code"],
  );
  // A detail of another form names nothing.
  for (const detail of [undefined, null, {}, { place: 3 }, "DI_CONNECT"]) {
    assert.deepEqual(
      errorMessages("INPUT_NOT_READABLE", detail).map((message) => message.key),
      ["stop.input_not_readable", "next.label", "error.code"],
    );
  }
});

test("every known stop code has words of its own, a next step, and shows its code", () => {
  // Each code says what happened in words of its own (stage B2a); codes
  // share a next step only as they share it in stops.py.
  const whats = new Set();
  for (const code of Object.keys(flow.STOP_KEYS)) {
    const [what, next, quoted] = errorMessages(code);
    assert.equal(what.key, flow.STOP_KEYS[code], code);
    assert.match(what.key, /^stop\./, code);
    assert.equal(next.key, "next.label", code);
    assert.equal(next.keyParams.step, flow.STOP_NEXT_KEYS[code], code);
    assert.match(next.keyParams.step, /^stop_next\./, code);
    assert.deepEqual(shape(quoted), ["error.code", { code }, {}], code);
    whats.add(what.key);
  }
  assert.deepEqual(Object.keys(flow.STOP_NEXT_KEYS).sort(), Object.keys(flow.STOP_KEYS).sort());
  // Only the four codes of entries that could not be read share their words.
  assert.equal(whats.size, Object.keys(flow.STOP_KEYS).length - 3);
});

test("an unexpected stop of an action has words of its own", () => {
  // COMMAND_FAILED says that this app stopped while it did the action, as the
  // CLI says it of a command (stage B2a); only a code that the page does not
  // know reads as an error that it does not know.
  assert.deepEqual(errorMessages("COMMAND_FAILED").map(shape), [
    ["stop.command_failed", {}, {}],
    ["next.label", {}, { step: "stop_next.command_failed" }],
    ["error.code", { code: "COMMAND_FAILED" }, {}],
  ]);
});

test("pre-run findings say what a run would stop with, and its next step", () => {
  // Stage B2b: a finding whose code is a stop has the words and the next
  // step of that stop, as the CLI's Doctor gives the next step, and one that
  // keeps the run from starting gives its code, as a stop does.
  const finding = (code, message_id, next_action_id, severity = "ERROR") =>
    findingMessages({ code, severity, message_id, next_action_id }).map(shape);
  assert.deepEqual(
    finding("ACTIVITIES_NOT_FOUND", "REQUIRED_ACTIVITIES_SOURCE_NOT_OBSERVED", "SELECT_EXPORT_WITH_ACTIVITIES"),
    [
      ["stop.activities_not_found", {}, {}],
      ["next.label", {}, { step: "stop_next.activities_not_found" }],
      ["error.code", { code: "ACTIVITIES_NOT_FOUND" }, {}],
    ],
  );
  // Two findings have a next action that names another step; they take the
  // next step of the stop of their code.
  assert.deepEqual(
    finding("INPUT_DISCOVERY_FAILED", "INPUT_COULD_NOT_BE_SAFELY_DISCOVERED", "OBTAIN_COMPLETE_READABLE_EXPORT"),
    [
      ["stop.input_discovery_failed", {}, {}],
      ["next.label", {}, { step: "stop_next.input_discovery_failed" }],
      ["error.code", { code: "INPUT_DISCOVERY_FAILED" }, {}],
    ],
  );
  assert.deepEqual(
    finding("ACTIVITIES_EMPTY", "ACTIVITIES_FILES_HOLD_NO_RECORDS", "SELECT_EXPORT_WITH_ACTIVITIES"),
    [
      ["finding.activities_empty", {}, {}],
      ["next.label", {}, { step: "stop_next.activities_empty" }],
      ["error.code", { code: "ACTIVITIES_EMPTY" }, {}],
    ],
  );
  // A finding whose code is not a stop takes the next step of its action.
  assert.deepEqual(
    finding("INPUT_DIRECTORY_INVALID", "INPUT_DIRECTORY_MUST_BE_LOCAL_DIRECTORY", "SELECT_VALID_EXPORT_DIRECTORY"),
    [
      ["finding.input_directory", {}, {}],
      ["next.label", {}, { step: "stop_next.input_not_directory" }],
      ["error.code", { code: "INPUT_DIRECTORY_INVALID" }, {}],
    ],
  );
  assert.deepEqual(findingMessages({}).map(shape), [["error.unknown", {}, {}]]);
  // The page says itself that the export is ready, and the boxes say what to
  // do next, so neither the ready finding nor the step "run" is shown.
  assert.deepEqual(finding("RUN_ALL_NOT_EVALUATED", "INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT", "RUN_ALL", "INFO"), []);
  // A note that does not stop the run has no next step and no code.
  assert.deepEqual(
    finding("INPUT_DUPLICATE_SOURCES", "INPUT_HOLDS_THE_SAME_EXPORT_MORE_THAN_ONCE", "RUN_ALL", "WARNING"),
    [["finding.input_duplicate_sources", {}, {}]],
  );
});

test("losing the server is a problem with a next step", () => {
  assert.deepEqual(connectionMessages("status.unavailable").status, []);
  assert.deepEqual(connectionMessages("status.unavailable").problem.map(shape), [
    ["status.unavailable", {}, {}],
    ["next.label", {}, { step: "next.restart_gui" }],
  ]);
  assert.deepEqual(connectionMessages("status.unauthorized").problem.map(shape), [
    ["status.unauthorized", {}, {}],
    ["next.label", {}, { step: "next.open_terminal_address" }],
  ]);
  for (const key of ["status.connected", "status.stopped"]) {
    assert.deepEqual(connectionMessages(key), { status: [{ key, params: {}, keyParams: {} }], problem: [] });
  }
  assert.deepEqual(connectionMessages(null), { status: [], problem: [] });
});

const FINISHED = {
  state: "finished",
  output_path: "/path/to/output",
  staging_folders: [],
  result: {
    status: "PASS_WITH_WARNINGS",
    exit_code: 0,
    families: {
      sleep: { status: "SKIPPED_NOT_PRESENT", record_count: 0, warning_count: 0 },
      activities: { status: "PROCESSED", record_count: 12, warning_count: 2 },
      future_family: { status: "NEW_STATUS", record_count: 1, warning_count: 1 },
    },
  },
};

test("family rows are sorted, fall back for unknown names, and say their color", () => {
  assert.deepEqual(familyRows(FINISHED.result), [
    {
      family: "activities",
      nameKey: "family.activities",
      statusKey: "family_status.processed_with_warnings",
      kind: "warn",
      records: 12,
      warnings: 2,
    },
    { family: "future_family", nameKey: null, statusKey: "family_status.other", kind: "warn", records: 1, warnings: 1 },
    {
      family: "sleep",
      nameKey: "family.sleep",
      statusKey: "family_status.skipped_not_present",
      kind: "none",
      records: 0,
      warnings: 0,
    },
  ]);
  const clean = familyRows({
    families: {
      fit: { status: "PARTIAL", record_count: 3, warning_count: 0 },
      gear: { status: "PROCESSED", record_count: 2, warning_count: 0 },
      hrv: { status: "PROCESSED_EMPTY", record_count: 0, warning_count: 0 },
    },
  });
  assert.deepEqual(
    clean.map((row) => [row.family, row.statusKey, row.kind]),
    [
      ["fit", "family_status.partial", "warn"],
      ["gear", "family_status.processed", "ok"],
      ["hrv", "family_status.processed_empty", "ok"],
    ],
  );
  assert.deepEqual(familyRows(null), []);
});

test("the result table shows a run whose cancellation came after its output, when its result is known", () => {
  // Until stage A5c, the table was shown for a finished run only. Its last
  // row holds the warnings of no family (stage B2c).
  const rows = [...familyRows(FINISHED.result), flow.otherRow(FINISHED.result)];
  assert.deepEqual(flow.resultRows(FINISHED), rows);
  assert.deepEqual(flow.resultRows({ ...FINISHED, state: "finished_after_cancel" }), rows);
  assert.deepEqual(flow.resultRows({ state: "finished_after_cancel", result: null }), []);
  assert.deepEqual(flow.resultRows({ ...FINISHED, state: "cancelled" }), []);
  assert.deepEqual(flow.resultRows({ ...FINISHED, state: "failed" }), []);
  assert.deepEqual(flow.resultRows(null), []);
});

test("the headline of the fourth box says what the exit code means", () => {
  // Decision 20261011-15: 3 left out part of the input, 0 kept every value,
  // 2 stopped. A run cancelled before its output shows no exit code.
  const summary = (status, view) => {
    const result = flow.runSummary(status, null, view);
    return [shape(result.headline), result.exitCode, result.sub === null ? null : shape(result.sub)];
  };
  assert.deepEqual(summary(FINISHED), [
    ["result.headline_done", {}, {}],
    0,
    ["result.sub_pass_with_warnings", { warnings: 0 }, {}],
  ]);
  const partial = { ...FINISHED, result: { ...FINISHED.result, status: "PARTIAL_SUCCESS", exit_code: 3, warning_count: 8 } };
  assert.deepEqual(summary(partial), [
    ["result.headline_partial", {}, {}],
    3,
    ["result.sub_partial", { warnings: 8 }, {}],
  ]);
  const clean = { ...FINISHED, result: { ...FINISHED.result, status: "PASS", warning_count: 0 } };
  assert.deepEqual(summary(clean)[2], ["result.sub_pass", { warnings: 0 }, {}]);
  assert.deepEqual(summary({ ...partial, state: "finished_after_cancel" }), [
    ["result.headline_late", {}, { headline: "result.headline_partial" }],
    3,
    ["result.sub_late", {}, {}],
  ]);
  assert.deepEqual(summary({ state: "failed", error_code: "OUTPUT_PUBLISH_FAILED" }, { failedBox: "output" }), [
    ["result.headline_failed", {}, {}],
    2,
    ["result.sub_failed", { box: 3 }, {}],
  ]);
  assert.deepEqual(summary({ state: "cancelled" }), [
    ["result.headline_cancelled", {}, {}],
    null,
    ["result.sub_cancelled", {}, {}],
  ]);
  assert.deepEqual(summary({ state: "running", progress: { stage: "writing_output" } }), [
    ["run.headline_running", {}, {}],
    null,
    ["run.sub_running", { number: 3, total: 4 }, { step: "steps.write" }],
  ]);
  assert.deepEqual(summary({ state: "cancelling" }), [["run.headline_cancelling", {}, {}], null, null]);
  const ready = flow.runSummary({ state: "idle" }, { run: "current" });
  assert.deepEqual([shape(ready.headline), shape(ready.sub)], [["run.headline_ready", {}, {}], ["run.sub_ready", {}, {}]]);
  assert.deepEqual(shape(flow.runSummary({ state: "idle" }, { run: "todo" }).headline), ["run.headline_waiting", {}, {}]);
});

test("the details of a run name its output and the staging folders it left", () => {
  // The place has a line of its own, after its label (stage B2a).
  assert.deepEqual(flow.resultDetails(FINISHED).map(shape), [
    ["result.output_label", {}, {}],
    ["result.path", { path: "/path/to/output" }, {}],
  ]);
  assert.deepEqual(flow.resultDetails({ state: "cancelled", staging_folders: [".output.run-all-1"] }).map(shape), [
    ["result.staging_left", { names: ".output.run-all-1" }, {}],
    ["next.label", {}, { step: "next.delete_staging" }],
  ]);
  assert.deepEqual(flow.resultDetails({ state: "running" }), []);
});

test("the boxes are confirmed one at a time, and the first open one is current", () => {
  const view = { ...READY, exportReady: false, snapshotDecided: false, outputDecided: false };
  assert.deepEqual(boxStates(view), { export: "current", snapshot: "todo", output: "todo", run: "todo" });
  assert.deepEqual(boxStates({ ...view, exportReady: true }), {
    export: "done",
    snapshot: "current",
    output: "todo",
    run: "todo",
  });
  assert.deepEqual(boxStates({ ...view, exportReady: true, snapshotDecided: true }), {
    export: "done",
    snapshot: "done",
    output: "current",
    run: "todo",
  });
  assert.deepEqual(boxStates(READY), { export: "done", snapshot: "done", output: "done", run: "current" });
  // A change in the first box keeps the others' confirmation, but the boxes
  // after it wait until it is done again.
  assert.deepEqual(boxStates({ ...READY, exportReady: false }), {
    export: "current",
    snapshot: "todo",
    output: "todo",
    run: "todo",
  });
  assert.deepEqual(boxStates({ ...READY, exportProblem: true, exportReady: false }), {
    export: "error",
    snapshot: "todo",
    output: "todo",
    run: "todo",
  });
});

test("a run fills the boxes, and a stop marks the box that it concerns", () => {
  for (const runState of ["running", "cancelling"]) {
    assert.deepEqual(boxStates({ ...READY, runState }), { export: "done", snapshot: "done", output: "done", run: "current" });
  }
  for (const runState of FINISHED_STATES) {
    assert.deepEqual(boxStates({ ...READY, runState }), { export: "done", snapshot: "done", output: "done", run: "done" });
  }
  assert.deepEqual(boxStates({ ...READY, runState: "failed", failedBox: "output" }), {
    export: "done",
    snapshot: "done",
    output: "error",
    run: "stopped",
  });
  assert.deepEqual(boxStates({ ...READY, runState: "failed", failedBox: "run" }), {
    export: "done",
    snapshot: "done",
    output: "done",
    run: "error",
  });
  // A cancelled run leaves the boxes as they were set.
  assert.deepEqual(boxStates({ ...READY, runState: "cancelled" }), boxStates(READY));
  // A change after a run that finished or stopped brings back the boxes as
  // they are set, so that a changed box can be confirmed again.
  assert.deepEqual(boxStates({ ...READY, runState: "finished", editedSinceRun: true, outputDecided: false }), {
    export: "done",
    snapshot: "done",
    output: "current",
    run: "todo",
  });
  assert.deepEqual(
    boxStates({ ...READY, runState: "failed", failedBox: "output", editedSinceRun: true, outputDecided: false }),
    { export: "done", snapshot: "done", output: "current", run: "todo" },
  );
  const changed = { ...READY, runState: "finished", editedSinceRun: true, outputDecided: false };
  assert.equal(enabled(changed).decideOutput, true);
  assert.equal(enabled(changed).start, false);
  assert.equal(enabled({ ...changed, outputDecided: true }).start, true);
});

test("a stop belongs to the box of what it concerns", () => {
  assert.equal(flow.errorBox("INPUT_ZIP_CORRUPT"), "export");
  assert.equal(flow.errorBox("INPUT_CHANGED"), "export");
  assert.equal(flow.errorBox("OUTPUT_EXISTS"), "output");
  assert.equal(flow.errorBox("OUTPUT_PUBLISH_FAILED"), "output");
  assert.equal(flow.errorBox("TIMEZONE_INVALID"), "output");
  assert.equal(flow.errorBox("RUN_ALL_FAILED"), "run");
  assert.equal(flow.errorBox("DIVERGENT_DUPLICATE"), "run");
  assert.equal(flow.errorBox("SOMETHING_NEW"), "run");
  // PATH_NOT_ABSOLUTE names no field; the run request checks the Export first.
  assert.equal(flow.errorBox("PATH_NOT_ABSOLUTE", "export"), "export");
  assert.equal(flow.errorBox("PATH_NOT_ABSOLUTE", "/path/to/export"), "output");
  assert.equal(flow.errorBox("PATH_NOT_ABSOLUTE", "C:\\Exports\\export"), "output");
  for (const path of ["/path", "~/path", "C:\\path", "c:/path", "\\\\server\\share"]) {
    assert.equal(flow.looksAbsolute(path), true, path);
  }
  for (const path of ["", "relative/path", "C:relative", null]) {
    assert.equal(flow.looksAbsolute(path), false, String(path));
  }
});

test("the line of what to do next follows the boxes and the run", () => {
  const line = (view) => {
    const result = flow.nextLine(view, boxStates(view));
    return result === null ? null : shape(result);
  };
  const fresh = { ...READY, exportReady: false, checkedReady: false, snapshotDecided: false, outputDecided: false };
  assert.deepEqual(line({ ...fresh, inputFilled: false }), ["next_line.choose_export", {}, {}]);
  assert.deepEqual(line({ ...fresh, inputFilled: true }), ["next_line.check_export", {}, {}]);
  assert.deepEqual(line({ ...fresh, exportProblem: true }), ["next_line.fix_box", { box: 1 }, {}]);
  assert.deepEqual(line({ ...fresh, exportReady: true }), ["next_line.decide_snapshot", {}, {}]);
  assert.deepEqual(line({ ...fresh, exportReady: true, snapshotDecided: true }), ["next_line.decide_output", {}, {}]);
  assert.deepEqual(line(READY), ["next_line.start", {}, {}]);
  assert.deepEqual(line({ ...READY, runState: "running" }), ["next_line.running", {}, {}]);
  assert.deepEqual(line({ ...READY, starting: true }), ["next_line.running", {}, {}]);
  assert.deepEqual(line({ ...READY, runState: "cancelling" }), ["next_line.cancelling", {}, {}]);
  assert.deepEqual(line({ ...READY, runState: "cancelled" }), ["next_line.cancelled", {}, {}]);
  assert.deepEqual(line({ ...READY, runState: "failed", failedBox: "output" }), ["next_line.fix_box", { box: 3 }, {}]);
  assert.deepEqual(line({ ...READY, runState: "finished_after_cancel" }), ["next_line.late", {}, {}]);
  const finished = (result) => line({ ...READY, runState: "finished", result });
  assert.deepEqual(finished({ exit_code: 0, warning_count: 0 }), ["next_line.done", {}, {}]);
  assert.deepEqual(finished({ exit_code: 0, warning_count: 4 }), ["next_line.done_warnings", { warnings: 4 }, {}]);
  assert.deepEqual(finished({ exit_code: 3, warning_count: 8 }), ["next_line.done_partial", { warnings: 8 }, {}]);
  assert.equal(line({ ...READY, connected: false }), null);
  // After Quit, the line says that the app stopped and how to start it
  // again (v2.0.1 F2); a lost connection has its own red box.
  assert.deepEqual(line({ ...READY, connected: false, stopped: true }), ["next_line.stopped", {}, {}]);
  assert.equal(flow.nextLineKind({ ...READY, connected: false, stopped: true }, boxStates(READY)), "current");
  // After a change, the line follows the boxes again, not the last result.
  assert.deepEqual(
    line({ ...READY, runState: "finished", result: { exit_code: 0, warning_count: 4 }, editedSinceRun: true, outputDecided: false }),
    ["next_line.decide_output", {}, {}],
  );
  assert.deepEqual(line({ ...READY, runState: "finished_after_cancel", editedSinceRun: true }), ["next_line.start", {}, {}]);
  // A refused run request points at the box that it concerns.
  assert.deepEqual(line({ ...READY, requestBox: "output" }), ["next_line.fix_box", { box: 3 }, {}]);
});

test("after a run, a line under Normalize says what pressing it again does", () => {
  // v2.0.1 F2: Normalize stays enabled after a run that finished, as the
  // page was made; the line says that it normalizes again with the name in
  // the name field and that the output stays, and in the way that imports,
  // that the same export is not imported twice (the registration knows it by
  // its content). Not after a change, a stop, or a cancellation, and not
  // while Normalize cannot be pressed.
  const note = (view) => flow.againNote(view, enabled(view)).map((line) => line.key);
  const finished = { ...READY, runState: "finished", result: { exit_code: 0, warning_count: 0 } };
  assert.deepEqual(note({ ...finished, how: "single" }), ["run.again_note"]);
  assert.deepEqual(note({ ...finished, how: "rerun" }), ["run.again_note"]);
  assert.deepEqual(note({ ...finished, how: "snapshots" }), ["run.again_note", "run.again_same_export"]);
  assert.deepEqual(note({ ...finished, runState: "finished_after_cancel", how: "single" }), ["run.again_note"]);
  assert.deepEqual(note({ ...finished, editedSinceRun: true, how: "single" }), []);
  assert.deepEqual(note({ ...finished, outputBusy: true, how: "single" }), []);
  assert.deepEqual(note({ ...finished, connected: false, how: "single" }), []);
  for (const runState of ["idle", "running", "cancelled", "failed"]) {
    assert.deepEqual(note({ ...READY, runState, how: "single" }), [], runState);
  }
});

test("the line of what to do next follows the dialog, the check, and the extraction", () => {
  // Stage B3a: the page checks a chosen Export by itself, and an extracted
  // folder needs the confirmation that its extraction was complete.
  const line = (view) => shape(flow.nextLine(view, boxStates(view)));
  const fresh = { ...READY, exportReady: false, checkedReady: false, snapshotDecided: false, outputDecided: false };
  assert.deepEqual(line({ ...fresh, choosing: true }), ["next_line.choosing", {}, {}]);
  assert.deepEqual(line({ ...READY, choosing: true }), ["next_line.choosing", {}, {}]);
  assert.deepEqual(line({ ...fresh, inputFilled: true, checking: true }), ["next_line.checking", {}, {}]);
  const unconfirmed = { ...fresh, inputFilled: true, extractNeeded: true, extractConfirmed: false };
  assert.deepEqual(line(unconfirmed), ["next_line.confirm_extract", {}, {}]);
  assert.equal(boxStates(unconfirmed).export, "current");
  // Confirmed, the export box is done as soon as its check is ready.
  const confirmed = { ...unconfirmed, extractConfirmed: true, exportReady: true, checkedReady: true };
  assert.deepEqual(line(confirmed), ["next_line.decide_snapshot", {}, {}]);
  // A run stays as it is while a dialog is not open.
  assert.deepEqual(line({ ...READY, runState: "running", choosing: false }), ["next_line.running", {}, {}]);
});

test("the color of the line under the title follows what the line says", () => {
  // Stage B3a: after a change in a box, the line is about the boxes, so its
  // color no longer shows the end of the last run.
  const kind = (view) => flow.nextLineKind(view, boxStates(view));
  const warned = { exit_code: 0, warning_count: 3 };
  assert.equal(kind({ ...READY, runState: "finished", result: warned }), "warn");
  assert.equal(kind({ ...READY, runState: "finished", result: { exit_code: 0, warning_count: 0 } }), "done");
  assert.equal(kind({ ...READY, runState: "finished_after_cancel" }), "warn");
  assert.equal(kind({ ...READY, runState: "finished", result: warned, editedSinceRun: true }), "current");
  assert.equal(kind({ ...READY, runState: "finished_after_cancel", editedSinceRun: true }), "current");
  assert.equal(kind({ ...READY, runState: "finished", result: warned, choosing: true }), "current");
  assert.equal(kind({ ...READY, runState: "running" }), "current");
  assert.equal(kind({ ...READY, runState: "failed", failedBox: "output" }), "error");
  assert.equal(kind({ ...READY, runState: "finished", result: warned, editedSinceRun: true, exportProblem: true, exportReady: false }), "error");
  assert.equal(kind(READY), "current");
});

test("the lines of the check come red first, then yellow, then what the check found", () => {
  // Stage B3b: each line has its kind, and the first line of each group the
  // mark of that kind.
  const counts = { activity_records: 3506, fit_files: 3498, files_read: 3561, files_left_out: 2, files_not_read: 4 };
  const ready = { code: "RUN_ALL_NOT_EVALUATED", severity: "INFO", message_id: "INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT", next_action_id: "RUN_ALL" };
  const leftOut = { code: "DATA_FILE_LEFT_OUT", severity: "WARNING", message_id: "INPUT_FILES_CANNOT_BE_READ_AND_WILL_BE_LEFT_OUT", next_action_id: "RUN_ALL" };
  const corrupt = { code: "INPUT_ZIP_CORRUPT", severity: "ERROR", message_id: "INPUT_ZIP_DAMAGED_OR_INCOMPLETE", next_action_id: "DOWNLOAD_EXPORT_AGAIN" };
  const lines = (check) => flow.checkMessages(check).map((line) => [line.kind, line.start, line.message.key, line.message.params]);
  assert.deepEqual(lines({ kind: "zip", counts, findings: [leftOut, ready] }), [
    ["warn", true, "finding.files_left_out_count", { count: 2 }],
    ["ok", true, "check.zip_ready", { files: 3561 }],
    ["ok", false, "check.counts", { activities: 3506, fit: 3498 }],
  ]);
  assert.deepEqual(lines({ kind: "folder", counts: { ...counts, files_left_out: 0 }, findings: [ready] }), [
    ["ok", true, "check.folder_ready", {}],
    ["ok", false, "check.counts", { activities: 3506, fit: 3498 }],
  ]);
  // A stop comes first, even when the check gives it after a note.
  assert.deepEqual(lines({ kind: "zip", counts: null, findings: [leftOut, corrupt] }), [
    ["error", true, "check.not_ready", {}],
    ["error", true, "stop.input_zip_corrupt", {}],
    ["error", false, "next.label", {}],
    ["error", false, "error.code", { code: "INPUT_ZIP_CORRUPT" }],
    ["warn", true, "finding.files_left_out", {}],
  ]);
  // Without counts, the words of the check need no number.
  assert.deepEqual(lines({ kind: null, counts: null, findings: [ready] }), [["ok", true, "check.ready", {}]]);
});

test("the Exports of a mixed input are named after what happened, and can be chosen", () => {
  // Stage B3c: the Exports with the same files are counted once.
  const mixed = { code: "INPUT_MULTIPLE_EXPORTS", severity: "ERROR", message_id: "INPUT_HOLDS_MORE_THAN_ONE_EXPORT", next_action_id: "SELECT_ONE_EXPORT_OR_USE_SNAPSHOTS" };
  const exportsFound = [
    { place: "export-a", zip: false, same_as: null, path: "/in/export-a" },
    { place: "export-a.zip", zip: true, same_as: 0, path: "/in/export-a.zip" },
    { place: null, zip: false, same_as: null, path: null },
    { place: "", zip: false, same_as: null, path: null },
  ];
  const lines = flow
    .checkMessages({ kind: "folder", counts: null, exportsFound, findings: [mixed] })
    .map((line) => [line.kind, line.start, line.message.key, line.message.params, line.message.keyParams]);
  assert.deepEqual(lines, [
    ["error", true, "check.not_ready", {}, {}],
    ["error", true, "stop.input_multiple_exports", {}, {}],
    ["error", false, "check.found_count", { count: 3 }, {}],
    ["error", false, "check.found_place", { place: "export-a" }, {}],
    ["error", false, "check.found_place_same", { place: "export-a.zip", same: "export-a" }, {}],
    ["error", false, "check.found_place", {}, { place: "check.name_hidden" }],
    ["error", false, "check.found_place", {}, { place: "check.name_itself" }],
    ["error", false, "next.label", {}, { step: "stop_next.input_multiple_exports" }],
    ["error", false, "error.code", { code: "INPUT_MULTIPLE_EXPORTS" }, {}],
  ]);
  // Only the places in the chosen folder have a button.
  assert.deepEqual(
    flow.foundChoices({ exportsFound }).map((choice) => [choice.message.key, choice.message.params, choice.path]),
    [
      ["check.choose_found", { name: "export-a" }, "/in/export-a"],
      ["check.choose_found", { name: "export-a.zip" }, "/in/export-a.zip"],
    ],
  );
  // A long name is cut on its button, and many Exports are named up to 20.
  const long = "x".repeat(130);
  assert.equal(flow.foundChoices({ exportsFound: [{ place: long, zip: false, same_as: null, path: "/in/x" }] })[0].message.params.name, `${"x".repeat(120)}…`);
  const many = Array.from({ length: 23 }, (_, index) => ({ place: `export-${index}`, zip: false, same_as: null, path: `/in/export-${index}` }));
  const named = flow.checkMessages({ kind: "folder", counts: null, exportsFound: many, findings: [mixed] }).map((line) => line.message.key);
  assert.equal(named.filter((key) => key === "check.found_place").length, 20);
  assert.ok(named.includes("check.found_more"));
  assert.equal(flow.foundChoices({ exportsFound: many }).length, 20);
  // A mix without places names none.
  assert.deepEqual(
    flow.checkMessages({ kind: "folder", counts: null, exportsFound: [], findings: [mixed] }).map((line) => line.message.key),
    ["check.not_ready", "stop.input_multiple_exports", "next.label", "error.code"],
  );
});

test("a run names a folder that cannot be shown as the check does", () => {
  // Stage B3c: the server gives such a name as null.
  assert.deepEqual(
    flow.errorMessages("INPUT_NOT_READABLE", { place: null, more: 2 }).map((line) => line.key),
    ["stop.input_not_readable", "error.place_hidden", "error.place_more", "next.label", "error.code"],
  );
});

test("the check names the first folder that cannot be opened, as a run does", () => {
  // Stage B3c.
  const closed = { code: "INPUT_NOT_READABLE", severity: "ERROR", message_id: "INPUT_FOLDER_OR_FILE_CANNOT_BE_OPENED", next_action_id: "ALLOW_INPUT_ACCESS_OR_SELECT_EXPORT_FOLDER" };
  const keys = (notReadable) =>
    flow.checkMessages({ kind: "folder", counts: null, notReadable, findings: [closed] }).map((line) => [line.message.key, line.message.params]);
  assert.deepEqual(keys({ place: "DI_CONNECT/closed", more: 2 }).slice(1, 4), [
    ["stop.input_not_readable", {}],
    ["error.place", { place: "DI_CONNECT/closed" }],
    ["error.place_more", { more: 2 }],
  ]);
  assert.deepEqual(keys({ place: null, more: 0 })[2], ["error.place_hidden", {}]);
  assert.deepEqual(keys({ place: "", more: 0 })[2], ["error.place_input_itself", {}]);
  assert.deepEqual(keys(null)[2][0], "next.label");
});

test("the timezone data that the check found missing belongs to the third box", () => {
  // Stage B3b: the first box waits, as the check counts no Activities.
  const timezone = { code: "TIMEZONE_DATA_UNAVAILABLE", severity: "ERROR", message_id: "INSTALL_REQUIRED_TIMEZONE_DATA", next_action_id: "REPAIR_RUNTIME_ENVIRONMENT" };
  const ready = { code: "RUN_ALL_NOT_EVALUATED", severity: "INFO", message_id: "INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT", next_action_id: "RUN_ALL" };
  const counts = { activity_records: null, fit_files: 0, files_read: 12, files_left_out: 0, files_not_read: 0 };
  const parts = flow.checkParts({ findings: [timezone, ready] });
  assert.equal(parts.timezone, timezone);
  assert.equal(parts.stops, false);
  const lines = (check) => flow.checkMessages(check).map((line) => [line.kind, line.message.key]);
  assert.deepEqual(lines({ kind: "zip", counts, findings: [timezone, ready] }), [
    ["ok", "check.zip_ready"],
    ["info", "check.counts_later"],
  ]);
  assert.deepEqual(lines({ kind: "folder", counts, findings: [timezone, ready] }), [["info", "check.counts_later"]]);
  const view = { ...READY, exportReady: false, checkedReady: false, snapshotDecided: false, outputDecided: false, timezoneProblem: true };
  assert.deepEqual(boxStates(view), { export: "current", snapshot: "todo", output: "error", run: "todo" });
  assert.deepEqual(shape(flow.nextLine(view, boxStates(view))), ["next_line.fix_box", { box: 3 }, {}]);
  assert.equal(enabled(view).start, false);
  // A stop of the first box comes first.
  assert.equal(boxStates({ ...view, exportProblem: true }).export, "error");
});

test("a run request that the server refused marks the box that it concerns", () => {
  assert.deepEqual(boxStates({ ...READY, outputDecided: false, requestBox: "output" }), {
    export: "done",
    snapshot: "done",
    output: "error",
    run: "todo",
  });
  assert.deepEqual(boxStates({ ...READY, requestBox: "run" }), {
    export: "done",
    snapshot: "done",
    output: "done",
    run: "error",
  });
});

test("the steps table follows the stages of Run-All and the output check", () => {
  const rows = (status, check = null) => flow.stepRows(status, check).map((row) => [row.key, row.state, row.seconds]);
  assert.deepEqual(rows({ state: "idle" }), [
    ["steps.check_export", "todo", null],
    ["steps.convert", "todo", null],
    ["steps.write", "todo", null],
    ["steps.check_output", "todo", null],
  ]);
  const seconds = { discovering: 2, normalizing: 30, reading_fit: 60.5, verifying_input: 1, building_output: 3, writing_output: 4 };
  assert.deepEqual(rows({ state: "running", progress: { stage: "reading_fit" }, stage_seconds: { discovering: 2, reading_fit: 1 } }), [
    ["steps.check_export", "done", 2],
    ["steps.convert", "run", 1],
    ["steps.write", "todo", null],
    ["steps.check_output", "todo", null],
  ]);
  // Before the first stage, the first step is running.
  assert.deepEqual(rows({ state: "running", progress: {} })[0], ["steps.check_export", "run", null]);
  const finished = { state: "finished", stage_seconds: seconds, result: { warning_count: 2 } };
  assert.deepEqual(rows(finished, "running"), [
    ["steps.check_export", "done", 2],
    ["steps.convert", "warn", 94.5],
    ["steps.write", "done", 4],
    ["steps.check_output", "run", null],
  ]);
  assert.equal(rows({ ...finished, result: { warning_count: 0 } }, "done")[1][1], "done");
  // The output check is no stage of Run-All; the page measures its seconds.
  assert.deepEqual(flow.stepRows(finished, "done", 1.5)[3], { key: "steps.check_output", state: "done", seconds: 1.5 });
  assert.equal(flow.stepRows({ state: "failed" }, null, 1.5)[3].seconds, null);
  assert.equal(rows(finished, "warn")[3][1], "warn");
  assert.equal(rows(finished, "error")[3][1], "error");
  assert.deepEqual(rows({ state: "failed", progress: { stage: "writing_output" }, stage_seconds: seconds }), [
    ["steps.check_export", "done", 2],
    ["steps.convert", "done", 94.5],
    ["steps.write", "error", 4],
    ["steps.check_output", "skipped", null],
  ]);
  assert.deepEqual(rows({ state: "cancelled", progress: { stage: "normalizing" } }).map((row) => row[1]), [
    "done",
    "cancelled",
    "skipped",
    "skipped",
  ]);
  // A failure before the first stage stops the first step.
  assert.equal(rows({ state: "failed" })[0][1], "error");
});

test("a confirmed box is summed up in one line", () => {
  const view = { inputPath: "/path/to/garmin-export/", outputParent: "C:\\Garmin", outputName: " out ", runState: "idle" };
  assert.deepEqual(shape(flow.boxSummary("export", view)), ["summary.export", { name: "garmin-export" }, {}]);
  assert.deepEqual(shape(flow.boxSummary("snapshot", view)), ["summary.snapshot_single", {}, {}]);
  assert.deepEqual(shape(flow.boxSummary("output", view)), ["summary.output", { parent: "Garmin", name: "out" }, {}]);
  // After a run, the summary names the output that it made, not the name
  // proposed for the next run.
  assert.deepEqual(
    shape(flow.boxSummary("output", { ...view, runState: "finished", outputPath: "/path/to/made-output" })),
    ["summary.output_done", { parent: "to", name: "made-output" }, {}],
  );
  assert.deepEqual(
    shape(flow.boxSummary("output", { ...view, runState: "finished_after_cancel", outputPath: "C:\\Garmin\\made" })),
    ["summary.output_done", { parent: "Garmin", name: "made" }, {}],
  );
  assert.equal(flow.boxSummary("run", view), null);
  // After the page is loaded again, the field is empty: no summary without a
  // name (stage B3a).
  assert.equal(flow.boxSummary("export", { ...view, inputPath: "" }), null);
  assert.equal(flow.boxSummary("export", { ...view, inputPath: "   " }), null);
  assert.equal(flow.lastName("/"), "/");
  assert.deepEqual(flow.boxesToConfirm({ export: "done", snapshot: "current", output: "todo", run: "todo" }), [2, 3]);
  assert.deepEqual(flow.boxesToConfirm(boxStates(READY)), []);
});

const CHECKED = {
  handoff: { status: "PASS", dataset_count: 17, relationship_count: 6, warning_count: 3 },
  doctor: {
    product_status: "PASS_WITH_WARNINGS",
    usability_scope: "USABLE_WITH_DISCLOSED_WARNINGS",
    next_action_id: "REVIEW_WARNING_CODES_AND_AFFECTED_SCOPES",
    support_bundle_suggested: true,
    warning_codes: ["FIT_PARSE_INCOMPLETE", "OPTIONAL_FAMILY_NOT_PRESENT"],
  },
};

// A run with warnings of two families and of no family, one by one as the
// run gives them (stage B2c).
const WARNED = {
  status: "PASS_WITH_WARNINGS",
  exit_code: 0,
  warning_count: 5,
  families: {
    fit: { status: "PARTIAL", record_count: 3, warning_count: 1 },
    gear: { status: "SKIPPED_NOT_PRESENT", record_count: 0, warning_count: 2 },
  },
  other_warning_counts: { candidate: 0, relationship: 1, input: 1 },
  warning_items: [
    { code: "DATA_FILE_LEFT_OUT", family: null, dataset: null, count: 2 },
    { code: "RELATIONSHIP_UNRESOLVED_VALID_LINK", family: "relationships", dataset: null, count: 4 },
    { code: "OPTIONAL_FAMILY_NOT_PRESENT", family: "gear", dataset: null, count: null },
    { code: "FIT_PARSE_INCOMPLETE", family: "fit", dataset: null, count: 3 },
    { code: "VALUES_DISAGREE", family: "gear", dataset: null, count: 1234 },
  ],
};

test("the output check shows the returned counts and the warnings of the run with their counts", () => {
  // The handoff line no longer counts the warnings; the warnings of the run
  // follow, one by one, under their total (stage B2c).
  assert.deepEqual(
    outputCheckMessages(CHECKED, WARNED).map(shape),
    [
      ["output_check.handoff_pass", { datasets: 17, relationships: 6 }, {}],
      ["doctor.usability_warnings", {}, {}],
      ["next.label", {}, { step: "doctor.next_review_warnings" }],
      ["output_check.warnings", { total: 5, families: 3, kinds: 2, other: 2 }, {}],
      ["warning.fit_parse_incomplete", { count: 3, code: "FIT_PARSE_INCOMPLETE" }, { name: "family.fit" }],
      ["warning.optional_family_not_present", { count: "—", code: "OPTIONAL_FAMILY_NOT_PRESENT" }, { name: "family.gear" }],
      ["warning.values_disagree", { count: 1234, code: "VALUES_DISAGREE" }, { name: "family.gear" }],
      ["warning.relationship_unresolved", { count: 4, code: "RELATIONSHIP_UNRESOLVED_VALID_LINK" }, { name: "family.other_relationship" }],
      ["warning.data_file_left_out", { count: 2, code: "DATA_FILE_LEFT_OUT" }, { name: "family.other_input" }],
      ["output_check.bundle_suggested", {}, {}],
    ],
  );
  const counts = outputCheckMessages({ ...CHECKED, handoff: { ...CHECKED.handoff, dataset_count: 5 } }, WARNED);
  assert.equal(counts[0].params.datasets, 5);
});

test("the warnings of no family come last, and their totals come from the counts of the run", () => {
  // The totals are the counts that the run gives, never the items counted
  // again: an item that the server left out does not change them.
  const fewer = { ...WARNED, warning_items: WARNED.warning_items.slice(1, 2) };
  assert.deepEqual(flow.warningTotals(fewer), { total: 5, families: 3, kinds: 2, other: 2 });
  assert.deepEqual(flow.warningMessages(fewer).map(shape), [
    ["output_check.warnings", { total: 5, families: 3, kinds: 2, other: 2 }, {}],
    ["warning.relationship_unresolved", { count: 4, code: "RELATIONSHIP_UNRESOLVED_VALID_LINK" }, { name: "family.other_relationship" }],
  ]);
  const candidate = { ...WARNED, warning_items: [{ code: "LACTATE_CANDIDATE_AUTHORITY_UNRESOLVED", family: "lactate_threshold", dataset: null, count: 2 }] };
  assert.deepEqual(flow.warningMessages(candidate).map(shape)[1][2], { name: "family.other_candidate" });
  // A family that the page does not know keeps its own name.
  const unknown = { ...WARNED, warning_items: [{ code: "NEW_CODE", family: "future_family", dataset: null, count: 1 }] };
  assert.deepEqual(flow.warningMessages(unknown).map(shape)[1], ["warning.other", { count: 1, code: "NEW_CODE", name: "future_family" }, {}]);
  // A run without warnings has no warning lines.
  assert.deepEqual(flow.warningMessages(FINISHED.result), []);
  assert.deepEqual(flow.warningMessages(null), []);
});

test("the result table ends with the warnings of no family and the total", () => {
  assert.deepEqual(flow.otherRow(WARNED), {
    family: null,
    nameKey: "family.other",
    statusKey: "family_status.other_warnings",
    kind: "warn",
    records: null,
    warnings: 2,
  });
  assert.deepEqual(flow.otherRow(FINISHED.result).statusKey, "family_status.no_warnings");
  assert.deepEqual(flow.otherRow(FINISHED.result).kind, "none");
  assert.deepEqual(shape(flow.resultTotal({ ...FINISHED, result: WARNED })), [
    "result.total_warnings",
    { total: 5, families: 3, other: 2 },
    {},
  ]);
  assert.equal(flow.resultTotal({ ...FINISHED, state: "failed" }), null);
  assert.equal(flow.resultTotal({ state: "finished_after_cancel", result: null }), null);
  assert.equal(flow.resultTotal(null), null);
});

test("a clean output check has no warning lines and no bundle suggestion", () => {
  const clean = {
    handoff: { status: "PASS", dataset_count: 17, relationship_count: 6, warning_count: 0 },
    doctor: {
      product_status: "PASS",
      usability_scope: "FULL_WITHIN_DECLARED_CONTRACT",
      next_action_id: "OPTIONAL_CONFIRMATION",
      support_bundle_suggested: false,
      warning_codes: [],
    },
  };
  assert.deepEqual(
    outputCheckMessages(clean).map(shape).slice(1),
    [
      ["doctor.usability_full", {}, {}],
      ["next.label", {}, { step: "doctor.next_optional" }],
    ],
  );
});

test("unknown output check values fall back without failing", () => {
  assert.deepEqual(
    outputCheckMessages({
      handoff: { status: "NOT_PASS" },
      doctor: { usability_scope: "toString", next_action_id: "__proto__", warning_codes: ["NEW_CODE"] },
    }).map((message) => [message.key, message.params]),
    [["error.unknown", {}]],
  );
  assert.deepEqual(outputCheckMessages(null).map((message) => message.key), ["error.unknown"]);
  assert.deepEqual(
    outputCheckMessages(null, { warning_count: "5", warning_items: "VALUES_DISAGREE" }).map((message) => message.key),
    ["error.unknown"],
  );
});

test("output action codes have their own messages", () => {
  assert.equal(errorMessages("OUTPUT_PARENT_NOT_WRITABLE")[0].key, "stop.output_parent_not_writable");
  assert.equal(errorMessages("HANDOFF_INVALID")[0].key, "stop.handoff_invalid");
  assert.equal(errorMessages("SUPPORT_BUNDLE_EXISTS")[0].key, "stop.support_bundle_exists");
  assert.equal(errorMessages("SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED")[0].key, "stop.support_bundle_privacy_scan_failed");
  assert.equal(errorMessages("SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED")[1].keyParams.step, "stop_next.bundle_defect");
  assert.equal(errorMessages("OPEN_FAILED")[0].key, "stop.open_failed");
  assert.equal(errorMessages("PUBLISH_FAILED")[0].key, "error.unknown");
  assert.equal(errorMessages("OUTPUT_PUBLISH_FAILED")[1].keyParams.step, "stop_next.output_publish_failed");
});

test("the announcer speaks at a new stage, a stall, a cancellation, and the end", () => {
  const reading = (done, seconds = 1) => ({
    state: "running",
    progress: { stage: "reading_fit", done, total: 9 },
    seconds_since_progress: seconds,
  });
  assert.equal(announcement(reading(1)).id, announcement(reading(2)).id);
  assert.deepEqual(announcement(reading(1)).message.params, { done: 1, total: 9 });
  const building = announcement({ state: "running", progress: { stage: "building_output" } });
  assert.notEqual(building.id, announcement(reading(1)).id);
  const fit = announcement({ state: "running", progress: { stage: "normalizing", step: "fit" } });
  const gear = announcement({ state: "running", progress: { stage: "normalizing", step: "gear" } });
  assert.notEqual(fit.id, gear.id);
  assert.equal(announcement(reading(3, 31)).id, "stalled");
  assert.equal(announcement(reading(3, 45)).id, "stalled");
  assert.deepEqual(shape(announcement(reading(3, 31)).message), ["run.stalled", { seconds: 31 }, {}]);
  assert.equal(announcement({ state: "cancelling" }).id, "cancelling");
  assert.deepEqual(shape(announcement(FINISHED).message), ["result.headline_done", {}, {}]);
  assert.equal(announcement(FINISHED).id, "end:finished");
  assert.equal(announcement({ state: "failed", error_code: "INPUT_CHANGED" }).message.key, "result.headline_failed");
  assert.equal(announcement({ state: "cancelled" }).message.key, "result.headline_cancelled");
  assert.equal(announcement({ state: "idle" }), null);
  assert.equal(announcement(undefined), null);
});

test("a run that ends within its first seconds speaks only its end", () => {
  // Stage C1: a message given to the live region is spoken even after a
  // later one, so the stage waits until the run has gone on for two seconds.
  const running = (elapsed) => ({
    state: "running",
    elapsed_seconds: elapsed,
    seconds_since_progress: 0,
    progress: { stage: "reading_fit", done: 1, total: 9 },
  });
  assert.equal(flow.QUIET_START_SECONDS, 2);
  for (const elapsed of [0, 0.3, 1.9]) {
    assert.equal(announcement(running(elapsed)), null, String(elapsed));
  }
  assert.equal(announcement(running(2)).id, announcement(running(10)).id);
  assert.deepEqual(shape(announcement(running(2)).message), shape(progressMessage(running(2).progress)));
  // The end, a cancellation, and a stall are spoken at any time.
  assert.equal(announcement({ ...FINISHED, elapsed_seconds: 0.3 }).id, "end:finished");
  assert.equal(announcement({ state: "cancelling", elapsed_seconds: 0.5 }).id, "cancelling");
  assert.equal(announcement({ ...running(1), seconds_since_progress: 31 }).id, "stalled");
});

test("the end of a run moves focus only from where the run left it", () => {
  const body = { name: "body" };
  const start = { name: "start" };
  const cancel = { name: "cancel" };
  const heading = { name: "run heading" };
  const language = { name: "language" };
  const runSection = { contains: (element) => [start, cancel, heading].includes(element) };
  for (const active of [null, body, start, cancel, heading]) {
    assert.equal(shouldFocusResult(active, body, runSection), true, active?.name ?? "null");
  }
  assert.equal(shouldFocusResult(language, body, runSection), false);
});

test("the help panel has five parts, and its steps follow the boxes", () => {
  assert.deepEqual(flow.HELP_SECTIONS, ["steps", "faq", "words", "ai", "report"]);
  assert.deepEqual(flow.HELP_STEPS, ["export", "snapshot", "output", "run", "results"]);
  const first = { ...READY, exportReady: false, checkedReady: false, snapshotDecided: false, outputDecided: false };
  assert.deepEqual(flow.helpSteps(boxStates(first), "idle"), {
    export: "current",
    snapshot: "todo",
    output: "todo",
    run: "todo",
    results: "todo",
  });
  assert.deepEqual(flow.helpSteps(boxStates(READY), "idle"), {
    export: "done",
    snapshot: "done",
    output: "done",
    run: "current",
    results: "todo",
  });
  // After a run, reading the result is the step to do, and it is done once
  // START_HERE.md was opened from the page (v2.0.1 F2).
  const finished = { ...READY, runState: "finished" };
  assert.deepEqual(flow.helpSteps(boxStates(finished), "finished"), {
    export: "done",
    snapshot: "done",
    output: "done",
    run: "done",
    results: "current",
  });
  assert.equal(flow.helpSteps(boxStates(finished), "finished", true).results, "done");
  assert.equal(flow.helpSteps(boxStates({ ...READY, runState: "finished_after_cancel" }), "finished_after_cancel").results, "current");
  // A box that changed after the run is to be set again; the result is old.
  const edited = { ...finished, editedSinceRun: true, outputDecided: false };
  const editedSteps = flow.helpSteps(boxStates(edited), "finished", true);
  assert.equal(editedSteps.output, "current");
  assert.equal(editedSteps.results, "todo");
  // A stop in the third box makes it the step to do; the fourth box waits.
  const stopped = { ...READY, runState: "failed", failedBox: "output" };
  assert.deepEqual(flow.helpSteps(boxStates(stopped), "failed"), {
    export: "done",
    snapshot: "done",
    output: "current",
    run: "todo",
    results: "todo",
  });
});

test("closing the help panel returns focus to its opener while it can take focus", () => {
  assert.equal(flow.helpReturnTarget({ usable: true }), "opener");
  assert.equal(flow.helpReturnTarget({ usable: false }), "help");
  assert.equal(flow.helpReturnTarget(null), "help");
  assert.equal(flow.helpReturnTarget(undefined), "help");
});

// Stage B4a: the Snapshot Store of the second box and the folder for the
// output.
const lineShapes = (lines) => lines.map((line) => [line.kind, line.start, line.message.key]);

test("the store's lines: what the page does, the problem, the notices, the cloud, the count", () => {
  assert.deepEqual(flow.storeMessages({ choosing: true, answer: null }).map((line) => line.message.key), [
    "choose.open",
  ]);
  assert.deepEqual(lineShapes(flow.storeMessages({ busy: true, answer: { state: "store", snapshots: [] } })), [
    ["info", true, "store.checking"],
  ]);
  // Nothing is known yet.
  assert.deepEqual(flow.storeMessages({ answer: null }), []);
  // A place for a new store, which a cloud may copy; this Export alone does
  // not use the store, so the page does not say that it makes one there
  // (v2.0.1 F2).
  const place = { answer: { state: "new", path: "/x", cloud: "desktop_documents" } };
  assert.deepEqual(lineShapes(flow.storeMessages(place, "snapshots")), [
    ["warn", true, "place.cloud_desktop"],
    ["info", true, "store.new"],
  ]);
  assert.deepEqual(lineShapes(flow.storeMessages(place, "single")), [["warn", true, "place.cloud_desktop"]]);
  assert.deepEqual(lineShapes(flow.storeMessages(place)), [["warn", true, "place.cloud_desktop"]]);
  // A store with two Snapshots and both notices, in yellow.
  const opened = {
    state: "store",
    path: "/x",
    snapshots: [{ order: 1 }, { order: 2 }],
    notices: ["SNAPSHOT_REGISTRATION_INCOMPLETE", "SNAPSHOT_STORE_LOCKED"],
    cloud: null,
  };
  const lines = flow.storeMessages({ answer: opened, checked: null });
  assert.deepEqual(
    lines.filter((line) => line.start).map((line) => [line.kind, line.message.key]),
    [
      ["warn", "stop.snapshot_store_locked"],
      ["warn", "stop.snapshot_registration_incomplete"],
      ["ok", "store.count"],
    ],
  );
  assert.deepEqual(lines.at(-1).message.params, { count: 2 });
  // The check: no problem, or a problem in red, which hides the count; an
  // interrupted import is yellow, and is not named twice.
  const checked = flow.storeMessages({ answer: { ...opened, notices: [] }, checked: { state: "checked", snapshot_count: 2, notices: [] } });
  assert.deepEqual(lineShapes(checked), [["ok", true, "store.checked"]]);
  const damaged = flow.storeMessages({ answer: opened, checked: { state: "error", error_code: "SNAPSHOT_STORE_INVALID" } });
  assert.equal(damaged[0].kind, "error");
  assert.equal(damaged[0].message.key, "stop.snapshot_store_invalid");
  assert.equal(damaged.some((line) => line.kind === "ok"), false);
  const interrupted = flow.storeMessages({
    answer: opened,
    checked: { state: "error", error_code: "SNAPSHOT_REGISTRATION_INCOMPLETE" },
  });
  // The notices keep their order, also when the check found one, and no
  // line is green after a check that failed.
  assert.deepEqual(
    interrupted.filter((line) => line.start).map((line) => [line.kind, line.message.key]),
    [
      ["warn", "stop.snapshot_store_locked"],
      ["warn", "stop.snapshot_registration_incomplete"],
    ],
  );
  // An interrupted import that only the check found is said too.
  assert.deepEqual(
    lineShapes(
      flow.storeMessages({
        answer: { ...opened, notices: [] },
        checked: { state: "error", error_code: "SNAPSHOT_REGISTRATION_INCOMPLETE", notices: [] },
      }),
    ).filter((line) => line[1]),
    [["warn", true, "stop.snapshot_registration_incomplete"]],
  );
  // Without the system's dialog, the folder list opens instead.
  assert.deepEqual(lineShapes(flow.storeMessages({ chooserError: "CHOOSER_NOT_AVAILABLE", answer: null })), [
    ["info", true, "choose.list_instead"],
  ]);
  assert.equal(flow.storeMessages({ chooserError: "CHOOSER_TIMEOUT", answer: null })[0].message.key, "stop.chooser_timeout");
  // An empty store says so.
  assert.deepEqual(lineShapes(flow.storeMessages({ answer: { ...opened, snapshots: [], notices: [] } })), [
    ["ok", true, "snapshot.empty"],
  ]);
});

test("a problem of a store names the place that cannot be opened in the store", () => {
  const lines = flow.storeMessages({
    answer: {
      state: "error",
      path: "/x",
      error_code: "SNAPSHOT_STORE_NOT_READABLE",
      detail: { place: "", more: 1, store: true },
    },
  });
  assert.deepEqual(
    lines.map((line) => line.message.key),
    ["stop.snapshot_store_not_readable", "error.place_store_itself", "error.place_more", "next.label", "error.code"],
  );
  assert.equal(lines.every((line) => line.kind === "error"), true);
  // The input itself keeps its words.
  assert.equal(errorMessages("INPUT_NOT_READABLE", { place: "", more: 0 })[1].key, "error.place_input_itself");
});

test("the rows of the Snapshots, with the time of each export in local time", () => {
  const observed = "2030-01-15T02:00:00+00:00";
  const local = new Date(observed);
  const pad = (number) => String(number).padStart(2, "0");
  const expected = `${local.getFullYear()}-${pad(local.getMonth() + 1)}-${pad(local.getDate())} ${pad(local.getHours())}:${pad(local.getMinutes())}`;
  assert.deepEqual(
    flow.snapshotRows({
      state: "store",
      snapshots: [
        { order: 1, label: "S1", observed_at: observed, files: 3561 },
        { order: "2", label: null, observed_at: "not a time", files: -1.5 },
      ],
    }),
    [
      { order: 1, label: "S1", time: expected, files: 3561, state: "kept" },
      { order: 2, label: "", time: "—", files: null, state: "kept" },
    ],
  );
  assert.deepEqual(flow.snapshotRows({ state: "new", path: "/x" }), []);
  assert.deepEqual(flow.snapshotRows(null), []);
});

test("the Export that a run imports takes its place in the order of the times of the Exports", () => {
  // Stage B4b-1: an older Export imported later goes between, and the
  // numbers follow; the label that the last run imported is marked.
  const answer = {
    state: "store",
    snapshots: [
      { order: 1, label: "2030-01-01", observed_at: "2030-01-01T02:00:00+00:00", files: 10 },
      { order: 2, label: "2030-03-01", observed_at: "2030-03-01T02:00:00+00:00", files: 12 },
    ],
  };
  const rows = flow.snapshotRows(answer, { label: "2030-02-01", time: "2030-02-01T02:00:00+00:00" });
  assert.deepEqual(rows.map((row) => [row.order, row.label, row.state]), [
    [1, "2030-01-01", "kept"],
    [2, "2030-02-01", "pending"],
    [3, "2030-03-01", "kept"],
  ]);
  assert.equal(rows[1].files, null);
  // A new store holds the pending import alone.
  assert.deepEqual(
    flow.snapshotRows({ state: "new", path: "/x" }, { label: "S1", time: "2030-01-01T02:00:00+00:00" }).map((row) => [row.order, row.state]),
    [[1, "pending"]],
  );
  assert.deepEqual(flow.snapshotRows(answer, null, "2030-03-01").map((row) => row.state), ["kept", "added"]);
});

test("the fields of an import: the proposed label, the local time, and what keeps a run from starting", () => {
  assert.equal(flow.defaultSnapshotLabel("2030-01-01 02:00", []), "2030-01-01");
  assert.equal(flow.defaultSnapshotLabel("2030-01-01 02:00", ["2030-01-01", "2030-01-01-2"]), "2030-01-01-3");
  assert.equal(flow.defaultSnapshotLabel("", []), "");
  for (const label of ["2030-01-01", "S1", "a.b_c-1", "A".repeat(64)]) {
    assert.equal(flow.isValidSnapshotLabel(label), true, label);
  }
  for (const label of ["", "-x", ".x", "日本語", "a b", "A".repeat(65), null]) {
    assert.equal(flow.isValidSnapshotLabel(label), false, String(label));
  }
  const iso = flow.localTimeIso("2030-01-01 02:00");
  assert.match(iso, /^2030-01-01T02:00:00[+-]\d{2}:\d{2}$/);
  // The same instant, read back in local time.
  assert.equal(flow.exportTime(iso), "2030-01-01 02:00");
  for (const text of ["2030-02-30 02:00", "2030-01-01", "02:00", "2030/01/01 02:00", null]) {
    assert.equal(flow.localTimeIso(text), null, String(text));
  }
  assert.equal(flow.importProblem({ label: "S1", time: "2030-01-01 02:00" }, []), null);
  assert.equal(flow.importProblem({ label: "S 1", time: "2030-01-01 02:00" }, []), "SNAPSHOT_LABEL_INVALID");
  assert.equal(flow.importProblem({ label: "S1", time: "2030-01-01 02:00" }, ["S1"]), "SNAPSHOT_LABEL_EXISTS");
  assert.equal(flow.importProblem({ label: "S1", time: "soon" }, []), "SNAPSHOT_TIME_INVALID");
  assert.equal(flow.downloadSourceMessage("zip").key, "import.time_from_zip");
  assert.equal(flow.downloadSourceMessage("newest_file").key, "import.time_from_folder");
  assert.equal(flow.downloadSourceMessage("other"), null);
});

test("the steps of a Snapshot run, as the mockup v10 gives them, and the bar of an import", () => {
  const steps = (how, newStore, numbers) =>
    flow.runSteps(how, newStore, numbers).map((step) => (step.params ? [step.key, step.params] : step.key));
  const tail = ["steps.convert", "steps.write", "steps.check_output"];
  assert.deepEqual(steps("single"), ["steps.check_export", ...tail]);
  // The first import makes the store, and Run-All reads its one Snapshot.
  assert.deepEqual(steps("snapshots", true), [
    "steps.check_export", "steps.import_new", "steps.check_store", "steps.read_snapshot", ...tail,
  ]);
  // A later import names its place in the order and the Snapshots built.
  assert.deepEqual(steps("snapshots", false, { order: 2, count: 3 }), [
    "steps.check_export",
    ["steps.import_nth", { order: 2 }],
    "steps.check_store",
    ["steps.build_count", { count: 3 }],
    ...tail,
  ]);
  assert.deepEqual(steps("snapshots", false, { order: 1, count: 1 }).slice(1, 4), [
    ["steps.import_nth", { order: 1 }], "steps.check_store", "steps.read_snapshot",
  ]);
  for (const numbers of [{}, { order: 0, count: "2" }, null]) {
    assert.deepEqual(steps("snapshots", false, numbers).slice(1, 4), ["steps.import", "steps.check_store", "steps.build_snapshots"]);
  }
  assert.deepEqual(steps("rerun", false, { order: 2, count: 3 }), ["steps.check_store", "steps.build_existing", ...tail]);
  // The status of a run names its way; the step of an import and its bar.
  const status = { state: "running", how: "snapshots", progress: { stage: "importing", done: 3, total: 9 } };
  assert.deepEqual(flow.currentStep(status, "single", false, { order: 2, count: 2 }), {
    key: "steps.import_nth", params: { order: 2 }, number: 2, total: 7,
  });
  assert.deepEqual(flow.currentStep({ ...status, progress: { stage: "reading_export", done: 0, total: 9 } }), {
    key: "steps.check_export", number: 1, total: 7,
  });
  // A store that is made is a part of the import.
  assert.equal(flow.currentStep({ ...status, progress: { stage: "creating_store" } }, "snapshots", true).key, "steps.import_new");
  assert.deepEqual(flow.progressBar(status.progress), { max: 9, value: 3 });
  assert.deepEqual(flow.progressBar({ stage: "reading_export", done: 4, total: 5 }), { max: 5, value: 4 });
  assert.deepEqual(flow.progressMessage(status.progress), { key: "progress.importing", params: { done: 3, total: 9 }, keyParams: {} });
  assert.equal(flow.progressMessage({ stage: "reading_export", done: 1, total: 2 }).key, "progress.reading_export");
  assert.deepEqual(flow.progressMessage({ stage: "building_snapshots", snapshots: 3 }).params, { snapshots: 3 });
  assert.equal(flow.progressBar({ stage: "checking_store" }), null);
  const running = flow.runSummary(status, null, { how: "snapshots", newStore: false, stepNumbers: { order: 2, count: 2 } });
  assert.deepEqual(running.sub, {
    key: "run.sub_running",
    params: { number: 2, total: 7 },
    keyParams: { step: { key: "steps.import_nth", params: { order: 2 }, keyParams: {} } },
  });
  const rows = flow.stepRows({ state: "running", how: "rerun", progress: { stage: "discovering" }, stage_seconds: { checking_store: 2, building_snapshots: 3, discovering: 1 } }, null);
  assert.deepEqual(rows.map((row) => [row.key, row.state, row.seconds]).slice(0, 3), [
    ["steps.check_store", "done", 2],
    ["steps.build_existing", "run", 4],
    ["steps.convert", "todo", null],
  ]);
  const imported = flow.stepRows(
    { state: "running", how: "snapshots", progress: { stage: "checking_store" }, stage_seconds: { reading_export: 1, importing: 2 } },
    null, null, "snapshots", false, { order: 3, count: 3 },
  );
  assert.deepEqual(imported.slice(0, 4).map((row) => [row.key, row.params ?? null, row.state, row.seconds]), [
    ["steps.check_export", null, "done", 1],
    ["steps.import_nth", { order: 3 }, "done", 2],
    ["steps.check_store", null, "run", null],
    ["steps.build_count", { count: 3 }, "todo", null],
  ]);
});

test("the second box is red for a store with a problem, and the result says what the import did", () => {
  const states = boxStates({ ...READY, storeProblem: true });
  assert.equal(states.snapshot, "error");
  assert.equal(states.run, "todo");
  assert.equal(flow.nextLine({ ...READY, storeProblem: true }, states).key, "next_line.fix_box");
  assert.equal(controls({ ...READY, importProblem: "SNAPSHOT_LABEL_EXISTS" }, boxStates(READY)).start, false);
  const done = flow.resultDetails({ state: "finished", output_path: "/x", imported: { order: 2, same_content: false, snapshot_count: 3 } });
  assert.deepEqual(done.slice(2).map((line) => [line.key, line.params]), [["result.import_done", { order: 2, count: 3 }]]);
  const failed = flow.resultDetails({ state: "failed", imported: { order: 1, same_content: true, snapshot_count: 1 } });
  assert.deepEqual(failed.map((line) => line.key), ["result.import_same", "result.import_kept"]);
  assert.equal(flow.boxSummary("snapshot", { how: "snapshots", newStore: true }).key, "summary.snapshot_new");
  assert.deepEqual(flow.boxSummary("snapshot", { how: "rerun", snapshotCount: 2 }).params, { count: 2 });
  assert.equal(flow.boxSummary("export", { how: "rerun" }).key, "summary.export_rerun");
});

test("a lock file stops an import only, and normalizing again needs Snapshots", () => {
  const store = (answer, extra = {}) => ({ answer, checked: null, busy: false, ...extra });
  const locked = store({ state: "store", path: "/path/to/store", snapshots: [{ label: "S1" }], notices: ["SNAPSHOT_STORE_LOCKED"] });
  // An import takes the lock, so its file stops the import; the Snapshots
  // can still be normalized again, and this Export alone uses no store.
  assert.deepEqual(["snapshots", "rerun", "single"].map((how) => flow.storeProblem(how, locked)), [true, false, false]);
  assert.deepEqual(["snapshots", "rerun", "single"].map((how) => flow.storeReady(how, locked)), [false, true, true]);
  const kinds = (how) => flow.storeMessages(locked, how).filter((line) => line.start).map((line) => line.kind);
  assert.equal(kinds("snapshots")[0], "error");
  assert.equal(kinds("single")[0], "warn");
  const empty = store({ state: "store", path: "/path/to/store", snapshots: [], notices: [] });
  assert.deepEqual(["snapshots", "rerun"].map((how) => flow.storeProblem(how, empty)), [false, true]);
  const fresh = store({ state: "new", path: "/path/to/store" });
  assert.deepEqual(["snapshots", "rerun"].map((how) => flow.storeReady(how, fresh)), [true, false]);
  assert.equal(flow.storeReady("snapshots", { ...fresh, busy: true }), false);
  // A store that its check found damaged stops both ways that use it.
  const damaged = store({ state: "store", path: "/path/to/store", snapshots: [{ label: "S1" }], notices: [] }, {
    checked: { state: "error", error_code: "SNAPSHOT_STORE_INVALID" },
  });
  assert.deepEqual(["snapshots", "rerun", "single"].map((how) => flow.storeProblem(how, damaged)), [true, true, false]);
});

test("paths too long for the files of an import stop an import only, as a lock file does", () => {
  // On Windows without long paths (stage B6c): the notice of an open store
  // stops an import, and is yellow for the other ways; the place of a new
  // store whose files would be too long is a problem in red.
  const store = (answer) => ({ answer, checked: null, busy: false });
  const long = store({ state: "store", path: "/path/to/store", snapshots: [{ label: "S1" }], notices: ["SNAPSHOT_STORE_PATH_TOO_LONG"] });
  assert.deepEqual(["snapshots", "rerun", "single"].map((how) => flow.storeProblem(how, long)), [true, false, false]);
  const first = (how) => {
    const line = flow.storeMessages(long, how).find((item) => item.start);
    return [line.kind, line.message.key];
  };
  assert.deepEqual(first("snapshots"), ["error", "stop.snapshot_store_path_too_long"]);
  assert.deepEqual(first("rerun"), ["warn", "stop.snapshot_store_path_too_long"]);
  assert.deepEqual(first("single"), ["warn", "stop.snapshot_store_path_too_long"]);
  // Only a lock file is offered to be removed.
  assert.equal(flow.lockOffered("snapshots", long), false);
  const place = store({ state: "error", path: "/path/to/store", error_code: "SNAPSHOT_STORE_PATH_TOO_LONG" });
  assert.deepEqual(flow.storeMessages(place, "snapshots").filter((line) => line.start).map((line) => line.kind), ["error"]);
  assert.equal(flow.storeProblem("snapshots", place), true);
  assert.equal(flow.errorBox("SNAPSHOT_STORE_PATH_TOO_LONG", "/path/to/export"), "snapshot");
  // A cancelled import tells only of what an import leaves in the store.
  assert.deepEqual(flow.resultDetails({ state: "cancelled", store_notices: ["SNAPSHOT_STORE_PATH_TOO_LONG"] }), []);
});

test("the summaries of the first two boxes say what the last run did, as the mockup v10 says it", () => {
  const summary = (box, view) => {
    const words = flow.boxSummary(box, view);
    return [words.key, words.params];
  };
  const name = { name: "garmin-export.zip" };
  const before = { runState: "idle", inputPath: "/path/to/garmin-export.zip", how: "snapshots", snapshotCount: 2 };
  assert.deepEqual(summary("export", before), ["summary.export_import", name]);
  assert.deepEqual(summary("export", { ...before, how: "single" }), ["summary.export", name]);
  assert.deepEqual(summary("snapshot", before), ["summary.snapshot_import", { count: 2 }]);
  const ran = {
    ...before,
    runState: "finished",
    editedSinceRun: false,
    runHow: "snapshots",
    snapshotCount: 3,
    result: { snapshot_count: 3 },
    imported: { order: 2, same_content: false, snapshot_count: 3 },
  };
  assert.deepEqual(summary("export", ran), ["summary.export_imported", name]);
  assert.deepEqual(summary("export", { ...ran, imported: { ...ran.imported, same_content: true } }), ["summary.export_same", name]);
  assert.deepEqual(summary("snapshot", ran), ["summary.snapshot_done", { count: 3 }]);
  assert.deepEqual(summary("snapshot", { ...ran, madeStore: true }), ["summary.snapshot_new_done", {}]);
  assert.deepEqual(summary("snapshot", { ...ran, how: "rerun", runHow: "rerun", imported: null }), ["summary.snapshot_rerun_done", { count: 3 }]);
  // Once a box changed, the summaries are those of the next run.
  assert.deepEqual(summary("export", { ...ran, editedSinceRun: true }), ["summary.export_import", name]);
  assert.deepEqual(summary("snapshot", { ...ran, editedSinceRun: true }), ["summary.snapshot_import", { count: 3 }]);
});

test("the three cases of a mix have words and boxes of their own", () => {
  // A next step is a line of its own that holds the key of its words.
  const keys = (detail) =>
    flow.errorMessages("INPUT_MULTIPLE_EXPORTS", detail).map((line) => line.keyParams?.step ?? line.key);
  assert.deepEqual(keys({ mix: "other_account" }), [
    "stop.mix_other_account",
    "stop_next.mix_other_account",
    "error.code",
  ]);
  assert.deepEqual(keys({ mix: "store" }), ["stop.mix_store", "stop_next.mix_store", "error.code"]);
  // The input itself, and a case that the page does not know, have the words
  // of the code.
  for (const detail of [{ mix: "input" }, { mix: "toString" }, null]) {
    assert.deepEqual(keys(detail), ["stop.input_multiple_exports", "stop_next.input_multiple_exports", "error.code"]);
  }
  assert.equal(flow.errorBox("INPUT_MULTIPLE_EXPORTS", "/x", { mix: "other_account" }), "snapshot");
  assert.equal(flow.errorBox("INPUT_MULTIPLE_EXPORTS", "/x", { mix: "store" }), "snapshot");
  assert.equal(flow.errorBox("INPUT_MULTIPLE_EXPORTS", "/x", { mix: "input" }), "export");
  assert.equal(flow.errorBox("INPUT_MULTIPLE_EXPORTS", "/x"), "export");
});

test("the lock file that a stopped import left: its age, the offer to remove it, and the lines", () => {
  const made = "2030-01-01T00:00:00+00:00";
  const at = (minutes) => Date.parse(made) + minutes * 60000;
  const age = (minutes) => {
    const words = flow.lockAge(made, at(minutes));
    return [words.key, words.params];
  };
  assert.deepEqual(age(0.5), ["lock.made_now", {}]);
  assert.deepEqual(age(5), ["lock.made_minutes", { count: 5 }]);
  assert.deepEqual(age(119), ["lock.made_minutes", { count: 119 }]);
  assert.deepEqual(age(180), ["lock.made_hours", { count: 3 }]);
  assert.deepEqual(age(3 * 24 * 60), ["lock.made_days", { count: 3 }]);
  assert.equal(flow.lockAge("soon", at(5)), null);
  assert.equal(flow.lockAge(undefined, at(5)), null);
  const locked = { answer: { state: "store", path: "/path/to/store", snapshots: [], notices: ["SNAPSHOT_STORE_LOCKED"] } };
  assert.equal(flow.lockOffered("snapshots", locked), true);
  assert.equal(flow.lockOffered("snapshots", locked, true), false);
  assert.equal(flow.lockOffered("single", locked), false);
  assert.equal(flow.lockOffered("rerun", locked), false);
  assert.equal(flow.lockOffered("snapshots", { answer: { ...locked.answer, notices: [] } }), false);
  // After the lock file was removed, and after a stop of the removal.
  const first = (store) => flow.storeMessages(store, "snapshots")[0];
  assert.deepEqual([first({ ...locked, answer: { ...locked.answer, notices: [] }, unlocked: true }).kind, first({ ...locked, unlocked: true }).message.key], ["ok", "lock.removed"]);
  const stopped = first({ ...locked, unlockError: "SNAPSHOT_LOCK_INVALID" });
  assert.deepEqual([stopped.kind, stopped.message.key], ["error", "stop.snapshot_lock_invalid"]);
});

test("a cancelled import tells of what it left in the store", () => {
  const status = {
    state: "cancelled",
    store_notices: ["SNAPSHOT_STORE_LOCKED", "SNAPSHOT_REGISTRATION_INCOMPLETE", "/path/to/private"],
  };
  assert.deepEqual(flow.resultDetails(status).map((line) => line.keyParams?.step ?? line.key), [
    "stop.snapshot_store_locked",
    "stop_next.snapshot_store_locked",
    "stop.snapshot_registration_incomplete",
    "stop_next.snapshot_registration_incomplete",
  ]);
  assert.deepEqual(flow.resultDetails({ ...status, state: "failed" }), []);
});

test("the folder for the output: the default place that a run makes, and a cloud", () => {
  const place = { path: "/path/to/GarminRunningData", default: true, exists: false, cloud: null };
  assert.deepEqual(lineShapes(flow.placeMessages(place, "/path/to/GarminRunningData")), [
    ["info", true, "output.parent_new"],
  ]);
  assert.deepEqual(flow.placeMessages({ ...place, exists: true }, "/path/to/GarminRunningData"), []);
  // Another folder that is not there is refused when the run starts.
  assert.deepEqual(flow.placeMessages({ ...place, default: false }, "/path/to/GarminRunningData"), []);
  assert.deepEqual(lineShapes(flow.placeMessages({ ...place, exists: true, cloud: "cloud" }, "/path/to/GarminRunningData")), [
    ["warn", true, "place.cloud"],
  ]);
  // An answer for another place says nothing.
  assert.deepEqual(flow.placeMessages(place, "/elsewhere"), []);
  assert.deepEqual(flow.placeMessages(null, "/path/to/GarminRunningData"), []);
  assert.deepEqual(flow.cloudMessages("unknown"), []);
});

test("a dialog for a folder of the store or the output says so in the line above the boxes", () => {
  const states = boxStates({ ...READY, choosing: true });
  assert.equal(flow.nextLine({ ...READY, choosing: true, choosingFolder: true }, states).key, "next_line.choosing_folder");
  assert.equal(flow.nextLine({ ...READY, choosing: true }, states).key, "next_line.choosing");
});

// The settings of an earlier launch (stage B4c).
test("the settings of an earlier launch: a later launch needs a place, and the tips follow them", () => {
  assert.deepEqual(flow.launchSettings({}), {
    launch: "first",
    store: null,
    outputParent: null,
    hints: null,
    notice: null,
    present: false,
  });
  assert.deepEqual(
    flow.launchSettings({
      settings: { launch: "later", store: "/path/to/store", output_parent: "/path/to", hints: false, notice: "SETTINGS_INVALID" },
    }),
    { launch: "later", store: "/path/to/store", outputParent: "/path/to", hints: false, notice: "SETTINGS_INVALID", present: false },
  );
  // A later launch without a place, and values of another form, are not taken.
  assert.equal(flow.launchSettings({ settings: { launch: "later", store: null, output_parent: "" } }).launch, "first");
  assert.deepEqual(
    flow.launchSettings({
      settings: { launch: "later", store: 3, output_parent: "/path/to", hints: "no", notice: "/path/to/private" },
    }),
    { launch: "later", store: null, outputParent: "/path/to", hints: null, notice: null, present: false },
  );
  // The tips: as the person last switched them, otherwise on at a first
  // launch and off at a later one (the mockup v10).
  assert.equal(flow.hintsShown({ launch: "first", hints: null }), true);
  assert.equal(flow.hintsShown({ launch: "later", hints: null }), false);
  assert.equal(flow.hintsShown({ launch: "later", hints: true }), true);
  assert.equal(flow.hintsShown({ launch: "first", hints: false }), false);
});

test("on a later launch, the boxes that hold the remembered places are set by themselves", () => {
  const later = { ...READY, snapshotDecided: false, outputDecided: false, snapshotAuto: true, outputAuto: true };
  assert.deepEqual(boxStates(later), { export: "done", snapshot: "done", output: "done", run: "current" });
  assert.equal(enabled(later).start, true);
  // The Export is chosen each time.
  assert.deepEqual(boxStates({ ...later, exportReady: false }), {
    export: "current",
    snapshot: "todo",
    output: "todo",
    run: "todo",
  });
  // A box that changed is confirmed again.
  assert.deepEqual(boxStates({ ...later, snapshotAuto: false }), {
    export: "done",
    snapshot: "current",
    output: "todo",
    run: "todo",
  });
  assert.deepEqual(boxStates({ ...later, outputAuto: false }), {
    export: "done",
    snapshot: "done",
    output: "current",
    run: "todo",
  });
  // A problem of the store, and a remembered folder that is not found, are red.
  assert.equal(boxStates({ ...later, snapshotAuto: false, storeProblem: true }).snapshot, "error");
  assert.deepEqual(boxStates({ ...later, outputAuto: false, outputProblem: true }), {
    export: "done",
    snapshot: "done",
    output: "error",
    run: "todo",
  });
  assert.equal(flow.nextLine({ ...later, outputAuto: false, outputProblem: true }, boxStates({ ...later, outputAuto: false, outputProblem: true })).key, "next_line.fix_box");
  // After a run, a run starts again with the boxes that the settings set.
  const ran = { ...later, runState: "finished" };
  assert.equal(enabled(ran).start, true);
  assert.equal(enabled({ ...ran, outputAuto: false }).start, false);
});

test("a box that the settings set says so in its summary, until a run", () => {
  const view = {
    inputPath: "/path/to/export",
    outputParent: "/path/to/GarminRunningData",
    outputName: "out",
    runState: "idle",
    how: "snapshots",
    snapshotCount: 2,
    snapshotAuto: true,
    outputAuto: true,
  };
  const snapshot = flow.boxSummary("snapshot", view);
  assert.equal(snapshot.key, "summary.as_last_time");
  assert.deepEqual(shape(snapshot.keyParams.summary), ["summary.snapshot_import", { count: 2 }, {}]);
  assert.deepEqual(shape(flow.boxSummary("output", view).keyParams.summary), [
    "summary.output",
    { parent: "GarminRunningData", name: "out" },
    {},
  ]);
  // The first box is never set by the settings.
  assert.equal(flow.boxSummary("export", view).key, "summary.export_import");
  assert.equal(flow.boxSummary("snapshot", { ...view, snapshotAuto: false }).key, "summary.snapshot_import");
  // After a run, the summary says what the run did.
  assert.equal(
    flow.boxSummary("output", { ...view, runState: "finished", outputPath: "/path/to/GarminRunningData/out" }).key,
    "summary.output_done",
  );
});

test("a remembered store that is not found is not made again, and the page offers the ways on", () => {
  const remembered = "/Volumes/External/snapshots";
  const missing = {
    busy: false,
    checked: null,
    remembered,
    answer: { state: "error", path: remembered, error_code: "SNAPSHOT_STORE_NOT_FOUND" },
  };
  assert.equal(flow.storeMissingRemembered(missing), true);
  const lines = flow.storeMessages(missing, "snapshots");
  assert.deepEqual(lineShapes(lines), [
    ["error", true, "remembered.store_missing"],
    ["error", false, "next.label"],
    ["error", false, "error.code"],
  ]);
  assert.equal(lines[1].message.keyParams.step, "remembered.store_missing_next");
  assert.deepEqual(lines[2].message.params, { code: "SNAPSHOT_STORE_NOT_FOUND" });
  // Another place, or another problem, has the words of its code.
  for (const store of [
    { ...missing, remembered: null },
    { ...missing, answer: { ...missing.answer, path: "/elsewhere" } },
    { ...missing, answer: { ...missing.answer, error_code: "SNAPSHOT_STORE_NOT_READABLE" } },
  ]) {
    assert.equal(flow.storeMissingRemembered(store), false);
    assert.notEqual(flow.storeMessages(store, "snapshots")[0].message.key, "remembered.store_missing");
  }
  assert.equal(flow.storeMissingRemembered({ ...missing, answer: { state: "store", path: remembered, snapshots: [] } }), false);
});

test("a remembered folder for the output that is not found is red, but the default place is made", () => {
  const remembered = "/Volumes/External/outputs";
  const place = { path: remembered, default: false, exists: false, cloud: null };
  assert.equal(flow.outputMissingRemembered(place, remembered, remembered), true);
  const lines = flow.placeMessages(place, remembered, remembered);
  assert.deepEqual(lineShapes(lines), [
    ["error", true, "remembered.output_missing"],
    ["error", false, "next.label"],
    ["error", false, "error.code"],
  ]);
  assert.equal(lines[1].message.keyParams.step, "remembered.output_missing_next");
  assert.deepEqual(lines[2].message.params, { code: "OUTPUT_PARENT_NOT_FOUND" });
  // A folder that is not remembered is refused when the run starts, as before.
  assert.deepEqual(flow.placeMessages(place, remembered, null), []);
  assert.equal(flow.outputMissingRemembered(place, remembered, "/elsewhere"), false);
  // The remembered default place is made by a run, as on a first launch.
  const home = { path: "/path/to/GarminRunningData", default: true, exists: false, cloud: null };
  assert.equal(flow.outputMissingRemembered(home, home.path, home.path), false);
  assert.deepEqual(lineShapes(flow.placeMessages(home, home.path, home.path)), [["info", true, "output.parent_new"]]);
  // Where an output can go without a question.
  assert.equal(flow.outputPlaceUsable({ ...place, exists: true }, remembered), true);
  assert.equal(flow.outputPlaceUsable(home, home.path), true);
  assert.equal(flow.outputPlaceUsable(place, remembered), false);
  assert.equal(flow.outputPlaceUsable({ ...place, exists: null }, remembered), false);
  assert.equal(flow.outputPlaceUsable({ ...place, exists: true }, "/elsewhere"), false);
  assert.equal(flow.outputPlaceUsable(null, remembered), false);
});

test("the page tells what it could not do with the settings", () => {
  const keys = (messages) => messages.map((item) => item.key);
  assert.deepEqual(keys(flow.settingsMessages("SETTINGS_INVALID")), ["settings.invalid"]);
  assert.deepEqual(keys(flow.settingsMessages("SETTINGS_NEWER")), ["settings.newer"]);
  assert.deepEqual(keys(flow.settingsMessages("SETTINGS_NEWER", true)), ["settings.newer_kept"]);
  assert.deepEqual(keys(flow.settingsMessages("SETTINGS_NOT_WRITTEN")), ["settings.not_written"]);
  assert.deepEqual(keys(flow.settingsMessages("SETTINGS_NOT_WRITTEN", true)), ["settings.not_written"]);
  assert.deepEqual(keys(flow.settingsMessages("SETTINGS_NOT_REMOVED")), ["settings.not_removed"]);
  assert.deepEqual(flow.settingsMessages("SETTINGS_NOT_REMOVED", true), []);
  assert.deepEqual(flow.settingsMessages("/path/to/private"), []);
  assert.deepEqual(flow.settingsMessages(null), []);
  // A run that made its output says when its places could not be remembered.
  const finished = { state: "finished", output_path: "/path/to/out", settings_notice: "SETTINGS_NOT_WRITTEN" };
  assert.ok(keys(flow.resultDetails(finished)).includes("settings.not_written"));
  assert.ok(keys(flow.resultDetails({ ...finished, settings_notice: "SETTINGS_NEWER" })).includes("settings.newer_kept"));
  assert.ok(!keys(flow.resultDetails({ ...finished, settings_notice: null })).some((key) => key.startsWith("settings.")));
  assert.ok(!keys(flow.resultDetails({ ...finished, state: "failed" })).some((key) => key.startsWith("settings.")));
});

test("the settings set the boxes of a later launch, and a change in a box takes that back", () => {
  // Which boxes the settings set when the page starts.
  assert.deepEqual(flow.boxesSetBySettings({ launch: "later", store: "/path/to/store", outputParent: "/path/to" }), {
    snapshotAuto: true,
    outputAuto: true,
  });
  assert.deepEqual(flow.boxesSetBySettings({ launch: "later", store: null, outputParent: "/path/to" }), {
    snapshotAuto: false,
    outputAuto: true,
  });
  assert.deepEqual(flow.boxesSetBySettings({ launch: "first", store: "/path/to/store", outputParent: "/path/to" }), {
    snapshotAuto: false,
    outputAuto: false,
  });
  // A box is set while its place has no problem.
  const store = { busy: false, checked: null, answer: { state: "store", path: "/path/to/store", snapshots: [], notices: [] } };
  assert.equal(flow.storeSetBySettings(true, "snapshots", store), true);
  assert.equal(flow.storeSetBySettings(false, "snapshots", store), false);
  assert.equal(flow.storeSetBySettings(true, "snapshots", { ...store, busy: true }), false);
  assert.equal(
    flow.storeSetBySettings(true, "snapshots", { ...store, answer: { ...store.answer, notices: ["SNAPSHOT_STORE_LOCKED"] } }),
    false,
  );
  assert.equal(flow.storeSetBySettings(true, "snapshots", { ...store, answer: { state: "error", path: "/path/to/store", error_code: "SNAPSHOT_STORE_NOT_READABLE" } }), false);
  assert.equal(flow.storeSetBySettings(true, "snapshots", { ...store, answer: { state: "new", path: "/path/to/store" } }), false);
  const place = { path: "/path/to", default: false, exists: true, cloud: null };
  assert.equal(flow.outputSetBySettings(true, place, "/path/to"), true);
  assert.equal(flow.outputSetBySettings(true, { ...place, exists: false }, "/path/to"), false);
  assert.equal(flow.outputSetBySettings(false, place, "/path/to"), false);
  // Choosing another store or the place of a new one, or another way, is a
  // change of the second box; the folder for the output, of the third.
  assert.equal(flow.changedBox("store-open"), "snapshot");
  assert.equal(flow.changedBox("store-place"), "snapshot");
  assert.equal(flow.changedBox("how"), "snapshot");
  assert.equal(flow.changedBox("output"), "output");
  assert.equal(flow.changedBox("input"), null);
  const set = { snapshotDecided: true, snapshotAuto: true, outputDecided: true, outputAuto: true };
  assert.deepEqual(flow.afterChange("snapshot", set), { ...set, snapshotDecided: false, snapshotAuto: false });
  assert.deepEqual(flow.afterChange("output", set), { ...set, outputDecided: false, outputAuto: false });
  assert.deepEqual(flow.afterChange(null, set), set);
  // A box that the settings set shows no button to confirm it until it
  // changes, as in the mockup v10.
  assert.equal(flow.decideHidden("todo", true), true);
  assert.equal(flow.decideHidden("error", true), true);
  assert.equal(flow.decideHidden("todo", false), false);
  assert.equal(flow.decideHidden("current", false), false);
  assert.equal(flow.decideHidden("done", false), true);
  // Opening another store after the second box was confirmed asks for its
  // confirmation again, also on a first launch.
  const view = { ...READY, ...flow.afterChange(flow.changedBox("store-open"), { ...set, snapshotAuto: false }) };
  assert.equal(boxStates(view).snapshot, "current");
});

// The name of the output and the place of the Support Bundle (stage B5a).
test("a name of something that is there already is red before the run, and the page's own proposal moves on", () => {
  const place = { path: "/path/to", name: "garmin-run-all-20261018-1637", default: false, exists: true, cloud: null, name_problem: "OUTPUT_EXISTS" };
  assert.equal(flow.outputNameProblem(place, "/path/to", "garmin-run-all-20261018-1637"), "OUTPUT_EXISTS");
  // An answer for another place or another name says nothing.
  assert.equal(flow.outputNameProblem(place, "/elsewhere", "garmin-run-all-20261018-1637"), null);
  assert.equal(flow.outputNameProblem(place, "/path/to", "another"), null);
  assert.equal(flow.outputNameProblem({ ...place, name_problem: null }, "/path/to", place.name), null);
  assert.equal(flow.outputNameProblem({ ...place, name_problem: "/path/to/private" }, "/path/to", place.name), null);
  assert.equal(flow.outputNameProblem(null, "/path/to", place.name), null);
  for (const code of ["OUTPUT_SYMLINK", "OUTPUT_NAME_INVALID"]) {
    assert.equal(flow.outputNameProblem({ ...place, name_problem: code }, "/path/to", place.name), code);
  }
  // Only the page's own proposal moves on to a free name, as the name of a
  // Snapshot does; a name that the person gave stays and is red.
  assert.equal(flow.movesProposedName("OUTPUT_EXISTS", true), true);
  assert.equal(flow.movesProposedName("OUTPUT_SYMLINK", true), true);
  assert.equal(flow.movesProposedName("OUTPUT_EXISTS", false), false);
  assert.equal(flow.movesProposedName("OUTPUT_NAME_INVALID", true), false);
  assert.equal(flow.movesProposedName(null, true), false);
  assert.equal(flow.nextOutputName("garmin-run-all-20261018-1637", new Date(2026, 9, 18, 16, 37)), "garmin-run-all-20261018-1637-2");
  assert.deepEqual(lineShapes(flow.nameMessages("OUTPUT_EXISTS")), [
    ["error", true, "stop.output_exists"],
    ["error", false, "next.label"],
    ["error", false, "error.code"],
  ]);
  assert.deepEqual(flow.nameMessages(null), []);
  // The third box is red, and no run starts.
  const red = { ...READY, outputProblem: true };
  assert.equal(boxStates(red).output, "error");
  assert.equal(enabled(red).start, false);
});

test("the Support Bundle shows its file and its place before it is made", () => {
  const keys = (messages) => messages.map((item) => [item.key, item.params]);
  assert.deepEqual(keys(flow.bundlePlan("/path/to/GarminRunningData/garmin-run-all-20261018-1637", null)), [
    ["bundle.file", { name: "garmin-run-all-20261018-1637-support-bundle.zip" }],
    ["bundle.place_default", { folder: "/path/to/GarminRunningData" }],
  ]);
  assert.deepEqual(keys(flow.bundlePlan("C:\\Garmin\\out\\", "D:\\Shared")), [
    ["bundle.file", { name: "out-support-bundle.zip" }],
    ["bundle.place_chosen", { folder: "D:\\Shared" }],
  ]);
  // The External-safe Pack that a run made is named by its output, apart
  // from the line of the file of the next run.
  assert.deepEqual(keys(flow.packMade("/path/to/GarminRunningData/garmin-run-all-20261018-1637-2")), [
    ["pack.made", { path: "garmin-run-all-20261018-1637-2/analysis/external_safe_handoff.zip" }],
  ]);
  assert.deepEqual(keys(flow.packMade("C:\\Garmin\\out")), [["pack.made", { path: "out/analysis/external_safe_handoff.zip" }]]);
  assert.deepEqual(flow.packMade(null), []);
  // An output at the root of a disk.
  assert.deepEqual(keys(flow.bundlePlan("/out", null))[1], ["bundle.place_default", { folder: "/" }]);
  assert.deepEqual(keys(flow.bundlePlan("C:\\out", null))[1], ["bundle.place_default", { folder: "C:\\" }]);
  assert.deepEqual(flow.bundlePlan(null, null), []);
  assert.deepEqual(flow.bundlePlan("", "/path/to"), []);
  // The stops of its place have words of their own.
  for (const code of ["SUPPORT_BUNDLE_PARENT_NOT_FOUND", "SUPPORT_BUNDLE_INSIDE_OUTPUT", "SUPPORT_BUNDLE_NOT_WRITTEN"]) {
    const messages = flow.errorMessages(code);
    assert.notEqual(messages[0].key, "error.unknown", code);
    assert.notEqual(messages[1].keyParams.step, "next.reload_page", code);
  }
});

test("the fourth box chooses an earlier output by its number, named by its folder when two have one name", () => {
  const keys = (messages) => messages.map((item) => [item.index, item.key, item.params]);
  assert.deepEqual(
    keys(
      flow.earlierChoices([
        { index: 0, name: "garmin-run-all-20261018-1637", path: "/path/to/GarminRunningData/garmin-run-all-20261018-1637" },
        { index: 1, name: "same", path: "/path/to/a/same" },
        { index: 2, name: "same", path: "C:\\Garmin\\b\\same" },
      ]),
    ),
    [
      [0, "target.earlier_name", { name: "garmin-run-all-20261018-1637" }],
      [1, "target.earlier_with_folder", { name: "same", folder: "a" }],
      [2, "target.earlier_with_folder", { name: "same", folder: "b" }],
    ],
  );
  assert.deepEqual(flow.earlierChoices(null), []);
  assert.deepEqual(flow.earlierChoices([{ index: "0", name: "x" }, { index: 1 }]), []);
});

test("a run is compared with the output before only when both were made the same way", () => {
  const previous = {
    name: "garmin-run-all-20261017-0900",
    families: { activities: 100, sleep: 30, gear: 2 },
    snapshots: true,
    version: "2.0.0",
    run_all_version: 2,
    timezone: "Asia/Tokyo",
  };
  const current = { snapshots: true, version: "2.0.0", run_all_version: 2, timezone: "Asia/Tokyo" };
  assert.deepEqual(flow.changePlan(previous, current), { comparable: true, reasons: [] });
  // How it was normalized, the version, the checks of the version, and the
  // timezone each keep the change from showing, as the person decided.
  assert.deepEqual(flow.changePlan(previous, { ...current, snapshots: false }).reasons, ["how"]);
  assert.deepEqual(flow.changePlan(previous, { ...current, version: "2.0.1" }).reasons, ["version"]);
  assert.deepEqual(flow.changePlan(previous, { ...current, run_all_version: 3 }).reasons, ["version"]);
  assert.deepEqual(flow.changePlan(previous, { ...current, timezone: "UTC" }).reasons, ["timezone"]);
  assert.deepEqual(flow.changePlan(previous, { snapshots: false, version: "2.0.1", run_all_version: 2, timezone: "UTC" }).reasons, [
    "how",
    "version",
    "timezone",
  ]);
  assert.deepEqual(flow.changePlan({ ...previous, version: null }, current).reasons, ["version"]);
  // An output before of 1.3, or of another version, is never compared.
  assert.deepEqual(flow.changePlan({ ...previous, version: "1.3.3", run_all_version: 1 }, current).reasons, ["version"]);
  assert.deepEqual(flow.changePlan({ ...previous, version: "1.7.1", run_all_version: 1 }, { ...current, version: "1.7.1" }).reasons, ["version"]);
  assert.deepEqual(flow.changePlan(null, current), { comparable: false, reasons: [] });
  // The change of each family; none for a family that the output before
  // had not, and for the row of no family.
  const rows = flow.changeRows(
    [
      { family: "activities", records: 138 },
      { family: "sleep", records: 28 },
      { family: "gear", records: 2 },
      { family: "hrv", records: 5 },
      { family: null, records: null },
    ],
    previous,
  );
  assert.deepEqual(
    rows.map((row) => row.change),
    [38, -2, 0, null, null],
  );
  assert.deepEqual(
    [38, -2, 0, null].map((change) => flow.signedChange(change)),
    ["+38", "\u22122", "0", ""],
  );
  // Under the table and in the fourth box.
  const shapes = (lines) => lines.map((line) => [line.key, line.params]);
  const shown = flow.changeMessages(flow.changePlan(previous, current), previous, rows);
  assert.deepEqual(shapes(shown.table), [
    ["change.column", { name: "garmin-run-all-20261017-0900" }],
    ["change.note", {}],
  ]);
  assert.deepEqual(shapes(shown.run), [["change.activities_up", { count: 38 }]]);
  const fewer = flow.changeRows([{ family: "activities", records: 90 }], previous);
  assert.deepEqual(shapes(flow.changeMessages({ comparable: true, reasons: [] }, previous, fewer).run), [
    ["change.activities_down", { count: 10 }],
  ]);
  const same = flow.changeRows([{ family: "activities", records: 100 }], previous);
  assert.deepEqual(shapes(flow.changeMessages({ comparable: true, reasons: [] }, previous, same).run), [["change.activities_same", {}]]);
  const hidden = flow.changeMessages(flow.changePlan(previous, { ...current, snapshots: false, timezone: "UTC" }), previous, rows);
  assert.deepEqual(shapes(hidden.table), [
    ["change.not_compared", { name: "garmin-run-all-20261017-0900" }],
    ["change.reason_how", {}],
    ["change.reason_timezone", {}],
  ]);
  assert.deepEqual(hidden.run, []);
  assert.deepEqual(flow.changeMessages({ comparable: false, reasons: [] }, null, rows), { table: [], run: [] });
  // Before a run, the counts of the output before.
  assert.deepEqual(
    flow.previousRows(previous).map((row) => [row.family, row.records, row.statusKey, row.kind, row.warnings]),
    [
      ["activities", 100, "family_status.previous", "prev", null],
      ["gear", 2, "family_status.previous", "prev", null],
      ["sleep", 30, "family_status.previous", "prev", null],
    ],
  );
  assert.deepEqual(flow.previousRows(null), []);
});

test("an output of another version is told with its version, and one of 1.3 by its result", () => {
  const shapes = (lines) => lines.map((line) => [line.key, line.params, line.keyParams]);
  assert.deepEqual(shapes(flow.errorMessages("OUTPUT_OTHER_VERSION", { version: "1.2.1" })), [
    ["stop.output_other_version", {}, {}],
    ["error.made_by_version", { version: "1.2.1" }, {}],
    ["next.label", {}, { step: "stop_next.output_other_version" }],
    ["error.code", { code: "OUTPUT_OTHER_VERSION" }, {}],
  ]);
  assert.equal(flow.errorMessages("OUTPUT_OTHER_VERSION", null).length, 3);
  assert.equal(flow.errorMessages("OUTPUT_OTHER_VERSION", { version: "" }).length, 3);
  const check = {
    handoff: { status: "PASS", dataset_count: 17, relationship_count: 6, warning_count: 1 },
    doctor: {
      usability_scope: "USABLE_WITH_DISCLOSED_WARNINGS",
      next_action_id: "REVIEW_WARNING_CODES_AND_AFFECTED_SCOPES",
      support_bundle_suggested: true,
      legacy: true,
      product_version: "1.3.3",
    },
  };
  assert.deepEqual(
    flow.outputCheckMessages(check, null).map((line) => [line.key, line.keyParams.step ?? null]),
    [
      ["output_check.handoff_pass", null],
      ["doctor.usability_warnings", null],
      ["output_check.legacy", null],
      ["error.made_by_version", null],
      ["next.label", "output_check.legacy_next"],
    ],
  );
  assert.deepEqual(
    flow.outputCheckMessages({ ...check, doctor: { ...check.doctor, product_version: null } }, null).map((line) => line.key),
    ["output_check.handoff_pass", "doctor.usability_warnings", "output_check.legacy", "next.label"],
  );
  // The page's list of earlier outputs changed in another tab.
  assert.notEqual(flow.errorMessages("OUTPUT_LIST_CHANGED")[0].key, "error.unknown");
});

// The GitHub report and the pages outside this app (stage B5c).
const ROOT = new URL("../../", import.meta.url);
const ENGLISH = JSON.parse(
  readFileSync(new URL("src/garmin_running_data_normalizer/gui/static/i18n/en.json", ROOT), "utf-8"),
);
const english = (key) => ENGLISH[key] ?? key;
const COMPUTER = {
  operating_system: "macOS 26.5",
  python_version: "Python 3.12.6",
  package_version: "python -m garmin_running_data_normalizer 2.0.0",
};
const STOP_FACTS = {
  code: "INPUT_ZIP_CORRUPT",
  partKey: "run.start",
  exitCode: 2,
  launch: "later",
  exportKind: "zip",
  how: "snapshots",
};

test("the report has the fields of the Bug report form, in its order", () => {
  const form = readFileSync(new URL(`.github/ISSUE_TEMPLATE/${flow.REPORT_FORM}`, ROOT), "utf-8");
  const ids = [...form.matchAll(/^ {4}id: (\S+)$/gm)].map((match) => match[1]);
  assert.deepEqual(
    flow.REPORT_FIELDS.map((field) => field.id),
    ["title", ...ids.filter((id) => id !== "privacy")],
  );
  assert.equal(ids.at(-1), "privacy");
  for (const field of flow.REPORT_FIELDS) {
    assert.equal(typeof ENGLISH[field.key], "string", field.key);
  }
});

test("the report gives the values of a stop in English, and the table and the address agree", () => {
  const rows = flow.reportRows(STOP_FACTS, COMPUTER, english);
  assert.deepEqual(
    rows.map((row) => [row.id, row.value]),
    [
      ["title", "[Bug]: INPUT_ZIP_CORRUPT in the GUI"],
      ["problem", ""],
      ["guide", "GUI — Run normalization"],
      ["operating_system", "macOS 26.5"],
      ["shell", "None (run from the GUI)"],
      ["python_version", "Python 3.12.6"],
      ["package_version", "python -m garmin_running_data_normalizer 2.0.0"],
      [
        "reproduction",
        "Launch: later.\nExport: ZIP file.\nHow: import into the Snapshots and normalize them together.",
      ],
      ["exit_code", "2"],
      ["synthetic_reproduction", ""],
      ["logs", "INPUT_ZIP_CORRUPT"],
    ],
  );
  // The person writes the problem and chooses the answer of the synthetic
  // data on GitHub.
  assert.deepEqual(
    rows.filter((row) => row.person).map((row) => [row.id, row.person]),
    [
      ["problem", "report.person_writes"],
      ["synthetic_reproduction", "report.person_chooses"],
    ],
  );
  // The address carries the rows of the table that have a value, in their
  // order, and nothing else.
  const url = new URL(flow.reportUrl(rows));
  assert.equal(`${url.origin}${url.pathname}`, `${flow.REPOSITORY}/issues/new`);
  assert.deepEqual(
    [...url.searchParams],
    [["template", flow.REPORT_FORM], ...rows.filter((row) => row.value !== "").map((row) => [row.id, row.value])],
  );
  // Without a stop, from a first launch that has chosen nothing yet.
  assert.deepEqual(
    flow.reportRows({}, null, english).map((row) => [row.id, row.value]).filter(([, value]) => value !== ""),
    [
      ["title", "[Bug]: "],
      ["guide", "GUI"],
      ["shell", "None (run from the GUI)"],
      ["reproduction", "Launch: first."],
    ],
  );
  // The other ways and an extracted folder.
  assert.equal(
    flow.reportRows({ how: "single", exportKind: "folder" }, null, english)[7].value,
    "Launch: first.\nExport: extracted folder.\nHow: normalize this export only.",
  );
  assert.equal(flow.reportRows({ how: "rerun" }, null, english)[7].value, "Launch: first.\nHow: normalize the Snapshots again.");
});

test("the report carries no place, name, count, time, timezone, or account", () => {
  const facts = {
    ...STOP_FACTS,
    path: "/Volumes/Running Data/synthetic-person-q7/GarminRunningData",
    label: "synthetic-label-k4",
    name: "garmin-run-all-20300102-0304",
    timezone: "Asia/Tokyo",
    count: 98765,
    account: "synthetic-account-boundary",
    exportKind: "toString",
    how: "constructor",
  };
  const computer = {
    operating_system: "macOS 26.5\n/Volumes/synthetic-person-q7",
    python_version: "Python 3.12.6 <script>",
    package_version: "x".repeat(81),
    node: "synthetic-machine-z9",
  };
  const rows = flow.reportRows(facts, computer, english);
  const url = flow.reportUrl(rows);
  for (const text of ["synthetic", "Volumes", "Running Data", "Garmin", "20300102", "Asia", "Tokyo", "98765", "script", "xxxx"]) {
    assert.equal(url.includes(text), false, text);
    assert.equal(rows.some((row) => row.value.includes(text)), false, text);
  }
  assert.deepEqual(
    rows.map((row) => row.value).filter((value) => value !== ""),
    ["[Bug]: INPUT_ZIP_CORRUPT in the GUI", "GUI — Run normalization", "None (run from the GUI)", "Launch: later.", "2", "INPUT_ZIP_CORRUPT"],
  );
  // A code takes only the form of a code.
  for (const code of ["../x", "input_zip", "A".repeat(65), "A B", 7]) {
    assert.equal(flow.reportRows({ code }, null, english)[0].value, "[Bug]: ", String(code));
  }
  // The exit code is one that the runs give.
  assert.equal(flow.reportRows({ exitCode: 1 }, null, english)[8].value, "");
  assert.equal(flow.reportRows({ exitCode: 3 }, null, english)[8].value, "3");
});

test("the address of the report stays short", () => {
  const longest = { ...STOP_FACTS, code: `A${"_B".repeat(31)}`, partKey: "bundle.button", how: "snapshots", exportKind: "folder" };
  const computer = Object.fromEntries(Object.keys(COMPUTER).map((key) => [key, "a.".repeat(40)]));
  const url = flow.reportUrl(flow.reportRows(longest, computer, english));
  assert.equal(longest.code.length, 63);
  assert.ok(url.length <= 2000, String(url.length));
});

test("a report from the help panel or the fourth box is about the first stop shown, or the last run", () => {
  assert.deepEqual(flow.reportFacts([], { state: "idle" }), {});
  assert.deepEqual(
    flow.reportFacts(
      [
        { code: "SNAPSHOT_STORE_LOCKED", partKey: "snapshot.heading" },
        { code: "OUTPUT_PUBLISH_FAILED", partKey: "run.start" },
      ],
      { state: "failed" },
    ),
    { code: "SNAPSHOT_STORE_LOCKED", partKey: "snapshot.heading", exitCode: 2 },
  );
  assert.deepEqual(flow.reportFacts([], { state: "finished", result: { status: "PARTIAL_SUCCESS", exit_code: 3 } }), {
    code: "PARTIAL_SUCCESS",
    partKey: "run.start",
    exitCode: 3,
  });
  assert.deepEqual(flow.reportFacts(null, { state: "cancelled", result: null }), {});
});

test("the links go only to the documents of the repository and the page of Garmin", () => {
  for (const prefix of flow.OUTSIDE_PREFIXES) {
    assert.ok(prefix.startsWith("https://"), prefix);
  }
  const allowed = (url) => flow.OUTSIDE_PREFIXES.some((prefix) => url.startsWith(prefix));
  for (const document of flow.OUTSIDE_DOCUMENTS) {
    const url = flow.outsideUrl(document, "2.0.0");
    assert.equal(url, `${flow.REPOSITORY}/blob/v2.0.0/${document}`);
    assert.ok(allowed(url), url);
    // The document is in the repository, so that the tag of a release has it.
    assert.ok(existsSync(new URL(document, ROOT)), document);
  }
  assert.equal(flow.outsideUrl("garmin", null), flow.GARMIN_DATA_PAGE);
  assert.equal(flow.outsideUrl("security", null), `${flow.REPOSITORY}/security/advisories/new`);
  assert.ok(allowed(flow.reportUrl(flow.reportRows(STOP_FACTS, COMPUTER, english))));
  // A version as the releases name theirs, and nothing else.
  assert.equal(flow.outsideUrl("docs/faq.md", "2.0.0rc1"), `${flow.REPOSITORY}/blob/v2.0.0rc1/docs/faq.md`);
  for (const version of [null, "", "2.0.0.dev1", "v2.0.0", "2.0.0/../main", "02.0.0"]) {
    assert.equal(flow.outsideUrl("docs/faq.md", version), null, String(version));
  }
  for (const link of ["docs/other.md", "../README.md", "https://example.invalid/", "toString"]) {
    assert.equal(flow.outsideUrl(link, "2.0.0"), null, link);
  }
});

// The checkpoint of stage B (stage B6a).
test("the fields of an import show for the next import, not after a run until something changes", () => {
  const view = { how: "snapshots", checkedReady: true, runState: "idle", editedSinceRun: false };
  assert.equal(flow.importFieldsShown(view), true);
  assert.equal(flow.importFieldsShown({ ...view, runState: "running" }), true);
  for (const runState of FINISHED_STATES) {
    assert.equal(flow.importFieldsShown({ ...view, runState }), false, runState);
    assert.equal(flow.importFieldsShown({ ...view, runState, editedSinceRun: true }), true, runState);
  }
  // A run that stopped or was cancelled imported nothing to show.
  assert.equal(flow.importFieldsShown({ ...view, runState: "failed" }), true);
  assert.equal(flow.importFieldsShown({ ...view, runState: "cancelled" }), true);
  assert.equal(flow.importFieldsShown({ ...view, how: "single" }), false);
  assert.equal(flow.importFieldsShown({ ...view, checkedReady: false }), false);
  // A name or a time that keeps a run from starting shows with its reason,
  // also after a run (a name that the person typed and the run took).
  for (const runState of FINISHED_STATES) {
    assert.equal(flow.importFieldsShown({ ...view, runState, importProblem: "SNAPSHOT_LABEL_EXISTS" }), true, runState);
  }
  assert.equal(flow.importFieldsShown({ ...view, runState: "finished", importProblem: null }), false);
});

test("the list says that an Export of the same content adds no Snapshot while it holds the one to import", () => {
  const answer = {
    state: "store",
    snapshots: [{ label: "2030-01-01", observed_at: "2030-01-01T02:00:00+00:00", files: 3 }],
  };
  const pending = { label: "2030-01-02", time: "2030-01-02T02:00:00+00:00" };
  assert.equal(flow.sameContentNoted(flow.snapshotRows(answer, pending)), true);
  assert.equal(flow.sameContentNoted(flow.snapshotRows(answer, null)), false);
  assert.equal(flow.sameContentNoted(flow.snapshotRows(answer, null, "2030-01-01")), false);
  assert.equal(flow.sameContentNoted([]), false);
  assert.equal(flow.sameContentNoted(null), false);
  // A new store holds nothing to compare the Export with.
  assert.deepEqual(flow.snapshotRows({ state: "new" }, pending).map((row) => row.state), ["pending"]);
  assert.equal(flow.sameContentNoted(flow.snapshotRows({ state: "new" }, pending)), false);
});

test("the line of a stop's report is kept apart from the stop's lines", () => {
  const report = { text: "If this does not solve it, report it on GitHub.", className: "report", report: { code: "A", partKey: "x" } };
  const lines = ["What happened.", { text: "Code: A", className: "m-error" }, report];
  assert.deepEqual(flow.apartReport(lines), { lines: ["What happened.", { text: "Code: A", className: "m-error" }], report: [report] });
  assert.deepEqual(flow.apartReport([]), { lines: [], report: [] });
  assert.deepEqual(flow.apartReport(null), { lines: [], report: [] });
});
