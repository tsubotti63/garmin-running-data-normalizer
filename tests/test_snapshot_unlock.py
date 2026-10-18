"""The lock file that a stopped registration leaves (stage B4b-2).

`snapshot unlock` and the GUI remove it with one function, only when the
person confirmed that no snapshot command uses the store, only in a store,
and only a regular file of this app's form, which is looked at once more
just before it is removed. The notices of a cancelled registration come from
one function for the CLI and the GUI (synthetic data only).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer import diagnostics  # noqa: F401
from garmin_running_data_normalizer.snapshot import store as store_module
from garmin_running_data_normalizer.snapshot.store import (
    LOCK_NAME,
    SnapshotStoreError,
    cancel_notices,
    initialize_store,
    load_manifests,
    lock_created_at,
    lock_exists,
    remove_lock,
    verify_store,
)
from tests.test_environment_stops import REAL_SYMLINKS
from tests.test_stops import SYNTHETIC_EXPORT, StopLines, registered, cli, register_args

ACCOUNT = "synthetic-account-boundary"


def tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class RemoveLockTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.store = self.root / "store"
        registered(self.store, SYNTHETIC_EXPORT)
        self.lock = self.store / LOCK_NAME

    def assert_code(self, code: str, **options: object) -> None:
        with self.assertRaises(SnapshotStoreError) as caught:
            remove_lock(self.store, **{"confirmed": True, **options})
        self.assertEqual(caught.exception.code, code)

    def test_a_lock_that_a_stopped_registration_left_is_removed(self) -> None:
        # The record of an interrupted registration and the Snapshots stay.
        journal = self.store / "journal" / "registration.json"
        journal.write_text('{"format": "snapshot-registration-journal-v1"}', encoding="utf-8")
        for content in (b"424242\n", b"424242", b""):
            with self.subTest(content=content):
                self.lock.write_bytes(content)
                before = tree(self.store)
                self.assertEqual(remove_lock(self.store, confirmed=True), {"status": "PASS", "removed": LOCK_NAME})
                self.assertFalse(os.path.lexists(self.lock))
                after = tree(self.store)
                self.assertEqual(after, {name: data for name, data in before.items() if name != LOCK_NAME})
        journal.unlink()
        self.assertEqual(verify_store(self.store)["status"], "PASS")
        self.assertEqual(len(load_manifests(self.store)), 1)

    def test_only_with_the_check_and_only_in_a_store(self) -> None:
        self.lock.write_text("424242\n", encoding="ascii")
        for confirmed in (False, None, "yes"):
            with self.subTest(confirmed=confirmed):
                self.assert_code("SNAPSHOT_UNLOCK_NOT_CONFIRMED", confirmed=confirmed)
        self.assertTrue(self.lock.exists())
        # A folder that is not a store, and one that holds a lock file only,
        # which reads as a damaged store, as for every snapshot command.
        folder = self.root / "folder"
        folder.mkdir()
        for code in ("SNAPSHOT_STORE_NOT_FOUND", "SNAPSHOT_STORE_INVALID"):
            with self.subTest(code=code):
                with self.assertRaises(SnapshotStoreError) as caught:
                    remove_lock(folder, confirmed=True)
                self.assertEqual(caught.exception.code, code)
                (folder / LOCK_NAME).write_text("424242\n", encoding="ascii")
        self.assertTrue((folder / LOCK_NAME).exists())
        self.lock.unlink()
        self.assert_code("SNAPSHOT_LOCK_NOT_FOUND")

    def test_a_file_that_is_not_this_apps_lock_stays(self) -> None:
        for content in (b"not a lock\n", b"1" * 65, b"424242\n\n", b"-1\n", "４２\n".encode("utf-8")):
            with self.subTest(content=content):
                self.lock.write_bytes(content)
                self.assert_code("SNAPSHOT_LOCK_INVALID")
                self.assertEqual(self.lock.read_bytes(), content)
        self.lock.unlink()
        self.lock.mkdir()
        self.assert_code("SNAPSHOT_LOCK_INVALID")
        self.assertTrue(self.lock.is_dir())

    @REAL_SYMLINKS
    def test_a_link_in_the_place_of_the_lock_stays(self) -> None:
        target = self.root / "elsewhere.txt"
        target.write_text("424242\n", encoding="ascii")
        self.lock.symlink_to(target)
        self.assert_code("SNAPSHOT_LOCK_INVALID")
        self.assertTrue(self.lock.is_symlink())
        self.assertEqual(target.read_text(encoding="ascii"), "424242\n")

    def test_a_lock_put_in_its_place_while_it_is_checked_stays(self) -> None:
        # Another file put in the place of the lock between the first look and
        # the last one, such as the lock of a registration that started.
        self.lock.write_text("424242\n", encoding="ascii")
        real_lstat = os.lstat
        calls = []

        def lstat(path: object, *args: object, **kwargs: object) -> os.stat_result:
            # The store names its folder as the system resolves it.
            if Path(str(path)).name == LOCK_NAME:
                calls.append(path)
                if len(calls) == 2:
                    self.lock.unlink()
                    self.lock.write_text("515151\n", encoding="ascii")
            return real_lstat(path, *args, **kwargs)

        with mock.patch.object(store_module.os, "lstat", side_effect=lstat):
            self.assert_code("SNAPSHOT_LOCK_INVALID")
        self.assertEqual(self.lock.read_text(encoding="ascii"), "515151\n")

    def test_the_time_of_the_lock(self) -> None:
        self.assertIsNone(lock_created_at(self.store))
        self.lock.write_text("424242\n", encoding="ascii")
        stamp = datetime(2030, 1, 1, 2, 3, 4, tzinfo=timezone.utc).timestamp()
        os.utime(self.lock, (stamp, stamp))
        self.assertEqual(lock_created_at(self.store), "2030-01-01T02:03:04+00:00")
        self.lock.unlink()
        self.lock.mkdir()
        self.assertIsNone(lock_created_at(self.store))


class CancelNoticesTest(unittest.TestCase):
    def test_what_a_cancelled_registration_left(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "store"
            initialize_store(store, ACCOUNT)
            self.assertFalse(lock_exists(store))
            self.assertEqual(cancel_notices(store, lock_before=False), [])
            (store / LOCK_NAME).write_text("424242\n", encoding="ascii")
            (store / "journal" / "registration.json").write_text("{}", encoding="utf-8")
            self.assertTrue(lock_exists(store))
            self.assertEqual(
                cancel_notices(store, lock_before=False),
                ["SNAPSHOT_REGISTRATION_INCOMPLETE", "SNAPSHOT_STORE_LOCKED"],
            )
            # A lock that was there before is not one that the run left.
            self.assertEqual(cancel_notices(store, lock_before=True), ["SNAPSHOT_REGISTRATION_INCOMPLETE"])
            self.assertEqual(cancel_notices(Path(directory) / "missing", lock_before=False), [])


class UnlockCommandTest(StopLines, unittest.TestCase):
    def test_snapshot_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            registered(store, SYNTHETIC_EXPORT)
            lock = store / LOCK_NAME
            unlock = ("snapshot", "unlock", "--store", store)
            confirmed = (*unlock, "--confirm-no-other-command")
            lock.write_text("424242\n", encoding="ascii")
            # The next step of a lock names the command.
            what = self.assert_stop("SNAPSHOT_STORE_LOCKED", (*register_args(store, SYNTHETIC_EXPORT, "S2"),), root)
            self.assertIn("pid 424242", what)
            self.assert_stop("SNAPSHOT_UNLOCK_NOT_CONFIRMED", unlock, root)
            self.assertTrue(lock.exists())
            self.assertEqual(cli(*confirmed), (0, ""))
            self.assertFalse(lock.exists())
            self.assert_stop("SNAPSHOT_LOCK_NOT_FOUND", confirmed, root)
            lock.write_text("not a lock", encoding="ascii")
            self.assert_stop("SNAPSHOT_LOCK_INVALID", confirmed, root)
            self.assertTrue(lock.exists())
            self.assert_stop("SNAPSHOT_STORE_NOT_FOUND", ("snapshot", "unlock", "--store", root / "missing", "--confirm-no-other-command"), root)
            # The registration that stopped completes now.
            lock.unlink()
            self.assertEqual(cli(*register_args(store, SYNTHETIC_EXPORT, "S2"))[0], 0)


if __name__ == "__main__":
    unittest.main()
