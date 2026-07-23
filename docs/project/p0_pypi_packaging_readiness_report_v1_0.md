# P0 PyPI Packaging Readiness Report v1.0

## Status

- Technical result: `PASS`
- P0 result: `P0_COMPLETE`
- Distribution name: `garmin-running-data-normalizer`
- Validated package version: `1.0.0`
- Runtime dependencies: none
- PyPI/TestPyPI upload: not performed
- Publication authority: not granted by P0

## Scope and boundary

P0 makes the stable `1.0.0` package technically suitable for a future PyPI
upload without changing product code, the stable CLI/Run-All contract, the
public/private boundary, the published `v1.0.0` tag, or the GitHub Release.

Uploading to TestPyPI or PyPI is an irreversible external operation. P0 does not
select the first index publication version or source commit, create an index
project, configure a publisher, handle a token, reserve a name, or upload an
artifact. Those actions require a separate Human decision and authorization.

## Implemented packaging gate

- PEP 621/639 metadata remains static and aligned at name/version/license,
  Python requirement, zero runtime dependencies, and the console entry point.
- `build` and `twine` are declared in a release-only optional dependency group;
  they are not installed with the default package.
- Project metadata exposes homepage, repository, issue, documentation, and
  changelog URLs.
- README links are absolute and tag-pinned so the PyPI long description does
  not depend on repository-relative link resolution.
- Build outputs and generated `*.egg-info` directories are ignored.
- CI builds wheel and source distribution, runs `twine check --strict`, installs
  each artifact into a separate virtual environment, runs `pip check`, imports
  the package, checks version `1.0.0`, and exercises the console entry point.
- Synthetic regression tests enforce package identity, release-tool bounds,
  PyPI-safe README links, and build-output ignore rules.

## Clean validation results

The uncommitted P0 candidate was overlaid on a clean archive of `main` and
validated in newly created virtual environments.

| Check | Result |
|---|---|
| Install `.[test,release]` | PASS |
| pytest | PASS, 67 of 67 |
| Wheel and sdist build | PASS |
| `twine check --strict` | PASS for both artifacts |
| Isolated wheel install and `pip check` | PASS |
| Isolated sdist install and `pip check` | PASS |
| Package import/version | PASS, `1.0.0` |
| Console entry point/version | PASS, `1.0.0` |
| Wheel license, metadata, and entry point | PASS |
| Tests absent from wheel | PASS |
| Bootstrap, Static Policy, Platform, Public History | PASS |

Validation-build SHA-256 values:

- wheel `garmin_running_data_normalizer-1.0.0-py3-none-any.whl`:
  `68575ef6dcefd4c711923f79dbbf8da032f87be3fa7275a9d3464eba2296cd4d`
- sdist `garmin_running_data_normalizer-1.0.0.tar.gz`:
  `36fc356d20da313dac4ff759e45fd9eeb6b0622fd302ff9e27bc5c50cb68aa9e`

These are local validation artifacts, not published artifacts. A future upload
must rebuild from its separately approved immutable source and record the hashes
of the exact uploaded files.

## Name and publication readiness

The normalized project name returned HTTP 404 from both the PyPI and TestPyPI
JSON project endpoints on 2026-07-23. This is a point-in-time availability check,
not a reservation or guarantee. PyPI project names are established by upload;
P0 does not claim ownership of the name.

Before initial publication, the Human owner must decide:

1. whether the first PyPI distribution uses the immutable `v1.0.0` source or a
   separately reviewed patch release;
2. whether to use PyPI Trusted Publishing or a manually handled API token;
3. whether a TestPyPI rehearsal is required; and
4. when the irreversible upload is authorized.

The preferred future path is a separately reviewed immutable release source,
PyPI Trusted Publishing configured outside the repository, exact artifact hash
capture, upload, and post-publication install verification. No credential or
token belongs in this repository.

## Official packaging references

- <https://packaging.python.org/en/latest/tutorials/packaging-projects/>
- <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>
- <https://packaging.python.org/en/latest/guides/tool-recommendations/>
- <https://twine.readthedocs.io/en/stable/>

## Decision

The repository meets the technical P0 exit criteria for packaging, README
rendering, artifact build, and isolated installation while preserving Stable
quality and the `1.x` public contract. Actual TestPyPI/PyPI publication remains
outside P0 and requires the decisions and authority listed above.
