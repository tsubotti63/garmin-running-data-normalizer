# Known Limitations

These limitations apply to the published stable v1.3.2 GitHub Release and
Production PyPI distribution. They remain explicit Product boundaries after
publication.

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

## Daily-metric boundaries

- v1.3 Sleep is not reconciled with FIT and does not
  recalculate scores, fill missing days, infer naps, shift days, or create an
  Activity relationship. A same-day `context_only` comparison must keep Sleep
  and Activity facts separate.
- The v1.3.3 Sleep contract candidate derives ex-awake duration only from
  observed finite deep/light/REM stages when any are present. It never fills a
  missing stage with zero or subtracts awake time from the sleep window. When
  all stages are absent, only the approved direct aliases
  (`sleepTimeSeconds`, `totalSleepSeconds`, `durationInSeconds`,
  `sleepDuration`) may provide a value; conflicting aliases fail closed and no
  authoritative value remains `null`.
- Sleep `review_required_count` and `excluded_record_count` are separate audit
  concepts. Excluded-only evidence does not create a review-required warning;
  `needs_review` and excluded rows remain ineligible for Activity context use.
- The v1.3 HRV reference does not average conflicting same-date
  values. Garmin/FIT raw sentinel
  `65535` is excluded, and Health Status HRV is not asserted to be equivalent to
  nightly FIT HRV. It is `analysis_reference_only`, not a Source of Truth and
  not intended for daily coaching, medical, or readiness decisions.
- Health Status unknown metrics remain in long-form evidence; duplicate metric
  types are not silently overwritten.
- Race Prediction is a Garmin algorithm prediction, not a measured result.
  Acute load and readiness components are source-provided and are not
  recalculated. VO2Max source-series differences are not automatically
  explained or collapsed.
- Race Prediction, Acute Training Load, Training Readiness, VO2Max, and Training
  History preserve each source observation. Their day-level QA view is a
  non-canonical aggregate; the package does not choose a latest or preferred row.
- Snapshot-based Endurance and UDS values that differ for one calendar key are
  preserved as public-safe observed variants in the corresponding audit output.
  Their canonical daily interpretation remains unresolved, so no winner is
  emitted. Same-export malformed/divergent values remain fail-closed.
- Snapshot-aware relationship resolution can use earlier authoritative
  observations when a later Export omits an endpoint. Valid unresolved links
  remain auditable; malformed links remain fail-closed.
- Runtime processing sequence is diagnostic only. It cannot alter acquisition
  chronology, normalized truth, relationship classification, or candidate
  selection.
- Naive source timestamps are retained with timezone semantics explicitly
  unconfirmed. Epoch-millisecond timestamps are normalized as UTC, and the
  Activity VO2Max `timestampGmt` field is treated as UTC by its source-field name.
- The v1.3 daily datasets are included in stable v1.3.0. Health
  Status remains deferred, is not supported in v1.3, and is not present in the
  stable registry or Run-All.
- Wellness/Metrics datasets are not Activity facts. Their direct Activity
  relationships remain `not_yet_defined`; documented same-day comparison is
  context only and must not create row identity or imply causality.

## Distribution and integrations

- Hosted processing, Garmin authentication, Open-Meteo, JMA, Instagram,
  wellness/coaching interpretation, Parquet output, and automatic personal
  analysis are outside the stable scope.
- Stable v1.3.2 retains `tzdata` as a Windows-only runtime dependency and emits
  the bounded `TIMEZONE_DATA_UNAVAILABLE` diagnostic if IANA timezone data is
  unavailable in an incomplete environment. Validation covers GitHub Actions
  `windows-latest` and one maintainer-owned physical Windows Production PyPI
  clean install. This does not establish universal Windows compatibility.
- External-safe output is opt-in, month-granularity, Activities-only, and does
  not automatically upload or provide provider-specific privacy guarantees.

The documented CLI and versioned Run-All output contract are stable for `1.x`.
Other Python modules are usable but are not all promoted to an independently
stable third-party API contract.

## Performance metrics and deferred promotion

- Hill Score Daily and Endurance Score Daily are stable v1.3 datasets.
- No Activity relationship is defined for either daily dataset. Date equality
  is not sufficient evidence for a join.
- Lactate Threshold is provided as candidate/audit infrastructure only. Stable
  public promotion is intentionally deferred until machine identity, units,
  timezone semantics, heart-rate authority, FTP/power authority, and public
  field/type rules are finalized. Fail-closed behavior is retained.
- Lactate source sequence may order records within its source family, but it is
  not identity and never authorizes latest-wins behavior.
- Power conflicts remain review evidence and are not averaged, converted, or
  silently resolved.
