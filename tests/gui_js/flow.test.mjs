import assert from "node:assert/strict";
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
    outputActions: false,
  });
});

test("nothing works without a connection", () => {
  const off = enabled({ ...READY, connected: false });
  assert.ok(Object.values(off).every((value) => value === false));
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
    outputActions: false,
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
  // After a change, the line follows the boxes again, not the last result.
  assert.deepEqual(
    line({ ...READY, runState: "finished", result: { exit_code: 0, warning_count: 4 }, editedSinceRun: true, outputDecided: false }),
    ["next_line.decide_output", {}, {}],
  );
  assert.deepEqual(line({ ...READY, runState: "finished_after_cancel", editedSinceRun: true }), ["next_line.start", {}, {}]);
  // A refused run request points at the box that it concerns.
  assert.deepEqual(line({ ...READY, requestBox: "output" }), ["next_line.fix_box", { box: 3 }, {}]);
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

test("the help panel has four parts, and its steps follow the boxes", () => {
  assert.deepEqual(flow.HELP_SECTIONS, ["steps", "faq", "words", "ai"]);
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
  const finished = { ...READY, runState: "finished" };
  assert.deepEqual(flow.helpSteps(boxStates(finished), "finished"), {
    export: "done",
    snapshot: "done",
    output: "done",
    run: "done",
    results: "done",
  });
  // A box that changed after the run is to be set again; the result is old.
  const edited = { ...finished, editedSinceRun: true, outputDecided: false };
  const editedSteps = flow.helpSteps(boxStates(edited), "finished");
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
