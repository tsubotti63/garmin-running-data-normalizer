"""The `gui` command (stage D1).

The CLI starts the GUI's server, prints its address with the launch key, opens
it in the default browser unless ``--no-browser`` is given, and ends with the
exit code of how the server stopped: 0 after the Quit button or ``Ctrl+C``
without a run, also before the server serves, and 130, the CLI's code, when
``Ctrl+C`` stopped a run. The command also runs in a process of its own, whose
home folders are each test's own. Synthetic data only.
"""
from __future__ import annotations

import io
import json
import os
import queue
import signal
import site
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from garmin_running_data_normalizer import runner, shortcut
from garmin_running_data_normalizer.gui import command
from garmin_running_data_normalizer.gui.server import LAUNCH_KEY_HEADER
from garmin_running_data_normalizer.runner import build_parser
from tests.test_gui_runs import child_environment

ADDRESS_LINE = "GUI address (it contains the launch key; do not share it):"
STOP_LINE = "Stop with Ctrl+C or the Quit button on the page."
TIMEOUT_SECONDS = 30.0


# No test of this module may write in a person's home folder, even when the
# code under test is broken: the whole module runs with a temporary home
# folder (stage E1d; a broken copy once wrote an icon on the real desktop).
_HOME_GUARD: list = []


def setUpModule() -> None:
    folder = tempfile.TemporaryDirectory()
    home = Path(folder.name)
    patches = [
        mock.patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}),
        mock.patch.object(Path, "home", return_value=home),
    ]
    for patch in patches:
        patch.start()
    _HOME_GUARD[:] = [folder, *patches]


def tearDownModule() -> None:
    folder, *patches = _HOME_GUARD
    for patch in reversed(patches):
        patch.stop()
    folder.cleanup()


def _default_ctrl_c() -> None:
    # A command started in the background of a shell inherits Ctrl+C as
    # ignored, and Python then never raises KeyboardInterrupt; the child of
    # the test takes it as a person's terminal gives it.
    signal.signal(signal.SIGINT, signal.SIG_DFL)


class GuiCommandParserTest(unittest.TestCase):
    def test_the_cli_has_the_gui_command(self) -> None:
        args = build_parser().parse_args(["gui"])
        self.assertEqual((args.command, args.no_browser), ("gui", False))
        self.assertIs(build_parser().parse_args(["gui", "--no-browser"]).no_browser, True)
        self.assertIn("gui", build_parser().format_help())


class GuiCommandRunnerTest(unittest.TestCase):
    def test_the_cli_opens_the_browser_unless_no_browser_is_given(self) -> None:
        # Without --create-shortcut no icon is made; were one made, the test
        # fails here instead of writing it (stage E1d).
        no_icon = AssertionError("an icon was made without --create-shortcut")
        with (
            patch.object(command, "run_gui", return_value=0) as run_gui,
            patch.object(shortcut, "create_shortcut", side_effect=no_icon),
        ):
            self.assertEqual(runner.main(["gui", "--no-browser"]), 0)
            self.assertEqual(runner.main(["gui"]), 0)
        self.assertEqual([call.kwargs for call in run_gui.call_args_list], [{"open_browser": False}, {"open_browser": True}])


class GuiCommandExitCodeTest(unittest.TestCase):
    def test_the_exit_code_follows_how_the_server_stopped(self) -> None:
        # The CLI's code for a command that Ctrl+C stopped, also after its
        # output, whatever the run had come to.
        self.assertEqual(command.CANCELLED_EXIT_CODE, 130)
        self.assertEqual(command.exit_code(None), 0)
        for state in ("cancelled", "finished_after_cancel", "failed", "finished"):
            with self.subTest(state=state):
                self.assertEqual(command.exit_code({"state": state}), 130)


class FakeServer:
    url = "http://127.0.0.1:1/#key=synthetic-key"

    def __init__(self) -> None:
        self.closed = False

    def server_close(self) -> None:
        self.closed = True


class GuiCommandRunTest(unittest.TestCase):
    def run_gui(self, stopped: dict[str, object] | None, **options: object) -> tuple[int, list[str], str, list[str]]:
        opened: list[str] = []
        options.setdefault("opener", opened.append)
        with (
            patch.object(command, "serve_until_stopped", return_value=stopped),
            patch("sys.stdout", new_callable=io.StringIO) as out,
            patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            code = command.run_gui(make_server=FakeServer, **options)
        return code, out.getvalue().splitlines(), err.getvalue(), opened

    def test_the_command_prints_the_address_and_opens_it(self) -> None:
        code, lines, err, opened = self.run_gui(None)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [ADDRESS_LINE, FakeServer.url, STOP_LINE, "GUI stopped."])
        self.assertEqual((err, opened), ("", [FakeServer.url]))
        # Without the browser, the address is only printed.
        code, lines, _err, opened = self.run_gui(None, open_browser=False)
        self.assertEqual((code, lines[1], opened), (0, FakeServer.url, []))

    def test_a_run_that_ctrl_c_stopped_is_reported_as_the_cli_reports_it(self) -> None:
        code, lines, err, _opened = self.run_gui({"state": "cancelled", "staging_folders": [".staging-synthetic"]})
        self.assertEqual((code, lines[-1]), (130, "GUI stopped."))
        self.assertIn("RUN_CANCELLED", err)
        self.assertIn("left next to the output: .staging-synthetic", err)
        code, _lines, err, _opened = self.run_gui({"state": "finished_after_cancel"})
        self.assertEqual(code, 130)
        self.assertIn("RUN_CANCELLED_AFTER_OUTPUT", err)

    def test_ctrl_c_before_the_server_serves_stops_it_without_a_report(self) -> None:
        servers: list[FakeServer] = []

        def make_server() -> FakeServer:
            servers.append(FakeServer())
            return servers[-1]

        def interrupted(url: str) -> None:
            raise KeyboardInterrupt

        with (
            patch.object(command, "serve_until_stopped") as serve,
            patch("sys.stdout", new_callable=io.StringIO) as out,
            patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            code = command.run_gui(make_server=make_server, opener=interrupted)
        self.assertEqual((code, out.getvalue().splitlines()[-1], err.getvalue()), (0, "GUI stopped.", ""))
        self.assertTrue(servers[0].closed)
        serve.assert_not_called()


class GuiCommandSecondCtrlCTest(unittest.TestCase):
    def test_a_second_ctrl_c_while_the_server_stops_is_ignored(self) -> None:
        # As the CLI ignores one while it reports (stage A5c): the first
        # Ctrl+C stops the server, a later one does nothing until the run is
        # reported, and the earlier handler is given back.
        before = signal.getsignal(signal.SIGINT)

        def serve(server: FakeServer) -> dict[str, object]:
            handler = signal.getsignal(signal.SIGINT)
            with self.assertRaises(KeyboardInterrupt):
                handler(signal.SIGINT, None)
            self.assertIsNone(handler(signal.SIGINT, None))
            return {"state": "cancelled"}

        with (
            patch.object(command, "serve_until_stopped", side_effect=serve),
            patch("sys.stdout", new_callable=io.StringIO) as out,
            patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            code = command.run_gui(make_server=FakeServer, opener=lambda url: None)
        self.assertEqual((code, out.getvalue().splitlines()[-1]), (130, "GUI stopped."))
        self.assertIn("RUN_CANCELLED", err.getvalue())
        self.assertIs(signal.getsignal(signal.SIGINT), before)


class GuiCommandProcessTest(unittest.TestCase):
    """The command in a process of its own, as a person starts it."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        home = Path(directory.name)
        # The child's places for the settings are under this folder on every
        # system, never the real home folder; Python's own place for the
        # user's packages stays where it is.
        self.environment = {
            **child_environment(),
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(home / "AppData" / "Roaming"),
            "LOCALAPPDATA": str(home / "AppData" / "Local"),
            "XDG_STATE_HOME": str(home / ".local" / "state"),
            "PYTHONUSERBASE": site.getuserbase(),
        }
        if os.name != "nt":
            # No browser opens from these tests, even for a command that
            # would open one.
            self.environment["BROWSER"] = "true"

    def start(self) -> tuple[subprocess.Popen[str], str, str]:
        process = subprocess.Popen(
            [sys.executable, "-m", "garmin_running_data_normalizer", "gui", "--no-browser"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
            preexec_fn=_default_ctrl_c if os.name != "nt" else None,
        )
        self.addCleanup(lambda: process.poll() is None and process.kill())
        # The first lines are read with a limit on the time, so that a
        # command that prints no address fails instead of waiting.
        lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=lambda: [lines.put(process.stdout.readline()) for _ in range(3)], daemon=True).start()
        try:
            first = [lines.get(timeout=TIMEOUT_SECONDS).strip() for _ in range(3)]
        except queue.Empty:
            self.fail("the command printed no address")
        self.assertEqual((first[0], first[2]), (ADDRESS_LINE, STOP_LINE))
        self.assertRegex(first[1], r"^http://127\.0\.0\.1:\d+/#key=[A-Za-z0-9_-]+$")
        origin, key = first[1].split("/#key=")
        return process, origin, key

    def post(self, origin: str, key: str, path: str) -> dict[str, object]:
        request = urllib.request.Request(
            f"{origin}{path}",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json", LAUNCH_KEY_HEADER: key},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read())

    def test_the_command_stops_with_the_quit_request(self) -> None:
        process, origin, key = self.start()
        self.assertEqual(self.post(origin, key, "/api/shutdown"), {"status": "stopping"})
        out, err = process.communicate(timeout=TIMEOUT_SECONDS)
        self.assertEqual((process.returncode, out.strip(), err), (0, "GUI stopped.", ""))

    @unittest.skipIf(os.name == "nt", "Ctrl+C reaches a process of its own as a signal on POSIX only")
    def test_ctrl_c_stops_the_command_when_no_run_is_active(self) -> None:
        process, origin, key = self.start()
        # Once the server answers, it serves.
        self.assertEqual(self.post(origin, key, "/api/heartbeat"), {"status": "ok"})
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=TIMEOUT_SECONDS)
        self.assertEqual((process.returncode, out.strip(), err), (0, "GUI stopped.", ""))


if __name__ == "__main__":
    unittest.main()
