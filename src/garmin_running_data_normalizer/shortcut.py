"""The icon that starts the GUI (stage E1d, decision 20261021-1).

``gui --create-shortcut`` makes it before the GUI opens: on macOS a file on
the desktop that the Terminal runs, and on Windows a shortcut on the desktop
and in the Start menu, whose window opens minimized. Both start the GUI with
the Python that runs the command, as the command does: the terminal's window
stays open while the GUI is used, and closing it stops the GUI. The icon holds
no key, since every launch makes its own. Other systems have no icon; there
the GUI starts with the command.

An icon is replaced only when this command made it: on macOS, a file whose
second line is the mark below, and on Windows, a shortcut with the arguments
below, whatever Python it starts, so that the command makes it again after
Python is replaced. Any other file of the same name stops the command.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

NAME = "Garmin Running Data Normalizer"
# -P keeps the folder where the icon starts Python, the home folder, out of the
# places of the modules, as the child of a run is started (gui/runs.py).
ARGUMENTS = "-P -m garmin_running_data_normalizer gui"
MAC_MARK = "# Garmin Running Data Normalizer: starts the GUI."
# The first bytes that tell whether a file on the desktop is the one that this
# command made; the mark is in its second line.
_HEAD_BYTES = 4096
POWERSHELL_TIMEOUT_SECONDS = 60.0


class ShortcutError(Exception):
    """A stop of ``gui --create-shortcut``: its code and what happened. The
    detail, such as what Windows PowerShell said, is for the tests and is
    never printed, since it can name places."""

    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def mac_script(executable: str) -> str:
    """The file that starts the GUI on macOS. The Terminal runs it in a
    window of its own, which shows the address of the GUI."""
    return (
        "#!/bin/sh\n"
        f"{MAC_MARK}\n"
        '# Made by "garmin-running-data-normalizer gui --create-shortcut"; run that\n'
        "# command again after Python is replaced.\n"
        f"exec {_shell_quoted(executable)} {ARGUMENTS}\n"
    )


def _shell_quoted(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def _made_here(place: Path) -> bool:
    try:
        with place.open("rb") as handle:
            head = handle.read(_HEAD_BYTES)
    except OSError:
        return False
    lines = head.decode("utf-8", "replace").split("\n")
    return len(lines) > 1 and lines[0] == "#!/bin/sh" and lines[1] == MAC_MARK


def _create_on_mac(executable: str, desktop: Path) -> list[Path]:
    place = desktop / f"{NAME}.command"
    # A desktop that the Terminal may not use, because its person answered
    # Don't Allow to the question of macOS, refuses even the look at the file.
    try:
        taken = place.is_symlink() or (place.exists() and not (place.is_file() and _made_here(place)))
        if taken:
            raise ShortcutError(
                "SHORTCUT_PLACE_TAKEN",
                f"the desktop has a file named {place.name} that this app did not make",
            )
        handle, temporary = tempfile.mkstemp(prefix=f".{NAME}.", suffix=".command", dir=desktop)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(mac_script(executable))
            os.chmod(temporary, 0o700)
            os.replace(temporary, place)
        except BaseException:
            # The temporary file of this command does not stay on the desktop.
            Path(temporary).unlink(missing_ok=True)
            raise
    except PermissionError as exc:
        raise ShortcutError("SHORTCUT_NOT_CREATED", "this app is not allowed to write on the desktop") from exc
    except OSError as exc:
        raise ShortcutError("SHORTCUT_NOT_CREATED", "the icon could not be written on the desktop") from exc
    return [place]


# The script that makes the shortcuts on Windows. The places come from the
# environment, so that no name is quoted into the script. It checks every
# place before it writes one: a place that holds anything else than a shortcut
# of this command ends it with 3, and any other failure with 4, after it says
# why on the standard error. WScript.Shell reads and saves a shortcut only in
# the temporary folder, under a name of plain letters, and the shortcut is
# then copied from or moved to its place: a place such as a desktop that
# OneDrive keeps as "デスクトップ" holds letters that it may not take. When the
# temporary folder itself has such letters, as under a home folder of another
# script, its short name of plain letters is used, and without one, the
# temporary folder of Windows. WScript.Shell may also lose such letters inside
# the shortcut, so it is given only plain letters (a Python or a home folder
# with other letters stands in as cmd.exe or the temporary folder), and the
# Python, the home folder, and the description are then written with the
# ShellLinkObject of Shell.Application, which keeps them. Until then the
# shortcut is only in the temporary folder, so no stand-in reaches a place.
WINDOWS_SCRIPT = (
    "$ErrorActionPreference = 'Stop'; "
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "try { "
    "$shell = New-Object -ComObject WScript.Shell; "
    "$application = New-Object -ComObject Shell.Application; "
    "$temp = [System.IO.Path]::GetTempPath(); "
    "if ($temp -match '[^\\x00-\\x7F]') { $temp = (New-Object -ComObject Scripting.FileSystemObject).GetFolder($temp).ShortPath }; "
    "if ($temp -match '[^\\x00-\\x7F]') { $temp = Join-Path $env:SystemRoot 'Temp' }; "
    "$folders = if ($env:GRDN_SHORTCUT_FOLDERS) { $env:GRDN_SHORTCUT_FOLDERS -split \"`n\" } "
    "else { @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs')) }; "
    "$places = @($folders | ForEach-Object { Join-Path $_ $env:GRDN_SHORTCUT_NAME }); "
    "foreach ($place in $places) { "
    "if (Test-Path -LiteralPath $place) { "
    "$item = Get-Item -LiteralPath $place -Force; "
    "if ($item.PSIsContainer) { exit 3 }; "
    "$copy = Join-Path $temp ('grdn-' + [guid]::NewGuid().ToString('N') + '.lnk'); "
    "Copy-Item -LiteralPath $place -Destination $copy; "
    "try { $arguments = $shell.CreateShortcut($copy).Arguments } catch { $arguments = $null } "
    "finally { Remove-Item -LiteralPath $copy -Force }; "
    "if ($arguments -ne $env:GRDN_SHORTCUT_ARGUMENTS) { exit 3 } } }; "
    "foreach ($place in $places) { "
    "$temporary = Join-Path $temp ('grdn-' + [guid]::NewGuid().ToString('N') + '.lnk'); "
    "$link = $shell.CreateShortcut($temporary); "
    "$link.TargetPath = if ($env:GRDN_SHORTCUT_TARGET -match '[^\\x00-\\x7F]') { Join-Path $env:SystemRoot 'System32\\cmd.exe' } else { $env:GRDN_SHORTCUT_TARGET }; "
    "$link.Arguments = $env:GRDN_SHORTCUT_ARGUMENTS; "
    "$link.WorkingDirectory = if ($env:GRDN_SHORTCUT_HOME -match '[^\\x00-\\x7F]') { $temp } else { $env:GRDN_SHORTCUT_HOME }; "
    "$link.WindowStyle = 7; "
    "$link.Description = $env:GRDN_SHORTCUT_DESCRIPTION; "
    "$link.Save(); "
    "$saved = $application.Namespace([System.IO.Path]::GetDirectoryName($temporary)).ParseName([System.IO.Path]::GetFileName($temporary)).GetLink; "
    "$saved.Path = $env:GRDN_SHORTCUT_TARGET; "
    "$saved.WorkingDirectory = $env:GRDN_SHORTCUT_HOME; "
    "$saved.Description = $env:GRDN_SHORTCUT_DESCRIPTION; "
    "$saved.Save(); "
    "Move-Item -LiteralPath $temporary -Destination $place -Force; "
    "$temporary = $null; "
    "[Console]::Out.WriteLine($place) } "
    "} catch { [Console]::Error.WriteLine($_.Exception.Message); "
    "if ($temporary -and (Test-Path -LiteralPath $temporary)) { Remove-Item -LiteralPath $temporary -Force }; "
    "exit 4 }"
)


def _windows_python(executable: str) -> str:
    """The console Python next to ``executable``: the shortcut opens its
    window minimized, which the windowless pythonw.exe does not have."""
    path = Path(executable)
    if path.name.lower() == "pythonw.exe":
        console = path.with_name("python.exe")
        if console.is_file():
            return str(console)
    return executable


def _create_on_windows(
    executable: str,
    folders: Sequence[Path] | None,
    home: Path,
    run: Callable[..., Any],
) -> list[Path]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        raise ShortcutError("SHORTCUT_NOT_CREATED", "Windows PowerShell, which makes the shortcut, was not found")
    environment = {
        **os.environ,
        "GRDN_SHORTCUT_NAME": f"{NAME}.lnk",
        "GRDN_SHORTCUT_TARGET": _windows_python(executable),
        "GRDN_SHORTCUT_ARGUMENTS": ARGUMENTS,
        "GRDN_SHORTCUT_HOME": str(home),
        "GRDN_SHORTCUT_DESCRIPTION": f"Starts the GUI of {NAME}",
        "GRDN_SHORTCUT_FOLDERS": "\n".join(str(folder) for folder in folders) if folders else "",
    }
    try:
        result = run(
            [powershell, "-NoProfile", "-NonInteractive", "-STA", "-Command", WINDOWS_SCRIPT],
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=POWERSHELL_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ShortcutError("SHORTCUT_NOT_CREATED", "Windows PowerShell could not make the shortcut") from exc
    if result.returncode == 3:
        raise ShortcutError(
            "SHORTCUT_PLACE_TAKEN",
            f"the desktop or the Start menu has a file named {NAME}.lnk that this app did not make",
        )
    if result.returncode != 0:
        said = result.stderr.decode("utf-8", "replace") if isinstance(result.stderr, bytes) else result.stderr
        raise ShortcutError(
            "SHORTCUT_NOT_CREATED", "Windows PowerShell could not make the shortcut", (said or "").strip() or None
        )
    output = result.stdout.decode("utf-8", "replace") if isinstance(result.stdout, bytes) else result.stdout
    return [Path(line) for line in output.splitlines() if line.strip()]


def create_shortcut(
    *,
    platform: str | None = None,
    executable: str | None = None,
    home: Path | None = None,
    desktop: Path | None = None,
    windows_folders: Sequence[Path] | None = None,
    run: Callable[..., Any] = subprocess.run,
) -> list[Path]:
    """Make the icon that starts the GUI, and return where it is. The tests
    give the places; the command uses those of the system."""
    platform = sys.platform if platform is None else platform
    executable = sys.executable if executable is None else executable
    home = Path.home() if home is None else home
    if platform == "darwin":
        return _create_on_mac(executable, home / "Desktop" if desktop is None else desktop)
    if platform == "win32":
        return _create_on_windows(executable, windows_folders, home, run)
    raise ShortcutError("SHORTCUT_NOT_SUPPORTED", "an icon that starts the GUI can be made only on macOS and Windows")


__all__ = [
    "ARGUMENTS",
    "MAC_MARK",
    "NAME",
    "ShortcutError",
    "WINDOWS_SCRIPT",
    "create_shortcut",
    "mac_script",
]
