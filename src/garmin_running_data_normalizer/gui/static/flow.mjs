// Run page rules that do not touch the DOM, so that node --test can check
// them. Message keys appear here only as literal strings, so that tests can
// check them against the catalogs.

export const ACTIVE_STATES = ["running", "cancelling"];
export const TERMINAL_STATES = ["finished", "finished_after_cancel", "cancelled", "failed"];
// States in which the run published a complete output folder.
export const FINISHED_STATES = ["finished", "finished_after_cancel"];
export const STALL_SECONDS = 30;

const STAGE_KEYS = {
  discovering: "progress.discovering",
  normalizing: "progress.normalizing",
  reading_fit: "progress.reading_fit",
  verifying_input: "progress.verifying_input",
  building_output: "progress.building_output",
  writing_output: "progress.writing_output",
};

const STEP_KEYS = {
  activities: "step.activities",
  gear: "step.gear",
  personal_records: "step.personal_records",
  fit: "step.fit",
  performance_metrics: "step.performance_metrics",
  daily_metrics: "step.daily_metrics",
  relationships: "step.relationships",
};

// The words of each stop that the page shows, by code (stage B2a): what
// happened, and the next step. Codes come from the server, the run manager,
// the folder browser, Run-All, and the actions on a finished output (handoff
// check, Doctor, Support Bundle, opening). The English words come from the
// tables of stops.py (STOPS, PAGE_STOPS, and PAGE_WORDING), and the Japanese
// from the text book of stage B0; tests check the catalogs against them.
export const STOP_KEYS = {
  INPUT_ZIP_CORRUPT: "stop.input_zip_corrupt",
  INPUT_MULTIPLE_EXPORTS: "stop.input_multiple_exports",
  INPUT_TOO_LARGE: "stop.input_too_large",
  INPUT_NOT_READABLE: "stop.input_not_readable",
  INPUT_SYMLINK: "stop.input_symlink",
  INPUT_NOT_DIRECTORY: "stop.input_not_directory",
  INPUT_DISCOVERY_FAILED: "stop.input_discovery_failed",
  INPUT_CHANGED: "stop.input_changed",
  TEMP_SPACE_INSUFFICIENT: "stop.temp_space_insufficient",
  ACTIVITIES_NOT_FOUND: "stop.activities_not_found",
  ACTIVITIES_EMPTY: "stop.activities_empty",
  OUTPUT_SYMLINK: "stop.output_symlink",
  OUTPUT_PARENT_NOT_FOUND: "stop.output_parent_not_found",
  OUTPUT_NAME_INVALID: "stop.output_name_invalid",
  OUTPUT_EXISTS: "stop.output_exists",
  OUTPUT_INSIDE_INPUT: "stop.output_inside_input",
  TIMEZONE_INVALID: "stop.timezone_invalid",
  TIMEZONE_DATA_UNAVAILABLE: "stop.timezone_data_unavailable",
  OUTPUT_PARENT_NOT_WRITABLE: "stop.output_parent_not_writable",
  OUTPUT_PATH_TOO_LONG: "stop.output_path_too_long",
  OUTPUT_SPACE_INSUFFICIENT: "stop.output_space_insufficient",
  OUTPUT_PUBLISH_FAILED: "stop.output_publish_failed",
  DIVERGENT_DUPLICATE: "stop.divergent_duplicate",
  ACTIVITIES_NORMALIZATION_FAILED: "stop.activities_normalization_failed",
  GEAR_NORMALIZATION_FAILED: "stop.gear_normalization_failed",
  PERSONAL_RECORDS_NORMALIZATION_FAILED: "stop.personal_records_normalization_failed",
  FIT_PROCESSING_FAILED: "stop.fit_processing_failed",
  DAILY_METRICS_NORMALIZATION_FAILED: "stop.daily_metrics_normalization_failed",
  PERFORMANCE_METRICS_NORMALIZATION_FAILED: "stop.performance_metrics_normalization_failed",
  DATASET_NOT_SERIALIZABLE: "stop.dataset_not_serializable",
  DATASET_TABLE_INVALID: "stop.dataset_table_invalid",
  OUTPUT_CONTRACT_INVALID: "stop.output_contract_invalid",
  OUTPUT_EXPERIENCE_FAILED: "stop.output_experience_failed",
  PROVENANCE_MISMATCH: "stop.provenance_mismatch",
  RELATIONSHIP_CONTRACT_FAILED: "stop.relationship_contract_failed",
  SNAPSHOT_CONTEXT_INVALID: "stop.snapshot_context_invalid",
  STABLE_KEY_MISSING: "stop.stable_key_missing",
  RUN_ALL_FAILED: "stop.run_all_failed",
  RUN_START_FAILED: "stop.run_start_failed",
  RUN_ACTIVE: "stop.run_active",
  NO_FINISHED_OUTPUT: "stop.no_finished_output",
  HANDOFF_INVALID: "stop.handoff_invalid",
  OUTPUT_CHANGED: "stop.output_changed",
  DOCTOR_AUTHORITY_INVALID: "stop.doctor_authority_invalid",
  DOCTOR_UNREGISTERED_DIAGNOSTIC: "stop.doctor_unregistered_diagnostic",
  DOCTOR_VERSION_UNSUPPORTED: "stop.doctor_version_unsupported",
  SUPPORT_BUNDLE_AUTHORITY_INVALID: "stop.support_bundle_authority_invalid",
  OUTPUT_NOT_AVAILABLE: "stop.output_not_available",
  SUPPORT_BUNDLE_PATH_UNSAFE: "stop.support_bundle_path_unsafe",
  SUPPORT_BUNDLE_EXISTS: "stop.support_bundle_exists",
  SUPPORT_BUNDLE_NOT_WRITTEN: "stop.support_bundle_not_written",
  SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED: "stop.support_bundle_archive_validation_failed",
  SUPPORT_BUNDLE_MEMBER_SET_INVALID: "stop.support_bundle_member_set_invalid",
  SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED: "stop.support_bundle_privacy_scan_failed",
  SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED: "stop.support_bundle_size_limit_exceeded",
  SUPPORT_BUNDLE_UNCLASSIFIED_FIELD: "stop.support_bundle_unclassified_field",
  SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC: "stop.support_bundle_unregistered_diagnostic",
  OPEN_NOT_AVAILABLE: "stop.open_not_available",
  OPEN_FAILED: "stop.open_failed",
  COMMAND_FAILED: "stop.command_failed",
  PATH_NOT_ABSOLUTE: "stop.path_not_absolute",
  PATH_INVALID: "stop.request_invalid",
  INPUT_PATH_INVALID: "stop.request_invalid",
  OUTPUT_PARENT_INVALID: "stop.request_invalid",
  REQUEST_INVALID: "stop.request_invalid",
  FOLDER_NOT_FOUND: "stop.folder_not_found",
  NOT_A_FOLDER: "stop.not_a_folder",
  FOLDER_NOT_READABLE: "stop.folder_not_readable",
};

// Several codes share a next step, as they share it in stops.py.
export const STOP_NEXT_KEYS = {
  INPUT_ZIP_CORRUPT: "stop_next.input_zip_corrupt",
  INPUT_MULTIPLE_EXPORTS: "stop_next.input_multiple_exports",
  INPUT_TOO_LARGE: "stop_next.input_too_large",
  INPUT_NOT_READABLE: "stop_next.input_not_readable",
  INPUT_SYMLINK: "stop_next.input_symlink",
  INPUT_NOT_DIRECTORY: "stop_next.input_not_directory",
  INPUT_DISCOVERY_FAILED: "stop_next.input_discovery_failed",
  INPUT_CHANGED: "stop_next.input_changed",
  TEMP_SPACE_INSUFFICIENT: "stop_next.temp_space_insufficient",
  ACTIVITIES_NOT_FOUND: "stop_next.activities_not_found",
  ACTIVITIES_EMPTY: "stop_next.activities_empty",
  OUTPUT_SYMLINK: "stop_next.output_symlink",
  OUTPUT_PARENT_NOT_FOUND: "stop_next.output_parent_not_found",
  OUTPUT_NAME_INVALID: "stop_next.output_name_invalid",
  OUTPUT_EXISTS: "stop_next.output_exists",
  OUTPUT_INSIDE_INPUT: "stop_next.output_inside_input",
  TIMEZONE_INVALID: "stop_next.timezone_invalid",
  TIMEZONE_DATA_UNAVAILABLE: "stop_next.timezone_data_unavailable",
  OUTPUT_PARENT_NOT_WRITABLE: "stop_next.output_parent_not_writable",
  OUTPUT_PATH_TOO_LONG: "stop_next.output_path_too_long",
  OUTPUT_SPACE_INSUFFICIENT: "stop_next.output_space_insufficient",
  OUTPUT_PUBLISH_FAILED: "stop_next.output_publish_failed",
  DIVERGENT_DUPLICATE: "stop_next.defect",
  ACTIVITIES_NORMALIZATION_FAILED: "stop_next.defect",
  GEAR_NORMALIZATION_FAILED: "stop_next.defect",
  PERSONAL_RECORDS_NORMALIZATION_FAILED: "stop_next.defect",
  FIT_PROCESSING_FAILED: "stop_next.defect",
  DAILY_METRICS_NORMALIZATION_FAILED: "stop_next.defect",
  PERFORMANCE_METRICS_NORMALIZATION_FAILED: "stop_next.defect",
  DATASET_NOT_SERIALIZABLE: "stop_next.defect",
  DATASET_TABLE_INVALID: "stop_next.defect",
  OUTPUT_CONTRACT_INVALID: "stop_next.defect",
  OUTPUT_EXPERIENCE_FAILED: "stop_next.defect",
  PROVENANCE_MISMATCH: "stop_next.defect",
  RELATIONSHIP_CONTRACT_FAILED: "stop_next.defect",
  SNAPSHOT_CONTEXT_INVALID: "stop_next.defect",
  STABLE_KEY_MISSING: "stop_next.defect",
  RUN_ALL_FAILED: "stop_next.run_again",
  RUN_START_FAILED: "stop_next.run_again",
  RUN_ACTIVE: "stop_next.run_active",
  NO_FINISHED_OUTPUT: "stop_next.no_finished_output",
  HANDOFF_INVALID: "stop_next.new_output",
  OUTPUT_CHANGED: "stop_next.output_changed",
  DOCTOR_AUTHORITY_INVALID: "stop_next.new_output",
  DOCTOR_UNREGISTERED_DIAGNOSTIC: "stop_next.doctor_version",
  DOCTOR_VERSION_UNSUPPORTED: "stop_next.doctor_version",
  SUPPORT_BUNDLE_AUTHORITY_INVALID: "stop_next.support_bundle_authority_invalid",
  OUTPUT_NOT_AVAILABLE: "stop_next.output_where",
  SUPPORT_BUNDLE_PATH_UNSAFE: "stop_next.output_where",
  SUPPORT_BUNDLE_EXISTS: "stop_next.support_bundle_exists",
  SUPPORT_BUNDLE_NOT_WRITTEN: "stop_next.support_bundle_not_written",
  SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED: "stop_next.bundle_defect",
  SUPPORT_BUNDLE_MEMBER_SET_INVALID: "stop_next.bundle_defect",
  SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED: "stop_next.bundle_defect",
  SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED: "stop_next.bundle_defect",
  SUPPORT_BUNDLE_UNCLASSIFIED_FIELD: "stop_next.bundle_defect",
  SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC: "stop_next.bundle_defect",
  OPEN_NOT_AVAILABLE: "stop_next.open_manually",
  OPEN_FAILED: "stop_next.open_manually",
  COMMAND_FAILED: "stop_next.command_failed",
  PATH_NOT_ABSOLUTE: "stop_next.path_not_absolute",
  PATH_INVALID: "stop_next.request_invalid",
  INPUT_PATH_INVALID: "stop_next.request_invalid",
  OUTPUT_PARENT_INVALID: "stop_next.request_invalid",
  REQUEST_INVALID: "stop_next.request_invalid",
  FOLDER_NOT_FOUND: "stop_next.folder_not_found",
  NOT_A_FOLDER: "stop_next.not_a_folder",
  FOLDER_NOT_READABLE: "stop_next.folder_not_readable",
};

// A pre-run finding says what a run would stop with in the words of the stop
// of its code, or in words of its own when its code is not a stop or when it
// does not stop a run (stage B2b). The page says itself that an Export can be
// normalized, so the ready finding shows nothing (null).
export const FINDING_KEYS = {
  INPUT_DIRECTORY_MUST_BE_LOCAL_DIRECTORY: "finding.input_directory",
  INSTALL_REQUIRED_TIMEZONE_DATA: "stop.timezone_data_unavailable",
  INPUT_COULD_NOT_BE_SAFELY_DISCOVERED: "stop.input_discovery_failed",
  INPUT_FOLDER_OR_FILE_CANNOT_BE_OPENED: "stop.input_not_readable",
  INPUT_ZIP_DAMAGED_OR_INCOMPLETE: "stop.input_zip_corrupt",
  INPUT_HOLDS_MORE_THAN_ONE_EXPORT: "stop.input_multiple_exports",
  INPUT_HOLDS_THE_SAME_EXPORT_MORE_THAN_ONCE: "finding.input_duplicate_sources",
  INPUT_FILES_CANNOT_BE_READ_AND_WILL_BE_LEFT_OUT: "finding.files_left_out",
  INPUT_ZIP_TOO_LARGE_TO_READ_DIRECTLY: "stop.input_too_large",
  TEMP_FOLDER_SPACE_INSUFFICIENT: "stop.temp_space_insufficient",
  REQUIRED_ACTIVITIES_SOURCE_NOT_OBSERVED: "stop.activities_not_found",
  ACTIVITIES_FILES_CANNOT_BE_READ: "finding.activities_unreadable",
  ACTIVITIES_FILES_HOLD_NO_RECORDS: "finding.activities_empty",
  INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT: null,
};
// A finding's next step is that of the stop of its code (STOP_NEXT_KEYS), as
// the CLI's Doctor gives it; these are the next actions of the findings whose
// code is not a stop. The boxes say what to do when nothing stops a run, so
// the step "run" shows nothing (null).
export const ACTION_KEYS = {
  SELECT_VALID_EXPORT_DIRECTORY: "stop_next.input_not_directory",
  RUN_ALL: null,
};

export const FAMILY_KEYS = {
  activities: "family.activities",
  acute_training_load: "family.acute_training_load",
  endurance_score: "family.endurance_score",
  fit: "family.fit",
  gear: "family.gear",
  hill_score: "family.hill_score",
  hrv: "family.hrv",
  personal_records: "family.personal_records",
  race_prediction: "family.race_prediction",
  sleep: "family.sleep",
  training_history: "family.training_history",
  training_readiness: "family.training_readiness",
  uds: "family.uds",
  vo2max: "family.vo2max",
};
export const FAMILY_STATUS_KEYS = {
  PROCESSED: "family_status.processed",
  PROCESSED_EMPTY: "family_status.processed_empty",
  SKIPPED_NOT_PRESENT: "family_status.skipped_not_present",
  PARTIAL: "family_status.partial",
};
// The color of a row of the result table: only a problem fills a row; a
// warning or a family that the Export does not hold is marked otherwise.
const FAMILY_STATUS_KINDS = {
  PROCESSED: "ok",
  PROCESSED_EMPTY: "ok",
  SKIPPED_NOT_PRESENT: "none",
  PARTIAL: "warn",
};
const RESULT_SUB_KEYS = {
  PASS: "result.sub_pass",
  PASS_WITH_WARNINGS: "result.sub_pass_with_warnings",
  PARTIAL_SUCCESS: "result.sub_partial",
};

// Post-run Doctor values for a completed run, and the registered warnings.
export const USABILITY_KEYS = {
  FULL_WITHIN_DECLARED_CONTRACT: "doctor.usability_full",
  USABLE_WITH_DISCLOSED_WARNINGS: "doctor.usability_warnings",
  BOUNDED_WITH_DISCLOSED_EXCLUSIONS: "doctor.usability_bounded",
};
export const NEXT_ACTION_KEYS = {
  OPTIONAL_CONFIRMATION: "doctor.next_optional",
  REVIEW_WARNING_CODES_AND_AFFECTED_SCOPES: "doctor.next_review_warnings",
  REVIEW_EXCLUDED_FIT_EVIDENCE: "doctor.next_review_left_out",
};
export const WARNING_KEYS = {
  ACTIVITY_FIT_LINK_AMBIGUOUS: "warning.activity_fit_link_ambiguous",
  OPTIONAL_FAMILY_NOT_PRESENT: "warning.optional_family_not_present",
  OPTIONAL_FAMILY_EMPTY: "warning.optional_family_empty",
  DAILY_METRICS_REVIEW_REQUIRED: "warning.daily_metrics_review",
  VALUES_DISAGREE: "warning.values_disagree",
  VALUES_UPDATED: "warning.values_updated",
  RECORDS_NOT_IN_LATEST_SNAPSHOT: "warning.records_not_in_latest_snapshot",
  INPUT_DUPLICATE_SOURCES: "warning.input_duplicate_sources",
  DATA_FILE_LEFT_OUT: "warning.data_file_left_out",
  DATA_ROW_LEFT_OUT: "warning.data_row_left_out",
  DATA_VALUE_INVALID: "warning.data_value_invalid",
  DATA_TEXT_REPAIRED: "warning.data_text_repaired",
  FIT_PARSE_INCOMPLETE: "warning.fit_parse_incomplete",
  LACTATE_CANDIDATE_AUTHORITY_UNRESOLVED: "warning.lactate_candidates",
  RELATIONSHIP_UNRESOLVED_VALID_LINK: "warning.relationship_unresolved",
  RELATIONSHIP_UNRESOLVED_INVALID_LINK: "warning.relationship_invalid_link",
};

const WINDOWS_RESERVED_NAMES = new Set([
  "CON", "PRN", "AUX", "NUL",
  "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
  "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
]);
const INVALID_NAME_CHARACTERS = /[<>:"\/\\|?*\u0000-\u001f]/;

function lookup(table, name, fallback) {
  return typeof name === "string" && Object.hasOwn(table, name) ? table[name] : fallback;
}

// A message is a key, its plain parameters, and parameters that are message
// keys themselves; the page translates both.
function nextStep(step) {
  return { key: "next.label", params: {}, keyParams: { step } };
}

// What happened, what to do next, and the code to quote when asking for help.
// ``detail`` names, for a folder or file of the input that cannot be opened,
// its place inside the input ("" is the input itself) and how many more.
export function errorMessages(code, detail) {
  const key = lookup(STOP_KEYS, code, "error.unknown");
  const messages = [{ key, params: {}, keyParams: {} }];
  if (typeof detail?.place === "string") {
    messages.push(
      detail.place === ""
        ? { key: "error.place_input_itself", params: {}, keyParams: {} }
        : { key: "error.place", params: { place: detail.place }, keyParams: {} },
    );
    if (Number.isInteger(detail.more) && detail.more > 0) {
      messages.push({ key: "error.place_more", params: { more: detail.more }, keyParams: {} });
    }
  }
  messages.push(nextStep(lookup(STOP_NEXT_KEYS, code, "next.reload_page")));
  if (typeof code === "string" && code !== "") {
    messages.push({ key: "error.code", params: { code }, keyParams: {} });
  }
  return messages;
}

// Losing the server is a problem with a next step; the other connection
// states are a short line in the footer.
export function connectionMessages(key) {
  const line = { key, params: {}, keyParams: {} };
  if (key === "status.unavailable") {
    return { status: [], problem: [line, nextStep("next.restart_gui")] };
  }
  if (key === "status.unauthorized") {
    return { status: [], problem: [line, nextStep("next.open_terminal_address")] };
  }
  return { status: key === null ? [] : [line], problem: [] };
}

export function progressMessage(progress) {
  const stage = progress?.stage;
  if (!Object.hasOwn(STAGE_KEYS, stage ?? "")) {
    return { key: "progress.starting", params: {}, keyParams: {} };
  }
  if (stage === "normalizing") {
    const step = lookup(STEP_KEYS, progress.step, null);
    if (step === null) {
      return { key: "progress.starting", params: {}, keyParams: {} };
    }
    return { key: STAGE_KEYS.normalizing, params: {}, keyParams: { step } };
  }
  if (stage === "reading_fit") {
    return {
      key: STAGE_KEYS.reading_fit,
      params: { done: progress.done, total: progress.total },
      keyParams: {},
    };
  }
  return { key: STAGE_KEYS[stage], params: {}, keyParams: {} };
}

// A pre-run finding, and what to do next when it has a step. A finding that
// keeps the run from starting also gives its code to quote, as a stop does.
export function findingMessages(finding) {
  const key = lookup(FINDING_KEYS, finding?.message_id, "error.unknown");
  if (key === null) {
    return [];
  }
  const messages = [{ key, params: {}, keyParams: {} }];
  const step = lookup(STOP_NEXT_KEYS, finding?.code, null) ?? lookup(ACTION_KEYS, finding?.next_action_id, null);
  if (step !== null) {
    messages.push(nextStep(step));
  }
  if (finding?.severity === "ERROR" && typeof finding.code === "string") {
    messages.push({ key: "error.code", params: { code: finding.code }, keyParams: {} });
  }
  return messages;
}

// The rows of the result table: for a finished run, and for one whose
// cancellation came after it wrote its output, when its result is known
// (stage A5c). The last row holds the warnings that belong to no family
// (stage B2c).
export function resultRows(status) {
  return FINISHED_STATES.includes(status?.state) && status.result
    ? [...familyRows(status.result), otherRow(status.result)]
    : [];
}

// The totals of the warnings of a run, from the counts that the run gives
// (stage B2c): the warnings of the families and those of no family add up to
// the total. The warnings one by one are not counted again.
export function warningTotals(result) {
  const families = Object.values(result?.families ?? {}).map((family) => family?.warning_count);
  const sum = (values) => values.reduce((total, value) => total + (Number.isInteger(value) ? value : 0), 0);
  return {
    total: Number.isInteger(result?.warning_count) ? result.warning_count : 0,
    families: sum(families),
    kinds: families.filter((count) => Number.isInteger(count) && count > 0).length,
    other: sum(Object.values(result?.other_warning_counts ?? {})),
  };
}

// The row of the warnings that belong to no family: those of the Lactate
// Threshold candidates, of the links between datasets, and of the input.
export function otherRow(result) {
  const warnings = warningTotals(result).other;
  return {
    family: null,
    nameKey: "family.other",
    statusKey: warnings > 0 ? "family_status.other_warnings" : "family_status.no_warnings",
    kind: warnings > 0 ? "warn" : "none",
    records: null,
    warnings,
  };
}

// The last line of the result table: the total of the warnings and what it
// is made of, when the result is known.
export function resultTotal(status) {
  if (!FINISHED_STATES.includes(status?.state) || !status.result) {
    return null;
  }
  const totals = warningTotals(status.result);
  return message("result.total_warnings", { total: totals.total, families: totals.families, other: totals.other });
}

// The groups of the warnings that belong to no family, by the name that a
// warning gives; a warning of the input gives none.
const OTHER_GROUP_KEYS = {
  lactate_threshold: "family.other_candidate",
  relationships: "family.other_relationship",
};
const OTHER_GROUP_ORDER = ["lactate_threshold", "relationships", null];

// The warnings of a finished run one by one, after their totals: the family
// or the group of no family that each concerns, and what it says with its
// count (stage B2c). The families come in the order of the result table, and
// the warnings of no family last.
export function warningMessages(result) {
  const totals = warningTotals(result);
  if (totals.total === 0) {
    return [];
  }
  const messages = [message("output_check.warnings", { ...totals })];
  const items = Array.isArray(result?.warning_items) ? result.warning_items : [];
  const rank = (item) => OTHER_GROUP_ORDER.indexOf(item.family ?? null) + 1;
  const sorted = [...items].sort(
    (first, second) => rank(first) - rank(second) || String(first.family).localeCompare(String(second.family)),
  );
  for (const item of sorted) {
    const name =
      item.family === null || item.family === undefined
        ? "family.other_input"
        : (OTHER_GROUP_KEYS[item.family] ?? lookup(FAMILY_KEYS, item.family, null));
    messages.push(
      message(
        lookup(WARNING_KEYS, item.code, "warning.other"),
        { count: item.count ?? "—", code: String(item.code), ...(name === null ? { name: String(item.family) } : {}) },
        name === null ? {} : { name },
      ),
    );
  }
  return messages;
}

export function familyRows(result) {
  const families = result?.families ?? {};
  return Object.keys(families)
    .sort()
    .map((family) => {
      const status = families[family]?.status;
      const warnings = families[family]?.warning_count ?? 0;
      const kind = lookup(FAMILY_STATUS_KINDS, status, "ok");
      return {
        family,
        nameKey: lookup(FAMILY_KEYS, family, null),
        statusKey:
          status === "PROCESSED" && warnings > 0
            ? "family_status.processed_with_warnings"
            : lookup(FAMILY_STATUS_KEYS, status, "family_status.other"),
        kind: kind === "ok" && warnings > 0 ? "warn" : kind,
        records: families[family]?.record_count ?? 0,
        warnings,
      };
    });
}

const message = (key, params = {}, keyParams = {}) => ({ key, params, keyParams });

// The four boxes of the page, in order (stage B1a): the Export, the
// Snapshots, the output, and the run.
export const BOXES = ["export", "snapshot", "output", "run"];

// The box that a stop turns red, as the text book of stage B0 places it.
// Codes of the output check, the Support Bundle, and opening the output show
// under their action instead. PATH_INVALID comes from the folder list and
// shows there. Other codes, such as REQUEST_INVALID, which names no field,
// belong to the fourth box.
const ERROR_BOXES = {
  INPUT_PATH_INVALID: "export",
  INPUT_NOT_DIRECTORY: "export",
  INPUT_SYMLINK: "export",
  INPUT_NOT_READABLE: "export",
  INPUT_CHANGED: "export",
  INPUT_ZIP_CORRUPT: "export",
  INPUT_TOO_LARGE: "export",
  INPUT_MULTIPLE_EXPORTS: "export",
  INPUT_DISCOVERY_FAILED: "export",
  TEMP_SPACE_INSUFFICIENT: "export",
  ACTIVITIES_NOT_FOUND: "export",
  ACTIVITIES_EMPTY: "export",
  FOLDER_NOT_FOUND: "export",
  NOT_A_FOLDER: "export",
  FOLDER_NOT_READABLE: "export",
  OUTPUT_PARENT_INVALID: "output",
  OUTPUT_SYMLINK: "output",
  OUTPUT_EXISTS: "output",
  OUTPUT_INSIDE_INPUT: "output",
  OUTPUT_PARENT_NOT_FOUND: "output",
  OUTPUT_PARENT_NOT_WRITABLE: "output",
  OUTPUT_NAME_INVALID: "output",
  OUTPUT_PATH_TOO_LONG: "output",
  OUTPUT_SPACE_INSUFFICIENT: "output",
  OUTPUT_PUBLISH_FAILED: "output",
  TIMEZONE_INVALID: "output",
  TIMEZONE_DATA_UNAVAILABLE: "output",
};

// A path that the server reads as absolute: a POSIX path, a home path that it
// expands, a Windows drive, or a network share.
export function looksAbsolute(path) {
  return typeof path === "string" && /^(\/|~|[A-Za-z]:[\\/]|\\\\)/.test(path.trim());
}

// PATH_NOT_ABSOLUTE names no field; the run request checks the Export first.
export function errorBox(code, inputPath) {
  if (code === "PATH_NOT_ABSOLUTE") {
    return looksAbsolute(inputPath) ? "output" : "export";
  }
  return lookup(ERROR_BOXES, code, "run");
}

// The state of each box: "current" (blue, what to do now), "done" (green),
// "todo", "error" (red, what to fix), or "stopped" (the fourth box when the
// run stopped in another box). Until stage B4a the page has no settings from
// an earlier launch, so the second and third boxes are confirmed one at a
// time, as on a first launch. After a run that finished or stopped, a change
// in a box (``editedSinceRun``) brings back the boxes as they are set.
export function boxStates(view) {
  const states = { export: "todo", snapshot: "todo", output: "todo", run: "todo" };
  const runState = view.runState;
  if (view.starting || ACTIVE_STATES.includes(runState)) {
    states.export = states.snapshot = states.output = "done";
    states.run = "current";
    return states;
  }
  if (FINISHED_STATES.includes(runState) && !view.editedSinceRun) {
    states.export = states.snapshot = states.output = states.run = "done";
    return states;
  }
  if (runState === "failed" && !view.editedSinceRun) {
    states.export = states.snapshot = states.output = "done";
    const box = view.failedBox ?? "run";
    states[box] = "error";
    if (box !== "run") {
      states.run = "stopped";
    }
    return states;
  }
  if (view.exportProblem) {
    states.export = "error";
    return states;
  }
  const done = [view.exportReady, view.snapshotDecided, view.outputDecided];
  let current = null;
  ["export", "snapshot", "output"].forEach((box, index) => {
    if (current === null && done.slice(0, index + 1).every(Boolean)) {
      states[box] = "done";
    } else if (current === null) {
      states[box] = "current";
      current = box;
    }
  });
  states.run = current === null ? "current" : "todo";
  // A run request that the server refused marks the box that it concerns.
  if (typeof view.requestBox === "string" && Object.hasOwn(states, view.requestBox)) {
    states[view.requestBox] = "error";
    if (view.requestBox !== "run") {
      states.run = "todo";
    }
  }
  return states;
}

// The number of a box, for the texts that name it.
export function boxNumber(box) {
  return BOXES.indexOf(box) + 1;
}

// The one line under the title: what to do now. A red box holds its own next
// step, so the line only points at it.
export function nextLine(view, states) {
  const runState = view.runState;
  if (!view.connected) {
    return null;
  }
  if (view.starting || runState === "running") {
    return message("next_line.running");
  }
  if (runState === "cancelling") {
    return message("next_line.cancelling");
  }
  if (runState === "finished_after_cancel" && !view.editedSinceRun) {
    return message("next_line.late");
  }
  if (runState === "finished" && !view.editedSinceRun) {
    const result = view.result ?? {};
    if (result.exit_code === 3) {
      return message("next_line.done_partial", { warnings: result.warning_count ?? 0 });
    }
    if ((result.warning_count ?? 0) > 0) {
      return message("next_line.done_warnings", { warnings: result.warning_count });
    }
    return message("next_line.done");
  }
  const red = BOXES.find((box) => states[box] === "error");
  if (red !== undefined) {
    return message("next_line.fix_box", { box: boxNumber(red) });
  }
  if (states.export === "current") {
    return message(view.inputFilled ? "next_line.check_export" : "next_line.choose_export");
  }
  if (states.snapshot === "current") {
    return message("next_line.decide_snapshot");
  }
  if (states.output === "current") {
    return message("next_line.decide_output");
  }
  if (runState === "cancelled") {
    return message("next_line.cancelled");
  }
  return message("next_line.start");
}

// The steps of a run of one Export, and the stages of Run-All that each one
// covers. The last step is the page's check of the output after the run.
export const RUN_STEPS = [
  { key: "steps.check_export", stages: ["discovering"] },
  { key: "steps.convert", stages: ["normalizing", "reading_fit", "verifying_input", "building_output"] },
  { key: "steps.write", stages: ["writing_output"] },
  { key: "steps.check_output", stages: [] },
];
const OUTPUT_CHECK_STEP = RUN_STEPS.length - 1;

// The step that a stage of Run-All belongs to, or 0 before the first stage.
function stepOf(stage) {
  const index = RUN_STEPS.findIndex((step) => step.stages.includes(stage));
  return index < 0 ? 0 : index;
}

function stepSeconds(step, stageSeconds) {
  const seconds = step.stages
    .map((stage) => stageSeconds?.[stage])
    .filter((value) => typeof value === "number" && value >= 0);
  return seconds.length === 0 ? null : seconds.reduce((sum, value) => sum + value, 0);
}

// The rows of the steps table: each step's state ("todo", "run", "done",
// "warn", "error", "cancelled", or "skipped") and its seconds.
// ``outputCheck`` is the page's check of the finished output: null before it
// starts, "running", "done", "warn", or "error". The check is no stage of
// Run-All, so the page measures its seconds (``outputCheckSeconds``).
export function stepRows(status, outputCheck, outputCheckSeconds = null) {
  const runState = status?.state;
  const seconds = (index) =>
    index === OUTPUT_CHECK_STEP
      ? FINISHED_STATES.includes(runState) && typeof outputCheckSeconds === "number"
        ? outputCheckSeconds
        : null
      : stepSeconds(RUN_STEPS[index], status?.stage_seconds);
  const rows = RUN_STEPS.map((step, index) => ({ key: step.key, state: "todo", seconds: seconds(index) }));
  if (ACTIVE_STATES.includes(runState)) {
    const current = stepOf(status.progress?.stage);
    rows.forEach((row, index) => {
      row.state = index < current ? "done" : index === current ? "run" : "todo";
    });
  } else if (FINISHED_STATES.includes(runState)) {
    rows.forEach((row) => {
      row.state = "done";
    });
    if ((status.result?.warning_count ?? 0) > 0) {
      rows[stepOf("normalizing")].state = "warn";
    }
    rows[OUTPUT_CHECK_STEP].state = outputCheck === "running" ? "run" : outputCheck ?? "todo";
  } else if (runState === "failed" || runState === "cancelled") {
    const last = stepOf(status.progress?.stage);
    rows.forEach((row, index) => {
      row.state = index < last ? "done" : index === last ? (runState === "failed" ? "error" : "cancelled") : "skipped";
    });
  }
  return rows;
}

// Where a run is, for the line under the headline: the step and how many.
export function currentStep(status) {
  const index = stepOf(status?.progress?.stage);
  return { key: RUN_STEPS[index].key, number: index + 1, total: RUN_STEPS.length };
}

// The headline of the fourth box, the exit code under it, and the line under
// that. The exit code is the CLI's for the same run; a run cancelled before
// its output shows none, because 130 means nothing on the page.
export function runSummary(status, states, view = {}) {
  const runState = status?.state;
  const result = status?.result;
  if (view.starting || runState === "running") {
    const step = currentStep(status);
    return {
      headline: message("run.headline_running"),
      exitCode: null,
      sub: message("run.sub_running", { number: step.number, total: step.total }, { step: step.key }),
    };
  }
  if (runState === "cancelling") {
    return { headline: message("run.headline_cancelling"), exitCode: null, sub: null };
  }
  if (FINISHED_STATES.includes(runState) && result) {
    // The headline says what the exit code means (decision 20261011-15):
    // 3 left out part of the input, 0 kept every value.
    const done = message(result.exit_code === 3 ? "result.headline_partial" : "result.headline_done");
    if (runState === "finished_after_cancel") {
      return {
        headline: message("result.headline_late", {}, { headline: done.key }),
        exitCode: result.exit_code,
        sub: message("result.sub_late"),
      };
    }
    return {
      headline: done,
      exitCode: result.exit_code,
      sub: message(lookup(RESULT_SUB_KEYS, result.status, "result.sub_pass"), {
        warnings: result.warning_count ?? 0,
      }),
    };
  }
  if (runState === "failed") {
    return {
      headline: message("result.headline_failed"),
      exitCode: 2,
      sub: message("result.sub_failed", { box: boxNumber(view.failedBox ?? "run") }),
    };
  }
  if (runState === "cancelled") {
    return { headline: message("result.headline_cancelled"), exitCode: null, sub: message("result.sub_cancelled") };
  }
  if (states?.run === "current") {
    return { headline: message("run.headline_ready"), exitCode: null, sub: message("run.sub_ready") };
  }
  return { headline: message("run.headline_waiting"), exitCode: null, sub: null };
}

// What a finished, cancelled, or failed run also tells: the output folder,
// and the staging folders that a forced stop left behind (stage A5c).
export function resultDetails(status) {
  const messages = [];
  const state = status?.state;
  if (FINISHED_STATES.includes(state) && status.output_path) {
    // The place has a line of its own, so that a long place never breaks the
    // words of the label.
    messages.push(message("result.output_label"));
    messages.push(message("result.path", { path: status.output_path }));
  }
  if (Array.isArray(status?.staging_folders) && status.staging_folders.length > 0) {
    messages.push(message("result.staging_left", { names: status.staging_folders.join(", ") }));
    messages.push(nextStep("next.delete_staging"));
  }
  return messages;
}

// The words that sum up a confirmed box (a green line under its heading).
export function boxSummary(box, view) {
  if (box === "export") {
    return message("summary.export", { name: lastName(view.inputPath) });
  }
  if (box === "snapshot") {
    return message("summary.snapshot_single");
  }
  if (box === "output") {
    // After a run, the output that it made; the name field already holds
    // the name proposed for the next run.
    if (FINISHED_STATES.includes(view.runState) && typeof view.outputPath === "string") {
      const parent = view.outputPath.trim().replace(/[\\/]+$/, "").replace(/[\\/][^\\/]*$/, "");
      return message("summary.output_done", { parent: lastName(parent), name: lastName(view.outputPath) });
    }
    return message("summary.output", {
      parent: lastName(view.outputParent),
      name: typeof view.outputName === "string" ? view.outputName.trim() : "",
    });
  }
  return null;
}

// The last name of a path, for the summaries: a folder, or the drive itself.
export function lastName(path) {
  const trimmed = typeof path === "string" ? path.trim().replace(/[\\/]+$/, "") : "";
  const parts = trimmed.split(/[\\/]/);
  return parts[parts.length - 1] || (typeof path === "string" ? path.trim() : "");
}

// Messages for the check of a finished output: the handoff counts, what the
// Doctor says about using the output, and the warnings of the run.
export function outputCheckMessages(check, result) {
  const handoff = check?.handoff;
  const doctor = check?.doctor;
  const messages = [];
  if (handoff?.status === "PASS") {
    messages.push({
      key: "output_check.handoff_pass",
      params: {
        datasets: handoff.dataset_count,
        relationships: handoff.relationship_count,
      },
      keyParams: {},
    });
  }
  messages.push({
    key: lookup(USABILITY_KEYS, doctor?.usability_scope, "error.unknown"),
    params: {},
    keyParams: {},
  });
  const next = lookup(NEXT_ACTION_KEYS, doctor?.next_action_id, null);
  if (next !== null) {
    messages.push(nextStep(next));
  }
  messages.push(...warningMessages(result));
  if (doctor?.support_bundle_suggested === true) {
    messages.push({ key: "output_check.bundle_suggested", params: {}, keyParams: {} });
  }
  return messages;
}

// Room for the hidden names derived from the output name, as on the server.
export const MAX_OUTPUT_NAME_BYTES = 200;

// The size in UTF-8, or null for a lone surrogate, which the server refuses.
function utf8Size(text) {
  try {
    encodeURIComponent(text);
  } catch {
    return null;
  }
  return new TextEncoder().encode(text).length;
}

// Mirrors the server's rule; the server stays the authority.
export function isValidOutputName(name) {
  const size = typeof name === "string" ? utf8Size(name) : null;
  if (size === null || size === 0 || size > MAX_OUTPUT_NAME_BYTES) {
    return false;
  }
  if (name.startsWith(".") || name.endsWith(".") || name.endsWith(" ")) {
    return false;
  }
  if (INVALID_NAME_CHARACTERS.test(name)) {
    return false;
  }
  return !WINDOWS_RESERVED_NAMES.has(name.split(".", 1)[0].trimEnd().toUpperCase());
}

export function defaultOutputName(date) {
  const two = (value) => String(value).padStart(2, "0");
  return (
    `garmin-run-all-${date.getFullYear()}${two(date.getMonth() + 1)}${two(date.getDate())}` +
    `-${two(date.getHours())}${two(date.getMinutes())}`
  );
}

// After a run, propose a name for the next one. Within the same minute the
// default name is the one just used, so a number is added: -2, -3, and so on.
export function nextOutputName(used, date) {
  const base = defaultOutputName(date);
  if (used !== base && !used.startsWith(`${base}-`)) {
    return base;
  }
  const number = used === base ? 1 : Number(used.slice(base.length + 1));
  return `${base}-${Number.isInteger(number) && number >= 1 ? number + 1 : 2}`;
}

export function formatElapsed(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = String(total % 60).padStart(2, "0");
  return hours > 0 ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

export function stalledSeconds(status) {
  const seconds = status?.seconds_since_progress;
  if (status?.state !== "running" || typeof seconds !== "number" || seconds < STALL_SECONDS) {
    return null;
  }
  return Math.floor(seconds);
}

// What the hidden live region says during and at the end of a run. Counts and
// seconds change every second, so the page speaks only when the id changes:
// at a new stage or step, when a run stalls or is being cancelled, and at the
// end.
export function announcement(status) {
  const state = status?.state;
  if (state === "running") {
    const stalled = stalledSeconds(status);
    if (stalled !== null) {
      return { id: "stalled", message: { key: "run.stalled", params: { seconds: stalled }, keyParams: {} } };
    }
    const progress = progressMessage(status.progress);
    return { id: `progress:${progress.key}:${progress.keyParams.step ?? ""}`, message: progress };
  }
  if (state === "cancelling") {
    return { id: "cancelling", message: { key: "run.cancelling", params: {}, keyParams: {} } };
  }
  if (TERMINAL_STATES.includes(state)) {
    return { id: `end:${state}`, message: runSummary(status, null).headline };
  }
  return null;
}

// The end of a run moves focus to the result heading only from where the run
// left it: nowhere, or the run section (its heading, Start, or Cancel). A
// keyboard user who has moved on stays there; the announcer still speaks.
export function shouldFocusResult(active, body, runSection) {
  return active === null || active === body || runSection.contains(active);
}

// Which controls the page enables, from one view of its state and the states
// of the boxes. A box is confirmed with its button while it is the current
// one. A run starts when the fourth box is current, and again after a run
// that finished or stopped, with the same confirmed boxes; a change in the
// third box takes back its confirmation, and one in the first its check.
export function controls(view, states) {
  const running = ACTIVE_STATES.includes(view.runState) || view.starting;
  const busy = running || view.checking || view.outputBusy;
  const filled = (value) => typeof value === "string" && value.trim() !== "";
  const outputReady =
    filled(view.outputParent) && filled(view.timezone) && isValidOutputName(view.outputName);
  return {
    form: view.connected && !running,
    browse: view.connected && !busy,
    check: view.connected && !busy && filled(view.inputPath),
    decideSnapshot: view.connected && !busy && states.snapshot === "current",
    decideOutput: view.connected && !busy && states.output === "current" && outputReady,
    start:
      view.connected &&
      !busy &&
      view.checkedReady &&
      outputReady &&
      (states.run === "current" ||
        ((FINISHED_STATES.includes(view.runState) || view.runState === "failed") &&
          view.snapshotDecided &&
          view.outputDecided)),
    cancel: view.connected && view.runState === "running",
    quit: view.connected && !running && !view.outputBusy,
    outputActions: view.connected && !busy && FINISHED_STATES.includes(view.runState),
  };
}

// Which boxes must still be confirmed before a run can start, by number.
export function boxesToConfirm(states) {
  return ["export", "snapshot", "output"].filter((box) => states[box] !== "done").map(boxNumber);
}

// The parts of the help panel, in the order of its buttons (stage B1b).
export const HELP_SECTIONS = ["steps", "faq", "words", "ai"];

// The steps of "How to use": the four boxes, then reading the result, which
// lights up the results table.
export const HELP_STEPS = [...BOXES, "results"];

// The state of each step of "How to use", from the states of the boxes:
// "done", "current" (what to do now, or a box to fix), or "todo". Reading the
// result is done once a run has finished and no box has changed since.
export function helpSteps(states, runState) {
  const steps = {};
  for (const box of BOXES) {
    const boxState = states[box];
    steps[box] =
      boxState === "done" ? "done" : boxState === "current" || boxState === "error" ? "current" : "todo";
  }
  steps.results = FINISHED_STATES.includes(runState) && states.run === "done" ? "done" : "todo";
  return steps;
}

// Where focus goes when the help panel closes: back to the button that opened
// it, or to the Help button when that button is gone, hidden, or disabled by
// then, as the fourth box's button is after a new run starts.
export function helpReturnTarget(opener) {
  return opener?.usable === true ? "opener" : "help";
}
