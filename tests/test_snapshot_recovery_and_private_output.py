from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.runner import run_activities
from garmin_running_data_normalizer.snapshot.merge import SnapshotMergeError, build_approved_input
from garmin_running_data_normalizer.snapshot.store import (
    SnapshotStoreError,
    initialize_store,
    register_snapshot,
    verify_store,
)
from tests.test_snapshot_lifecycle import _activity, _write_snapshot

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_EXPORT = ROOT / "examples/synthetic/garmin_export"
ACCOUNT = "synthetic-account-boundary"


def register(store: Path, source: Path, label: str, day: int) -> dict[str, object]:
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
        confirm_complete=True,
    )


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def is_immutable_store_file(relative: str) -> bool:
    return (
        relative.startswith("blobs/")
        or relative.endswith("/manifest.json")
        or relative.endswith(".inventory.json")
    )


class PermissiveUmask:
    def __enter__(self) -> None:
        self.previous = os.umask(0)

    def __exit__(self, *exc_info: object) -> None:
        os.umask(self.previous)


@unittest.skipIf(os.name == "nt", "POSIX permission bits")
class PrivateOutputPermissionTest(unittest.TestCase):
    def test_new_snapshot_store_is_owner_only_under_permissive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            store.mkdir()
            store.chmod(0o755)
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])

            with PermissiveUmask():
                initialize_store(store, ACCOUNT)
                register(store, source, "S1", 1)

            self.assertEqual(mode(store), 0o700)
            observed = 0
            for path in store.rglob("*"):
                relative = path.relative_to(store).as_posix()
                observed += 1
                with self.subTest(path=relative):
                    if path.is_dir():
                        self.assertEqual(mode(path), 0o700)
                    elif is_immutable_store_file(relative):
                        self.assertEqual(mode(path), 0o400)
                    else:
                        self.assertEqual(mode(path), 0o600)
            self.assertGreater(observed, 5)
            self.assertEqual(verify_store(store)["status"], "PASS")

    def test_older_store_permissions_are_kept_and_still_verify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            first = root / "source-1"
            _write_snapshot(first, [_activity("A1")])
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            for path in [store, *store.rglob("*")]:
                relative = path.relative_to(store).as_posix()
                if path.is_dir():
                    path.chmod(0o755)
                elif is_immutable_store_file(relative):
                    path.chmod(0o444)
                else:
                    path.chmod(0o644)
            older = {path: mode(path) for path in store.rglob("*") if path.is_file()}

            second = root / "source-2"
            _write_snapshot(second, [_activity("A1"), _activity("A2")])
            register(store, second, "S2", 2)

            self.assertEqual(verify_store(store)["status"], "PASS")
            build_approved_input(store, root / "build")
            for path, previous in older.items():
                if is_immutable_store_file(path.relative_to(store).as_posix()):
                    self.assertEqual(mode(path), previous)

    def test_normalize_activities_output_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            created = root / "created"
            existing = root / "existing"
            existing.mkdir()
            existing.chmod(0o755)

            with PermissiveUmask():
                run_activities(SYNTHETIC_EXPORT, created)
                run_activities(SYNTHETIC_EXPORT, existing)

            self.assertEqual(mode(created), 0o700)
            self.assertEqual(mode(existing), 0o755)
            for output in (created, existing):
                files = [path for path in output.iterdir() if path.is_file()]
                self.assertEqual(len(files), 3)
                for path in files:
                    with self.subTest(path=path.name):
                        self.assertEqual(mode(path), 0o600)


class SnapshotRecoveryMessageTest(unittest.TestCase):
    def test_stop_conflict_error_reports_counts_without_private_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            for day, score in ((1, 71), (2, 99)):
                source = root / f"source-{day}"
                _write_snapshot(source, [_activity(f"A{day}")])
                metrics = source / "DI-Connect-Metrics"
                metrics.mkdir()
                (metrics / f"HillScore_conflict_{day}.json").write_text(
                    json.dumps(
                        [
                            {
                                "calendarDate": "2030-01-01",
                                "overallScore": score,
                                "strengthScore": 60,
                                "enduranceScore": 80,
                                "hillScoreClassificationId": 4,
                                "hillScoreFeedbackPhraseId": 12,
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                register(store, source, f"S{day}", day)

            with self.assertRaises(SnapshotMergeError) as context:
                build_approved_input(store, root / "build")

            message = str(context.exception)
            self.assertTrue(
                message.startswith("canonical merge contains unresolved stop conflicts: ")
            )
            self.assertIn("hill_score_daily same_stable_key_different_public_value=1", message)
            for private in ("2030-01-01", "71", "99", "canonical_key", str(root)):
                self.assertNotIn(private, message)
            self.assertFalse((root / "build").exists())

    def test_stale_lock_reports_holder_and_documented_recovery_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            first = root / "source-1"
            second = root / "source-2"
            _write_snapshot(first, [_activity("A1")])
            _write_snapshot(second, [_activity("A1"), _activity("A2")])
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            lock = store / ".single-writer.lock"
            lock.write_text("424242\n", encoding="ascii")
            (store / "journal" / "registration.json").write_text(
                json.dumps(
                    {
                        "format": "snapshot-registration-journal-v1",
                        "snapshot_id": "snapshot-interrupted",
                        "phase": "preserving_blobs",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SnapshotStoreError) as context:
                register(store, second, "S2", 2)
            message = str(context.exception)
            self.assertTrue(message.startswith("snapshot store is locked by another writer"))
            self.assertIn(".single-writer.lock", message)
            self.assertIn("pid 424242", message)
            self.assertIn("If no other snapshot command is running", message)
            verification = verify_store(store)
            self.assertEqual(verification["status"], "FAIL")
            self.assertIn("incomplete_registration_journal_present", verification["failures"])

            lock.unlink()
            result = register(store, second, "S2", 2)

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["recovery_status"], "incomplete_registration_reconciled")
            self.assertEqual(result["snapshot_count"], 2)
            self.assertEqual(verify_store(store)["status"], "PASS")

    def test_unreadable_lock_holder_is_reported_as_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            source = root / "source"
            _write_snapshot(source, [_activity("A1")])
            initialize_store(store, ACCOUNT)
            (store / ".single-writer.lock").write_text("not-a-pid\n", encoding="ascii")

            with self.assertRaises(SnapshotStoreError) as context:
                register(store, source, "S1", 1)

            self.assertIn("held by an unknown process", str(context.exception))


if __name__ == "__main__":
    unittest.main()
