# Release Post-Validation Report v0.1

## Release identity

- Release: `v0.1.0-rc.2`
- Release URL: <https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v0.1.0-rc.2>
- Release ID: `RE_kwDOTbsba84VU-IY`
- Published: `2026-07-22T06:41:18Z`
- Classification: prerelease
- Draft: false
- Attached assets: none
- Annotated tag object: `ff372c3adaaa453e78c67864af8c96a8c0bd5dba`
- Peeled commit: `0996c4889ae807be0082ae83a26319a860f62c96`

## Verdict

**PASS.** The GitHub prerelease is public, resolves to the exact M5.5B-validated
candidate, retains the prerelease boundary, exposes no attached artifact, and
passes post-publication reproduction and link checks.

## Public validation

| Check | Result | Evidence |
|---|---|---|
| Tag clone | PASS | Detached `HEAD` equals exact reviewed commit |
| Unit tests | PASS | 39/39 with documented `PYTHONPATH=src` invocation |
| Bootstrap | PASS | Lifecycle `post-public`, Apache-2.0, overall PASS |
| Static Policy | PASS | No violations |
| Platform Alignment | PASS | 62 Standard files, no mismatches |
| Golden Path | PASS | Golden Result byte comparison succeeded |
| Run-All | PASS | `PASS_WITH_WARNINGS`, exit 0, documented fixed layout |
| GitHub Actions | PASS | `bootstrap-ci / test`, run `29896162447` |
| Release metadata | PASS | prerelease true, draft false, correct tag |
| Release assets | PASS | zero attached assets |
| Public links | PASS | Release plus five tag-pinned document/license links returned HTTP 200 |
| Open Issues | PASS | zero open Issues at post-release inspection |

The first tag-clone unittest invocation omitted both installation and the
documented `PYTHONPATH=src` setting, so it produced import errors. The same
unchanged public clone was immediately rerun with the documented environment;
all 39 tests and subsequent checks passed. This was a validation-invocation
error, not a product or release defect.

## Privacy and scope

- Public reproduction used only the tracked synthetic fixture.
- No real export or generated personal output was attached to the Release.
- The final Release body uses tag-pinned links and repeats the stable-key and
  date-granularity sharing cautions.
- The Release does not claim a stable API, stable release, PyPI publication,
  medical/coaching output, complete FIT support, or hosted processing.
- RC1 remains unchanged and points to its historical activities-only commit.

## Post-release issue assessment

No immediate public Issue was present after publication. Future Issues are
operational evidence and must be triaged without publishing user data or
silently expanding the product contract.

## Remaining risk

The known bounded FIT, stable API, external-sharing derivative, stable-release,
and PyPI limitations remain unchanged. Editable-install `*.egg-info/` ignore
hygiene and post-public Bootstrap status vocabulary remain non-blocking future
improvements.

## Conclusion

M6 release execution and public validation are complete. No release blocker or
rollback condition was detected.
