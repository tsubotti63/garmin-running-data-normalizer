"""The place of a Snapshot Store (stage B4a): ``snapshot init`` makes a new
store only where the folder that holds it exists, in a new or empty folder
that is not inside another store, and every snapshot command refuses a link
to a store, each with its own code. The GUI checks a new place with the same
function (synthetic data only)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.snapshot import SnapshotLifecycleError, initialize_store
from garmin_running_data_normalizer.snapshot.store import (
    MAX_STORE_METADATA_BYTES,
    NEW_STORE_INSIDE_STORE_MESSAGE,
    NEW_STORE_NOT_EMPTY_MESSAGE,
    NEW_STORE_PARENT_MESSAGE,
    STORE_FORMAT,
    STORE_SYMLINK_MESSAGE,
    check_new_store_place,
)
from tests.test_environment_stops import REAL_PERMISSIONS, REAL_SYMLINKS, permissions
from tests.test_snapshot_store_environment import cli, line, tree

ACCOUNT = "synthetic-account-boundary"
STAMP = "2030-01-01T02:00:00+00:00"


def init(store: Path, account: str = ACCOUNT) -> tuple[int, str, str]:
    return cli("snapshot", "init", "--store", store, "--account", account)


class NewStorePlaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(self._remove)

    def _remove(self) -> None:
        import shutil

        shutil.rmtree(self.root, ignore_errors=True)

    def assert_stop(self, store: Path, code: str, what: str) -> None:
        before = tree(self.root)
        status, stdout, stderr = init(store)
        self.assertEqual((status, stdout, stderr), (2, "", line(code, what)))
        # Nothing is written, and nothing is made above the store.
        self.assertEqual(tree(self.root), before)
        with self.assertRaises(SnapshotLifecycleError) as raised:
            check_new_store_place(store)
        self.assertEqual(raised.exception.code, code)

    def test_a_new_store_needs_the_folder_that_holds_it(self) -> None:
        # Until stage B4a, init made every missing folder above the store.
        self.assert_stop(
            self.root / "mistyped" / "store",
            "SNAPSHOT_STORE_PARENT_NOT_FOUND",
            NEW_STORE_PARENT_MESSAGE,
        )
        (self.root / "file").write_bytes(b"not a folder")
        self.assert_stop(
            self.root / "file" / "store", "SNAPSHOT_STORE_PARENT_NOT_FOUND", NEW_STORE_PARENT_MESSAGE
        )

    def test_a_new_store_is_made_in_a_new_or_an_empty_folder(self) -> None:
        new = self.root / "new"
        empty = self.root / "empty"
        empty.mkdir()
        for store in (new, empty):
            with self.subTest(store=store.name):
                self.assertEqual(check_new_store_place(store), store.resolve())
                status, _, stderr = init(store)
                self.assertEqual((status, stderr), (0, ""))
                self.assertTrue((store / "store.json").is_file())

    def test_a_file_or_a_folder_that_holds_other_files_is_not_used(self) -> None:
        # Until stage B4a, both stopped with SNAPSHOT_LIFECYCLE_FAILED.
        (self.root / "a-file").write_bytes(b"a file")
        self.assert_stop(self.root / "a-file", "SNAPSHOT_STORE_NOT_EMPTY", NEW_STORE_NOT_EMPTY_MESSAGE)
        (self.root / "other").mkdir()
        (self.root / "other" / "notes.txt").write_text("other files", encoding="utf-8")
        self.assert_stop(self.root / "other", "SNAPSHOT_STORE_NOT_EMPTY", NEW_STORE_NOT_EMPTY_MESSAGE)
        # A folder that holds a store is not empty either.
        holder = self.root / "holder"
        holder.mkdir()
        initialize_store(holder / "snapshots", ACCOUNT)
        self.assert_stop(holder, "SNAPSHOT_STORE_NOT_EMPTY", NEW_STORE_NOT_EMPTY_MESSAGE)

    def test_a_folder_with_what_a_store_writes_but_no_store_json_is_damaged(self) -> None:
        damaged = self.root / "damaged"
        damaged.mkdir()
        (damaged / "registry.json").write_text("{}", encoding="utf-8")
        before = tree(self.root)
        status, _, stderr = init(damaged)
        self.assertEqual(
            (status, stderr),
            (2, line("SNAPSHOT_STORE_INVALID", "the Snapshot Store is damaged: store.json is missing")),
        )
        self.assertEqual(tree(self.root), before)

    def test_a_folder_that_holds_a_store_in_its_folder_snapshots_holds_no_store(self) -> None:
        # The GUI's default place keeps its store in the folder snapshots of
        # GarminRunningData. Until stage B4a, the name snapshots alone made
        # such a folder read as a damaged store.
        holder = self.root / "GarminRunningData"
        holder.mkdir()
        initialize_store(holder / "snapshots", ACCOUNT)
        (holder / "garmin-run-all-20301009-0930").mkdir()
        for command in ("status", "verify"):
            with self.subTest(command=command):
                status, _, stderr = cli("snapshot", command, "--store", holder)
                self.assertEqual(status, 2)
                self.assertTrue(stderr.startswith("ERROR [SNAPSHOT_STORE_NOT_FOUND]: "), stderr)

    def test_a_store_that_is_there_is_used_as_before(self) -> None:
        store = self.root / "store"
        self.assertEqual(init(store)[0], 0)
        status, stdout, stderr = init(store)
        self.assertEqual((status, stderr), (0, ""))
        self.assertFalse(json.loads(stdout)["initialized"])
        status, _, stderr = init(store, "another-account-boundary")
        self.assertEqual(status, 2)
        self.assertTrue(stderr.startswith("ERROR [SNAPSHOT_LIFECYCLE_FAILED]: "), stderr)

    def test_no_new_store_inside_another_store(self) -> None:
        outer = self.root / "outer"
        initialize_store(outer, ACCOUNT)
        for store in (outer / "inner", outer / "blobs" / "sha256" / "inner", outer / "snapshots"):
            with self.subTest(store=store.relative_to(outer).as_posix()):
                self.assert_stop(store, "SNAPSHOT_STORE_INSIDE_STORE", NEW_STORE_INSIDE_STORE_MESSAGE)

    def test_only_a_store_of_this_app_counts_as_a_store_above(self) -> None:
        cases = {
            # Another program's store.json.
            "other-format": json.dumps({"format": "another-program-store"}).encode("utf-8"),
            "not-json": b"\xff\xfe not json",
            # Larger than a store.json of this app can be.
            "too-large": json.dumps(
                {"format": STORE_FORMAT, "padding": "x" * MAX_STORE_METADATA_BYTES}
            ).encode("utf-8"),
        }
        for name, data in cases.items():
            with self.subTest(name=name):
                holder = self.root / name
                holder.mkdir()
                (holder / "store.json").write_bytes(data)
                sub = holder / "sub"
                sub.mkdir()
                self.assertEqual(init(sub / "store")[0], 0)
        # A folder named store.json is not a store either.
        folder_holder = self.root / "folder-holder"
        (folder_holder / "store.json").mkdir(parents=True)
        self.assertEqual(init(folder_holder / "store")[0], 0)

    @REAL_PERMISSIONS
    def test_a_store_json_above_that_cannot_be_read_is_passed_over(self) -> None:
        # A store.json above that cannot be opened is not taken for a store,
        # and the walk goes on instead of stopping there.
        above = self.root / "above"
        holder = above / "holder"
        holder.mkdir(parents=True)
        (above / "store.json").write_text(json.dumps({"format": STORE_FORMAT}), encoding="utf-8")
        (above / "store.json").chmod(0)
        try:
            self.assertEqual(init(holder / "store")[0], 0)
        finally:
            (above / "store.json").chmod(0o600)

    @REAL_PERMISSIONS
    def test_a_place_that_cannot_be_looked_at(self) -> None:
        closed = self.root / "closed"
        (closed / "inside").mkdir(parents=True)
        with permissions(closed, 0o000):
            status, _, stderr = init(closed / "inside" / "store")
        self.assertEqual(status, 2)
        self.assertTrue(stderr.startswith("ERROR [SNAPSHOT_STORE_NOT_READABLE]: "), stderr)
        self.assertFalse((closed / "inside" / "store").exists())

    @REAL_SYMLINKS
    def test_every_snapshot_command_refuses_a_link_to_a_store(self) -> None:
        # Until stage B4a, every command stopped with SNAPSHOT_LIFECYCLE_FAILED.
        store = self.root / "store"
        initialize_store(store, ACCOUNT)
        link = self.root / "link"
        link.symlink_to(store, target_is_directory=True)
        export = self.root / "export"
        export.mkdir()
        commands = {
            "init": ("--account", ACCOUNT),
            "register": (
                "--input", export, "--label", "S1", "--requested-at", STAMP,
                "--downloaded-at", STAMP, "--observed-at", STAMP, "--confirm-complete",
            ),
            "status": (),
            "verify": (),
            "build-input": ("--output", self.root / "build"),
            "run-all": ("--output", self.root / "run"),
        }
        for command, arguments in commands.items():
            with self.subTest(command=command):
                status, stdout, stderr = cli("snapshot", command, "--store", link, *arguments)
                self.assertEqual(
                    (status, stdout, stderr), (2, "", line("SNAPSHOT_STORE_SYMLINK", STORE_SYMLINK_MESSAGE))
                )
        self.assertFalse((self.root / "build").exists())
        self.assertFalse((self.root / "run").exists())
        # A new store at a link is refused too.
        dangling = self.root / "dangling"
        dangling.symlink_to(self.root / "nowhere", target_is_directory=True)
        self.assert_stop(dangling, "SNAPSHOT_STORE_SYMLINK", STORE_SYMLINK_MESSAGE)

    def test_the_folders_above_a_new_store_may_be_links(self) -> None:
        if os.name == "nt":
            self.skipTest("symbolic links need privileges on Windows")
        target = self.root / "target"
        target.mkdir()
        holder = self.root / "holder-link"
        holder.symlink_to(target, target_is_directory=True)
        self.assertEqual(init(holder / "store")[0], 0)
        self.assertTrue((target / "store" / "store.json").is_file())


if __name__ == "__main__":
    unittest.main()
