"""An Export is read one file at a time, in a folder and in a ZIP file alike."""

from __future__ import annotations

import errno
import json
import os
import tempfile
import tracemalloc
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from garmin_running_data_normalizer.diagnostics.doctor import doctor_input
from garmin_running_data_normalizer.intake import source as source_module
from garmin_running_data_normalizer.intake.archive import ArchiveLimits
from garmin_running_data_normalizer.intake.discovery import (
    DiscoveredAsset,
    discover_export,
    read_export,
)
from garmin_running_data_normalizer.intake.source import ExportSource
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.snapshot import initialize_store
from garmin_running_data_normalizer.snapshot.store import load_manifests
from tests.test_zip_input import (
    register,
    run_cli,
    snapshot_register_arguments,
    write_export,
    zip_export,
)


MIB = 1024 * 1024
UNREAD_FILES = 24
NESTED_FILES = 24
# What a reading may hold at once, far below the size of the Export below.
PEAK_LIMIT = 16 * MIB


def write_large_export(root: Path) -> Path:
    """Write a synthetic Export with 48 MiB of JSON files that no normalizer uses."""
    folder = write_export(root)
    unread = folder / "DI_CONNECT/DI-Connect-Synthetic-Unread"
    unread.mkdir()
    for index in range(UNREAD_FILES):
        (unread / f"synthetic_unread_{index:02d}.json").write_text(
            json.dumps({"synthetic": os.urandom(MIB // 2).hex()}), encoding="utf-8"
        )
    with zipfile.ZipFile(
        folder / "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Large.zip",
        "w",
        compression=zipfile.ZIP_STORED,
    ) as archive:
        for index in range(NESTED_FILES):
            archive.writestr(
                f"synthetic_nested_{index:02d}.json",
                json.dumps({"synthetic": os.urandom(MIB // 2).hex()}),
            )
    return folder


def stored_zip(folder: Path, target: Path) -> Path:
    """Compress an Export folder without compression, which is quick for large files."""
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(folder).as_posix())
    return target


def peak_memory(action: Callable[[], Any]) -> int:
    """Return the peak of the memory that Python allocated while ``action`` ran.

    ``tracemalloc`` counts Python allocations only; buffers inside zlib and the
    operating system's file cache are not included.
    """
    tracemalloc.start()
    try:
        action()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


class OneFileAtATimeTest(unittest.TestCase):
    """Peak memory stays far below the Export's size."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls._directory.name)
        cls.folder = write_large_export(cls.root / "export")
        cls.archive = stored_zip(cls.folder, cls.root / "export.zip")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_run_all(self) -> None:
        for index, form in enumerate((self.folder, self.archive)):
            with self.subTest(form=form.name):
                output = self.root / f"run-all-{index}"
                peak = peak_memory(lambda: run_all(form, output))
                self.assertLess(peak, PEAK_LIMIT)
                manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(manifest["input_assets"]), UNREAD_FILES + NESTED_FILES)

    def test_doctor(self) -> None:
        for form in (self.folder, self.archive):
            with self.subTest(form=form.name):
                peak = peak_memory(lambda: doctor_input(form))
                self.assertLess(peak, PEAK_LIMIT)

    def test_snapshot_registration(self) -> None:
        for index, form in enumerate((self.folder, self.archive)):
            with self.subTest(form=form.name):
                store = self.root / f"store-{index}"
                initialize_store(store, "synthetic-account-boundary")
                peak = peak_memory(lambda: register(store, form))
                self.assertLess(peak, PEAK_LIMIT)
                [manifest] = load_manifests(store)
                self.assertGreaterEqual(manifest["archive_member_count"], NESTED_FILES)


class ReadCountTest(unittest.TestCase):
    def test_files_that_no_normalizer_uses_are_read_only_for_their_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            unread = folder / "DI_CONNECT/DI-Connect-Synthetic-Unread/synthetic_unread.json"
            unread.parent.mkdir()
            unread.write_text("{}", encoding="utf-8")
            digests: Counter[str] = Counter()
            reads: Counter[str] = Counter()
            original_digest = ExportSource.digest
            original_read = ExportSource.read

            def count_digest(export: ExportSource, item: Any) -> tuple[str, int]:
                digests[item.relative_path] += 1
                return original_digest(export, item)

            def count_read(export: ExportSource, item: Any) -> bytes:
                reads[item.relative_path] += 1
                return original_read(export, item)

            with mock.patch.object(ExportSource, "digest", count_digest), mock.patch.object(
                ExportSource, "read", count_read
            ):
                run_all(folder, root / "output")
            unread_path = "DI_CONNECT/DI-Connect-Synthetic-Unread/synthetic_unread.json"
            activities = "DI_CONNECT/DI-Connect-Fitness/synthetic_summarizedActivities.json"
            # Once at the start for the digests, once at the end to check them.
            self.assertEqual(digests[unread_path], 2)
            self.assertEqual(reads[unread_path], 0)
            self.assertEqual(digests[activities], 2)
            # Once to compare the accounts that the records name (stage A3a),
            # once to normalize them.
            self.assertEqual(reads[activities], 2)


class InputChangeTest(unittest.TestCase):
    def test_a_file_changed_before_it_is_read_stops_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            activities = folder / "DI_CONNECT/DI-Connect-Fitness/synthetic_summarizedActivities.json"

            def change_before_activities(event: dict[str, Any]) -> None:
                if event.get("step") == "activities":
                    activities.write_bytes(activities.read_bytes() + b" ")

            with self.assertRaises(RunAllError) as raised:
                run_all(folder, root / "output", progress=change_before_activities)
            self.assertEqual(raised.exception.code, "INPUT_CHANGED")
            self.assertFalse((root / "output").exists())

    def test_a_replaced_zip_file_is_found_by_the_final_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            archive = zip_export(folder, root / "export.zip")
            (folder / "synthetic-readme.txt").unlink()
            fitness = folder / "DI_CONNECT/DI-Connect-Fitness"
            (fitness / "synthetic_gear.json").write_text(
                json.dumps({"gearDTOS": [], "gearActivityDTOs": {}}), encoding="utf-8"
            )
            replacement = zip_export(folder, root / "replacement.zip")

            def replace_before_the_check(event: dict[str, Any]) -> None:
                if event.get("stage") == "verifying_input":
                    os.replace(replacement, archive)

            with self.assertRaises(RunAllError) as raised:
                run_all(archive, root / "output", progress=replace_before_the_check)
            self.assertEqual(raised.exception.code, "INPUT_CHANGED")
            self.assertFalse((root / "output").exists())


class TemporarySpaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.folder = write_export(self.root / "export")
        self.archive = zip_export(self.folder, self.root / "export.zip")
        self.temporary = self.root / "temporary"
        self.temporary.mkdir()

    def tearDown(self) -> None:
        self._directory.cleanup()

    def no_free_space(self) -> mock._patch[Any]:
        return mock.patch.object(
            source_module.shutil, "disk_usage", return_value=mock.Mock(free=0)
        )

    def test_too_little_space_stops_every_command_before_copying(self) -> None:
        with mock.patch.object(tempfile, "tempdir", str(self.temporary)), self.no_free_space():
            with self.assertRaises(RunAllError) as raised:
                run_all(self.archive, self.root / "output")
            self.assertEqual(raised.exception.code, "TEMP_SPACE_INSUFFICIENT")
            self.assertFalse((self.root / "output").exists())
            exit_code, console = run_cli(
                "run-all", "--input", str(self.archive), "--output", str(self.root / "output")
            )
            self.assertEqual(exit_code, 2)
            self.assertIn("ERROR [TEMP_SPACE_INSUFFICIENT]: the temporary folder", console)
            report = doctor_input(self.archive)
            self.assertEqual(
                [
                    (item["code"], item["safe_message_id"], item["next_action_id"])
                    for item in report["findings"]
                ],
                [
                    (
                        "TEMP_SPACE_INSUFFICIENT",
                        "TEMP_FOLDER_SPACE_INSUFFICIENT",
                        "FREE_TEMP_SPACE_OR_SELECT_EXTRACTED_FOLDER",
                    )
                ],
            )
            exit_code, console = run_cli(
                "normalize-activities",
                "--input",
                str(self.archive),
                "--output",
                str(self.root / "activities"),
            )
            self.assertEqual(exit_code, 2)
            self.assertIn("ERROR [TEMP_SPACE_INSUFFICIENT]", console)
            store = self.root / "store"
            initialize_store(store, "synthetic-account-boundary")
            exit_code, console = run_cli(*snapshot_register_arguments(store, self.archive))
            self.assertEqual(exit_code, 2)
            self.assertIn("ERROR [TEMP_SPACE_INSUFFICIENT]", console)
            self.assertEqual(load_manifests(store), [])
            # Nothing was copied, and a folder needs no copies.
            self.assertEqual(list(self.temporary.iterdir()), [])
            self.assertIn(run_all(self.folder, self.root / "folder-output")["exit_code"], (0, 3))

    def test_running_out_of_space_while_copying(self) -> None:
        full = OSError(errno.ENOSPC, "No space left on device")
        with mock.patch.object(tempfile, "tempdir", str(self.temporary)), mock.patch.object(
            source_module.shutil, "copyfileobj", side_effect=full
        ):
            with self.assertRaises(RunAllError) as raised:
                run_all(self.archive, self.root / "output")
        self.assertEqual(raised.exception.code, "TEMP_SPACE_INSUFFICIENT")
        self.assertEqual(list(self.temporary.iterdir()), [])


class CleanupTest(unittest.TestCase):
    def test_copies_are_closed_and_removed_after_a_run_and_a_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = zip_export(write_export(root / "export"), root / "export.zip")
            temporary = root / "temporary"
            temporary.mkdir()

            def cancel_while_reading_fit(event: dict[str, Any]) -> None:
                if event.get("stage") == "reading_fit":
                    # The copies exist and are open while FIT files are read.
                    self.assertEqual(len(list(temporary.iterdir())), 1)
                    raise KeyboardInterrupt

            with mock.patch.object(tempfile, "tempdir", str(temporary)):
                run_all(archive, root / "output")
                self.assertEqual(list(temporary.iterdir()), [])
                with self.assertRaises(KeyboardInterrupt):
                    run_all(archive, root / "cancelled", progress=cancel_while_reading_fit)
            # On Windows, removing the folder would fail if a copy were still open.
            self.assertEqual(list(temporary.iterdir()), [])
            self.assertFalse((root / "cancelled").exists())


class PublicFunctionsTest(unittest.TestCase):
    def test_discover_export_keeps_the_content_and_read_export_reads_it_on_demand(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            archive = zip_export(folder, root / "export.zip")
            for form in (folder, archive):
                with self.subTest(form=form.name):
                    kept = discover_export(form)
                    with read_export(form) as reading:
                        listed = reading.assets
                        self.assertEqual(
                            [(item.provenance_path, item.size_bytes, item.sha256) for item in listed],
                            [(item.provenance_path, item.size_bytes, item.sha256) for item in kept],
                        )
                        self.assertEqual([item.data for item in listed], [item.data for item in kept])
                        self.assertFalse(reading.changed)

    def test_assets_can_still_be_made_with_their_content(self) -> None:
        positional = DiscoveredAsset("json", "synthetic.json", None, 2, "0" * 64, b"{}")
        named = DiscoveredAsset(
            kind="json", source_path="synthetic.json", member_path=None,
            size_bytes=2, sha256="0" * 64, data=b"{}",
        )
        self.assertEqual(positional.data, named.data)
        self.assertEqual(positional.provenance_path, "synthetic.json")

    def test_totals_for_an_export_zip_file(self) -> None:
        limits = ArchiveLimits()
        self.assertEqual(limits.max_export_read_bytes, 64 * 1024 * MIB)
        self.assertEqual(limits.max_export_read_files, 4_000_000)


if __name__ == "__main__":
    unittest.main()
