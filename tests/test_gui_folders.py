from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from garmin_running_data_normalizer.gui import folders as folders_module
from garmin_running_data_normalizer.gui.folders import FolderError, list_folders


class GuiFolderListTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(os.path.abspath(directory.name))
        for name in ("Gamma", "alpha", "Beta", ".hidden"):
            (self.root / name).mkdir()
        (self.root / "notes.txt").write_text("synthetic", encoding="utf-8")

    def test_lists_visible_folder_names_only(self) -> None:
        listing = list_folders(str(self.root))
        self.assertEqual(listing["folders"], ["alpha", "Beta", "Gamma"])
        self.assertEqual(listing["path"], str(self.root))
        self.assertEqual(listing["parent"], str(self.root.parent))
        self.assertFalse(listing["truncated"])

    def test_symbolic_links_are_left_out(self) -> None:
        try:
            (self.root / "link").symlink_to(self.root / "alpha", target_is_directory=True)
        except OSError:
            self.skipTest("this system does not allow creating symbolic links")
        self.assertEqual(list_folders(str(self.root))["folders"], ["alpha", "Beta", "Gamma"])

    @unittest.skipUnless(os.name == "nt", "junctions and hidden attributes are Windows features")
    def test_junctions_and_hidden_folders_are_left_out_on_windows(self) -> None:
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.root / "junction"), str(self.root / "alpha")],
            check=True,
            capture_output=True,
        )
        (self.root / "marked").mkdir()
        subprocess.run(["attrib", "+h", str(self.root / "marked")], check=True, capture_output=True)
        self.assertEqual(list_folders(str(self.root))["folders"], ["alpha", "Beta", "Gamma"])

    @unittest.skipUnless(
        hasattr(os, "chflags") and hasattr(stat, "UF_HIDDEN"),
        "this system has no hidden flag for files",
    )
    def test_folders_with_the_hidden_flag_are_left_out(self) -> None:
        flagged = self.root / "Flagged"
        flagged.mkdir()
        try:
            os.chflags(flagged, stat.UF_HIDDEN)
        except OSError:
            self.skipTest("this file system does not keep the hidden flag")
        self.assertEqual(list_folders(str(self.root))["folders"], ["alpha", "Beta", "Gamma"])

    def test_the_home_folder_is_the_default(self) -> None:
        with patch.object(Path, "home", return_value=self.root):
            self.assertEqual(list_folders()["path"], str(self.root))
            self.assertEqual(list_folders("")["path"], str(self.root))

    def test_a_tilde_means_the_home_folder(self) -> None:
        with patch.dict(os.environ, {"HOME": str(self.root), "USERPROFILE": str(self.root)}):
            self.assertEqual(list_folders("~")["folders"], ["alpha", "Beta", "Gamma"])

    def test_the_parent_of_a_root_folder_is_none(self) -> None:
        anchor = self.root.anchor
        self.assertIsNone(list_folders(anchor)["parent"])

    def test_problems_are_reported_as_codes(self) -> None:
        cases = {
            "relative/path": "PATH_NOT_ABSOLUTE",
            str(self.root / "missing"): "FOLDER_NOT_FOUND",
            str(self.root / "notes.txt"): "NOT_A_FOLDER",
            "bad\x00path": "PATH_INVALID",
        }
        for path, code in cases.items():
            with self.subTest(path=path):
                with self.assertRaises(FolderError) as caught:
                    list_folders(path)
                self.assertEqual(caught.exception.code, code)
        with self.assertRaises(FolderError) as caught:
            list_folders(7)
        self.assertEqual(caught.exception.code, "PATH_INVALID")

    @unittest.skipIf(
        os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
        "permission bits do not stop this user here",
    )
    def test_an_unreadable_folder_is_reported(self) -> None:
        locked = self.root / "alpha"
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o700)
        with self.assertRaises(FolderError) as caught:
            list_folders(str(locked))
        self.assertEqual(caught.exception.code, "FOLDER_NOT_READABLE")

    def test_long_listings_are_truncated(self) -> None:
        with patch.object(folders_module, "MAX_FOLDERS", 2):
            listing = list_folders(str(self.root))
        self.assertEqual(listing["folders"], ["alpha", "Beta"])
        self.assertTrue(listing["truncated"])


if __name__ == "__main__":
    unittest.main()
