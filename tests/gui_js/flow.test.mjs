import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ACTIVE_STATES,
  FINISHED_STATES,
  TERMINAL_STATES,
  controls,
  defaultOutputName,
  errorMessage,
  familyRows,
  findingMessages,
  formatElapsed,
  isValidOutputName,
  outputCheckMessages,
  progressMessage,
  resultMessages,
  stalledSeconds,
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
  assert.deepEqual(FINISHED_STATES, ["finished", "finished_after_cancel"]);
});

test("a checked folder with a valid output can start a run", () => {
  assert.deepEqual(controls(READY), {
    form: true,
    browse: true,
    check: true,
    start: true,
    cancel: false,
    quit: true,
    outputActions: false,
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
    outputActions: false,
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

test("only a finished output can be checked, opened, or bundled", () => {
  for (const state of FINISHED_STATES) {
    assert.equal(controls({ ...READY, runState: state }).outputActions, true, state);
  }
  for (const state of ["idle", "running", "cancelling", "cancelled", "failed"]) {
    assert.equal(controls({ ...READY, runState: state }).outputActions, false, state);
  }
  const finished = { ...READY, runState: "finished" };
  assert.equal(controls({ ...finished, connected: false }).outputActions, false);
  assert.equal(controls({ ...finished, starting: true }).outputActions, false);
  assert.equal(controls({ ...finished, checking: true }).outputActions, false);
  const busy = controls({ ...finished, outputBusy: true });
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
  assert.deepEqual(familyRows(null), []);
});

test("result messages describe each way a run can end", () => {
  assert.deepEqual(
    resultMessages(FINISHED).map((message) => [message.key, message.params]),
    [
      ["result.pass_with_warnings", {}],
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

test("the output check shows the returned counts and one line per kind of warning", () => {
  assert.deepEqual(
    outputCheckMessages(CHECKED).map((message) => [message.key, message.params]),
    [
      ["output_check.handoff_pass", { datasets: 17, relationships: 6, warnings: 3 }],
      ["doctor.usability_warnings", {}],
      ["doctor.next_review_warnings", {}],
      ["warning.fit_parse_incomplete", { code: "FIT_PARSE_INCOMPLETE" }],
      ["warning.optional_family_not_present", { code: "OPTIONAL_FAMILY_NOT_PRESENT" }],
      ["output_check.bundle_suggested", {}],
    ],
  );
  const counts = outputCheckMessages({ ...CHECKED, handoff: { ...CHECKED.handoff, dataset_count: 5 } });
  assert.equal(counts[0].params.datasets, 5);
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
    outputCheckMessages(clean).map((message) => message.key),
    ["output_check.handoff_pass", "doctor.usability_full", "doctor.next_optional"],
  );
});

test("unknown output check values fall back without failing", () => {
  assert.deepEqual(
    outputCheckMessages({
      handoff: { status: "NOT_PASS" },
      doctor: { usability_scope: "toString", next_action_id: "__proto__", warning_codes: ["NEW_CODE"] },
    }).map((message) => [message.key, message.params]),
    [
      ["error.unknown", {}],
      ["warning.other", { code: "NEW_CODE" }],
    ],
  );
  assert.deepEqual(outputCheckMessages(null).map((message) => message.key), ["error.unknown"]);
  assert.deepEqual(
    outputCheckMessages({ doctor: { warning_codes: "FIT_PARSE_INCOMPLETE" } }).map((message) => message.key),
    ["error.unknown"],
  );
});

test("output action codes have their own messages", () => {
  assert.equal(errorMessage("OUTPUT_PARENT_NOT_WRITABLE").key, "error.output_parent_not_writable");
  assert.equal(errorMessage("HANDOFF_INVALID").key, "error.output_changed");
  assert.equal(errorMessage("SUPPORT_BUNDLE_EXISTS").key, "error.bundle_exists");
  assert.equal(errorMessage("SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED").key, "error.bundle_refused");
  assert.equal(errorMessage("OPEN_FAILED").key, "error.open_failed");
});
