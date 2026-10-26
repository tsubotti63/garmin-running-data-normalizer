"""The `gui` command (stage D1): start the server, print its address with the
launch key in the terminal, open it in the default browser, and wait until
the server stops. `Ctrl+C` and the Quit button are the ways to stop it, so
the command ends with exit 0, unless `Ctrl+C` stopped the server during a
run: the terminal then gets the lines that the CLI prints for a cancelled
command, and the command ends with the CLI's exit code for it, 130. A second
`Ctrl+C` while the server stops and reports is ignored, as the CLI ignores
one while it reports (stage A5c), so that the run's child always ends first.

The address also carries the colors that the settings remember (stage G3a),
after the key, so that the page is drawn in them from the start.
"""
from __future__ import annotations

import signal
import sys
import threading
from collections.abc import Callable
from typing import Any

from .server import GuiServer, cancel_report, serve_until_stopped
from .settings import launch_theme

# The CLI's exit code for a command that Ctrl+C cancelled (stage A5c).
CANCELLED_EXIT_CODE = 130


def exit_code(stopped: dict[str, Any] | None) -> int:
    """The exit code of the command, from the run that was active when
    `Ctrl+C` stopped the server: 130 whatever its state, as the CLI ends a
    command that `Ctrl+C` stopped, also after its output; 0 when no run was
    active, as after the Quit button."""
    return 0 if stopped is None else CANCELLED_EXIT_CODE


def _stop_once_on_ctrl_c() -> list[tuple[int, Any]]:
    """Make the first Ctrl+C, and Ctrl+Break on Windows, stop the server, and
    any later one do nothing; return the handlers to give back. Signals are
    handled in the main thread only."""
    if threading.current_thread() is not threading.main_thread():
        return []
    pressed = False

    def handler(signum: int, frame: object) -> None:
        nonlocal pressed
        if pressed:
            return
        pressed = True
        raise KeyboardInterrupt

    saved = []
    for name in ("SIGINT", "SIGBREAK"):
        number = getattr(signal, name, None)
        if number is not None:
            saved.append((number, signal.getsignal(number)))
            signal.signal(number, handler)
    return saved


def _give_back(saved: list[tuple[int, Any]]) -> None:
    for number, previous in reversed(saved):
        if previous is not None:
            signal.signal(number, previous)


def launch_address(url: str, theme: str | None) -> str:
    """The address that a launch prints and opens: the server's, and the
    colors that the settings remember, in the fragment with the key, which
    the browser never sends (stage G3a)."""
    return url if theme is None else f"{url}&theme={theme}"


def _open_in_browser(url: str) -> object:
    # Only a launch that opens the browser loads the module.
    import webbrowser

    return webbrowser.open(url)


def run_gui(
    *,
    open_browser: bool = True,
    make_server: Callable[[], GuiServer] = GuiServer,
    opener: Callable[[str], object] = _open_in_browser,
) -> int:
    """Serve one launch of the GUI until it stops, and return the exit code."""
    server = make_server()
    saved = _stop_once_on_ctrl_c()
    try:
        try:
            address = launch_address(server.url, launch_theme())
            print("GUI address (it contains the launch key; do not share it):")
            print(address)
            print("Stop with Ctrl+C or the Quit button on the page.", flush=True)
            if open_browser:
                opener(address)
            stopped = serve_until_stopped(server)
        except KeyboardInterrupt:
            # Ctrl+C before the server serves, which takes it when it
            # serves: no run can have started.
            server.server_close()
            stopped = None
        for line in cancel_report(stopped) if stopped is not None else []:
            print(line, file=sys.stderr)
        print("GUI stopped.", flush=True)
        return exit_code(stopped)
    finally:
        _give_back(saved)


__all__ = ["CANCELLED_EXIT_CODE", "exit_code", "launch_address", "run_gui"]
