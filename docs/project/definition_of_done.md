# Garmin Running Data Normalizer Definition of Done

## Technical complete

Required Platform-aligned structure exists; the bounded Garmin core is
importable; all created directories have a responsibility README or substantive
artifact; production imports remain Target-local or standard library. The
v2.0.0 GUI adds no Python dependency; it uses a web browser on the same
machine, and the CLI does not require a browser. The GUI is complete only when a
person who has not seen it before can select an Export and finish a
normalization without instructions. No such person could be found before the
stable release v2.0.0, so, as the Human maintainer decided on 2026-10-20, new
AI sessions that had never seen the GUI finished a normalization of the
synthetic Export without instructions in place of that check by hand. That
check is weaker than a check by a person; a person checks the GUI after
v2.0.0 if one can be found (see Testing in the
[v2.0.0 GUI Design](../gui_design.md#testing)).

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
