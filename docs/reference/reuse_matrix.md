# Responsibility-level Reuse Matrix — Phase 0.1

Local reuse is Human-authorized. The Human owner confirmed that the
predecessor-derived responsibilities currently included in this Target may
continue to be distributed under Apache-2.0 and included in `v1.0.0`. Future
material requires its own review. Exact predecessor paths and file names are
omitted from public provenance.

| Predecessor responsibility | Target area | Status | Public adaptation |
|---|---|---|---|
| Time and date normalization | `common/time.py` | modified | explicit timezone behavior |
| Stable Garmin identity | `common/identity.py` | modified | Garmin-only fallback semantics |
| Record validation | `common/validation.py` | modified | generic fail-closed validation |
| Garmin archive safety | `intake/archive.py` | modified | traversal, count, size, total, and ratio limits |
| Export discovery | `intake/discovery.py` | new/derived | deterministic relative-path manifest |
| Activity normalization | `normalizers/activities.py` | modified | stdlib records and safe provenance |
| Gear normalization and links | `normalizers/gear.py` | modified | separate records and stable keys |
| Personal-record normalization | `normalizers/personal_records.py` | modified | bounded discovery without host paths |
| FIT session/lap parsing | `fit/parser.py` | modified | bounded input and no record coordinates |
| Dataset policy | `policies/datasets.py` | modified | phase-independent registry contract |
| Deterministic QA | `qa.py` | new/derived | order-independent record checks |
| Portable Analysis Pack | `export/analysis_pack.py` | reimplemented | caller allowlist and no environment lists |
| Predecessor tests | `tests/` | recreated | synthetic stdlib tests only |
| Optional weather adapter | none | excluded/deferred | privacy, attribution, and use-tier unresolved |
| JMA, Instagram, wellness, coaching, and personal analysis | none | excluded | outside product boundary |
| Raw/generated data, private workflow evidence, and Git history | none | excluded | prohibited |
