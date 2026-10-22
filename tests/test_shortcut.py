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
import re
import stat
import struct
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
    MAC_PICTURE,
    NAME,
    NO_PICTURE_NOTE,
    ShortcutError,
    Shortcuts,
    WINDOWS_PICTURE,
    create_shortcut,
    mac_script,
)
from tests.test_gui_guides import one_lines
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


def set_picture(arguments, **keywords):  # type: ignore[no-untyped-def]
    """A stand-in for osascript that gives the file its picture."""
    return subprocess.CompletedProcess(arguments, 0, b"set\n", b"")


class MacFileTest(TemporaryFolder):
    def make(self, **options: object) -> Shortcuts:
        options.setdefault("platform", "darwin")
        options.setdefault("executable", "/usr/bin/python3")
        options.setdefault("run", set_picture)
        return create_shortcut(**options)  # type: ignore[arg-type]

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
        made = self.make(home=self.root)
        place = desktop / f"{NAME}.command"
        self.assertEqual(made, Shortcuts([place], picture=True))
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
        [place] = self.make(executable=str(python), desktop=desktop).places
        result = subprocess.run(["/bin/sh", str(place)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, f"{python}|-P|-m|garmin_running_data_normalizer|gui|")

    def test_the_file_that_this_command_made_is_replaced(self) -> None:
        self.make(executable="/old/python3", desktop=self.root)
        [place] = self.make(executable="/new/python3", desktop=self.root).places
        self.assertEqual(place.read_text(encoding="utf-8"), mac_script("/new/python3"))
        self.assertEqual([path.name for path in self.root.iterdir()], [place.name])

    def test_another_file_of_the_same_name_stops_the_command_and_stays(self) -> None:
        place = self.root / f"{NAME}.command"
        for text in ("#!/bin/sh\necho mine\n", f"#!/bin/zsh\n{MAC_MARK}\n", f"{MAC_MARK}\n"):
            with self.subTest(text=text):
                place.write_text(text, encoding="utf-8")
                with self.assertRaises(ShortcutError) as caught:
                    self.make(desktop=self.root)
                self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")
                self.assertEqual(place.read_text(encoding="utf-8"), text)
        place.unlink()
        place.mkdir()
        with self.assertRaises(ShortcutError) as caught:
            self.make(desktop=self.root)
        self.assertEqual(caught.exception.code, "SHORTCUT_PLACE_TAKEN")

    @POSIX_ONLY
    def test_a_link_of_the_same_name_stops_the_command(self) -> None:
        target = self.root / "target.command"
        target.write_text(mac_script("/usr/bin/python3"), encoding="utf-8")
        (self.root / f"{NAME}.command").symlink_to(target)
        with self.assertRaises(ShortcutError) as caught:
            self.make(desktop=self.root)
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
                    self.make(desktop=self.root)
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
            self.make(desktop=self.root / "none")
        self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")

    def test_the_file_gets_its_picture_once_it_is_in_its_place(self) -> None:
        # The picture and the hidden extension live beside the content of the
        # file, so a new file needs them again (stage E1i).
        seen = []

        def run(arguments, **keywords):  # type: ignore[no-untyped-def]
            place = Path(arguments[5])
            seen.append((arguments, keywords, place.read_text(encoding="utf-8"), stat.S_IMODE(place.stat().st_mode)))
            return set_picture(arguments)

        executables = ("/old/python3", "/new/python3")
        for executable in executables:
            self.make(executable=executable, desktop=self.root, run=run)
        place = self.root / f"{NAME}.command"
        self.assertEqual(len(seen), 2)
        for (arguments, keywords, text, mode), executable in zip(seen, executables):
            self.assertEqual(
                arguments,
                ["/usr/bin/osascript", "-l", "JavaScript", "-e", shortcut.MAC_PICTURE_SCRIPT, str(place), str(MAC_PICTURE)],
            )
            self.assertEqual(keywords["timeout"], shortcut.OSASCRIPT_TIMEOUT_SECONDS)
            self.assertEqual(text, mac_script(executable))
            if os.name != "nt":
                self.assertEqual(mode, 0o700)
        self.assertIn("setIconForFileOptions(image, argv[0], 0)", shortcut.MAC_PICTURE_SCRIPT)
        self.assertIn("NSFileExtensionHidden: true", shortcut.MAC_PICTURE_SCRIPT)
        self.assertTrue(MAC_PICTURE.is_file())

    def test_an_icon_without_its_picture_still_starts_the_gui(self) -> None:
        def answer(returncode: int, stdout: bytes):  # type: ignore[no-untyped-def]
            return lambda arguments, **keywords: subprocess.CompletedProcess(arguments, returncode, stdout, b"")

        def fail(error: BaseException):  # type: ignore[no-untyped-def]
            def run(arguments, **keywords):  # type: ignore[no-untyped-def]
                raise error

            return run

        place = self.root / f"{NAME}.command"
        for label, run in (
            ("not set", answer(0, b"not set\n")),
            ("no picture", answer(0, b"no picture\n")),
            ("an error of osascript", answer(1, b"")),
            ("no osascript", fail(FileNotFoundError(2, "No such file or directory"))),
            ("too slow", fail(subprocess.TimeoutExpired("osascript", 30))),
        ):
            with self.subTest(label):
                self.assertEqual(self.make(desktop=self.root, run=run), Shortcuts([place], picture=False))
                self.assertEqual(place.read_text(encoding="utf-8"), mac_script("/usr/bin/python3"))
        # Without the picture, osascript is not asked.
        made = self.make(desktop=self.root, picture=self.root / "none.icns", run=fail(AssertionError("asked")))
        self.assertEqual(made, Shortcuts([place], picture=False))

    @unittest.skipUnless(hasattr(os, "setxattr"), "extended attributes as Linux has them")
    def test_attributes_beside_the_content_do_not_change_what_is_made_here(self) -> None:
        self.make(desktop=self.root)
        place = self.root / f"{NAME}.command"
        try:
            os.setxattr(place, "user.picture", b"picture")
        except OSError:
            self.skipTest("this file system takes no extended attributes")
        self.assertEqual(self.make(executable="/new/python3", desktop=self.root).places, [place])
        self.assertEqual(place.read_text(encoding="utf-8"), mac_script("/new/python3"))


@unittest.skipUnless(
    sys.platform == "darwin" and Path("/usr/bin/osascript").is_file(), "macOS gives the picture of a file"
)
class MacPictureTest(TemporaryFolder):
    """The picture that macOS gives, in a temporary folder only (stage E1i)."""

    def test_macos_gives_the_picture_and_the_file_stays_one_that_this_command_made(self) -> None:
        for executable in ("/old/python3", "/new/python3"):
            made = create_shortcut(platform="darwin", executable=executable, desktop=self.root)
            self.assertTrue(made.picture)
            [place] = made.places
            names = subprocess.run(["xattr", str(place)], capture_output=True, text=True, check=True).stdout.split()
            self.assertIn("com.apple.ResourceFork", names)
            finder = subprocess.run(
                ["xattr", "-px", "com.apple.FinderInfo", str(place)], capture_output=True, text=True, check=True
            ).stdout.split()
            flags = int(finder[8] + finder[9], 16)
            self.assertTrue(flags & 0x0400, "the picture of the file")
            self.assertTrue(flags & 0x0010, "the hidden extension")
            self.assertEqual(place.read_text(encoding="utf-8"), mac_script(executable))
            self.assertEqual(stat.S_IMODE(place.stat().st_mode), 0o700)


class OtherSystemTest(unittest.TestCase):
    def test_only_macos_and_windows_have_an_icon(self) -> None:
        for platform in ("linux", "freebsd14", "cygwin"):
            with self.subTest(platform=platform), self.assertRaises(ShortcutError) as caught:
                create_shortcut(platform=platform, executable="/usr/bin/python3", home=Path("/nowhere"))
            self.assertEqual(caught.exception.code, "SHORTCUT_NOT_SUPPORTED")


class WindowsRequestTest(TemporaryFolder):
    """What this command asks of Windows PowerShell, on any system."""

    def run_with(self, returncode: int, stdout: bytes = b"", **options: object) -> tuple[Shortcuts, dict]:
        seen: dict = {}

        def run(arguments, **keywords):  # type: ignore[no-untyped-def]
            seen.update(arguments=arguments, **keywords)
            if isinstance(options.get("error"), BaseException):
                raise options["error"]  # type: ignore[misc]
            return subprocess.CompletedProcess(arguments, returncode, stdout, options.get("stderr", b""))

        with mock.patch.object(shortcut.shutil, "which", return_value="C:\\Windows\\powershell.exe"):
            made = create_shortcut(
                platform="win32",
                executable=str(options.get("executable", "C:\\Python311\\python.exe")),
                home=Path("C:\\Profiles\\runner"),
                windows_folders=options.get("folders"),  # type: ignore[arg-type]
                picture=options.get("picture"),  # type: ignore[arg-type]
                run=run,
            )
        return made, seen

    def test_the_shortcuts_start_the_gui_minimized_with_the_python_that_ran_the_command(self) -> None:
        made, seen = self.run_with(0, "C:\\D\\Garmin Running Data Normalizer.lnk\r\nC:\\S\\Garmin Running Data Normalizer.lnk\r\n".encode())
        self.assertEqual(
            made,
            Shortcuts([Path("C:\\D\\Garmin Running Data Normalizer.lnk"), Path("C:\\S\\Garmin Running Data Normalizer.lnk")], picture=True),
        )
        self.assertEqual(seen["arguments"][:5], ["C:\\Windows\\powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-Command"])
        self.assertEqual(seen["arguments"][5], shortcut.WINDOWS_SCRIPT)
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
        self.assertEqual(script.count("{ exit 3 }"), 2)
        # WScript.Shell reads and saves only in the temporary folder, under a
        # name of plain letters; the shortcut is moved to its place.
        self.assertNotIn("CreateShortcut($place)", script)
        self.assertIn("$shell.CreateShortcut($copy).Arguments", script)
        self.assertIn("Move-Item -LiteralPath $temporary -Destination $place -Force", script)
        # A temporary folder with other letters gives way to its short name,
        # and then to the temporary folder of Windows.
        self.assertEqual(script.count("if ($temp -match '[^\\x00-\\x7F]')"), 2)
        # WScript.Shell is given only plain letters: a Python or a home folder
        # with other letters stands in as cmd.exe or the temporary folder.
        self.assertIn("if ($env:GRDN_SHORTCUT_TARGET -match '[^\\x00-\\x7F]') { Join-Path $env:SystemRoot 'System32\\cmd.exe' }", script)
        self.assertIn("if ($env:GRDN_SHORTCUT_HOME -match '[^\\x00-\\x7F]') { $temp }", script)
        self.assertLess(script.index(".ShortPath"), script.index("Join-Path $env:SystemRoot 'Temp'"))
        self.assertLess(script.index("Join-Path $env:SystemRoot 'Temp'"), script.index("$copy = Join-Path $temp"))
        # The Python, the home folder, and the description are written again
        # with Shell.Application, which keeps letters that WScript.Shell may
        # lose, before the shortcut is moved to its place.
        for line in ("$saved.Path = $env:GRDN_SHORTCUT_TARGET", "$saved.WorkingDirectory = $env:GRDN_SHORTCUT_HOME",
                     "$saved.Description = $env:GRDN_SHORTCUT_DESCRIPTION"):
            self.assertLess(script.index("$link.Save()"), script.index(line))
            self.assertLess(script.index(line), script.index("$saved.Save()"))
        self.assertLess(script.index("$saved.Save()"), script.index("Move-Item -LiteralPath $temporary"))
        # Windows PowerShell 5.1 takes no -Leaf with -LiteralPath in Split-Path;
        # .NET names the folder and the file of a place in every version.
        self.assertNotIn("Split-Path", script)
        self.assertIn("[System.IO.Path]::GetDirectoryName($temporary)", script)
        self.assertIn("[System.IO.Path]::GetFileName($temporary)", script)
        # The ShellLinkObject also points the shortcut to the picture of the
        # icon in the package, never WScript.Shell (stage E1i).
        self.assertEqual(environment["GRDN_SHORTCUT_PICTURE"], str(WINDOWS_PICTURE))
        self.assertTrue(WINDOWS_PICTURE.is_file())
        picture = "$saved.SetIconLocation($env:GRDN_SHORTCUT_PICTURE, 0)"
        self.assertLess(script.index("$saved.Description = $env:GRDN_SHORTCUT_DESCRIPTION"), script.index(picture))
        self.assertLess(script.index(picture), script.index("$saved.Save()"))
        self.assertNotIn("IconLocation =", script)
        first, second = Path("C:\\a"), Path("C:\\b")
        _, seen = self.run_with(0, folders=[first, second])
        self.assertEqual(seen["env"]["GRDN_SHORTCUT_FOLDERS"], f"{first}\n{second}")

    def test_the_reader_of_a_shortcut_finds_its_picture(self) -> None:
        # The bytes of a shortcut as [MS-SHLLINK] lays them out, so that the
        # reader of the Windows tests is checked on every system.
        def strings(*texts: str) -> bytes:
            return b"".join(struct.pack("<H", len(text)) + text.encode("utf-16-le") for text in texts)

        header = bytearray(0x4C)
        struct.pack_into("<I", header, 0, 0x4C)
        struct.pack_into("<I", header, 0x14, 0x80 | 0x10 | 0x20 | 0x40)
        struct.pack_into("<i", header, 0x38, 0)
        body = bytes(header) + strings("C:\\ホーム", ARGUMENTS, "C:\\テスト\\icon.ico")
        place = self.root / "plain.lnk"
        place.write_bytes(body + struct.pack("<I", 0))
        self.assertEqual(shortcut_picture(place), ("C:\\テスト\\icon.ico", 0))
        target = "C:\\Profiles\\ホーム\\icon.ico"
        block = struct.pack("<II", 0x314, 0xA0000007) + bytes(260) + target.encode("utf-16-le").ljust(520, b"\0")
        place.write_bytes(body + block + struct.pack("<I", 0))
        self.assertEqual(shortcut_picture(place), (target, 0))

    def test_a_shortcut_without_its_picture_still_starts_the_gui(self) -> None:
        made, _ = self.run_with(0, "C:\\D\\x.lnk\r\nC:\\S\\x.lnk\r\nNO-PICTURE\r\n".encode())
        self.assertEqual(made, Shortcuts([Path("C:\\D\\x.lnk"), Path("C:\\S\\x.lnk")], picture=False))
        script = shortcut.WINDOWS_SCRIPT
        self.assertIn("catch { $pictured = $false } } else { $pictured = $false }", script)
        self.assertIn("if (-not $pictured) { [Console]::Out.WriteLine('NO-PICTURE') }", script)
        # Without the picture, the script is not asked to point to one.
        _, seen = self.run_with(0, picture=self.root / "none.ico")
        self.assertEqual(seen["env"]["GRDN_SHORTCUT_PICTURE"], "")

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

    def test_what_windows_powershell_said_is_kept_but_not_printed(self) -> None:
        with self.assertRaises(ShortcutError) as caught:
            self.run_with(4, stderr="Unable to save shortcut\r\n".encode())
        self.assertEqual(caught.exception.message, "Windows PowerShell could not make the shortcut")
        self.assertEqual(caught.exception.detail, "Unable to save shortcut")
        self.assertNotIn("Unable", stops.stop_line(caught.exception.code, caught.exception.message))

    def test_a_system_without_windows_powershell_stops_the_command(self) -> None:
        with mock.patch.object(shortcut.shutil, "which", return_value=None), self.assertRaises(ShortcutError) as caught:
            create_shortcut(platform="win32", executable="C:\\Python311\\python.exe", home=self.root)
        self.assertEqual(caught.exception.code, "SHORTCUT_NOT_CREATED")


def on_shortcut(place: Path, script: str) -> str:
    """Run a script on the ShellLinkObject of a shortcut, with Shell.Application,
    which keeps every letter of its place and of its fields, and give its output."""
    opening = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$application = New-Object -ComObject Shell.Application; "
        "$link = $application.Namespace([System.IO.Path]::GetDirectoryName($env:GRDN_TEST_PLACE))"
        ".ParseName([System.IO.Path]::GetFileName($env:GRDN_TEST_PLACE)).GetLink; "
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-Command", opening + script],
        env={**os.environ, "GRDN_TEST_PLACE": str(place)},
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8")


def read_shortcut(place: Path) -> dict[str, object]:
    script = (
        "[Console]::Out.WriteLine($link.Path); [Console]::Out.WriteLine($link.Arguments); "
        "[Console]::Out.WriteLine($link.WorkingDirectory); [Console]::Out.WriteLine($link.ShowCommand)"
    )
    target, arguments, folder, style = on_shortcut(place, script).splitlines()[:4]
    return {"target": target, "arguments": arguments, "folder": folder, "style": int(style)}


def shortcut_picture(place: Path) -> tuple[str, int]:
    """The picture that a shortcut points to and its index, read from its
    bytes as [MS-SHLLINK] lays them out: the string ICON_LOCATION, or the
    IconEnvironmentDataBlock when Windows keeps it with an environment
    variable. Reading the bytes keeps every letter of the place."""
    data = place.read_bytes()
    (flags,) = struct.unpack_from("<I", data, 0x14)
    (index,) = struct.unpack_from("<i", data, 0x38)
    position = 0x4C
    if flags & 0x01:  # HasLinkTargetIDList
        (size,) = struct.unpack_from("<H", data, position)
        position += 2 + size
    if flags & 0x02:  # HasLinkInfo
        (size,) = struct.unpack_from("<I", data, position)
        position += size
    width, encoding = (2, "utf-16-le") if flags & 0x80 else (1, "latin-1")  # IsUnicode
    location = ""
    # The strings of a shortcut, in their order: the name, the relative path,
    # the working directory, the arguments, and the place of its picture.
    for flag in (0x04, 0x08, 0x10, 0x20, 0x40):
        if flags & flag:
            (count,) = struct.unpack_from("<H", data, position)
            text = data[position + 2 : position + 2 + count * width].decode(encoding)
            position += 2 + count * width
            if flag == 0x40:
                location = text
    while position + 8 <= len(data):
        size, signature = struct.unpack_from("<II", data, position)
        if size < 8:
            break
        if signature == 0xA0000007:  # IconEnvironmentDataBlock, after 260 bytes of ANSI
            target = data[position + 8 + 260 : position + 8 + 260 + 520].decode("utf-16-le").split("\0", 1)[0]
            location = target or location
        position += size
    return os.path.expandvars(location), index


@WINDOWS_ONLY
class WindowsShortcutTest(TemporaryFolder):
    """Real shortcuts in temporary folders, read back with Windows PowerShell."""

    def setUp(self) -> None:
        super().setUp()
        self.folders = [self.root / "デスクトップ", self.root / "Start Menu Programs"]
        for folder in self.folders:
            folder.mkdir()
        self.places = [folder / f"{NAME}.lnk" for folder in self.folders]

    def make(self, folders: list[Path] | None = None, **options: object) -> Shortcuts:
        options.setdefault("home", self.root)
        try:
            return create_shortcut(
                platform="win32", windows_folders=self.folders if folders is None else folders, **options
            )
        except ShortcutError as exc:
            self.fail(f"{exc.code}: {exc.message}; Windows PowerShell said: {exc.detail}")

    def test_the_shortcuts_in_folders_of_plain_letters(self) -> None:
        folders = [self.root / "Desktop", self.root / "Programs"]
        for folder in folders:
            folder.mkdir()
        self.assertEqual(self.make(folders).places, [folder / f"{NAME}.lnk" for folder in folders])
        self.assertEqual(read_shortcut(folders[0] / f"{NAME}.lnk")["arguments"], ARGUMENTS)

    def test_a_temporary_folder_with_other_letters_is_not_given_to_wscript_shell(self) -> None:
        temporary = self.root / "一時"
        temporary.mkdir()
        with mock.patch.dict(os.environ, {"TEMP": str(temporary), "TMP": str(temporary)}):
            made = self.make()
        self.assertEqual(made.places, self.places)
        self.assertEqual(read_shortcut(self.places[0])["arguments"], ARGUMENTS)
        self.assertEqual(list(temporary.iterdir()), [])

    def test_letters_of_other_scripts_inside_the_shortcut_are_kept(self) -> None:
        # A home folder and a Python whose places have letters that the
        # Windows of the runner cannot write in its code page.
        python = self.root / "テスト" / "python.exe"
        python.parent.mkdir()
        python.write_bytes(b"")
        home = self.root / "ホーム"
        home.mkdir()
        picture = python.parent / "icon.ico"
        picture.write_bytes(WINDOWS_PICTURE.read_bytes())
        self.assertTrue(self.make(executable=str(python), home=home, picture=picture).picture)
        for place in self.places:
            with self.subTest(place=place.parent.name):
                read = read_shortcut(place)
                # Windows gives the Python of a shortcut by the long names of
                # its folders, also when it was given a short name, as the
                # temporary folder of the runner is; the places are resolved.
                self.assertEqual(Path(str(read["target"])).resolve(), python.resolve())
                self.assertEqual(Path(str(read["folder"])).resolve(), home.resolve())
                self.assertEqual(read["arguments"], ARGUMENTS)
                self.assertNotIn("?", f"{read['target']}{read['folder']}")
                location, index = shortcut_picture(place)
                self.assertEqual((Path(location).resolve(), index), (picture.resolve(), 0))
                self.assertNotIn("?", location)

    def test_the_shortcuts_start_the_gui_minimized_in_the_home(self) -> None:
        made = self.make()
        self.assertEqual(made, Shortcuts(self.places, picture=True))
        for place in self.places:
            with self.subTest(place=place.parent.name):
                read = read_shortcut(place)
                self.assertEqual(Path(str(read["target"])).resolve(), Path(sys.executable).resolve())
                self.assertEqual(read["arguments"], ARGUMENTS)
                self.assertEqual(Path(str(read["folder"])), self.root)
                self.assertEqual(read["style"], 7)
                # The picture of the icon in the package (stage E1i).
                location, index = shortcut_picture(place)
                self.assertEqual((Path(location).resolve(), index), (WINDOWS_PICTURE.resolve(), 0))

    def test_the_shortcuts_of_this_command_are_made_again(self) -> None:
        # The Python that the icon started before, as after Python is
        # replaced; a shortcut points to a Python that is there.
        old_python = self.root / "Old" / "python.exe"
        old_python.parent.mkdir()
        old_python.write_bytes(b"")
        self.make(executable=str(old_python))
        self.assertEqual(Path(str(read_shortcut(self.places[0])["target"])).resolve(), old_python.resolve())
        self.make()
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
        self.make(self.folders[:1])
        on_shortcut(self.places[0], "$link.Arguments = '-m something_else'; $link.Save()")
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
    """The line of the guides in Windows PowerShell 5.1, which has no "&&",
    with a stand-in for each of its parts."""

    @staticmethod
    def said(line: str) -> list[str]:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", line], capture_output=True, text=True
        )
        return result.stdout.split()

    def test_the_line_of_the_guide_runs_each_part_only_after_the_one_before_it_succeeded(self) -> None:
        [_, (_, line)] = one_lines("en")
        parts = re.fullmatch(r"(.+?); if \(\$\?\) \{ (.+?); if \(\$\?\) \{ (.+) \} \}", line)
        assert parts is not None
        names = ("venv", "install", "icon")
        for failing in (*names, None):
            stand_in = line
            for name, part in zip(names, parts.groups()):
                stand_in = stand_in.replace(part, f'cmd /c "echo {name}& exit {int(name == failing)}"')
            with self.subTest(failing=failing):
                ran = list(names[: names.index(failing) + 1]) if failing else list(names)
                self.assertEqual(self.said(stand_in), ran)

    def test_an_if_that_reads_the_answer_leaves_it_true(self) -> None:
        # The reason why the guides put one "if" inside the other (stage
        # E1i): with two in a row, the third part ran after the first failed.
        self.assertEqual(
            self.said('cmd /c "echo A& exit 1"; if ($?) { cmd /c "echo B& exit 0" }; if ($?) { cmd /c "echo C& exit 0" }'),
            ["A", "C"],
        )


class CommandTest(unittest.TestCase):
    def test_the_gui_command_has_the_choice(self) -> None:
        self.assertIs(build_parser().parse_args(["gui"]).create_shortcut, False)
        self.assertIs(build_parser().parse_args(["gui", "--create-shortcut"]).create_shortcut, True)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            build_parser().parse_args(["gui", "--help"])
        self.assertIn("--create-shortcut", output.getvalue())

    def test_the_icon_comes_first_and_then_the_gui_opens(self) -> None:
        places = [Path("place-a"), Path("place-b")]
        lines = [f"Icon that starts the GUI: {place}" for place in places]
        # An icon without its picture still starts the GUI: one line says so,
        # not an ERROR line, and the GUI opens (stage E1i).
        for picture, said in ((True, lines), (False, [*lines, NO_PICTURE_NOTE])):
            output = io.StringIO()
            with (
                self.subTest(picture=picture),
                mock.patch.object(shortcut, "create_shortcut", return_value=Shortcuts(places, picture)) as made,
                mock.patch.object(command, "run_gui", return_value=0) as run_gui,
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(runner.main(["gui", "--create-shortcut", "--no-browser"]), 0)
                made.assert_called_once_with()
                self.assertEqual(run_gui.call_args.kwargs, {"open_browser": False})
            self.assertEqual(output.getvalue().splitlines(), said)
        self.assertNotIn("ERROR", NO_PICTURE_NOTE)

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
