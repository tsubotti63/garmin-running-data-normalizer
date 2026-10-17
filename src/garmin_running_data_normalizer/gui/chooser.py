"""Open the operating system's own dialog to choose an Export (internal).

The dialog runs from a fixed script that holds no input of the user and no
path: ``osascript`` on macOS, PowerShell on Windows, and ``zenity`` or
``kdialog`` on Linux (stage B3a). One dialog is open at a time; another
request is refused at once. The request that opens the dialog returns at
once, and the page asks for the answer until the dialog closes, so that no
request of the page waits for the user. A dialog that is not answered within
the time limit counts as no selection, and its program is stopped, so that
no dialog stays on the screen. The page checks the returned path as it
checks a path that is pasted.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any

KINDS = ("zip", "folder")
TIMEOUT_SECONDS = 600.0

# macOS: AppleScript cancels with error -128 and exit status 1.
_MACOS = {
    "zip": 'POSIX path of (choose file of type {"zip", "public.zip-archive"})',
    "folder": "POSIX path of (choose folder)",
}
# Windows: the dialogs need a single-threaded apartment (-STA), and the path
# is written as UTF-8, so that names in Japanese reach the server intact. A
# form that stays on top keeps the dialog in front of the browser.
_WINDOWS_PREFIX = (
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$owner = New-Object System.Windows.Forms.Form -Property @{TopMost = $true}; "
)
_WINDOWS = {
    "zip": _WINDOWS_PREFIX
    + "$dialog = New-Object System.Windows.Forms.OpenFileDialog; "
    "$dialog.Filter = 'ZIP (*.zip)|*.zip'; $dialog.Multiselect = $false; "
    "if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) "
    "{ [Console]::Out.Write($dialog.FileName) }",
    "folder": _WINDOWS_PREFIX
    + "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
    "$dialog.ShowNewFolderButton = $false; "
    "if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) "
    "{ [Console]::Out.Write($dialog.SelectedPath) }",
}
# Linux: both programs cancel with exit status 1, and need a display.
_ZENITY = {
    "zip": ["--file-selection", "--file-filter=ZIP | *.zip *.ZIP"],
    "folder": ["--file-selection", "--directory"],
}
_KDIALOG = {
    "zip": ["--getopenfilename", ".", "*.zip *.ZIP"],
    "folder": ["--getexistingdirectory", "."],
}


class ChooserError(ValueError):
    """A dialog that could not be opened, reported as a code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def command(kind: str, platform: str = sys.platform) -> list[str] | None:
    """The fixed command that opens the dialog for ``kind``, or None when
    this system has no program for it."""
    if platform == "darwin":
        return ["/usr/bin/osascript", "-e", _MACOS[kind]]
    if platform == "win32":
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell is None:
            return None
        return [powershell, "-NoProfile", "-NonInteractive", "-STA", "-Command", _WINDOWS[kind]]
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return None
    for program, arguments in (("zenity", _ZENITY), ("kdialog", _KDIALOG)):
        found = shutil.which(program)
        if found is not None:
            return [found, *arguments[kind]]
    return None


def _cancelled(platform: str, stderr: bytes) -> bool:
    """Whether the program ended because the user cancelled: AppleScript
    says error -128; zenity and kdialog say nothing."""
    if platform == "darwin":
        return b"(-128)" in stderr
    return platform != "win32"


def _failed(code: str) -> dict[str, Any]:
    return {"state": "failed", "error_code": code}


def answer(platform: str, returncode: int, stdout: bytes, stderr: bytes) -> dict[str, Any]:
    """What a closed dialog answered: the chosen path, None when nothing was
    chosen, or the code of a dialog that did not work."""
    if returncode == 1 and _cancelled(platform, stderr):
        return {"state": "closed", "path": None}
    if returncode != 0:
        return _failed("CHOOSER_NOT_AVAILABLE")
    try:
        path = stdout.decode("utf-8")
    except UnicodeDecodeError:
        return _failed("CHOOSER_NOT_AVAILABLE")
    # Only the line end that the programs add; a name may end in a space.
    path = path.removesuffix("\n").removesuffix("\r")
    if not path:
        return {"state": "closed", "path": None}
    if any(character in path for character in "\x00\r\n") or not os.path.isabs(path):
        return _failed("CHOOSER_NOT_AVAILABLE")
    return {"state": "closed", "path": path}


class Chooser:
    """One dialog at a time, and the answer of the last one until the page
    reads it."""

    def __init__(
        self,
        *,
        platform: str = sys.platform,
        timeout: float = TIMEOUT_SECONDS,
        find_command: Callable[[str, str], list[str] | None] = command,
    ) -> None:
        self._platform = platform
        self._timeout = timeout
        self._find_command = find_command
        self._lock = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._answer: dict[str, Any] | None = None

    def start(self, kind: Any) -> None:
        """Open the dialog for ``kind`` and return at once."""
        if kind not in KINDS:
            raise ChooserError("REQUEST_INVALID")
        with self._lock:
            if self._process is not None:
                raise ChooserError("CHOOSER_BUSY")
            arguments = self._find_command(kind, self._platform)
            if arguments is None:
                raise ChooserError("CHOOSER_NOT_AVAILABLE")
            try:
                process = subprocess.Popen(
                    arguments,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                raise ChooserError("CHOOSER_NOT_AVAILABLE") from exc
            self._process = process
            self._answer = None
        threading.Thread(target=self._wait, args=(process,), daemon=True).start()

    def _wait(self, process: subprocess.Popen[bytes]) -> None:
        try:
            stdout, stderr = process.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            result = _failed("CHOOSER_TIMEOUT")
        else:
            result = answer(self._platform, process.returncode, stdout, stderr)
        with self._lock:
            self._process = None
            self._answer = result

    def status(self) -> dict[str, Any]:
        """``open`` while the dialog is open. Then, once, ``closed`` with the
        chosen path (None when nothing was chosen), or ``failed`` with a code;
        ``idle`` when there is nothing to give."""
        with self._lock:
            if self._process is not None:
                return {"state": "open"}
            result, self._answer = self._answer, None
        return result if result is not None else {"state": "idle"}

    def stop(self) -> None:
        """Close a dialog that is still open, when the server stops."""
        with self._lock:
            process = self._process
        if process is not None:
            process.kill()


__all__ = ["Chooser", "ChooserError", "KINDS", "TIMEOUT_SECONDS", "answer", "command"]
