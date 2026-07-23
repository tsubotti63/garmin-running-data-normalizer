# Known Limitations

These limitations apply to the `1.1` release candidate. They are explicit product
boundaries, not hidden fallback behavior.

## Input and orchestration

- Run-All requires a supported `summarizedActivities.json` asset.
- Gear, Personal Records, and FIT are optional and use exact filename or bounded
  FIT discovery rules.
- Existing output is never overwritten. A new output directory is required for
  each run.
- A detected but incompletely parsed FIT asset produces auditable
  `PARTIAL_SUCCESS` rather than silent omission.

## FIT

- Only selected Activity session and lap fields are normalized.
- Chained FIT payloads are rejected rather than merged.
- Activity/FIT linkage is limited to the documented evidence-qualified eligible
  population; excluded and ambiguous candidates are not guessed.
- Record coordinates, raw telemetry, and arbitrary FIT message preservation are
  intentionally excluded from public output.

## Library-only datasets

- Sleep is not reconciled with FIT, does not recalculate scores, fill missing
  days, infer naps, shift days, or join activities.
- Conflicting same-date HRV candidates are not averaged. Garmin/FIT raw sentinel
  `65535` is excluded, and Health Status HRV is not asserted to be equivalent to
  nightly FIT HRV.
- Health Status unknown metrics remain in long-form evidence; duplicate metric
  types are not silently overwritten.
- Sleep, HRV, and Health Status are not Run-All output families in v1.1.

## Distribution and integrations

- No v1.1 PyPI distribution is published before the separate approval boundary.
- Hosted processing, Garmin authentication, Open-Meteo, JMA, Instagram,
  wellness/coaching interpretation, Parquet output, and automatic personal
  analysis are outside the stable scope.
- No third-party runtime package dependency is declared.
- External-safe output is opt-in, month-granularity, Activities-only, and does
  not automatically upload or provide provider-specific privacy guarantees.

The documented CLI and versioned Run-All output contract are stable for `1.x`.
Other Python modules are usable but are not all promoted to an independently
stable third-party API contract.
