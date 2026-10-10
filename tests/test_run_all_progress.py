from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer import run_all as run_all_module
from garmin_running_data_normalizer.fit.parser import parse_fit_export
from garmin_running_data_normalizer.run_all import (
    PROGRESS_STAGES,
    PROGRESS_STEPS,
    RunAllError,
    run_all,
)
from tests.fit_fixture_factory import synthetic_fit


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
RUNNING_DYNAMICS = (843, 3698, 2421, 789, 4884, 10656)


class Stop(BaseException):
    """Stands in for a stop that must pass through Run-All's error handling."""


def export_with_fit(root: Path) -> Path:
    """Copy the synthetic Export and add four FIT files with three contents."""
    export = root / "export"
    shutil.copytree(SYNTHETIC_EXPORT, export)
    uploaded = export / "DI-Connect-Uploaded-Files"
    uploaded.mkdir()
    first = synthetic_fit()
    (uploaded / "synthetic_1.fit").write_bytes(first)
    (uploaded / "synthetic_1_copy.fit").write_bytes(first)
    (uploaded / "synthetic_2.fit").write_bytes(synthetic_fit(sessions=2))
    (uploaded / "synthetic_3.fit").write_bytes(
        synthetic_fit(
            session_running_dynamics=RUNNING_DYNAMICS,
            lap_running_dynamics=RUNNING_DYNAMICS,
        )
    )
    return export


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def staging_folders(output: Path) -> list[Path]:
    return sorted(output.parent.glob(f".{output.name}.run-all-*"))


class RunAllProgressTest(unittest.TestCase):
    def test_output_is_identical_with_and_without_progress(self) -> None:
        options = {
            "default": {},
            "external-safe-pack": {"external_safe_pack": True},
            "timezone": {"timezone_name": "UTC"},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {"synthetic": SYNTHETIC_EXPORT, "fit": export_with_fit(root)}
            for export_name, export in exports.items():
                for option_name, option in options.items():
                    with self.subTest(export=export_name, option=option_name):
                        plain = root / f"{export_name}-{option_name}-plain"
                        followed = root / f"{export_name}-{option_name}-followed"
                        events: list[dict[str, Any]] = []
                        first = run_all(export, plain, **option)
                        second = run_all(export, followed, progress=events.append, **option)
                        self.assertEqual(first, second)
                        self.assertEqual(tree_bytes(plain), tree_bytes(followed))
                        self.assertTrue(events)

    def test_events_follow_the_run_and_count_distinct_fit_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events: list[dict[str, Any]] = []
            run_all(export_with_fit(root), root / "output", progress=events.append)
        self.assertEqual(
            events,
            [
                {"stage": "discovering"},
                {"stage": "normalizing", "step": "activities"},
                {"stage": "normalizing", "step": "fit"},
                {"stage": "reading_fit", "done": 0, "total": 3},
                {"stage": "reading_fit", "done": 1, "total": 3},
                {"stage": "reading_fit", "done": 2, "total": 3},
                {"stage": "reading_fit", "done": 3, "total": 3},
                {"stage": "normalizing", "step": "performance_metrics"},
                {"stage": "normalizing", "step": "daily_metrics"},
                {"stage": "normalizing", "step": "relationships"},
                {"stage": "verifying_input"},
                {"stage": "building_output"},
                {"stage": "writing_output"},
            ],
        )

    def test_events_carry_only_stage_names_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events: list[dict[str, Any]] = []
            run_all(export_with_fit(root), root / "output", progress=events.append)
        self.assertEqual(
            {event["stage"] for event in events} - {"normalizing"},
            set(PROGRESS_STAGES) - {"normalizing"},
        )
        for event in events:
            with self.subTest(event=event):
                self.assertIn(event["stage"], PROGRESS_STAGES)
                if event["stage"] == "normalizing":
                    self.assertEqual(set(event), {"stage", "step"})
                    self.assertIn(event["step"], PROGRESS_STEPS)
                elif event["stage"] == "reading_fit":
                    self.assertEqual(set(event), {"stage", "done", "total"})
                    self.assertIs(type(event["done"]), int)
                    self.assertIs(type(event["total"]), int)
                    self.assertLessEqual(0, event["done"])
                    self.assertLessEqual(event["done"], event["total"])
                else:
                    self.assertEqual(set(event), {"stage"})

    def test_parse_fit_export_counts_files_with_distinct_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            export = export_with_fit(Path(directory))
            events: list[dict[str, Any]] = []
            followed = parse_fit_export(export, progress=events.append)
            plain = parse_fit_export(export)
        self.assertEqual(followed, plain)
        self.assertEqual(
            events,
            [{"stage": "reading_fit", "done": done, "total": 3} for done in range(4)],
        )

    def test_an_exception_from_the_callback_ends_the_run_without_output(self) -> None:
        # While FIT files are read, Run-All reports any failure as a FIT
        # failure; elsewhere the callback's exception passes through.
        cases = (
            ({"stage": "discovering"}, None),
            ({"stage": "normalizing", "step": "activities"}, None),
            ({"stage": "reading_fit", "done": 1, "total": 3}, "FIT_PROCESSING_FAILED"),
            ({"stage": "verifying_input"}, None),
            ({"stage": "writing_output"}, None),
        )
        for failing_event, code in cases:
            with self.subTest(event=failing_event), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "output"

                def failing(event: dict[str, Any]) -> None:
                    if event == failing_event:
                        raise RuntimeError("callback failure")

                expected = RunAllError if code else RuntimeError
                with self.assertRaises(expected) as caught:
                    run_all(export_with_fit(root), output, progress=failing)
                if code:
                    self.assertEqual(caught.exception.code, code)
                self.assertFalse(output.exists())
                self.assertEqual(staging_folders(output), [])

    def test_a_base_exception_from_the_callback_passes_through(self) -> None:
        for stage in ("reading_fit", "verifying_input", "writing_output"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "output"

                def stop(event: dict[str, Any]) -> None:
                    if event["stage"] == stage:
                        raise Stop

                with self.assertRaises(Stop):
                    run_all(export_with_fit(root), output, progress=stop)
                self.assertFalse(output.exists())
                self.assertEqual(staging_folders(output), [])

    def test_a_stop_while_writing_leaves_no_output_or_staging_folder(self) -> None:
        real_write = run_all_module._write_exclusive
        written: list[str] = []

        def write_then_stop(root: Path, relative: str, data: bytes) -> None:
            if len(written) == 2:
                raise KeyboardInterrupt
            written.append(relative)
            real_write(root, relative, data)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            with patch.object(run_all_module, "_write_exclusive", write_then_stop):
                with self.assertRaises(KeyboardInterrupt):
                    run_all(SYNTHETIC_EXPORT, output)
            self.assertEqual(len(written), 2)
            self.assertFalse(output.exists())
            self.assertEqual(staging_folders(output), [])


if __name__ == "__main__":
    unittest.main()
