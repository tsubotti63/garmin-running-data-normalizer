from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

from garmin_running_data_normalizer import __version__


ROOT = Path(__file__).resolve().parents[1]


class PackagingReadinessTest(unittest.TestCase):
    def test_distribution_metadata_matches_candidate_identity(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = metadata["project"]

        self.assertEqual(project["name"], "garmin-running-data-normalizer")
        self.assertNotIn("version", project)
        self.assertEqual(project["dynamic"], ["version"])
        self.assertEqual(__version__, "2.0.0rc5")
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

    def test_ci_runs_the_newest_python_too(self) -> None:
        # python.org gives the newest Python to a first-time user, so jobs
        # run with Python 3.15 on Linux and Windows (stage E2c) and on macOS
        # (stage E2c2) besides the jobs of 3.11, which keep their names, since
        # the ruleset requires them. Twine stays with the jobs of 3.11: its
        # dependencies may have no wheels for a new Python yet.
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        parts = re.split(r"^  ([a-z0-9-]+):\n", workflow.split("\njobs:\n", 1)[1], flags=re.M)
        jobs = dict(zip(parts[1::2], parts[2::2]))
        versions = {name: re.findall(r'python-version: "([0-9.]+)"', body) for name, body in jobs.items()}
        self.assertEqual(
            versions,
            {
                "test": ["3.11"],
                "test-python-3-15": ["3.15"],
                "macos-python-3-15": ["3.15"],
                "windows-runtime": ["3.11"],
                "windows-python-3-15": ["3.15"],
            },
        )
        self.assertIn("runs-on: macos-latest", jobs["macos-python-3-15"])
        for name in ("test-python-3-15", "macos-python-3-15", "windows-python-3-15"):
            with self.subTest(job=name):
                self.assertIn("-m pytest", jobs[name])
                self.assertIn("-m build", jobs[name])
                self.assertIn("load_static_files", jobs[name])
                self.assertNotIn("-m twine", jobs[name])
                self.assertNotIn("release]", jobs[name])

    def test_windows_ci_steps_stop_at_any_failed_command(self) -> None:
        # A multi-line PowerShell step fails only on the exit code of its last
        # command, so every command line needs its own check. Only variable
        # assignments, comments, and the checks themselves are not commands.
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = workflow.split("\n  windows-runtime:\n", 1)[1]
        check = "if ($LASTEXITCODE -ne 0) { throw "
        multi_line_steps = 0
        commands = 0
        for step in job.split("\n      - ")[1:]:
            if "\n        run: |\n" not in step:
                continue
            multi_line_steps += 1
            block = step.split("\n        run: |\n", 1)[1].splitlines()
            lines = [line.strip() for line in block if line.startswith("          ")]
            for index, line in enumerate(lines):
                if line.startswith(("$", "#", "if (")):
                    continue
                commands += 1
                with self.subTest(command=line[:80]):
                    self.assertLess(index + 1, len(lines))
                    self.assertTrue(lines[index + 1].startswith(check))
        self.assertGreaterEqual(multi_line_steps, 6)
        self.assertGreaterEqual(commands, 32)


if __name__ == "__main__":
    unittest.main()
