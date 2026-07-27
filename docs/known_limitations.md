# Known Limitations

These limitations apply to the stable v1.2.1 release. They are
explicit product boundaries, not hidden fallback behavior.

## Input and orchestration

- Run-All requires a supported `summarizedActivities.json` asset.
- Gear, Personal Records, and FIT are optional and use exact filename or bounded
  FIT discovery rules.
- Existing output is never overwritten. A new output directory is required for
  each run.
- A detected but incompletely parsed FIT asset produces auditable
  `PARTIAL_SUCCESS` rather than silent omission.
- The compatible one-shot Run-All processes one supplied Export. It does not
  accumulate historical records across multiple Export downloads.
- A newer Export can omit files, periods, records, or fields observed in an
  older Export. Missing from the newer Export is not evidence of deletion.
  Retain every downloaded Export until the additive Snapshot lifecycle has
  registered and verified it.

## Snapshot lifecycle

- The v1.2.0 workflow stores complete, explicitly confirmed Export
  observations in one private local store per opaque account boundary.
- Canonical merge uses `missing_is_not_delete`; explicit null and empty values
  preserve the prior explicit value and become review holds.
- Automatic deletion, snapshot/blob deletion, and garbage collection are not
  implemented. Unknown and unsupported inputs are preserved as raw evidence,
  not promoted to normalized public datasets.
- A Snapshot Store is not a public artifact or a backup service. Back up only
  after integrity verification and verify again after restore.

## FIT

- Only selected Activity session and lap fields are normalized.
- Chained FIT payloads are rejected rather than merged.
- Multi-session FIT is normalized only when declared lap counts allocate every
  lap to exactly one session. Allocation conflicts exclude the whole file from
  normalized sessions/laps, remain explicit in FIT audit, and do not enter the
  eligible Activity/FIT Relationship Coverage population.
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
- Sleep, HRV, and Health Status are not Run-All output families in v1.2.0.

## Distribution and integrations

- Hosted processing, Garmin authentication, Open-Meteo, JMA, Instagram,
  wellness/coaching interpretation, Parquet output, and automatic personal
  analysis are outside the stable scope.
- Stable v1.2.1 declares `tzdata` as a Windows-only runtime dependency and emits
  the bounded `TIMEZONE_DATA_UNAVAILABLE` diagnostic if IANA timezone data is
  unavailable in an incomplete environment. Validation covers GitHub Actions
  `windows-latest` and one maintainer-owned physical Windows Production PyPI
  clean install. This does not establish universal Windows compatibility.
- External-safe output is opt-in, month-granularity, Activities-only, and does
  not automatically upload or provide provider-specific privacy guarantees.

The documented CLI and versioned Run-All output contract are stable for `1.x`.
Other Python modules are usable but are not all promoted to an independently
stable third-party API contract.
