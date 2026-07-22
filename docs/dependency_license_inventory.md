# Dependency and License Inventory

## Target project license

Status: `APACHE_2_0`. The project is published under the Apache License 2.0.

The repository-root [`LICENSE`](../LICENSE) file is the canonical license text.
Its SPDX identifier is `Apache-2.0`.

This project-license status is separate from dependency-license review. Adding
or changing a dependency still requires its own version, transitive-license,
attribution, and compatibility review as appropriate.

## Current dependencies

| Dependency | Use | Known license | Gate |
|---|---|---|---|
| Python >=3.11 | runtime platform | PSF License | Verify supported versions for a release |
| setuptools >=77 | build | MIT | PEP 639 license metadata; verified during release validation |
| wheel | build | MIT | Verify the resolved build environment for a release |
| pytest >=8.4,<9 | test-only | MIT | Verify the resolved test environment for a release |

The project declares no third-party runtime package dependency. Build and test
tools are not covered merely by the project's Apache-2.0 license and remain
independently licensed.

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
