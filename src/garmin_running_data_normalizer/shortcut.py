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
    """A stop of ``gui --create-shortcut``: its code and what happened."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


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
# of this command ends it with 3, and any other failure with 4.
WINDOWS_SCRIPT = (
    "$ErrorActionPreference = 'Stop'; "
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "try { "
    "$shell = New-Object -ComObject WScript.Shell; "
    "$folders = if ($env:GRDN_SHORTCUT_FOLDERS) { $env:GRDN_SHORTCUT_FOLDERS -split \"`n\" } "
    "else { @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs')) }; "
    "$places = @($folders | ForEach-Object { Join-Path $_ $env:GRDN_SHORTCUT_NAME }); "
    "foreach ($place in $places) { "
    "if (Test-Path -LiteralPath $place) { "
    "$item = Get-Item -LiteralPath $place -Force; "
    "if ($item.PSIsContainer) { exit 3 }; "
    "try { $arguments = $shell.CreateShortcut($place).Arguments } catch { exit 3 }; "
    "if ($arguments -ne $env:GRDN_SHORTCUT_ARGUMENTS) { exit 3 } } }; "
    "foreach ($place in $places) { "
    "$link = $shell.CreateShortcut($place); "
    "$link.TargetPath = $env:GRDN_SHORTCUT_TARGET; "
    "$link.Arguments = $env:GRDN_SHORTCUT_ARGUMENTS; "
    "$link.WorkingDirectory = $env:GRDN_SHORTCUT_HOME; "
    "$link.WindowStyle = 7; "
    "$link.Description = $env:GRDN_SHORTCUT_DESCRIPTION; "
    "$link.Save(); "
    "[Console]::Out.WriteLine($place) } "
    "} catch { exit 4 }"
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
            [powershell, "-NoProfile", "-NonInteractive", "-Command", WINDOWS_SCRIPT],
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
        raise ShortcutError("SHORTCUT_NOT_CREATED", "Windows PowerShell could not make the shortcut")
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
