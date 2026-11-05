from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
# What the publish workflow runs before it builds, and what it checks in each built
# distribution and in each published version (stage W5 of v2.2.1), as it writes them.
REPOSITORY_CHECKS = (
    "validate_bootstrap",
    "validate_platform_alignment",
    "static_policy_scan",
    "validate_public_command_examples",
    "validate_public_product_state",
)
STANDALONE_FIRST = "import garmin_running_data_normalizer.standalone"
SAME_AS_SOURCE = """\
from importlib.resources import files
from pathlib import Path

from garmin_running_data_normalizer.gui.layouts import built_in_name_keys

installed = Path(str(files("garmin_running_data_normalizer"))).resolve()
source = Path("src/garmin_running_data_normalizer").resolve()
assert installed != source and source.is_dir(), installed
for folder in ("gui/static", "assets"):
    found, wanted = ({path.relative_to(root / folder).as_posix(): path.read_bytes() for path in (root / folder).rglob("*") if path.is_file()} for root in (installed, source))
    assert wanted and found == wanted, (folder, sorted(set(found) ^ set(wanted)) or sorted(name for name in wanted if found[name] != wanted[name]))
assert len(built_in_name_keys()) == 12
"""
PAGES_AND_CATALOGS = """\
import json
from importlib.resources import files

from garmin_running_data_normalizer.gui.layouts import built_in_name_keys
from garmin_running_data_normalizer.gui.server import STATIC_FILES, load_static_files

loaded = load_static_files()
assert loaded and len(loaded) == len(STATIC_FILES) and all(body for body, _ in loaded.values())
catalogs = files("garmin_running_data_normalizer.gui").joinpath("static").joinpath("i18n")
english, japanese = (json.loads(catalogs.joinpath(name).read_text(encoding="utf-8")) for name in ("en.json", "ja.json"))
assert english and english.keys() == japanese.keys()
assert all(isinstance(text, str) and text.strip() for text in (*english.values(), *japanese.values()))
assert len(built_in_name_keys()) == 12
"""


def _jobs(workflow: str) -> dict[str, str]:
    """The jobs of a workflow by name, each the text under its name (a name
    as GitHub takes it: a letter or _ first, then letters, digits, - or _)."""
    parts = re.split(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\n", workflow.split("\njobs:\n", 1)[1], flags=re.MULTILINE)
    return {parts[index]: parts[index + 1] for index in range(1, len(parts), 2)}


def _steps(job: str) -> list[str]:
    """The steps of a job, each the whole text of the step."""
    body = job.split("\n    steps:\n", 1)[1]
    return ["      - " + part for part in re.split(r"^      - ", body, flags=re.MULTILINE)[1:]]


def _step(job: str, head: str) -> str:
    """The one step of a job whose first line is head."""
    found = [step for step in _steps(job) if step.splitlines()[0] == head]
    assert len(found) == 1, (head, len(found))
    return found[0]


def _head(job: str) -> str:
    """What a job says before its steps (its name, needs, if, runs-on)."""
    return job.split("    steps:\n", 1)[0]


def _settings(step: str) -> str:
    """What a step says before its run block (its name, and env, if, shell)."""
    return step.split("        run: |\n", 1)[0]


def _run(step: str) -> list[str]:
    """The lines of the run block of a step, as the shell gets them."""
    lines = step.split("        run: |\n", 1)[1].splitlines()
    return [line[10:] if line.startswith(" " * 10) else line for line in lines]


def _indented(code: str) -> str:
    return "".join(("          " + line if line else "") + "\n" for line in code.splitlines())


class PyPIPublishWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_is_manual_and_build_only_by_default(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertNotRegex(
            self.workflow,
            re.compile(r"^  (push|pull_request|schedule):", re.MULTILINE),
        )
        self.assertRegex(
            self.workflow,
            re.compile(
                r"perform_upload:\n"
                r"(?:        .*\n)+?"
                r"        default: false\n",
                re.MULTILINE,
            ),
        )

    def test_upload_requires_target_specific_approval_and_environment(self) -> None:
        self.assertIn("vars.PYPI_PUBLISH_APPROVED", self.workflow)
        self.assertIn("vars.TESTPYPI_PUBLISH_APPROVED", self.workflow)
        self.assertIn("name: pypi", self.workflow)
        self.assertIn("name: testpypi", self.workflow)
        self.assertEqual(self.workflow.count("id-token: write"), 2)
        self.assertIn("needs:\n      - build\n      - approval-gate", self.workflow)

    def test_upload_requires_reviewed_main_workflow_definition(self) -> None:
        self.assertIn("WORKFLOW_GIT_REF: ${{ github.ref }}", self.workflow)
        self.assertIn("WORKFLOW_REF: ${{ github.workflow_ref }}", self.workflow)
        self.assertIn(
            'test "$WORKFLOW_GIT_REF" = "refs/heads/main"',
            self.workflow,
        )
        self.assertIn(
            'test "$WORKFLOW_REF" = '
            '"tsubotti63/garmin-running-data-normalizer/'
            '.github/workflows/publish-pypi.yml@refs/heads/main"',
            self.workflow,
        )

    def test_source_and_version_are_checked_before_upload(self) -> None:
        self.assertIn(
            'if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then',
            self.workflow,
        )
        self.assertIn('test "$WORKFLOW_GIT_REF" = "refs/heads/main"', self.workflow)
        self.assertIn(
            'test "$WORKFLOW_REF" = '
            '"tsubotti63/garmin-running-data-normalizer/'
            '.github/workflows/publish-pypi.yml@refs/heads/main"',
            self.workflow,
        )
        self.assertIn('test "$WORKFLOW_SHA" = "$SOURCE_SHA"', self.workflow)
        self.assertIn('test "$(git rev-parse HEAD)" = "$WORKFLOW_SHA"', self.workflow)
        self.assertIn("parse_wheel_filename", self.workflow)
        self.assertIn("parse_sdist_filename", self.workflow)
        self.assertIn("python -m twine check --strict dist/*", self.workflow)
        self.assertIn("sha256sum dist/*", self.workflow)

    def test_build_executes_only_the_trusted_dispatch_sha(self) -> None:
        self.assertIn("ref: ${{ github.sha }}", self.workflow)
        self.assertNotRegex(
            self.workflow,
            re.compile(r"^\s+ref:\s*\$\{\{\s*inputs\.", re.MULTILINE),
        )
        self.assertIn("WORKFLOW_GIT_REF: ${{ github.ref }}", self.workflow)
        self.assertIn("WORKFLOW_REF: ${{ github.workflow_ref }}", self.workflow)
        self.assertIn("WORKFLOW_SHA: ${{ github.sha }}", self.workflow)
        dispatch_verification = self.workflow.index("- name: Verify trusted dispatch source")
        checkout = self.workflow.index("- uses: actions/checkout@")
        identity_verification = self.workflow.index("- name: Verify checked-out source identity")
        repository_execution = self.workflow.index("- name: Install validation tooling")
        self.assertLess(dispatch_verification, checkout)
        self.assertLess(checkout, identity_verification)
        self.assertLess(identity_verification, repository_execution)

    def test_ci_declares_least_privilege_permissions(self) -> None:
        self.assertRegex(
            self.ci_workflow,
            re.compile(r"^permissions:\n  contents: read$", re.MULTILINE),
        )

    def test_workflow_uses_oidc_without_repository_credentials(self) -> None:
        self.assertNotIn("secrets.", self.workflow)
        self.assertNotIn("twine upload", self.workflow)
        self.assertNotIn("skip-existing", self.workflow)
        self.assertNotIn(".pypirc", self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)
        self.assertEqual(
            self.workflow.count(
                "pypa/gh-action-pypi-publish@"
                "ba38be9e461d3875417946c167d0b5f3d385a247"
            ),
            2,
        )

    def test_all_actions_are_pinned_to_commit_shas(self) -> None:
        uses = re.findall(r"^\s+- uses: ([^ ]+)", self.workflow, re.MULTILINE)

        self.assertGreater(len(uses), 0)
        for action in uses:
            self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")

    def test_post_publication_install_checks_both_indexes(self) -> None:
        self.assertIn("--index-url https://test.pypi.org/simple/", self.workflow)
        self.assertIn(
            '"garmin-running-data-normalizer==$EXPECTED_VERSION"', self.workflow
        )
        self.assertEqual(
            self.workflow.count(
                "m.version('garmin-running-data-normalizer') == p.__version__"
            ),
            4,
        )
        self.assertEqual(
            self.workflow.count("garmin-running-data-normalizer --version"),
            4,
        )

    def test_the_workflow_never_lets_a_failure_pass(self) -> None:
        # A step that goes on after a failure would publish what failed a
        # check (stage W5 of v2.2.1). An "||" that stops (the approval gate's
        # "esac || { ...; exit 1; }") is fine.
        self.assertNotIn("continue-on-error", self.workflow)
        self.assertNotRegex(self.workflow, re.compile(r"\bset \+e\b"))
        self.assertNotRegex(
            self.workflow,
            re.compile(r"\|\|\s*(?:true|:|exit\s+0)(?=\s|;|\)|$)", re.MULTILINE),
        )
        # Nor a condition on a step, or a shell other than the default one,
        # which stops at the first command that fails.
        self.assertNotRegex(self.workflow, re.compile(r"^        if:", re.MULTILINE))
        self.assertNotRegex(self.workflow, re.compile(r"^\s*(?:shell|defaults):", re.MULTILINE))

    def test_the_build_runs_the_repository_checks_and_the_page_tests_before_it_builds(self) -> None:
        # As the usual CI does, after the tests and before the distributions
        # are built, with no condition; the version of Node is printed for
        # the record (stage W5 of v2.2.1). The jobs are the six of the
        # publication, so that no check can move to a job of its own.
        self.assertEqual(
            list(_jobs(self.workflow)),
            ["build", "approval-gate", "publish-testpypi", "verify-testpypi", "publish-pypi", "verify-pypi"],
        )
        build = _jobs(self.workflow)["build"]
        self.assertEqual(_head(build), "    name: Build and validate exact source\n    runs-on: ubuntu-latest\n")
        heads = [step.splitlines()[0] for step in _steps(build)]
        start = heads.index("      - name: Run synthetic regression tests")
        self.assertEqual(
            heads[start : start + 4],
            [
                "      - name: Run synthetic regression tests",
                "      - name: Run repository checks",
                "      - name: Run page tests",
                "      - name: Build wheel and source distribution",
            ],
        )
        self.assertEqual(
            _step(build, "      - name: Run repository checks"),
            "      - name: Run repository checks\n        run: |\n"
            + "".join(f"          python scripts/{name}.py\n" for name in REPOSITORY_CHECKS),
        )
        self.assertEqual(
            _step(build, "      - name: Run page tests"),
            "      - name: Run page tests\n        run: |\n"
            "          node --version\n          node --test tests/gui_js/*.test.mjs\n",
        )

    def test_each_built_distribution_holds_the_files_of_the_source(self) -> None:
        # In its own environment, by its own python with -I (never the python
        # that the tests installed from the source): standalone is the first
        # module imported, the page files, the catalogs, and the icons are those
        # of the source byte for byte, and the built-in layout names are read
        # (stage W5 of v2.2.1).
        build = _jobs(self.workflow)["build"]
        for head, place in (
            ("      - name: Verify isolated wheel installation", "/tmp/garmin-normalizer-wheel"),
            ("      - name: Verify isolated source distribution installation", "/tmp/garmin-normalizer-sdist"),
        ):
            with self.subTest(step=head):
                step = _step(build, head)
                self.assertEqual(_settings(step), head + "\n")
                run = _run(step)
                end = run.index(f"{place}/bin/garmin-running-data-normalizer --version")
                self.assertEqual(
                    run[end + 1 :],
                    [
                        f'{place}/bin/python -I -c "{STANDALONE_FIRST}"',
                        f"{place}/bin/python -I - <<'PY'",
                        *SAME_AS_SOURCE.splitlines(),
                        "PY",
                    ],
                )
        self.assertEqual(self.workflow.count(_indented(SAME_AS_SOURCE)), 2)

    def test_each_published_version_reads_its_pages_and_catalogs(self) -> None:
        # The distribution that pip installs from the index (normally the
        # wheel), by python -I: standalone is the first module imported, every
        # page file that the server serves is there and not empty, both
        # catalogs have the same keys and no empty message, and the built-in
        # layout names are read (stage W5 of v2.2.1).
        jobs = _jobs(self.workflow)
        for job, head, job_head in (
            (
                "verify-testpypi",
                "      - name: Install and exercise the exact TestPyPI version",
                "    name: Verify TestPyPI publication\n    needs: publish-testpypi\n    runs-on: ubuntu-latest\n",
            ),
            (
                "verify-pypi",
                "      - name: Install and exercise the exact PyPI version",
                "    name: Verify PyPI publication\n    needs: publish-pypi\n    runs-on: ubuntu-latest\n",
            ),
        ):
            with self.subTest(job=job):
                # The job itself runs after its upload with no condition of
                # its own, which would skip the checks and still end well.
                self.assertEqual(_head(jobs[job]), job_head)
                step = _step(jobs[job], head)
                self.assertEqual(
                    _settings(step),
                    head + "\n        env:\n          EXPECTED_VERSION: ${{ inputs.expected_version }}\n",
                )
                run = _run(step)
                end = run.index("garmin-running-data-normalizer --version")
                self.assertEqual(
                    [line for line in run[end + 1 :] if line],
                    [
                        f'python -I -c "{STANDALONE_FIRST}"',
                        "python -I - <<'PY'",
                        *[line for line in PAGES_AND_CATALOGS.splitlines() if line],
                        "PY",
                    ],
                )
        self.assertEqual(self.workflow.count(_indented(PAGES_AND_CATALOGS)), 2)


if __name__ == "__main__":
    unittest.main()
