"""The icon that starts the GUI (stage E1d, decision 20261021-1).

``gui --create-shortcut`` makes it with the Python that runs the command, and
the GUI does not open when it cannot be made. The tests give every place: the
desktop and the Start menu are temporary folders, so no test writes on a
person's desktop. The Windows tests make real shortcuts with Windows
PowerShell and read them back. Synthetic data only.
"""
from __future__ import annotations

import contextlib
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer import runner, shortcut, stops
from garmin_running_data_normalizer.gui import command
from garmin_running_data_normalizer.runner import build_parser
from garmin_running_data_normalizer.shortcut import (
    ARGUMENTS,
    MAC_MARK,
    NAME,
    ShortcutError,
    create_shortcut,
    mac_script,
)
from tests.test_gui_i18n import flow_table

SHORTCUT_CODES = ("SHORTCUT_NOT_SUPPORTED", "SHORTCUT_PLACE_TAKEN", "SHORTCUT_NOT_CREATED")
POSIX_ONLY = unittest.skipIf(os.name == "nt", "the file of macOS runs with sh")
WINDOWS_ONLY = unittest.skipUnless(os.name == "nt", "shortcuts and Windows PowerShell are Windows features")


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


class TemporaryFolder(unittest.TestCase):
    def setUp(self) -> None:
        handle = tempfile.TemporaryDirectory()
        self.addCleanup(handle.cleanup)
        self.root = Path(handle.name)


class MacFileTest(TemporaryFolder):
    def test_the_file_starts_the_gui_with_the_python_that_ran_the_command(self) -> None:
        self.assertEqual(
            mac_script("/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"),
            "#!/bin/sh\n"
            "# Garmin Running Data Normalizer: starts the GUI.\n"
            '# Made by "garmin-running-data-normalizer gui --create-shortcut"; run that\n'
            "# command again after Python is replaced.\n"
            "exec '/Library/Frameworks/Python.framework/Versions/3.11/bin/python3' "
            "-P -m garmin_running_data_normalizer gui\n",
        )

    def test_the_file_is_on_the_desktop_and_only_its_owner_runs_it(self) -> None:
        desktop = self.root / "Desktop"
        desktop.mkdir()
        places = create_shortcut(platform="darwin", executable="/usr/bin/python3", home=self.root)
        place = desktop / f"{NAME}.command"
        self.assertEqual(places, [place])
        self.assertEqual(place.read_text(encoding="utf-8"), mac_script("/usr/bin/python3"))
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(place.stat().st_mode), 0o700)
        self.assertEqual(sorted(path.name for path in desktop.iterdir()), [place.name])

    @POSIX_ONLY
    def test_a_place_with_spaces_quotes_and_other_letters_reaches_python_as_it_is(self) -> None:
        # A stand-in for Python prints what it is given, so that the file is
        # run as the Terminal runs it.
        folder = self.root / "Python 3.11 の 'test' $HOME `x`"
        folder.mkdir()
        python = folder / "python3"
        python.write_text('#!/bin/sh\nprintf "%s|" "$0" "$@"\n', encoding="utf-8")
        python.chmod(0o700)
        desktop = self.root / "Desktop"
        desktop.mkdir()
        [place] = create_shortcut(platform="darwin", executable=str(python), desktop=desktop)
        result = subprocess.run(["/bin/sh", str(place)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, f"{python}|-P|-m|garmin_running_data_normalizer|gui|")

    def test_the_file_that_this_command_made_is_replaced(self) -> None:
        create_shortcut(platform="darwin", executable="/old/python3", desktop=self.root)
        [place] = create_shortcut(platform="darwin", executable="/new/python3", desktop=self.root)
        self.assertEqual(place.read_text(encoding="utf-8"), mac_script("/new/python3"))
        self.assertEqual([path.name for path in self.root.iterdir()], [place.name])

    def test_another_file_of_the_same_name_stops_the_command_and_stays(self) -> None:
        place = self.root / f"{NAME}.command"
        for text in ("#!/bin/sh\necho mine\n", f"#!/bin/zsh\n{MAC_MARK}\n", f"{MAC_MARK}\n"):
            with self.subTest(text=text):
                place.write_text(text, encoding="utf-8")
                with self.assertRaises(ShortcutError) as caught:
                    create_shortcut(platform="darwin", executable="/usr/bin/python3", desktop=self.root)
                self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")
                self.assertEqual(place.read_text(encoding="utf-8"), text)
        place.unlink()
        place.mkdir()
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="darwin", executable="/usr/bin/python3", desktop=self.root)
        self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")

    @POSIX_ONLY
    def test_a_link_of_the_same_name_stops_the_command(self) -> None:
        target = self.root / "target.command"
        target.write_text(mac_script("/usr/bin/python3"), encoding="utf-8")
        (self.root / f"{NAME}.command").symlink_to(target)
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="darwin", executable="/usr/bin/python3", desktop=self.root)
        self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")
        self.assertEqual(target.read_text(encoding="utf-8"), mac_script("/usr/bin/python3"))

    def test_a_desktop_that_cannot_be_used_stops_the_command_without_a_file_left(self) -> None:
        # The answer Don't Allow to the question of macOS refuses the look at
        # the desktop and the writing in it with PermissionError.
        for patched, error in (
            ("exists", PermissionError(1, "Operation not permitted")),
            ("mkstemp", PermissionError(1, "Operation not permitted")),
            ("replace", PermissionError(1, "Operation not permitted")),
            ("replace", OSError(28, "No space left on device")),
        ):
            with self.subTest(patched=patched, error=type(error).__name__):
                if patched == "exists":
                    patch = mock.patch.object(Path, "exists", side_effect=error)
                elif patched == "mkstemp":
                    patch = mock.patch.object(shortcut.tempfile, "mkstemp", side_effect=error)
                else:
                    patch = mock.patch.object(shortcut.os, "replace", side_effect=error)
                with patch, self.assertRaises(ShortcutError) as caught:
                    create_shortcut(platform="darwin", executable="/usr/bin/python3", desktop=self.root)
                self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")
                expected = (
                    "this app is not allowed to write on the desktop"
                    if isinstance(error, PermissionError)
                    else "the icon could not be written on the desktop"
                )
                self.assertEqual(caught.exception.message, expected)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_a_desktop_that_does_not_exist_stops_the_command(self) -> None:
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="darwin", executable="/usr/bin/python3", desktop=self.root / "none")
        self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")


class OtherSystemTest(unittest.TestCase):
    def test_only_macos_and_windows_have_an_icon(self) -> None:
        for platform in ("linux", "freebsd14", "cygwin"):
            with self.subTest(platform=platform), self.assertRaises(ShortcutError) as caught:
                create_shortcut(platform=platform, executable="/usr/bin/python3", home=Path("/nowhere"))
            self.assertEqual(caught.exception.code, "SHORTCUT_NOT_SUPPORTED")


class WindowsRequestTest(TemporaryFolder):
    """What this command asks of Windows PowerShell, on any system."""

    def run_with(self, returncode: int, stdout: bytes = b"", **options: object) -> tuple[list[Path], dict]:
        seen: dict = {}

        def run(arguments, **keywords):  # type: ignore[no-untyped-def]
            seen.update(arguments=arguments, **keywords)
            if isinstance(options.get("error"), BaseException):
                raise options["error"]  # type: ignore[misc]
            return subprocess.CompletedProcess(arguments, returncode, stdout, b"")

        with mock.patch.object(shortcut.shutil, "which", return_value="C:\\Windows\\powershell.exe"):
            places = create_shortcut(
                platform="win32",
                executable=str(options.get("executable", "C:\\Python311\\python.exe")),
                home=Path("C:\\Profiles\\runner"),
                windows_folders=options.get("folders"),  # type: ignore[arg-type]
                run=run,
            )
        return places, seen

    def test_the_shortcuts_start_the_gui_minimized_with_the_python_that_ran_the_command(self) -> None:
        places, seen = self.run_with(0, "C:\\D\\Garmin Running Data Normalizer.lnk\r\nC:\\S\\Garmin Running Data Normalizer.lnk\r\n".encode())
        self.assertEqual(places, [Path("C:\\D\\Garmin Running Data Normalizer.lnk"), Path("C:\\S\\Garmin Running Data Normalizer.lnk")])
        self.assertEqual(seen["arguments"][:4], ["C:\\Windows\\powershell.exe", "-NoProfile", "-NonInteractive", "-Command"])
        self.assertEqual(seen["arguments"][4], shortcut.WINDOWS_SCRIPT)
        environment = seen["env"]
        self.assertEqual(environment["GRDN_SHORTCUT_NAME"], "Garmin Running Data Normalizer.lnk")
        self.assertEqual(environment["GRDN_SHORTCUT_TARGET"], "C:\\Python311\\python.exe")
        self.assertEqual(environment["GRDN_SHORTCUT_ARGUMENTS"], ARGUMENTS)
        self.assertEqual(environment["GRDN_SHORTCUT_HOME"], str(Path("C:\\Profiles\\runner")))
        # The system's desktop and Start menu, unless a test gives folders.
        self.assertEqual(environment["GRDN_SHORTCUT_FOLDERS"], "")
        script = shortcut.WINDOWS_SCRIPT
        self.assertIn("$link.WindowStyle = 7", script)
        self.assertIn("GetFolderPath('Desktop')", script)
        self.assertIn("GetFolderPath('Programs')", script)
        # Every place is checked before the first one is written, and a place
        # that holds anything else ends the script with 3.
        self.assertLess(script.index("Test-Path -LiteralPath $place"), script.index("$link.Save()"))
        self.assertEqual(script.count("{ exit 3 }"), 3)
        first, second = Path("C:\\a"), Path("C:\\b")
        _, seen = self.run_with(0, folders=[first, second])
        self.assertEqual(seen["env"]["GRDN_SHORTCUT_FOLDERS"], f"{first}\n{second}")

    def test_the_windowless_python_is_replaced_by_the_console_python_next_to_it(self) -> None:
        for name in ("pythonw.exe", "python.exe"):
            (self.root / name).write_bytes(b"")
        _, seen = self.run_with(0, executable=self.root / "pythonw.exe")
        self.assertEqual(seen["env"]["GRDN_SHORTCUT_TARGET"], str(self.root / "python.exe"))

    def test_the_answers_of_windows_powershell_give_the_codes(self) -> None:
        for returncode, code in ((3, "SHORTCUT_PLACE_TAKEN"), (4, "SHORTCUT_NOT_CREATED"), (1, "SHORTCUT_NOT_CREATED")):
            with self.subTest(returncode=returncode), self.assertRaises(ShortcutError) as caught:
                self.run_with(returncode)
            self.assertEqual(caught.exception.code, code)
        for error in (OSError("no such program"), subprocess.TimeoutExpired("powershell", 60)):
            with self.subTest(error=type(error).__name__), self.assertRaises(ShortcutError) as caught:
                self.run_with(0, error=error)
            self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")

    def test_a_system_without_windows_powershell_stops_the_command(self) -> None:
        with mock.patch.object(shortcut.shutil, "which", return_value=None), self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="win32", executable="C:\\Python311\\python.exe", home=self.root)
        self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")


def read_shortcut(place: Path) -> dict[str, object]:
    script = (
        "$link = (New-Object -ComObject WScript.Shell).CreateShortcut($env:GRDN_TEST_PLACE); "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::Out.WriteLine($link.TargetPath); [Console]::Out.WriteLine($link.Arguments); "
        "[Console]::Out.WriteLine($link.WorkingDirectory); [Console]::Out.WriteLine($link.WindowStyle)"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, "GRDN_TEST_PLACE": str(place)},
        capture_output=True,
        check=True,
    )
    target, arguments, folder, style = result.stdout.decode("utf-8").splitlines()[:4]
    return {"target": target, "arguments": arguments, "folder": folder, "style": int(style)}


@WINDOWS_ONLY
class WindowsShortcutTest(TemporaryFolder):
    """Real shortcuts in temporary folders, read back with Windows PowerShell."""

    def setUp(self) -> None:
        super().setUp()
        self.folders = [self.root / "デスクトップ", self.root / "Start Menu Programs"]
        for folder in self.folders:
            folder.mkdir()
        self.places = [folder / f"{NAME}.lnk" for folder in self.folders]

    def test_the_shortcuts_start_the_gui_minimized_in_the_home(self) -> None:
        made = create_shortcut(platform="win32", home=self.root, windows_folders=self.folders)
        self.assertEqual([Path(place) for place in made], self.places)
        for place in self.places:
            with self.subTest(place=place.parent.name):
                read = read_shortcut(place)
                self.assertEqual(Path(str(read["target"])).resolve(), Path(sys.executable).resolve())
                self.assertEqual(read["arguments"], ARGUMENTS)
                self.assertEqual(Path(str(read["folder"])), self.root)
                self.assertEqual(read["style"], 7)

    def test_the_shortcuts_of_this_command_are_made_again(self) -> None:
        create_shortcut(platform="win32", executable="C:\\Old\\python.exe", home=self.root, windows_folders=self.folders)
        create_shortcut(platform="win32", home=self.root, windows_folders=self.folders)
        for place in self.places:
            self.assertEqual(Path(str(read_shortcut(place)["target"])).resolve(), Path(sys.executable).resolve())

    def test_another_file_of_the_same_name_stops_the_command_before_any_is_written(self) -> None:
        self.places[1].write_bytes(b"not a shortcut")
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="win32", home=self.root, windows_folders=self.folders)
        self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")
        self.assertFalse(self.places[0].exists())
        self.assertEqual(self.places[1].read_bytes(), b"not a shortcut")
        self.places[1].unlink()
        self.places[1].mkdir()
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="win32", home=self.root, windows_folders=self.folders)
        self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")

    def test_a_shortcut_with_other_arguments_stops_the_command(self) -> None:
        create_shortcut(platform="win32", home=self.root, windows_folders=self.folders[:1])
        script = (
            "$link = (New-Object -ComObject WScript.Shell).CreateShortcut($env:GRDN_TEST_PLACE); "
            "$link.Arguments = '-m something_else'; $link.Save()"
        )
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            env={**os.environ, "GRDN_TEST_PLACE": str(self.places[0])},
            check=True,
        )
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="win32", home=self.root, windows_folders=self.folders)
        self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")
        self.assertEqual(read_shortcut(self.places[0])["arguments"], "-m something_else")
        self.assertFalse(self.places[1].exists())

    def test_a_folder_that_does_not_exist_stops_the_command(self) -> None:
        with self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="win32", home=self.root, windows_folders=[self.root / "none"])
        self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")


@WINDOWS_ONLY
class WindowsPowerShellLineTest(unittest.TestCase):
    def test_the_line_of_the_guide_runs_its_second_command_only_after_the_first_succeeded(self) -> None:
        # Windows PowerShell 5.1 has no "&&"; the guides join the two
        # commands with "if ($?) { … }" (stage E1d).
        for first, expected in (("cmd /c exit 1", "stopped"), ("cmd /c exit 0", "ran")):
            with self.subTest(first=first):
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                     f"{first}; if ($?) {{ 'ran' }} else {{ 'stopped' }}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertEqual(result.stdout.strip(), expected)


class CommandTest(unittest.TestCase):
    def test_the_gui_command_has_the_choice(self) -> None:
        self.assertIs(build_parser().parse_args(["gui"]).create_shortcut, False)
        self.assertIs(build_parser().parse_args(["gui", "--create-shortcut"]).create_shortcut, True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            build_parser().parse_args(["gui", "--help"])
        self.assertIn("--create-shortcut", output.getvalue())

    def test_the_icon_comes_first_and_then_the_gui_opens(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(shortcut, "create_shortcut", return_value=[Path("place-a"), Path("place-b")]) as made,
            mock.patch.object(command, "run_gui", return_value=0) as run_gui,
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(runner.main(["gui", "--create-shortcut", "--no-browser"]), 0)
        made.assert_called_once_with()
        self.assertEqual(run_gui.call_args.kwargs, {"open_browser": False})
        self.assertEqual(
            output.getvalue().splitlines(),
            [f"Icon that starts the GUI: {Path('place-a')}", f"Icon that starts the GUI: {Path('place-b')}"],
        )

    def test_an_icon_that_cannot_be_made_stops_the_command_before_the_gui(self) -> None:
        for code in SHORTCUT_CODES:
            errors = io.StringIO()
            with (
                self.subTest(code=code),
                mock.patch.object(shortcut, "create_shortcut", side_effect=ShortcutError(code, "what happened")),
                mock.patch.object(command, "run_gui", return_value=0) as run_gui,
                contextlib.redirect_stderr(errors),
            ):
                self.assertEqual(runner.main(["gui", "--create-shortcut"]), 2)
                run_gui.assert_not_called()
                self.assertEqual(errors.getvalue(), stops.stop_line(code, "what happened") + "\n")

    def test_without_the_choice_no_icon_is_made(self) -> None:
        with (
            mock.patch.object(shortcut, "create_shortcut") as made,
            mock.patch.object(command, "run_gui", return_value=0),
        ):
            self.assertEqual(runner.main(["gui", "--no-browser"]), 0)
        made.assert_not_called()


class StopCodeTest(unittest.TestCase):
    def test_the_codes_of_the_icon_are_the_cli_s_and_the_page_never_shows_them(self) -> None:
        page = set(flow_table("STOP_KEYS"))
        for code in SHORTCUT_CODES:
            with self.subTest(code=code):
                self.assertIn(code, stops.STOPS)
                self.assertNotIn(code, page)
                self.assertNotIn(code, stops.PAGE_STOPS)


if __name__ == "__main__":
    unittest.main()
