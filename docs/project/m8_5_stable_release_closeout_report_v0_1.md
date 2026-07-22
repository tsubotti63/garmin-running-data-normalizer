# M8.5 Stable Release Closeout Report v0.1

## Release identity

- Release: `v1.0.0`
- Release URL: <https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v1.0.0>
- Release ID: `358081555`
- Release node ID: `RE_kwDOTbsba84VV-QT`
- Published: `2026-07-22T14:18:23Z`
- Classification: stable and latest
- Draft: false
- Prerelease: false
- Annotated tag object: `a1d13fa1320c5c95e97238d585f36a78f78a2395`
- Peeled release commit: `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1`

## Verdict

**PASS.** M8.4 published the Human-approved candidate as the first stable
release. M8.5 confirmed that the public Release, fixed annotated tag, approved
notes, latest designation, source-only artifact policy, links, privacy boundary,
default branch, and final candidate CI are healthy.

## Post-release verification

| Check | Result | Evidence |
|---|---|---|
| Remote tag | PASS | `v1.0.0^{}` resolves to approved commit `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1` |
| Release state | PASS | Public, draft false, prerelease false, returned by the GitHub latest-release endpoint |
| Release notes | PASS | Published body exactly matches `docs/release_notes/v1.0.0.md` |
| Release assets | PASS | Zero attached assets; GitHub-generated source archives only |
| Public links | PASS | Release, tag-pinned Known Limitations, and Supported Datasets links returned HTTP 200 |
| Repository | PASS | Public, active, and default branch `main` |
| Candidate CI | PASS | `bootstrap-ci / test`, run `29927192799`, commit `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1` |
| Local branch | PASS | Release checkpoint had `HEAD == origin/main` and a clean worktree |
| Privacy boundary | PASS | No real export, personal output, secret, private path, or unintended binary asset was published |

## Artifact policy

The repository policy does not require wheel or source-distribution attachment
to the GitHub Release. No locally built artifact was uploaded, so no published
binary artifact hash applies. GitHub provides source archives derived from the
fixed reviewed tag. No PyPI or other package-index publication occurred.

## Remaining non-blocking gaps

- complete FIT CRC validation;
- multi-session FIT identity;
- hosted processing;
- Open-Meteo integration;
- Parquet output;
- PyPI publication;
- Run-All integration for Sleep, HRV, and Health Status; and
- the GitHub Actions Node.js 20 deprecation annotation. The final workflow
  passed while GitHub forced `actions/checkout@v4` and `actions/setup-python@v5`
  onto Node.js 24.

## v1.1 backlog entry points

- `docs/known_limitations.md` is the current product-boundary inventory.
- `docs/project/roadmap.md` records Post-Stable / v1.1 themes.
- FIT integrity and identity should be handled before broader FIT expansion.
- Library-only dataset integration must preserve the versioned Run-All output
  contract and remain separately reviewed.
- Hosted, weather, Parquet, and package-index capabilities require their own
  privacy, dependency, operations, and Human authorization gates.

## Lessons learned from M7 and M8

- M7 kept Sleep, HRV, and Health Status migrations useful without overstating
  Run-All or stable third-party API support. Explicit provenance, review states,
  synthetic fixtures, and no-inference rules were effective migration gates.
- M8 clean-state editable installation exposed generated `.egg-info` metadata
  to the static policy scan. A narrow exclusion plus a regression test restored
  CI without weakening product-source checks.
- Release lifecycle facts must be updated after each irreversible boundary;
  candidate readiness, Tag creation, GitHub Release publication, latest status,
  and closeout are distinct evidence states.
- Tag-pinned links and a fixed annotated tag keep Release documentation tied to
  the exact reviewed source even when post-release closeout documentation is
  committed later on `main`.

## Closeout decision

M8.1 through M8.5 are complete. The `v1.0.0` tag must remain fixed on the
approved release commit and must not be moved to include this post-release
documentation. No rollback condition, release blocker, or urgent correction
was found. Future work begins from the Post-Stable / v1.1 entry points and does
not inherit standing release or publication authority.
