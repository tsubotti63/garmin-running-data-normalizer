from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
import stat
from pathlib import Path

from garmin_running_data_normalizer.intake.archive import (
    MAX_ARCHIVE_MEMBERS,
    ArchiveLimits,
    UnsafeArchiveError,
    validated_members,
)
from garmin_running_data_normalizer.intake.discovery import discover_export
from garmin_running_data_normalizer.normalizers import (
    normalize_activities,
    normalize_gear,
    normalize_personal_records,
)


class IntakeAndNormalizersTest(unittest.TestCase):
    @staticmethod
    def _fake_archive(*infos):
        class FakeArchive:
            def infolist(self):
                return list(infos)
        return FakeArchive()

    @staticmethod
    def _info(name: str, *, size: int = 1, compressed: int = 1, mode: int = 0) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name)
        info.file_size = size
        info.compress_size = compressed
        info.external_attr = mode << 16
        return info

    def test_discovery_and_activity_normalization_from_zip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = [{"summarizedActivitiesExport": [{
                "activityId": 123,
                "name": "Synthetic Run",
                "description": " synthetic memo ",
                "activityType": "running",
                "startTimeGmt": 1_750_000_000_000,
                "distance": 500_000,
                "duration": 1_800_000,
            }]}]
            with zipfile.ZipFile(root / "synthetic-export.zip", "w") as archive:
                archive.writestr("DI-Connect-Fitness/synthetic_summarizedActivities.json", json.dumps(payload))
                archive.writestr("__MACOSX/._ignored.json", "{}")
            assets = discover_export(root)
            self.assertEqual(len(assets), 1)
            records = normalize_activities(str(root))
            self.assertEqual(records[0]["garmin_activity_key"], "garmin_activity:123")
            self.assertTrue(records[0]["memo_present"])
            self.assertNotIn(str(root), records[0]["source_path"])

    def test_archive_traversal_member_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.json", "{}")
                archive.writestr("safe.json", "{}")
            with zipfile.ZipFile(path, "r") as archive:
                with self.assertRaises(UnsafeArchiveError):
                    validated_members(archive)

    def test_encrypted_flag_fails_closed(self) -> None:
        class FakeArchive:
            def infolist(self):
                info = zipfile.ZipInfo("sample.json")
                info.file_size = 1
                info.compress_size = 1
                info.flag_bits = 1
                return [info]

        with self.assertRaises(UnsafeArchiveError):
            validated_members(FakeArchive())  # type: ignore[arg-type]

    def test_archive_windows_unc_and_symlink_paths_fail_closed(self) -> None:
        cases = [
            self._info("C:/escape.json"),
            self._info("//server/share.json"),
            self._info("link.json", mode=stat.S_IFLNK | 0o777),
        ]
        for info in cases:
            with self.subTest(info=info.filename), self.assertRaises(UnsafeArchiveError):
                validated_members(self._fake_archive(info))  # type: ignore[arg-type]

        class NulInfo:
            filename = "unsafe\x00.json"
            file_size = 1
            compress_size = 1
            flag_bits = 0
            external_attr = 0

            @staticmethod
            def is_dir() -> bool:
                return False

        with self.assertRaises(UnsafeArchiveError):
            validated_members(self._fake_archive(NulInfo()))  # type: ignore[arg-type]

    def test_archive_count_size_total_and_ratio_limits_fail_closed(self) -> None:
        with self.assertRaises(UnsafeArchiveError):
            validated_members(self._fake_archive(self._info("a.json"), self._info("b.json")), ArchiveLimits(max_members=1))  # type: ignore[arg-type]
        with self.assertRaises(UnsafeArchiveError):
            validated_members(self._fake_archive(self._info("a.json", size=2)), ArchiveLimits(max_member_bytes=1))  # type: ignore[arg-type]
        with self.assertRaises(UnsafeArchiveError):
            validated_members(self._fake_archive(self._info("a.json"), self._info("b.json")), ArchiveLimits(max_total_bytes=1))  # type: ignore[arg-type]
        with self.assertRaises(UnsafeArchiveError):
            validated_members(self._fake_archive(self._info("a.json", size=201, compressed=1)), ArchiveLimits(max_compression_ratio=200))  # type: ignore[arg-type]

    def test_t7_t8_large_archive_member_boundaries(self) -> None:
        self.assertEqual(MAX_ARCHIVE_MEMBERS, 100_000)
        safe_member = self._info("safe/member.json", size=0, compressed=0)
        for count in (10_000, 10_001, 46_432, 100_000):
            with self.subTest(count=count):
                archive = self._fake_archive(*([safe_member] * count))
                self.assertEqual(len(validated_members(archive)), count)  # type: ignore[arg-type]
        excessive = self._fake_archive(*([safe_member] * 100_001))
        with self.assertRaisesRegex(UnsafeArchiveError, "member count"):
            validated_members(excessive)  # type: ignore[arg-type]

    def test_t9_malformed_archive_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "malformed.zip").write_bytes(b"not-a-zip")
            with self.assertRaises(zipfile.BadZipFile):
                discover_export(root)

    def test_gear_and_personal_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic_gear.json").write_text(json.dumps({
                "gearDTOS": [{"gearPk": 7, "displayName": "Synthetic Shoe", "gearTypeName": "shoes"}],
                "gearActivityDTOs": {"7": [{"activityId": 123}]},
            }), encoding="utf-8")
            (root / "synthetic_personalRecord.json").write_text(json.dumps({
                "personalRecords": [{"personalRecordId": 9, "activityId": 123, "personalRecordType": "synthetic_best"}]
            }), encoding="utf-8")
            gear, links = normalize_gear(str(root))
            records = normalize_personal_records(str(root))
            self.assertEqual(gear[0]["display_name"], "Synthetic Shoe")
            self.assertEqual(links[0]["activity_id"], 123)
            self.assertIn("source_sha256", links[0])
            self.assertEqual(records[0]["personal_record_id"], 9)

    def test_missing_stable_key_inputs_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic_gear.json").write_text(json.dumps({"gearDTOS": [{}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                normalize_gear(str(root))
            (root / "synthetic_gear.json").unlink()
            (root / "synthetic_personalRecord.json").write_text(json.dumps({"personalRecords": [{}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                normalize_personal_records(str(root))

    def test_personal_record_identifier_type_fails_closed(self) -> None:
        unsupported_values = [True, 1.5, ["synthetic"], {"id": "synthetic"}]
        for value in unsupported_values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "synthetic_personalRecord.json").write_text(
                    json.dumps(
                        {
                            "personalRecords": [
                                {
                                    "personalRecordId": value,
                                    "activityId": 123,
                                    "personalRecordType": "synthetic_best",
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "unsupported type"):
                    normalize_personal_records(str(root))

    def test_activity_gear_link_missing_stable_key_fails_closed(self) -> None:
        cases = [
            {"gearActivityDTOs": {"7": [{}]}},
            {"gearActivityDTOs": {"": [{"activityId": 123}]}},
        ]
        for payload in cases:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "synthetic_gear.json").write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    normalize_gear(str(root))


if __name__ == "__main__":
    unittest.main()
