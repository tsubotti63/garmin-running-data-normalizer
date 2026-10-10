import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ACTIVE_STATES,
  TERMINAL_STATES,
  controls,
  defaultOutputName,
  errorMessage,
  familyRows,
  findingMessages,
  formatElapsed,
  isValidOutputName,
  progressMessage,
  resultMessages,
  stalledSeconds,
  warningCount,
} from "../../src/garmin_running_data_normalizer/gui/static/flow.mjs";

const READY = {
  connected: true,
  runState: "idle",
  starting: false,
  checking: false,
  checkedReady: true,
  inputPath: "/path/to/export",
  outputParent: "/path/to",
  outputName: "garmin-run-all-20261010-0705",
  timezone: "Asia/Tokyo",
};

test("run states are either active or terminal", () => {
  assert.deepEqual(ACTIVE_STATES, ["running", "cancelling"]);
  assert.deepEqual(TERMINAL_STATES, ["finished", "finished_after_cancel", "cancelled", "failed"]);
});

test("a checked folder with a valid output can start a run", () => {
  assert.deepEqual(controls(READY), {
    form: true,
    browse: true,
    check: true,
    start: true,
    cancel: false,
    quit: true,
  });
});

test("nothing works without a connection", () => {
  const enabled = controls({ ...READY, connected: false });
  assert.ok(Object.values(enabled).every((value) => value === false));
});

test("a running job can only be cancelled", () => {
  assert.deepEqual(controls({ ...READY, runState: "running" }), {
    form: false,
    browse: false,
    check: false,
    start: false,
    cancel: true,
    quit: false,
  });
  const cancelling = controls({ ...READY, runState: "cancelling" });
  assert.equal(cancelling.cancel, false);
  assert.equal(cancelling.quit, false);
  assert.equal(controls({ ...READY, starting: true }).start, false);
});

test("a run needs a current successful check and a complete form", () => {
  assert.equal(controls({ ...READY, checkedReady: false }).start, false);
  assert.equal(controls({ ...READY, checking: true }).start, false);
  assert.equal(controls({ ...READY, checking: true }).check, false);
  assert.equal(controls({ ...READY, outputParent: "  " }).start, false);
  assert.equal(controls({ ...READY, timezone: "" }).start, false);
  assert.equal(controls({ ...READY, outputName: ".hidden" }).start, false);
  assert.equal(controls({ ...READY, inputPath: "" }).check, false);
  for (const state of TERMINAL_STATES) {
    assert.equal(controls({ ...READY, runState: state }).start, true, state);
  }
});

test("output names follow the server's rules", () => {
  for (const name of ["garmin-run-all-20261010-0705", "My output", "run.v2", "x".repeat(255)]) {
    assert.equal(isValidOutputName(name), true, name);
  }
  for (const name of [
    "", ".", "..", ".hidden", "a/b", "a\\b", "CON", "con.txt", "Nul", "name.", "name ",
    "a:b", "a*b", "a?b", 'a"b', "a<b", "a|b", "tab\tname", "x".repeat(256), null, 7,
  ]) {
    assert.equal(isValidOutputName(name), false, String(name));
  }
});

test("the proposed output name uses the local date and time", () => {
  assert.equal(defaultOutputName(new Date(2026, 9, 10, 7, 5)), "garmin-run-all-20261010-0705");
  assert.equal(defaultOutputName(new Date(2026, 0, 2, 23, 59)), "garmin-run-all-20260102-2359");
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

test("error codes become messages and unknown codes fall back", () => {
  assert.equal(errorMessage("OUTPUT_EXISTS").key, "error.output_exists");
  assert.equal(errorMessage("RUN_ALL_FAILED").key, "error.internal");
  for (const code of ["NOT_A_CODE", null, undefined, "__proto__", "toString"]) {
    assert.equal(errorMessage(code).key, "error.unknown");
  }
});

test("pre-run findings become a message and a next action", () => {
  assert.deepEqual(
    findingMessages({ message_id: "REQUIRED_ACTIVITIES_SOURCE_NOT_OBSERVED", next_action_id: "SELECT_EXPORT_WITH_ACTIVITIES" }),
    { message: "finding.activities_missing", action: "action.select_export_with_activities" },
  );
  assert.deepEqual(findingMessages({}), { message: "error.unknown", action: null });
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

test("family rows are sorted and fall back for unknown names", () => {
  assert.deepEqual(familyRows(FINISHED.result), [
    { family: "activities", nameKey: "family.activities", statusKey: "family_status.processed", records: 12, warnings: 2 },
    { family: "future_family", nameKey: null, statusKey: "family_status.other", records: 1, warnings: 1 },
    { family: "sleep", nameKey: "family.sleep", statusKey: "family_status.skipped_not_present", records: 0, warnings: 0 },
  ]);
  assert.equal(warningCount(FINISHED.result), 3);
  assert.deepEqual(familyRows(null), []);
});

test("result messages describe each way a run can end", () => {
  assert.deepEqual(
    resultMessages(FINISHED).map((message) => [message.key, message.params]),
    [
      ["result.pass_with_warnings", {}],
      ["result.warnings", { count: 3 }],
      ["result.output", { path: "/path/to/output" }],
    ],
  );
  assert.deepEqual(
    resultMessages({ state: "finished_after_cancel", output_path: "/path/to/output", staging_folders: [] })
      .map((message) => message.key),
    ["result.finished_after_cancel", "result.output"],
  );
  assert.deepEqual(
    resultMessages({ state: "cancelled", staging_folders: [".output.run-all-1"] })
      .map((message) => [message.key, message.params]),
    [
      ["result.cancelled", {}],
      ["result.staging_left", { names: ".output.run-all-1" }],
    ],
  );
  assert.deepEqual(
    resultMessages({ state: "failed", error_code: "INPUT_CHANGED", staging_folders: [] })
      .map((message) => [message.key, message.params]),
    [
      ["result.failed", {}],
      ["error.input_changed", {}],
      ["error.code", { code: "INPUT_CHANGED" }],
    ],
  );
  assert.deepEqual(resultMessages({ state: "running" }), []);
});
