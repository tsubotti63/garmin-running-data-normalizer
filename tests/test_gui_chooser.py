"""The system's own dialog to choose an Export (stage B3a).

No test opens a real dialog: the commands are checked as text, and small
programs stand in for the dialogs and answer as they do.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from typing import Any
from unittest.mock import patch

from garmin_running_data_normalizer.gui import chooser
from garmin_running_data_normalizer.gui.chooser import KINDS, Chooser, ChooserError, answer, command
from tests.test_gui_runs import wait_until

# A place in Japanese with a space at its end, absolute on this system.
PLACE = os.path.join(os.path.abspath(tempfile.gettempdir()), "ガーミン エクスポート ")


def program(code: str) -> list[str]:
    """A stand-in for a dialog: a Python program that runs ``code``."""
    return [sys.executable, "-c", code]


def printing(text: str, status: int = 0, stderr: str = "") -> list[str]:
    """A stand-in that writes ``text`` in UTF-8 and ends with ``status``."""
    return program(
        "import sys; "
        f"sys.stdout.buffer.write({text.encode('utf-8')!r}); "
        f"sys.stderr.write({stderr!r}); "
        f"sys.exit({status})"
    )


SLEEPING = program("import time; time.sleep(60)")


class ChooserCommandTest(unittest.TestCase):
    def test_macos_uses_fixed_scripts_of_osascript(self) -> None:
        self.assertEqual(
            command("zip", "darwin"),
            [
                "/usr/bin/osascript",
                "-e",
                'POSIX path of (choose file of type {"zip", "public.zip-archive"})',
            ],
        )
        self.assertEqual(
            command("folder", "darwin"),
            ["/usr/bin/osascript", "-e", "POSIX path of (choose folder)"],
        )

    def test_windows_uses_fixed_scripts_of_powershell_in_utf8(self) -> None:
        program_path = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        with patch.object(chooser.shutil, "which", lambda name: program_path if name == "powershell.exe" else None):
            commands = {kind: command(kind, "win32") for kind in KINDS}
        for kind, arguments in commands.items():
            with self.subTest(kind=kind):
                assert arguments is not None
                self.assertEqual(
                    arguments[:5], [program_path, "-NoProfile", "-NonInteractive", "-STA", "-Command"]
                )
                self.assertEqual(len(arguments), 6)
                script = arguments[5]
                # Names in Japanese reach the server intact, and the dialog
                # stays in front of the browser.
                self.assertTrue(script.startswith("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "))
                self.assertIn("TopMost = $true", script)
        self.assertIn("OpenFileDialog", commands["zip"][5])
        self.assertIn("'ZIP (*.zip)|*.zip'", commands["zip"][5])
        self.assertIn("[Console]::Out.Write($dialog.FileName)", commands["zip"][5])
        self.assertIn("FolderBrowserDialog", commands["folder"][5])
        self.assertIn("[Console]::Out.Write($dialog.SelectedPath)", commands["folder"][5])
        with patch.object(chooser.shutil, "which", lambda name: None):
            self.assertIsNone(command("zip", "win32"))

    def test_linux_uses_zenity_or_kdialog_with_a_display(self) -> None:
        found = {"zenity": "/usr/bin/zenity", "kdialog": "/usr/bin/kdialog"}
        with patch.dict(os.environ, {"DISPLAY": ":0"}):
            with patch.object(chooser.shutil, "which", found.get):
                self.assertEqual(
                    command("zip", "linux"),
                    ["/usr/bin/zenity", "--file-selection", "--file-filter=ZIP | *.zip *.ZIP"],
                )
                self.assertEqual(
                    command("folder", "linux"), ["/usr/bin/zenity", "--file-selection", "--directory"]
                )
            with patch.object(chooser.shutil, "which", lambda name: found.get(name) if name == "kdialog" else None):
                self.assertEqual(
                    command("zip", "linux"), ["/usr/bin/kdialog", "--getopenfilename", ".", "*.zip *.ZIP"]
                )
                self.assertEqual(
                    command("folder", "linux"), ["/usr/bin/kdialog", "--getexistingdirectory", "."]
                )
            with patch.object(chooser.shutil, "which", lambda name: None):
                self.assertIsNone(command("zip", "linux"))
        # Without a display, no dialog can open.
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
            with patch.object(chooser.shutil, "which", found.get):
                self.assertIsNone(command("folder", "linux"))
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": "wayland-0"}):
            with patch.object(chooser.shutil, "which", found.get):
                self.assertEqual(command("folder", "linux")[0], "/usr/bin/zenity")


class ChooserAnswerTest(unittest.TestCase):
    def test_what_a_closed_dialog_answered(self) -> None:
        def closed(path: str | None) -> dict[str, Any]:
            return {"state": "closed", "path": path}

        unusable = {"state": "failed", "error_code": "CHOOSER_NOT_AVAILABLE"}
        place = PLACE.encode("utf-8")
        cases = [
            # The place as it is, with the space at its end; only the line
            # end that the programs add is left out.
            (("darwin", 0, place + b"\n", b""), closed(PLACE)),
            (("linux", 0, place + b"\n", b"Gtk-Message: a note\n"), closed(PLACE)),
            (("win32", 0, place, b""), closed(PLACE)),
            (("win32", 0, place + b"\r\n", b""), closed(PLACE)),
            # Cancelled: AppleScript says -128; zenity and kdialog end with 1;
            # the script of PowerShell writes nothing.
            (("darwin", 1, b"", b"execution error: User canceled. (-128)\n"), closed(None)),
            (("linux", 1, b"", b""), closed(None)),
            (("win32", 0, b"", b""), closed(None)),
            (("darwin", 0, b"\n", b""), closed(None)),
            # A dialog that did not work.
            (("darwin", 1, b"", b"execution error: other (-1700)\n"), unusable),
            (("win32", 1, b"", b"an error"), unusable),
            (("linux", 2, b"", b""), unusable),
            (("darwin", 0, b"relative/place\n", b""), unusable),
            (("darwin", 0, place + b"\nsecond\n", b""), unusable),
            (("darwin", 0, place + b"\x00\n", b""), unusable),
            (("darwin", 0, place + b"\r", b""), closed(PLACE)),
            (("darwin", 0, b"\xff\xfe\n", b""), unusable),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(answer(*arguments), expected)


class ChooserTest(unittest.TestCase):
    def wait_for_answer(self, dialogs: Chooser) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def closed() -> bool:
            nonlocal result
            result = dialogs.status()
            return result["state"] != "open"

        self.assertTrue(wait_until(closed, 30))
        return result

    def test_the_chosen_place_is_given_once(self) -> None:
        asked: list[tuple[str, str]] = []

        def find(kind: str, platform: str) -> list[str]:
            asked.append((kind, platform))
            return printing(PLACE + "\n")

        dialogs = Chooser(platform="darwin", find_command=find)
        self.assertEqual(dialogs.status(), {"state": "idle"})
        dialogs.start("zip")
        self.assertEqual(self.wait_for_answer(dialogs), {"state": "closed", "path": PLACE})
        self.assertEqual(dialogs.status(), {"state": "idle"})
        self.assertEqual(asked, [("zip", "darwin")])

    def test_a_cancelled_dialog_chooses_nothing(self) -> None:
        dialogs = Chooser(
            platform="darwin",
            find_command=lambda kind, platform: printing("", 1, "User canceled. (-128)"),
        )
        dialogs.start("folder")
        self.assertEqual(self.wait_for_answer(dialogs), {"state": "closed", "path": None})

    def test_only_the_two_kinds_open_a_dialog(self) -> None:
        # Nothing from the page reaches a command: the kind only picks one of
        # the fixed scripts.
        asked: list[Any] = []
        dialogs = Chooser(find_command=lambda kind, platform: asked.append(kind))
        for kind in (None, "", "ZIP", "file", 'zip"} & (do shell script "x")', ["zip"], 1):
            with self.subTest(kind=kind):
                with self.assertRaises(ChooserError) as caught:
                    dialogs.start(kind)
                self.assertEqual(caught.exception.code, "REQUEST_INVALID")
        self.assertEqual(asked, [])

    def test_a_system_without_a_dialog_says_so(self) -> None:
        missing = os.path.join(os.path.abspath(tempfile.gettempdir()), "no-such-dialog-program-b3a")
        for find in (lambda kind, platform: None, lambda kind, platform: [missing]):
            with self.assertRaises(ChooserError) as caught:
                Chooser(find_command=find).start("zip")
            self.assertEqual(caught.exception.code, "CHOOSER_NOT_AVAILABLE")
        failing = Chooser(platform="darwin", find_command=lambda kind, platform: printing("", 3))
        failing.start("folder")
        self.assertEqual(
            self.wait_for_answer(failing), {"state": "failed", "error_code": "CHOOSER_NOT_AVAILABLE"}
        )

    def test_one_dialog_is_open_at_a_time(self) -> None:
        dialogs = Chooser(platform="darwin", find_command=lambda kind, platform: SLEEPING)
        dialogs.start("zip")
        self.addCleanup(dialogs.stop)
        with self.assertRaises(ChooserError) as caught:
            dialogs.start("folder")
        self.assertEqual(caught.exception.code, "CHOOSER_BUSY")
        self.assertEqual(dialogs.status(), {"state": "open"})
        # The server closes a dialog that is still open when it stops; then
        # another one can open.
        dialogs.stop()
        self.assertNotEqual(self.wait_for_answer(dialogs)["state"], "open")
        dialogs.start("folder")
        self.assertEqual(dialogs.status(), {"state": "open"})

    def test_an_unanswered_dialog_is_closed_at_the_time_limit(self) -> None:
        started: list[subprocess.Popen[bytes]] = []
        real_popen = subprocess.Popen

        def recording_popen(*arguments: Any, **options: Any) -> subprocess.Popen[bytes]:
            process = real_popen(*arguments, **options)
            started.append(process)
            return process

        dialogs = Chooser(platform="darwin", timeout=0.5, find_command=lambda kind, platform: SLEEPING)
        begun = time.monotonic()
        with patch.object(chooser.subprocess, "Popen", recording_popen):
            dialogs.start("zip")
        self.assertEqual(
            self.wait_for_answer(dialogs), {"state": "failed", "error_code": "CHOOSER_TIMEOUT"}
        )
        self.assertLess(time.monotonic() - begun, 30)
        # Its program is stopped, so that no dialog stays on the screen.
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].poll())


if __name__ == "__main__":
    unittest.main()
