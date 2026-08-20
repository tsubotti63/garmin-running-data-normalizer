from __future__ import annotations

import json
import copy
import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from garmin_running_data_normalizer import __version__
from garmin_running_data_normalizer.diagnostics.completeness import (
    build_source_completeness,
)
from garmin_running_data_normalizer.diagnostics.contracts import (
    FAMILY_DATASETS,
    SOURCE_FAMILY_ORDER,
)
from garmin_running_data_normalizer.diagnostics.doctor import (
    DoctorError,
    doctor_input,
    doctor_run_output,
    render_doctor_human,
)
from garmin_running_data_normalizer.diagnostics.support_bundle import (
    BUNDLE_MEMBERS,
    PRIVACY_PATTERNS,
    SupportBundleError,
    _completeness_projection,
    _doctor_projection,
    _privacy_scan,
    _run_quality_projection,
    _validate_archive,
    _zip_entry,
    build_support_bundle,
)
from garmin_running_data_normalizer.run_all import DATASET_PATHS, run_all
from test_run_all import RunAllTest
from tests.fit_fixture_factory import synthetic_fit


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC_VECTOR = (
    ROOT / "examples/synthetic/expected/v1_4_diagnostics_vector.json"
)


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class V14DiagnosticsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = RunAllTest()

    def _run(self, root: Path, *, optional: bool = True, bad_fit: bool = False) -> Path:
        input_root = self.helper.synthetic_input(
            root, optional=optional, bad_fit=bad_fit
        )
        output = root / "output"
        run_all(input_root, output)
        return output

    def _rehash(self, output: Path) -> None:
        manifest_path = output / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["outputs"]:
            data = (output / item["path"]).read_bytes()
            item["bytes"] = len(data)
            item["sha256"] = hashlib.sha256(data).hexdigest()
        canonical = "\n".join(
            f"{item['path']}:{item['sha256']}"
            for item in sorted(manifest["outputs"], key=lambda value: value["path"])
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        manifest["deterministic_output_digest"] = digest
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary_path = output / "run_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["deterministic_output_digest"] = digest
        summary["manifest_sha256"] = hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest()
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_run_all_adds_exact_diagnostic_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory))
            completeness = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            quality = json.loads(
                (output / "diagnostics/run_quality.json").read_text()
            )
            self.assertEqual(completeness["product_version"], "1.4.0")
            self.assertEqual(
                [item["source_family_id"] for item in completeness["families"]],
                list(SOURCE_FAMILY_ORDER),
            )
            self.assertEqual(len(quality["dataset_summary"]), 17)
            self.assertEqual(len(quality["relationship_summary"]), 6)
            self.assertEqual(quality["run_status"], "PASS")
            self.assertEqual(quality["exit_code"], 0)

    def test_absent_is_not_zero_or_delete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory), optional=False)
            report = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            sleep = next(
                item for item in report["families"] if item["source_family_id"] == "sleep"
            )
            self.assertEqual(sleep["state"], "ABSENT")
            self.assertEqual(sleep["content_validity"], "NOT_APPLICABLE")
            self.assertEqual(sleep["source_observation_count"], 0)
            self.assertIn("DO_NOT_INFER_ZERO_OR_DELETION", sleep["user_guidance_id"])

    def test_unknown_evidence_is_separate_from_six_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_root = self.helper.synthetic_input(root, optional=False)
            (input_root / "futureUnknown.json").write_text("{}", encoding="utf-8")
            output = root / "output"
            run_all(input_root, output)
            report = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            self.assertEqual(report["unknown_evidence_summary"]["classification"], "UNKNOWN")
            self.assertEqual(report["unknown_evidence_summary"]["count"], 1)
            self.assertNotIn(
                "UNKNOWN", {item["state"] for item in report["families"]}
            )

    def test_fit_bad_input_is_unreadable_or_ambiguous_and_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root, optional=True, bad_fit=True)
            report = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            fit = next(item for item in report["families"] if item["source_family_id"] == "fit")
            self.assertEqual(fit["state"], "AMBIGUOUS")
            self.assertEqual(fit["content_validity"], "UNKNOWN")
            quality = json.loads((output / "diagnostics/run_quality.json").read_text())
            self.assertEqual(quality["run_status"], "PARTIAL_SUCCESS")
            self.assertEqual(quality["exit_code"], 3)
            self.assertEqual(quality["completion_state"], "COMPLETED")

    def test_fit_allocation_conflict_is_present_malformed_partial_and_bundleable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_root = self.helper.synthetic_input(root, optional=False)
            (input_root / "synthetic-allocation-conflict.fit").write_bytes(
                synthetic_fit(sessions=2, declared_laps_per_session=2)
            )
            output = root / "output"
            result = run_all(input_root, output)
            self.assertEqual((result["status"], result["exit_code"]), ("PARTIAL_SUCCESS", 3))
            report = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            fit = next(
                item for item in report["families"]
                if item["source_family_id"] == "fit"
            )
            self.assertEqual((fit["state"], fit["content_validity"]), ("PRESENT", "MALFORMED"))
            self.assertIn("FIT_CONTENT_INCOMPLETE", fit["content_reason_codes"])
            audit = json.loads((output / "audit/fit_audit.json").read_text())
            self.assertEqual(audit[0]["parse_status"], "session_lap_allocation_conflict")
            self.assertEqual(audit[0]["session_count"], 2)
            self.assertEqual(audit[0]["lap_count"], 2)
            self.assertEqual(audit[0]["unallocated_lap_count"], 0)
            self.assertEqual(
                json.loads((output / "normalized/fit_sessions.json").read_text()),
                [],
            )
            self.assertEqual(
                json.loads((output / "normalized/fit_laps.json").read_text()),
                [],
            )
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            self.assertTrue(bundle.is_file())

    def test_closed_fit_state_matrix(self) -> None:
        records = {name: [] for names in FAMILY_DATASETS.values() for name in names}
        counts = {family: 0 for family in SOURCE_FAMILY_ORDER}
        counts["fit"] = 1
        cases = (
            ({"status_parsed_activity": 1, "incomplete_fit_count": 0}, "EMPTY", "VALID"),
            ({"status_session_lap_allocation_conflict": 1, "incomplete_fit_count": 1}, "PRESENT", "MALFORMED"),
            ({"status_bad_file_crc": 1, "incomplete_fit_count": 1}, "UNREADABLE", "UNKNOWN"),
            ({"status_unsupported_chained": 1, "incomplete_fit_count": 1}, "UNSUPPORTED", "NOT_APPLICABLE"),
        )
        for fit_status, state, validity in cases:
            with self.subTest(state=state):
                report = build_source_completeness(
                    product_version="1.4.0",
                    family_candidate_counts=counts,
                    records=records,
                    fit_status=fit_status,
                    performance_audit={},
                    unknown_evidence_count=0,
                )
                fit = next(item for item in report["families"] if item["source_family_id"] == "fit")
                self.assertEqual((fit["state"], fit["content_validity"]), (state, validity))

    def test_source_completeness_present_empty_absent_and_malformed_states(self) -> None:
        records = {name: [] for names in FAMILY_DATASETS.values() for name in names}
        for candidate, observed, audit, expected in (
            (1, 1, {}, ("PRESENT", "VALID")),
            (1, 0, {}, ("EMPTY", "VALID")),
            (0, 0, {}, ("ABSENT", "NOT_APPLICABLE")),
            (1, 1, {"invalid_value_count": 1}, ("PRESENT", "MALFORMED")),
        ):
            with self.subTest(expected=expected):
                counts = {family: 0 for family in SOURCE_FAMILY_ORDER}
                observed_counts = dict(counts)
                counts["sleep"] = candidate
                observed_counts["sleep"] = observed
                report = build_source_completeness(
                    product_version="1.4.0",
                    family_candidate_counts=counts,
                    source_observation_counts=observed_counts,
                    records=records,
                    fit_status={"incomplete_fit_count": 0},
                    performance_audit={"sleep_daily": audit},
                    unknown_evidence_count=0,
                )
                sleep = next(
                    item for item in report["families"]
                    if item["source_family_id"] == "sleep"
                )
                self.assertEqual(
                    (sleep["state"], sleep["content_validity"]), expected
                )

    def test_doctor_pre_run_does_not_predict_product_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_root = self.helper.synthetic_input(Path(directory), optional=False)
            report = doctor_input(input_root)
            self.assertEqual(report["product_status"], None)
            self.assertEqual(report["product_exit_code"], None)
            self.assertEqual(report["completion_state"], "NOT_EVALUATED")
            self.assertEqual(report["findings"][0]["code"], "RUN_ALL_NOT_EVALUATED")

    def test_doctor_pre_run_missing_activities_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = doctor_input(Path(directory))
            self.assertEqual(report["actionability"], "ACTION_REQUIRED")
            self.assertEqual(report["findings"][0]["code"], "ACTIVITIES_NOT_FOUND")

    def test_doctor_missing_completion_marker_does_not_reconstruct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = doctor_run_output(Path(directory))
            self.assertEqual(report["completion_state"], "NOT_COMPLETED")
            self.assertIsNone(report["product_status"])
            self.assertEqual(report["findings"][0]["code"], "COMPLETION_MARKER_MISSING")

    def test_doctor_post_run_preserves_pass_and_partial_exit(self) -> None:
        for optional, bad_fit, status, exit_code in (
            (True, False, "PASS", 0),
            (False, False, "PASS_WITH_WARNINGS", 0),
            (True, True, "PARTIAL_SUCCESS", 3),
        ):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                output = self._run(
                    Path(directory), optional=optional, bad_fit=bad_fit
                )
                report = doctor_run_output(output)
                self.assertEqual(report["product_status"], status)
                self.assertEqual(report["product_exit_code"], exit_code)
                self.assertEqual(report["diagnostic_contract_availability"], "CURRENT")
                self.assertIn("known_boundary", report)
                self.assertIsInstance(report["affected_scopes"], list)
                self.assertIsInstance(report["unaffected_scopes"], list)
                self.assertIsInstance(report["doctor_next_action_id"], str)
                self.assertIsInstance(report["support_bundle_suggested"], bool)

    def test_doctor_human_wording_preserves_first_user_result_meanings(self) -> None:
        cases = (
            (True, False, "Completed. Outputs are available within the declared Product contract."),
            (False, False, "Completed with warnings. Outputs are available"),
            (True, True, "This is not a fatal run failure. Valid Activities output is available"),
        )
        for optional, bad_fit, wording in cases:
            with self.subTest(wording=wording), tempfile.TemporaryDirectory() as directory:
                output = self._run(Path(directory), optional=optional, bad_fit=bad_fit)
                human = render_doctor_human(doctor_run_output(output))
                self.assertIn(wording, human)
        with tempfile.TemporaryDirectory() as directory:
            human = render_doctor_human(doctor_run_output(Path(directory)))
            self.assertIn("Run not completed (exit 2)", human)
            self.assertIn("No completed Run-All output was published", human)

    def test_support_bundle_exact_members_metadata_and_privacy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            bundle = root / "support.zip"
            result = build_support_bundle(output, bundle)
            self.assertFalse(result["uploaded"])
            with zipfile.ZipFile(bundle) as archive:
                self.assertEqual(archive.namelist(), list(BUNDLE_MEMBERS))
                self.assertEqual(archive.comment, b"")
                for info in archive.infolist():
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                    self.assertEqual(info.create_system, 3)
                    self.assertEqual(info.create_version, 20)
                    self.assertEqual(info.extract_version, 20)
                    self.assertEqual(info.flag_bits, 0)
                    self.assertEqual(info.volume, 0)
                    self.assertEqual(info.internal_attr, 0)
                    self.assertEqual(info.external_attr >> 16, 0o100644)
                    data = archive.read(info)
                    self.assertFalse(any(pattern.search(data) for pattern in PRIVACY_PATTERNS))
                public_quality = json.loads(archive.read("run_quality.json"))
                public_source = json.loads(
                    archive.read("source_completeness.json")
                )
                self.assertNotIn("output_digests", public_quality)
                self.assertEqual(len(public_quality["dataset_summary"]), 17)
                self.assertEqual(len(public_source["families"]), 13)
                self.assertTrue(
                    all("observation_ref" not in item for item in public_source["families"])
                )

    def test_support_bundle_repeat_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            first = root / "first.zip"
            second = root / "second.zip"
            one = build_support_bundle(output, first)
            two = build_support_bundle(output, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(one["archive_sha256"], two["archive_sha256"])

    def test_partial_support_bundle_repeat_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root, bad_fit=True)
            first = root / "partial-first.zip"
            second = root / "partial-second.zip"
            one = build_support_bundle(output, first)
            two = build_support_bundle(output, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(one["archive_sha256"], two["archive_sha256"])
            with zipfile.ZipFile(first) as archive:
                quality = json.loads(archive.read("run_quality.json"))
            self.assertEqual((quality["run_status"], quality["exit_code"]), ("PARTIAL_SUCCESS", 3))

    def test_support_bundle_completed_status_matrix_and_fatal_boundary(self) -> None:
        for optional, bad_fit, expected_status, expected_exit in (
            (True, False, "PASS", 0),
            (False, False, "PASS_WITH_WARNINGS", 0),
            (True, True, "PARTIAL_SUCCESS", 3),
        ):
            with self.subTest(status=expected_status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = self._run(root, optional=optional, bad_fit=bad_fit)
                bundle = root / "support.zip"
                build_support_bundle(output, bundle)
                with zipfile.ZipFile(bundle) as archive:
                    quality = json.loads(archive.read("run_quality.json"))
                    self.assertEqual(quality["run_status"], expected_status)
                    self.assertEqual(quality["exit_code"], expected_exit)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "fatal.zip"
            with self.assertRaises(SupportBundleError):
                build_support_bundle(root, destination)
            self.assertFalse(destination.exists())

    def test_support_projection_rejects_unknown_warning_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory), optional=False)
            quality = json.loads((output / "diagnostics/run_quality.json").read_text())
            tampered = copy.deepcopy(quality)
            tampered["warnings"] = [
                {"code": "OPTIONAL_FAMILY_NOT_PRESENT", "family": "private-family", "count": 1}
            ]
            with self.assertRaisesRegex(
                SupportBundleError, "Run Quality warning is not registered"
            ):
                _run_quality_projection(tampered)

    def test_support_projection_accepts_registered_hrv_warning_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory), optional=False)
            quality = json.loads((output / "diagnostics/run_quality.json").read_text())
            quality["warnings"] = [
                {
                    "code": "DAILY_METRICS_REVIEW_REQUIRED",
                    "family": "hrv",
                    "count": 1,
                }
            ]
            projected = _run_quality_projection(quality)
            self.assertEqual(projected["warnings"], quality["warnings"])

    def test_support_projection_rejects_unknown_completeness_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory), optional=False)
            completeness = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            tampered = copy.deepcopy(completeness)
            tampered["families"][0]["reason_codes"] = ["UNREGISTERED_PRIVATE_TEXT"]
            with self.assertRaisesRegex(
                SupportBundleError, "unregistered code"
            ):
                _completeness_projection(tampered)

    def test_support_projection_rejects_unknown_fields_default_deny(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory))
            completeness = json.loads(
                (output / "diagnostics/source_completeness.json").read_text()
            )
            quality = json.loads(
                (output / "diagnostics/run_quality.json").read_text()
            )
            for artifact, projector in (
                (completeness, _completeness_projection),
                (quality, _run_quality_projection),
            ):
                with self.subTest(projector=projector.__name__):
                    tampered = copy.deepcopy(artifact)
                    tampered["private_value"] = "synthetic-sensitive-row"
                    with self.assertRaisesRegex(
                        SupportBundleError, "shape is invalid"
                    ):
                        projector(tampered)

    def test_privacy_scan_rejects_registered_negative_classes(self) -> None:
        samples = {
            "PN-01": b"/" + b"Users/private/input.json",
            "PN-01-private": b"/" + b"private/tmp/input.json",
            "PN-01-var": b"/" + b"var/folders/secret/input.json",
            "PN-01-posix": b"/" + b"tmp/SYNTHETIC/input.json",
            "PN-01-relative": b"private/source/file.json",
            "PN-02": b"C:\\private\\input.json",
            "PN-03": b"\\\\synthetic-host\\private-share\\file.json",
            "PN-04": b"person" + b"@example.invalid",
            "PN-05": b"1735689600000",
            "PN-06": b'"stable_key":"private"',
            "PN-06-garmin": b"garmin_activity:SYNTHETIC-SECRET",
            "PN-07": b'"latitude":35.0',
            "PN-07-coordinate": b"35.6812,139.7671",
            "PN-07-route": b"route=SYNTHETIC-CANARY",
            "PN-08": b"Traceback (most recent call last)",
            "PN-09": b"exception message: private",
            "PN-09-value-error": b"ValueError: SYNTHETIC-CANARY",
            "PN-09-warning": b"warning: SYNTHETIC-CANARY",
            "PN-09-password": b"password=SYNTHETIC-CANARY",
            "PN-09-token": b"token=SYNTHETIC-CANARY",
            "PN-09-private-key": b"-----BEGIN PRIVATE KEY-----",
            "PN-09-basic": b"Authorization: Basic SYNTHETIC-CANARY",
            "PN-10": b'"source_sha256":"private"',
            "PN-10-output": b"private_output_sha256=SYNTHETIC-CANARY",
            "PN-10-digest": b"deterministic_output_digest=SYNTHETIC-CANARY",
            "PN-11": b'{"activityId":"PRIVATE-ROW"}',
            "PN-11-csv": b"calendarDate,activityId,value\n2030-01-01,A1,1",
            "PN-11-generic-csv": b"a,b,c\n1,2,3",
            "PN-11-two-column-csv": b"a,b\n1,2\n",
            "PN-11-four-column-csv": b"a,b,c,d\n1,2,3,4\n",
            "PN-12": b'{"hostname":"private-host"}',
            "PN-12-free": b"hostname=host cwd=/" + b"tmp locale=ja_JP",
            "PN-12-packages": b"package list: private-package",
            "PN-20": b'{"automatic_upload":true}',
        }
        for case_id, sample in samples.items():
            with self.subTest(case_id=case_id):
                with self.assertRaisesRegex(
                    SupportBundleError, "privacy validation failed"
                ):
                    _privacy_scan(
                        {
                            "README.md": sample,
                            "doctor.json": b"{}",
                            "source_completeness.json": b"{}",
                            "run_quality.json": b"{}",
                        }
                    )

    def test_privacy_negative_final_byte_boundary_is_non_mutating(self) -> None:
        samples = (
            ("PN-01", b"/" + b"private/tmp/SYNTHETIC-CANARY/input.json"),
            ("PN-01-posix", b"/" + b"usr/local/SYNTHETIC-CANARY/python"),
            ("PN-02", b"C:\\" + b"Users\\SYNTHETIC-CANARY\\input.json"),
            ("PN-03", b"\\\\SYNTHETIC-CANARY\\private-share\\file.json"),
            ("PN-04", b"SYNTHETIC-CANARY" + b"@example.invalid"),
            ("PN-05", b"2039-12-31T23:59:59+09:00 SYNTHETIC-CANARY"),
            ("PN-06", b'"stable_key":"SYNTHETIC-CANARY"'),
            ("PN-07", b"35.6812,139.7671 SYNTHETIC-CANARY"),
            ("PN-08", b"Traceback (most recent call last): SYNTHETIC-CANARY"),
            ("PN-09", b"ValueError: SYNTHETIC-CANARY"),
            ("PN-10", b"private_output_sha256=SYNTHETIC-CANARY"),
            ("PN-11", b"a,b,c\nSYNTHETIC-CANARY,2,3"),
            ("PN-12", b"hostname=SYNTHETIC-CANARY cwd=/" + b"tmp locale=ja_JP"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            before = _tree_hashes(output)
            for index, (case_id, sample) in enumerate(samples):
                with self.subTest(case_id=case_id):
                    destination = root / f"blocked-{index}.zip"
                    with patch(
                        "garmin_running_data_normalizer.diagnostics.support_bundle.README",
                        sample,
                    ):
                        with self.assertRaises(SupportBundleError) as caught:
                            build_support_bundle(output, destination)
                    self.assertEqual(
                        caught.exception.code, "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED"
                    )
                    self.assertNotIn("SYNTHETIC-CANARY", str(caught.exception))
                    self.assertFalse(destination.exists())
                    self.assertEqual(list(root.glob(f".{destination.name}.*")), [])
                    self.assertEqual(_tree_hashes(output), before)

    def test_privacy_negative_archive_and_sharing_boundaries_are_non_mutating(
        self,
    ) -> None:
        def mutated_archive(kind: str, expected: dict[str, bytes]) -> bytes:
            stream = io.BytesIO()
            with zipfile.ZipFile(
                stream,
                "w",
                compression=zipfile.ZIP_STORED,
            ) as archive:
                for name in BUNDLE_MEMBERS:
                    actual_name = name
                    if name == "manifest.json":
                        actual_name = {
                            "traversal": "../SYNTHETIC-CANARY.json",
                            "nested": "nested/SYNTHETIC-CANARY.zip",
                        }.get(kind, name)
                    info, data = _zip_entry(actual_name, expected[name])
                    if kind == "metadata" and name == "doctor.json":
                        info.comment = b"SYNTHETIC-CANARY"
                    archive.writestr(info, data)
                if kind == "extra":
                    info, data = _zip_entry(
                        "SYNTHETIC-CANARY.json",
                        b"{}",
                    )
                    archive.writestr(info, data)
            return stream.getvalue()

        def archive_attack(kind: str):
            def invoke(output: Path, destination: Path) -> None:
                def validate(_: bytes, expected: dict[str, bytes]) -> None:
                    _validate_archive(mutated_archive(kind, expected), expected)

                with patch(
                    "garmin_running_data_normalizer.diagnostics."
                    "support_bundle._validate_archive",
                    side_effect=validate,
                ):
                    build_support_bundle(output, destination)

            return invoke

        def symlink_attack(output: Path, destination: Path) -> None:
            linked = destination.parent / "SYNTHETIC-CANARY-output-link"
            linked.symlink_to(output, target_is_directory=True)
            build_support_bundle(linked, destination)

        def size_attack(output: Path, destination: Path) -> None:
            with patch(
                "garmin_running_data_normalizer.diagnostics."
                "support_bundle.MAX_MEMBER_BYTES",
                1,
            ):
                build_support_bundle(output, destination)

        def collision_attack(output: Path, destination: Path) -> None:
            def project(report: dict[str, object]) -> dict[str, object]:
                value = _doctor_projection(report)
                value["authority_references"] = [
                    "SYNTHETIC-CANARY.json",
                    "synthetic-canary.json",
                ]
                return value

            with patch(
                "garmin_running_data_normalizer.diagnostics."
                "support_bundle._doctor_projection",
                side_effect=project,
            ):
                build_support_bundle(output, destination)

        def sharing_attack(mode: str):
            def invoke(output: Path, destination: Path) -> None:
                def encode(value: object) -> bytes:
                    changed = copy.deepcopy(value)
                    if (
                        isinstance(changed, dict)
                        and changed.get("format")
                        == "garmin-running-data-normalizer-support-privacy-scan-v1"
                    ):
                        if mode == "automatic_upload":
                            changed["automatic_upload"] = True
                        elif mode == "missing_human_review":
                            changed.pop("human_review_required", None)
                    return (
                        json.dumps(
                            changed,
                            ensure_ascii=False,
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    ).encode("utf-8")

                with patch(
                    "garmin_running_data_normalizer.diagnostics."
                    "support_bundle._json_bytes",
                    side_effect=encode,
                ):
                    build_support_bundle(output, destination)

            return invoke

        cases = (
            ("PN-13", archive_attack("extra"), "SUPPORT_BUNDLE_MEMBER_SET_INVALID"),
            ("PN-14", archive_attack("traversal"), "SUPPORT_BUNDLE_MEMBER_SET_INVALID"),
            ("PN-15", symlink_attack, "SUPPORT_BUNDLE_PATH_UNSAFE"),
            ("PN-16", archive_attack("nested"), "SUPPORT_BUNDLE_MEMBER_SET_INVALID"),
            ("PN-17", archive_attack("metadata"), "SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED"),
            ("PN-18", size_attack, "SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED"),
            ("PN-19", collision_attack, "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED"),
            ("PN-20-auto", sharing_attack("automatic_upload"), "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED"),
            ("PN-20-missing", sharing_attack("missing_human_review"), "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            before = _tree_hashes(output)
            for index, (case_id, invoke, expected_code) in enumerate(cases):
                with self.subTest(case_id=case_id):
                    destination = root / f"archive-blocked-{index}.zip"
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(
                        stderr
                    ), self.assertRaises(SupportBundleError) as caught:
                        invoke(output, destination)
                    self.assertEqual(caught.exception.code, expected_code)
                    visible = stdout.getvalue() + stderr.getvalue() + str(caught.exception)
                    self.assertNotIn("SYNTHETIC-CANARY", visible)
                    self.assertFalse(destination.exists())
                    self.assertEqual(list(root.glob(f".{destination.name}.*")), [])
                    self.assertEqual(_tree_hashes(output), before)

    def test_privacy_scan_requires_human_review_boundary(self) -> None:
        base = {
            "README.md": b"Human review is required.",
            "doctor.json": b"{}",
            "source_completeness.json": b"{}",
            "run_quality.json": b"{}",
        }
        for name, value in (
            ("false", {"status": "PASS", "forbidden_finding_count": 0, "human_review_required": False}),
            ("missing", {"status": "PASS", "forbidden_finding_count": 0}),
        ):
            with self.subTest(name=name), self.assertRaises(SupportBundleError) as caught:
                _privacy_scan(
                    {
                        **base,
                        "privacy_scan.json": json.dumps(value).encode("utf-8"),
                    }
                )
            self.assertEqual(caught.exception.code, "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED")

    def test_privacy_scan_rejects_unicode_and_casefold_reference_collision(self) -> None:
        for values in (("A\u030a.json", "Å.json"), ("Qa.json", "qa.json")):
            with self.subTest(values=values):
                doctor = json.dumps(
                    {"authority_references": list(values)},
                    ensure_ascii=False,
                ).encode("utf-8")
                with self.assertRaisesRegex(SupportBundleError, "privacy validation failed"):
                    _privacy_scan(
                        {
                            "README.md": b"Human review is required.",
                            "doctor.json": doctor,
                            "source_completeness.json": b"{}",
                            "run_quality.json": b"{}",
                        }
                    )

    def test_support_projection_rejects_non_integer_counts_and_inference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory))
            quality = json.loads((output / "diagnostics/run_quality.json").read_text())
            mutations = (
                ("dataset_bool", lambda value: value["dataset_summary"][0].__setitem__("record_count", True)),
                ("dataset_string", lambda value: value["dataset_summary"][0].__setitem__("record_count", "1")),
                ("relationship_private", lambda value: value["relationship_summary"][0].__setitem__("eligible_count", "SYNTHETIC_PRIVATE_ROW_VALUE")),
                ("inference", lambda value: value["relationship_summary"][0].__setitem__("inference_performed", True)),
            )
            for name, mutate in mutations:
                with self.subTest(name=name):
                    tampered = copy.deepcopy(quality)
                    mutate(tampered)
                    with self.assertRaises(SupportBundleError):
                        _run_quality_projection(tampered)

    def test_rehashed_semantic_contradiction_blocks_doctor_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            quality_path = output / "diagnostics/run_quality.json"
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            quality["dataset_summary"][0]["record_count"] = 999
            quality_path.write_text(
                json.dumps(quality, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self._rehash(output)
            with self.assertRaises(DoctorError):
                doctor_run_output(output)
            destination = root / "contradictory.zip"
            with self.assertRaises(SupportBundleError):
                build_support_bundle(output, destination)
            self.assertFalse(destination.exists())

    def test_rehashed_source_completeness_contradiction_blocks_doctor_and_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            completeness_path = output / "diagnostics/source_completeness.json"
            completeness = json.loads(completeness_path.read_text(encoding="utf-8"))
            activities = completeness["families"][0]
            activities.update(
                {
                    "state": "ABSENT",
                    "content_validity": "NOT_APPLICABLE",
                    "candidate_asset_count": 0,
                    "readable_asset_count": 0,
                    "source_observation_count": 0,
                    "state_counts": {"ABSENT": 1},
                    "reason_codes": ["SOURCE_NOT_OBSERVED"],
                    "content_reason_codes": [],
                    "user_guidance_id": "DO_NOT_INFER_ZERO_OR_DELETION",
                }
            )
            completeness_path.write_text(
                json.dumps(completeness, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            quality_path = output / "diagnostics/run_quality.json"
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            quality["source_completeness"]["state_counts"] = {
                **quality["source_completeness"]["state_counts"],
                "ABSENT": quality["source_completeness"]["state_counts"].get("ABSENT", 0) + 1,
                "PRESENT": quality["source_completeness"]["state_counts"].get("PRESENT", 0) - 1,
            }
            quality_path.write_text(
                json.dumps(quality, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self._rehash(output)
            with self.assertRaises(DoctorError):
                doctor_run_output(output)
            destination = root / "contradictory-completeness.zip"
            with self.assertRaises(SupportBundleError):
                build_support_bundle(output, destination)
            self.assertFalse(destination.exists())

    def test_projection_required_and_unknown_key_matrix_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory))
            artifacts = (
                (
                    json.loads((output / "diagnostics/source_completeness.json").read_text()),
                    _completeness_projection,
                ),
                (
                    json.loads((output / "diagnostics/run_quality.json").read_text()),
                    _run_quality_projection,
                ),
            )
            for artifact, projector in artifacts:
                for key in tuple(artifact):
                    with self.subTest(projector=projector.__name__, removed=key):
                        changed = copy.deepcopy(artifact)
                        changed.pop(key)
                        with self.assertRaises(SupportBundleError):
                            projector(changed)
                    with self.subTest(projector=projector.__name__, renamed=key):
                        changed = copy.deepcopy(artifact)
                        value = changed.pop(key)
                        changed[f"renamed_{key}"] = value
                        with self.assertRaises(SupportBundleError):
                            projector(changed)
                with self.subTest(projector=projector.__name__, added="unknown"):
                    changed = copy.deepcopy(artifact)
                    changed["unknown_required_key"] = None
                    with self.assertRaises(SupportBundleError):
                        projector(changed)
            completeness, quality = (item[0] for item in artifacts)
            nested_models = (
                (
                    "completeness_family",
                    completeness,
                    _completeness_projection,
                    lambda value: value["families"][0],
                ),
                (
                    "completeness_unknown",
                    completeness,
                    _completeness_projection,
                    lambda value: value["unknown_evidence_summary"],
                ),
                (
                    "quality_dataset",
                    quality,
                    _run_quality_projection,
                    lambda value: value["dataset_summary"][0],
                ),
                (
                    "quality_relationship",
                    quality,
                    _run_quality_projection,
                    lambda value: value["relationship_summary"][0],
                ),
                (
                    "quality_source_summary",
                    quality,
                    _run_quality_projection,
                    lambda value: value["source_completeness"],
                ),
                (
                    "quality_record_counts",
                    quality,
                    _run_quality_projection,
                    lambda value: value["record_counts"],
                ),
                (
                    "quality_review_aggregate",
                    quality,
                    _run_quality_projection,
                    lambda value: value["review_required"],
                ),
            )
            for name, artifact, projector, accessor in nested_models:
                keys = tuple(accessor(artifact))
                for key in keys:
                    for mutation in ("remove", "rename"):
                        with self.subTest(model=name, key=key, mutation=mutation):
                            changed = copy.deepcopy(artifact)
                            target = accessor(changed)
                            value = target.pop(key)
                            if mutation == "rename":
                                target[f"renamed_{key}"] = value
                            with self.assertRaises(SupportBundleError):
                                projector(changed)
                with self.subTest(model=name, mutation="add"):
                    changed = copy.deepcopy(artifact)
                    accessor(changed)["unknown_nested_key"] = None
                    with self.assertRaises(SupportBundleError):
                        projector(changed)

    def test_run_quality_schema_and_cardinality_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = self._run(Path(directory))
            quality = json.loads((output / "diagnostics/run_quality.json").read_text())
            mutations = (
                ("unknown_field", lambda value: value.__setitem__("unexpected", 1)),
                ("extra_dataset", lambda value: value["dataset_summary"].append(copy.deepcopy(value["dataset_summary"][0]))),
                ("seventh_relationship", lambda value: value["relationship_summary"].append(copy.deepcopy(value["relationship_summary"][0]))),
                ("status_exit", lambda value: value.__setitem__("exit_code", 2)),
                ("schema", lambda value: value.__setitem__("schema_version", "garmin-run-quality:v2")),
                ("version", lambda value: value.__setitem__("product_version", "1.3.3")),
            )
            for name, mutate in mutations:
                with self.subTest(name=name):
                    tampered = copy.deepcopy(quality)
                    mutate(tampered)
                    with self.assertRaises(SupportBundleError):
                        _run_quality_projection(tampered)

    def test_fixture_contract_identifiers_have_executable_coverage(self) -> None:
        coverage = json.loads(
            (ROOT / "tests/v14_contract_coverage.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(coverage), 55)
        self.assertEqual(set(coverage), {
            *(f"FX-{index:02d}" for index in range(1, 13)),
            *(f"SB-{index:02d}" for index in range(1, 16)),
            *(f"PN-{index:02d}" for index in range(1, 21)),
            *(f"DET-{index:02d}" for index in range(1, 9)),
        })
        for case_id, references in coverage.items():
            self.assertIsInstance(references, list, case_id)
            self.assertTrue(references, case_id)
            for reference in references:
                relative, symbol = reference.split("::", 1)
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertTrue(
                    f"def {symbol}" in source or f"{symbol}:" in source,
                    reference,
                )

    def test_generated_manifest_is_in_privacy_scan_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            destination = root / "manifest-private.zip"
            with patch(
                "garmin_running_data_normalizer.diagnostics.support_bundle.BUNDLE_FORMAT",
                "/" + "Users/SYNTHETIC_PRIVATE/bundle-v1",
            ):
                with self.assertRaisesRegex(SupportBundleError, "privacy validation failed"):
                    build_support_bundle(output, destination)
            self.assertFalse(destination.exists())

    def test_archive_validation_rejects_traversal_extra_and_symlink(self) -> None:
        expected = {name: b"{}" for name in BUNDLE_MEMBERS}
        for mutation in (
            "traversal", "absolute", "backslash", "extra", "nested", "extension", "symlink"
        ):
            with self.subTest(mutation=mutation):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
                    for name in BUNDLE_MEMBERS:
                        actual_name = name
                        if name == "manifest.json":
                            actual_name = {
                                "traversal": "../manifest.json",
                                "absolute": "/manifest.json",
                                "backslash": "..\\manifest.json",
                                "nested": "nested/manifest.json",
                                "extension": "manifest.zip",
                            }.get(mutation, name)
                        info = zipfile.ZipInfo(actual_name, (1980, 1, 1, 0, 0, 0))
                        info.create_system = 3
                        info.compress_type = zipfile.ZIP_STORED
                        info.external_attr = (
                            0o120777 << 16
                            if mutation == "symlink" and name == "doctor.json"
                            else 0o100644 << 16
                        )
                        archive.writestr(info, expected[name])
                    if mutation == "extra":
                        archive.writestr("unexpected.json", b"{}")
                with self.assertRaises(SupportBundleError):
                    _validate_archive(stream.getvalue(), expected)

    def test_archive_validation_rejects_each_frozen_metadata_mutation(self) -> None:
        expected = {name: b"{}" for name in BUNDLE_MEMBERS}
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in BUNDLE_MEMBERS:
                info, data = _zip_entry(name, expected[name])
                archive.writestr(info, data)
        original = stream.getvalue()
        local = original.index(b"PK\x03\x04")
        central = original.index(b"PK\x01\x02")
        mutations = {
            "create_system": ((central + 5, b"\x00"),),
            "create_version": ((central + 4, b"\x0a"),),
            "extract_version": ((local + 4, b"\x0a\x00"), (central + 6, b"\x0a\x00")),
            "flag_bits": ((local + 6, b"\x01\x00"), (central + 8, b"\x01\x00")),
            "volume": ((central + 34, b"\x01\x00"),),
            "internal_attr": ((central + 36, b"\x01\x00"),),
            "mtime": ((local + 10, b"\x01\x00"), (central + 12, b"\x01\x00")),
            "mode": ((central + 38, b"\xff\xff\xff\xff"),),
        }
        for field, edits in mutations.items():
            with self.subTest(field=field):
                changed = bytearray(original)
                for offset, value in edits:
                    changed[offset : offset + len(value)] = value
                with self.assertRaises(SupportBundleError):
                    _validate_archive(bytes(changed), expected)

    def test_archive_validation_rejects_comment_extra_and_size_overflow(self) -> None:
        expected = {name: b"{}" for name in BUNDLE_MEMBERS}
        for mutation in ("comment", "extra"):
            with self.subTest(mutation=mutation):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
                    for name in BUNDLE_MEMBERS:
                        info, data = _zip_entry(name, expected[name])
                        if name == "doctor.json":
                            if mutation == "comment":
                                info.comment = b"SYNTHETIC-CANARY"
                            else:
                                info.extra = b"\x01\x00\x00\x00"
                        archive.writestr(info, data)
                with self.assertRaises(SupportBundleError):
                    _validate_archive(stream.getvalue(), expected)
        stream = io.BytesIO()
        large_expected = dict(expected)
        large_expected["doctor.json"] = b"x" * 8
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
            for name in BUNDLE_MEMBERS:
                info, data = _zip_entry(name, large_expected[name])
                archive.writestr(info, data)
        with patch(
            "garmin_running_data_normalizer.diagnostics.support_bundle.MAX_MEMBER_BYTES",
            4,
        ):
            with self.assertRaises(SupportBundleError) as caught:
                _validate_archive(stream.getvalue(), large_expected)
        self.assertEqual(caught.exception.code, "SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED")
        with patch(
            "garmin_running_data_normalizer.diagnostics.support_bundle.MAX_TOTAL_BYTES",
            len(stream.getvalue()) - 1,
        ):
            with self.assertRaises(SupportBundleError) as caught:
                _validate_archive(stream.getvalue(), large_expected)
        self.assertEqual(caught.exception.code, "SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED")

    def test_support_bundle_preserves_source_and_required_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root, optional=False)
            before = _tree_hashes(output)
            bundle = root / "support.zip"
            build_support_bundle(output, bundle)
            self.assertEqual(_tree_hashes(output), before)
            with zipfile.ZipFile(bundle) as archive:
                readme = archive.read("README.md").decode("utf-8")
                quality = json.loads(archive.read("run_quality.json"))
            for wording in (
                "Human review is required",
                "No automatic upload occurred",
                "aggregate counts can reveal usage volume",
                "Private Vulnerability Reporting",
            ):
                self.assertIn(wording, readme)
            self.assertEqual(
                set(("review_required", "excluded", "missing")),
                set(("review_required", "excluded", "missing")) & set(quality),
            )
            self.assertIsNot(quality["review_required"], quality["excluded"])

    def test_support_bundle_separate_process_and_different_root_are_identical(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first_root = Path(first_directory)
            second_root = Path(second_directory)
            output = self._run(first_root)
            copied = second_root / "copied-output"
            shutil.copytree(output, copied)
            first = first_root / "first.zip"
            second = second_root / "second.zip"
            build_support_bundle(output, first)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "garmin_running_data_normalizer",
                    "support-bundle",
                    "--run-output",
                    str(copied),
                    "--output",
                    str(second),
                ],
                cwd=Path(__file__).resolve().parents[1],
                env={**os.environ, "PYTHONPATH": "src"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_reversed_creation_and_mapping_order_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_output = self._run(root)
            second_output = root / "reverse-created"
            second_output.mkdir()
            files = sorted(
                (path for path in first_output.rglob("*") if path.is_file()),
                reverse=True,
            )
            for source in files:
                relative = source.relative_to(first_output)
                destination = second_output / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.suffix == ".json":
                    value = json.loads(source.read_text(encoding="utf-8"))
                    if isinstance(value, dict):
                        value = dict(reversed(list(value.items())))
                    destination.write_text(
                        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                        + "\n",
                        encoding="utf-8",
                    )
                else:
                    destination.write_bytes(source.read_bytes())
            first = root / "ordered.zip"
            second = root / "reverse.zip"
            build_support_bundle(first_output, first)
            build_support_bundle(second_output, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_tracked_cross_platform_diagnostic_vector(self) -> None:
        expected = json.loads(DIAGNOSTIC_VECTOR.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            run_all(ROOT / expected["fixture"], output)
            doctor = doctor_run_output(output)
            doctor_bytes = (
                json.dumps(doctor, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8")
            bundle = root / "support.zip"
            result = build_support_bundle(output, bundle)
            summary = json.loads((output / "run_summary.json").read_text())
            schema = json.loads((output / "SCHEMA_CATALOG.json").read_text())
            run_quality = json.loads(
                (output / "diagnostics/run_quality.json").read_text()
            )
            self.assertEqual(__version__, expected["product_version"])
            self.assertEqual(summary["status"], expected["run_status"])
            self.assertEqual(
                3 if summary["status"] == "PARTIAL_SUCCESS" else 0,
                expected["product_exit_code"],
            )
            self.assertEqual(len(summary["generated_paths"]), expected["generated_path_count"])
            self.assertEqual(len(schema["datasets"]), expected["dataset_count"])
            self.assertEqual(
                sum(len(item["fields"]) for item in schema["datasets"]),
                expected["field_count"],
            )
            self.assertEqual(
                len(run_quality["relationship_summary"]),
                expected["relationship_count"],
            )
            self.assertEqual(
                hashlib.sha256(
                    (output / "diagnostics/source_completeness.json").read_bytes()
                ).hexdigest(),
                expected["source_completeness_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(
                    (output / "diagnostics/run_quality.json").read_bytes()
                ).hexdigest(),
                expected["run_quality_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(doctor_bytes).hexdigest(),
                expected["doctor_json_sha256"],
            )
            self.assertEqual(
                result["archive_sha256"],
                expected["support_bundle"]["archive_sha256"],
            )
            self.assertEqual(
                result["bundle_content_sha256"],
                expected["support_bundle"]["content_sha256"],
            )
            with zipfile.ZipFile(bundle) as archive:
                actual_members = {
                    name: {
                        "bytes": len(archive.read(name)),
                        "sha256": hashlib.sha256(archive.read(name)).hexdigest(),
                    }
                    for name in archive.namelist()
                }
            self.assertEqual(actual_members, expected["support_bundle"]["members"])

    def test_support_bundle_rejects_symlinked_authority_and_fatal_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            quality = output / "diagnostics/run_quality.json"
            target = root / "quality-copy.json"
            target.write_bytes(quality.read_bytes())
            quality.unlink()
            quality.symlink_to(target)
            with self.assertRaises(SupportBundleError):
                build_support_bundle(output, root / "unsafe.zip")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(SupportBundleError):
                build_support_bundle(root, root / "fatal.zip")

    def test_support_bundle_member_size_cap_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            with patch(
                "garmin_running_data_normalizer.diagnostics.support_bundle.MAX_MEMBER_BYTES",
                1,
            ):
                with self.assertRaisesRegex(SupportBundleError, "size limit"):
                    build_support_bundle(output, root / "oversized.zip")

    def test_support_bundle_existing_destination_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = self._run(root)
            destination = root / "support.zip"
            destination.write_bytes(b"existing")
            with self.assertRaisesRegex(
                SupportBundleError, "destination must be new"
            ):
                build_support_bundle(output, destination)
            self.assertEqual(destination.read_bytes(), b"existing")

    def test_normalized_dataset_count_and_names_remain_frozen(self) -> None:
        self.assertEqual(len(DATASET_PATHS), 17)
        self.assertEqual(
            set(DATASET_PATHS),
            {
                "activities", "gear", "activity_gear", "personal_records",
                "fit_sessions", "fit_laps", "activity_fit_links",
                "hill_score_daily", "endurance_score_daily", "race_prediction_daily",
                "sleep_daily", "uds_daily", "acute_training_load_daily",
                "training_readiness_daily", "vo2max_daily", "hrv_daily",
                "training_history_daily",
            },
        )

    def test_version_is_v14_candidate(self) -> None:
        self.assertEqual(__version__, "1.4.0")


if __name__ == "__main__":
    unittest.main()
