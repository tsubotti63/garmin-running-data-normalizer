// Run page rules that do not touch the DOM, so that node --test can check
// them. Message keys appear here only as literal strings, so that tests can
// check them against the catalogs.

export const ACTIVE_STATES = ["running", "cancelling"];
export const TERMINAL_STATES = ["finished", "finished_after_cancel", "cancelled", "failed"];
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

// Codes from the server, the run manager, the folder browser, and Run-All.
export const ERROR_KEYS = {
  PATH_NOT_ABSOLUTE: "error.path_not_absolute",
  PATH_INVALID: "error.request_invalid",
  INPUT_PATH_INVALID: "error.request_invalid",
  OUTPUT_PARENT_INVALID: "error.request_invalid",
  REQUEST_INVALID: "error.request_invalid",
  FOLDER_NOT_FOUND: "error.folder_not_found",
  INPUT_NOT_DIRECTORY: "error.folder_not_found",
  NOT_A_FOLDER: "error.not_a_folder",
  FOLDER_NOT_READABLE: "error.folder_not_readable",
  INPUT_SYMLINK: "error.symlink",
  OUTPUT_SYMLINK: "error.symlink",
  OUTPUT_PARENT_NOT_FOUND: "error.output_parent_not_found",
  OUTPUT_NAME_INVALID: "error.output_name_invalid",
  OUTPUT_EXISTS: "error.output_exists",
  OUTPUT_INSIDE_INPUT: "error.output_inside_input",
  TIMEZONE_INVALID: "error.timezone_invalid",
  TIMEZONE_DATA_UNAVAILABLE: "error.timezone_data_unavailable",
  ACTIVITIES_NOT_FOUND: "error.activities_not_found",
  ACTIVITIES_EMPTY: "error.activities_not_found",
  INPUT_CHANGED: "error.input_changed",
  INPUT_DISCOVERY_FAILED: "error.input_unreadable",
  DIVERGENT_DUPLICATE: "error.data_conflict",
  DAILY_METRICS_CONFLICT: "error.data_conflict",
  PERFORMANCE_METRICS_CONFLICT: "error.data_conflict",
  ACTIVITIES_NORMALIZATION_FAILED: "error.conversion_failed",
  GEAR_NORMALIZATION_FAILED: "error.conversion_failed",
  PERSONAL_RECORDS_NORMALIZATION_FAILED: "error.conversion_failed",
  FIT_PROCESSING_FAILED: "error.conversion_failed",
  DAILY_METRICS_NORMALIZATION_FAILED: "error.conversion_failed",
  PERFORMANCE_METRICS_NORMALIZATION_FAILED: "error.conversion_failed",
  OUTPUT_PUBLISH_FAILED: "error.publish_failed",
  DATASET_NOT_SERIALIZABLE: "error.internal",
  DATASET_TABLE_INVALID: "error.internal",
  OUTPUT_CONTRACT_INVALID: "error.internal",
  OUTPUT_EXPERIENCE_FAILED: "error.internal",
  PROVENANCE_MISMATCH: "error.internal",
  RELATIONSHIP_CONTRACT_FAILED: "error.internal",
  SNAPSHOT_CONTEXT_INVALID: "error.internal",
  STABLE_KEY_MISSING: "error.internal",
  RUN_ALL_FAILED: "error.internal",
  RUN_START_FAILED: "error.internal",
  RUN_ACTIVE: "error.run_active",
};

// Pre-run Doctor message and next-action identifiers.
export const FINDING_KEYS = {
  INPUT_DIRECTORY_MUST_BE_LOCAL_DIRECTORY: "finding.input_directory",
  INSTALL_REQUIRED_TIMEZONE_DATA: "finding.timezone_data",
  INPUT_COULD_NOT_BE_SAFELY_DISCOVERED: "finding.input_unreadable",
  REQUIRED_ACTIVITIES_SOURCE_NOT_OBSERVED: "finding.activities_missing",
  INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT: "finding.ready",
};
export const ACTION_KEYS = {
  SELECT_VALID_EXPORT_DIRECTORY: "action.select_folder",
  REPAIR_RUNTIME_ENVIRONMENT: "action.repair_python",
  OBTAIN_COMPLETE_READABLE_EXPORT: "action.get_new_export",
  SELECT_EXPORT_WITH_ACTIVITIES: "action.select_export_with_activities",
  RUN_ALL: "action.run_all",
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
const RESULT_KEYS = {
  PASS: "result.pass",
  PASS_WITH_WARNINGS: "result.pass_with_warnings",
  PARTIAL_SUCCESS: "result.partial_success",
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
export function errorMessage(code) {
  return { key: lookup(ERROR_KEYS, code, "error.unknown"), params: {}, keyParams: {} };
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

export function findingMessages(finding) {
  return {
    message: lookup(FINDING_KEYS, finding?.message_id, "error.unknown"),
    action: lookup(ACTION_KEYS, finding?.next_action_id, null),
  };
}

export function familyRows(result) {
  const families = result?.families ?? {};
  return Object.keys(families)
    .sort()
    .map((family) => ({
      family,
      nameKey: lookup(FAMILY_KEYS, family, null),
      statusKey: lookup(FAMILY_STATUS_KEYS, families[family]?.status, "family_status.other"),
      records: families[family]?.record_count ?? 0,
      warnings: families[family]?.warning_count ?? 0,
    }));
}

export function warningCount(result) {
  return familyRows(result).reduce((sum, row) => sum + row.warnings, 0);
}

// Messages for the result area of a finished, cancelled, or failed run.
export function resultMessages(status) {
  const messages = [];
  const state = status?.state;
  if (state === "finished") {
    messages.push({ key: lookup(RESULT_KEYS, status.result?.status, "error.unknown"), params: {}, keyParams: {} });
  } else if (state === "finished_after_cancel") {
    messages.push({ key: "result.finished_after_cancel", params: {}, keyParams: {} });
  } else if (state === "cancelled") {
    messages.push({ key: "result.cancelled", params: {}, keyParams: {} });
  } else if (state === "failed") {
    messages.push({ key: "result.failed", params: {}, keyParams: {} });
    messages.push(errorMessage(status.error_code));
    messages.push({ key: "error.code", params: { code: status.error_code ?? "" }, keyParams: {} });
  }
  if (state === "finished" && status.result) {
    messages.push({ key: "result.warnings", params: { count: warningCount(status.result) }, keyParams: {} });
  }
  if ((state === "finished" || state === "finished_after_cancel") && status.output_path) {
    messages.push({ key: "result.output", params: { path: status.output_path }, keyParams: {} });
  }
  if (Array.isArray(status?.staging_folders) && status.staging_folders.length > 0) {
    messages.push({
      key: "result.staging_left",
      params: { names: status.staging_folders.join(", ") },
      keyParams: {},
    });
  }
  return messages;
}

// Mirrors the server's rule; the server stays the authority.
export function isValidOutputName(name) {
  if (typeof name !== "string" || name.length === 0 || name.length > 255) {
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

// Which controls the page enables, from one view of its state.
export function controls(view) {
  const running = ACTIVE_STATES.includes(view.runState) || view.starting;
  const busy = running || view.checking;
  const filled = (value) => typeof value === "string" && value.trim() !== "";
  return {
    form: view.connected && !running,
    browse: view.connected && !busy,
    check: view.connected && !busy && filled(view.inputPath),
    start:
      view.connected &&
      !busy &&
      view.checkedReady &&
      filled(view.outputParent) &&
      filled(view.timezone) &&
      isValidOutputName(view.outputName),
    cancel: view.connected && view.runState === "running",
    quit: view.connected && !running,
  };
}
