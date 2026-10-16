"""Stage A5c: Ctrl+C ends every command of the CLI with a line and exit 130,
instead of a traceback, says what the command left, and one Ctrl+C leaves no
part of an output; the GUI's server reports a run that Ctrl+C cancelled with
the same content (synthetic data only)."""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.snapshot.store import initialize_store, register_snapshot

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
STAMP = "2030-01-01T02:00:00+00:00"
GOLDEN_FILES = ["normalized_activities.json", "qa_summary.json", "run_manifest.json"]


def stops_module() -> Any:
    # Read where it is used, so that each test fails on its own on a version
    # without the codes of a cancellation.
    return importlib.import_module("garmin_running_data_normalizer.stops")


def cli(*args: object) -> tuple[int, str]:
    stderr = io.StringIO()
    before = signal.getsignal(signal.SIGINT)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = runner.main([str(arg) for arg in args])
    except KeyboardInterrupt:
        # Until stage A5c, Ctrl+C left the CLI as a traceback; a test fails on
        # it instead of stopping the whole test run.
        raise AssertionError("Ctrl+C left the CLI as a traceback") from None
    # The CLI gives back the handling of Ctrl+C, whether the command finished,
    # stopped, or was cancelled.
    if signal.getsignal(signal.SIGINT) is not before:
        raise AssertionError("the CLI did not give back the handling of Ctrl+C")
    return code, stderr.getvalue()


def register_args(store: Path, source: Path = SYNTHETIC_EXPORT, label: str = "S1") -> tuple[object, ...]:
    return (
        "snapshot", "register", "--store", store, "--input", source, "--label", label,
        "--requested-at", STAMP, "--downloaded-at", STAMP, "--observed-at", STAMP, "--confirm-complete",
    )


def registered(store: Path) -> None:
    initialize_store(store, "synthetic")
    register_snapshot(
        store,
        SYNTHETIC_EXPORT,
        snapshot_label="S1",
        export_requested_at=STAMP,
        export_downloaded_at=STAMP,
        export_observed_at=STAMP,
        confirm_complete=True,
    )


def interrupt(*args: object, **kwargs: object) -> None:
    raise KeyboardInterrupt


def names(folder: Path) -> list[str]:
    return sorted(path.name for path in folder.iterdir())


@contextlib.contextmanager
def interrupted_rename(target_folder: Path, at: int) -> Any:
    """Path.rename that raises KeyboardInterrupt at its ``at``-th rename into
    ``target_folder``, as Ctrl+C would at that moment."""
    real = Path.rename
    count = {"renames": 0}

    def rename(self: Path, target: Any) -> Any:
        if Path(target).parent == target_folder:
            count["renames"] += 1
            if count["renames"] == at:
                raise KeyboardInterrupt
        return real(self, target)

    with mock.patch.object(Path, "rename", rename):
        yield


class UsualCtrlC(unittest.TestCase):
    """A shell that runs the tests in the background starts them with SIGINT
    ignored, which a child process inherits. The tests start from the usual
    handler, so that the CLI is seen to give it back and a child follows
    SIGINT."""

    def setUp(self) -> None:
        previous = signal.signal(signal.SIGINT, signal.default_int_handler)
        self.addCleanup(signal.signal, signal.SIGINT, previous)


class CancelledCommandTest(UsualCtrlC):
    def assert_cancelled(self, args: tuple[object, ...], root: Path, name: str, code: str = "RUN_CANCELLED") -> list[str]:
        """The command ends with exit 130 and the line of its cancellation,
        without a traceback; return the lines after it."""
        before = signal.getsignal(signal.SIGINT)
        exit_code, stderr = cli(*args)
        self.assertEqual(exit_code, 130, stderr)
        self.assertNotIn("Traceback", stderr)
        lines = stderr.splitlines()
        self.assertTrue(lines, stderr)
        stop = stops_module().STOPS[code]
        what = f"{name} was cancelled with Ctrl+C"
        if code == "RUN_CANCELLED_AFTER_OUTPUT":
            what += " after it wrote its output"
        self.assertEqual(lines[0], f"ERROR [{code}]: {what}; {stop.next_step}")
        # No path of the computer in any line: only names, after the first.
        for line in lines:
            self.assertNotIn(str(root), line)
        # The handling of Ctrl+C is given back.
        self.assertIs(signal.getsignal(signal.SIGINT), before)
        return lines[1:]

    def test_every_command_ends_with_the_line_of_a_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            store = root / "store"
            registered(store)
            done = root / "done"
            self.assertEqual(cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", done)[0], 0)
            commands = [
                ("run-all", "garmin_running_data_normalizer.runner.run_all",
                 ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o1")),
                ("normalize-activities", "garmin_running_data_normalizer.runner.run_activities",
                 ("normalize-activities", "--input", SYNTHETIC_EXPORT, "--output", root / "o2")),
                ("snapshot init", "garmin_running_data_normalizer.snapshot.initialize_store",
                 ("snapshot", "init", "--store", root / "s1", "--account", "synthetic")),
                ("snapshot register", "garmin_running_data_normalizer.snapshot.register_snapshot",
                 register_args(store, label="S2")),
                ("snapshot status", "garmin_running_data_normalizer.snapshot.snapshot_status",
                 ("snapshot", "status", "--store", store)),
                ("snapshot verify", "garmin_running_data_normalizer.snapshot.verify_store",
                 ("snapshot", "verify", "--store", store)),
                ("snapshot build-input", "garmin_running_data_normalizer.snapshot.build_approved_input",
                 ("snapshot", "build-input", "--store", store, "--output", root / "o3")),
                ("snapshot run-all", "garmin_running_data_normalizer.snapshot.run_snapshot_all",
                 ("snapshot", "run-all", "--store", store, "--output", root / "o4")),
                ("validate-handoff", "garmin_running_data_normalizer.runner.validate_standalone_handoff",
                 ("validate-handoff", "--input", done)),
                ("doctor", "garmin_running_data_normalizer.runner.doctor_input",
                 ("doctor", "--input", SYNTHETIC_EXPORT)),
                ("doctor", "garmin_running_data_normalizer.runner.doctor_run_output",
                 ("doctor", "--run-output", done)),
                ("support-bundle", "garmin_running_data_normalizer.runner.build_support_bundle",
                 ("support-bundle", "--run-output", done, "--output", root / "bundle.zip")),
            ]
            before = names(root)
            for name, target, args in commands:
                with self.subTest(command=name, target=target.rsplit(".", 1)[1]):
                    with mock.patch(target, side_effect=interrupt):
                        self.assertEqual(self.assert_cancelled(args, root, name), [])
                    self.assertEqual(names(root), before)

    def test_one_ctrl_c_leaves_no_part_of_an_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            store = root / "store"
            registered(store)
            done = root / "done"
            self.assertEqual(cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", done)[0], 0)
            empty = root / "empty"
            empty.mkdir()
            before = names(root)
            cases = [
                # Run-All while it writes its staging folder.
                ("run-all", mock.patch("garmin_running_data_normalizer.run_all._write_exclusive", side_effect=interrupt),
                 ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o1")),
                # The build, whose staging folder stayed until stage A5c.
                ("snapshot build-input", mock.patch("garmin_running_data_normalizer.snapshot.merge._write_json", side_effect=interrupt),
                 ("snapshot", "build-input", "--store", store, "--output", root / "o2")),
                # The second of the three files moved into an empty folder,
                # which stayed until stage A5c.
                ("normalize-activities", interrupted_rename(empty, 2),
                 ("normalize-activities", "--input", SYNTHETIC_EXPORT, "--output", empty)),
                # The Support Bundle while it is put in its place; its
                # temporary file stayed until stage A5c.
                ("support-bundle", mock.patch.object(Path, "replace", interrupt),
                 ("support-bundle", "--run-output", done, "--output", root / "bundle.zip")),
                # A new store while it is written.
                ("snapshot init", mock.patch("garmin_running_data_normalizer.snapshot.store._write_registry", side_effect=interrupt),
                 ("snapshot", "init", "--store", root / "new-store", "--account", "synthetic")),
            ]
            for name, patch, args in cases:
                with self.subTest(command=name):
                    with patch:
                        self.assertEqual(self.assert_cancelled(args, root, name), [])
                    self.assertEqual(names(root), before)
                    self.assertEqual(names(empty), [])

    def test_a_cancelled_registration_says_that_the_next_one_completes_the_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            store = root / "store"
            initialize_store(store, "synthetic")
            # While the Export's files are copied, after the journal is
            # written; the lock is removed.
            with mock.patch("garmin_running_data_normalizer.snapshot.store._preserve_blob", side_effect=interrupt):
                lines = self.assert_cancelled(register_args(store), root, "snapshot register")
            notices = stops_module().stop_text("SNAPSHOT_REGISTRATION_INCOMPLETE")
            self.assertEqual(lines, [f"NOTE [SNAPSHOT_REGISTRATION_INCOMPLETE]: {notices}"])
            self.assertFalse((store / ".single-writer.lock").exists())
            # Registering it again completes the store, as the next step says.
            self.assertEqual(cli(*register_args(store)), (0, ""))
            self.assertEqual(cli("snapshot", "verify", "--store", store)[0], 0)

    def test_a_cancellation_after_the_output_was_written_says_that_it_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            store = root / "store"
            registered(store)
            done = root / "done"
            self.assertEqual(cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", done)[0], 0)
            empty = root / "empty"
            empty.mkdir()

            def after(module: Any, function: str) -> Any:
                real = getattr(module, function)

                def wrapped(*args: Any, **kwargs: Any) -> Any:
                    real(*args, **kwargs)
                    raise KeyboardInterrupt

                return mock.patch.object(module, function, wrapped)

            run_all_module = importlib.import_module("garmin_running_data_normalizer.run_all")
            real_rename, real_replace = Path.rename, Path.replace

            def rename_then_interrupt(self: Path, target: Any) -> Any:
                result = real_rename(self, target)
                if Path(target) == root / "o2":
                    raise KeyboardInterrupt
                return result

            def replace_then_interrupt(self: Path, target: Any) -> Any:
                real_replace(self, target)
                raise KeyboardInterrupt

            cases = [
                ("run-all", after(run_all_module, "_publish_outputs"),
                 ("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o1"), root / "o1"),
                ("snapshot build-input", mock.patch.object(Path, "rename", rename_then_interrupt),
                 ("snapshot", "build-input", "--store", store, "--output", root / "o2"), root / "o2"),
                ("normalize-activities", after(runner, "_publish_golden_output"),
                 ("normalize-activities", "--input", SYNTHETIC_EXPORT, "--output", empty), empty),
                ("support-bundle", mock.patch.object(Path, "replace", replace_then_interrupt),
                 ("support-bundle", "--run-output", done, "--output", root / "bundle.zip"), root / "bundle.zip"),
            ]
            for name, patch, args, output in cases:
                with self.subTest(command=name):
                    with patch:
                        lines = self.assert_cancelled(args, root, name, "RUN_CANCELLED_AFTER_OUTPUT")
                    self.assertEqual(lines, [])
                    self.assertTrue(output.exists())
            # The outputs are whole: the run's passes its checks, the empty
            # folder holds the three files, and the bundle is a ZIP file.
            self.assertEqual(cli("validate-handoff", "--input", root / "o1")[0], 0)
            self.assertEqual(names(empty), GOLDEN_FILES)
            with zipfile.ZipFile(root / "bundle.zip") as archive:
                self.assertIsNone(archive.testzip())
            # Running the command again stops, as the next step says.
            exit_code, stderr = cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o1")
            self.assertEqual(exit_code, 2)
            self.assertTrue(stderr.startswith("ERROR [OUTPUT_EXISTS]: "), stderr)

    def test_a_second_ctrl_c_that_stops_the_cleanup_leaves_names_on_their_own_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            # Run-All: the second Ctrl+C stops the removal of its staging
            # folder.
            with mock.patch("garmin_running_data_normalizer.run_all._write_exclusive", side_effect=interrupt), \
                    mock.patch("garmin_running_data_normalizer.run_all.shutil.rmtree", side_effect=interrupt):
                lines = self.assert_cancelled(("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o1"), root, "run-all")
            self.assertEqual(len(lines), 1)
            self.assertRegex(lines[0], r"^left next to the output: \.o1\.run-all-[^/\\]+$")
            self.assertTrue((root / lines[0].split(": ", 1)[1]).is_dir())
            # normalize-activities in an empty folder: the second Ctrl+C stops
            # taking back the file that it moved.
            empty = root / "empty"
            empty.mkdir()
            with interrupted_rename(empty, 2), mock.patch.object(Path, "unlink", interrupt):
                lines = self.assert_cancelled(
                    ("normalize-activities", "--input", SYNTHETIC_EXPORT, "--output", empty), root, "normalize-activities"
                )
            self.assertEqual(lines, ["left in the output folder: normalized_activities.json"])
            # A registration: the second Ctrl+C stops the removal of the lock.
            store = root / "store"
            initialize_store(store, "synthetic")
            real_unlink = Path.unlink

            def unlink(self: Path, missing_ok: bool = False) -> None:
                if self.name == ".single-writer.lock":
                    raise KeyboardInterrupt
                real_unlink(self, missing_ok=missing_ok)

            with mock.patch("garmin_running_data_normalizer.snapshot.store._preserve_blob", side_effect=interrupt), \
                    mock.patch.object(Path, "unlink", unlink):
                lines = self.assert_cancelled(register_args(store), root, "snapshot register")
            self.assertEqual(
                [line.split(":", 1)[0] for line in lines],
                ["NOTE [SNAPSHOT_REGISTRATION_INCOMPLETE]", "NOTE [SNAPSHOT_STORE_LOCKED]"],
            )

    def test_ctrl_c_is_ignored_while_a_command_reports_how_it_ended(self) -> None:
        seen: list[Any] = []
        before = signal.getsignal(signal.SIGINT)

        def record(*args: Any, **kwargs: Any) -> str:
            seen.append(signal.getsignal(signal.SIGINT))
            return "report"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            # A cancelled command, while it prints its line.
            stops = stops_module()
            with mock.patch("garmin_running_data_normalizer.runner.run_all", side_effect=interrupt), \
                    mock.patch("garmin_running_data_normalizer.runner.stop_line", side_effect=lambda code, message: record() and stops.stop_line(code, message)):
                cli("run-all", "--input", SYNTHETIC_EXPORT, "--output", root / "o1")
            # A finished command, while it prints its result.
            with mock.patch("garmin_running_data_normalizer.runner.render_doctor_human", side_effect=record):
                self.assertEqual(cli("doctor", "--input", SYNTHETIC_EXPORT), (0, ""))
        self.assertEqual(seen, [signal.SIG_IGN, signal.SIG_IGN])
        self.assertIs(signal.getsignal(signal.SIGINT), before)

    @unittest.skipIf(os.name == "nt", "a real SIGINT is sent on POSIX only")
    def test_a_real_sigint_ends_a_run_with_the_line_and_exit_130(self) -> None:
        # A shell that runs the tests in the background starts them with
        # SIGINT ignored, which the child inherits and Python keeps: take
        # back the handler that raises KeyboardInterrupt, as the GUI's child
        # does.
        child = (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGINT, signal.default_int_handler)\n"
            "from pathlib import Path\n"
            "from unittest import mock\n"
            "from garmin_running_data_normalizer import runner\n"
            "ready = Path(sys.argv[1])\n"
            "def wait(*args, **kwargs):\n"
            "    ready.write_text('ready', encoding='utf-8')\n"
            "    time.sleep(60)\n"
            "with mock.patch('garmin_running_data_normalizer.run_all.normalize_activities', side_effect=wait):\n"
            "    sys.exit(runner.main(['run-all', '--input', sys.argv[2], '--output', sys.argv[3]]))\n"
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join(
            path for path in (str(ROOT / "src"), environment.get("PYTHONPATH")) if path
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            ready, output = root / "ready", root / "output"
            process = subprocess.Popen(
                [sys.executable, "-c", child, str(ready), str(SYNTHETIC_EXPORT), str(output)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )
            deadline = time.monotonic() + 60
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(ready.exists())
            process.send_signal(signal.SIGINT)
            _stdout, stderr = process.communicate(timeout=60)
            self.assertEqual(process.returncode, 130, stderr)
            self.assertNotIn("Traceback", stderr)
            self.assertEqual(
                stderr.splitlines()[-1],
                f"ERROR [RUN_CANCELLED]: run-all was cancelled with Ctrl+C; "
                f"{stops_module().STOPS['RUN_CANCELLED'].next_step}",
            )
            self.assertEqual(names(root), ["ready"])


class ServerCtrlCTest(UsualCtrlC):
    def test_the_lines_of_a_run_that_ctrl_c_stopped_with_the_server(self) -> None:
        from garmin_running_data_normalizer.gui import server

        stops = stops_module()
        cases = [
            ({"state": "cancelled", "staging_folders": []},
             [stops.stop_line("RUN_CANCELLED", "the run of the GUI was cancelled with Ctrl+C")]),
            ({"state": "cancelled", "staging_folders": [".output.run-all-x"]},
             [stops.stop_line("RUN_CANCELLED", "the run of the GUI was cancelled with Ctrl+C"),
              "left next to the output: .output.run-all-x"]),
            ({"state": "finished_after_cancel", "staging_folders": []},
             [stops.stop_line("RUN_CANCELLED_AFTER_OUTPUT",
                              "the run of the GUI was cancelled with Ctrl+C after it wrote its output")]),
            ({"state": "failed", "error_code": "INPUT_ZIP_CORRUPT", "staging_folders": []},
             [stops.stop_line("INPUT_ZIP_CORRUPT", stops.STOPS["INPUT_ZIP_CORRUPT"].what)]),
            ({"state": "finished", "staging_folders": []}, []),
        ]
        for status, lines in cases:
            with self.subTest(state=status["state"]):
                self.assertEqual(server.cancel_report(status), lines)

    def test_ctrl_c_returns_the_status_of_the_run_that_it_cancelled(self) -> None:
        from garmin_running_data_normalizer.gui import server
        from tests.test_gui_runs import child_environment, request, stub_manager

        with mock.patch.dict(os.environ, child_environment()), tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            runs = stub_manager("wait")
            gui = server.GuiServer(runs=runs)
            runs.start(request(SYNTHETIC_EXPORT, parent))
            self.assertTrue(runs.active())
            with mock.patch.object(gui, "serve_forever", side_effect=KeyboardInterrupt):
                status = server.serve_until_stopped(gui)
            self.assertIsNotNone(status)
            self.assertEqual(status["state"], "cancelled")
            self.assertEqual(
                server.cancel_report(status),
                [stops_module().stop_line("RUN_CANCELLED", "the run of the GUI was cancelled with Ctrl+C")],
            )
            # Without an active run, the server stops without a status.
            idle = server.GuiServer(runs=stub_manager("wait"))
            with mock.patch.object(idle, "serve_forever", side_effect=KeyboardInterrupt):
                self.assertIsNone(server.serve_until_stopped(idle))


if __name__ == "__main__":
    unittest.main()
