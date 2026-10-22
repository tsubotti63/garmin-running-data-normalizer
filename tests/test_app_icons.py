"""The pictures of the icon that starts the GUI and of the tab of the browser
(stage E1i).

scripts/generate_app_icons.py makes them on macOS from the two SVG files in
the package. The drawing differs a little from one computer to another, so
these tests check the form of the files: the sizes, the PNG pictures with
only the chunks that hold the picture and a transparent corner, the copy of
the SVG for the browser, and the package data that holds them.
"""
from __future__ import annotations

import re
import struct
import tomllib
import unittest
import zlib
from pathlib import Path

from garmin_running_data_normalizer.gui.server import STATIC_FILES
from garmin_running_data_normalizer.shortcut import MAC_PICTURE, WINDOWS_PICTURE
from scripts.static_policy_scan import EMAIL, HOST_PATH
from scripts.generate_app_icons import (
    FAVICON_SIZE,
    ICNS_TYPES,
    ICO_SIZES,
    PNG_SIGNATURE,
    build_icns,
    build_ico,
    png_chunks,
    png_size,
    strip_png,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "garmin_running_data_normalizer"
ASSETS = PACKAGE / "assets"
STATIC = PACKAGE / "gui" / "static"


def icns_entries(data: bytes) -> list[tuple[bytes, bytes]]:
    if data[:4] != b"icns" or struct.unpack(">I", data[4:8])[0] != len(data):
        raise ValueError("not an icns file")
    entries, position = [], 8
    while position < len(data):
        kind, (length,) = data[position : position + 4], struct.unpack(">I", data[position + 4 : position + 8])
        entries.append((kind, data[position + 8 : position + length]))
        position += length
    return entries


def ico_entries(data: bytes) -> list[tuple[int, bytes]]:
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    if (reserved, kind) != (0, 1):
        raise ValueError("not an ICO file")
    entries = []
    for number in range(count):
        width, _, _, _, _, _, size, offset = struct.unpack("<BBBBHHII", data[6 + 16 * number : 22 + 16 * number])
        entries.append((width or 256, data[offset : offset + size]))
    return entries


def corner_alpha(picture: bytes) -> int:
    """The alpha of the top left pixel of an 8-bit RGBA PNG picture."""
    header = dict(png_chunks(picture))[b"IHDR"]
    width, _, depth, colour = struct.unpack(">IIBB", header[:10])
    if (depth, colour) != (8, 6):
        raise ValueError("not an 8-bit RGBA picture")
    raw = zlib.decompress(b"".join(body for kind, body in png_chunks(picture) if kind == b"IDAT"))
    # The first row needs only the filters that do not look up: none, sub,
    # and the ones that read a row above it as zeros.
    line = bytearray(raw[1 : 1 + width * 4])
    if raw[0] in (1, 3, 4):
        for index in range(4, len(line)):
            left = line[index - 4]
            line[index] = (line[index] + (left // 2 if raw[0] == 3 else left)) & 255
    return line[3]


class AppIconTest(unittest.TestCase):
    def test_the_mac_picture_has_every_size_of_an_iconset_up_to_512(self) -> None:
        entries = icns_entries(MAC_PICTURE.read_bytes())
        self.assertEqual([(kind, png_size(picture)) for kind, picture in entries],
                         [(kind, (size, size)) for kind, size in ICNS_TYPES])

    def test_the_windows_picture_has_the_sizes_of_windows(self) -> None:
        entries = ico_entries(WINDOWS_PICTURE.read_bytes())
        self.assertEqual([(width, png_size(picture)) for width, picture in entries],
                         [(size, (size, size)) for size in ICO_SIZES])

    def test_the_pictures_hold_nothing_but_the_picture(self) -> None:
        # No name of a tool, time, colour profile, or place of a computer.
        pictures = [picture for _, picture in icns_entries(MAC_PICTURE.read_bytes())]
        pictures += [picture for _, picture in ico_entries(WINDOWS_PICTURE.read_bytes())]
        pictures.append((STATIC / "favicon.png").read_bytes())
        for number, picture in enumerate(pictures):
            with self.subTest(picture=number):
                self.assertTrue(picture.startswith(PNG_SIGNATURE))
                self.assertLessEqual({kind for kind, _ in png_chunks(picture)}, {b"IHDR", b"IDAT", b"IEND"})
                self.assertEqual(corner_alpha(picture), 0, "a transparent corner")
        # The policy scan reads these files as text too: its patterns of a
        # place of a computer and of an email address find nothing there.
        for path in (MAC_PICTURE, WINDOWS_PICTURE, STATIC / "favicon.png"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertIsNone(HOST_PATH.search(text))
                self.assertIsNone(EMAIL.search(text))

    def test_the_browser_shows_the_picture_of_the_icon(self) -> None:
        self.assertEqual((STATIC / "favicon.svg").read_bytes(), (ASSETS / "icon-square.svg").read_bytes())
        self.assertEqual(png_size((STATIC / "favicon.png").read_bytes()), (FAVICON_SIZE, FAVICON_SIZE))
        page = (STATIC / "index.html").read_text(encoding="utf-8")
        head = page.split("</head>", 1)[0]
        self.assertIn('<link rel="icon" type="image/svg+xml" href="/favicon.svg">', head)
        self.assertIn(f'<link rel="icon" type="image/png" sizes="{FAVICON_SIZE}x{FAVICON_SIZE}" href="/favicon.png">', head)
        self.assertEqual(STATIC_FILES["/favicon.svg"], ("favicon.svg", "image/svg+xml"))
        self.assertEqual(STATIC_FILES["/favicon.png"], ("favicon.png", "image/png"))
        # A data: address would be stopped by img-src 'self'.
        self.assertNotRegex(page, re.compile(r"href=\"data:"))

    def test_the_svg_files_are_the_drawing_of_the_icon(self) -> None:
        icon = (ASSETS / "icon.svg").read_text(encoding="utf-8")
        square = (ASSETS / "icon-square.svg").read_text(encoding="utf-8")
        self.assertIn('viewBox="0 0 1024 1024"', icon)
        self.assertIn('viewBox="100 100 824 824"', square)
        letters = re.findall(r'<path stroke="(#[0-9A-F]{6})" d="([^"]+)"/>', icon)
        self.assertEqual(len(letters), 4)
        self.assertEqual(letters, re.findall(r'<path stroke="(#[0-9A-F]{6})" d="([^"]+)"/>', square))
        self.assertEqual([colour for colour, _ in letters], ["#FFFFFF", "#FFFFFF", "#8ED8FF", "#8ED8FF"])
        for text in (icon, square):
            self.assertNotIn("<text", text)

    def test_the_package_data_holds_the_pictures(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        patterns = metadata["tool"]["setuptools"]["package-data"]["garmin_running_data_normalizer"]
        matched = {path.name for pattern in patterns for path in PACKAGE.glob(pattern) if path.is_file()}
        self.assertEqual(matched, {"icon.svg", "icon-square.svg", "icon.icns", "icon.ico"})
        self.assertEqual({path.name for path in ASSETS.iterdir() if not path.name.startswith(".")}, matched)


class AssemblyTest(unittest.TestCase):
    """The steps of scripts/generate_app_icons.py that do not draw."""

    @staticmethod
    def picture(size: int, extra: bytes = b"") -> bytes:
        def chunk(kind: bytes, body: bytes) -> bytes:
            return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

        rows = b"".join(b"\x00" + bytes(4 * size) for _ in range(size))
        return (PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + extra
                + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))

    def test_the_picture_loses_every_chunk_but_the_picture(self) -> None:
        def chunk(kind: bytes, body: bytes) -> bytes:
            return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

        extra = chunk(b"tEXt", b"Software\x00a tool") + chunk(b"tIME", bytes(7)) + chunk(b"iCCP", b"p\x00\x00x")
        stripped = strip_png(self.picture(4, extra))
        self.assertEqual([kind for kind, _ in png_chunks(stripped)], [b"IHDR", b"IDAT", b"IEND"])
        self.assertEqual(stripped, strip_png(self.picture(4)))
        self.assertEqual(stripped, self.picture(4))

    def test_the_ico_and_the_icns_hold_the_pictures_in_their_order(self) -> None:
        pictures = [self.picture(16), self.picture(256)]
        ico = build_ico(pictures)
        self.assertEqual(struct.unpack("<HHH", ico[:6]), (0, 1, 2))
        self.assertEqual(ico_entries(ico), [(16, pictures[0]), (256, pictures[1])])
        self.assertEqual(ico[6 + 16], 0, "a size of 256 is written as 0")
        icns = build_icns([(b"icp4", pictures[0]), (b"ic08", pictures[1])])
        self.assertEqual(icns_entries(icns), [(b"icp4", pictures[0]), (b"ic08", pictures[1])])


if __name__ == "__main__":
    unittest.main()
