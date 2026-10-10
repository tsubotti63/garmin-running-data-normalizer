# Garmin Running Data Normalizer Definition of Done

## Technical complete

Required Platform-aligned structure exists; the bounded Garmin core is
importable; all created directories have a responsibility README or substantive
artifact; production imports remain Target-local or standard library. The
planned v2.0.0 GUI adds no Python dependency; it uses a web browser on the same
machine, and the CLI does not require a browser.

## Operational complete

Bootstrap validation, static policy scan, and all synthetic unit tests pass.
Rollback remains available and no external resource is created.

## Review complete

A Git-ignored Review Pack contains request, mapping, inventory, manifest/hash,
QA, scans, negative paths, Unit Review, and caveats. Target Project Core Review
returns `PASS`.

## Handoff complete

The Target Project Core Review task receives the frozen Review Pack directly
from the Target Implementation task.

## Formal close

This Work Package closes only after Target Project Core Review `PASS`. Commit
remains prohibited until that verdict and Target rules permit it. Publication
or release always requires later Human direction.
