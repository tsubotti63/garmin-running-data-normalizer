# P1 PyPI Publication Runbook v1.0

## Status and authority

- Status: `P1_READY_FOR_APPROVAL`
- Distribution: `garmin-running-data-normalizer`
- Current package version: `1.0.0`
- Recommended authentication: PyPI Trusted Publishing through GitHub Actions
- TestPyPI/PyPI upload: not authorized and not performed
- Publisher, repository variable, and GitHub Environment configuration: not
  authorized and not performed
- Tag or GitHub Release creation/change: not authorized and not performed

This runbook defines a repeatable publication path. It does not grant
publication authority. Every initial index upload, publisher/configuration
change, tag, and GitHub Release operation remains a separate Product decision.

## Current verified snapshot

At P1 intake on 2026-07-23:

- `main` and `origin/main` were
  `29f1b0b811ae9657dd8a94c70c31e12ec1643437`;
- `bootstrap-ci` run `29987671951` completed with `success`;
- the existing annotated `v1.0.0` tag still peeled to
  `605eaba4106c3dbc040bda1ff06ccbba6e6b69e1`;
- the public `v1.0.0` GitHub Release remained latest, non-draft, and
  non-prerelease;
- PyPI and TestPyPI returned HTTP 404 for the normalized project JSON endpoint;
  and
- the GitHub repository had no configured Environments.

HTTP 404 is only a point-in-time observation. A pending Trusted Publisher does
not reserve a project name before its first successful upload.

## Publication workflow contract

`.github/workflows/publish-pypi.yml` is manual-only. A push, pull request, tag,
or schedule cannot start it.

The workflow requires:

1. a full reviewed 40-character `source_sha`;
2. an exact `expected_version`;
3. the selected `testpypi` or `pypi` target; and
4. an explicit `perform_upload` boolean.

The default is build-only. In build-only mode it checks out the exact SHA,
verifies the clean source identity, runs all synthetic tests, builds one wheel
and one source distribution, applies strict Twine checks, confirms the expected
version, installs both artifacts in isolated environments, records SHA-256
values, and retains the workflow artifact for one day.

An upload additionally requires all of the following:

- `perform_upload=true`;
- the workflow definition is dispatched from `main` and its full
  `github.workflow_ref` matches the reviewed repository path on
  `refs/heads/main`;
- the target-specific repository variable equals `true`;
- the matching GitHub Environment is entered; and
- its required Human reviewer approves the deployment.

| Target | Approval variable | Environment | Pending publisher workflow |
|---|---|---|---|
| TestPyPI | `TESTPYPI_PUBLISH_APPROVED` | `testpypi` | `publish-pypi.yml` |
| PyPI | `PYPI_PUBLISH_APPROVED` | `pypi` | `publish-pypi.yml` |

The upload jobs have only `id-token: write`, download the artifact produced by
the separate build job, and use a commit-pinned PyPA publishing action. No
password, API token, `.pypirc`, or repository secret is used. Successful upload
is followed by a clean index install, metadata/library version comparison, and
console-entry-point execution.

## Required Product decisions

### 1. First index version and source

The Product owner must select one exact version and immutable source before
publisher configuration or upload.

| Option | Benefit | Cost or risk | Recommendation |
|---|---|---|---|
| Publish `1.0.0` from the existing `v1.0.0` tag | Exact GitHub tag alignment | Predates the P0 PyPI-safe README and publication gate | Not recommended |
| Publish `1.0.0` from post-P0 `main` | Includes P0 packaging improvements | PyPI `1.0.0` artifacts would not correspond to the published `v1.0.0` tag | Not recommended |
| Prepare a reviewed `1.0.1` patch from post-P0 `main` | Preserves release identity and includes the packaging gate | Requires version update, review, CI, new tag, and GitHub Release approval | Recommended |

No option is selected by P1. If `1.0.1` is approved, update all authoritative
version declarations and exact-version tests together, run the complete Target
review gate, create a new immutable tag only after approval, and use its peeled
commit as `source_sha`.

### 2. TestPyPI rehearsal

Recommended: require a TestPyPI first upload and successful post-upload install
before authorizing production PyPI. TestPyPI is a separate service and account;
its project and publisher do not authorize production PyPI.

### 3. Authentication

Recommended: Trusted Publishing. It uses short-lived OIDC credentials and
avoids storing a long-lived PyPI token in GitHub. API Token publication is a
fallback only and requires a separately reviewed credential-handling plan;
this repository intentionally contains no token path.

### 4. Irreversible upload

TestPyPI and PyPI each need an explicit Product approval naming:

- target index;
- distribution name and version;
- full source commit SHA;
- expected wheel and sdist filenames/hashes;
- approved workflow run;
- authentication method; and
- authorization to set the target approval variable to `true` for that run.

## Trusted Publishing setup after approval

Perform these external changes only after the matching Product approval:

1. Create GitHub Environments `testpypi` and `pypi`.
2. Require the Human owner as a deployment reviewer for both. Production
   approval is mandatory; this project also requires it for TestPyPI.
3. Restrict the deployment branches/tags for both Environments to selected
   branches, with `main` as the only allowed branch and no allowed tag.
4. Create a pending publisher separately on TestPyPI and PyPI using:
   - PyPI project name: `garmin-running-data-normalizer`
   - GitHub owner: `tsubotti63`
   - GitHub repository: `garmin-running-data-normalizer`
   - workflow: `publish-pypi.yml`
   - environment: `testpypi` or `pypi`
5. Do not treat the pending publisher as a name reservation.
6. Set only the selected target approval variable to `true` immediately before
   the approved upload. Return it to `false` after the run.

If any owner, repository, workflow, environment, project name, source SHA,
version, or artifact hash differs, stop without uploading.

## Build-only rehearsal

After this workflow is merged and CI passes, a reversible build-only run may be
started from the `main` workflow ref with:

- the reviewed source commit SHA;
- its expected version;
- either target label; and
- `perform_upload=false`.

Expected result:

- build job `PASS`;
- approval and publish jobs skipped;
- one wheel and one sdist in the one-day workflow artifact;
- logged SHA-256 values; and
- no PyPI/TestPyPI project creation or upload.

## Approved TestPyPI execution

Only after Product approves TestPyPI upload and its external configuration:

1. Confirm the selected version is absent from TestPyPI.
2. Confirm the exact source SHA, CI, review verdict, tag policy, and clean
   worktree.
3. Enable `TESTPYPI_PUBLISH_APPROVED=true`.
4. Select branch `main` in the workflow dispatch UI, then dispatch with target
   `testpypi` and `perform_upload=true`.
5. Approve the `testpypi` Environment deployment.
6. Record the workflow/run/job IDs, artifact digest, published file hashes,
   project URL, upload time, and post-upload install result.
7. Return `TESTPYPI_PUBLISH_APPROVED=false`.
8. Do not proceed to PyPI unless TestPyPI verification passed and production
   upload received its own approval.

## Approved production PyPI execution

Only after Product approves the production upload:

1. Confirm the exact version remains absent from PyPI.
2. Confirm the TestPyPI evidence if rehearsal was required.
3. Confirm the source SHA, reviewed tag/release plan, CI, exact filenames and
   hashes, license, README, and public/private scan.
4. Enable `PYPI_PUBLISH_APPROVED=true`.
5. Select branch `main` in the workflow dispatch UI, then dispatch with target
   `pypi` and `perform_upload=true`.
6. Approve the `pypi` Environment deployment.
7. Record the workflow/run/job IDs, artifact digest, attestations, published
   file hashes, project URL, upload time, and post-upload install result.
8. Return `PYPI_PUBLISH_APPROVED=false`.
9. Update current-state documentation in a separate reviewed closeout commit;
   do not move the published tag.

## Post-publication verification

For the selected index verify:

- project page and JSON API are reachable;
- normalized name and exact version are correct;
- wheel and sdist both exist and their SHA-256 values match the approved run;
- license, `Requires-Python`, project URLs, and README render correctly;
- a clean Python 3.11 environment installs the exact version with `--no-deps`;
- installed metadata equals `garmin_running_data_normalizer.__version__`;
- `garmin-running-data-normalizer --version` succeeds;
- no extra release file, credential, private data, or generated personal output
  was published; and
- repository HEAD, tag, GitHub Release, and package-index state are recorded as
  distinct facts.

## Failure handling

- Before upload: stop and discard the workflow artifact; do not weaken checks.
- Upload rejected: record the error and stop; do not use `skip-existing`.
- Partial or incorrect publication: stop. Do not delete, replace, or re-upload
  without a new Product decision.
- Broken published release: prefer an explicitly reasoned yank and a reviewed
  patch release. Yanking and deletion are separate Human decisions.
- Never reuse a published version for changed files.

## Official references

- <https://packaging.python.org/en/latest/flow/>
- <https://packaging.python.org/en/latest/guides/using-testpypi/>
- <https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/>
- <https://packaging.python.org/en/latest/guides/tool-recommendations/>
- <https://docs.pypi.org/trusted-publishers/>
- <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>
- <https://docs.pypi.org/project-management/yanking/>
