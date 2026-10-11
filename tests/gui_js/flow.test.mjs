import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ACTIVE_STATES,
  ERROR_KEYS,
  FINISHED_STATES,
  TERMINAL_STATES,
  announcement,
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
  resultMessages,
  stalledSeconds,
} from "../../src/garmin_running_data_normalizer/gui/static/flow.mjs";

// A message as [key, params, keyParams], for compact comparisons.
const shape = (message) => [message.key, message.params, message.keyParams];

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
    ["error.output_exists", {}, {}],
    ["next.label", {}, { step: "next.choose_another_name" }],
    ["error.code", { code: "OUTPUT_EXISTS" }, {}],
  ]);
  assert.deepEqual(errorMessages("RUN_ALL_FAILED").map(shape), [
    ["error.internal", {}, {}],
    ["next.label", {}, { step: "next.report_code" }],
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

test("every known error code has its own next step and shows its code", () => {
  for (const code of Object.keys(ERROR_KEYS)) {
    const [what, next, quoted] = errorMessages(code);
    assert.equal(what.key, ERROR_KEYS[code], code);
    assert.equal(next.key, "next.label", code);
    assert.match(next.keyParams.step, /^next\./, code);
    assert.notEqual(next.keyParams.step, "next.reload_page", code);
    assert.deepEqual(shape(quoted), ["error.code", { code }, {}], code);
  }
});

test("pre-run findings show the finding and then the next step", () => {
  assert.deepEqual(
    findingMessages({
      message_id: "REQUIRED_ACTIVITIES_SOURCE_NOT_OBSERVED",
      next_action_id: "SELECT_EXPORT_WITH_ACTIVITIES",
    }).map(shape),
    [
      ["finding.activities_missing", {}, {}],
      ["next.label", {}, { step: "action.select_export_with_activities" }],
    ],
  );
  assert.deepEqual(findingMessages({}).map(shape), [["error.unknown", {}, {}]]);
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
    resultMessages({ state: "cancelled", staging_folders: [".output.run-all-1"] }).map(shape),
    [
      ["result.cancelled", {}, {}],
      ["next.label", {}, { step: "next.start_again" }],
      ["result.staging_left", { names: ".output.run-all-1" }, {}],
      ["next.label", {}, { step: "next.delete_staging" }],
    ],
  );
  assert.deepEqual(
    resultMessages({ state: "failed", error_code: "INPUT_CHANGED", staging_folders: [] }).map(shape),
    [
      ["result.failed", {}, {}],
      ["error.input_changed", {}, {}],
      ["next.label", {}, { step: "next.run_again_unchanged" }],
      ["error.code", { code: "INPUT_CHANGED" }, {}],
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
    outputCheckMessages(CHECKED).map(shape),
    [
      ["output_check.handoff_pass", { datasets: 17, relationships: 6, warnings: 3 }, {}],
      ["doctor.usability_warnings", {}, {}],
      ["next.label", {}, { step: "doctor.next_review_warnings" }],
      ["warning.fit_parse_incomplete", { code: "FIT_PARSE_INCOMPLETE" }, {}],
      ["warning.optional_family_not_present", { code: "OPTIONAL_FAMILY_NOT_PRESENT" }, {}],
      ["output_check.bundle_suggested", {}, {}],
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
  assert.equal(errorMessages("OUTPUT_PARENT_NOT_WRITABLE")[0].key, "error.output_parent_not_writable");
  assert.equal(errorMessages("HANDOFF_INVALID")[0].key, "error.output_changed");
  assert.equal(errorMessages("SUPPORT_BUNDLE_EXISTS")[0].key, "error.bundle_exists");
  assert.equal(errorMessages("SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED")[0].key, "error.bundle_refused");
  assert.equal(errorMessages("OPEN_FAILED")[0].key, "error.open_failed");
  assert.equal(errorMessages("PUBLISH_FAILED")[0].key, "error.unknown");
  assert.equal(errorMessages("OUTPUT_PUBLISH_FAILED")[1].keyParams.step, "next.check_space_and_path");
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
  assert.deepEqual(shape(announcement(FINISHED).message), ["result.pass_with_warnings", {}, {}]);
  assert.equal(announcement(FINISHED).id, "end:finished");
  assert.equal(announcement({ state: "failed", error_code: "INPUT_CHANGED" }).message.key, "result.failed");
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
