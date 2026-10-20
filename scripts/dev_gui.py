#!/usr/bin/env python3
"""Open the GUI from a source checkout, as the `gui` command does.

The `gui` command opens the GUI of an installed package. This helper runs the
same launch from a source checkout, for development only, and is not part of
the wheel.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open the GUI from a source checkout, as the gui command does."
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="print the address without opening the default browser",
    )
    args = parser.parse_args()

    source = str(ROOT / "src")
    sys.path.insert(0, source)
    # The Run-All child process imports the package too; let it find this
    # checkout when the package is not installed.
    os.environ["PYTHONPATH"] = os.pathsep.join(
        path for path in (source, os.environ.get("PYTHONPATH")) if path
    )
    # The same launch as the `gui` command (stage D1).
    from garmin_running_data_normalizer.gui.command import run_gui

    return run_gui(open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
