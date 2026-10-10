#!/usr/bin/env python3
"""Open the GUI that is in development, from a source checkout.

The command-line interface does not expose the GUI until the v2.0.0 release
candidate. This helper is for development only and is not part of the wheel.
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open the GUI that is in development, from a source checkout."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="print the address without opening the default browser",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "src"))
    from garmin_running_data_normalizer.gui.server import GuiServer, serve_until_stopped

    server = GuiServer()
    print("GUI address (it contains the launch key; do not share it):")
    print(server.url)
    print("Stop with Ctrl+C or the Quit button on the page.", flush=True)
    if not args.no_browser:
        webbrowser.open(server.url)
    serve_until_stopped(server)
    print("GUI stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
