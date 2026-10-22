#!/usr/bin/env python3
"""Make the pictures of the icon that starts the GUI (stage E1i) from the two
SVG files in src/garmin_running_data_normalizer/assets:

- assets/icon.icns from icon.svg, for the file on the desktop of macOS;
- assets/icon.ico from icon-square.svg, for the shortcuts of Windows;
- gui/static/favicon.svg, a copy of icon-square.svg, and gui/static/favicon.png,
  for the tab of the browser.

It runs on macOS only: Google Chrome draws the SVG files on a transparent
ground, and sips makes the smaller sizes. The CI does not run it. Every PNG
picture keeps only its IHDR, IDAT, and IEND chunks, so that no name of a
tool, time, colour profile, or place of the computer goes into the files. The
drawing differs a little from one computer to another, so the tests check the
form of the files, not their bytes.

Usage: python3 scripts/generate_app_icons.py
"""

from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "garmin_running_data_normalizer" / "assets"
STATIC = ROOT / "src" / "garmin_running_data_normalizer" / "gui" / "static"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
KEPT_CHUNKS = (b"IHDR", b"IDAT", b"IEND")
# The types of icns that hold a PNG picture, with its size in pixels, as
# iconutil names them: the sizes of an iconset from 16 to 256 points, so up
# to 512 pixels on a Retina display, which covers a file on the desktop.
ICNS_TYPES = (
    (b"icp4", 16),
    (b"ic11", 32),
    (b"icp5", 32),
    (b"ic12", 64),
    (b"ic07", 128),
    (b"ic13", 256),
    (b"ic08", 256),
    (b"ic14", 512),
)
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
FAVICON_SIZE = 64
DRAWN_SIZE = 1024


def png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """The chunks of a PNG picture, as (type, body)."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG picture")
    chunks, position = [], len(PNG_SIGNATURE)
    while position < len(data):
        (length,) = struct.unpack(">I", data[position : position + 4])
        kind = data[position + 4 : position + 8]
        chunks.append((kind, data[position + 8 : position + 8 + length]))
        position += 12 + length
    return chunks


def strip_png(data: bytes) -> bytes:
    """The picture with its IHDR, IDAT, and IEND chunks only."""
    out = [PNG_SIGNATURE]
    for kind, body in png_chunks(data):
        if kind in KEPT_CHUNKS:
            out.append(struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body)))
    return b"".join(out)


def png_size(data: bytes) -> tuple[int, int]:
    kind, body = png_chunks(data)[0]
    if kind != b"IHDR":
        raise ValueError("a PNG picture starts with IHDR")
    width, height = struct.unpack(">II", body[:8])
    return width, height


def build_ico(pictures: list[bytes]) -> bytes:
    """An ICO file whose pictures are PNG, as Windows reads them since Vista;
    a size of 256 is written as 0."""
    header = struct.pack("<HHH", 0, 1, len(pictures))
    offset = len(header) + 16 * len(pictures)
    entries = []
    for picture in pictures:
        width, height = png_size(picture)
        entries.append(struct.pack("<BBBBHHII", width % 256, height % 256, 0, 0, 1, 32, len(picture), offset))
        offset += len(picture)
    return header + b"".join(entries) + b"".join(pictures)


def build_icns(pictures: list[tuple[bytes, bytes]]) -> bytes:
    """An icns file of (type, PNG picture) entries, without the table of
    contents that iconutil adds."""
    body = b"".join(kind + struct.pack(">I", 8 + len(picture)) + picture for kind, picture in pictures)
    return b"icns" + struct.pack(">I", 8 + len(body)) + body


def _draw(svg: Path, picture: Path, work: Path) -> None:
    page = work / f"{svg.stem}.html"
    page.write_text(
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        "html,body{margin:0;padding:0;background:transparent}"
        f"img{{display:block;width:{DRAWN_SIZE}px;height:{DRAWN_SIZE}px}}</style></head>"
        f'<body><img src="{svg.as_uri()}"></body></html>\n',
        encoding="utf-8",
    )
    subprocess.run(
        [str(CHROME), "--headless=new", "--disable-gpu", "--use-mock-keychain", "--no-first-run",
         "--no-default-browser-check", f"--user-data-dir={work / 'chrome'}", "--hide-scrollbars",
         "--default-background-color=00000000", "--force-device-scale-factor=1",
         f"--window-size={DRAWN_SIZE},{DRAWN_SIZE}", f"--screenshot={picture}", page.as_uri()],
        check=True, capture_output=True,
    )


def _resized(picture: Path, size: int, work: Path) -> bytes:
    out = work / f"{picture.stem}-{size}.png"
    subprocess.run(["sips", "-z", str(size), str(size), str(picture), "--out", str(out)], check=True, capture_output=True)
    return strip_png(out.read_bytes())


def main() -> int:
    if sys.platform != "darwin" or not CHROME.is_file() or shutil.which("sips") is None:
        print("This script runs on macOS with Google Chrome and sips.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        drawn = {}
        for name in ("icon", "icon-square"):
            drawn[name] = work / f"{name}.png"
            _draw(ASSETS / f"{name}.svg", drawn[name], work)
        icns = build_icns([(kind, _resized(drawn["icon"], size, work)) for kind, size in ICNS_TYPES])
        ico = build_ico([_resized(drawn["icon-square"], size, work) for size in ICO_SIZES])
        favicon = _resized(drawn["icon-square"], FAVICON_SIZE, work)
    (ASSETS / "icon.icns").write_bytes(icns)
    (ASSETS / "icon.ico").write_bytes(ico)
    (STATIC / "favicon.png").write_bytes(favicon)
    shutil.copyfile(ASSETS / "icon-square.svg", STATIC / "favicon.svg")
    for path in (ASSETS / "icon.icns", ASSETS / "icon.ico", STATIC / "favicon.png", STATIC / "favicon.svg"):
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
