from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.gui.runs import (
    RunActiveError,
    RunManager,
    RunRequestError,
)
from garmin_running_data_normalizer.standalone import validate_standalone_handoff
from tests.fit_fixture_factory import synthetic_fit
from tests.test_run_all_progress import export_with_fit, tree_bytes


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
STUB = Path(__file__).with_name("gui_stub_worker.py")
WORKER = "garmin_running_data_normalizer.gui.run_worker"
PRIVATE_TEXT = "/path/to/private"


def child_environment() -> dict[str, str]:
    """Let child processes import the package from this checkout."""
    paths = [str(ROOT / "src"), str(ROOT)]
    if os.environ.get("PYTHONPATH"):
        paths.append(os.environ["PYTHONPATH"])
    return {**os.environ, "PYTHONPATH": os.pathsep.join(paths)}


def wait_until(condition: Callable[[], bool], timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def stub_manager(mode: str, **options: float) -> RunManager:
    return RunManager(
        command_prefix=[sys.executable, "-P", str(STUB), f"--mode={mode}"],
        **options,
    )


def request(input_path: Path, parent: Path, name: str = "output", **extra: Any) -> dict[str, Any]:
    return {
        "input": str(input_path),
        "output_parent": str(parent),
        "output_name": name,
        "timezone": "Asia/Tokyo",
        **extra,
    }


def run_worker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-P", "-m", WORKER, *args],
        capture_output=True,
        text=True,
        env=child_environment(),
        timeout=120,
    )


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "garmin_running_data_normalizer", "run-all", *args],
        capture_output=True,
        text=True,
        env=child_environment(),
        timeout=120,
    )


class RunWorkerTest(unittest.TestCase):
    def test_worker_reports_progress_and_the_result_as_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            completed = run_worker(f"--input={SYNTHETIC_EXPORT}", f"--output={output}")
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(completed.stderr, "")
            messages = [json.loads(line) for line in completed.stdout.splitlines()]
            self.assertTrue(output.is_dir())
        self.assertEqual(messages[0], {"event": "progress", "stage": "discovering"})
        self.assertTrue(all(message["event"] == "progress" for message in messages[:-1]))
        result = messages[-1]
        self.assertEqual(result["event"], "finished")
        self.assertEqual((result["status"], result["exit_code"]), ("PASS_WITH_WARNINGS", 0))
        self.assertEqual(result["families"]["activities"]["processed_asset_count"], 1)
        self.assertNotIn(str(SYNTHETIC_EXPORT), completed.stdout)

    def test_worker_output_matches_the_cli(self) -> None:
        options = {"default": [], "pack": ["--external-safe-pack"], "timezone": ["--timezone=UTC"]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exports = {"synthetic": SYNTHETIC_EXPORT, "fit": export_with_fit(root)}
            for export_name, export in exports.items():
                for option_name, option in options.items():
                    with self.subTest(export=export_name, option=option_name):
                        gui_output = root / f"{export_name}-{option_name}-gui"
                        cli_output = root / f"{export_name}-{option_name}-cli"
                        gui = run_worker(f"--input={export}", f"--output={gui_output}", *option)
                        cli = run_cli("--input", str(export), "--output", str(cli_output), *option)
                        self.assertEqual(gui.returncode, cli.returncode)
                        self.assertEqual(tree_bytes(gui_output), tree_bytes(cli_output))

    def test_worker_reports_run_all_errors_as_codes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = run_worker(f"--input={root / 'missing'}", f"--output={root / 'output'}")
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(
                [json.loads(line) for line in completed.stdout.splitlines()],
                [{"event": "failed", "code": "INPUT_NOT_DIRECTORY"}],
            )
            self.assertFalse((root / "output").exists())

    def test_worker_stops_when_nobody_reads_its_messages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            process = subprocess.Popen(
                [sys.executable, "-P", "-m", WORKER, f"--input={SYNTHETIC_EXPORT}", f"--output={output}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=child_environment(),
            )
            assert process.stdout is not None
            process.stdout.close()
            self.assertEqual(process.wait(timeout=120), 2)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.iterdir()), [])


class RunManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.dict(os.environ, child_environment())
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.parent = self.root / "outputs"
        self.parent.mkdir()

    def start(self, manager: RunManager, name: str = "output", **extra: Any) -> dict[str, Any]:
        self.addCleanup(manager.stop)
        status = manager.start(request(SYNTHETIC_EXPORT, self.parent, name, **extra))
        self.assertIn(status["state"], {"running", "finished", "failed"})
        return status

    def wait_for_progress(self, manager: RunManager) -> None:
        self.assertTrue(wait_until(lambda: bool(manager.status()["progress"])))

    def wait_for_end(self, manager: RunManager, timeout: float = 60.0) -> dict[str, Any]:
        self.assertTrue(wait_until(lambda: not manager.active(), timeout))
        return manager.status()

    def test_a_signal_cancels_the_run(self) -> None:
        manager = stub_manager("wait", cancel_grace=60.0)
        self.start(manager)
        self.wait_for_progress(manager)
        self.assertEqual(manager.cancel()["state"], "cancelling")
        status = self.wait_for_end(manager, timeout=30.0)
        self.assertEqual(status["state"], "cancelled")
        self.assertEqual(manager._run.process.returncode, 130)
        self.assertFalse((self.parent / "output").exists())
        self.assertEqual(status["staging_folders"], [])

    def test_a_run_that_ignores_the_signal_is_terminated(self) -> None:
        manager = stub_manager("ignore", cancel_grace=0.5, kill_grace=10.0)
        self.start(manager)
        self.wait_for_progress(manager)
        manager.cancel()
        status = self.wait_for_end(manager, timeout=30.0)
        self.assertEqual(status["state"], "cancelled")
        self.assertNotEqual(manager._run.process.returncode, 130)

    def test_an_output_published_before_the_cancel_is_reported(self) -> None:
        manager = stub_manager("publish-then-wait")
        self.start(manager)
        self.wait_for_progress(manager)
        manager.cancel()
        status = self.wait_for_end(manager)
        self.assertEqual(status["state"], "finished_after_cancel")
        self.assertTrue((self.parent / "output").is_dir())

    def test_a_staging_folder_left_by_a_forced_stop_is_reported_and_kept(self) -> None:
        manager = stub_manager("stage-then-ignore", cancel_grace=0.3)
        self.start(manager)
        self.wait_for_progress(manager)
        manager.cancel()
        status = self.wait_for_end(manager)
        self.assertEqual(status["state"], "cancelled")
        self.assertEqual(status["staging_folders"], [".output.run-all-stub"])
        self.assertTrue((self.parent / ".output.run-all-stub").is_dir())

    def test_only_one_run_is_active_at_a_time(self) -> None:
        manager = stub_manager("wait")
        self.start(manager)
        with self.assertRaises(RunActiveError):
            manager.start(request(SYNTHETIC_EXPORT, self.parent, "second"))
        manager.cancel()
        self.wait_for_end(manager)
        self.start(manager, "third")
        self.assertTrue(manager.active())

    def test_stop_cancels_an_active_run_and_waits(self) -> None:
        manager = stub_manager("wait")
        self.start(manager)
        self.wait_for_progress(manager)
        manager.stop()
        # The outcome is recorded by the time stop() returns.
        self.assertIsNotNone(manager._run.process.poll())
        self.assertFalse(manager.active())
        self.assertEqual(manager.status()["state"], "cancelled")

    def test_stop_waits_until_a_slow_outcome_is_recorded(self) -> None:
        # Windows CI showed that the outcome can be recorded after the child
        # has ended; stop() must still return with the outcome recorded.
        manager = stub_manager("wait")
        record_outcome = manager._finish

        def slow_record(run: Any, returncode: int) -> None:
            time.sleep(0.5)
            record_outcome(run, returncode)

        with patch.object(manager, "_finish", slow_record):
            self.start(manager)
            self.wait_for_progress(manager)
            manager.stop()
            self.assertFalse(manager.active())
            self.assertEqual(manager.status()["state"], "cancelled")

    def test_only_validated_messages_from_the_child_reach_the_status(self) -> None:
        manager = stub_manager("noise")
        self.start(manager)
        status = self.wait_for_end(manager)
        self.assertEqual(status["state"], "failed")
        self.assertEqual(status["error_code"], "RUN_ALL_FAILED")
        self.assertEqual(status["progress"], {"stage": "normalizing", "step": "activities"})
        self.assertIsNone(status["result"])
        self.assertNotIn(PRIVATE_TEXT, json.dumps(status))

    def test_requests_are_checked_before_a_child_starts(self) -> None:
        manager = stub_manager("wait")
        (self.parent / "existing").mkdir()
        cases: list[tuple[dict[str, Any], str]] = [
            ({**request(SYNTHETIC_EXPORT, self.parent), "input": "relative/export"}, "PATH_NOT_ABSOLUTE"),
            ({**request(SYNTHETIC_EXPORT, self.parent), "input": 7}, "INPUT_PATH_INVALID"),
            (request(SYNTHETIC_EXPORT, self.root / "missing"), "OUTPUT_PARENT_NOT_FOUND"),
            (request(SYNTHETIC_EXPORT, self.parent, "existing"), "OUTPUT_EXISTS"),
            ({**request(SYNTHETIC_EXPORT, self.parent), "timezone": 9}, "TIMEZONE_INVALID"),
            ({**request(SYNTHETIC_EXPORT, self.parent), "timezone": "x" * 65}, "TIMEZONE_INVALID"),
            (request(SYNTHETIC_EXPORT, self.parent, external_safe_pack="yes"), "REQUEST_INVALID"),
        ]
        for name in ("", ".", "..", ".hidden", "a/b", "a\\b", "CON", "con.txt", "Nul",
                     "name.", "name ", "a:b", "a*b", "a?b", 'a"b', "a<b", "a|b", "tab\tname", "x" * 256):
            cases.append((request(SYNTHETIC_EXPORT, self.parent, name), "OUTPUT_NAME_INVALID"))
        if hasattr(os, "symlink") and os.name != "nt":
            (self.parent / "link").symlink_to(self.root)
            cases.append((request(SYNTHETIC_EXPORT, self.parent, "link"), "OUTPUT_SYMLINK"))
        for case, code in cases:
            with self.subTest(case=case, code=code):
                with self.assertRaises(RunRequestError) as caught:
                    manager.start(case)
                self.assertEqual(caught.exception.code, code)
        self.assertEqual(manager.status(), {"state": "idle"})
        self.assertEqual(
            sorted(path.name for path in self.parent.iterdir()),
            sorted(["existing", *(["link"] if (self.parent / "link").is_symlink() else [])]),
        )

    def test_the_real_worker_runs_through_the_manager(self) -> None:
        manager = RunManager()
        self.start(manager)
        status = self.wait_for_end(manager)
        self.assertEqual(status["state"], "finished")
        self.assertEqual(status["result"]["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(status["output_path"], str(self.parent / "output"))
        cli_output = self.root / "cli-output"
        self.assertEqual(run_cli("--input", str(SYNTHETIC_EXPORT), "--output", str(cli_output)).returncode, 0)
        self.assertEqual(tree_bytes(self.parent / "output"), tree_bytes(cli_output))

    def test_the_real_worker_can_be_cancelled_without_leftovers(self) -> None:
        export = self.root / "export"
        export_with_fit(self.root)
        uploaded = export / "DI-Connect-Uploaded-Files"
        for number in range(300):
            dynamics = (843 + number, 3698, 2421, 789, 4884, 10656)
            (uploaded / f"generated_{number}.fit").write_bytes(
                synthetic_fit(session_running_dynamics=dynamics, lap_running_dynamics=dynamics)
            )
        manager = RunManager()
        self.addCleanup(manager.stop)
        manager.start(request(export, self.parent))
        # Cancel while FIT files are read, unless the run is already over.
        self.assertTrue(
            wait_until(
                lambda: manager.status()["progress"].get("stage") == "reading_fit"
                or not manager.active()
            )
        )
        manager.cancel()
        status = self.wait_for_end(manager)
        # On a fast machine the run can finish before the cancellation is
        # requested ("finished") or before the signal arrives
        # ("finished_after_cancel"). Either way nothing is left behind.
        self.assertIn(status["state"], {"cancelled", "finished_after_cancel", "finished"})
        output = self.parent / "output"
        if status["state"] == "cancelled":
            self.assertFalse(output.exists())
        else:
            validate_standalone_handoff(output)
        self.assertEqual(status["staging_folders"], [])
        self.assertEqual(
            [path.name for path in self.parent.iterdir() if path.name.startswith(".")], []
        )


if __name__ == "__main__":
    unittest.main()
