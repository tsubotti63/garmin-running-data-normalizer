# GitHub Prerelease Execution Plan v0.2

## Target

- Repository: `tsubotti63/garmin-running-data-normalizer`
- Release: `v0.1.0-rc.2`
- Classification: GitHub prerelease
- Exact commit: `0996c4889ae807be0082ae83a26319a860f62c96`
- Release assets: none
- PyPI publication: none
- Application submission: not part of M6

## Authority and boundaries

M6 instruction v0.3 authorizes creation of the RC2 Git tag and GitHub
prerelease after the M5.5B Phase 3 `GO` decision. It does not authorize a stable
release, PyPI publication, Codex for Open Source submission, private-data
publication, force push, tag movement, or RC1 modification.

The three Phase 3 reports and M6 operational records are not part of the
validated RC2 product snapshot. They are recorded in a separate post-release
documentation commit so the tag remains fixed at the exact candidate reviewed
by M5.5B.

## Preconditions

- [x] Branch is `main`.
- [x] Local `HEAD` equals `origin/main`.
- [x] Exact candidate commit is `0996c4889ae807be0082ae83a26319a860f62c96`.
- [x] GitHub Actions run `29896162447` passed for that exact commit.
- [x] M5.5B Phase 3 verdict is `GO`.
- [x] RC1 remains an annotated historical tag.
- [x] RC2 Git tag and GitHub Release are absent.
- [x] Final Release body uses tag-pinned absolute repository links.
- [x] No Release asset is required.

## Execution sequence

1. Reconfirm candidate commit, remote equality, RC2 absence, CI success, and
   GitHub authentication.
2. Create annotated tag `v0.1.0-rc.2` at the exact candidate commit.
3. Push only that tag to `origin`; do not push or rewrite branch history.
4. Confirm the remote tag resolves to the exact candidate commit.
5. Create GitHub Release `v0.1.0-rc.2` from the existing tag, using
   `docs/project/release_notes_v0_3.md` as the body and marking it prerelease.
6. Confirm tag, target commit, prerelease flag, body links, Release assets, and
   public visibility.
7. Confirm the exact candidate CI remains successful and inspect open Issues
   for an immediate release blocker.
8. Create the post-release validation report, application-readiness roadmap,
   and evidence tracker.
9. Update current release-state documentation in a separate documentation-only
   commit, validate it, push it to `main`, and require CI PASS.

## Stop conditions

Stop without repair, deletion, or tag movement if any of the following occurs:

- the candidate commit, remote equality, CI verdict, or M5.5B verdict differs;
- an RC2 tag or Release unexpectedly exists;
- tag push or Release creation fails;
- the remote tag does not resolve to the exact validated commit;
- the Release is not marked prerelease or contains an unintended asset;
- a privacy, contract, license, or public-scope discrepancy is found.

## Rollback boundary

Do not automatically delete or move a pushed tag or published Release. If an
external publication defect is discovered after creation, preserve evidence,
stop further actions, and obtain Human direction for any corrective external
operation.

## Completion evidence

Record the following after execution:

- tag object and peeled commit;
- GitHub Release URL, ID, publication time, tag, and prerelease status;
- asset inventory;
- exact-candidate GitHub Actions result;
- public tag-pinned link checks;
- open-Issue inspection result;
- post-release documentation commit and CI result;
- remaining Human-only application action.

## Execution result

- Status: **PASS**
- Annotated tag object: `ff372c3adaaa453e78c67864af8c96a8c0bd5dba`
- Peeled release commit: `0996c4889ae807be0082ae83a26319a860f62c96`
- Release ID: `RE_kwDOTbsba84VU-IY`
- Published: `2026-07-22T06:41:18Z`
- URL: <https://github.com/tsubotti63/garmin-running-data-normalizer/releases/tag/v0.1.0-rc.2>
- Classification: prerelease; draft false
- Attached assets: none
- Exact-candidate CI: `bootstrap-ci / test` PASS, run `29896162447`
- Public tag-pinned links: six of six returned HTTP 200
- Open Issues at validation: zero

The post-release operational documents are intentionally separate from the
tagged product snapshot. Their documentation-only commit and CI result are
verified as the final M6 step.
