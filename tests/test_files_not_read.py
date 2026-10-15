"""Files that a run does not read are listed with the reason (stage A4b).

A file of a form that no dataset reads, in the Export or in one of its ZIP
files, is listed in ``run_manifest.json`` as ``format_not_read``, and a ZIP
file inside a ZIP file of the Export as ``zip_in_zip``; ``START_HERE.md``
counts them, and the status does not change. A Snapshot run lists the same
files by Snapshot number, and it does not read a ZIP file inside a ZIP file
either: until stage A4b, the build wrote one where the run read it as a ZIP
file of the Export.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_input
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.run_all import RunAllError, run_all
from garmin_running_data_normalizer.snapshot import (
    build_approved_input,
    initialize_store,
    lifecycle,
    run_snapshot_all,
)
from tests.fit_fixture_factory import synthetic_fit
from tests.test_snapshot_lifecycle import _activity
from tests.test_snapshot_parity import differences, runs, zip_bytes
from tests.test_snapshot_record_updates import ACCOUNT, load
from tests.test_snapshot_record_updates import write_export as minimal_export
from tests.test_snapshot_unreadable_files import (
    SMALL,
    listed,
    one_snapshot,
    register,
    small_limits,
    without_snapshot,
)
from tests.test_unreadable_files import export, padding, write
from tests.test_zip_input import SYNTHETIC_NOT_READ, run_cli, write_export, zip_export

LINE = "`run_manifest.json` lists them with the reason"


def reasons(output: Path) -> list[tuple[str, str]]:
    return [(item["source_path"], item["reason"]) for item in listed(output, "files_not_read")]


def sizes(folder: Path, files: list[tuple[str, str]]) -> dict[str, int]:
    """The sizes of these files of an Export folder; a member of a ZIP file
    by the ZIP file."""
    found: dict[str, int] = {}
    for path, _reason in files:
        if "!" in path:
            container, member = path.split("!", 1)
            with zipfile.ZipFile(folder / container) as archive:
                found[path] = archive.getinfo(member).file_size
        else:
            found[path] = (folder / path).stat().st_size
    return found


def normalized_text(output: Path) -> str:
    return "".join(
        path.read_text(encoding="utf-8") for path in sorted((output / "normalized").glob("*.json"))
    )


class OneShotRunTest(unittest.TestCase):
    def test_files_of_a_form_not_read_are_listed_with_the_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = write_export(root / "plain")
            folder = write_export(root / "export")
            # Files of forms that a Garmin Export may also hold.
            uploaded = folder / "DI_CONNECT/DI-Connect-Uploaded-Files"
            write(uploaded / "synthetic-track.tcx", b"<synthetic/>")
            write(uploaded / "synthetic-track.gpx", b"<synthetic/>")
            write(folder / "DI_CONNECT/DI-Connect-Wellness/synthetic.csv", b"synthetic\n")
            expected = sorted(
                [
                    *SYNTHETIC_NOT_READ,
                    ("DI_CONNECT/DI-Connect-Uploaded-Files/synthetic-track.gpx", "format_not_read"),
                    ("DI_CONNECT/DI-Connect-Uploaded-Files/synthetic-track.tcx", "format_not_read"),
                    ("DI_CONNECT/DI-Connect-Wellness/synthetic.csv", "format_not_read"),
                ]
            )
            run_all(plain, root / "plain-output")
            plain_summary = load(root / "plain-output/run_summary.json")
            for form in (folder, zip_export(folder, root / "export.zip")):
                with self.subTest(form=form.name):
                    output = root / f"output-{form.name}"
                    run_all(form, output)
                    self.assertEqual(reasons(output), expected)
                    self.assertEqual(
                        {item["source_path"]: item["bytes"] for item in listed(output, "files_not_read")},
                        sizes(folder, expected),
                    )
                    # The operating-system metadata files are not Export files.
                    self.assertFalse(
                        [path for path, _reason in reasons(output) if ".DS_Store" in path or "__MACOSX" in path]
                    )
                    self.assertIn(
                        f"- Files not read: {len(expected)}; {LINE}",
                        (output / "START_HERE.md").read_text(encoding="utf-8"),
                    )
                    # They change nothing else: no warning, and the status of
                    # the Export without them.
                    summary = load(output / "run_summary.json")
                    self.assertEqual(
                        (summary["status"], summary["warnings"]),
                        (plain_summary["status"], plain_summary["warnings"]),
                    )
                    # The ZIP file inside a ZIP file holds an Activities file,
                    # which is not read.
                    self.assertNotIn("synthetic-deeper", normalized_text(output))

    def test_an_input_without_the_layout_folders_is_read_whole(self) -> None:
        # Without a root, the whole input is the Export: its files of another
        # form are listed, as the files of an Export (stage A3a).
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input"
            write(
                source / "synthetic_summarizedActivities.json",
                json.dumps([{"summarizedActivitiesExport": [_activity("1001")]}]).encode(),
            )
            write(source / "synthetic-notes.pdf", b"synthetic")
            write(source / "photos/synthetic.jpg", b"synthetic")
            output = root / "output"
            run_all(source, output)
            self.assertEqual(
                reasons(output),
                [("photos/synthetic.jpg", "format_not_read"), ("synthetic-notes.pdf", "format_not_read")],
            )

    def test_the_names_of_files_not_read_stay_in_the_local_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / "DI-Connect-Uploaded-Files/Private-not-read.tcx", b"<synthetic/>")
            write(
                source / "DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part1.zip",
                zip_bytes(
                    {
                        "Private-not-read-notes.txt": b"synthetic\n",
                        "Private-not-read-inner.zip": zip_bytes({"synthetic.json": b"[]"}),
                    }
                ),
            )
            output = root / "output"
            exit_code, console = run_cli(
                "run-all", "--input", str(source), "--output", str(output), "--external-safe-pack"
            )
            self.assertEqual(exit_code, 0)
            self.assertNotIn("Private-not-read", console)
            self.assertEqual(
                sorted(reason for path, reason in reasons(output) if "Private-not-read" in path),
                ["format_not_read", "format_not_read", "zip_in_zip"],
            )
            self.assertNotIn("Private-not-read", json.dumps(doctor_input(source)))
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, source)
            snapshot = root / "snapshot"
            exit_code, console = run_cli(
                "snapshot", "run-all", "--store", str(store), "--output", str(snapshot), "--external-safe-pack"
            )
            self.assertEqual(exit_code, 0)
            self.assertNotIn("Private-not-read", console)
            self.assertEqual(without_snapshot(listed(snapshot, "files_not_read")), without_snapshot(listed(output, "files_not_read")))
            for run in (output, snapshot):
                bundle = root / f"support-{run.name}.zip"
                build_support_bundle(run, bundle)
                for path in (bundle, run / "analysis/external_safe_handoff.zip"):
                    with self.subTest(run=run.name, file=path.name), zipfile.ZipFile(path) as archive:
                        content = b"".join(archive.read(name) for name in archive.namelist())
                        self.assertNotIn(b"Private-not-read", content)


class SnapshotRunTest(unittest.TestCase):
    def test_a_snapshot_run_gives_what_a_one_shot_run_gives(self) -> None:
        # The ZIP file inside a ZIP file holds the Activities file again: a
        # Snapshot run read it until stage A4b, and its relationships failed.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            for form in (folder, zip_export(folder, root / "export.zip")):
                with self.subTest(form=form.name):
                    one_shot, snapshot = runs(root / f"runs-{form.name}", form)
                    self.assertEqual(differences(one_shot, snapshot), [])
                    self.assertEqual(
                        without_snapshot(listed(snapshot, "files_not_read")),
                        without_snapshot(listed(one_shot, "files_not_read")),
                    )
                    self.assertEqual({item["snapshot"] for item in listed(snapshot, "files_not_read")}, {1})

    def test_a_zip_file_inside_a_zip_file_is_read_by_neither_run(self) -> None:
        # A UDS file inside one stopped a Snapshot run from stage A3d-4a: the
        # build found no UDS file, and the run read UDS records.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = minimal_export(root, "export", [_activity("1001")])
            inner = zip_bytes(
                {"UDSFile_1.json": json.dumps([{"calendarDate": "2030-02-01", "totalSteps": 5}]).encode()}
            )
            write(
                source / "DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip",
                zip_bytes({"synthetic.fit": synthetic_fit(), "UDSFile_parts.zip": inner}),
            )
            one_shot, snapshot = runs(root / "runs", source)
            self.assertEqual(differences(one_shot, snapshot), [])
            for output in (one_shot, snapshot):
                with self.subTest(run=output.name):
                    self.assertEqual(load(output / "normalized/uds_daily.json"), [])
                    self.assertIn(
                        ("DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip!UDSFile_parts.zip", "zip_in_zip"),
                        reasons(output),
                    )

    def test_files_are_listed_by_snapshot_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = export(root, "first")
            second = export(root, "second")
            write(second / "DI-Connect-Uploaded-Files/synthetic-track.gpx", b"<synthetic/>")
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, first, "S1", 1)
            register(store, second, "S2", 2)
            output = root / "output"
            run_snapshot_all(store, output)
            self.assertEqual(
                [
                    (item["snapshot"], item["source_path"], item["reason"])
                    for item in listed(output, "files_not_read")
                ],
                [
                    (1, "preserved-unknown.txt", "format_not_read"),
                    (2, "DI-Connect-Uploaded-Files/synthetic-track.gpx", "format_not_read"),
                    (2, "preserved-unknown.txt", "format_not_read"),
                ],
            )
            self.assertIn(
                f"- Files not read: 3; {LINE}", (output / "START_HERE.md").read_text(encoding="utf-8")
            )

    def test_members_over_the_limit_of_a_form_not_read(self) -> None:
        # Registration does not list a member over the limit for one file;
        # the build finds it in the stored ZIP file (stage A3c-2), and lists
        # one of a form not read as a run does.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(
                source / "DI-Connect-Uploaded-Files/UploadedFiles_big_Part1.zip",
                zip_bytes(
                    {
                        "synthetic-video.mp4": padding(SMALL + 1),
                        "synthetic-big.zip": padding(SMALL + 2),
                        "synthetic.fit": synthetic_fit(),
                    }
                ),
            )
            with small_limits():
                one_shot = root / "one-shot"
                run_all(source, one_shot)
                snapshot = one_snapshot(root, source)
            for output in (one_shot, snapshot):
                with self.subTest(run=output.name):
                    self.assertEqual(
                        [
                            (item["source_path"], item["bytes"], item["reason"])
                            for item in without_snapshot(listed(output, "files_not_read"))
                        ],
                        [
                            ("DI-Connect-Uploaded-Files/UploadedFiles_big_Part1.zip!synthetic-big.zip", SMALL + 2, "zip_in_zip"),
                            ("DI-Connect-Uploaded-Files/UploadedFiles_big_Part1.zip!synthetic-video.mp4", SMALL + 1, "format_not_read"),
                            ("preserved-unknown.txt", 10, "format_not_read"),
                        ],
                    )
                    self.assertEqual(len(load(output / "normalized/fit_sessions.json")), 1)

    def test_the_build_writes_a_zip_file_inside_a_zip_file_under_a_name_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = write_export(root / "export")
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, folder)
            build_approved_input(store, root / "build")
            with zipfile.ZipFile(folder / "DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_synthetic_Part2.zip") as archive:
                deeper = archive.read("synthetic-deeper.zip")
            preserved = root / "build/approved_input/preserved_unknown"
            self.assertEqual(
                (preserved / f"object_{hashlib.sha256(deeper).hexdigest()}.bin").read_bytes(), deeper
            )
            self.assertEqual([path.name for path in preserved.iterdir() if path.suffix == ".zip"], [])

    def test_a_zip_file_inside_a_zip_file_in_the_approved_input_stops_a_snapshot_run(self) -> None:
        # The build writes none: one there is a defect of the build, and the
        # run stops rather than read it. A file of a form not read, which
        # the build writes, does not stop it.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            initialize_store(store, ACCOUNT)
            register(store, export(root))
            build = lifecycle.build_approved_input

            def with_a_zip_file_inside(store_root: Any, build_root: Any, **options: Any) -> Any:
                built = build(store_root, build_root, **options)
                write(
                    Path(build_root) / "approved_input/DI-Connect-Uploaded-Files/Parts.zip",
                    zip_bytes({"inner.zip": zip_bytes({"synthetic.json": b"[]"})}),
                )
                return built

            with mock.patch.object(lifecycle, "build_approved_input", side_effect=with_a_zip_file_inside):
                with self.assertRaises(RunAllError) as raised:
                    run_snapshot_all(store, root / "output")
            self.assertEqual(raised.exception.code, "SNAPSHOT_CONTEXT_INVALID")


if __name__ == "__main__":
    unittest.main()
