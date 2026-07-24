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
        self.assertEqual(project["version"], "1.1.1")
        self.assertEqual(project["version"], __version__)
        self.assertEqual(project["license"], "Apache-2.0")
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["dependencies"], [])
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


if __name__ == "__main__":
    unittest.main()
