"""Files that cannot be read are left out with a reason, and the run goes on (stage A3c)."""

from __future__ import annotations

import json
import random
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

# Import the diagnostics package before the standalone module: importing
# standalone first meets a circular import when this file runs on its own.
from garmin_running_data_normalizer.diagnostics import doctor_input, doctor_run_output
from garmin_running_data_normalizer.diagnostics.support_bundle import build_support_bundle
from garmin_running_data_normalizer.intake.archive import ArchiveLimits
from garmin_running_data_normalizer.intake.discovery import read_export
from garmin_running_data_normalizer.normalizers.activities import normalize_activities
from garmin_running_data_normalizer.normalizers.gear import normalize_gear
from garmin_running_data_normalizer.run_all import (
    ACTIVITIES_NOT_READABLE_MESSAGE,
    RunAllError,
    run_all,
)
from garmin_running_data_normalizer.runner import GoldenPathError, run_activities
from tests.fit_fixture_factory import synthetic_fit
from tests.test_snapshot_lifecycle import _activity, _write_remaining_daily_metrics
from tests.test_snapshot_record_updates import gear, load, personal_record, write_export
from tests.test_zip_input import flip_member_byte, mark_encrypted, run_cli, zip_export

NOT_ZIP = b"synthetic, not a ZIP file\n"
NOT_JSON = b"{synthetic, not JSON"
BOM = b"\xef\xbb\xbf"
UPLOADED = "DI-Connect-Uploaded-Files"
# A limit for one file that synthetic files can exceed.
SMALL = ArchiveLimits(max_member_bytes=64 * 1024)
LEFT_OUT_MESSAGE = (
    "one or more files could not be read and were left out; "
    "run_manifest.json lists them with the reason"
)


def export(root: Path, name: str = "export") -> Path:
    """Write an Export with two Activities, Gear and a link, a Personal Record, and daily metrics."""
    source = write_export(
        root,
        name,
        [_activity("A1"), _activity("A2")],
        gear_rows=[gear(1, "Synthetic Shoe")],
        links={"1": ["A1"]},
        records=[personal_record(1, "A1", 1.0)],
    )
    _write_remaining_daily_metrics(source, 1)
    return source


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def zip_with(path: Path, members: dict[str | zipfile.ZipInfo, bytes], compression: int = zipfile.ZIP_STORED) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return path


def padding(size: int) -> bytes:
    """Bytes that do not compress, so that a ZIP file holding them stays within the compression ratio."""
    return random.Random(size).randbytes(size)


def big_json(rows: list[dict[str, Any]]) -> bytes:
    """A JSON file of these rows, over the small limit for one file."""
    return json.dumps([*rows, {"syntheticPadding": padding(48 * 1024).hex()}]).encode("utf-8")


def run(source: Path, output: Path, limits: ArchiveLimits | None = None, **options: Any) -> dict[str, Any]:
    if limits is None:
        return run_all(source, output, **options)
    with mock.patch(
        "garmin_running_data_normalizer.run_all.read_export",
        side_effect=lambda path: read_export(path, limits),
    ):
        return run_all(source, output, **options)


def check(source: Path, limits: ArchiveLimits | None = None) -> dict[str, Any]:
    if limits is None:
        return doctor_input(source)
    with mock.patch(
        "garmin_running_data_normalizer.diagnostics.doctor.read_export",
        side_effect=lambda path: read_export(path, limits),
    ):
        return doctor_input(source)


def findings(report: dict[str, Any]) -> list[tuple[str, str]]:
    return [(item["code"], item["severity"]) for item in report["findings"]]


def left_out(output: Path) -> list[tuple[str, str, str]]:
    manifest = load(output / "run_manifest.json")
    return [
        (item["source_path"], item["family"], item["reason"])
        for item in manifest.get("files_left_out", [])
    ]


def not_read(output: Path) -> list[tuple[str, str]]:
    manifest = load(output / "run_manifest.json")
    return [(item["source_path"], item["reason"]) for item in manifest.get("files_not_read", [])]


def record_counts(output: Path) -> dict[str, int]:
    summary = load(output / "run_summary.json")
    return {family: result["record_count"] for family, result in summary["family_results"].items()}


def rows(output: Path, dataset: str) -> int:
    return len(load(output / f"normalized/{dataset}.json"))


class LeftOutFilesTest(unittest.TestCase):
    def assert_left_out(self, output: Path, expected: list[tuple[str, str, str]]) -> None:
        """The run finished with these files left out, and says so in each place."""
        summary = load(output / "run_summary.json")
        self.assertEqual(summary["status"], "PARTIAL_SUCCESS")
        self.assertEqual(left_out(output), expected)
        self.assertEqual(
            [item for item in summary["warnings"] if item["code"] == "DATA_FILE_LEFT_OUT"],
            [{"code": "DATA_FILE_LEFT_OUT", "count": len(expected), "message": LEFT_OUT_MESSAGE}],
        )
        self.assertEqual(summary["input_warning_count"], 1)
        quality = load(output / "diagnostics/run_quality.json")
        self.assertIn({"code": "DATA_FILE_LEFT_OUT", "count": len(expected)}, quality["warnings"])
        self.assertIn(
            f"- Files left out: {len(expected)}, which could not be read; "
            "`run_manifest.json` lists them with the reason",
            (output / "START_HERE.md").read_text(encoding="utf-8"),
        )

    def test_json_files_that_cannot_be_read_are_left_out(self) -> None:
        # The four errors that leave a JSON file out.
        contents = {
            "not UTF-8": '[{"summarizedActivitiesExport": [{"activityId": "A9", "name": "Caf\xe9"}]}]'.encode("latin-1"),
            "not JSON": b'[{"summarizedActivitiesExport": [{"activityId": "A9"',
            "nested too deeply": b"[" * 100_000 + b"]" * 100_000,
            "a number with too many digits": b"[" + b"1" * 5_000 + b"]",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (name, content) in enumerate(contents.items()):
                with self.subTest(content=name):
                    source = export(root / f"case-{index}")
                    write(source / "DI-Connect-Fitness/other_summarizedActivities.json", content)
                    output = root / f"output-{index}"
                    run_all(source, output)
                    self.assert_left_out(
                        output,
                        [("DI-Connect-Fitness/other_summarizedActivities.json", "activities", "json_not_readable")],
                    )
                    # The other file of the same family is still read.
                    self.assertEqual(record_counts(output)["activities"], 2)

    def test_a_file_of_any_family_that_cannot_be_read_is_left_out(self) -> None:
        files = {
            "gear": "DI-Connect-Fitness/other_gear.json",
            "personal_records": "DI-Connect-Fitness/other_personalRecord.json",
            "hill_score": "DI-Connect-Metrics/HillScore_other.json",
            "sleep": "DI-Connect-Wellness/other_sleepData.json",
            "uds": "DI-Connect-Aggregator/UDSFile_other.json",
            "vo2max": "DI-Connect-Metrics/MetricsMaxMetData_other.json",
            "lactate_threshold": "DI-Connect-User/synthetic_userBiometrics.json",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_all(export(root, "plain"), root / "plain-output")
            expected = record_counts(root / "plain-output")
            for family, relative in files.items():
                with self.subTest(family=family):
                    source = export(root / family)
                    write(source / relative, NOT_JSON)
                    output = root / f"{family}-output"
                    run_all(source, output)
                    self.assert_left_out(output, [(relative, family, "json_not_readable")])
                    self.assertEqual(record_counts(output), expected)

    def test_zip_files_that_cannot_be_read_are_left_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = zip_with(root / "valid.zip", {"synthetic-session-1.fit": synthetic_fit()})
            contents = {
                "not a ZIP file": NOT_ZIP,
                "ends early": valid.read_bytes()[: valid.stat().st_size // 2],
                "a member is damaged": flip_member_byte(
                    valid, "synthetic-session-1.fit", root / "damaged.zip"
                ).read_bytes(),
            }
            relative = f"{UPLOADED}/UploadedFiles_synthetic_Part1.zip"
            for index, (name, content) in enumerate(contents.items()):
                folder = export(root / f"case-{index}")
                write(folder / relative, content)
                for form in (folder, zip_export(folder, root / f"case-{index}.zip")):
                    with self.subTest(case=name, form=form.name):
                        output = root / f"output-{index}-{form.name}"
                        run_all(form, output)
                        self.assert_left_out(output, [(relative, "unclassified", "zip_not_readable")])
                        self.assertEqual(record_counts(output)["activities"], 2)
                        self.assertEqual(
                            findings(check(form)),
                            [("DATA_FILE_LEFT_OUT", "WARNING"), ("RUN_ALL_NOT_EVALUATED", "INFO")],
                        )

    def test_a_zip_file_inside_the_export_with_an_unsafe_member_is_left_out(self) -> None:
        # Its members are read in memory and never written, so leaving it out
        # is safe; the same members in the Export ZIP file itself stop the run
        # (tests/test_zip_input.py).
        link = zipfile.ZipInfo("synthetic-link.fit")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            encrypted = mark_encrypted(
                zip_with(root / "plain.zip", {"synthetic-session-1.fit": synthetic_fit()}),
                "synthetic-session-1.fit",
                root / "encrypted.zip",
            )
            cases = {
                "a path outside the folder": zip_with(
                    root / "outside.zip", {"../synthetic-escape.fit": synthetic_fit()}
                ),
                "a link": zip_with(root / "link.zip", {link: b"synthetic-session-1.fit"}),
                "encryption": encrypted,
                "a compression ratio over the limit": zip_with(
                    root / "ratio.zip", {"synthetic-zeros.fit": b"\0" * 100_000}, zipfile.ZIP_DEFLATED
                ),
            }
            relative = f"{UPLOADED}/UploadedFiles_synthetic_Part1.zip"
            for index, (name, inner) in enumerate(cases.items()):
                folder = export(root / f"case-{index}")
                write(folder / relative, inner.read_bytes())
                for form in (folder, zip_export(folder, root / f"case-{index}.zip")):
                    with self.subTest(case=name, form=form.name):
                        output = root / f"output-{index}-{form.name}"
                        run_all(form, output)
                        self.assert_left_out(output, [(relative, "unclassified", "zip_unsafe_member")])
                        self.assertEqual(
                            findings(check(form)),
                            [("DATA_FILE_LEFT_OUT", "WARNING"), ("RUN_ALL_NOT_EVALUATED", "INFO")],
                        )

    def test_files_over_the_limits_are_left_out(self) -> None:
        limits = ArchiveLimits(max_member_bytes=SMALL.max_member_bytes, max_members=2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = export(root)
            write(folder / f"{UPLOADED}/synthetic_big.fit", synthetic_fit() + padding(70 * 1024))
            write(
                folder / "DI-Connect-Aggregator/UDSFile_big.json",
                big_json([{"calendarDate": "2030-02-02", "totalSteps": 2}]),
            )
            # JSON files that no dataset reads are not read instead: nothing
            # is left out of the datasets for them.
            write(folder / "DI-Connect-User/synthetic_big_user.json", big_json([]))
            zip_with(
                folder / f"{UPLOADED}/UploadedFiles_big_Part1.zip",
                {
                    "synthetic-session-1.fit": synthetic_fit(),
                    "synthetic-big.fit": synthetic_fit() + padding(70 * 1024),
                    "synthetic-big-notes.json": big_json([]),
                },
            )
            zip_with(
                folder / f"{UPLOADED}/UploadedFiles_many_Part2.zip",
                {f"synthetic-{number}.fit": synthetic_fit() for number in range(3)},
            )
            expected = [
                ("DI-Connect-Aggregator/UDSFile_big.json", "uds", "file_too_large"),
                (f"{UPLOADED}/UploadedFiles_big_Part1.zip!synthetic-big.fit", "fit", "file_too_large"),
                (f"{UPLOADED}/UploadedFiles_many_Part2.zip", "unclassified", "zip_too_large"),
                (f"{UPLOADED}/synthetic_big.fit", "fit", "file_too_large"),
            ]
            for form in (folder, zip_export(folder, root / "export.zip")):
                with self.subTest(form=form.name):
                    output = root / f"output-{form.name}"
                    run(form, output, limits)
                    self.assert_left_out(output, expected)
                    self.assertEqual(
                        not_read(output),
                        [
                            (f"{UPLOADED}/UploadedFiles_big_Part1.zip!synthetic-big-notes.json", "file_too_large"),
                            ("DI-Connect-User/synthetic_big_user.json", "file_too_large"),
                        ],
                    )
                    # The other member of the ZIP file is read.
                    self.assertEqual(rows(output, "fit_sessions"), 1)
                    self.assertEqual(
                        findings(check(form, limits)),
                        [("DATA_FILE_LEFT_OUT", "WARNING"), ("RUN_ALL_NOT_EVALUATED", "INFO")],
                    )

    def test_a_json_file_that_no_dataset_reads_over_the_limit_is_not_read(self) -> None:
        # It adds nothing to the datasets, so the status does not change, as
        # for the files outside the Export.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = export(root, "plain")
            run(plain, root / "plain-output", SMALL)
            source = export(root)
            write(source / "DI-Connect-User/synthetic_big_user.json", big_json([]))
            output = root / "output"
            run(source, output, SMALL)
            summary = load(output / "run_summary.json")
            self.assertEqual(summary["status"], load(root / "plain-output/run_summary.json")["status"])
            self.assertNotIn("DATA_FILE_LEFT_OUT", [item["code"] for item in summary["warnings"]])
            self.assertNotIn("input_warning_count", summary)
            manifest = load(output / "run_manifest.json")
            self.assertNotIn("files_left_out", manifest)
            self.assertEqual(
                manifest["files_not_read"],
                [
                    {
                        "source_path": "DI-Connect-User/synthetic_big_user.json",
                        "bytes": (source / "DI-Connect-User/synthetic_big_user.json").stat().st_size,
                        "reason": "file_too_large",
                    }
                ],
            )
            self.assertIn(
                "- Files not read: 1", (output / "START_HERE.md").read_text(encoding="utf-8")
            )
            self.assertEqual(findings(check(source, SMALL)), [("RUN_ALL_NOT_EVALUATED", "INFO")])

    def test_a_file_over_the_limit_is_compared_by_its_path_and_size(self) -> None:
        # Two copies of an Export are the same Export when such files have
        # the same paths and sizes, as the files of the kinds not read.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "parent"
            copies = (export(parent, "copy-a"), export(parent, "copy-b"))
            for copy in copies:
                write(copy / f"{UPLOADED}/synthetic_big.fit", synthetic_fit() + padding(70 * 1024))
                write(copy / "DI-Connect-User/synthetic_big_user.json", big_json([]))
            output = root / "same"
            run(parent, output, SMALL)
            codes = [item["code"] for item in load(output / "run_summary.json")["warnings"]]
            self.assertIn("INPUT_DUPLICATE_SOURCES", codes)
            self.assertEqual(left_out(output), [(f"{UPLOADED}/synthetic_big.fit", "fit", "file_too_large")])
            for relative, data in (
                (f"{UPLOADED}/synthetic_big.fit", synthetic_fit() + padding(70 * 1024 + 1)),
                ("DI-Connect-User/synthetic_big_user.json", big_json([]) + b" "),
            ):
                with self.subTest(file=relative):
                    original = (copies[1] / relative).read_bytes()
                    write(copies[1] / relative, data)
                    with self.assertRaises(RunAllError) as raised:
                        run(parent, root / "different", SMALL)
                    self.assertEqual(raised.exception.code, "INPUT_MULTIPLE_EXPORTS")
                    write(copies[1] / relative, original)

    def test_records_that_point_to_a_left_out_activity_do_not_stop_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            # The Activities file that held A1, which the Gear link and the
            # Personal Record point to, cannot be read.
            write(
                source / "DI-Connect-Fitness/synthetic_summarizedActivities.json",
                json.dumps([{"summarizedActivitiesExport": [_activity("A2")]}]).encode("utf-8"),
            )
            write(source / "DI-Connect-Fitness/other_summarizedActivities.json", NOT_JSON)
            write(source / f"{UPLOADED}/synthetic.fit", synthetic_fit())
            output = root / "output"
            exit_code, console = run_cli("run-all", "--input", str(source), "--output", str(output))
            self.assertEqual(exit_code, 3)
            self.assertIn("STATUS: PARTIAL_SUCCESS", console)
            self.assert_left_out(
                output,
                [("DI-Connect-Fitness/other_summarizedActivities.json", "activities", "json_not_readable")],
            )
            codes = {item["code"] for item in load(output / "run_summary.json")["warnings"]}
            self.assertIn("RELATIONSHIP_UNRESOLVED_VALID_LINK", codes)
            self.assertEqual((rows(output, "activities"), rows(output, "fit_sessions")), (1, 1))
            # The link and the record leave the tables, as in v1.7.1, until
            # stage A4 keeps them as unresolved.
            self.assertEqual((rows(output, "activity_gear"), rows(output, "personal_records")), (0, 0))
            # The Doctor reads the warning of a completed run.
            self.assertIn(
                ("DATA_FILE_LEFT_OUT", "WARNING"), findings(doctor_run_output(output))
            )

    def test_the_names_of_left_out_files_stay_in_the_local_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / f"{UPLOADED}/Private-left-out_Part1.zip", NOT_ZIP)
            write(source / "DI-Connect-Fitness/Private-left-out_summarizedActivities.json", NOT_JSON)
            output = root / "output"
            exit_code, console = run_cli(
                "run-all", "--input", str(source), "--output", str(output), "--external-safe-pack"
            )
            self.assertEqual(exit_code, 3)
            self.assertNotIn("Private-left-out", console)
            self.assertEqual(len(left_out(output)), 2)
            self.assertNotIn("Private-left-out", json.dumps(doctor_input(source)))
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            for path in (bundle, output / "analysis/external_safe_handoff.zip"):
                with self.subTest(file=path.name), zipfile.ZipFile(path) as archive:
                    content = b"".join(archive.read(name) for name in archive.namelist())
                    self.assertNotIn(b"Private-left-out", content)

    def test_a_byte_order_mark_is_accepted_everywhere(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = export(root, "plain")
            marked = export(root, "marked")
            for path in sorted(marked.rglob("*.json")):
                path.write_bytes(BOM + path.read_bytes())
            run_all(plain, root / "plain-output")
            run_all(marked, root / "marked-output")
            self.assertEqual(
                load(root / "marked-output/run_summary.json")["status"],
                load(root / "plain-output/run_summary.json")["status"],
            )
            self.assertEqual(left_out(root / "marked-output"), [])
            self.assertEqual(record_counts(root / "marked-output"), record_counts(root / "plain-output"))
            self.assertEqual(rows(root / "marked-output", "gear"), 1)


class NormalizationErrorsTest(unittest.TestCase):
    def test_an_error_after_a_file_is_read_stops_the_run(self) -> None:
        # Only the reading of a file is guarded. A ValueError raised while
        # a file that was read is normalized is a defect: the run stops, and
        # the file is not left out.
        cases = {
            "activities": (
                "garmin_running_data_normalizer.normalizers.activities._unwrap",
                lambda root, assets: normalize_activities(root, assets=assets),
                "ACTIVITIES_NORMALIZATION_FAILED",
            ),
            "gear": (
                "garmin_running_data_normalizer.normalizers.gear._containers",
                lambda root, assets: normalize_gear(root, assets=assets),
                "GEAR_NORMALIZATION_FAILED",
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            for family, (target, normalize, code) in cases.items():
                with self.subTest(family=family), mock.patch(
                    target, side_effect=ValueError("synthetic normalization error")
                ):
                    with read_export(source) as reading:
                        with self.assertRaisesRegex(ValueError, "synthetic normalization error"):
                            normalize(str(source), reading.assets)
                        self.assertEqual(reading.left_out, [])
                    output = root / f"output-{family}"
                    with self.assertRaises(RunAllError) as raised:
                        run_all(source, output)
                    self.assertEqual(raised.exception.code, code)
                    self.assertFalse(output.exists())


class NoActivitiesLeftTest(unittest.TestCase):
    def test_activities_files_that_all_cannot_be_read_stop_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / "DI-Connect-Fitness/synthetic_summarizedActivities.json", NOT_JSON)
            output = root / "output"
            with self.assertRaises(RunAllError) as raised:
                run_all(source, output)
            self.assertEqual(
                (raised.exception.code, raised.exception.safe_message),
                ("ACTIVITIES_EMPTY", ACTIVITIES_NOT_READABLE_MESSAGE),
            )
            self.assertFalse(output.exists())
            exit_code, console = run_cli("run-all", "--input", str(source), "--output", str(output))
            self.assertEqual(exit_code, 2)
            self.assertIn(
                "ERROR [ACTIVITIES_EMPTY]: the Activities files could not be read; "
                "obtain a complete, readable Export",
                console,
            )
            # The pre-run check does not parse JSON content, so only the run
            # can tell.
            self.assertEqual(findings(check(source)), [("RUN_ALL_NOT_EVALUATED", "INFO")])

    def test_activities_files_over_the_limit_are_reported_before_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / "DI-Connect-Fitness/synthetic_summarizedActivities.json", big_json([]))
            report = check(source, SMALL)
            self.assertEqual(
                [
                    (item["code"], item["severity"], item["safe_message_id"], item["next_action_id"])
                    for item in report["findings"]
                ],
                [
                    ("DATA_FILE_LEFT_OUT", "WARNING", "INPUT_FILES_CANNOT_BE_READ_AND_WILL_BE_LEFT_OUT", "RUN_ALL"),
                    ("ACTIVITIES_EMPTY", "ERROR", "ACTIVITIES_FILES_CANNOT_BE_READ", "OBTAIN_COMPLETE_READABLE_EXPORT"),
                ],
            )
            self.assertEqual(report["actionability"], "ACTION_REQUIRED")
            with self.assertRaises(RunAllError) as raised:
                run(source, root / "output", SMALL)
            self.assertEqual(raised.exception.code, "ACTIVITIES_EMPTY")

    def test_normalize_activities_stops_for_an_activities_file_only(self) -> None:
        # Its output has no list of left-out files, so it stops rather than
        # leave Activities out; it does not use the other files.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root)
            write(source / f"{UPLOADED}/UploadedFiles_broken_Part1.zip", NOT_ZIP)
            self.assertEqual(run_activities(source, root / "with-broken-zip")["status"], "PASS")
            write(source / "DI-Connect-Fitness/other_summarizedActivities.json", NOT_JSON)
            with self.assertRaisesRegex(
                GoldenPathError, "^an Activities file could not be read; obtain a complete, readable Export$"
            ):
                run_activities(source, root / "with-unreadable-activities")


if __name__ == "__main__":
    unittest.main()
