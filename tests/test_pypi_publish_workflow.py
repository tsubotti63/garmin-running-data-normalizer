from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"


class PyPIPublishWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

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
        self.assertIn('test "$(git rev-parse HEAD)" = "$SOURCE_SHA"', self.workflow)
        self.assertIn("parse_wheel_filename", self.workflow)
        self.assertIn("parse_sdist_filename", self.workflow)
        self.assertIn("python -m twine check --strict dist/*", self.workflow)
        self.assertIn("sha256sum dist/*", self.workflow)

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


if __name__ == "__main__":
    unittest.main()
