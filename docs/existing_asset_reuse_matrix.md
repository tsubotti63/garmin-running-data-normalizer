# Existing Asset Reuse Matrix

The exact names and paths of the private predecessor are intentionally omitted.
This public matrix records only responsibility-level provenance and safety
decisions. Local reuse authorization does not establish public redistribution
rights or select an OSS license.

| Predecessor responsibility | Classification | Main risk | Required public adaptation | Target responsibility | Decision |
|---|---|---|---|---|---|
| Common identity, time, and validation helpers | Reusable after modification | Hidden project assumptions | Target namespace and explicit contracts | `common/` | Adapted locally |
| Garmin archive discovery and filtering | Review required | Traversal and resource exhaustion | Fail-closed path and size limits | `intake/` | Reimplemented/adapted locally |
| Activity normalization | Reusable after modification | Private export layouts and identifiers | Public records, provenance, synthetic tests | `normalizers/activities.py` | Adapted locally |
| Gear and activity links | Reusable after modification | Internal batch coupling | Separate records and stable keys | `normalizers/gear.py` | Adapted locally |
| Personal-record normalization | Reusable after modification | Private paths and schema assumptions | Bounded discovery and synthetic tests | `normalizers/personal_records.py` | Adapted locally |
| FIT parsing | Review required | Parser correctness and coordinates | Bounded session/lap parser without record coordinates | `fit/parser.py` | Adapted locally |
| Dataset policy | Reusable after modification | Private workflow statuses | Phase-independent registry and merge policy | `policies/datasets.py` | Adapted locally |
| QA and portable export concepts | Reusable after modification | Private artifact lists and environment leakage | Deterministic checks and caller allowlist | `qa.py`, `export/analysis_pack.py` | Reimplemented locally |
| Optional weather adapter | Deferred | Coordinates, attribution, and service tier | Separate privacy and terms review | none | Excluded for now |
| JMA, Instagram, wellness, coaching, and personal analysis | Private/out of scope | Personal or non-Garmin behavior | None | none | Excluded |
| Raw/generated data, runtime evidence, and predecessor Git history | Prohibited | Privacy and operational leakage | None | none | Excluded |

Exact predecessor evidence remains outside the public repository. The public
contract is defined by Target code, synthetic tests, and Target documentation.
