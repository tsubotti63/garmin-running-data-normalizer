# Dependency and License Inventory

## Target project license

Status: `HUMAN_DECISION_PENDING`. No license file is present.

Candidates:

| Candidate | Strength | Trade-off | Status |
|---|---|---|---|
| Apache-2.0 | Explicit patent grant and contribution clarity | Longer notice obligations | Recommended for Human consideration |
| MIT | Short and permissive | No explicit patent grant | Alternative |

The recommendation is not a license decision. The Human owner must confirm code
ownership and select the license before public release or Source code reuse.

## Bootstrap dependencies

| Dependency | Use | Known license | Gate |
|---|---|---|---|
| Python >=3.11 | runtime | PSF License | Verify supported versions before release |
| setuptools | build | MIT | Pin/verify at release |
| wheel | build | MIT | Pin/verify at release |
| pytest | test-only | MIT | Pin/verify at release |

The bootstrap has no third-party runtime dependency.

## Candidate future dependencies

`pandas` (BSD-3-Clause), `pyarrow` (Apache-2.0), and `PyYAML` (MIT) are used by
the Source Project but are not yet Target runtime dependencies. Versions,
transitive dependencies, notices, and compatibility must be verified before
adoption.

## Open-Meteo

Open-Meteo API data are offered under CC BY 4.0 and require attribution and an
indication of modifications. The free API is described as non-commercial and
rate-limited; commercial use requires an appropriate subscription/use tier.
The server code is separately AGPLv3. Target plans to call the API, not copy the
server. Production use tier and attribution wording remain release gates.

Official references (checked 2026-07-17):

- https://open-meteo.com/en/terms
- https://open-meteo.com/en/license
- https://open-meteo.com/en/pricing

