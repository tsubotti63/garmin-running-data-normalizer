from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

from garmin_running_data_normalizer import __version__


ROOT = Path(__file__).resolve().parents[1]


class PackagingReadinessTest(unittest.TestCase):
    def test_distribution_metadata_matches_stable_identity(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = metadata["project"]

        self.assertEqual(project["name"], "garmin-running-data-normalizer")
        self.assertNotIn("version", project)
        self.assertEqual(project["dynamic"], ["version"])
        self.assertEqual(__version__, "1.3.2")
        self.assertEqual(
            metadata["tool"]["setuptools"]["dynamic"]["version"],
            {"attr": "garmin_running_data_normalizer.__version__"},
        )
        self.assertEqual(project["license"], "Apache-2.0")
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(
            project["dependencies"],
            ["tzdata; platform_system == 'Windows'"],
        )
        self.assertIn(
            "Development Status :: 5 - Production/Stable",
            project["classifiers"],
        )
        self.assertEqual(
            project["scripts"]["garmin-running-data-normalizer"],
            "garmin_running_data_normalizer.runner:main",
        )
        self.assertEqual(
            project["optional-dependencies"]["release"],
            ["build>=1.2,<2", "twine>=6,<7"],
        )

    def test_readme_links_are_absolute_for_pypi_rendering(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        targets = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)

        self.assertGreater(len(targets), 0)
        self.assertEqual(
            [target for target in targets if not target.startswith(("https://", "#"))],
            [],
        )

    def test_build_outputs_are_ignored(self) -> None:
        entries = set((ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
        self.assertTrue({"build/", "dist/", "*.egg-info/"}.issubset(entries))

    def test_windows_ci_runs_packaged_synthetic_flows(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertIn("windows-runtime:", workflow)
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn(
            "workspace/windows-wheel-run-all/run_summary.json",
            workflow,
        )
        self.assertIn(
            "workspace/windows-sdist-run-all/run_summary.json",
            workflow,
        )
        self.assertEqual(workflow.count("assert s['status'] == 'PASS_WITH_WARNINGS'"), 3)


if __name__ == "__main__":
    unittest.main()
