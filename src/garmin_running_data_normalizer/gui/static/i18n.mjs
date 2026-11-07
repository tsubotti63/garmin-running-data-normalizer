// Message catalog helpers for the GUI page. They do not touch the DOM, so the
// tests in tests/gui_js run them with node --test.

export const DEFAULT_LANGUAGE = "en";

// Return the stored choice if it is available, otherwise the first browser
// language whose primary subtag is available, otherwise English.
export function chooseLanguage(available, stored, browserLanguages) {
  if (typeof stored === "string" && available.includes(stored)) {
    return stored;
  }
  for (const tag of browserLanguages ?? []) {
    if (typeof tag !== "string") {
      continue;
    }
    const primary = tag.split("-")[0].toLowerCase();
    if (available.includes(primary)) {
      return primary;
    }
  }
  return DEFAULT_LANGUAGE;
}

// Fill {name} placeholders; a placeholder without a value stays visible.
export function formatMessage(template, params = {}) {
  return template.replace(/\{([A-Za-z0-9_]+)\}/g, (placeholder, name) =>
    Object.hasOwn(params, name) ? String(params[name]) : placeholder,
  );
}

function lookup(catalogs, language, key) {
  if (!Object.hasOwn(catalogs, language)) {
    return undefined;
  }
  const catalog = catalogs[language];
  if (catalog === null || typeof catalog !== "object" || !Object.hasOwn(catalog, key)) {
    return undefined;
  }
  return typeof catalog[key] === "string" ? catalog[key] : undefined;
}

// Return the message in the language, falling back to English, then to the key.
export function translate(catalogs, language, key, params = {}) {
  const template =
    lookup(catalogs, language, key) ?? lookup(catalogs, DEFAULT_LANGUAGE, key) ?? key;
  return formatMessage(template, params);
}

// The words for a count of one (stage U1 of v2.2.0): the key of each message
// whose English says a count of several, with the key of its words for one,
// whose Japanese is the same. Written out whole, so that the test of the keys
// that the pages use finds them (Codex's review of the plan of U1, 7).
export const ONE_KEYS = Object.freeze({
  "view.note.activity_disagree": "view.note.activity_disagree_one",
  "view.note.activity_missing": "view.note.activity_missing_one",
  "view.note.after_today": "view.note.after_today_one",
  "view.note.day_disagree": "view.note.day_disagree_one",
  "view.note.fit_missing": "view.note.fit_missing_one",
  "view.note.no_date": "view.note.no_date_one",
  "view.note.no_duration": "view.note.no_duration_one",
  "view.note.record_disagree": "view.note.record_disagree_one",
  "view.note.several_mean": "view.note.several_mean_one",
  "view.note.several_points": "view.note.several_points_one",
  "view.compare.weeks_before": "view.compare.weeks_before_one",
  "view.shoes.note_without": "view.shoes.note_without_one",
  "view.shoes.note_unknown": "view.shoes.note_unknown_one",
  "view.shoes.note_no_distance": "view.shoes.note_no_distance_one",
  "view.shoes.note_left_out": "view.shoes.note_left_out_one",
  "next_line.done_partial": "next_line.done_partial_one",
  "next_line.done_warnings": "next_line.done_warnings_one",
  "result.sub_pass_with_warnings": "result.sub_pass_with_warnings_one",
  "rerun.chosen": "rerun.chosen_one",
  "summary.snapshot_done": "summary.snapshot_done_one",
  "summary.snapshot_import": "summary.snapshot_import_one",
  "summary.snapshot_rerun": "summary.snapshot_rerun_one",
  "summary.snapshot_rerun_done": "summary.snapshot_rerun_done_one",
  "progress.building_snapshots": "progress.building_snapshots_one",
  // By the number of the families with warnings, not of the warnings.
  "output_check.warnings": "output_check.warnings_one",
  // The laps of an activity (stage X10 of v2.3.0).
  "view.laps.unknown_note": "view.laps.unknown_note_one",
  "view.laps.no_distance": "view.laps.no_distance_one",
});

// The key of a message for a count: its words for one where the count is the
// whole number 1, as a page has it before it writes it with separators
// (stage U1 of v2.2.0), and the key itself otherwise.
export function countKey(key, count) {
  return count === 1 && Object.hasOwn(ONE_KEYS, key) ? ONE_KEYS[key] : key;
}
