from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from garmin_running_data_normalizer.common.os_metadata import is_os_metadata_path
from garmin_running_data_normalizer.gui.server import STATIC_FILES, load_static_files


ROOT = Path(__file__).resolve().parents[1]
GUI_ROOT = ROOT / "src/garmin_running_data_normalizer/gui"
STATIC_ROOT = GUI_ROOT / "static"


def static_resources() -> set[str]:
    return {resource for resource, _ in STATIC_FILES.values()}


class GuiPackageDataTest(unittest.TestCase):
    def test_static_directory_holds_exactly_the_served_files(self) -> None:
        present = {
            path.relative_to(STATIC_ROOT).as_posix()
            for path in STATIC_ROOT.rglob("*")
            if path.is_file()
            and not is_os_metadata_path(path.relative_to(STATIC_ROOT).as_posix())
        }
        self.assertEqual(present, static_resources())

    def test_package_data_patterns_cover_every_static_file(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        patterns = metadata["tool"]["setuptools"]["package-data"][
            "garmin_running_data_normalizer.gui"
        ]
        matched = {
            path.relative_to(GUI_ROOT).as_posix()
            for pattern in patterns
            for path in GUI_ROOT.glob(pattern)
            if path.is_file()
        }
        self.assertEqual(matched, {f"static/{resource}" for resource in static_resources()})

    def test_every_static_file_loads_from_the_package(self) -> None:
        loaded = load_static_files()
        self.assertEqual(set(loaded), set(STATIC_FILES))
        for path, (body, content_type) in loaded.items():
            with self.subTest(path=path):
                self.assertTrue(body)
                self.assertEqual(content_type, STATIC_FILES[path][1])


if __name__ == "__main__":
    unittest.main()
