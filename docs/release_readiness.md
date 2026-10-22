# Release Readiness

## v2.0.0rc4 release candidate

Version `2.0.0rc4`, the fourth release candidate of v2.0.0, is published on
TestPyPI only, for the checks of stage E before the stable release. It is
v2.0.0rc3 with the picture of the icon and of the tab of the browser (#146)
and the guides that answer what a first reader asked (#147). Production PyPI
and the latest GitHub Release stay v1.7.1, and no GitHub Release was made for
the release candidate.

From v2.0.0rc3, the package's Python changes in the version in `__init__.py`
and in the picture of the icon; the page gains its two favicons and one
sentence (`next.restart_gui`), and the package its pictures:

```text
$ git diff --stat v2.0.0rc3 v2.0.0rc4 -- 'src/**/*.py'
 src/garmin_running_data_normalizer/__init__.py   |  2 +-
 src/garmin_running_data_normalizer/gui/server.py |  4 +
 src/garmin_running_data_normalizer/runner.py     |  9 ++-
 src/garmin_running_data_normalizer/shortcut.py   | 94 +++++++++++++++++++++---
 4 files changed, 95 insertions(+), 14 deletions(-)
```

The Windows CI ran every Windows step with v2.0.0rc4, among them a step that
makes the shortcuts of the icon in temporary folders and reads back their
picture, and a step that runs the line of the guides with a stand-in for
each part. A physical Windows machine checks v2.0.0rc4 after this
publication, as the Human maintainer decided on 2026-10-22: the check of
v2.0.0rc3 on a physical Windows machine was moved to this release candidate.

The release source is `687ebf3595d9dd08815ba89c756217d7a3d5e2aa` (#148). The annotated `v2.0.0rc4` tag
(tag object `b23d4f303e64ca138349ff3fa9c9a7155a38a349`) points to it, so that the links of the GUI's help
panel open the documents of that tag. TestPyPI publication through Trusted
Publishing/OIDC on 2026-10-22 JST and the publish workflow's exact-version
TestPyPI install verification are complete.

The release source passed main CI run `39719956285` (Ubuntu `test` and
`windows-runtime`) and CodeQL (`39719956073`). A build-only publish workflow
run (`39720723992`) on the release source passed with every upload job
skipped. Publish workflow run `39722121909` then built and validated the
exact source and published to TestPyPI; the PyPI jobs were skipped. The
Sigstore transparency log (Rekor) was read before the run and answered. The
publication and the tag ran under one Human approval given after their values
were shown. The `testpypi` Environment deployment was Human-authorized, and
the approval was submitted through the GitHub API on the Human's
instruction. `TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish
run and returned to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`97c8f1c0c7c0cba971f68cdc7895ca720928fd8e944161c854c30bf91217ef8b` and source distribution `5e06d48c37e4d99c5b79eaa8894d777c12196cbf0364d0f22abc0adfe707c7de`. Each file carries a
PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.0.0rc4` tag describe the installation from TestPyPI in the words used
before the publication.

## v2.0.0rc3 release candidate

Version `2.0.0rc3`, the third release candidate of v2.0.0, is published on
TestPyPI only, for the checks of stage E before the stable release. It is
v2.0.0rc2 with the documents of stages E1a to E1c, the icon that starts the
GUI of stage E1d (#143), and the line of the GUI guides that installs it and
makes the icon (#144). Production PyPI and the latest GitHub Release stay
v1.7.1, and no GitHub Release was made for the release candidate.

From v2.0.0rc2, the package's Python changes in the version in `__init__.py`
and in the icon of stage E1d; the page does not change:

```text
$ git diff --stat v2.0.0rc2 v2.0.0rc3 -- 'src/**/*.py'
 src/garmin_running_data_normalizer/__init__.py |   2 +-
 src/garmin_running_data_normalizer/runner.py   |  19 ++
 src/garmin_running_data_normalizer/shortcut.py | 246 +++++++++++++++++++++++++
 src/garmin_running_data_normalizer/stops.py    |  18 ++
 4 files changed, 284 insertions(+), 1 deletion(-)
```

The Windows CI ran every Windows step with v2.0.0rc3, among them a step that
makes the shortcuts of the icon in temporary folders and reads them back. A
physical Windows machine checks v2.0.0rc3, with the line of the guide and the
icon, after this publication, as the Human maintainer decided on 2026-10-21.
On 2026-10-22, the Human maintainer moved that check to v2.0.0rc4, with the
picture of the icon and the fixed guides.

The release source is `8d110487815ff8ebe9a8fb38c486a46e390416be` (#144). The
annotated `v2.0.0rc3` tag (tag object
`8c8ca2aab912e99d1539500d211889a1cefb62f5`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-10-21 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `39590294371` (Ubuntu `test` and
`windows-runtime`) and CodeQL (`39590293318`). A build-only publish workflow
run (`39603091848`) on the release source passed with every upload job
skipped. Publish workflow run `39608977862` then built and validated the
exact source and published to TestPyPI; the PyPI jobs were skipped. The
Sigstore transparency log (Rekor) was read before the run and answered. The
publication and the tag ran under one Human approval given after their values
were shown. The `testpypi` Environment deployment was Human-authorized, and
the approval was submitted through the GitHub API on the Human's
instruction. `TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish
run and returned to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`cbc51620f06ce8806bd2904f47823654d5d0b106a1db5f05dec9e6e3b0364498` and source
distribution `0d20059517c23a5593807b9168fb1d358c56cd73e6f2b61c5c955b81ab46629a`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.0.0rc3` tag describe the installation from TestPyPI in the words used
before the publication.

## v2.0.0rc2 release candidate

Version `2.0.0rc2`, the second release candidate of v2.0.0, is published on
TestPyPI only, for the checks of stage D before the stable release. It is
v2.0.0rc1 with the clearer screen texts of stage D6 (#136): two new AI
sessions that had never seen the GUI used v2.0.0rc1 with no instructions, in
place of a first-time user, and the texts that made them hesitate changed.
Production PyPI and the latest GitHub Release stay v1.7.1, and no GitHub
Release was made for the release candidate.

From v2.0.0rc1, the only line of the package's Python that changes is the
version in `__init__.py`:

```text
$ git diff --stat v2.0.0rc1 v2.0.0rc2 -- 'src/**/*.py'
 src/garmin_running_data_normalizer/__init__.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

So the physical Windows check of v2.0.0rc1 below was not repeated for
v2.0.0rc2, as the Human maintainer decided on 2026-10-20; the Windows CI ran
every Windows step with v2.0.0rc2.

The release source is `b210e5285e003aa0912980a478ceca4cf192b074` (#137). The
annotated `v2.0.0rc2` tag (tag object
`75a0d23193e4b989200fad1e7be2beeb1736645c`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-10-20 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `39408498560` (Ubuntu `test` and
`windows-runtime`) and CodeQL (`39408498438`). A build-only publish workflow
run (`39410892656`) on the release source passed with every upload job
skipped. Publish workflow run `39411324672` then built and validated the
exact source and published to TestPyPI; the PyPI jobs were skipped. The
Sigstore transparency log (Rekor) was read before the run and answered. The
publication and the tag ran under one Human approval given after their values
were shown. The `testpypi` Environment deployment was Human-authorized, and
the approval was submitted through the GitHub API on the Human's
instruction. `TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish
run and returned to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`4cc90dc5bffbb6e18f07acc31121324916d80667e67cee466b160fa33f2edc70` and source
distribution `b4584c434707b40d0124d2fc3e7642b28536e6b5d8aeb702fdf248fb86273b28`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.0.0rc2` tag describe the installation from TestPyPI in the words used
before the publication.

On 2026-10-20, v2.0.0rc2 installed from TestPyPI was checked on macOS: the
downloaded wheel was the file on TestPyPI, and the installed files of the
package were those of the `v2.0.0rc2` tag, byte for byte. With the tracked
synthetic fixture and with one real Export of the maintainer, compared by
counts and identity only, the page's three ways of normalizing gave the same
files as the CLI, file by file, and the same counts. An output of v2.0.0rc1
was refused with `OUTPUT_OTHER_VERSION`, naming 2.0.0rc1, and the page
showed no change since such an output. No personal Garmin data, and no count
from it, is recorded here.

In place of a first-time user, new AI sessions that had never seen the GUI
normalized the synthetic Export in a work home of their own, with one
sentence of request and no instructions, and then showed the output folder
and quit the app: two with v2.0.0rc1, whose findings stage D6 made clearer in
the texts of v2.0.0rc2, and one with v2.0.0rc2 installed from TestPyPI, which
read the clearer texts without hesitating there. They chose files from the
page's own list, as on a computer without the system's dialog. An AI session
does not hesitate as a person does, so this check is weaker than a check by a
person; a person checks the GUI after the stable release if one can be found.
The five things that the third session found new are left for after the
stable release.

## v2.0.0rc1 release candidate

Version `2.0.0rc1`, the release candidate of v2.0.0, is published on TestPyPI
only, for the checks of stage D before the stable release. It adds the local
GUI and the data handling of v2.0.0, as the
[draft of the v2.0.0 migration notes](v2_migration_notes_draft.md) lists.
Production PyPI and the latest GitHub Release stay v1.7.1, and no GitHub
Release was made for the release candidate.

The release source is `f9d12fc8b49915add1a43efa34417e36569dcd9e` (#133). The
annotated `v2.0.0rc1` tag (tag object
`1ddf9c6f5e5f7677ed5cc7d8ee2437b321638e06`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-10-20 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `39366348529` (Ubuntu `test` and
`windows-runtime`) and CodeQL. A build-only publish workflow run
(`39366955879`) on the release source passed with every upload job skipped.
Publish workflow run `39368797742` then built and validated the exact source
and published to TestPyPI; the PyPI jobs were skipped. In its first attempt,
creating the PEP 740 attestations failed before any upload, because the
Sigstore transparency log (Rekor) answered HTTP 502. On the Human's
instruction, the failed job was re-run in the same run (attempt 2): the build
and the approval gate did not run again, as their jobs kept the start times of
the first attempt, and the re-run published the artifact of the first
attempt's build and verified the exact-version TestPyPI install. The
publication and the tag ran under one Human approval given after their values
were shown, and the re-run under another. The `testpypi` Environment
deployment was Human-authorized for each attempt, and the approvals were
submitted through the GitHub API on the Human's instruction.
`TESTPYPI_PUBLISH_APPROVED` was returned to `false` during the first attempt,
once its approval gate had passed, and was not set again for the re-run.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`f64485cf4a861a7dc9da64cff74633f21cdbb063caaf51f76a7765e49722aa4b` and source
distribution `b36a93179d46df93159abd51321646cbafc44c21ff232ad2ea841fbcdc6f4df8`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.0.0rc1` tag describe the installation from TestPyPI in the words used
before the publication.

On 2026-10-20, the release candidate was checked by hand on one physical
Windows 11 x64 machine (build 26200) with Python 3.14.5 (64-bit); CI runs
Python 3.11. A clean installation
from TestPyPI, with Production PyPI as the extra index, installed
`tzdata 2026.5` from Production PyPI; `Asia/Tokyo` resolved and `--version`
reported `2.0.0rc1`. With the tracked synthetic fixture of the `v2.0.0rc1`
tag, the `gui` command printed its three lines and opened Edge; the dialogs
of Windows chose the ZIP file and the extracted folder; the page normalized
in its three ways and showed the change since the output before the run;
the keyboard alone reached the start of a run; File Explorer opened the
outputs and the saved files, also in a folder whose name has spaces and
Japanese; Windows without long paths stopped with
`SNAPSHOT_STORE_PATH_TOO_LONG` and `OUTPUT_PATH_TOO_LONG`; the Quit button
ended the command with `GUI stopped.` and left no process of the app; Chrome
showed the page and normalized; the Support Bundle, the remembered settings,
and forgetting them worked. Two of the later runs finished, but their
headings were not noted. No Git command, no local installation, and no
personal Garmin data were used. This evidence is bounded: it does not
establish compatibility with every Windows version or environment, and
Windows on Arm64 was not checked by hand. The planned Windows 11 on Arm64
virtual machine was left out, as the Human maintainer decided.

## v1.7.1 stable release

Version `1.7.1` is published as the Snapshot metrics fix release. It makes
`snapshot run-all` normalize the Hill Score, Endurance Score, and VO2Max rows
that `snapshot build-input` merges, which v1.3.0 through v1.7.0 left out of
its output, while keeping one-shot `run-all` output, the 17 datasets, 224
fields, stable keys, output paths, the Snapshot lifecycle contract and policy
registry `v1.0`, and the `0 / 0 / 3 / 2` Product exit contract unchanged. It
also contains internal changes toward v2.0.0 that add no user-facing
feature, including an internal GUI package that has no command.

The release source is `94f91fd4ac026eb8583f116df839849989f7320b` (#74).
The annotated `v1.7.1` tag (tag object
`e4d026de8ac67c992c3059cd1faa3a18f58f9da9`), the latest stable GitHub Release
published on 2026-10-11 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.7.0 stable release

Version `1.7.0` is published as the FIT running dynamics release. It adds six
FIT running-dynamics averages (vertical oscillation, stance time, stance time
percent, stance time balance, vertical ratio, and step length) to
`fit_sessions` and `fit_laps`, read from the FIT session and lap messages in
the units defined by the FIT profile, and appends elapsed and moving time and
the linked FIT session's values to `analysis/activities.csv`, while keeping
the 17 datasets, stable keys, output paths, the Snapshot lifecycle contract
and policy registry `v1.0`, and the `0 / 0 / 3 / 2` Product exit contract
unchanged; the field inventory grows from 212 to 224.

The release source is `221fb297e1615168165ad4434b1b3963b27ec62b` (#60).
The annotated `v1.7.0` tag (tag object
`56107ef1db1fd00226eb7ce891e75df8000ffdcd`), the then-latest stable GitHub
Release published on 2026-10-10 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.6.0 stable release

Version `1.6.0` is published as the local timezone release. It adds
`--timezone` to `run-all`, `snapshot run-all`, `normalize-activities`, and
`doctor --input`, records the timezone used as `local_timezone`, and stops with
`TIMEZONE_INVALID` for a name that is not an exact IANA timezone name, while
keeping the default `Asia/Tokyo`, the 17-dataset/212-field inventory, stable
keys, the Snapshot lifecycle contract and policy registry `v1.0`, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `877f42289f99acd7eb1fc2adea0379c040cb772e` (#56).
The annotated `v1.6.0` tag (tag object
`1bfb75e1b7e3ae94e8742ae8c33ad10e76c2b0df`), the then-latest stable GitHub
Release published on 2026-10-09 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.5.0 stable release

Version `1.5.0` is published as the Snapshot and output hardening release. It
creates new Snapshot Stores and `normalize-activities` output owner-only,
reports Snapshot stop conflicts by dataset and type with lock recovery
guidance, skips `Thumbs.db` inside ZIP files, and keeps every Sleep field that
Run-All reads in Snapshot input, while keeping the 17-dataset/212-field
inventory, stable keys, the Snapshot lifecycle contract and policy registry
`v1.0`, and the `0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `e5970fa398fbd9711b395fbe4cc212df0bcbb98e` (#53).
The annotated `v1.5.0` tag (tag object
`55ebfd97ce46654f2732bc2ebb746f78fc6ed61b`), the then-latest stable GitHub
Release published on 2026-10-07 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.4.1 stable patch release

Version `1.4.1` is published as the FIT correctness and metadata-file patch
release. It corrects FIT session sport names to the FIT profile, checks FIT
containers before reading FIT-derived HRV, and ignores operating-system
metadata files in Export folders and completed outputs, while keeping the
17-dataset/212-field inventory, stable keys, Snapshot semantics, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `9e3bd6d3d7faa64f6961547756559703158ae0b2` (#49).
The annotated `v1.4.1` tag (tag object
`402ec6cbff2af618f2f10233ce5f5cc704da21c6`), the then-latest stable GitHub
Release published on 2026-10-07 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v1.4.0 stable release

Version `1.4.0` is published as the Export Evidence and Diagnostics release. It
adds the Export Evidence Doctor, the read-only
`diagnostics/source_completeness.json` and `diagnostics/run_quality.json`
projections, and the Human-reviewed public-safe Support Bundle while keeping
the 17-dataset/212-field inventory, stable keys, Snapshot semantics, and the
`0 / 0 / 3 / 2` Product exit contract unchanged.

The release source is `ae9cb28a60c450897284fd1023b1e4e7c02d127e`.
The annotated `v1.4.0` tag, then-latest stable GitHub Release, Production PyPI
publication through Trusted Publishing/OIDC, and the publish workflow's
exact-version PyPI install verification are complete.

## v1.3.3 stable patch release

Version `1.3.3` is published as the Sleep contract restoration patch. It keeps
the 17-dataset/212-field inventory, stable keys, schemas, relationships, and
the compatible `1.x` output contract unchanged while restoring observed-stage
duration semantics and separating review-required from excluded evidence.

The release source is `cf7e44c18d77adda4c908207361e6f6f5f2b682c`.
The annotated `v1.3.3` tag, then-latest stable GitHub Release, Production PyPI
publication through Trusted Publishing/OIDC, exact-version clean install,
Synthetic Run-All, and Sleep contract smoke are complete.

## v1.3.2 stable patch release

Version `1.3.2` is published as a Snapshot correctness and
evidence-preservation patch. Snapshot-aware relationship resolution, exact
Sleep duplicate handling, Endurance/UDS observed-variant preservation, Lactate
candidate preservation, and acquisition/processing-order separation retain
observed evidence without selecting an unsupported winner.

The release source is `c6f7737aa24d099b30e897cef0840f0189fb1d7b`.
The annotated `v1.3.2` tag, then-latest stable GitHub Release, Production PyPI
publication, and exact-version clean-install smoke test are complete.

## v1.3.1 stable patch release

Version `1.3.1` is published as a documentation, GitHub public-surface,
Product-owned entry-point, Public Product State Validator, and Platform
Alignment patch. It changes no Product API, runtime behavior, dataset, schema,
stable key, output path, Snapshot policy, relationship contract, or privacy
boundary.

PR #15 was squash-merged as
`9fac26ee8f81f1db1273cac5984415e103e756b3`. The annotated `v1.3.1` tag,
stable GitHub Release, Production PyPI publication, and clean-install smoke
test are complete.

## v1.3.0 stable release

PR #10 was merged as `d2aca48b9a5b0bee732fa3f004c25289972e7e15`.
Version `1.3.0` is published as an annotated tag, a stable GitHub Release, and a
verified Production PyPI distribution. The release includes 17 normalized
datasets, reviewed Snapshot policies, expanded Output Experience, and
lifecycle-aware relationship guidance. The remaining Lactate Threshold gates
apply only to a future stable promotion and do not reopen v1.3 scope.

## Current repository state

- Public repository operation: Active
- Default branch: `main`
- License: `Apache-2.0`
- GitHub Actions: Operational
- Current source and package version: `2.0.0rc5`
- Current Production PyPI version: `1.7.1`
- Latest GitHub Release: `v1.7.1`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `1.7.1`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `1.7.1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc4`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc3`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc2`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc1`: Published and exact-version install verified by the
  publish workflow
- Release candidate tags: `v2.0.0rc4`, `v2.0.0rc3`, `v2.0.0rc2`, and
  `v2.0.0rc1`, without a GitHub Release
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v1.7.1 is the current stable release;
v2.0.0rc4, v2.0.0rc3, v2.0.0rc2, and v2.0.0rc1 are release candidates on
TestPyPI only; v1.7.0, v1.6.0, v1.5.0, v1.4.1, v1.4.0, and v1.3.3 are
historical releases. The v2.0.0rc4, v2.0.0rc3, v2.0.0rc2, and v2.0.0rc1 tag and
TestPyPI publication evidence was recorded only after the corresponding
external state was observed.
The v1.7.1, v1.7.0, v1.6.0, v1.5.0, v1.4.1, v1.4.0, and v1.3.3 tag, GitHub
Release, and Production PyPI publication evidence was recorded only after the
corresponding external state was observed.

## Windows CI correction

The main CI runs cited below for v1.4.0, v1.4.1, v1.5.0, v1.6.0, and v1.7.0
reported the `windows-runtime` job as passed, but one test in that job failed
in each of them. The "Verify Windows Core 4 diagnostics and tracked vector"
step, added in commit `f4d07ed` (first run on 2026-08-20 UTC), ran
`tests/test_v14_diagnostics.py` and other commands in one PowerShell script,
and such a step fails only when its last command fails. The failing test,
`test_reversed_creation_and_mapping_order_is_deterministic`, rewrote copied
JSON files with Windows line endings, so the Product correctly rejected the
changed Run-All manifest; the failure came from the test, not the Product.
Pull Request #65 made every command in the multi-line Windows steps stop the
job on failure, with a test that keeps it so; its first commit stopped the
Windows job at that test (run `38055811063`). It then corrected the test,
which passed on Windows (run `38056053424`: 57 passed). In the cited runs, the
other Windows steps show no failed command in their logs. Tags, GitHub
Releases, Production PyPI files, and release notes are unchanged.

## Current release assessment

The v1.7.1 release source passed main CI run `38125071544` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `38125071252`. A build-only publish workflow
run (`38125143577`) on the release source passed with every upload job
skipped. Production publish workflow run `38125322756` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The tag, the
GitHub Release, and the Production publication ran under one Human approval
given after their values were shown. The `pypi` Environment deployment was
Human-authorized, and the approval was submitted through the GitHub API on
the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`dc5733e3b9089b416687d70e8993cd3a2750b480910ca463411d970ce51c7f95` and source
distribution `62573b038c27373e1629645bef5afaf3098b3b2cc8ff9939fdf28df078a96962`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`, and its `--help` lists no `gui`
command. With a synthetic two-Snapshot store built with the test helpers,
its `snapshot run-all` wrote Hill Score, Endurance Score, and VO2Max rows.

### v1.7.0 release assessment (historical)

The v1.7.0 release source passed main CI run `38035096711` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `38035096430`. A build-only publish workflow
run (`38035574609`) on the release source passed with every upload job
skipped. Production publish workflow run `38035713879` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The publication
sequence ran under one Human approval given after its values were shown. The
`pypi` Environment deployment was Human-authorized, and the approval was
submitted through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`a40664c077409ddaa3301d7985323151d1b25226d05f049ce6a8fb132f4fe765` and source
distribution `845f6670ae692714404faf9e7d85ec3b877f62efc37a8d4398400e1535cc70fe`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`, and wrote the ten new
`analysis/activities.csv` columns. With a synthetic FIT file from the test
fixture factory, it reported the six running-dynamics fields in `fit_sessions`
and `fit_laps` and repeated the linked session's values in the `fit_*`
columns.

### v1.6.0 release assessment (historical)

The v1.6.0 release source passed main CI run `37905835932` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `37905835352`. A build-only publish workflow
run (`37912699868`) on the release source passed with every upload job
skipped. Production publish workflow run `37912868187` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The publication
sequence ran under one Human approval given after its values were shown. The
`pypi` Environment deployment was Human-authorized, and the approval was
submitted through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`5aae3599c609a7470b6806320b3b962d34ee1336cc069236f56ec4a67511d8bb` and source
distribution `fa164c2c11b189b8a743a578641c225c492b671a301762dc9df611a813f1bfc2`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`, recorded `America/New_York` as
`local_timezone` with `--timezone America/New_York`, and stopped with
`TIMEZONE_INVALID` (exit 2) without creating output for `asia/tokyo`.

### v1.5.0 release assessment (historical)

The v1.5.0 release source passed main CI run `37587836756` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `37587836696`. A build-only publish workflow
run (`37588024918`) on the release source passed with every upload job
skipped. Production publish workflow run `37588284218` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The publication
sequence ran under one Human approval given after its values were shown. The
`pypi` Environment deployment was Human-authorized, and the approval was
submitted through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`6d17b79e3fee5c9cbeb9a80c66c69213c5b29e6f15f7e9294f7c949c5b2c2b7a` and source
distribution `873171db165c5d79fd7db0f54336d62e167b96f82774535ea55b801cfac464da`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`.

### v1.4.1 release assessment (historical)

The v1.4.1 release source passed main CI run `37563843781` (Ubuntu `test` and
`windows-runtime`) and CodeQL run `37563843505`. A build-only publish workflow
run (`37563874206`) on the release source passed with every upload job
skipped. Production publish workflow run `37566440958` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The `pypi`
Environment deployment was Human-authorized, and the approval was submitted
through the GitHub API on the Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`703926f16e6dde1a6a515b04e44cc6090823dc9fcd0c5d4a8a71e09443564ee5` and source
distribution `76e04d70421f0dbe9b12a3a451d285de534fe1519ad1401d99e362b95114a428`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` in the
`pypi` Environment. The build-only run produced different checksums because
the distributions are not byte-reproducible across runs; only the production
run's artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to
`false` after the upload. A clean install from Production PyPI completed the
Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0), `validate-handoff`,
`doctor --run-output`, and `support-bundle`.

### v1.4.0 release assessment (historical)

The v1.4.0 release source passed main CI run `32388440076` (Ubuntu `test` and
`windows-runtime`) and Production publish workflow run `32389085934`. In that
publish run, the exact-source build and validation, Production PyPI
publication, and exact-version PyPI install verification succeeded, and the
TestPyPI jobs were skipped. The SHA-256 checksums recorded by the run match the
Production PyPI wheel and source distribution, which carry PEP 740 publish
attestations. A later publish workflow run on 2026-09-03 (`33726686281`,
source `a97a4ec`) was a build-only validation of the hardened workflow; its
upload and verification jobs were skipped and it published nothing. Earlier
tags, Releases, and package artifacts remain immutable and are not renamed or
reused.

### v1.3.3 release assessment (historical)

The reviewed v1.3.3 source passed 274 pytest tests, 219 unittest checks,
repository validators, strict wheel and source-distribution metadata checks,
isolated artifact installs, and Ubuntu and Windows CI while preserving the
stable `1.x` one-shot and Snapshot contracts. Main CI run `31648832233` and
Production publish workflow run `31653110586` passed. Clean Production PyPI
installation, version/import checks, `pip check`, Synthetic Run-All, and its
17-dataset/6-relationship handoff passed; the Production Sleep smoke passed
11/11 checks. Earlier tags, Releases, and package artifacts remain immutable
and are not renamed or reused.

The prior v1.3.0 feature release remains the immutable source of the 17-dataset
and 212-field Wellness/Metrics contract. The v1.3.1, v1.3.2, and v1.3.3 patches
and the v1.4.0 release do not change that contract.

Post-publication validation on one maintainer-owned physical Windows
environment clean-installed Production PyPI v1.2.1, installed `tzdata`
automatically, resolved `Asia/Tokyo`, and completed Synthetic Run-All with
`PASS_WITH_WARNINGS`, exit 0, Activities detected=1 / processed=1, and
`run_summary.json` present. This supplements, but does not generalize beyond,
the `windows-latest` CI evidence.
