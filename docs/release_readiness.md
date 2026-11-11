# Release Readiness

## v2.3.0rc3 release candidate

Version `2.3.0rc3`, the third release candidate of v2.3.0, is published on
TestPyPI only, for the checks on macOS and on Windows before v2.3.0. It is
v2.3.0rc2 with three stages that the hand checks of v2.3.0rc2 asked for: the
notes of a panel open in place under its row of numbers and cover nothing, and
a panel is never lower than what it holds (stage X12d3, #241); notes that open
below what the panels show bring them into view and the panels go back when
they close, the reading at the top right of a panel keeps its place as the
cross line moves, and a picture saved with the notes open leaves the panels
where they were (stage X12d4, #242); and, in a narrow window, the list of the
activities of a period keeps its names at least 7em wide and its column of the
laps at the right edge (stage X12d5, #243). Production PyPI and the latest
GitHub Release stay v2.2.1, and no GitHub Release was made for the release
candidate.

From v2.3.0rc2, the package changes only in the view page and in the version:
three files of `gui/static` and `__init__.py`; no other file under `src`
differs, and no file is added or removed. For the same input, timezone, and
options, the processing of a run, the outputs, and the Snapshot Store are
those of v2.3.0rc2, and the series command writes the same files; only the
version that an output records, and what is computed from it, differ:

```text
$ git diff --stat v2.3.0rc2 v2.3.0rc3 -- src
 src/garmin_running_data_normalizer/__init__.py     |   2 +-
 .../gui/static/view.css                            | 115 +++++++-
 .../gui/static/view.mjs                            | 302 ++++++++++++++++++---
 .../gui/static/view_flow.mjs                       |  25 +-
 4 files changed, 388 insertions(+), 56 deletions(-)
```

The Windows CI ran every Windows step with v2.3.0rc3 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. The CI ran
the whole test suite with Python 3.15 on Linux and macOS as well. The hand
checks of v2.3.0rc2 were stopped so that their steps could be corrected; after
this publication, with steps written again, a macOS machine checks v2.3.0rc3,
and a Windows machine checks its installation from TestPyPI, the file chooser,
the windows of the laps in the fonts of Windows and in a narrow window, and
the end of the GUI in its PowerShell window. What 2.3.0 does on Windows only
(the half-written files of a write and the reading of the Snapshot Store) is
left to the tests of the Windows CI, as the Human maintainer decided on
2026-11-11. The GUI guides at the `v2.3.0rc3` tag, which the links of the
GUI's help panel open, give the lines that install v2.2.1 from Production PyPI
and say "from 2.3.0" where they describe what 2.3.0 changes; the README says
how to try the release candidate from TestPyPI.

The release source is `1c7c7023e231d383214aaa376809954babe04a86` (#244). The
annotated `v2.3.0rc3` tag (tag object
`2a83bfcb9b938f7e9abc5a4e69aeb85e47bec101`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-11-11 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `42998889692` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `42998888767`. A build-only publish
workflow run (`43000574994`) on the release source passed with every upload
job skipped. Publish workflow run `43002219879` then built and validated the
exact source, with the same steps passing (the repository checks, the page
tests, and the checks of the files of the wheel and of the source distribution
after an isolated installation), and published to TestPyPI; the PyPI jobs were
skipped. Both runs used the `ubuntu-26.04` runner image (20261101.186.1),
Python 3.11.18, and Node.js 24.22.2: 1,903 tests passed and 19 were skipped,
as on Ubuntu in the CI, and 353 page tests passed. The Sigstore transparency
log (Rekor) was read before the run and answered. The publication and the tag
ran under one Human approval given after their values were shown. The
`testpypi` Environment deployment was Human-authorized, and the approval was
submitted once through the GitHub API on the Human's instruction and accepted;
what waited and the approvals of the run were read again after it.
`TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish run and returned
to `false` once its approval gate had passed, before the deployment was
approved.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`8cfa272a1bf98b5cc3683ac4af5e6909b226b8e07b060f3ece22f50d044bc949` and source
distribution
`ec71b988699b363106c19b08673bab1c21015ca4076765f5b639a734f5266348`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. On TestPyPI, the wheel is 1,141,508 bytes,
the size of the wheel built from the release source on macOS before the
publication, and the source distribution is 1,809,397 bytes, 1,299 bytes
smaller than that build (1,810,696 bytes), as the distributions are built
again in each run and are not byte-reproducible. The build-only run produced
different checksums for the same reason; only the publish run's artifacts were
published. The documents at the `v2.3.0rc3` tag describe the installation of
the release candidate from TestPyPI in the words used before the publication.

## v2.3.0rc2 release candidate

Version `2.3.0rc2`, the second release candidate of v2.3.0, is published on
TestPyPI only, for the checks on macOS and on Windows before v2.3.0. It is
v2.3.0rc1 with stage X12d1 (#238), which the hand checks of v2.3.0rc1 asked
for: in a narrow window, every window of the right column of the view page
stays inside the column (the summary, the laps, the marks, the menu of the
other views, and the picker of the items; all but the laps were cut the same
way since v2.2.0), the tables of the laps keep their heads and two rows or so,
and the button of a window and the kinds of the laps keep one line. Production
PyPI and the latest GitHub Release stay v2.2.1, and no GitHub Release was made
for the release candidate.

From v2.3.0rc1, the package changes only in the view page and in the version:
three files of `gui/static` and `__init__.py`; no other file under `src`
differs, and no file is added or removed. For the same input, timezone, and
options, the processing of a run, the outputs, and the Snapshot Store are
those of v2.3.0rc1, and the series command writes the same files; only the
version that an output records, and what is computed from it, differ:

```text
$ git diff --stat v2.3.0rc1 v2.3.0rc2 -- src
 src/garmin_running_data_normalizer/__init__.py     |  2 +-
 .../gui/static/view.css                            | 15 +++++++
 .../gui/static/view.mjs                            | 51 ++++++++++++++++++++--
 .../gui/static/view_flow.mjs                       | 32 ++++++++++++++
 4 files changed, 95 insertions(+), 5 deletions(-)
```

The Windows CI ran every Windows step with v2.3.0rc2 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. The CI ran
the whole test suite with Python 3.15 on Linux and macOS as well. After this
publication, a macOS machine checks v2.3.0rc2, and a Windows machine checks
what 2.3.0 does on Windows only (the half-written files of a write and the
reading of the Snapshot Store), as the Human maintainer decided on 2026-11-09,
and on 2026-11-10 for this release candidate. The GUI guides at the
`v2.3.0rc2` tag, which the links of the GUI's help panel open, give the lines
that install v2.2.1 from Production PyPI and say "from 2.3.0" where they
describe what 2.3.0 changes; the README says how to try the release candidate
from TestPyPI.

The release source is `048c885fb58c15d403e8e2a0e7f63007e9699f69` (#239). The
annotated `v2.3.0rc2` tag (tag object
`f44b1240688afd5ae2698e456dbcb0f50447359b`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-11-10 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `42777683848` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `42777683849`. A build-only publish
workflow run (`42779180981`) on the release source passed with every upload
job skipped. Publish workflow run `42781780880` then built and validated the
exact source, with the same steps passing (the repository checks, the page
tests, and the checks of the files of the wheel and of the source distribution
after an isolated installation), and published to TestPyPI; the PyPI jobs were
skipped. Both runs used the `ubuntu-26.04` runner image (20261101.186.1),
Python 3.11.18, and Node.js 24.22.2: 1,898 tests passed and 19 were skipped,
as on Ubuntu in the CI, and 352 page tests passed. The Sigstore transparency
log (Rekor) was read before the run and answered. The publication and the tag
ran under one Human approval given after their values were shown. The
`testpypi` Environment deployment was Human-authorized, and the approval was
submitted once through the GitHub API on the Human's instruction and accepted;
what waited and the approvals of the run were read again after it.
`TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish run and returned
to `false` once its approval gate had passed, before the deployment was
approved.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`5a3eab28587dc11c1348d0faa0a7423d49964c6f8cdb99e3229486f3f08cf05e` and source
distribution
`a0d898f1bd0a08740f69a190afe86b69cdcf1eadff168145d09ec2d55bb9404d`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. On TestPyPI, the wheel is 1,137,063 bytes,
the size of the wheel built from the release source on macOS before the
publication, and the source distribution is 1,799,170 bytes, 1,399 bytes
smaller than that build (1,800,569 bytes), as the distributions are built
again in each run and are not byte-reproducible. The build-only run produced
different checksums for the same reason; only the publish run's artifacts were
published. The documents at the `v2.3.0rc2` tag describe the installation of
the release candidate from TestPyPI in the words used before the publication.

## v2.3.0rc1 release candidate

Version `2.3.0rc1`, the first release candidate of v2.3.0, is published on
TestPyPI only, for the checks on macOS and on Windows before v2.3.0. It is
v2.2.1 with the stages X1 to X7, X9b to X11, and X12p (#223 to #235): the laps
of an activity and the work laps of the shoes, read from the FIT files of the
Snapshot Store only when asked for; the race days by day and over 2 or 4
weeks; the highest of each year and of each race; pictures saved as PNG in the
sizes of posts; why a period of a panel left records out; the records that
changed since the output before; the cadence in steps per minute; a question
that closes by Escape wherever the focus is; a half-written file that stays on
Windows, told; the sizes of some tables and windows; and the privacy sentences
of the guides. Production PyPI and the latest GitHub Release stay v2.2.1, and
no GitHub Release was made for the release candidate.

From v2.2.1, the package changes in 23 files under `src`: the version, the lap
kinds of a FIT file, the reading of the FIT files of the store and the check
of its metadata, the work laps of the shoes, the list of the earlier outputs,
the server, the settings and the views of the GUI, the pages and the words of
both catalogs, the comparison of two outputs, and the data and the series of
the view page. For the same input, timezone, and options, the processing of a
run, the outputs, and the Snapshot Store are those of v2.2.1, and the series
command writes the same files; only the version that an output records, and
what is computed from it, differ:

```text
$ git diff --stat v2.2.1 v2.3.0rc1 -- src
 src/garmin_running_data_normalizer/__init__.py     |    2 +-
 .../fit/lap_kinds.py                               |  250 +++
 .../gui/fit_reading.py                             | 1051 +++++++++++
 src/garmin_running_data_normalizer/gui/outputs.py  |   39 +
 src/garmin_running_data_normalizer/gui/server.py   |  276 ++-
 src/garmin_running_data_normalizer/gui/settings.py |  101 +-
 .../gui/shoe_work.py                               |  220 +++
 .../gui/static/app.mjs                             |  152 +-
 .../gui/static/flow.mjs                            |  150 +-
 .../gui/static/i18n.mjs                            |   10 +
 .../gui/static/i18n/en.json                        |  220 ++-
 .../gui/static/i18n/ja.json                        |  220 ++-
 .../gui/static/index.html                          |    4 +
 .../gui/static/styles.css                          |    7 +
 .../gui/static/view.css                            |  266 +++
 .../gui/static/view.html                           |   83 +-
 .../gui/static/view.mjs                            | 1899 ++++++++++++++++++--
 .../gui/static/view_flow.mjs                       | 1435 ++++++++++++++-
 src/garmin_running_data_normalizer/gui/views.py    |   79 +-
 .../snapshot/store.py                              |   13 +-
 src/garmin_running_data_normalizer/view/changes.py |  345 ++++
 src/garmin_running_data_normalizer/view/data.py    |    9 +-
 src/garmin_running_data_normalizer/view/series.py  |  135 +-
 23 files changed, 6718 insertions(+), 248 deletions(-)
```

The Windows CI ran every Windows step with v2.3.0rc1 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. The CI ran
the whole test suite with Python 3.15 on Linux and macOS as well. After this
publication, a macOS machine checks v2.3.0rc1, and a Windows machine checks
what 2.3.0 does on Windows only (the half-written files of a write and the
reading of the Snapshot Store), as the Human maintainer decided on 2026-11-09.
The GUI guides at the `v2.3.0rc1` tag, which the links of the GUI's help panel
open, give the lines that install v2.2.1 from Production PyPI and say "from
2.3.0" where they describe what 2.3.0 changes; the README says how to try the
release candidate from TestPyPI.

The release source is `ec0cb2e506fd8ca44e1ebabce006d5f670b8240f` (#236). The
annotated `v2.3.0rc1` tag (tag object
`005ad07fba3fae4ec02f653b94efec3500c18eb0`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-11-10 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `42725802563` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `42725801995`. A build-only publish
workflow run (`42727282642`) on the release source passed with every upload
job skipped. Publish workflow run `42733125388` then built and validated the
exact source, with the same steps passing (the repository checks, the page
tests, and the checks of the files of the wheel and of the source distribution
after an isolated installation), and published to TestPyPI; the PyPI jobs were
skipped. Both runs used the `ubuntu-26.04` runner image (20261101.186.1),
Python 3.11.18, and Node.js 24.22.2: 1,897 tests passed and 19 were skipped,
as on Ubuntu in the CI, and 342 page tests passed. The Sigstore transparency
log (Rekor) was read before the run and answered. The publication and the tag
ran under one Human approval given after their values were shown. The
`testpypi` Environment deployment was Human-authorized, and the approval was
submitted once through the GitHub API on the Human's instruction and accepted;
what waited and the approvals of the run were read again after it.
`TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish run and returned
to `false` once its approval gate had passed, before the deployment was
approved.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`25cdb44610329070e8be68ba99bb9f3bee3c179e225838a0e97ed9cce4853589` and source
distribution
`f94d5df2651f343c2dc950c9b6524ce2809d92c636b9908132e8815ceb18b111`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. On TestPyPI, the wheel is 1,135,628 bytes,
the size of the wheel built from the release source on macOS before the
publication, and the source distribution is 1,796,294 bytes, 1,212 bytes
smaller than that build (1,797,506 bytes), as the distributions are built
again in each run and are not byte-reproducible. The build-only run produced
different checksums for the same reason; only the publish run's artifacts were
published. The documents at the `v2.3.0rc1` tag describe the installation of
the release candidate from TestPyPI in the words used before the publication.

## v2.2.1 stable release

Version `2.2.1` is published as the release that fixes small things of the
view page and of the bar at the bottom of the pages of the local GUI: the
view page opens the output again when it finds that the output changed, the
questions of the bar show right above their buttons, the words of the view
page and its table of six years are clearer, and forgetting the settings
also removes the half-written files of a write. It is v2.2.1rc1 with the
version 2.2.1, the documents of the stable release, and the pictures of the
GUI Guides taken again with 2.2.1. From v2.2.1rc1, the package's Python
changes only in the version in `__init__.py`, and the files of the page do
not change. The release publishes directly to Production PyPI through the
protected `pypi` Environment; it is not published on TestPyPI.

The Windows CI runs every Windows step with v2.2.1 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. The
release candidate v2.2.1rc1 was checked on macOS with synthetic data after
its publication: its installation from TestPyPI, whose 109 package files are
those of its tag byte for byte; its refusal of an output of v2.2.0 in
`validate-handoff`, `doctor --run-output`, `support-bundle`, and `series`
(exit 2 with `OUTPUT_OTHER_VERSION`, writing no file) and on the view page
(HTTP 422 with `OUTPUT_OTHER_VERSION`), with both outputs unchanged; what
stages W1 to W4 changed, measured in a scripted browser at 1366 × 650 and
900 × 700 in English and Japanese, with the images that the view page saves;
and by hand in Safari and Chrome. The look on Windows was not checked by hand
for v2.2.1rc1, as the Human maintainer decided on 2026-11-06, and the release
notes list it as not checked. From v2.2.1rc1, only the version and the
documents change.

The release source is `7feb9c56bedddbe5707403c2bc1dde10ece38878` (#220). The
annotated `v2.2.1` tag (tag object
`0b83b66bacf787d8092c8185f7afb6e76b592c76`), the latest stable GitHub Release
published on 2026-11-06 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v2.2.1rc1 release candidate

Version `2.2.1rc1`, the first release candidate of v2.2.1, is published on
TestPyPI only, for the checks on macOS before v2.2.1. It is v2.2.0 with the
fixes of stages W1 to W5 (#211 to #214, #216, and #217): the view page opens
the output again when the output changes while it is open, the questions of
**Quit** and **Forget the remembered settings…** stand above their buttons,
the words of the view page and its tables of six years are mended,
forgetting the settings also removes the half-written files of a write,
`standalone` can be the first module imported, and the publish workflow runs
the repository checks and the page tests and checks the files of what it
builds and publishes. Production PyPI and the latest GitHub Release stay
v2.2.0, and no GitHub Release was made for the release candidate.

From v2.2.0, the package changes in 15 files under `src`: the server and the
settings of the GUI, the pages and the words of both catalogs, the views of
the server, the check of an output, `standalone`, and the version. For the
same input, timezone, and options, the processing of a run, the outputs, and
the Snapshot Store are those of v2.2.0; only the version that an output
records, and what is computed from it, differ:

```text
$ git diff --stat v2.2.0 v2.2.1rc1 -- src
 src/garmin_running_data_normalizer/__init__.py     |   2 +-
 src/garmin_running_data_normalizer/gui/server.py   |  52 +++-
 src/garmin_running_data_normalizer/gui/settings.py | 125 ++++++++-
 .../gui/static/app.mjs                             |  68 +++++
 .../gui/static/i18n/en.json                        |  39 +--
 .../gui/static/i18n/ja.json                        |  59 +++--
 .../gui/static/index.html                          |   4 +
 .../gui/static/styles.css                          |  20 ++
 .../gui/static/view.css                            |  10 +
 .../gui/static/view.html                           |   3 +
 .../gui/static/view.mjs                            | 284 ++++++++++++++++++++-
 .../gui/static/view_flow.mjs                       | 142 ++++++++++-
 src/garmin_running_data_normalizer/gui/views.py    |  21 +-
 src/garmin_running_data_normalizer/output_check.py |   2 -
 src/garmin_running_data_normalizer/standalone.py   |   7 +-
 15 files changed, 765 insertions(+), 73 deletions(-)
```

The Windows CI ran every Windows step with v2.2.1rc1 and Python 3.11, and
the Windows tests and the isolated wheel installation with Python 3.15. The
CI ran the whole test suite with Python 3.15 on Linux and macOS as well. A
macOS machine checks v2.2.1rc1 after this publication; the look on Windows
is not checked by hand for this release candidate, as the Human maintainer
decided on 2026-11-06, and the release notes of v2.2.1 are to list it as not
checked. The GUI guides at the `v2.2.1rc1` tag, which the links of the GUI's
help panel open, give the lines that install v2.2.0 from Production PyPI and
say "from 2.2.1" where they describe what 2.2.1 changes; the README says how
to try the release candidate from TestPyPI.

The release source is `0b9e7fa075edd78c4d4ffb33129f4cefb2c7fc5f` (#218). The
annotated `v2.2.1rc1` tag (tag object
`2e836fb15bd7e5f2a54214906bdc71af793cbfec`) points to it, so that the links of
the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-11-06 JST and the publish
workflow's exact-version TestPyPI install verification are complete.

The release source passed main CI run `42118119499` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `42118119364`. A build-only publish
workflow run (`42120193468`) on the release source passed with every
upload job skipped. In it, the steps that stage W5 added ran in the publish
workflow for the first time and passed: the repository checks, the page
tests, and the checks of the files of the wheel and of the source
distribution after an isolated installation. Publish workflow run
`42128633967` then built and validated the exact source, with the same steps
passing, and published to TestPyPI; the PyPI jobs were skipped. Both runs
used the `ubuntu-26.04` runner image (20261101.186), Python 3.11.18, and
Node.js 24.22.2: 1,713 tests passed and 14 were skipped, as on Ubuntu in the
CI, and 290 page tests passed. The Sigstore transparency log (Rekor) was read
before the run and answered. The publication and the tag ran under one Human
approval given after their values were shown. The `testpypi` Environment
deployment was Human-authorized, and the approval was submitted through the
GitHub API on the Human's instruction: the first two submissions were
answered with HTTP 500 and recorded nothing, and the third, after the same
checks of the run and of `main`, was accepted. `TESTPYPI_PUBLISH_APPROVED`
was set to `true` for the publish run and returned to `false` once its
approval gate had passed, before the deployment was approved.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`35825e4bd5afbcc5b1a80a49c385b80379c79993eec862cbe385433b286e9601` and source
distribution `0b8fac7a522384ee29aaf4d7be351f2732951964c41f08889cbabf4cd74e8034`.
Each file carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. On TestPyPI, the wheel is 1,055,861 bytes,
the size of the wheel built from the release source on macOS before the
publication, and the source distribution is 1,619,597 bytes, 1,348 bytes
smaller than that build (1,620,945 bytes), as the distributions are built
again in each run and are not byte-reproducible. The build-only run produced
different checksums for the same reason; only the publish run's artifacts
were published. The documents at the `v2.2.1rc1` tag describe the
installation of the release candidate from TestPyPI in the words used before
the publication.

## v2.2.0 stable release

Version `2.2.0` is published as the release that adds layouts, comparisons
of years, marks and the list of the activities of a period, other views, a
summary, conditions on the activities, and saving as an image to the view
page of the local GUI, and that remembers the view and the timezone of the
last run that made an output. It is v2.2.0rc2 with the version 2.2.0, the
documents of the stable release, and the pictures of the GUI Guides taken
again with 2.2.0. From v2.2.0rc2, the package's Python changes only in the
version in `__init__.py`, and the files of the page do not change. The
release publishes directly to Production PyPI through the protected `pypi`
Environment; it is not published on TestPyPI.

The Windows CI runs every Windows step with v2.2.0 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. The
checks of the two release candidates are recorded in their sections below:
v2.2.0rc1 on macOS, with the maintainer's own real Export by a script that
recorded only whether each check passed, on one physical Windows 11 PC, and
by two new AI sessions; and v2.2.0rc2, with the words and looks that those
checks found, on macOS, where what changed was measured in a scripted
browser at three sizes in English and Japanese and seen by hand in Safari
and Chrome. The fonts, display scaling, contrast themes, and Edge of Windows
were not checked again for v2.2.0rc2. From v2.2.0rc2, only the version and
the documents change.

The release source is `4546a1b58b519291e153aacb8320acb78bd39f5c` (#208). The
annotated `v2.2.0` tag (tag object
`881873a0697ac7b0c780a7d8b884486eb4c4a938`), the latest stable GitHub Release
published on 2026-11-04 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v2.2.0rc2 release candidate

Version `2.2.0rc2`, the second release candidate of v2.2.0, is published on
TestPyPI only, for the checks on macOS of what changed after v2.2.0rc1,
before v2.2.0. It is v2.2.0rc1 with the words and the looks of the view page
that stage U3 (#205) changed after the checks of v2.2.0rc1: the Japanese name
of the layouts, where the items of a comparison of years are chosen, the
rules of a comparison on race days in the help and the guides, the colour of
the years in the legend of a comparison, a line before each year in the
table of a comparison, and the note of the calendar legend, which moved under
its information button. Production PyPI and the latest GitHub Release stay
v2.1.0, and no GitHub Release was made for the release candidate.

From v2.2.0rc1, the package changes in 8 files under `src`: seven files of
the GUI (the words of both catalogs, the styles of the pages, and the view
page) and the version. For the same input, timezone, and options, the
processing of a run, the outputs, and the Snapshot Store are those of
v2.2.0rc1 and v2.1.0. The view page and `series` read only outputs that the
installed version produced, so outputs of v2.2.0rc1 are normalized again
with v2.2.0rc2:

```text
$ git diff --stat v2.2.0rc1 v2.2.0rc2 -- src
 src/garmin_running_data_normalizer/__init__.py     |  2 +-
 .../gui/static/i18n/en.json                        | 11 +--
 .../gui/static/i18n/ja.json                        | 55 ++++++-------
 .../gui/static/styles.css                          | 23 ++++++
 .../gui/static/view.css                            | 94 ++++++++++++++++++++--
 .../gui/static/view.html                           |  6 +-
 .../gui/static/view.mjs                            | 56 +++++++++----
 .../gui/static/view_flow.mjs                       | 12 +++
 8 files changed, 205 insertions(+), 54 deletions(-)
```

The Windows CI ran every Windows step with v2.2.0rc2 and Python 3.11, and
the Windows tests and the isolated wheel installation with Python 3.15. The
CI ran the whole test suite with Python 3.15 on Linux and macOS as well. A
macOS machine checks what changed after v2.2.0rc1 with synthetic data after
this publication. The look of v2.2.0rc2 on Windows is not checked by hand and
is recorded as not checked, as the Human maintainer decided on 2026-11-04.
The GUI guides at the `v2.2.0rc2` tag, which the links of the GUI's help
panel open, give the lines that install v2.1.0 from Production PyPI and
describe what 2.2.0 adds in the sections marked "from 2.2.0"; their pictures
show v2.1.0, except four Japanese pictures that stage U3 took again, which
show v2.2.0rc1, and all of them are to be taken again before v2.2.0. The
README says how to try the release candidate from TestPyPI.

The release source is `52906e783a0bfc0183b05db85e04bcdbbc70aedd` (#206). The annotated `v2.2.0rc2` tag
(tag object `1750864cf2cf881c9326e0f3118dc8b9ce5b3603`) points to it, so that the links of the GUI's help
panel open the documents of that tag. TestPyPI publication through Trusted
Publishing/OIDC on 2026-11-04 JST and the publish workflow's exact-version
TestPyPI install verification are complete.

The release source passed main CI run `41725983369` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `41725981990`. A build-only publish
workflow run (`41728923972`) on the release source passed with every
upload job skipped. Publish workflow run `41735622046` then built and
validated the exact source. In its first attempt, TestPyPI answered 503 to
the Trusted Publishing token request, and the job that publishes to TestPyPI
stopped before any upload. After TestPyPI had answered as usual for fifteen
minutes in a row (from 23:21 to 23:35 UTC), the failed jobs were run again
in a second attempt. The second attempt kept the build and the approval gate
of the first, so it published the artifact that the first attempt built; it
published to TestPyPI and verified the installation, and the PyPI jobs were
skipped. The Sigstore transparency log (Rekor) was read before the run and
answered. The publication and the tag ran under one Human approval given
after their values were shown, and the second attempt under a second Human
approval given after the failure was shown. The `testpypi` Environment
deployment was Human-authorized in each attempt, and the approvals were
submitted through the GitHub API on the Human's instruction.
`TESTPYPI_PUBLISH_APPROVED` was set to `true` for the first attempt and
returned to `false` as soon as it finished; it stayed `false` through the
second attempt, as the approval gate did not run again.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`16dfc619032740e915712b76c43e698921a35aa8a70b2975dde8ade1bdfbbb0a` and source distribution `04ff607f23a3b1a13a556c1b80facc1115dd08b420a21291cf28e7b4ad585b09`. Each file carries a
PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The wheel on TestPyPI has the size of the
wheel built from the release source on macOS before the publication
(1,046,280 bytes); the source distribution on TestPyPI is 1,206 bytes
smaller than that build (1,583,208 bytes), as the distributions are built
again in each run and are not byte-reproducible. The build-only run produced
different checksums for the same reason; only the publish run's artifacts
were published. The documents at the `v2.2.0rc2` tag, and the README in the
metadata of the published wheel, describe the installation of the release
candidate from TestPyPI in the words used before the publication.

## v2.2.0rc1 release candidate

Version `2.2.0rc1`, the first release candidate of v2.2.0, is published on
TestPyPI only, for the checks on macOS, on a physical Windows machine, and by
new AI sessions before v2.2.0. It is v2.1.0 with what stages K1 to U2 (#177
to #202) add to the view page: layouts, comparisons of years, marks and the
list of the activities of a period, a calendar, two items plotted, a
distribution, a summary, saving as a picture, a view by shoes, and conditions
on the activities, with the guides of stage H1 (#176) and of those stages.
Production PyPI and the latest GitHub Release stay v2.1.0, and no GitHub
Release was made for the release candidate.

From v2.1.0, the package changes in 25 files under `src`: the layouts and the
marks of the view page, the names of the activities that only the view page
reads, the server of the view page and its answers, the settings that the GUI
remembers (the layouts, the view, and the timezone of the last run that made
an output), with a generation of them that each forgetting moves on and that
the server keeps only while it runs, the numbers of the view page and of
`series`, the files of the pages and the words of both catalogs, a stop for
conditions of another form, the longest name of a timezone, and the version.
For the same input, timezone, and options, the processing of a run, the
outputs, and the Snapshot Store are those of v2.1.0:

```text
$ git diff --stat v2.1.0 v2.2.0rc1 -- src
 src/garmin_running_data_normalizer/__init__.py     |    2 +-
 src/garmin_running_data_normalizer/common/names.py |   30 +
 src/garmin_running_data_normalizer/common/time.py  |    3 +
 src/garmin_running_data_normalizer/gui/layouts.py  |  281 +
 src/garmin_running_data_normalizer/gui/marks.py    |  202 +
 src/garmin_running_data_normalizer/gui/places.py   |   15 +-
 src/garmin_running_data_normalizer/gui/runs.py     |   25 +-
 src/garmin_running_data_normalizer/gui/server.py   |  380 +-
 src/garmin_running_data_normalizer/gui/settings.py |  561 +-
 .../gui/static/app.mjs                             |  125 +-
 .../gui/static/flow.mjs                            |  310 +-
 .../gui/static/i18n.mjs                            |   40 +
 .../gui/static/i18n/en.json                        |  415 +-
 .../gui/static/i18n/ja.json                        |  415 +-
 .../gui/static/launch.mjs                          |    6 +-
 .../gui/static/styles.css                          |   55 +-
 .../gui/static/view.css                            | 2192 ++++-
 .../gui/static/view.html                           |  356 +-
 .../gui/static/view.mjs                            | 8960 +++++++++++++++++---
 .../gui/static/view_chart.mjs                      |  445 +-
 .../gui/static/view_flow.mjs                       | 2605 +++++-
 src/garmin_running_data_normalizer/gui/views.py    |  391 +-
 src/garmin_running_data_normalizer/stops.py        |    5 +
 src/garmin_running_data_normalizer/view/data.py    |  274 +-
 src/garmin_running_data_normalizer/view/series.py  |  727 +-
 25 files changed, 17268 insertions(+), 1552 deletions(-)
```

The Windows CI ran every Windows step with v2.2.0rc1 and Python 3.11, and
the Windows tests and the isolated wheel installation with Python 3.15. The
CI ran the whole test suite with Python 3.15 on Linux and macOS as well. A
macOS machine, a physical Windows machine, and new AI sessions check
v2.2.0rc1 after this publication, as the Human maintainer decided on
2026-11-02. The GUI guides at the `v2.2.0rc1` tag, which the links of the
GUI's help panel open, give the lines that install v2.1.0 from Production
PyPI and describe what 2.2.0 adds in the sections marked "from 2.2.0"; the
README says how to try the release candidate from TestPyPI.

The release source is `8f1d3b7654f87777f0f54a9329d2877c1910e33b` (#203). The annotated `v2.2.0rc1` tag
(tag object `2024e867691ddb48ec0b8173acc6188e6d1194dd`) points to it, so that the links of the GUI's help
panel open the documents of that tag. TestPyPI publication through Trusted
Publishing/OIDC on 2026-11-03 JST and the publish workflow's exact-version
TestPyPI install verification are complete.

The release source passed main CI run `41474275786` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`; the first attempt of `macos-python-3-15` was cancelled
when no hosted runner took it, and the job passed on its second attempt) and
CodeQL run `41474276415`. A build-only publish workflow run (`41476210613`)
on the release source passed with every upload job skipped. Publish workflow
run `41481826282` then built and validated the exact source and published to
TestPyPI; the PyPI jobs were skipped. The Sigstore transparency log (Rekor)
was read before the run and answered. The publication and the tag ran under
one Human approval given after their values were shown. The `testpypi`
Environment deployment was Human-authorized, and the approval was submitted
through the GitHub API on the Human's instruction.
`TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish run and returned
to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`0998dac99f18effc082d0ae9e702813ea0092cb0e9ab56b12d9e3a520acc8067` and source distribution `71485dd8e190ede28b705a3695b99b63fd8254ab6886d17556d6b3e641b59d0c`. Each file carries a
PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.2.0rc1` tag describe the installation of the release candidate from
TestPyPI in the words used before the publication.

## v2.1.0 stable release

Version `2.1.0` is published as the release that adds the view page of the
local GUI, the `series` command, and the colors of the page. It is v2.1.0rc1
with the version 2.1.0, the documents of the stable release, and the GUI
Guides that describe the view page. From v2.1.0rc1, the package's Python
changes only in the version in `__init__.py`, and the files of the page do not
change. The release publishes directly to Production PyPI through the
protected `pypi` Environment; it is not published on TestPyPI.

The Windows CI runs every Windows step with v2.1.0 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. macOS
checked the installation of v2.1.0rc1 from TestPyPI, and the view page by hand
in Safari and Chrome with a synthetic Export of fifteen and a half years: its
overview, its full screen, and quitting from it. A script checked v2.1.0rc1
with the maintainer's own real Export on macOS and recorded only whether each
check passed. On one physical Windows 11 PC, with Windows PowerShell 5.1,
Python 3.14.5 (a version that the CI does not run: it runs 3.11 and 3.15),
Microsoft Edge, and the display at 150%, the line of the guide for Windows
PowerShell, with the index of TestPyPI, installed v2.1.0rc1 and made the two
icons, and the page normalized a synthetic Export. That Export, the same
fifteen and a half years of made-up records as on macOS, made from the parts
of the tests at the tag `v2.1.0rc1` and copied as a ZIP, took the place of the
tracked synthetic fixture that the
[Windows validation workflow policy](release_closeout/v1.2.1.md#windows-validation-workflow-policy)
of v1.2.1 names, since that fixture holds a single activity, too little to
check the panels, the overview, and the full screen of the view page; no Git
command ran on Windows. The view page opened in the next tab with no
overlapping or cut text in its top rows and with the light colors that Windows
was set to, moved to and from the tab of the page of the GUI without opening
new tabs, chose a range on its overview, went to and from its full screen, and
quit the app, after which no process of the app was left. The line that
removes this app then removed its six places; Windows first reported the
folder of the virtual environment in use, and a retry went on. Two new AI
sessions with no context read the draft of the part of the guide about the
view page and used the view page from its screen only. From v2.1.0rc1, only
the version and the documents change.

The release source is `4ad43f509f81dad4dbb57a7c0d0d14bc1022ddf9` (#174). The
annotated `v2.1.0` tag (tag object
`79126489f9b8dac48d76b7436051b17c55920d1b`), the latest stable GitHub Release
published on 2026-10-28 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v2.1.0rc1 release candidate

Version `2.1.0rc1`, the first release candidate of v2.1.0, is published on
TestPyPI only, for the checks on macOS, on a physical Windows machine, and by
new AI sessions before v2.1.0. It is v2.0.1 with the view page in the tab
next to the normalization page, the `series` command, and the colors of the
page (#165 to #170), and with an hour, instead of 10 minutes, before the GUI
stops by itself (#171). Production PyPI and the latest GitHub Release stay
v2.0.1, and no GitHub Release was made for the release candidate.

From v2.0.1, the package changes in 31 files under `src`: the new package
`view/` and the `series` command, the server and the files of the view page,
the colors of the page, rules moved without a change of behavior so that the
view page, `series`, and the earlier commands share them, two fixes of 2.0.x,
the wait of the GUI, and the version. The processing of a run, the outputs,
and the Snapshot Store are those of v2.0.1:

```text
$ git diff --stat v2.0.1 v2.1.0rc1 -- src
 src/garmin_running_data_normalizer/__init__.py     |    2 +-
 .../common/new_file.py                             |  107 +
 src/garmin_running_data_normalizer/common/sport.py |   43 +
 .../diagnostics/support_bundle.py                  |   85 +-
 src/garmin_running_data_normalizer/gui/command.py  |   18 +-
 src/garmin_running_data_normalizer/gui/outputs.py  |   38 +-
 src/garmin_running_data_normalizer/gui/server.py   |  135 +-
 src/garmin_running_data_normalizer/gui/settings.py |  164 +-
 .../gui/static/app.mjs                             |  207 +-
 .../gui/static/flow.mjs                            |  118 +-
 .../gui/static/i18n/en.json                        |  293 ++-
 .../gui/static/i18n/ja.json                        |  293 ++-
 .../gui/static/index.html                          |   21 +-
 .../gui/static/launch.mjs                          |   89 +
 .../gui/static/styles.css                          |  150 +-
 .../gui/static/theme.js                            |   37 +
 .../gui/static/view.css                            | 1239 +++++++++
 .../gui/static/view.html                           |  255 ++
 .../gui/static/view.mjs                            | 2630 ++++++++++++++++++++
 .../gui/static/view_chart.mjs                      |  424 ++++
 .../gui/static/view_flow.mjs                       | 1095 ++++++++
 src/garmin_running_data_normalizer/gui/views.py    |  201 ++
 src/garmin_running_data_normalizer/output_check.py |   59 +
 .../relationships.py                               |   33 +-
 src/garmin_running_data_normalizer/runner.py       |   86 +-
 src/garmin_running_data_normalizer/stops.py        |   76 +-
 .../view/__init__.py                               |    2 +
 src/garmin_running_data_normalizer/view/data.py    |  329 +++
 src/garmin_running_data_normalizer/view/items.py   |  168 ++
 src/garmin_running_data_normalizer/view/series.py  |  459 ++++
 .../view/series_file.py                            |  186 ++
 31 files changed, 8796 insertions(+), 246 deletions(-)
```

The Windows CI ran every Windows step with v2.1.0rc1 and Python 3.11, and
the Windows tests and the isolated wheel installation with Python 3.15. The
CI ran the whole test suite with Python 3.15 on Linux and macOS as well. A
macOS machine, a physical Windows machine, and new AI sessions check
v2.1.0rc1 after this publication, as the Human maintainer decided on
2026-10-27. The GUI guides stay those of v2.0.1 until v2.1.0 (decision
20261024-4): the guides at the `v2.1.0rc1` tag, which the links of the GUI's
help panel open, give the line that installs v2.0.1 from Production PyPI and
do not describe the view page yet, and the README says how to install the
release candidate from TestPyPI.

The release source is `f48729dcd6582c74d4b3a62955621111ccf25a6d` (#172). The annotated `v2.1.0rc1` tag
(tag object `a68f94c435ceb8d1f465bf68a53f256cb2896ba6`) points to it, so that the links of the GUI's help
panel open the documents of that tag. TestPyPI publication through Trusted
Publishing/OIDC on 2026-10-27 JST and the publish workflow's exact-version
TestPyPI install verification are complete.

The release source passed main CI run `40467207420` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `40467207269`. A build-only publish
workflow run (`40467378405`) on the release source passed with every upload
job skipped. Publish workflow run `40468864289` then built and validated the
exact source and published to TestPyPI; the PyPI jobs were skipped. The
Sigstore transparency log (Rekor) was read before the run and answered. The
publication and the tag ran under one Human approval given after their values
were shown. The `testpypi` Environment deployment was Human-authorized, and
the approval was submitted through the GitHub API on the Human's
instruction. `TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish
run and returned to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`94a37c36dfc208e74e4c8dca25d29fcd8b26a7b56abfb2d7330b662dc23f3b6c` and source distribution `0672605d35eef9b0a0e3cdcec6f8bb08e8222f5009a496ea5a180dc2f580de89`. Each file carries a
PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.1.0rc1` tag describe the installation of the release candidate from
TestPyPI in the words used before the publication.

## v2.0.1 stable release

Version `2.0.1` is published as the release that fixes small things of the
page of the local GUI and of the GUI Guide. It is v2.0.1rc1 with the version
2.0.1, the documents of the stable release, and the GUI Guides that describe
the page of v2.0.1. From v2.0.1rc1, the package's Python changes only in the
version in `__init__.py`, and the files of the page and the pictures do not
change. The release publishes directly to Production PyPI through the
protected `pypi` Environment; it is not published on TestPyPI.

The Windows CI runs every Windows step with v2.0.1 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. macOS
checked the installation of v2.0.1rc1 from TestPyPI, the line of the guide,
and the page by hand with synthetic data. On one physical Windows 11 x64
machine, with Windows PowerShell 5.1 and Python 3.14, the line of the guide
for Windows PowerShell, with the index of TestPyPI, installed v2.0.1rc1 and
made the two icons. The page, opened in Microsoft Edge, showed the bar at the
bottom, the hint of the box that runs, and the help of the timezone as they
were fixed, and normalized a synthetic Export without and with the import
into the Snapshots. The line for macOS, pasted there, ran nothing, and the
GUI Guide now names the lines that it shows. The rest of that check (the line
that a second normalization of the same Export shows, what the bar says on
**Quit**, and starting the GUI from the icon) was not observed there. From
v2.0.1rc1, only the version and the documents change.

The release source is `51d24f5e681b11028435c39159f72bee16863834` (#163). The
annotated `v2.0.1` tag (tag object
`fa62b1904c49ae0f6587e4108497b8f876754413`), the latest stable GitHub Release
published on 2026-10-26 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v2.0.1rc1 release candidate

Version `2.0.1rc1`, the first release candidate of v2.0.1, is published on
TestPyPI only, for the checks on macOS and on a physical Windows machine
before v2.0.1. It is v2.0.0 with the answers of the GUI guides to a reading
of v2.0.0 (#159) and the small fixes of the page of the GUI (#160).
Production PyPI and the latest GitHub Release stay v2.0.0, and no GitHub
Release was made for the release candidate.

From v2.0.0, the package changes in the version in `__init__.py`, in the
files of the page, and in the English words of `OPEN_FAILED`, a code that
only the GUI gives, in `stops.py`. The processing, the outputs, the command
line, and the Snapshot Store are those of v2.0.0:

```text
$ git diff --stat v2.0.0 v2.0.1rc1 -- src
 src/garmin_running_data_normalizer/__init__.py     |  2 +-
 .../gui/static/app.mjs                             | 59 ++++++++++++++++++-
 .../gui/static/flow.mjs                            | 66 ++++++++++++++++------
 .../gui/static/i18n/en.json                        | 16 ++++--
 .../gui/static/i18n/ja.json                        | 12 +++-
 .../gui/static/index.html                          | 11 +++-
 .../gui/static/styles.css                          |  7 ++-
 src/garmin_running_data_normalizer/stops.py        |  2 +-
 8 files changed, 146 insertions(+), 29 deletions(-)
```

The Windows CI ran every Windows step with v2.0.1rc1 and Python 3.11, and
the Windows tests and the isolated wheel installation with Python 3.15. The
CI ran the whole test suite with Python 3.15 on Linux and macOS as well. A
macOS machine and a physical Windows machine check v2.0.1rc1 after this
publication, as the Human maintainer decided on 2026-10-24. The GUI guides
stay those of v2.0.0 until v2.0.1, as the Human maintainer decided on the
same day: the guides at the `v2.0.1rc1` tag, which the links of the GUI's
help panel open, give the line that installs v2.0.0 from Production PyPI,
and the README says how to install the release candidate from TestPyPI.

The release source is `0c5f26ccac1fa4701ad6084689348eaf4d03c5f7` (#161). The
annotated `v2.0.1rc1` tag (tag object
`f85d6ae2aced95e488d103eebe6ed82cabdfafae`) points to it, so that the links
of the GUI's help panel open the documents of that tag. TestPyPI publication
through Trusted Publishing/OIDC on 2026-10-24 JST and the publish workflow's
exact-version TestPyPI install verification are complete.

The release source passed main CI run `40069475155` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `40069475238`. A build-only publish
workflow run (`40069977616`) on the release source passed with every upload
job skipped. Publish workflow run `40072369201` then built and validated the
exact source and published to TestPyPI; the PyPI jobs were skipped. The
Sigstore transparency log (Rekor) was read before the run and answered. The
publication and the tag ran under one Human approval given after their values
were shown. The `testpypi` Environment deployment was Human-authorized, and
the approval was submitted through the GitHub API on the Human's
instruction. `TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish
run and returned to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`224022cdd2ff686a759d1d786686d78beddb3accc404b516778d73f22f42d665` and
source distribution
`75e6f8aae9ffdf379bfb2e2d1a028f1e5743fa06d4f43d01c52db221da651da2`. Each
file carries a PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.0.1rc1` tag describe the installation of the release candidate from
TestPyPI in the words used before the publication.

## v2.0.0 stable release

Version `2.0.0` is published as the release that adds the local GUI and the
data handling of v2.0.0, the first release of the stable `2.x` family. It is
v2.0.0rc5 with the version 2.0.0, the documents of the stable release, and
the two changes of the GUI guides that were left for it: how to install
Python on Windows with the Python install manager, and the start of
**What you need**. From v2.0.0rc5, the package's Python changes only in the
version in `__init__.py`, and the files of the page and the pictures do not
change. The release publishes directly to Production PyPI through the
protected `pypi` Environment; it is not published on TestPyPI.

The Windows CI runs every Windows step with v2.0.0 and Python 3.11, and the
Windows tests and the isolated wheel installation with Python 3.15. No
physical Windows machine checks v2.0.0, as the Human maintainer decided on
2026-10-23. One physical Windows 11 x64 machine checked v2.0.0rc4; from it,
only the reading of JSON (v2.0.0rc5), the version, and the documents change.
The lines of the guides about the Python install manager on Windows follow the
python.org documentation and the source of the Python install manager 26.4,
read on 2026-10-23; they are not checked on a physical Windows machine.

The release source is `dce8b8aa36f4a99ef162bdbdcfd31e1f7e61ea6b` (#156). The
annotated `v2.0.0` tag (tag object
`d9ca58b4ec36df907fecb2bfb8cd85db24953ce5`), the latest stable GitHub Release
published on 2026-10-23 JST, Production PyPI publication through Trusted
Publishing/OIDC, and the publish workflow's exact-version PyPI install
verification are complete.

## v2.0.0rc5 release candidate

Version `2.0.0rc5`, the fifth release candidate of v2.0.0, is published on
TestPyPI only, for the checks of stage E before the stable release. It is
v2.0.0rc4 with the limit of the nesting of JSON (#152), the guides with the
answers to a second reading and to the physical Windows check of
v2.0.0rc4 (#150), and the CI with Python 3.15 on Linux, Windows, and
macOS (#151 and #153). Production PyPI and the latest GitHub Release stay
v1.7.1, and no GitHub Release was made for the release candidate.

From v2.0.0rc4, the package's Python changes in the version in `__init__.py`
and in the limit of the nesting of JSON: JSON nested more than 256 deep is
left out as a file that cannot be read, on every Python and operating
system. The files of the page and the pictures do not change:

```text
$ git diff --stat v2.0.0rc4 v2.0.0rc5 -- 'src/**/*.py'
 src/garmin_running_data_normalizer/__init__.py     |  2 +-
 .../common/json_depth.py                           | 35 ++++++++++++++++++++++
 src/garmin_running_data_normalizer/gui/outputs.py  |  4 ++-
 src/garmin_running_data_normalizer/gui/server.py   |  6 +++-
 src/garmin_running_data_normalizer/gui/settings.py |  2 ++
 .../intake/accounts.py                             |  2 ++
 .../intake/discovery.py                            | 22 +++++++++-----
 .../snapshot/merge.py                              |  4 +++
 .../snapshot/store.py                              |  3 ++
 9 files changed, 69 insertions(+), 11 deletions(-)
```

The Windows CI ran every Windows step with v2.0.0rc5 and Python 3.11, and with
Python 3.15 the tests of the GUI, the icon, the reading of the Export, and the
files that cannot be read, and the isolated wheel installation with a
Synthetic Run-All. The CI ran the whole test suite with Python 3.15 on Linux
and macOS as well. No physical Windows machine checks v2.0.0rc5, as the Human
maintainer decided on 2026-10-22: from v2.0.0rc4, only the reading of JSON
changes, and the Windows CI checks it.

The release source is `a701e60170baa5f9959be6dcb4f0e872bda9800f` (#154). The annotated `v2.0.0rc5` tag
(tag object `8aaa4e67b07885d8ebfe75e1de632ccb08f310ae`) points to it, so that the links of the GUI's help
panel open the documents of that tag. TestPyPI publication through Trusted
Publishing/OIDC on 2026-10-23 JST and the publish workflow's exact-version
TestPyPI install verification are complete.

The release source passed main CI run `39808774051` (Ubuntu `test`,
`windows-runtime`, and the three jobs of Python 3.15) and CodeQL
(`39808773191`). A build-only publish workflow run (`39809902427`) on the
release source passed with every upload job skipped. Publish workflow run
`39859727702` then built and validated the exact source and published to
TestPyPI; the PyPI jobs were skipped. The Sigstore transparency log (Rekor)
was read before the run and answered. The publication and the tag ran under
one Human approval given after their values were shown. The `testpypi`
Environment deployment was Human-authorized, and the approval was submitted
through the GitHub API on the Human's instruction.
`TESTPYPI_PUBLISH_APPROVED` was set to `true` for the publish run and
returned to `false` as soon as the run finished.

The SHA-256 checksums recorded by that run match TestPyPI: wheel
`297c832304bf6da43662d29a0fedd2f50fd8c62d3c12308156becdae6c646630` and source distribution `68c6a222ddc216a6bd28e0317427a9fc40c070c7768ad213ef5944c333f634c6`. Each file carries a
PEP 740 publish attestation from `publish-pypi.yml` of
`tsubotti63/garmin-running-data-normalizer` in the `testpypi` Environment,
through GitHub Trusted Publishing. The build-only run produced different
checksums because the distributions are not byte-reproducible across runs;
only the publish run's artifacts were published. The documents at the
`v2.0.0rc5` tag describe the installation from TestPyPI in the words used
before the publication.

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
[draft of the v2.0.0 migration notes](https://github.com/tsubotti63/garmin-running-data-normalizer/blob/v2.0.0rc1/docs/v2_migration_notes_draft.md) lists.
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
- Current source and package version: `2.3.0rc3`
- Current Production PyPI version: `2.2.1`
- Latest GitHub Release: `v2.2.1`
- GitHub Release: Public, non-prerelease, and marked latest
- PyPI packaging readiness: PASS on `main`
- TestPyPI `2.2.1`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `2.2.1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.2.0`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `2.2.0`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.1.0`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `2.1.0`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.1`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `2.0.1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `2.0.0`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `1.7.1`: Not used; the publish workflow's TestPyPI jobs were
  skipped
- Production PyPI `1.7.1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.3.0rc3`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.3.0rc2`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.3.0rc1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.2.1rc1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.2.0rc2`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.2.0rc1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.1.0rc1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.1rc1`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc5`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc4`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc3`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc2`: Published and exact-version install verified by the
  publish workflow
- TestPyPI `2.0.0rc1`: Published and exact-version install verified by the
  publish workflow
- Release candidate tags: `v2.3.0rc3`, `v2.3.0rc2`, `v2.3.0rc1`, `v2.2.1rc1`,
  `v2.2.0rc2`, `v2.2.0rc1`, `v2.1.0rc1`, `v2.0.1rc1`, `v2.0.0rc5`,
  `v2.0.0rc4`, `v2.0.0rc3`, `v2.0.0rc2`, and `v2.0.0rc1`, without a GitHub
  Release
- Trusted Publishing: Configured for protected `testpypi` and `pypi`
  Environments; target approval variables are disabled after use

The repository is public and under ongoing maintenance. Existing release tags
and GitHub Releases remain immutable. v2.2.1 is the current stable release;
v2.3.0rc3, v2.3.0rc2, v2.3.0rc1, v2.2.1rc1, v2.2.0rc2, v2.2.0rc1, v2.1.0rc1,
v2.0.1rc1, v2.0.0rc5, v2.0.0rc4, v2.0.0rc3, v2.0.0rc2, and v2.0.0rc1 are
release candidates on TestPyPI only; v2.2.0, v2.1.0, v2.0.1, v2.0.0, v1.7.1,
v1.7.0, v1.6.0, v1.5.0, v1.4.1, v1.4.0, and v1.3.3 are historical releases.
The v2.3.0rc3, v2.3.0rc2, v2.3.0rc1, v2.2.1rc1, v2.2.0rc2, v2.2.0rc1,
v2.1.0rc1, v2.0.1rc1, v2.0.0rc5, v2.0.0rc4, v2.0.0rc3, v2.0.0rc2, and
v2.0.0rc1 tag and TestPyPI publication evidence was recorded only after the
corresponding external state was observed.
The v2.2.1, v2.2.0, v2.1.0, v2.0.1, v2.0.0, v1.7.1, v1.7.0, v1.6.0, v1.5.0,
v1.4.1, v1.4.0, and v1.3.3 tag, GitHub Release, and Production PyPI
publication evidence was recorded only after the corresponding external state
was observed.

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

The v2.2.1 release source passed main CI run `42165559301` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `42165558489`. A build-only publish
workflow run (`42166931733`) on the release source passed with every upload
job skipped. Production publish workflow run `42168280803` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. In both runs, the
steps that stage W5 added to the publish workflow passed: the repository
checks, the page tests, and the checks of the files of the wheel and of the
source distribution after an isolated installation. Both runs used the
`ubuntu-26.04` runner image (20261101.186), Python 3.11.18, and Node.js
24.22.2: 1,713 tests passed and 14 were skipped, as on Ubuntu in the CI, and
290 page tests passed. The tag, the GitHub Release, and the Production
publication ran under one Human approval given after their values were shown.
The `pypi` Environment deployment was Human-authorized, and the approval was
submitted once through the GitHub API on the Human's instruction, after
`PYPI_PUBLISH_APPROVED` was returned to `false` once the approval gate of the
run had passed; it was accepted, and the deployment no longer waited.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`83e2304822ed214cabacf93b3d3f9d2ba6eca1473916975b6921628b1a835299` and source
distribution
`4adf6056d81591f8a165026cdc2e4688e77f4d381fb0ad8078415a56ee5cd93d`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` in the `pypi`
Environment. On Production PyPI, the wheel is 1,055,427 bytes, the size of the
wheel built from the release source on macOS before the publication, and the
source distribution is 1,618,433 bytes, 1,318 bytes smaller than that build
(1,619,751 bytes), as the distributions are built again in each run and are
not byte-reproducible. The build-only run produced different checksums for the
same reason; only the production run's artifacts were published.
`PYPI_PUBLISH_APPROVED` stayed `false` after the upload.

Before the tag and the GitHub Release were made, the installation was checked
on macOS, each check with a home folder of its own and synthetic data only. A
clean install from Production PyPI held the files of the release source,
completed the Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0) with the run
digest of the README figures, and its output passed `validate-handoff`,
`doctor --run-output`, and `support-bundle`. The macOS line of the GUI Guide,
run as written with `--no-browser` at its end, installed 2.2.1 from Production
PyPI, made the icon, and served the page, twice. An update from v2.2.0 was
checked too: the macOS line of the GUI Guide of v2.2.0 installed 2.2.0, whose
GUI remembered a theme and a mark and whose command line made a Snapshot
Store; the line of v2.2.1 then installed 2.2.1 into the same virtual
environment and made the icon again; the file of the icon, run by `/bin/sh`
with that home folder and without a browser, started 2.2.1 with the theme that
2.2.0 remembered, and 2.2.1 read the mark that 2.2.0 saved; the store was
verified by 2.2.1, and its files and those of the settings and the marks were
those of before the update. Opening the icon from the Finder after an update
was not checked, as the release notes say.

From v2.2.1, the publish workflow also runs the repository checks and the page
tests, and compares the page files, the catalogs, and the icons of each built
distribution with the source; after the publication it reads the page files
and the catalogs of what it installs from the index. It does not compare the
published files with what it built by their hashes, open the GUI, or read the
tag and the GitHub Release: the checks above did, after the run.

### v2.2.0 release assessment (historical)

The v2.2.0 release source passed main CI run `41823696700` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `41823696195`. A build-only publish
workflow run (`41829891373`) on the release source passed with every upload
job skipped. Production publish workflow run `41837445186` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The tag, the
GitHub Release, and the Production publication ran under one Human approval
given after their values were shown. The `pypi` Environment deployment was
Human-authorized, and the approval was submitted through the GitHub API on the
Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`bd9d3079bf732bdaa9c40cba41bd8709a13a4421cfdc3a1f721167d413a3b674` and source
distribution
`fa16960a49f0c6daf3e45d43207a6b98ebf2ac1b44201247b6c584aab8b00e00`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` in the `pypi`
Environment. The build-only run produced different checksums because the
distributions are not byte-reproducible across runs; only the production run's
artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to `false`
after the upload. A clean install from Production PyPI on macOS, with a home
folder of its own and synthetic data only, held the files of the tag,
completed the Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0) with the run
digest of the README figures, and its output passed `validate-handoff`,
`doctor --run-output`, and `support-bundle`. The macOS line of the GUI Guide,
run as written with `--no-browser` at its end, installed 2.2.0 from Production
PyPI, made the icon, and served the page, twice.

The publish workflow runs the Python tests, builds the distributions, and
checks that there is one wheel and one source distribution of the version,
their metadata, and the version and the command line of what it installs from
each; it does not run the tests of the pages or the public checks, and it does
not read the pages and catalogs from the distributions. The main CI run above
ran those on the release source, and the clean install above served the page;
running them in the publish workflow too is left for a release after v2.2.0.

### v2.1.0 release assessment (historical)

The v2.1.0 release source passed main CI run `40591156433` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `40591155986`. A build-only publish
workflow run (`40591514066`) on the release source passed with every upload
job skipped. Production publish workflow run `40599011436` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The tag, the
GitHub Release, and the Production publication ran under one Human approval
given after their values were shown. The `pypi` Environment deployment was
Human-authorized, and the approval was submitted through the GitHub API on the
Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`c9569a10afdf6501abcfe9da7eced5095b29b98fb9c2b9170137bdfe2305392d` and source
distribution
`c88d6935d2ca3a1058d51bd8eaec39f357c94610da145d8cc3d70f509092d309`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` in the `pypi`
Environment. The build-only run produced different checksums because the
distributions are not byte-reproducible across runs; only the production run's
artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to `false`
after the upload. A clean install from Production PyPI on macOS, with a home
folder of its own and synthetic data only, held the files of the tag,
completed the Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0) with the run
digest of the README figures, and its output passed `validate-handoff`,
`doctor --run-output`, and `support-bundle`. The macOS line of the GUI Guide,
run as written with `--no-browser` at its end, installed 2.1.0 from Production
PyPI, made the icon, and served the page, twice.

### v2.0.1 release assessment (historical)

The v2.0.1 release source passed main CI run `40332848244` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `40332848710`. A build-only publish
workflow run (`40333234269`) on the release source passed with every upload
job skipped. Production publish workflow run `40336421519` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The tag, the
GitHub Release, and the Production publication ran under one Human approval
given after their values were shown. The `pypi` Environment deployment was
Human-authorized, and the approval was submitted through the GitHub API on the
Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`599bb596e3b5140706cef27517af67cf03054cf758e6e7912c8f9574c946a0a2` and source
distribution
`24a33c7dc0cde0f6aa74e236747de6953e1f48a404bd69ec1b24229badcd64a1`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` in the `pypi`
Environment. The build-only run produced different checksums because the
distributions are not byte-reproducible across runs; only the production run's
artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to `false`
after the upload. A clean install from Production PyPI on macOS, with a home
folder of its own and synthetic data only, held the files of the tag,
completed the Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0) with the run
digest of the README figures, and its output passed `validate-handoff`,
`doctor --run-output`, and `support-bundle`. The macOS line of the GUI Guide,
run as written with `--no-browser` at its end, installed 2.0.1 from Production
PyPI, made the icon, and served the page, twice.

### v2.0.0 release assessment (historical)

The v2.0.0 release source passed main CI run `39970315509` (`test` and
`test-python-3-15` on Ubuntu, `macos-python-3-15`, and `windows-runtime` and
`windows-python-3-15`) and CodeQL run `39970316102`. A build-only publish
workflow run (`39971318269`) on the release source passed with every upload
job skipped. Production publish workflow run `39972408058` then built and
validated the exact source, published to Production PyPI, and verified the
exact-version PyPI install; the TestPyPI jobs were skipped. The tag, the
GitHub Release, and the Production publication ran under one Human approval
given after their values were shown. The `pypi` Environment deployment was
Human-authorized, and the approval was submitted through the GitHub API on the
Human's instruction.

The SHA-256 checksums recorded by that run match Production PyPI: wheel
`f1930acb05fd724b75f1766f5e137632d18b6f120dab848ceebffbc7054bbb24` and source
distribution
`3cf09a7e08dca2b58341c59706255017c017bbc3c1c8d16f71263e49e0a21428`. Each file
carries a PEP 740 publish attestation from `publish-pypi.yml` in the `pypi`
Environment. The build-only run produced different checksums because the
distributions are not byte-reproducible across runs; only the production run's
artifacts were published. `PYPI_PUBLISH_APPROVED` was returned to `false`
after the upload. A clean install from Production PyPI on macOS, with a home
folder of its own and synthetic data only, held the files of the tag,
completed the Synthetic Run-All (`PASS_WITH_WARNINGS`, exit 0) with the run
digest of the README figures, and its output passed `validate-handoff`,
`doctor --run-output`, and `support-bundle`. The macOS line of the GUI Guide,
run as written with `--no-browser` at its end, installed 2.0.0 from Production
PyPI, made the icon, and served the page, twice.

### v1.7.1 release assessment (historical)

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
