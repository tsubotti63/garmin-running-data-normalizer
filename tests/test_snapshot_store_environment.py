"""Stops of the Snapshot Store and its build have a code and a next step
(stage A3d-3b): a store that cannot be written or has no free space, its lock
and an interrupted registration, which status and verify tell, a damaged
store and one that a newer version made, folders and files of the store that
cannot be opened, which status and a registration no longer pass over, a
listed Snapshot whose files are missing, an input that changes during a
registration, the temporary files of a stopped write, and the free space and
the output of the build."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_input  # noqa: F401
from garmin_running_data_normalizer.output_location import MESSAGES as OUTPUT_MESSAGES
from garmin_running_data_normalizer.run_all import RunAllError
from garmin_running_data_normalizer.runner import main
from garmin_running_data_normalizer.snapshot import (
    SnapshotLifecycleError,
    build_approved_input,
    initialize_store,
    run_snapshot_all,
    shown_store_message,
    snapshot_status,
    verify_store,
)
from garmin_running_data_normalizer.snapshot import store as store_module
from garmin_running_data_normalizer.snapshot.lifecycle import SNAPSHOT_BUILD_TEMP_MESSAGE
from garmin_running_data_normalizer.snapshot.store import (
    NEW_STORE_NOT_WRITABLE_MESSAGE,
    NOTICE_MESSAGES,
    REGISTRATION_INCOMPLETE_MESSAGE,
    REGISTRATION_INPUT_CHANGED_MESSAGE,
    STORE_INVALID_NEXT_STEP,
    STORE_NOT_WRITABLE_MESSAGE,
    STORE_SPACE_MESSAGE,
    STORE_VERSION_MESSAGE,
    load_manifests,
    store_not_readable_message,
)
from tests.test_environment_stops import REAL_PERMISSIONS, REAL_SYMLINKS, files, permissions
from tests.test_items_and_containers import ACTIVITIES, activities, export
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_record_updates import ACCOUNT
from tests.test_snapshot_unreadable_files import register

STORE = "garmin_running_data_normalizer.snapshot.store"
MERGE = "garmin_running_data_normalizer.snapshot.merge"
FIT = "DI-Connect-Uploaded-Files/synthetic_activity.fit"
JOURNAL = {
    "format": "snapshot-registration-journal-v1",
    "snapshot_id": "snapshot-interrupted",
    "phase": "preserving_blobs",
}
LISTS = ("registry.json", "snapshot_registry.json", "snapshot_family_coverage.json")


def later_files(name: str) -> dict[str, Any]:
    """The files of a later Export: one more Activity."""
    return {**files(), ACTIVITIES: activities(_activity("A1"), _activity("A2"), _activity(name))}


def cli(*args: object) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main([str(arg) for arg in args])
    return code, stdout.getvalue(), stderr.getvalue().strip()


def register_args(store: Path, source: Path, label: str, number: int) -> tuple[object, ...]:
    stamp = f"2030-01-{number:02d}T02:00:00+00:00"
    return (
        "snapshot", "register", "--store", store, "--input", source, "--label", label,
        "--requested-at", stamp, "--downloaded-at", stamp, "--observed-at", stamp,
        "--confirm-complete",
    )


def tree(root: Path) -> dict[str, bytes | None]:
    """The paths under a folder, with the bytes of its files."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def temporary_files(store: Path) -> list[str]:
    return sorted(path.relative_to(store).as_posix() for path in store.rglob("*.tmp"))


@contextlib.contextmanager
def closed(*folders: Path) -> Iterator[None]:
    """Make these folders fail to open, as their permissions make them, on any
    system: they cannot be listed, and nothing in them can be looked at."""
    real_scandir, real_stat, real_lstat = os.scandir, os.stat, os.lstat

    def within(path: Any, *, itself: bool) -> bool:
        path = Path(path)
        return any(folder in path.parents or (itself and path == folder) for folder in folders)

    def denied(path: Any) -> PermissionError:
        return PermissionError(errno.EACCES, "denied", str(path))

    def scandir(path: Any = ".") -> Any:
        if within(path, itself=True):
            raise denied(path)
        return real_scandir(path)

    def stat(path: Any, *args: Any, **kwargs: Any) -> Any:
        if within(path, itself=False):
            raise denied(path)
        return real_stat(path, *args, **kwargs)

    def lstat(path: Any, *args: Any, **kwargs: Any) -> Any:
        if within(path, itself=False):
            raise denied(path)
        return real_lstat(path, *args, **kwargs)

    with (
        mock.patch(f"{STORE}.os.scandir", side_effect=scandir),
        mock.patch(f"{STORE}.os.stat", side_effect=stat),
        mock.patch(f"{STORE}.os.lstat", side_effect=lstat),
    ):
        yield


class Store(unittest.TestCase):
    """A store with one Snapshot, in a temporary folder."""

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        # The store works on the resolved path of its folder.
        self.root = Path(directory.name).resolve()
        self.store = self.root / "store"
        initialize_store(self.store, ACCOUNT)
        register(self.store, export(self.root, "first", files()), "S1", 1)

    def later(self, name: str = "second", activity: str = "A3") -> Path:
        return export(self.root, name, later_files(activity))

    def stops(self, code: str, *args: object) -> str:
        """Run a snapshot command that must stop with ``code``; return the
        rest of its error line."""
        exit_code, stdout, stderr = cli("snapshot", *args)
        self.assertEqual(exit_code, 2, (args, stderr))
        prefix = f"ERROR [{code}]: "
        self.assertTrue(stderr.startswith(prefix), (args, stderr))
        return stderr[len(prefix):]

    def every_reading_command(self) -> list[tuple[object, ...]]:
        return [
            ("status", "--store", self.store),
            ("verify", "--store", self.store),
            ("build-input", "--store", self.store, "--output", self.root / "build"),
            ("run-all", "--store", self.store, "--output", self.root / "output"),
        ]


class NormalStoreTest(Store):
    def test_a_store_without_problems_reports_as_before(self) -> None:
        status = snapshot_status(self.store)
        self.assertEqual(
            sorted(status), ["account_store_id", "automatic_deletion", "snapshot_count", "snapshots", "status"]
        )
        verification = verify_store(self.store)
        self.assertEqual(verification["status"], "PASS")
        self.assertNotIn("notices", verification)
        result = register(self.store, self.later(), "S2", 2)
        self.assertNotIn("temporary_files_removed", result)
        for command in ("status", "verify"):
            code, _, stderr = cli("snapshot", command, "--store", self.store)
            self.assertEqual((code, stderr), (0, ""), command)


class LockAndJournalTest(Store):
    def test_a_lock_stops_a_registration_and_status_and_verify_tell_it(self) -> None:
        (self.store / ".single-writer.lock").write_text("424242\n", encoding="ascii")
        message = self.stops("SNAPSHOT_STORE_LOCKED", *register_args(self.store, self.later(), "S2", 2)[1:])
        self.assertTrue(message.startswith("snapshot store is locked by another writer"), message)
        self.assertIn("pid 424242", message)
        self.assertIn("delete that lock file", message)
        for command in ("status", "verify"):
            code, stdout, stderr = cli("snapshot", command, "--store", self.store)
            # A notice never stops a command.
            self.assertEqual(code, 0, command)
            self.assertEqual(json.loads(stdout)["notices"], ["SNAPSHOT_STORE_LOCKED"])
            self.assertEqual(
                stderr, f"NOTE [SNAPSHOT_STORE_LOCKED]: {NOTICE_MESSAGES['SNAPSHOT_STORE_LOCKED']}"
            )
        # The commands that only read the store still run.
        build_approved_input(self.store, self.root / "build")

    def test_an_interrupted_registration_is_named_until_the_next_one_completes_it(self) -> None:
        journal = self.store / "journal" / "registration.json"
        journal.write_text(json.dumps(JOURNAL), encoding="utf-8")
        code, stdout, stderr = cli("snapshot", "status", "--store", self.store)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["notices"], ["SNAPSHOT_REGISTRATION_INCOMPLETE"])
        self.assertEqual(stderr, f"NOTE [SNAPSHOT_REGISTRATION_INCOMPLETE]: {REGISTRATION_INCOMPLETE_MESSAGE}")
        code, stdout, stderr = cli("snapshot", "verify", "--store", self.store)
        self.assertEqual(code, 2)
        # verify still prints its report, and an error line.
        self.assertEqual(json.loads(stdout)["failures"], ["incomplete_registration_journal_present"])
        self.assertEqual(stderr, f"ERROR [SNAPSHOT_REGISTRATION_INCOMPLETE]: {REGISTRATION_INCOMPLETE_MESSAGE}")
        for args in self.every_reading_command()[2:]:
            self.assertEqual(self.stops("SNAPSHOT_REGISTRATION_INCOMPLETE", *args), REGISTRATION_INCOMPLETE_MESSAGE)
        result = register(self.store, self.later(), "S2", 2)
        self.assertEqual(result["recovery_status"], "incomplete_registration_reconciled")
        self.assertNotIn("notices", snapshot_status(self.store))
        self.assertEqual(verify_store(self.store)["status"], "PASS")

    def test_a_registration_stopped_before_its_lists_were_written_is_incomplete(self) -> None:
        lists = {name: (self.store / name).read_bytes() for name in LISTS}
        result = register(self.store, self.later(), "S2", 2)
        # As if the registration stopped after it wrote the Snapshot and
        # before it wrote the lists again.
        for name, data in lists.items():
            (self.store / name).write_bytes(data)
        (self.store / "journal" / "registration.json").write_text(
            json.dumps({**JOURNAL, "snapshot_id": result["snapshot_id"]}), encoding="utf-8"
        )
        self.assertIn("registry_manifest_binding_mismatch", verify_store(self.store)["failures"])
        self.stops("SNAPSHOT_REGISTRATION_INCOMPLETE", "verify", "--store", self.store)
        again = register(self.store, self.later("second-again"), "S2", 2)
        self.assertEqual(again["recovery_status"], "completed_commit_reconciled")
        self.assertEqual(verify_store(self.store)["status"], "PASS")

    def test_the_journal_is_kept_when_its_registration_stops_before_it_is_completed(self) -> None:
        journal = self.store / "journal" / "registration.json"
        journal.write_text(json.dumps(JOURNAL), encoding="utf-8")
        before = tree(self.store)
        unreadable = SnapshotLifecycleError(
            store_not_readable_message(), "SNAPSHOT_STORE_NOT_READABLE", places=["snapshots/synthetic"]
        )
        with mock.patch(f"{STORE}.load_manifests", side_effect=unreadable):
            with self.assertRaises(SnapshotLifecycleError):
                register(self.store, self.later(), "S2", 2)
        # The registry was not written again, and the journal is still there.
        self.assertEqual(tree(self.store), before)


class DamagedStoreTest(Store):
    def test_other_failures_of_verification_are_a_damaged_store(self) -> None:
        (self.store / "registry.json").write_text(json.dumps({"format": "tampered", "snapshots": []}), encoding="utf-8")
        code, stdout, stderr = cli("snapshot", "verify", "--store", self.store)
        self.assertEqual(code, 2)
        self.assertIn("registry_manifest_binding_mismatch", json.loads(stdout)["failures"])
        expected = (
            "the Snapshot Store failed verification (registry_manifest_binding_mismatch, "
            f"snapshot_registry_alias_mismatch); {STORE_INVALID_NEXT_STEP}"
        )
        self.assertEqual(stderr, f"ERROR [SNAPSHOT_STORE_INVALID]: {expected}")
        for args in self.every_reading_command()[2:]:
            self.assertEqual(self.stops("SNAPSHOT_STORE_INVALID", *args), expected)

    def test_a_damaged_file_of_the_store_is_a_damaged_store_for_every_command(self) -> None:
        (self.store / "store.json").write_text("{not json", encoding="utf-8")
        expected = (
            "the Snapshot Store is damaged: invalid snapshot store metadata: store.json; "
            f"{STORE_INVALID_NEXT_STEP}"
        )
        self.assertEqual(self.stops("SNAPSHOT_STORE_INVALID", "status", "--store", self.store), expected)
        self.assertEqual(
            self.stops("SNAPSHOT_STORE_INVALID", *register_args(self.store, self.later(), "S2", 2)[1:]), expected
        )
        code, stdout, stderr = cli("snapshot", "verify", "--store", self.store)
        self.assertEqual(json.loads(stdout)["failures"], ["snapshot_store_metadata_failure"])
        self.assertTrue(stderr.startswith("ERROR [SNAPSHOT_STORE_INVALID]: "), stderr)

    def test_a_manifest_that_breaks_the_contract_is_a_damaged_store(self) -> None:
        manifest = self.store / "snapshots" / load_manifests(self.store)[0]["snapshot_id"] / "manifest.json"
        value = json.loads(manifest.read_text(encoding="utf-8"))
        manifest.chmod(0o600)
        manifest.write_text(json.dumps({**value, "immutable": False}), encoding="utf-8")
        self.assertEqual(
            self.stops("SNAPSHOT_STORE_INVALID", "status", "--store", self.store),
            f"the Snapshot Store is damaged: snapshot manifest is not immutable; {STORE_INVALID_NEXT_STEP}",
        )

    def test_a_store_of_a_newer_version_is_not_a_damaged_one(self) -> None:
        metadata = json.loads((self.store / "store.json").read_text(encoding="utf-8"))
        newer = {**metadata, "contract_version": "garmin_public_snapshot_lifecycle:v9.0"}
        (self.store / "store.json").write_text(json.dumps(newer), encoding="utf-8")
        commands = [
            *self.every_reading_command(),
            register_args(self.store, self.later(), "S2", 2)[1:],
            ("init", "--store", self.store, "--account-store-id", ACCOUNT),
        ]
        for args in commands:
            code, stdout, stderr = cli("snapshot", *args)
            self.assertEqual(code, 2, args)
            # verify cannot check such a store either, and prints no report.
            self.assertEqual(stdout, "", args)
            self.assertEqual(stderr, f"ERROR [SNAPSHOT_STORE_VERSION_UNSUPPORTED]: {STORE_VERSION_MESSAGE}")
        newer_format = {**metadata, "format": "garmin-running-data-normalizer-snapshot-store-v2", "format_version": 2}
        (self.store / "store.json").write_text(json.dumps(newer_format), encoding="utf-8")
        self.stops("SNAPSHOT_STORE_VERSION_UNSUPPORTED", "status", "--store", self.store)
        # A store.json of another kind is not a store of a newer version.
        (self.store / "store.json").write_text(json.dumps({**metadata, "format": "another-format"}), encoding="utf-8")
        self.stops("SNAPSHOT_STORE_INVALID", "status", "--store", self.store)

    def test_a_registration_never_takes_a_listed_snapshot_out_of_the_registry(self) -> None:
        register(self.store, self.later(), "S2", 2)
        first = self.store / "snapshots" / load_manifests(self.store)[0]["snapshot_id"]
        # As if the folder was deleted by hand or removed by a sync app.
        first.rename(self.root / "moved")
        before = tree(self.store)
        for source, label, number in (
            (self.later("third", "A4"), "S3", 3),
            (self.later("second-again"), "S2", 2),
        ):
            with self.assertRaises(SnapshotLifecycleError) as raised:
                register(self.store, source, label, number)
            self.assertEqual(raised.exception.code, "SNAPSHOT_STORE_INVALID")
            self.assertIn("deleted by hand or removed by a sync app", str(raised.exception))
            self.assertEqual(tree(self.store), before)
        (self.root / "moved").rename(first)
        self.assertEqual(verify_store(self.store)["status"], "PASS")


class WriteAndSpaceTest(Store):
    def test_a_store_that_cannot_be_written_stops_before_the_input_is_read(self) -> None:
        real_open = os.open

        def lock_denied(path: Any, *args: Any, **kwargs: Any) -> int:
            if Path(path).name == ".single-writer.lock":
                raise PermissionError(errno.EACCES, "denied", str(path))
            return real_open(path, *args, **kwargs)

        before = tree(self.store)
        with (
            mock.patch(f"{STORE}.os.open", side_effect=lock_denied),
            mock.patch(f"{STORE}._scan_source", side_effect=AssertionError("the input was read")),
        ):
            message = self.stops("SNAPSHOT_STORE_NOT_WRITABLE", *register_args(self.store, self.later(), "S2", 2)[1:])
        self.assertEqual(message, STORE_NOT_WRITABLE_MESSAGE)
        self.assertEqual(tree(self.store), before)

    @REAL_PERMISSIONS
    def test_real_permissions(self) -> None:
        source = self.later()
        before = tree(self.store)
        with permissions(self.store, 0o555):
            self.stops("SNAPSHOT_STORE_NOT_WRITABLE", *register_args(self.store, source, "S2", 2)[1:])
        self.assertEqual(tree(self.store), before)

    def test_too_little_free_space_stops_before_anything_is_written(self) -> None:
        before = tree(self.store)
        usage = shutil.disk_usage(self.root)._replace(free=0)
        with mock.patch(f"{STORE}.shutil.disk_usage", return_value=usage):
            message = self.stops(
                "SNAPSHOT_STORE_SPACE_INSUFFICIENT", *register_args(self.store, self.later(), "S2", 2)[1:]
            )
            self.assertEqual(message, STORE_SPACE_MESSAGE)
            self.assertEqual(tree(self.store), before)
            # Only the files that the store does not hold are counted: an
            # Export of files that it holds needs no space for them.
            held = export(self.root, "held", {ACTIVITIES: files()[ACTIVITIES]})
            self.assertEqual(register(self.store, held, "S2", 2)["blob_added_count"], 0)

    def test_no_space_while_a_file_is_copied(self) -> None:
        real = os.fsync
        calls: list[int] = []

        def full(descriptor: int) -> None:
            # The journal is written first, then the first new file.
            calls.append(descriptor)
            if len(calls) == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
            real(descriptor)

        source = self.later()
        with mock.patch(f"{STORE}.os.fsync", side_effect=full):
            with self.assertRaises(SnapshotLifecycleError) as raised:
                register(self.store, source, "S2", 2)
        self.assertEqual(raised.exception.code, "SNAPSHOT_STORE_SPACE_INSUFFICIENT")
        self.assertTrue((self.store / "journal" / "registration.json").exists())
        # The file that was not copied whole is gone at once.
        self.assertEqual(temporary_files(self.store), [])
        result = register(self.store, source, "S2", 2)
        self.assertEqual(result["recovery_status"], "incomplete_registration_reconciled")
        self.assertEqual(verify_store(self.store)["status"], "PASS")

    def test_temporary_files_are_removed_by_their_names_only(self) -> None:
        snapshot_id = load_manifests(self.store)[0]["snapshot_id"]
        digest = "ab" + "0" * 62
        removed = [
            ".registry.json.123.tmp",
            ".store.json.9.tmp",
            "journal/.registration.json.5.tmp",
            f"snapshots/{snapshot_id}/.manifest.json.7.tmp",
            f"snapshots/{snapshot_id}/.{snapshot_id}.inventory.json.8.tmp",
            f"blobs/sha256/ab/.{digest}.4.tmp",
        ]
        kept = [
            "notes.tmp",
            ".other.json.1.tmp",
            ".registry.json.tmp",
            "journal/.registration.json.x.tmp",
            f"snapshots/{snapshot_id}/.registry.json.2.tmp",
            # The SHA-256 of a blob starts with the name of its folder.
            f"blobs/sha256/ab/.cd{'0' * 62}.4.tmp",
            f"blobs/sha256/ab/.{digest}.tmp",
            f"blobs/sha256/abc/.{digest}.4.tmp",
        ]
        for name in removed + kept:
            path = self.store / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"partial")
        (self.store / ".snapshot_registry.json.3.tmp").mkdir()
        result = register(self.store, self.later(), "S2", 2)
        self.assertEqual(result["temporary_files_removed"], len(removed))
        for name in removed:
            self.assertFalse((self.store / name).exists(), name)
        for name in kept:
            self.assertTrue((self.store / name).exists(), name)
        self.assertTrue((self.store / ".snapshot_registry.json.3.tmp").is_dir())

    @REAL_SYMLINKS
    def test_the_removal_of_temporary_files_follows_no_link(self) -> None:
        target = self.root / "target.tmp"
        target.write_bytes(b"outside")
        link = self.store / ".registry.json.6.tmp"
        link.symlink_to(target)
        source = self.later()
        # A folder of blobs that links outside the store, by a name that no
        # file of this registration uses.
        used = {hashlib.sha256(path.read_bytes()).hexdigest()[:2] for path in source.rglob("*") if path.is_file()}
        used |= {path.name for path in (self.store / "blobs" / "sha256").iterdir()}
        prefix = next(f"{number:02x}" for number in range(256) if f"{number:02x}" not in used)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / f".{prefix}{'0' * 62}.1.tmp").write_bytes(b"outside")
        (self.store / "blobs" / "sha256" / prefix).symlink_to(outside, target_is_directory=True)
        result = register(self.store, source, "S2", 2)
        self.assertNotIn("temporary_files_removed", result)
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"outside")
        self.assertEqual(sorted(path.name for path in outside.iterdir()), [f".{prefix}{'0' * 62}.1.tmp"])


class NotReadableTest(Store):
    def setUp(self) -> None:
        super().setUp()
        register(self.store, self.later(), "S2", 2)
        self.first = self.store / "snapshots" / load_manifests(self.store)[0]["snapshot_id"]
        self.place = f"snapshots/{self.first.name}"

    def test_a_snapshot_folder_that_cannot_be_opened_stops_every_command(self) -> None:
        before = tree(self.store)
        with closed(self.first):
            for args in self.every_reading_command():
                self.assertEqual(
                    self.stops("SNAPSHOT_STORE_NOT_READABLE", *args),
                    store_not_readable_message([self.place]),
                )
            with self.assertRaises(SnapshotLifecycleError) as raised:
                register(self.store, self.later("third", "A4"), "S3", 3)
        self.assertEqual(raised.exception.code, "SNAPSHOT_STORE_NOT_READABLE")
        # The place is named only where the command is started.
        self.assertNotIn(self.first.name, str(raised.exception))
        self.assertIn(self.place, shown_store_message(raised.exception))
        # The registry was not written again without the Snapshot.
        self.assertEqual(tree(self.store), before)
        self.assertEqual(snapshot_status(self.store)["snapshot_count"], 2)
        self.assertEqual(verify_store(self.store)["status"], "PASS")

    def test_a_folder_of_blobs_that_cannot_be_opened_stops_verification_and_the_build(self) -> None:
        folder = next((self.store / "blobs" / "sha256").iterdir())
        with closed(folder):
            # status does not read the blobs.
            self.assertEqual(snapshot_status(self.store)["snapshot_count"], 2)
            for args in self.every_reading_command()[1:]:
                self.assertEqual(
                    self.stops("SNAPSHOT_STORE_NOT_READABLE", *args),
                    store_not_readable_message([f"blobs/sha256/{folder.name}"]),
                )

    @REAL_PERMISSIONS
    def test_real_permissions(self) -> None:
        before = tree(self.store)
        with permissions(self.first, 0o000):
            self.stops("SNAPSHOT_STORE_NOT_READABLE", "status", "--store", self.store)
            with self.assertRaises(SnapshotLifecycleError) as raised:
                register(self.store, self.later("third", "A4"), "S3", 3)
            self.assertEqual(raised.exception.places, [self.place])
        self.assertEqual(tree(self.store), before)
        blob = next(path for path in (self.store / "blobs" / "sha256").rglob("*") if path.is_file())
        with permissions(blob, 0o000):
            message = self.stops("SNAPSHOT_STORE_NOT_READABLE", "verify", "--store", self.store)
            self.assertIn(blob.relative_to(self.store).as_posix(), message)
            self.stops("SNAPSHOT_STORE_NOT_READABLE", "run-all", "--store", self.store, "--output", self.root / "output")
        with permissions(self.store / "store.json", 0o000):
            self.assertEqual(
                self.stops("SNAPSHOT_STORE_NOT_READABLE", "status", "--store", self.store),
                store_not_readable_message(["store.json"]),
            )
        with permissions(self.store, 0o000):
            for command in ("status", "verify"):
                self.assertEqual(
                    self.stops("SNAPSHOT_STORE_NOT_READABLE", command, "--store", self.store),
                    store_not_readable_message([""]),
                )
        self.assertEqual(verify_store(self.store)["status"], "PASS")


class InputChangedTest(Store):
    def test_a_file_that_changes_after_it_was_listed(self) -> None:
        source = self.later()
        real = store_module._check_space

        def change(*args: Any) -> None:
            real(*args)
            (source / ACTIVITIES).write_text(json.dumps(activities(_activity("Z9"))), encoding="utf-8")

        with mock.patch(f"{STORE}._check_space", side_effect=change):
            message = self.stops("INPUT_CHANGED", *register_args(self.store, source, "S2", 2)[1:])
        self.assertEqual(message, REGISTRATION_INPUT_CHANGED_MESSAGE)
        self.assertEqual(temporary_files(self.store), [])
        # The next registration completes the store.
        self.assertEqual(register(self.store, source, "S2", 2)["recovery_status"], "incomplete_registration_reconciled")

    def test_a_file_that_goes_away_after_it_was_listed(self) -> None:
        source = self.later()
        real = store_module._check_space

        def remove(*args: Any) -> None:
            real(*args)
            (source / ACTIVITIES).unlink()

        with mock.patch(f"{STORE}._check_space", side_effect=remove):
            with self.assertRaises(SnapshotLifecycleError) as raised:
                register(self.store, source, "S2", 2)
        self.assertEqual(raised.exception.code, "INPUT_CHANGED")

    def test_a_folder_that_goes_away_while_the_input_is_listed(self) -> None:
        with mock.patch(f"{STORE}.walk_paths", side_effect=FileNotFoundError(errno.ENOENT, "gone")):
            with self.assertRaises(SnapshotLifecycleError) as raised:
                register(self.store, self.later(), "S2", 2)
        self.assertEqual(raised.exception.code, "INPUT_CHANGED")


class BuildTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        # The store works on the resolved path of its folder.
        self.root = Path(directory.name).resolve()
        self.store = self.root / "store"
        initialize_store(self.store, ACCOUNT)
        register(self.store, export(self.root, "export", {**files(), FIT: "x" * 2000}))

    def test_the_build_stops_before_it_starts_without_room_for_its_fit_files(self) -> None:
        usage = shutil.disk_usage(self.root)._replace(free=1000)
        with (
            mock.patch(f"{MERGE}.shutil.disk_usage", return_value=usage),
            mock.patch(f"{MERGE}._read_blob", side_effect=AssertionError("the build started")),
        ):
            with self.assertRaises(RunAllError) as raised:
                run_snapshot_all(self.store, self.root / "output")
            self.assertEqual(raised.exception.code, "TEMP_SPACE_INSUFFICIENT")
            self.assertEqual(raised.exception.safe_message, SNAPSHOT_BUILD_TEMP_MESSAGE)
            code, _, stderr = cli("snapshot", "build-input", "--store", self.store, "--output", self.root / "build")
        self.assertEqual(code, 2)
        self.assertEqual(stderr, f"ERROR [OUTPUT_SPACE_INSUFFICIENT]: {OUTPUT_MESSAGES['OUTPUT_SPACE_INSUFFICIENT']}")
        self.assertFalse((self.root / "build").exists())
        # Room for the FIT files is enough to start.
        with mock.patch(f"{MERGE}.shutil.disk_usage", return_value=usage._replace(free=2000)):
            build_approved_input(self.store, self.root / "build")

    def test_no_space_while_the_build_is_written(self) -> None:
        full = OSError(errno.ENOSPC, "No space left on device")
        with mock.patch(f"{MERGE}._write_bytes", side_effect=full):
            code, _, stderr = cli("snapshot", "run-all", "--store", self.store, "--output", self.root / "output")
            self.assertEqual((code, stderr), (2, f"ERROR [TEMP_SPACE_INSUFFICIENT]: {SNAPSHOT_BUILD_TEMP_MESSAGE}"))
            with self.assertRaises(SnapshotLifecycleError) as raised:
                build_approved_input(self.store, self.root / "build")
        self.assertEqual(raised.exception.code, "OUTPUT_SPACE_INSUFFICIENT")
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["export", "store"])

    def test_build_input_checks_its_output_before_the_store(self) -> None:
        with (
            mock.patch(
                "garmin_running_data_normalizer.output_location.tempfile.mkdtemp",
                side_effect=PermissionError(errno.EACCES, "denied"),
            ),
            mock.patch(f"{MERGE}.verify_store", side_effect=AssertionError("the store was verified")),
        ):
            code, _, stderr = cli("snapshot", "build-input", "--store", self.store, "--output", self.root / "build")
        self.assertEqual(code, 2)
        self.assertEqual(stderr, f"ERROR [OUTPUT_PARENT_NOT_WRITABLE]: {OUTPUT_MESSAGES['OUTPUT_PARENT_NOT_WRITABLE']}")

    @REAL_PERMISSIONS
    def test_real_permissions(self) -> None:
        parent = self.root / "parent"
        parent.mkdir()
        with permissions(parent, 0o555):
            code, _, stderr = cli("snapshot", "build-input", "--store", self.store, "--output", parent / "build")
        self.assertEqual(code, 2)
        self.assertTrue(stderr.startswith("ERROR [OUTPUT_PARENT_NOT_WRITABLE]: "), stderr)
        self.assertEqual(list(parent.iterdir()), [])


class InitTest(unittest.TestCase):
    def test_a_place_where_the_store_cannot_be_made(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch(
                f"{STORE}.ensure_private_directory", side_effect=PermissionError(errno.EACCES, "denied")
            ):
                code, _, stderr = cli("snapshot", "init", "--store", root / "store", "--account-store-id", ACCOUNT)
            self.assertEqual((code, stderr), (2, f"ERROR [SNAPSHOT_STORE_NOT_WRITABLE]: {NEW_STORE_NOT_WRITABLE_MESSAGE}"))
            self.assertFalse((root / "store").exists())

    @REAL_PERMISSIONS
    def test_real_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "parent"
            parent.mkdir()
            with permissions(parent, 0o555):
                code, _, stderr = cli("snapshot", "init", "--store", parent / "store", "--account-store-id", ACCOUNT)
            self.assertEqual((code, stderr), (2, f"ERROR [SNAPSHOT_STORE_NOT_WRITABLE]: {NEW_STORE_NOT_WRITABLE_MESSAGE}"))

    def test_an_init_that_runs_out_of_space_can_be_run_again(self) -> None:
        full = OSError(errno.ENOSPC, "No space left on device")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root / "empty"
            empty.mkdir()
            for store in (root / "store", empty):
                with mock.patch(f"{STORE}.os.fsync", side_effect=full):
                    with self.assertRaises(SnapshotLifecycleError) as raised:
                        initialize_store(store, ACCOUNT)
                self.assertEqual(raised.exception.code, "SNAPSHOT_STORE_SPACE_INSUFFICIENT")
                # What it wrote is removed: a new folder entirely, and an
                # empty folder that was there is left empty.
                if store == empty:
                    self.assertEqual(list(store.iterdir()), [])
                else:
                    self.assertFalse(store.exists())
                self.assertTrue(initialize_store(store, ACCOUNT)["initialized"])


class UnexpectedErrorTest(unittest.TestCase):
    def test_an_unexpected_error_of_a_snapshot_command_names_the_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "store"
            with mock.patch("garmin_running_data_normalizer.snapshot.snapshot_status", side_effect=RuntimeError):
                code, _, stderr = cli("snapshot", "status", "--store", store)
            self.assertEqual(
                (code, stderr),
                (2, "ERROR [COMMAND_FAILED]: snapshot status failed; verify the input and output contract"),
            )
            with mock.patch("garmin_running_data_normalizer.snapshot.run_snapshot_all", side_effect=RuntimeError):
                code, _, stderr = cli("snapshot", "run-all", "--store", store, "--output", Path(directory) / "output")
            self.assertEqual(
                (code, stderr),
                (2, "ERROR [RUN_ALL_FAILED]: Run-All failed; verify the input and output contract"),
            )


if __name__ == "__main__":
    unittest.main()
