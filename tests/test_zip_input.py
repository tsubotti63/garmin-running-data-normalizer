"""An Export given as its downloaded ZIP file is read as the folder extracted from it."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import struct
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from garmin_running_data_normalizer import runner
from garmin_running_data_normalizer.diagnostics.doctor import doctor_input
from garmin_running_data_normalizer.intake import source as source_module
from garmin_running_data_normalizer.intake.archive import ArchiveLimits, UnsafeArchiveError
from garmin_running_data_normalizer.intake.discovery import discover_export
from garmin_running_data_normalizer.intake.source import (
    CorruptArchiveError,
    ExportSource,
    ExportTooLargeError,
)
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.snapshot import (
    SnapshotLifecycleError,
    build_approved_input,
    initialize_store,
    register_snapshot,
    verify_store,
)
from garmin_running_data_normalizer.snapshot.store import load_manifests
from tests.fit_fixture_factory import synthetic_fit


ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = ROOT / "examples/synthetic/garmin_export/DI-Connect-Fitness/synthetic_summarizedActivities.json"
ACTIVITIES_PATH = "DI_CONNECT/DI-Connect-Fitness/synthetic_summarizedActivities.json"
WRAPPER = "Garmin Export Synthetic"


def write_export(root: Path) -> Path:
    """Write a synthetic Export in the layout of a real one."""
    connect = root / "DI_CONNECT"
    fitness = connect / "DI-Connect-Fitness"
    fitness.mkdir(parents=True)
    shutil.copyfile(ACTIVITIES, fitness / "synthetic_summarizedActivities.json")
    (fitness / "synthetic_gear.json").write_text(
        json.dumps(
            {
                "gearDTOS": [{"gearPk": "SYNTHETIC-GEAR-1", "displayName": "Synthetic Shoe"}],
                "gearActivityDTOs": {"SYNTHETIC-GEAR-1": [{"activityId": "SYNTHETIC-RUN-0001"}]},
            }
        ),
        encoding="utf-8",
    )
    (fitness / "synthetic_personalRecord.json").write_text(
        json.dumps(
            {
                "personalRecords": [
                    {
                        "personalRecordId": "SYNTHETIC-PR-1",
                        "activityId": "SYNTHETIC-RUN-0001",
                        "personalRecordType": "synthetic_best",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    # Garmin keeps uploaded FIT files in ZIP files inside the Export: one is
    # stored here and one compressed, and the second holds a ZIP file that is
    # not read.
    uploaded = connect / "DI-Connect-Uploaded-Files"
    uploaded.mkdir()
    with zipfile.ZipFile(
        uploaded / "UploadedFiles_synthetic_Part1.zip", "w", compression=zipfile.ZIP_STORED
    ) as archive:
        archive.writestr("synthetic-session-1.fit", synthetic_fit())
        archive.writestr("synthetic-notes.txt", "synthetic\n")
    deeper = io.BytesIO()
    with zipfile.ZipFile(deeper, "w") as archive:
        archive.writestr("deeper_summarizedActivities.json", ACTIVITIES.read_bytes())
    with zipfile.ZipFile(
        uploaded / "UploadedFiles_synthetic_Part2.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr("synthetic-session-2.fit", synthetic_fit(sessions=2))
        archive.writestr("synthetic-deeper.zip", deeper.getvalue())
    # A folder whose name extends another folder's name: sorted as paths and
    # sorted as text, these files come in different orders.
    extra = connect / "DI-Connect-Fitness-Synthetic"
    extra.mkdir()
    (extra / "synthetic-notes.txt").write_text("synthetic\n", encoding="utf-8")
    (connect / ".DS_Store").write_bytes(b"synthetic metadata")
    (root / "synthetic-readme.txt").write_text("synthetic\n", encoding="utf-8")
    return root


def zip_export(
    folder: Path,
    target: Path,
    *,
    wrapper: str | None = None,
    folder_entries: bool = True,
) -> Path:
    """Compress an Export folder as Garmin or an operating system would."""
    prefix = f"{wrapper}/" if wrapper else ""
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if wrapper and folder_entries:
            archive.writestr(prefix, b"")
        for path in sorted(folder.rglob("*")):
            name = prefix + path.relative_to(folder).as_posix()
            if path.is_dir():
                if folder_entries:
                    archive.writestr(f"{name}/", b"")
            else:
                archive.write(path, name)
        archive.writestr(f"__MACOSX/{prefix}._synthetic-readme.txt", b"synthetic metadata")
    return target


def wrap_folder(folder: Path, parent: Path, names: tuple[str, ...] = (WRAPPER,)) -> Path:
    """Put the Export folder inside other folders, as when a folder above it is selected."""
    parent.mkdir()
    target = parent.joinpath(*names)
    shutil.copytree(folder, target)
    (parent / ".DS_Store").write_bytes(b"synthetic metadata")
    (target.parent / ".DS_Store").write_bytes(b"synthetic metadata")
    return parent


def flip_member_byte(source: Path, name: str, target: Path) -> Path:
    """Change one byte of a member's data, as a damaged download would."""
    data = bytearray(source.read_bytes())
    with zipfile.ZipFile(source) as archive:
        info = archive.getinfo(name)
    header = info.header_offset
    name_length, extra_length = struct.unpack("<HH", data[header + 26 : header + 30])
    start = header + 30 + name_length + extra_length
    data[start + info.compress_size // 2] ^= 0xFF
    target.write_bytes(bytes(data))
    return target


def mark_encrypted(source: Path, name: str, target: Path) -> Path:
    """Set the encryption flag of one member in the central directory."""
    data = bytearray(source.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    entries, _size, position = struct.unpack("<HII", data[end + 10 : end + 20])
    for _ in range(entries):
        name_length, extra_length, comment_length = struct.unpack(
            "<HHH", data[position + 28 : position + 34]
        )
        member = bytes(data[position + 46 : position + 46 + name_length]).decode("utf-8")
        if member == name:
            flags = struct.unpack("<H", data[position + 8 : position + 10])[0] | 0x1
            data[position + 8 : position + 10] = struct.pack("<H", flags)
        position += 46 + name_length + extra_length + comment_length
    target.write_bytes(bytes(data))
    return target


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def asset_rows(root: Path, limits: ArchiveLimits = ArchiveLimits()) -> list[tuple[str, str]]:
    return [(asset.provenance_path, asset.sha256) for asset in discover_export(root, limits)]


def register(store: Path, source: Path, label: str = "S1") -> dict[str, object]:
    return register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at="2030-01-01T00:00:00+00:00",
        export_downloaded_at="2030-01-01T01:00:00+00:00",
        export_observed_at="2030-01-01T02:00:00+00:00",
        confirm_complete=True,
    )


def run_cli(*arguments: str) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = runner.main(list(arguments))
    return exit_code, stdout.getvalue() + stderr.getvalue()


def snapshot_register_arguments(store: Path, source: Path) -> list[str]:
    return [
        "snapshot",
        "register",
        "--store",
        str(store),
        "--input",
        str(source),
        "--label",
        "S1",
        "--requested-at",
        "2030-01-01T00:00:00+00:00",
        "--downloaded-at",
        "2030-01-01T01:00:00+00:00",
        "--observed-at",
        "2030-01-01T02:00:00+00:00",
        "--confirm-complete",
    ]


class ZipInputFormsTest(unittest.TestCase):
    """The same Export gives the same results in each form."""

    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.folder = write_export(self.root / "export")
        self.forms = {
            "ZIP file": zip_export(self.folder, self.root / "export.zip"),
            "ZIP file with one folder around the Export": zip_export(
                self.folder, self.root / "wrapped.zip", wrapper=WRAPPER
            ),
            "ZIP file with two folders around the Export": zip_export(
                self.folder, self.root / "wrapped-twice.zip", wrapper=f"Synthetic Outer/{WRAPPER}"
            ),
            "ZIP file without folder entries, upper-case name": zip_export(
                self.folder, self.root / "plain.ZIP", folder_entries=False
            ),
            "folder with one folder around the Export": wrap_folder(
                self.folder, self.root / "wrapped-folder"
            ),
            "folder with two folders around the Export": wrap_folder(
                self.folder, self.root / "wrapped-twice-folder", ("Synthetic Outer", WRAPPER)
            ),
            "folder whose name ends in .zip": Path(
                shutil.copytree(self.folder, self.root / "folder.zip")
            ),
        }

    def tearDown(self) -> None:
        self._directory.cleanup()

    def test_assets_and_provenance_are_the_same(self) -> None:
        expected = asset_rows(self.folder)
        paths = [path for path, _digest in expected]
        self.assertIn(ACTIVITIES_PATH, paths)
        self.assertIn(
            "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part1.zip"
            "!synthetic-session-1.fit",
            paths,
        )
        self.assertIn(
            "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part2.zip"
            "!synthetic-session-2.fit",
            paths,
        )
        # A ZIP file inside a ZIP file inside the Export is not read.
        self.assertFalse(any("deeper" in path for path in paths))
        for name, form in self.forms.items():
            with self.subTest(form=name):
                self.assertEqual(asset_rows(form), expected)

    def test_run_all_output_is_byte_identical(self) -> None:
        expected_result = run_all(self.folder, self.root / "output-folder")
        expected = tree_hashes(self.root / "output-folder")
        sessions = json.loads(
            (self.root / "output-folder/normalized/fit_sessions.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(sessions), 3)
        for index, (name, form) in enumerate(self.forms.items()):
            with self.subTest(form=name):
                before = tree_hashes(form) if form.is_dir() else form.read_bytes()
                output = self.root / f"output-{index}"
                result = run_all(form, output)
                self.assertEqual(result["status"], expected_result["status"])
                self.assertEqual(tree_hashes(output), expected)
                self.assertEqual(tree_hashes(form) if form.is_dir() else form.read_bytes(), before)

    def test_cli_runs_accept_the_zip_file(self) -> None:
        exit_code, console = run_cli(
            "run-all", "--input", str(self.forms["ZIP file"]), "--output", str(self.root / "cli-zip")
        )
        self.assertEqual(exit_code, 0, console)
        self.assertNotIn(str(self.root), console)
        run_all(self.folder, self.root / "cli-folder")
        self.assertEqual(tree_hashes(self.root / "cli-zip"), tree_hashes(self.root / "cli-folder"))
        exit_code, console = run_cli(
            "normalize-activities",
            "--input",
            str(self.forms["ZIP file"]),
            "--output",
            str(self.root / "activities-zip"),
        )
        self.assertEqual(exit_code, 0, console)
        run_cli(
            "normalize-activities",
            "--input",
            str(self.folder),
            "--output",
            str(self.root / "activities-folder"),
        )
        self.assertEqual(
            tree_hashes(self.root / "activities-zip"),
            tree_hashes(self.root / "activities-folder"),
        )

    def test_doctor_reports_the_same(self) -> None:
        expected = doctor_input(self.folder)
        self.assertEqual(
            [item["code"] for item in expected["findings"]], ["RUN_ALL_NOT_EVALUATED"]
        )
        for name, form in self.forms.items():
            with self.subTest(form=name):
                self.assertEqual(doctor_input(form), expected)

    def test_snapshot_registration_gives_the_same_content_identity(self) -> None:
        folder_store = self.root / "folder-store"
        initialize_store(folder_store, "synthetic-account-boundary")
        register(folder_store, self.folder)
        [expected] = load_manifests(folder_store)
        self.assertEqual(expected["archive_member_count"], 4)
        for index, (name, form) in enumerate(self.forms.items()):
            with self.subTest(form=name):
                store = self.root / f"store-{index}"
                initialize_store(store, "synthetic-account-boundary")
                register(store, form)
                [manifest] = load_manifests(store)
                for field in ("snapshot_id", "snapshot_content_id", "objects", "total_bytes"):
                    self.assertEqual(manifest[field], expected[field], field)
                self.assertEqual(verify_store(store)["status"], "PASS")
                # The same Export registered again in another form is the same Snapshot.
                again = register(folder_store, form)
                self.assertTrue(again["registration_was_idempotent"])
        # A Snapshot run reads the same input from either store.
        folder_build = build_approved_input(folder_store, self.root / "build-folder")
        zip_build = build_approved_input(self.root / "store-0", self.root / "build-zip")
        for field in ("canonical_build_sha256", "approved_input_content_sha256"):
            self.assertEqual(zip_build[field], folder_build[field], field)

    def test_snapshot_registration_streams_the_files_of_the_zip_file(self) -> None:
        store = self.root / "store"
        initialize_store(store, "synthetic-account-boundary")
        whole: list[str] = []
        original = ExportSource._read_member

        def record_whole_read(export: ExportSource, info: zipfile.ZipInfo, max_bytes: int) -> bytes:
            whole.append(info.filename)
            return original(export, info, max_bytes)

        with mock.patch.object(ExportSource, "_read_member", record_whole_read):
            register(store, self.forms["ZIP file"])
        # Only the ZIP files inside the Export are read whole, to open them;
        # every other file is copied to the store in parts.
        self.assertEqual(
            sorted(whole),
            [
                "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part1.zip",
                "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part2.zip",
            ],
        )
        self.assertEqual(verify_store(store)["status"], "PASS")


class ZipInputLayoutTest(unittest.TestCase):
    def test_a_layout_folder_at_the_top_is_kept_in_the_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "export"
            fitness = folder / "di_connect" / "DI-Connect-Fitness"
            fitness.mkdir(parents=True)
            shutil.copyfile(ACTIVITIES, fitness / "synthetic_summarizedActivities.json")
            expected = ["di_connect/DI-Connect-Fitness/synthetic_summarizedActivities.json"]
            self.assertEqual([path for path, _digest in asset_rows(folder)], expected)
            archive = zip_export(folder, root / "export.zip")
            self.assertEqual([path for path, _digest in asset_rows(archive)], expected)
            synthetic = ROOT / "examples/synthetic/garmin_export"
            self.assertEqual(
                [path for path, _digest in asset_rows(synthetic)],
                ["DI-Connect-Fitness/synthetic_summarizedActivities.json"],
            )

    def test_input_that_is_neither_a_folder_nor_a_zip_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notes = root / "notes.txt"
            notes.write_text("synthetic\n", encoding="utf-8")
            with self.assertRaises(RunAllError) as raised:
                run_all(notes, root / "output")
            self.assertEqual(raised.exception.code, "INPUT_NOT_DIRECTORY")
            exit_code, console = run_cli("run-all", "--input", str(notes), "--output", str(root / "o"))
            self.assertEqual(exit_code, 2)
            self.assertIn(
                "ERROR [INPUT_NOT_DIRECTORY]: input must be an existing folder or ZIP file", console
            )
            report = doctor_input(notes)
            self.assertEqual([item["code"] for item in report["findings"]], ["INPUT_DIRECTORY_INVALID"])
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            with self.assertRaisesRegex(SnapshotLifecycleError, "existing folder or ZIP file"):
                register(store, notes)
            self.assertFalse((root / "output").exists())

    def test_a_link_to_a_zip_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = zip_export(write_export(root / "export"), root / "export.zip")
            link = root / "link.zip"
            try:
                link.symlink_to(archive)
            except OSError:
                self.skipTest("symbolic links are not available")
            with self.assertRaises(RunAllError) as raised:
                run_all(link, root / "output")
            self.assertEqual(raised.exception.code, "INPUT_SYMLINK")
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            with self.assertRaisesRegex(SnapshotLifecycleError, "symbolic link"):
                register(store, link)


class DamagedZipTest(unittest.TestCase):
    def damaged_exports(self, root: Path) -> dict[str, Path]:
        """Return Export ZIP files damaged in the ways that a download can be."""
        valid = zip_export(write_export(root / "export"), root / "valid.zip")
        not_zip = root / "not-a-zip.zip"
        not_zip.write_bytes(b"synthetic, not a ZIP file\n")
        truncated = root / "truncated.zip"
        truncated.write_bytes(valid.read_bytes()[: valid.stat().st_size // 2])
        stored = root / "stored.zip"
        with zipfile.ZipFile(stored, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr(ACTIVITIES_PATH, ACTIVITIES.read_bytes())
        return {
            "not a ZIP file": not_zip,
            "ends early": truncated,
            "stored member fails its CRC check": flip_member_byte(
                stored, ACTIVITIES_PATH, root / "crc.zip"
            ),
            "compressed member is damaged": flip_member_byte(
                valid, ACTIVITIES_PATH, root / "deflate.zip"
            ),
        }

    def test_every_command_stops_with_input_zip_corrupt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (name, damaged) in enumerate(self.damaged_exports(root).items()):
                with self.subTest(damage=name):
                    with self.assertRaises(CorruptArchiveError):
                        discover_export(damaged)
                    output = root / f"output-{index}"
                    with self.assertRaises(RunAllError) as raised:
                        run_all(damaged, output)
                    self.assertEqual(raised.exception.code, "INPUT_ZIP_CORRUPT")
                    self.assertFalse(output.exists())
                    exit_code, console = run_cli(
                        "run-all", "--input", str(damaged), "--output", str(output)
                    )
                    self.assertEqual(exit_code, 2)
                    self.assertIn(
                        "ERROR [INPUT_ZIP_CORRUPT]: the Export ZIP file is damaged or incomplete",
                        console,
                    )
                    self.assertNotIn(str(root), console)
                    report = doctor_input(damaged)
                    self.assertEqual(
                        [
                            (item["code"], item["safe_message_id"], item["next_action_id"])
                            for item in report["findings"]
                        ],
                        [("INPUT_ZIP_CORRUPT", "INPUT_ZIP_DAMAGED_OR_INCOMPLETE", "DOWNLOAD_EXPORT_AGAIN")],
                    )
                    exit_code, console = run_cli(
                        "normalize-activities", "--input", str(damaged), "--output", str(output)
                    )
                    self.assertEqual(exit_code, 2)
                    self.assertIn("ERROR [INPUT_ZIP_CORRUPT]", console)
                    store = root / f"store-{index}"
                    initialize_store(store, "synthetic-account-boundary")
                    exit_code, console = run_cli(*snapshot_register_arguments(store, damaged))
                    self.assertEqual(exit_code, 2)
                    self.assertIn("ERROR [INPUT_ZIP_CORRUPT]", console)
                    self.assertEqual(load_manifests(store), [])
                    self.assertEqual(verify_store(store)["status"], "PASS")
                    self.assertFalse(output.exists())

    def test_a_damaged_zip_file_inside_the_export_still_stops_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            (folder / "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part3.zip").write_bytes(
                b"synthetic, not a ZIP file\n"
            )
            archive = zip_export(folder, root / "export.zip")
            for form in (folder, archive):
                with self.subTest(form=form.name):
                    with self.assertRaises(RunAllError) as raised:
                        run_all(form, root / "output")
                    self.assertEqual(raised.exception.code, "INPUT_DISCOVERY_FAILED")


class UnsafeZipTest(unittest.TestCase):
    def unsafe_exports(self, root: Path) -> dict[str, Path]:
        folder = write_export(root / "export")
        valid = zip_export(folder, root / "valid.zip")
        cases = {}
        outside = root / "outside.zip"
        shutil.copyfile(valid, outside)
        with zipfile.ZipFile(outside, "a") as archive:
            archive.writestr("../synthetic-escape.json", "{}")
        cases["path outside the folder"] = outside
        link = root / "link.zip"
        shutil.copyfile(valid, link)
        with zipfile.ZipFile(link, "a") as archive:
            info = zipfile.ZipInfo("DI_CONNECT/synthetic-link.json")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "synthetic_summarizedActivities.json")
        cases["link"] = link
        cases["encrypted member"] = mark_encrypted(valid, ACTIVITIES_PATH, root / "encrypted.zip")
        nested = root / "nested-unsafe"
        shutil.copytree(folder, nested)
        with zipfile.ZipFile(
            nested / "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part1.zip", "a"
        ) as archive:
            archive.writestr("../synthetic-escape.fit", b"synthetic")
        cases["path outside the folder in a ZIP file inside the Export"] = zip_export(
            nested, root / "nested-unsafe.zip"
        )
        return cases

    def test_unsafe_members_stop_every_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (name, unsafe) in enumerate(self.unsafe_exports(root).items()):
                with self.subTest(case=name):
                    with self.assertRaises(RunAllError) as raised:
                        run_all(unsafe, root / "output")
                    self.assertEqual(raised.exception.code, "INPUT_DISCOVERY_FAILED")
                    self.assertFalse((root / "output").exists())
                    report = doctor_input(unsafe)
                    self.assertEqual(
                        [item["code"] for item in report["findings"]], ["INPUT_DISCOVERY_FAILED"]
                    )
                    store = root / f"store-{index}"
                    initialize_store(store, "synthetic-account-boundary")
                    with self.assertRaisesRegex(SnapshotLifecycleError, "safe archive validation"):
                        register(store, unsafe)
                    self.assertEqual(load_manifests(store), [])


class ZipLimitsTest(unittest.TestCase):
    def test_limits_apply_only_to_members_that_are_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            uploaded = folder / "DI_CONNECT/DI-Connect-Uploaded-Files"
            large = bytes(range(256)) * 64
            (folder / "synthetic-video.mp4").write_bytes(large)
            with zipfile.ZipFile(
                uploaded / "UploadedFiles_synthetic_Part3.zip", "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr("synthetic-video.mp4", large)
                archive.writestr("synthetic-spaces.txt", b" " * 100_000)
                for number in range(3):
                    archive.writestr(f"synthetic-notes-{number}.txt", b"synthetic\n")
            archive = zip_export(folder, root / "export.zip")
            limits = ArchiveLimits(max_member_bytes=8192, max_members=3)
            for form in (folder, archive):
                with self.subTest(form=form.name):
                    self.assertEqual(asset_rows(form, limits), asset_rows(form))

    def test_members_that_are_read_are_limited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            fitness = folder / "DI_CONNECT/DI-Connect-Fitness"
            (fitness / "synthetic_spaces.json").write_bytes(b"[" + b" " * 100_000 + b"]")
            archive = zip_export(folder, root / "export.zip")
            with self.assertRaisesRegex(UnsafeArchiveError, "size limit"):
                discover_export(archive, ArchiveLimits(max_member_bytes=8192))
            with self.assertRaisesRegex(ValueError, "size limit"):
                discover_export(folder, ArchiveLimits(max_member_bytes=8192))
            with self.assertRaisesRegex(UnsafeArchiveError, "compression ratio"):
                discover_export(archive)
            nested = root / "nested"
            shutil.copytree(folder, nested)
            (nested / "DI_CONNECT/DI-Connect-Fitness/synthetic_spaces.json").unlink()
            with zipfile.ZipFile(
                nested / "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part3.zip", "w"
            ) as inner:
                for number in range(3):
                    inner.writestr(f"synthetic-{number}.fit", synthetic_fit())
            for form in (nested, zip_export(nested, root / "nested.zip")):
                with self.subTest(form=form.name):
                    with self.assertRaisesRegex(UnsafeArchiveError, "member count"):
                        discover_export(form, ArchiveLimits(max_members=2))

    def test_whole_export_zip_limits_stop_with_input_too_large(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            archive = zip_export(folder, root / "export.zip")
            count = len(asset_rows(folder))
            for limits in (
                ArchiveLimits(max_export_read_files=count - 1),
                ArchiveLimits(max_export_read_bytes=1024),
            ):
                with self.subTest(limits=limits):
                    with self.assertRaises(ExportTooLargeError):
                        discover_export(archive, limits)
                    # An extracted folder has no limit for the whole Export.
                    self.assertEqual(asset_rows(folder, limits), asset_rows(folder))
            small = ArchiveLimits(max_export_read_files=1)
            with mock.patch(
                "garmin_running_data_normalizer.run_all.discover_export",
                side_effect=lambda path: discover_export(path, small),
            ):
                with self.assertRaises(RunAllError) as raised:
                    run_all(archive, root / "output")
                self.assertEqual(raised.exception.code, "INPUT_TOO_LARGE")
                exit_code, console = run_cli(
                    "run-all", "--input", str(archive), "--output", str(root / "output")
                )
            self.assertEqual(exit_code, 2)
            self.assertIn(
                "ERROR [INPUT_TOO_LARGE]: the Export ZIP file is too large to read directly; "
                "extract it and use the folder",
                console,
            )
            self.assertFalse((root / "output").exists())
            with mock.patch(
                "garmin_running_data_normalizer.diagnostics.doctor.discover_export",
                side_effect=lambda path: discover_export(path, small),
            ):
                report = doctor_input(archive)
            self.assertEqual(
                [
                    (item["code"], item["safe_message_id"], item["next_action_id"])
                    for item in report["findings"]
                ],
                [
                    (
                        "INPUT_TOO_LARGE",
                        "INPUT_ZIP_TOO_LARGE_TO_READ_DIRECTLY",
                        "EXTRACT_EXPORT_AND_SELECT_FOLDER",
                    )
                ],
            )
            store = root / "store"
            initialize_store(store, "synthetic-account-boundary")
            with mock.patch(
                "garmin_running_data_normalizer.snapshot.store.ExportSource",
                side_effect=lambda path: ExportSource(path, small),
            ):
                exit_code, console = run_cli(*snapshot_register_arguments(store, archive))
            self.assertEqual(exit_code, 2)
            self.assertIn("ERROR [INPUT_TOO_LARGE]", console)
            self.assertEqual(load_manifests(store), [])


class NestedZipCopyTest(unittest.TestCase):
    """A large ZIP file inside an Export ZIP file is read from a private temporary copy."""

    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.folder = write_export(self.root / "export")
        self.archive = zip_export(self.folder, self.root / "export.zip")
        self.temporary = self.root / "temporary"
        self.temporary.mkdir()
        self.copy_limits = ArchiveLimits(max_nested_in_memory_bytes=1)

    def tearDown(self) -> None:
        self._directory.cleanup()

    def test_copy_is_private_and_removed(self) -> None:
        folders: list[tuple[str, int]] = []
        original = shutil.copyfileobj

        def record_copy(source: object, target: object, length: int = 0) -> None:
            folder = Path(target.name).parent  # type: ignore[attr-defined]
            folders.append((folder.name, stat.S_IMODE(folder.stat().st_mode)))
            original(source, target, length)  # type: ignore[arg-type]

        expected = asset_rows(self.archive)
        with mock.patch.object(tempfile, "tempdir", str(self.temporary)), mock.patch.object(
            source_module.shutil, "copyfileobj", record_copy
        ):
            self.assertEqual(asset_rows(self.archive, self.copy_limits), expected)
        self.assertEqual(len(folders), 2)
        self.assertTrue(all(name.startswith("garmin-export-zip-") for name, _mode in folders))
        if os.name == "posix":
            self.assertTrue(all(mode == 0o700 for _name, mode in folders))
        self.assertEqual(list(self.temporary.iterdir()), [])

    def test_copy_is_removed_after_a_failure_or_a_cancellation(self) -> None:
        damaged = self.root / "damaged"
        shutil.copytree(self.folder, damaged)
        (damaged / "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part3.zip").write_bytes(
            b"synthetic, not a ZIP file\n"
        )
        damaged_archive = zip_export(damaged, self.root / "damaged.zip")
        with mock.patch.object(tempfile, "tempdir", str(self.temporary)):
            with self.assertRaises(zipfile.BadZipFile):
                discover_export(damaged_archive, self.copy_limits)
            self.assertEqual(list(self.temporary.iterdir()), [])
            with mock.patch(
                "garmin_running_data_normalizer.intake.discovery.read_member",
                side_effect=KeyboardInterrupt,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    discover_export(self.archive, self.copy_limits)
            self.assertEqual(list(self.temporary.iterdir()), [])

    def test_snapshot_registration_reads_large_nested_zip_files_from_a_copy(self) -> None:
        folder_store = self.root / "folder-store"
        initialize_store(folder_store, "synthetic-account-boundary")
        register(folder_store, self.folder)
        store = self.root / "store"
        initialize_store(store, "synthetic-account-boundary")
        with mock.patch.object(tempfile, "tempdir", str(self.temporary)), mock.patch(
            "garmin_running_data_normalizer.snapshot.store.ExportSource",
            side_effect=lambda path: ExportSource(path, self.copy_limits),
        ):
            register(store, self.archive)
        self.assertEqual(list(self.temporary.iterdir()), [])
        self.assertEqual(
            load_manifests(store)[0]["snapshot_content_id"],
            load_manifests(folder_store)[0]["snapshot_content_id"],
        )

    def test_zip_file_changed_during_registration_stops_it(self) -> None:
        store = self.root / "store"
        initialize_store(store, "synthetic-account-boundary")
        original = ExportSource.open_stream
        changed: list[bool] = []

        def touch_after_first_read(export: ExportSource, item: object):  # type: ignore[no-untyped-def]
            if not changed:
                changed.append(True)
                status = self.archive.stat()
                os.utime(self.archive, ns=(status.st_atime_ns, status.st_mtime_ns + 1_000_000_000))
            return original(export, item)  # type: ignore[arg-type]

        with mock.patch.object(ExportSource, "open_stream", touch_after_first_read):
            with self.assertRaisesRegex(SnapshotLifecycleError, "changed during completeness scan"):
                register(store, self.archive)
        self.assertEqual(load_manifests(store), [])


if __name__ == "__main__":
    unittest.main()
