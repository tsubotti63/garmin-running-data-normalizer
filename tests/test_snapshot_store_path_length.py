"""The paths inside a Snapshot Store on Windows without long paths (stage
B6c): the deepest file that a registration writes adds 189 characters to the
path of the store, so ``snapshot init``, ``snapshot register``, and the GUI
stop before anything is written with ``SNAPSHOT_STORE_PATH_TOO_LONG``, and
``snapshot status`` tells it of an open store. Until stage B6c, the
registration stopped with ``COMMAND_FAILED`` after it had copied part of the
Export (synthetic data only)."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer.gui import places, stores
from garmin_running_data_normalizer.snapshot import SnapshotLifecycleError, initialize_store
from garmin_running_data_normalizer.snapshot import store as store_module
from garmin_running_data_normalizer.snapshot.store import (
    DEEPEST_STORE_FILE,
    DEEPEST_STORE_FOLDER,
    NOTICE_MESSAGES,
    PATH_TOO_LONG_MESSAGE,
    check_new_store_place,
    snapshot_status,
    store_paths_too_long,
    windows_store_paths_too_long,
)
from tests.test_gui_runs import SYNTHETIC_EXPORT
from tests.test_snapshot_store_environment import cli, line, register_args, tree

ACCOUNT = "synthetic-account-boundary"
CODE = "SNAPSHOT_STORE_PATH_TOO_LONG"


def too_long(value: bool = True) -> mock._patch:
    """The answer of the check of this system: True as Windows without long
    paths gives it for a long place, and False as any other system gives it,
    so that the tests give the same result on every system, also on Windows
    whose long paths are not enabled."""
    return mock.patch.object(store_module, "store_paths_too_long", return_value=value)


class WindowsPathLengthTest(unittest.TestCase):
    def test_the_deepest_paths_of_a_store(self) -> None:
        # The temporary file of the inventory of a Snapshot, with a process
        # number of 10 digits, and the folder of a Snapshot.
        snapshot_id = "snapshot-" + "0" * 64
        self.assertEqual(
            DEEPEST_STORE_FILE,
            len(f"snapshots/{snapshot_id}/.{snapshot_id}.inventory.json.{'9' * 10}.tmp"),
        )
        self.assertEqual(DEEPEST_STORE_FOLDER, len(f"snapshots/{snapshot_id}"))
        self.assertEqual(DEEPEST_STORE_FILE, 188)

    def test_a_store_of_70_characters_fits_and_one_of_71_does_not(self) -> None:
        for length, expected in ((70, False), (71, True)):
            root = "C:\\" + "s" * (length - 3)
            with self.subTest(length=length):
                self.assertEqual(len(root), length)
                self.assertEqual(windows_store_paths_too_long(root), expected)

    def test_the_length_counts_the_units_of_windows(self) -> None:
        # A character outside the Basic Multilingual Plane takes two units,
        # as Windows counts a path.
        self.assertFalse(windows_store_paths_too_long("C:\\" + "s" * 65 + "\U0001f3c3"))
        self.assertTrue(windows_store_paths_too_long("C:\\" + "s" * 66 + "\U0001f3c3"))
        # A path that starts with \\?\ has no such limit.
        self.assertFalse(windows_store_paths_too_long("\\\\?\\C:\\" + "s" * 200))

    def test_only_windows_without_long_paths_has_the_limit(self) -> None:
        root = "C:\\" + "s" * 100
        with mock.patch.object(store_module.os, "name", "posix"):
            self.assertFalse(store_paths_too_long(root))
        for enabled, expected in ((True, False), (False, True)):
            with self.subTest(long_paths=enabled), mock.patch.object(store_module.os, "name", "nt"), mock.patch.object(
                store_module, "long_paths_enabled", return_value=enabled
            ):
                self.assertEqual(store_paths_too_long(root), expected)


class StorePathStopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        self.store = self.root / "snapshots"
        # The GUI's default places are in a home folder of the test's own.
        patcher = mock.patch.object(places, "home", lambda: self.root / "home")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_snapshot_init_stops_before_it_makes_the_store(self) -> None:
        before = tree(self.root)
        with too_long():
            status, stdout, stderr = cli("snapshot", "init", "--store", self.store, "--account", ACCOUNT)
            with self.assertRaises(SnapshotLifecycleError) as raised:
                check_new_store_place(self.store)
        self.assertEqual((status, stdout, stderr), (2, "", line(CODE, PATH_TOO_LONG_MESSAGE)))
        self.assertEqual(raised.exception.code, CODE)
        self.assertEqual(tree(self.root), before)
        # The GUI checks the place of a new store with the same function.
        with too_long():
            answer = stores.store_place(self.root)
        self.assertEqual(answer, {"state": "error", "path": str(self.store), "error_code": CODE})
        self.assertIn(CODE, stores.ANSWER_CODES)
        self.assertEqual(tree(self.root), before)
        # The default place, whose folder a run makes, is told at once too.
        default = places.default_folder()
        with too_long():
            answer = stores.store_place(default)
        self.assertEqual(answer, {"state": "error", "path": str(places.default_store()), "error_code": CODE})
        with too_long(False):
            self.assertEqual(stores.store_place(default)["state"], "new")
        self.assertEqual(tree(self.root), before)

    def test_a_registration_stops_before_it_looks_at_the_export(self) -> None:
        initialize_store(self.store, ACCOUNT)
        before = tree(self.store)
        # Even an Export that is not there gives the code of the store: the
        # registration writes nothing, and takes no lock.
        for source in (SYNTHETIC_EXPORT, self.root / "missing-export"):
            with self.subTest(source=source.name), too_long():
                status, stdout, stderr = cli(*register_args(self.store, source, "S1", 1))
            self.assertEqual((status, stdout, stderr), (2, "", line(CODE, PATH_TOO_LONG_MESSAGE)))
            self.assertEqual(tree(self.store), before)
        # Without the limit, the same registration imports the Export.
        with too_long(False):
            self.assertEqual(cli(*register_args(self.store, SYNTHETIC_EXPORT, "S1", 1))[0], 0)

    def test_snapshot_status_tells_it_of_an_open_store(self) -> None:
        initialize_store(self.store, ACCOUNT)
        with too_long(False):
            self.assertNotIn("notices", snapshot_status(self.store))
        with too_long():
            self.assertEqual(snapshot_status(self.store)["notices"], [CODE])
            status, _stdout, stderr = cli("snapshot", "status", "--store", self.store)
            answer = stores.open_store(self.store)
        # A NOTE never means a stop.
        self.assertEqual(status, 0)
        self.assertEqual(stderr, f"NOTE [{CODE}]: {NOTICE_MESSAGES[CODE]}")
        self.assertEqual(answer["notices"], [CODE])


if __name__ == "__main__":
    unittest.main()
