// Run page rules that do not touch the DOM, so that node --test can check
// them. Message keys appear here only as literal strings, so that tests can
// check them against the catalogs.

export const ACTIVE_STATES = ["running", "cancelling"];
export const TERMINAL_STATES = ["finished", "finished_after_cancel", "cancelled", "failed"];
// States in which the run published a complete output folder.
export const FINISHED_STATES = ["finished", "finished_after_cancel"];
export const STALL_SECONDS = 30;
// The seconds of a run before the hidden live region speaks its stage, so
// that a run that ends at once speaks only its end (stage C1).
export const QUIET_START_SECONDS = 2;

const STAGE_KEYS = {
  // The stages of a Snapshot run before those of Run-All (stage B4b-1).
  creating_store: "progress.creating_store",
  reading_export: "progress.reading_export",
  importing: "progress.importing",
  checking_store: "progress.checking_store",
  building_snapshots: "progress.building_snapshots",
  discovering: "progress.discovering",
  normalizing: "progress.normalizing",
  reading_fit: "progress.reading_fit",
  verifying_input: "progress.verifying_input",
  building_output: "progress.building_output",
  writing_output: "progress.writing_output",
};

const COUNTED_STAGES = ["reading_export", "importing", "reading_fit"];

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
  OUTPUT_LIST_CHANGED: "stop.output_list_changed",
  HANDOFF_INVALID: "stop.handoff_invalid",
  // An output that another version made (stage B5b).
  OUTPUT_OTHER_VERSION: "stop.output_other_version",
  OUTPUT_CHANGED: "stop.output_changed",
  DOCTOR_AUTHORITY_INVALID: "stop.doctor_authority_invalid",
  DOCTOR_UNREGISTERED_DIAGNOSTIC: "stop.doctor_unregistered_diagnostic",
  DOCTOR_VERSION_UNSUPPORTED: "stop.doctor_version_unsupported",
  SUPPORT_BUNDLE_AUTHORITY_INVALID: "stop.support_bundle_authority_invalid",
  OUTPUT_NOT_AVAILABLE: "stop.output_not_available",
  SUPPORT_BUNDLE_PATH_UNSAFE: "stop.support_bundle_path_unsafe",
  SUPPORT_BUNDLE_EXISTS: "stop.support_bundle_exists",
  // The place of a Support Bundle (stage B5a).
  SUPPORT_BUNDLE_PARENT_NOT_FOUND: "stop.support_bundle_parent_not_found",
  SUPPORT_BUNDLE_INSIDE_OUTPUT: "stop.support_bundle_inside_output",
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
  CHOOSER_NOT_AVAILABLE: "stop.chooser_not_available",
  CHOOSER_TIMEOUT: "stop.chooser_timeout",
  CHOOSER_BUSY: "stop.chooser_busy",
  // The Snapshot Store, which the page opens and checks (stage B4a).
  SNAPSHOT_STORE_NOT_FOUND: "stop.snapshot_store_not_found",
  SNAPSHOT_STORE_INVALID: "stop.snapshot_store_invalid",
  SNAPSHOT_STORE_VERSION_UNSUPPORTED: "stop.snapshot_store_version_unsupported",
  SNAPSHOT_STORE_NOT_READABLE: "stop.snapshot_store_not_readable",
  SNAPSHOT_STORE_SYMLINK: "stop.snapshot_store_symlink",
  SNAPSHOT_STORE_PARENT_NOT_FOUND: "stop.snapshot_store_parent_not_found",
  SNAPSHOT_STORE_NOT_EMPTY: "stop.snapshot_store_not_empty",
  SNAPSHOT_STORE_INSIDE_STORE: "stop.snapshot_store_inside_store",
  SNAPSHOT_STORE_PATH_TOO_LONG: "stop.snapshot_store_path_too_long",
  SNAPSHOT_STORE_LOCKED: "stop.snapshot_store_locked",
  SNAPSHOT_REGISTRATION_INCOMPLETE: "stop.snapshot_registration_incomplete",
  // A Snapshot run of the page (stage B4b-1).
  SNAPSHOT_LABEL_INVALID: "stop.snapshot_label_invalid",
  SNAPSHOT_LABEL_EXISTS: "stop.snapshot_label_exists",
  SNAPSHOT_TIME_INVALID: "stop.snapshot_time_invalid",
  SNAPSHOT_INPUT_INSIDE_STORE: "stop.snapshot_input_inside_store",
  SNAPSHOT_STORE_NOT_WRITABLE: "stop.snapshot_store_not_writable",
  SNAPSHOT_STORE_SPACE_INSUFFICIENT: "stop.snapshot_store_space_insufficient",
  SNAPSHOT_STORE_EMPTY: "stop.snapshot_store_empty",
  SNAPSHOT_LIFECYCLE_FAILED: "stop.snapshot_lifecycle_failed",
  // Removing a lock file (stage B4b-2).
  SNAPSHOT_UNLOCK_NOT_CONFIRMED: "stop.snapshot_unlock_not_confirmed",
  SNAPSHOT_LOCK_NOT_FOUND: "stop.snapshot_lock_not_found",
  SNAPSHOT_LOCK_INVALID: "stop.snapshot_lock_invalid",
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
  OUTPUT_LIST_CHANGED: "stop_next.output_list_changed",
  HANDOFF_INVALID: "stop_next.handoff_invalid",
  OUTPUT_OTHER_VERSION: "stop_next.output_other_version",
  OUTPUT_CHANGED: "stop_next.output_changed",
  DOCTOR_AUTHORITY_INVALID: "stop_next.new_output",
  DOCTOR_UNREGISTERED_DIAGNOSTIC: "stop_next.doctor_version",
  DOCTOR_VERSION_UNSUPPORTED: "stop_next.doctor_version",
  SUPPORT_BUNDLE_AUTHORITY_INVALID: "stop_next.support_bundle_authority_invalid",
  OUTPUT_NOT_AVAILABLE: "stop_next.output_where",
  SUPPORT_BUNDLE_PATH_UNSAFE: "stop_next.output_where",
  SUPPORT_BUNDLE_EXISTS: "stop_next.support_bundle_exists",
  SUPPORT_BUNDLE_PARENT_NOT_FOUND: "stop_next.support_bundle_parent_not_found",
  SUPPORT_BUNDLE_INSIDE_OUTPUT: "stop_next.support_bundle_inside_output",
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
  CHOOSER_NOT_AVAILABLE: "stop_next.chooser_not_available",
  CHOOSER_TIMEOUT: "stop_next.chooser_timeout",
  CHOOSER_BUSY: "stop_next.chooser_busy",
  SNAPSHOT_STORE_NOT_FOUND: "stop_next.snapshot_store_not_found",
  SNAPSHOT_STORE_INVALID: "stop_next.snapshot_store_invalid",
  SNAPSHOT_STORE_VERSION_UNSUPPORTED: "stop_next.snapshot_store_version_unsupported",
  SNAPSHOT_STORE_NOT_READABLE: "stop_next.snapshot_store_not_readable",
  SNAPSHOT_STORE_SYMLINK: "stop_next.snapshot_store_symlink",
  SNAPSHOT_STORE_PARENT_NOT_FOUND: "stop_next.snapshot_store_parent_not_found",
  SNAPSHOT_STORE_NOT_EMPTY: "stop_next.snapshot_store_not_empty",
  SNAPSHOT_STORE_INSIDE_STORE: "stop_next.snapshot_store_inside_store",
  SNAPSHOT_STORE_PATH_TOO_LONG: "stop_next.snapshot_store_path_too_long",
  SNAPSHOT_STORE_LOCKED: "stop_next.snapshot_store_locked",
  SNAPSHOT_REGISTRATION_INCOMPLETE: "stop_next.snapshot_registration_incomplete",
  SNAPSHOT_LABEL_INVALID: "stop_next.snapshot_label_invalid",
  SNAPSHOT_LABEL_EXISTS: "stop_next.snapshot_label_exists",
  SNAPSHOT_TIME_INVALID: "stop_next.snapshot_time_invalid",
  SNAPSHOT_INPUT_INSIDE_STORE: "stop_next.snapshot_input_inside_store",
  SNAPSHOT_STORE_NOT_WRITABLE: "stop_next.snapshot_store_not_writable",
  SNAPSHOT_STORE_SPACE_INSUFFICIENT: "stop_next.snapshot_store_space_insufficient",
  SNAPSHOT_STORE_EMPTY: "stop_next.snapshot_store_empty",
  SNAPSHOT_LIFECYCLE_FAILED: "stop_next.snapshot_lifecycle_failed",
  SNAPSHOT_UNLOCK_NOT_CONFIRMED: "stop_next.snapshot_unlock_not_confirmed",
  SNAPSHOT_LOCK_NOT_FOUND: "stop_next.snapshot_lock_not_found",
  SNAPSHOT_LOCK_INVALID: "stop_next.snapshot_lock_invalid",
};

// The cases of INPUT_MULTIPLE_EXPORTS that have words of their own (stage
// B4b-2), as stops.PAGE_MIX_WORDING gives them; the input itself has those
// of the code. The code stays the same.
const MIX_KEYS = {
  other_account: "stop.mix_other_account",
  store: "stop.mix_store",
};

const MIX_NEXT_KEYS = {
  other_account: "stop_next.mix_other_account",
  store: "stop_next.mix_store",
};

function mixOf(code, detail) {
  return code === "INPUT_MULTIPLE_EXPORTS" && Object.hasOwn(MIX_KEYS, detail?.mix ?? "") ? detail.mix : null;
}

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
// A finding that gives a count of the check uses words with that count
// (stage B3b): the key, and the count of the check that it takes.
const COUNTED_FINDING_KEYS = {
  INPUT_FILES_CANNOT_BE_READ_AND_WILL_BE_LEFT_OUT: ["finding.files_left_out_count", "files_left_out"],
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
// its place inside the input ("" is the input itself) and how many more; for
// one of a Snapshot Store, ``store`` is true, and "" is the store's folder
// itself (stage B4a).
export function errorMessages(code, detail) {
  const mix = mixOf(code, detail);
  const key = mix === null ? lookup(STOP_KEYS, code, "error.unknown") : MIX_KEYS[mix];
  const messages = [{ key, params: {}, keyParams: {} }];
  // A name that cannot be shown comes as null, as the check gives it (stage
  // B3c).
  if (typeof detail?.place === "string" || detail?.place === null) {
    const itself = detail.store === true ? "error.place_store_itself" : "error.place_input_itself";
    messages.push(
      detail.place === null
        ? { key: "error.place_hidden", params: {}, keyParams: {} }
        : detail.place === ""
          ? { key: itself, params: {}, keyParams: {} }
          : { key: "error.place", params: { place: detail.place }, keyParams: {} },
    );
    if (Number.isInteger(detail.more) && detail.more > 0) {
      messages.push({ key: "error.place_more", params: { more: detail.more }, keyParams: {} });
    }
  }
  // The version that made an output that this version cannot check, as the
  // server read it from the output (stage B5b).
  if (typeof detail?.version === "string" && detail.version !== "") {
    messages.push({ key: "error.made_by_version", params: { version: detail.version }, keyParams: {} });
  }
  messages.push(nextStep(mix === null ? lookup(STOP_NEXT_KEYS, code, "next.reload_page") : MIX_NEXT_KEYS[mix]));
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
  // The stages that count files: the FIT files that Run-All reads, and from
  // stage B4b-1 the files of an import, read and copied.
  if (COUNTED_STAGES.includes(stage)) {
    return {
      key: STAGE_KEYS[stage],
      params: { done: progress.done, total: progress.total },
      keyParams: {},
    };
  }
  if (stage === "building_snapshots") {
    return { key: STAGE_KEYS.building_snapshots, params: { snapshots: progress.snapshots }, keyParams: {} };
  }
  return { key: STAGE_KEYS[stage], params: {}, keyParams: {} };
}

// The bar under the headline: the files of an import, or the FIT files that
// Run-All reads (stage B4b-1); null for a stage without numbers.
export function progressBar(progress) {
  const stage = progress?.stage;
  if (COUNTED_STAGES.includes(stage) && Number.isInteger(progress.total) && progress.total > 0) {
    return { max: progress.total, value: Number.isInteger(progress.done) ? progress.done : 0 };
  }
  return null;
}

// A pre-run finding, and what to do next when it has a step. A finding that
// keeps the run from starting also gives its code to quote, as a stop does.
// A count of the check, or null when it is not a whole number.
function countOf(value) {
  return Number.isInteger(value) && value >= 0 ? value : null;
}

export function findingMessages(finding, counts = {}) {
  const key = lookup(FINDING_KEYS, finding?.message_id, "error.unknown");
  if (key === null) {
    return [];
  }
  const counted = lookup(COUNTED_FINDING_KEYS, finding?.message_id, null);
  const count = counted === null ? null : countOf(counts?.[counted[1]]);
  const messages = [
    count !== null && count > 0
      ? { key: counted[0], params: { count }, keyParams: {} }
      : { key, params: {}, keyParams: {} },
  ];
  const step = lookup(STOP_NEXT_KEYS, finding?.code, null) ?? lookup(ACTION_KEYS, finding?.next_action_id, null);
  if (step !== null) {
    messages.push(nextStep(step));
  }
  if (finding?.severity === "ERROR" && typeof finding.code === "string") {
    messages.push({ key: "error.code", params: { code: finding.code }, keyParams: {} });
  }
  return messages;
}

// The finding of the pre-run check that belongs to the third box: the
// timezone data, which a run needs for the times of its records (stage B3b).
// Without it, the check counts no Activities.
const TIMEZONE_FINDING = "TIMEZONE_DATA_UNAVAILABLE";

// A pre-run check as the boxes read it: the finding of the third box, the
// other findings, and whether one of them stops a run.
export function checkParts(check) {
  const findings = Array.isArray(check?.findings) ? check.findings : [];
  const timezone = findings.find((finding) => finding?.code === TIMEZONE_FINDING) ?? null;
  const others = findings.filter((finding) => finding?.code !== TIMEZONE_FINDING);
  return { timezone, others, stops: others.some((finding) => finding?.severity === "ERROR") };
}

// The Exports of a mixed input that the page names at most, and the longest
// name on the button that chooses one (stage B3c).
const MAX_EXPORTS_SHOWN = 20;
const MAX_NAME_LENGTH = 120;

// A place inside the input as a parameter of a message: its name, or the
// words for the input itself or for a name that cannot be shown.
function placeParam(name, place) {
  if (place === null || typeof place !== "string") {
    return { params: {}, keyParams: { [name]: "check.name_hidden" } };
  }
  if (place === "") {
    return { params: {}, keyParams: { [name]: "check.name_itself" } };
  }
  return { params: { [name]: place }, keyParams: {} };
}

// The lines of the Exports that a mixed input holds: how many different ones,
// then each place, with the first one that holds the same files (stage B3c).
function foundExportMessages(found) {
  if (!Array.isArray(found) || found.length === 0) {
    return [];
  }
  const count = found.filter((item) => !Number.isInteger(item?.same_as)).length;
  const lines = [message("check.found_count", { count })];
  for (const item of found.slice(0, MAX_EXPORTS_SHOWN)) {
    const place = placeParam("place", item?.place);
    const same = Number.isInteger(item?.same_as) ? found[item.same_as] : undefined;
    if (same === undefined) {
      lines.push(message("check.found_place", place.params, place.keyParams));
    } else {
      const other = placeParam("same", same?.place);
      lines.push(
        message(
          "check.found_place_same",
          { ...place.params, ...other.params },
          { ...place.keyParams, ...other.keyParams },
        ),
      );
    }
  }
  if (found.length > MAX_EXPORTS_SHOWN) {
    lines.push(message("check.found_more", { more: found.length - MAX_EXPORTS_SHOWN }));
  }
  return lines;
}

// The first folder or file that cannot be opened and how many more, as the
// page names them after a run (stage B3c).
function notReadableMessages(detail) {
  if (detail === null || typeof detail !== "object") {
    return [];
  }
  const lines = [];
  if (detail.place === null) {
    lines.push(message("error.place_hidden"));
  } else if (detail.place === "") {
    lines.push(message("error.place_input_itself"));
  } else if (typeof detail.place === "string") {
    lines.push(message("error.place", { place: detail.place }));
  }
  if (Number.isInteger(detail.more) && detail.more > 0) {
    lines.push(message("error.place_more", { more: detail.more }));
  }
  return lines;
}

// The Exports of a mixed input that the page can choose, each with the words
// of its button and its full place (stage B3c).
export function foundChoices(check) {
  const found = Array.isArray(check?.exportsFound) ? check.exportsFound : [];
  return found
    .slice(0, MAX_EXPORTS_SHOWN)
    .filter((item) => typeof item?.path === "string" && typeof item?.place === "string" && item.place !== "")
    .map((item) => {
      const name = item.place.length > MAX_NAME_LENGTH ? `${item.place.slice(0, MAX_NAME_LENGTH)}…` : item.place;
      return { message: message("check.choose_found", { name }), path: item.path };
    });
}

// The lines of the first box for a pre-run check, each with its kind: "error"
// (red), "warn" (yellow), "ok" (green), or "info". The red ones come first,
// then the yellow ones, then what the check found (stage B3b). ``start`` marks
// the first line of each group, which carries the mark of its kind.
export function checkMessages(check) {
  const lines = [];
  const add = (kind, messages) =>
    messages.forEach((line, index) => lines.push({ kind, start: index === 0, message: line }));
  const { timezone, others, stops } = checkParts(check);
  const counts = check?.counts ?? {};
  if (stops) {
    add("error", [message("check.not_ready")]);
  }
  for (const finding of others.filter((item) => item?.severity === "ERROR")) {
    // The places that the check found follow what happened (stage B3c).
    const messages = findingMessages(finding, counts);
    if (finding?.code === "INPUT_MULTIPLE_EXPORTS") {
      messages.splice(1, 0, ...foundExportMessages(check?.exportsFound));
    } else if (finding?.code === "INPUT_NOT_READABLE") {
      messages.splice(1, 0, ...notReadableMessages(check?.notReadable));
    }
    add("error", messages);
  }
  for (const finding of others.filter((item) => item?.severity === "WARNING")) {
    add("warn", findingMessages(finding, counts));
  }
  if (stops) {
    return lines;
  }
  // What the check found is one group: a ZIP file was checked whole, also
  // without the timezone data, and the counts follow.
  const found = [];
  const files = countOf(counts.files_read);
  if (check?.kind === "zip" && files !== null) {
    found.push(message("check.zip_ready", { files }));
  } else if (timezone === null) {
    found.push(message(check?.kind === "folder" ? "check.folder_ready" : "check.ready"));
  }
  const activities = countOf(counts.activity_records);
  const fit = countOf(counts.fit_files);
  if (timezone === null && activities !== null && fit !== null) {
    found.push(message("check.counts", { activities, fit }));
  }
  add("ok", found);
  if (timezone !== null) {
    add("info", [message("check.counts_later")]);
  }
  return lines;
}

// The words for a place that a cloud may copy (stage B4a): a folder that a
// cloud app keeps, or the Desktop or Documents of a Mac, which iCloud copies
// when its setting for them is on.
const CLOUD_KEYS = {
  cloud: "place.cloud",
  desktop_documents: "place.cloud_desktop",
};

export function cloudMessages(kind) {
  const key = lookup(CLOUD_KEYS, kind, null);
  return key === null ? [] : [message(key)];
}

// An interrupted import does not stop anything: the next import completes
// the store, so it is yellow, as the notices of a store are (stage B4a).
const STORE_WARN_CODES = ["SNAPSHOT_STORE_LOCKED", "SNAPSHOT_REGISTRATION_INCOMPLETE"];
const storeProblemKind = (code) => (STORE_WARN_CODES.includes(code) ? "warn" : "error");
// The notices of an open store, in their order. A lock file, and paths too
// long for the files of an import on this system (stage B6c), keep an
// import from starting; for another way they are yellow.
const STORE_NOTICE_CODES = [...STORE_WARN_CODES, "SNAPSHOT_STORE_PATH_TOO_LONG"];
const IMPORT_STOP_NOTICES = ["SNAPSHOT_STORE_LOCKED", "SNAPSHOT_STORE_PATH_TOO_LONG"];

// The lines of the Snapshot Store in the second box, each with its kind, in
// the order of the first box (stage B4a): what the page is doing, a problem
// of the store or of the place for a new one, the notices of the store and a
// cloud that may copy it, and then the number of its Snapshots or what the
// check found. ``store`` holds the dialog that is open for it, its error,
// whether the page is asking the server, the answer of the store or of the
// place for a new one, and the answer of the check.
export function storeMessages(store, how = "single") {
  const lines = [];
  const add = (kind, messages) =>
    messages.forEach((line, index) => lines.push({ kind, start: index === 0, message: line }));
  if (store?.choosing === true) {
    add("info", [message("choose.open")]);
    return lines;
  }
  // Without the system's dialog, the page's own folder list opens: the store
  // has no field to paste a place in (stage B4a).
  if (store?.chooserError === "CHOOSER_NOT_AVAILABLE") {
    add("info", [message("choose.list_instead")]);
  } else if (typeof store?.chooserError === "string") {
    add("error", errorMessages(store.chooserError));
  }
  if (store?.busy === true) {
    add("info", [message("store.checking")]);
    return lines;
  }
  const answer = store?.answer;
  if (answer === null || typeof answer !== "object") {
    return lines;
  }
  // Removing the lock file (stage B4b-2): done, or the stop of it.
  if (store?.unlocked === true) {
    add("ok", [message("lock.removed")]);
  } else if (typeof store?.unlockError === "string") {
    add("error", errorMessages(store.unlockError));
  }
  const checked = store.checked !== null && typeof store.checked === "object" ? store.checked : null;
  // A check that found a notice gives it with the notices, in their order;
  // any other problem of the store or of its check is red.
  const checkedNotice =
    answer.state === "store" && checked?.state === "error" && STORE_WARN_CODES.includes(checked.error_code);
  const problem =
    answer.state === "error"
      ? answer
      : answer.state === "store" && checked?.state === "error" && !checkedNotice
        ? checked
        : null;
  if (problem !== null) {
    // The store that the settings remembered says so, and that this app does
    // not make it again (stage B4c).
    add(
      storeProblemKind(problem.error_code),
      storeMissingRemembered(store) ? rememberedMessages("store", problem.error_code) : errorMessages(problem.error_code, problem.detail),
    );
  }
  if (answer.state === "store") {
    const notices = new Set([...(answer.notices ?? []), ...(checked?.notices ?? [])]);
    if (checkedNotice) {
      notices.add(checked.error_code);
    }
    for (const code of STORE_NOTICE_CODES.filter((item) => notices.has(item))) {
      // A lock file keeps an import from starting, so it is red then
      // (stage B4b-1), and so do paths too long (stage B6c).
      add(IMPORT_STOP_NOTICES.includes(code) && how === "snapshots" ? "error" : "warn", errorMessages(code));
    }
  }
  add("warn", cloudMessages(answer.cloud));
  if (answer.state === "new") {
    add("info", [message("store.new")]);
  } else if (answer.state === "store" && checked?.state !== "error") {
    // The count is green while no check failed.
    const count = Array.isArray(answer.snapshots) ? answer.snapshots.length : 0;
    if (checked?.state === "checked") {
      add("ok", [message("store.checked", { count: checked.snapshot_count })]);
    } else {
      add("ok", [count === 0 ? message("snapshot.empty") : message("store.count", { count })]);
    }
  }
  return lines;
}

// The words of a place that the settings of an earlier launch remembered and
// that is not found (stage B4c): what happened, what to do next, and the code.
const REMEMBERED_KEYS = {
  store: ["remembered.store_missing", "remembered.store_missing_next"],
  output: ["remembered.output_missing", "remembered.output_missing_next"],
};

function rememberedMessages(kind, code) {
  const [what, next] = REMEMBERED_KEYS[kind];
  return [message(what), nextStep(next), message("error.code", { code })];
}

// Whether the store of the second box is the one that the settings
// remembered, and is not found (stage B4c): then the page offers to open
// another, to look again, and to make a new one, and makes none by itself.
export function storeMissingRemembered(store) {
  const answer = store?.answer;
  return (
    typeof store?.remembered === "string" &&
    answer?.state === "error" &&
    answer.error_code === "SNAPSHOT_STORE_NOT_FOUND" &&
    answer.path === store.remembered
  );
}

// When the lock file of a store was written (stage B4b-2): how long ago, so
// that the person can tell a lock that an import holds now from one that a
// stopped import left. ``nowMs`` is the time of the page; null for a time
// that cannot be read.
export function lockAge(createdAt, nowMs) {
  const made = typeof createdAt === "string" ? new Date(createdAt).getTime() : NaN;
  if (!Number.isFinite(made) || !Number.isFinite(nowMs)) {
    return null;
  }
  const minutes = Math.max(0, Math.floor((nowMs - made) / 60000));
  if (minutes < 1) {
    return message("lock.made_now");
  }
  if (minutes < 120) {
    return message("lock.made_minutes", { count: minutes });
  }
  const hours = Math.floor(minutes / 60);
  return hours < 48 ? message("lock.made_hours", { count: hours }) : message("lock.made_days", { count: Math.floor(hours / 24) });
}

// Whether the page offers to remove the lock file: for an import, of an
// open store that has one, while no run is active (stage B4b-2).
export function lockOffered(how, store, active = false) {
  const answer = store?.answer;
  return (
    how === "snapshots" &&
    !active &&
    answer?.state === "store" &&
    Array.isArray(answer.notices) &&
    answer.notices.includes("SNAPSHOT_STORE_LOCKED")
  );
}

// Whether the store keeps the chosen way from starting (stage B4b-1): a
// problem of the store or of its check, a lock file or paths too long for an
// import (stage B6c), or no Snapshot to normalize again. This Export alone
// never uses the store.
export function storeProblem(how, store) {
  const answer = store?.answer;
  if (how === "single" || answer === null || typeof answer !== "object") {
    return false;
  }
  const checked = store.checked;
  if (answer.state === "error" || (checked?.state === "error" && !STORE_WARN_CODES.includes(checked.error_code))) {
    return true;
  }
  const snapshots = Array.isArray(answer.snapshots) ? answer.snapshots.length : 0;
  if (how === "rerun") {
    return answer.state !== "store" || snapshots === 0;
  }
  return (
    answer.state === "store" &&
    Array.isArray(answer.notices) &&
    IMPORT_STOP_NOTICES.some((code) => answer.notices.includes(code))
  );
}

// Whether the store is ready for the chosen way: a store, or for an import
// also the place of a new one, without a problem.
export function storeReady(how, store) {
  if (how === "single") {
    return true;
  }
  const state = store?.answer?.state;
  const known = state === "store" || (how === "snapshots" && state === "new");
  return known && store?.busy !== true && !storeProblem(how, store);
}

// The time of an Export, which orders the Snapshots, in the local time of
// this computer, to the minute; a dash for one that cannot be read.
export function exportTime(value) {
  const date = typeof value === "string" ? new Date(value) : null;
  if (date === null || Number.isNaN(date.getTime())) {
    return "—";
  }
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// The rows of the Snapshots of an opened store, in their order: the number,
// the label, the time of the Export, the number of files, and the state
// (stage B4a). ``pending`` is the Export that the run will import, with its
// label and time: it takes its place in the order of the times of the
// Exports, and the numbers follow (stage B4b-1). ``added`` names the label
// that the last run imported.
export function snapshotRows(answer, pending = null, added = null) {
  const kept =
    answer?.state === "store" && Array.isArray(answer.snapshots)
      ? answer.snapshots.map((item) => ({
          label: typeof item?.label === "string" ? item.label : "",
          observed: typeof item?.observed_at === "string" ? item.observed_at : null,
          files: Number.isInteger(item?.files) ? item.files : null,
          state: typeof added === "string" && item?.label === added ? "added" : "kept",
        }))
      : [];
  if (answer?.state !== "store" && answer?.state !== "new") {
    return [];
  }
  if (pending !== null && typeof pending?.time === "string") {
    const time = new Date(pending.time).getTime();
    const index = kept.findIndex((row) => row.observed !== null && new Date(row.observed).getTime() > time);
    const row = { label: pending.label ?? "", observed: pending.time, files: null, state: "pending" };
    kept.splice(index < 0 ? kept.length : index, 0, row);
  }
  return kept.map((row, index) => ({
    order: index + 1,
    label: row.label,
    time: exportTime(row.observed),
    files: row.files,
    state: row.state,
  }));
}

// The label rule of a new Snapshot, as the store checks it (stage B4b-1);
// the server checks it again with the store's own function.
export const SNAPSHOT_LABEL = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;

export function isValidSnapshotLabel(label) {
  return typeof label === "string" && SNAPSHOT_LABEL.test(label);
}

// The proposed label of an import: the date of its download, with -2, -3,
// and so on when the store has that label already, as the names of outputs
// are proposed (stage B4b-1).
export function defaultSnapshotLabel(timeText, labels = []) {
  const date = /^\d{4}-\d{2}-\d{2}/.exec(typeof timeText === "string" ? timeText : "")?.[0];
  if (date === undefined) {
    return "";
  }
  const taken = new Set(labels);
  let label = date;
  for (let number = 2; taken.has(label); number += 1) {
    label = `${date}-${number}`;
  }
  return label;
}

// The instant of a local date and time that the page writes, as "2030-01-01
// 02:00", with the offset of this computer at that time; null for one that
// cannot be read (stage B4b-1).
export function localTimeIso(text) {
  const match = /^\s*(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})\s*$/.exec(typeof text === "string" ? text : "");
  if (match === null) {
    return null;
  }
  const [year, month, day, hour, minute] = match.slice(1).map(Number);
  const date = new Date(year, month - 1, day, hour, minute);
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day ||
    date.getHours() !== hour ||
    date.getMinutes() !== minute
  ) {
    return null;
  }
  const offset = -date.getTimezoneOffset();
  const pad = (number) => String(number).padStart(2, "0");
  const sign = offset < 0 ? "-" : "+";
  return `${year}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}:00${sign}${pad(Math.floor(Math.abs(offset) / 60))}:${pad(Math.abs(offset) % 60)}`;
}

// What keeps an import from starting, as the code of its stop: a label that
// the store does not take or has already, or a time that cannot be read
// (stage B4b-1). The server checks them again.
export function importProblem(fields, labels = []) {
  if (!isValidSnapshotLabel(fields?.label)) {
    return "SNAPSHOT_LABEL_INVALID";
  }
  if (labels.includes(fields.label)) {
    return "SNAPSHOT_LABEL_EXISTS";
  }
  return localTimeIso(fields?.time) === null ? "SNAPSHOT_TIME_INVALID" : null;
}

// Where the download time came from: the time of the ZIP file, or of the
// newest file of an extracted folder (decision 20261017-16).
const DOWNLOAD_SOURCE_KEYS = {
  zip: "import.time_from_zip",
  newest_file: "import.time_from_folder",
};

export function downloadSourceMessage(source) {
  const key = lookup(DOWNLOAD_SOURCE_KEYS, source, null);
  return key === null ? null : message(key);
}

// The lines under the folder for the output (stage B4a): the default place,
// which a run makes when it is not there, a remembered place that is not
// found (stage B4c), and a cloud that may copy the place. ``place`` is the
// server's answer for the place in the field; an answer for another place
// says nothing.
export function placeMessages(place, outputParent, remembered = null) {
  if (place === null || typeof place !== "object" || place.path !== outputParent) {
    return [];
  }
  const lines = [];
  if (place.default === true && place.exists === false) {
    lines.push({ kind: "info", start: true, message: message("output.parent_new") });
  } else if (outputMissingRemembered(place, outputParent, remembered)) {
    rememberedMessages("output", "OUTPUT_PARENT_NOT_FOUND").forEach((line, index) =>
      lines.push({ kind: "error", start: index === 0, message: line }),
    );
  }
  cloudMessages(place.cloud).forEach((line, index) =>
    lines.push({ kind: "warn", start: index === 0, message: line }),
  );
  return lines;
}

// What keeps the name of the output from being a new folder (stage B5a): the
// server's answer for the place and the name in the fields, as the start of
// a run checks it; an answer for another place or name says nothing.
const NAME_PROBLEMS = ["OUTPUT_EXISTS", "OUTPUT_SYMLINK", "OUTPUT_NAME_INVALID"];

export function outputNameProblem(place, outputParent, outputName) {
  if (place === null || typeof place !== "object" || place.path !== outputParent || place.name !== outputName) {
    return null;
  }
  return NAME_PROBLEMS.includes(place.name_problem) ? place.name_problem : null;
}

// Whether the page moves its own proposed name on to a free one: something
// of that name is there already, and the person did not change the name, as
// for the name of a Snapshot (decision 20261018-10). A name that the person
// gave is shown red instead.
export function movesProposedName(problem, proposed) {
  return proposed === true && (problem === "OUTPUT_EXISTS" || problem === "OUTPUT_SYMLINK");
}

// The red lines under the name of the output, in the words of its code.
export function nameMessages(problem) {
  return typeof problem === "string"
    ? errorMessages(problem).map((line, index) => ({ kind: "error", start: index === 0, message: line }))
    : [];
}

// The Support Bundle before it is made (stage B5a): the file that the button
// makes and its place, next to the output unless the person chose a folder,
// as the server names them (decision 20261011-14).
export function bundlePlan(outputPath, folder) {
  const output = typeof outputPath === "string" ? outputPath.trim().replace(/[\\/]+$/, "") : "";
  const name = lastName(output);
  if (name === "") {
    return [];
  }
  // The folder that holds the output, with the root of a disk as the server
  // names it ("/" or "C:\\").
  const above = output.slice(0, output.length - name.length);
  const trimmed = above.replace(/[\\/]+$/, "");
  const parent = trimmed === "" || /^[A-Za-z]:$/.test(trimmed) ? above : trimmed;
  const chosen = typeof folder === "string" && folder !== "";
  return [
    message("bundle.file", { name: `${name}-support-bundle.zip` }),
    chosen ? message("bundle.place_chosen", { folder }) : message("bundle.place_default", { folder: parent }),
  ];
}

// The External-safe Pack that a run made, by the name of its output (stage
// B5a): the line beside the button that shows it, apart from the line of the
// file of the next run.
export function packMade(outputPath) {
  const name = lastName(typeof outputPath === "string" ? outputPath : "");
  return name === "" ? [] : [message("pack.made", { path: `${name}/analysis/external_safe_handoff.zip` })];
}

// The earlier outputs to choose from (stage B5b), by their number in the
// server's list: their names, and the folder that holds one whose name
// another has too.
export function earlierChoices(outputs) {
  const list = Array.isArray(outputs) ? outputs : [];
  const counts = new Map();
  for (const output of list) {
    counts.set(output?.name, (counts.get(output?.name) ?? 0) + 1);
  }
  return list
    .filter((output) => Number.isInteger(output?.index) && typeof output?.name === "string")
    .map((output) =>
      counts.get(output.name) > 1
        ? { index: output.index, ...message("target.earlier_with_folder", { name: output.name, folder: parentName(output.path) }) }
        : { index: output.index, ...message("target.earlier_name", { name: output.name }) },
    );
}

function parentName(path) {
  const output = typeof path === "string" ? path.trim().replace(/[\\/]+$/, "") : "";
  const name = lastName(output);
  return lastName(output.slice(0, output.length - name.length));
}

// The output before the run, and whether the run is compared with it (stage
// B5b): only when both were normalized the same way (Snapshots or this Export
// alone), by the same version, and with the same timezone, as the person
// decided; otherwise the line says which of them differ.
export const CHANGE_REASON_KEYS = {
  how: "change.reason_how",
  version: "change.reason_version",
  timezone: "change.reason_timezone",
};

export function changePlan(previous, current) {
  if (previous === null || typeof previous !== "object" || typeof previous.families !== "object") {
    return { comparable: false, reasons: [] };
  }
  const reasons = [];
  if (previous.snapshots !== current?.snapshots) {
    reasons.push("how");
  }
  if (previous.version !== current?.version || previous.run_all_version !== current?.run_all_version) {
    reasons.push("version");
  }
  if (previous.timezone !== current?.timezone) {
    reasons.push("timezone");
  }
  return { comparable: reasons.length === 0, reasons };
}

// The change of the records of each family since the output before the run;
// none for a family that the output before had not, and for the row of no
// family.
export function changeRows(rows, previous) {
  const families = previous?.families ?? {};
  return rows.map((row) => ({
    ...row,
    change:
      row.family !== null && Number.isInteger(row.records) && Number.isInteger(families[row.family])
        ? row.records - families[row.family]
        : null,
  }));
}

// The lines of the change (stage B5b): under the table, what the column is,
// or why there is none; in the fourth box, the change of the activities.
export function changeMessages(plan, previous, rows) {
  if (previous === null || typeof previous !== "object") {
    return { table: [], run: [] };
  }
  if (!plan.comparable) {
    return {
      table: [message("change.not_compared", { name: previous.name }), ...plan.reasons.map((reason) => message(CHANGE_REASON_KEYS[reason]))],
      run: [],
    };
  }
  const activities = rows.find((row) => row.family === "activities")?.change;
  const run = !Number.isInteger(activities)
    ? []
    : activities > 0
      ? [message("change.activities_up", { count: activities })]
      : activities < 0
        ? [message("change.activities_down", { count: -activities })]
        : [message("change.activities_same")];
  return { table: [message("change.column", { name: previous.name }), message("change.note")], run };
}

// Before a run on a later launch (stage B5b), the table shows the counts of
// the output before, as the mockup v10 does.
export function previousRows(previous) {
  const families = previous?.families ?? {};
  return Object.keys(families)
    .sort()
    .map((family) => ({
      family,
      nameKey: lookup(FAMILY_KEYS, family, null),
      statusKey: "family_status.previous",
      kind: "prev",
      records: families[family],
      warnings: null,
      change: null,
    }));
}

// A change as the column shows it: +38, −2, or 0.
export function signedChange(change, format = String) {
  if (!Number.isInteger(change)) {
    return "";
  }
  return change > 0 ? `+${format(change)}` : change < 0 ? `\u2212${format(-change)}` : format(0);
}

// Whether the folder for the output is the one that the settings remembered,
// and is not found (stage B4c). The default place is made by a run as on a
// first launch, since an output is always a new folder; any other one is not
// made by this app.
export function outputMissingRemembered(place, outputParent, remembered) {
  return (
    typeof remembered === "string" &&
    remembered === outputParent &&
    place !== null &&
    typeof place === "object" &&
    place.path === outputParent &&
    place.exists === false &&
    place.default !== true
  );
}

// Whether the folder for the output can take an output without a question:
// a folder that is there, or the default place, which a run makes (stage
// B4c).
export function outputPlaceUsable(place, outputParent) {
  return (
    place !== null &&
    typeof place === "object" &&
    place.path === outputParent &&
    (place.exists === true || (place.default === true && place.exists === false))
  );
}

// What the page says of the settings (stage B4c), codes only from the server.
const SETTINGS_KEYS = {
  SETTINGS_INVALID: "settings.invalid",
  SETTINGS_NEWER: "settings.newer",
  SETTINGS_NOT_WRITTEN: "settings.not_written",
  SETTINGS_NOT_REMOVED: "settings.not_removed",
};
// When a run or the tips could not be remembered, the words say so.
const SETTINGS_WRITE_KEYS = {
  SETTINGS_NEWER: "settings.newer_kept",
  SETTINGS_NOT_WRITTEN: "settings.not_written",
};

// Which boxes the settings of an earlier launch set when the page starts
// (stage B4c): on a later launch, the second box with a remembered store and
// the third with a remembered folder. Without a remembered store, the second
// box is confirmed as on a first launch, so that no store is made unseen.
export function boxesSetBySettings(settings) {
  const later = settings?.launch === "later";
  return {
    snapshotAuto: later && typeof settings.store === "string",
    outputAuto: later && typeof settings.outputParent === "string",
  };
}

// Whether a box that the settings set is set now: it still holds the
// remembered place, and the place has no problem (stage B4c).
export function storeSetBySettings(remembered, how, store) {
  return remembered === true && store?.answer?.state === "store" && storeReady(how, store);
}

export function outputSetBySettings(remembered, place, outputParent) {
  return remembered === true && outputPlaceUsable(place, outputParent);
}

// Whether a box hides its button that confirms it: once it is confirmed, and
// while the settings of an earlier launch set it, until it changes (the
// mockup v10, stage B4c).
export function decideHidden(boxState, auto) {
  return boxState === "done" || auto === true;
}

// The box that a choice changes (stage B4c): the store to open or the place
// of a new one, and the way to normalize, are the second box's; the folder
// for the output is the third's; the Export is the first's, which confirms
// itself.
const CHANGED_BOXES = {
  "store-open": "snapshot",
  "store-place": "snapshot",
  how: "snapshot",
  output: "output",
};

export function changedBox(purpose) {
  return lookup(CHANGED_BOXES, purpose, null);
}

// What a change in a box takes back: its confirmation, and the remembered
// place that set it on a later launch; the box is confirmed again.
export function afterChange(box, confirmations) {
  const next = { ...confirmations };
  if (box === "snapshot") {
    next.snapshotDecided = false;
    next.snapshotAuto = false;
  } else if (box === "output") {
    next.outputDecided = false;
    next.outputAuto = false;
  }
  return next;
}

// The settings of an earlier launch, as the page takes them from the server
// (stage B4c): a later launch only with a remembered place, places as text,
// the tips as true or false, and the code of what to tell of the file.
export function launchSettings(status) {
  const settings = status?.settings;
  const text = (value) => (typeof value === "string" && value !== "" ? value : null);
  const store = text(settings?.store);
  const outputParent = text(settings?.output_parent);
  return {
    launch: settings?.launch === "later" && (store !== null || outputParent !== null) ? "later" : "first",
    store,
    outputParent,
    hints: typeof settings?.hints === "boolean" ? settings.hints : null,
    notice: lookup(SETTINGS_KEYS, settings?.notice, null) === null ? null : settings.notice,
    // Whether there is a file of the settings to forget (stage C1).
    present: settings?.present === true,
  };
}

// Whether there is a file of the settings to forget after a run ended (stage
// C1): a run that made its output remembers its places before the page
// learns that it ended, and then tells no notice.
export function settingsPresentAfterRun(present, run) {
  return present === true || (FINISHED_STATES.includes(run?.state) && run?.settings_notice === null);
}

// What the page tells after forgetting the settings (stage C1): the server
// says "forgotten" when no file is left, and whether there was one; when a
// file is left, it could not be removed.
export function forgetOutcome(answer) {
  if (answer?.forgotten === true) {
    return { key: answer.had_settings === false ? "forget.nothing" : "forget.done", notice: null, present: false };
  }
  return { key: null, notice: "SETTINGS_NOT_REMOVED", present: true };
}

// Whether the tips show (the mockup v10): as the person last switched them,
// otherwise on at a first launch and off at a later one (stage B4c).
export function hintsShown(settings) {
  return typeof settings?.hints === "boolean" ? settings.hints : settings?.launch !== "later";
}

export function settingsMessages(code, writing = false) {
  const key = lookup(writing ? SETTINGS_WRITE_KEYS : SETTINGS_KEYS, code, null);
  return key === null ? [] : [message(key)];
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
  // An import names its fields in the first box, and the store is the
  // second box's (stage B4b-1).
  SNAPSHOT_LABEL_INVALID: "export",
  SNAPSHOT_LABEL_EXISTS: "export",
  SNAPSHOT_TIME_INVALID: "export",
  SNAPSHOT_INPUT_INSIDE_STORE: "snapshot",
  SNAPSHOT_STORE_NOT_FOUND: "snapshot",
  SNAPSHOT_STORE_INVALID: "snapshot",
  SNAPSHOT_STORE_VERSION_UNSUPPORTED: "snapshot",
  SNAPSHOT_STORE_NOT_READABLE: "snapshot",
  SNAPSHOT_STORE_SYMLINK: "snapshot",
  SNAPSHOT_STORE_PARENT_NOT_FOUND: "snapshot",
  SNAPSHOT_STORE_NOT_EMPTY: "snapshot",
  SNAPSHOT_STORE_INSIDE_STORE: "snapshot",
  SNAPSHOT_STORE_PATH_TOO_LONG: "snapshot",
  SNAPSHOT_STORE_LOCKED: "snapshot",
  SNAPSHOT_REGISTRATION_INCOMPLETE: "snapshot",
  SNAPSHOT_STORE_NOT_WRITABLE: "snapshot",
  SNAPSHOT_STORE_SPACE_INSUFFICIENT: "snapshot",
  SNAPSHOT_STORE_EMPTY: "snapshot",
  SNAPSHOT_LIFECYCLE_FAILED: "snapshot",
  SNAPSHOT_UNLOCK_NOT_CONFIRMED: "snapshot",
  SNAPSHOT_LOCK_NOT_FOUND: "snapshot",
  SNAPSHOT_LOCK_INVALID: "snapshot",
};

// A path that the server reads as absolute: a POSIX path, a home path that it
// expands, a Windows drive, or a network share.
export function looksAbsolute(path) {
  return typeof path === "string" && /^(\/|~|[A-Za-z]:[\\/]|\\\\)/.test(path.trim());
}

// PATH_NOT_ABSOLUTE names no field; the run request checks the Export first.
export function errorBox(code, inputPath, detail = null) {
  if (code === "PATH_NOT_ABSOLUTE") {
    return looksAbsolute(inputPath) ? "output" : "export";
  }
  // An Export of another account, and a store of more than one, are the
  // second box's (stage B4b-2).
  if (mixOf(code, detail) !== null) {
    return "snapshot";
  }
  return lookup(ERROR_BOXES, code, "run");
}

// The state of each box: "current" (blue, what to do now), "done" (green),
// "todo", "error" (red, what to fix), or "stopped" (the fourth box when the
// run stopped in another box). On a first launch the second and third boxes
// are confirmed one at a time; on a later launch, a box that holds what the
// settings of the earlier launch remembered is set by itself while it has no
// problem (``snapshotAuto``, ``outputAuto``), and a box that changed is
// confirmed again (stage B4c). After a run that finished or stopped, a change
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
  // The timezone data that the pre-run check found missing belongs to the
  // third box; the first box waits until the check can count the Activities
  // (stage B3b).
  if (view.timezoneProblem) {
    states.export = "current";
    states.output = "error";
    return states;
  }
  const done = [
    view.exportReady,
    view.snapshotDecided || view.snapshotAuto === true,
    view.outputDecided || view.outputAuto === true,
  ];
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
  // A Snapshot run needs a store without a problem: the second box is red
  // until the store is fixed or another way is chosen (stage B4b-1).
  if (view.storeProblem === true) {
    states.snapshot = "error";
    if (states.output === "current") {
      states.output = "todo";
    }
    states.run = "todo";
  }
  // A remembered folder for the output that is not found (stage B4c).
  if (view.outputProblem === true) {
    states.output = "error";
    states.run = "todo";
  }
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
  // A dialog of the system to choose the Export is open (stage B3a), or one
  // to choose a folder for the store or the output (stage B4a).
  if (view.choosing === true) {
    return message(view.choosingFolder === true ? "next_line.choosing_folder" : "next_line.choosing");
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
    // The page checks a chosen Export by itself.
    if (view.checking) {
      return message("next_line.checking");
    }
    if (view.extractNeeded && !view.extractConfirmed) {
      return message("next_line.confirm_extract");
    }
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

// The color of the line under the title, as the line reads: the run or the
// dialog in blue, the end of the last run while no box changed since, red
// while a box has a problem, and blue otherwise (stage B3a).
export function nextLineKind(view, states) {
  const runState = view.runState;
  if (view.starting || ACTIVE_STATES.includes(runState) || view.choosing === true) {
    return "current";
  }
  if (!view.editedSinceRun && runState === "finished_after_cancel") {
    return "warn";
  }
  if (!view.editedSinceRun && runState === "finished") {
    return (view.result?.warning_count ?? 0) > 0 ? "warn" : "done";
  }
  return BOXES.some((box) => states[box] === "error") ? "error" : "current";
}

// The steps of a run of one Export, and the stages of Run-All that each one
// covers. The last step is the page's check of the output after the run.
export const RUN_STEPS = [
  { key: "steps.check_export", stages: ["discovering"] },
  { key: "steps.convert", stages: ["normalizing", "reading_fit", "verifying_input", "building_output"] },
  { key: "steps.write", stages: ["writing_output"] },
  { key: "steps.check_output", stages: [] },
];
// The steps of a Snapshot run (stage B4b-1), as the mockup v10 gives them:
// an import reads the Export, then copies it into the store, which a first
// import makes; the Snapshots are checked, then read or built into one input,
// which Run-All then reads. Normalizing the Snapshots again starts with the
// check.
const CHECK_STORE_STEP = { key: "steps.check_store", stages: ["checking_store"] };
const READ_SNAPSHOTS = ["building_snapshots", "discovering"];

function positive(value) {
  return Number.isInteger(value) && value > 0 ? value : null;
}

// The steps of a way to normalize: "single", "snapshots", or "rerun".
// ``numbers`` are the place of the imported Snapshot in the order and the
// number of Snapshots after the import, when they are known; a new store's
// import is its first Snapshot.
export function runSteps(how, newStore = false, numbers = {}) {
  const after = RUN_STEPS.slice(1);
  if (how === "rerun") {
    return [CHECK_STORE_STEP, { key: "steps.build_existing", stages: READ_SNAPSHOTS }, ...after];
  }
  if (how !== "snapshots") {
    return RUN_STEPS;
  }
  const order = positive(numbers?.order);
  const count = positive(numbers?.count);
  let importStep = { key: "steps.import", stages: ["importing"] };
  if (newStore) {
    importStep = { key: "steps.import_new", stages: ["creating_store", "importing"] };
  } else if (order !== null) {
    importStep = { ...importStep, key: "steps.import_nth", params: { order } };
  }
  let readStep = { key: "steps.build_snapshots", stages: READ_SNAPSHOTS };
  if (newStore || count === 1) {
    readStep = { ...readStep, key: "steps.read_snapshot" };
  } else if (count !== null) {
    readStep = { ...readStep, key: "steps.build_count", params: { count } };
  }
  return [{ key: "steps.check_export", stages: ["reading_export"] }, importStep, CHECK_STORE_STEP, readStep, ...after];
}

// The step that a stage belongs to, or 0 before the first stage.
function stepOf(steps, stage) {
  const index = steps.findIndex((step) => step.stages.includes(stage));
  return index < 0 ? 0 : index;
}

// The steps of a run as its status gives its way, or as the page is set.
function stepsOf(status, how, newStore, numbers) {
  return runSteps(typeof status?.how === "string" ? status.how : how, newStore, numbers);
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
export function stepRows(status, outputCheck, outputCheckSeconds = null, how = "single", newStore = false, numbers = {}) {
  const runState = status?.state;
  const steps = stepsOf(status, how, newStore, numbers);
  const checkStep = steps.length - 1;
  const seconds = (index) =>
    index === checkStep
      ? FINISHED_STATES.includes(runState) && typeof outputCheckSeconds === "number"
        ? outputCheckSeconds
        : null
      : stepSeconds(steps[index], status?.stage_seconds);
  const rows = steps.map((step, index) => ({
    key: step.key,
    ...(step.params ? { params: step.params } : {}),
    state: "todo",
    seconds: seconds(index),
  }));
  if (ACTIVE_STATES.includes(runState)) {
    const current = stepOf(steps, status.progress?.stage);
    rows.forEach((row, index) => {
      row.state = index < current ? "done" : index === current ? "run" : "todo";
    });
  } else if (FINISHED_STATES.includes(runState)) {
    rows.forEach((row) => {
      row.state = "done";
    });
    if ((status.result?.warning_count ?? 0) > 0) {
      rows[stepOf(steps, "normalizing")].state = "warn";
    }
    rows[checkStep].state = outputCheck === "running" ? "run" : outputCheck ?? "todo";
  } else if (runState === "failed" || runState === "cancelled") {
    const last = stepOf(steps, status.progress?.stage);
    rows.forEach((row, index) => {
      row.state = index < last ? "done" : index === last ? (runState === "failed" ? "error" : "cancelled") : "skipped";
    });
  }
  return rows;
}

// Where a run is, for the line under the headline: the step and how many.
export function currentStep(status, how = "single", newStore = false, numbers = {}) {
  const steps = stepsOf(status, how, newStore, numbers);
  const index = stepOf(steps, status?.progress?.stage);
  const step = steps[index];
  return { key: step.key, ...(step.params ? { params: step.params } : {}), number: index + 1, total: steps.length };
}

// The headline of the fourth box, the exit code under it, and the line under
// that. The exit code is the CLI's for the same run; a run cancelled before
// its output shows none, because 130 means nothing on the page.
export function runSummary(status, states, view = {}) {
  const runState = status?.state;
  const result = status?.result;
  if (view.starting || runState === "running") {
    const step = currentStep(status, view.how, view.newStore, view.stepNumbers);
    // A step with numbers names them (stage B4b-1).
    const name = step.params ? message(step.key, step.params) : step.key;
    return {
      headline: message("run.headline_running"),
      exitCode: null,
      sub: message("run.sub_running", { number: step.number, total: step.total }, { step: name }),
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
  // What the import of a Snapshot run did, which stays also when the run
  // then stopped (stage B4b-1). The order is that of the times of the
  // Exports, not of the imports.
  const imported = status?.imported;
  if (imported !== null && typeof imported === "object" && Number.isInteger(imported.order)) {
    messages.push(
      imported.same_content === true
        ? message("result.import_same", { order: imported.order })
        : message("result.import_done", { order: imported.order, count: imported.snapshot_count }),
    );
    if (status.state === "failed" || status.state === "cancelled") {
      messages.push(message("result.import_kept"));
    }
  }
  if (Array.isArray(status?.staging_folders) && status.staging_folders.length > 0) {
    messages.push(message("result.staging_left", { names: status.staging_folders.join(", ") }));
    messages.push(nextStep("next.delete_staging"));
  }
  // The places of a run that made its output are the settings of the next
  // launch; the page says when they could not be remembered (stage B4c).
  if (FINISHED_STATES.includes(state)) {
    messages.push(...settingsMessages(status.settings_notice, true));
  }
  // What a cancelled import left in the store, as the CLI says it after a
  // cancelled registration (stage B4b-2).
  if (status?.state === "cancelled" && Array.isArray(status.store_notices)) {
    for (const code of STORE_WARN_CODES.filter((item) => status.store_notices.includes(item))) {
      messages.push(message(STOP_KEYS[code]));
      messages.push(nextStep(STOP_NEXT_KEYS[code]));
    }
  }
  return messages;
}

// The words that sum up a confirmed box (a green line under its heading).
// A box that the settings of an earlier launch set says so (stage B4c).
export function boxSummary(box, view) {
  const words = confirmedWords(box, view);
  const auto = box === "snapshot" ? view.snapshotAuto === true : box === "output" ? view.outputAuto === true : false;
  const ran = FINISHED_STATES.includes(view.runState) && !view.editedSinceRun;
  return words !== null && auto && !ran ? message("summary.as_last_time", {}, { summary: words }) : words;
}

function confirmedWords(box, view) {
  // What the last run did, while no box changed since (stage B4b-1), as the
  // mockup v10 says it.
  const ran = FINISHED_STATES.includes(view.runState) && !view.editedSinceRun;
  if (box === "export") {
    // Normalizing the Snapshots again takes no Export (stage B4b-1).
    if (view.how === "rerun") {
      return message("summary.export_rerun");
    }
    // After the page is loaded again, the field is empty, as the settings
    // never remember the Export (stage B4c); the fourth box names the output.
    const name = lastName(view.inputPath);
    if (name === "") {
      return null;
    }
    if (ran && view.imported) {
      return message(view.imported.same_content === true ? "summary.export_same" : "summary.export_imported", { name });
    }
    return message(view.how === "snapshots" ? "summary.export_import" : "summary.export", { name });
  }
  if (box === "snapshot") {
    const count = Number.isInteger(view.snapshotCount) ? view.snapshotCount : 0;
    if (ran && (view.runHow === "snapshots" || view.runHow === "rerun")) {
      const used = Number.isInteger(view.result?.snapshot_count) ? view.result.snapshot_count : count;
      if (view.runHow === "rerun") {
        return message("summary.snapshot_rerun_done", { count: used });
      }
      return view.madeStore ? message("summary.snapshot_new_done") : message("summary.snapshot_done", { count: used });
    }
    if (view.how === "rerun") {
      return message("summary.snapshot_rerun", { count });
    }
    if (view.how === "snapshots") {
      return view.newStore ? message("summary.snapshot_new") : message("summary.snapshot_import", { count });
    }
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
  // An output of 1.3 has none of the diagnostics of v1.4, and the result
  // that it recorded is the one to use (stage B5b).
  if (doctor?.legacy === true) {
    messages.push(message("output_check.legacy"));
    if (typeof doctor.product_version === "string") {
      messages.push(message("error.made_by_version", { version: doctor.product_version }));
    }
    messages.push(nextStep("output_check.legacy_next"));
    return messages;
  }
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
    // A run that ends within its first seconds speaks only its end: a
    // message given to the live region is spoken even after a later one, so
    // the first stage waits until the run has gone on (stage C1).
    if (typeof status.elapsed_seconds === "number" && status.elapsed_seconds < QUIET_START_SECONDS) {
      return null;
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
  const busy = running || view.checking || view.outputBusy || view.choosing === true;
  const filled = (value) => typeof value === "string" && value.trim() !== "";
  const outputReady =
    filled(view.outputParent) && filled(view.timezone) && isValidOutputName(view.outputName);
  return {
    form: view.connected && !running,
    choose: view.connected && !busy,
    browse: view.connected && !busy,
    check: view.connected && !busy && filled(view.inputPath),
    decideSnapshot: view.connected && !busy && states.snapshot === "current",
    decideOutput: view.connected && !busy && states.output === "current" && outputReady,
    start:
      view.connected &&
      !busy &&
      view.checkedReady &&
      outputReady &&
      typeof view.importProblem !== "string" &&
      view.storeReady !== false &&
      (states.run === "current" ||
        ((FINISHED_STATES.includes(view.runState) || view.runState === "failed") &&
          (view.snapshotDecided || view.snapshotAuto === true) &&
          (view.outputDecided || view.outputAuto === true))),
    cancel: view.connected && view.runState === "running",
    quit: view.connected && !running && !view.outputBusy,
    outputActions: view.connected && !busy && FINISHED_STATES.includes(view.runState),
    // The settings are not forgotten while a run, which remembers its places
    // when it ends, is active (stage B4c), nor when there is no file of them
    // (stage C1).
    forget: view.connected && !running && view.forgetBusy !== true && view.settingsPresent === true,
  };
}

// The one button that the page fills with its accent color, so that the next
// step is clear (stage C1): after a run that made its output, until a box
// changes, the button that shows the output (as from stage B5a); otherwise
// the confirmation of the second or third box while it is the current one and
// shows, and then Normalize while it can start. Never more than one, and
// never a button that cannot be pressed; null when none of them is the next
// step.
export function primaryControl(view, states, enabled) {
  if (FINISHED_STATES.includes(view.runState) && !view.editedSinceRun) {
    return enabled.outputActions ? "openFolder" : null;
  }
  if (enabled.decideSnapshot && states.snapshot === "current" && !decideHidden(states.snapshot, view.snapshotAuto)) {
    return "snapshotDecide";
  }
  if (enabled.decideOutput && states.output === "current" && !decideHidden(states.output, view.outputAuto)) {
    return "outputDecide";
  }
  return enabled.start ? "start" : null;
}

// Which boxes must still be confirmed before a run can start, by number.
export function boxesToConfirm(states) {
  return ["export", "snapshot", "output"].filter((box) => states[box] !== "done").map(boxNumber);
}

// The fields of an import (the name and the time of the download) are for
// the next import: they show until a run has finished and nothing has
// changed since, when the second box shows what the run imported, or that
// the Export was there already (stage B6a). They show again while the name
// or the time keeps a run from starting, so that the reason is in sight.
export function importFieldsShown(view) {
  return (
    view?.how === "snapshots" &&
    view?.checkedReady === true &&
    (typeof view?.importProblem === "string" ||
      !(FINISHED_STATES.includes(view?.runState) && view?.editedSinceRun !== true))
  );
}

// Whether the list of the second box says that an Export of the same content
// adds no new Snapshot: while it holds the Export that the run will import
// and a Snapshot to compare it with, which the import does (stage B6a).
export function sameContentNoted(rows) {
  return (
    Array.isArray(rows) &&
    rows.some((row) => row?.state === "pending") &&
    rows.some((row) => row?.state !== "pending")
  );
}

// The lines of a stop apart from the line of its report, which the first
// and second box show after the buttons that fix the stop (stage B6a).
export function apartReport(lines) {
  const items = Array.isArray(lines) ? lines : [];
  return { lines: items.filter((line) => !line?.report), report: items.filter((line) => Boolean(line?.report)) };
}

// The parts of the help panel, in the order of its buttons (stage B1b), and
// the GitHub report (stage B5c).
export const HELP_SECTIONS = ["steps", "faq", "words", "ai", "report"];

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

// The GitHub report and the pages outside this app (stage B5c). The page
// reads nothing outside and sends nothing itself: a link opens in a new tab
// only when it is pressed, and the address of the report carries only the
// values that the help panel shows before it.
export const REPOSITORY = "https://github.com/tsubotti63/garmin-running-data-normalizer";
export const GARMIN_DATA_PAGE = "https://www.garmin.com/account/datamanagement/";
// Every page that this app links to starts with one of these.
export const OUTSIDE_PREFIXES = [`${REPOSITORY}/`, GARMIN_DATA_PAGE];
// The documents of the repository that the help panel links to.
export const OUTSIDE_DOCUMENTS = [
  "docs/gui_guide.md",
  "docs/gui_guide.ja.md",
  "docs/getting_started_from_garmin_export.md",
  "docs/faq.md",
  "docs/known_limitations.md",
  "docs/ai_analysis_quick_start.md",
  "SUPPORT.md",
];
// A version as the releases name theirs; their tags add a "v" before it.
const RELEASE_VERSION = /^(?:0|[1-9][0-9]{0,3})(?:\.(?:0|[1-9][0-9]{0,3})){1,2}(?:(?:a|b|rc)(?:0|[1-9][0-9]{0,3}))?$/;

// The address of a link of the help panel: the page of Garmin, the private
// channel for a vulnerability, or a document at the tag of this version, so
// that it describes the version that is installed. A version in development
// keeps the name of the release before it, whose tag has no GUI guide yet:
// those links open once the tag of 2.0.0 is made. Null for anything else, and
// until the version is known.
export function outsideUrl(link, version) {
  if (link === "garmin") {
    return GARMIN_DATA_PAGE;
  }
  if (link === "security") {
    return `${REPOSITORY}/security/advisories/new`;
  }
  if (OUTSIDE_DOCUMENTS.includes(link) && typeof version === "string" && RELEASE_VERSION.test(version)) {
    return `${REPOSITORY}/blob/v${version}/${link}`;
  }
  return null;
}

// The fields of the form "Bug report" of the repository
// (.github/ISSUE_TEMPLATE), in its order, with the words of the table that
// shows them first. The title is not a field of the form, but its address
// takes one too. The person writes the problem and chooses whether the
// synthetic data shows it on GitHub, and ticks the four checks of privacy
// there.
export const REPORT_FORM = `bug_report.yml`;
export const REPORT_FIELDS = [
  { id: "title", key: "report.field_title" },
  { id: "problem", key: "report.field_problem", person: "report.person_writes" },
  { id: "guide", key: "report.field_guide" },
  { id: "operating_system", key: "report.field_os" },
  { id: "shell", key: "report.field_shell" },
  { id: "python_version", key: "report.field_python" },
  { id: "package_version", key: "report.field_version" },
  { id: "reproduction", key: "report.field_reproduction" },
  { id: "exit_code", key: "report.field_exit" },
  { id: "synthetic_reproduction", key: "report.field_synthetic", person: "report.person_chooses" },
  { id: "logs", key: "report.field_logs" },
];

// The words of the report are English, as the form and the reports of the
// repository are; the table shows them as they go in.
const REPORT_HOW = {
  snapshots: "import into the Snapshots and normalize them together",
  single: "normalize this export only",
  rerun: "normalize the Snapshots again",
};
const REPORT_EXPORT = { zip: "ZIP file", folder: "extracted folder" };
const REPORT_CODE = /^[A-Z][A-Z0-9_]{0,63}$/;
// What this computer's values may hold, as the server makes them.
const REPORT_COMPUTER = /^[A-Za-z0-9 ._()+-]{1,80}$/;

const computerValue = (value) => (typeof value === "string" && REPORT_COMPUTER.test(value) ? value : "");

// The values of the report, one row for each field of the form, in its
// order: the code and the part of the page of the stop that it is about,
// how this launch normalizes, and this computer's values as the server
// gives them (``english`` gives the English words of a message key). No
// place, name, count, time, timezone, or account goes in.
export function reportRows(facts, computer, english) {
  const code = typeof facts?.code === "string" && REPORT_CODE.test(facts.code) ? facts.code : "";
  const part = typeof facts?.partKey === "string" ? english(facts.partKey) : "";
  const lines = [`Launch: ${facts?.launch === "later" ? "later" : "first"}.`];
  if (Object.hasOwn(REPORT_EXPORT, facts?.exportKind ?? "")) {
    lines.push(`Export: ${REPORT_EXPORT[facts.exportKind]}.`);
  }
  if (Object.hasOwn(REPORT_HOW, facts?.how ?? "")) {
    lines.push(`How: ${REPORT_HOW[facts.how]}.`);
  }
  const exit = String(facts?.exitCode ?? "");
  const values = {
    title: code === "" ? "[Bug]: " : `[Bug]: ${code} in the GUI`,
    guide: part === "" ? "GUI" : `GUI — ${part}`,
    operating_system: computerValue(computer?.operating_system),
    shell: "None (run from the GUI)",
    python_version: computerValue(computer?.python_version),
    package_version: computerValue(computer?.package_version),
    reproduction: lines.join("\n"),
    exit_code: ["0", "2", "3"].includes(exit) ? exit : "",
    logs: code,
  };
  return REPORT_FIELDS.map((field) => ({ ...field, value: values[field.id] ?? "" }));
}

// The address of the form with the values of the rows, in their order; a
// field without a value is left to the form.
export function reportUrl(rows) {
  const query = [`template=${REPORT_FORM}`];
  for (const row of rows) {
    if (row.value !== "") {
      query.push(`${row.id}=${encodeURIComponent(row.value)}`);
    }
  }
  return `${REPOSITORY}/issues/new?${query.join("&")}`;
}

// What a report opened from the help panel or the fourth box is about: the
// first stop that the page shows, from the top, or else the result of the
// last run, or nothing. A stop's report comes from the line under it.
export function reportFacts(shownStops, run) {
  if (Array.isArray(shownStops) && shownStops.length > 0) {
    return { code: shownStops[0].code, partKey: shownStops[0].partKey, exitCode: 2 };
  }
  if (FINISHED_STATES.includes(run?.state) && run?.result) {
    return { code: run.result.status, partKey: "run.start", exitCode: run.result.exit_code };
  }
  return {};
}
