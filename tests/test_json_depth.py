"""The limit of the nesting of the JSON that the product reads (stage E2d).

Python 3.11 stops reading near its recursion limit, while Python 3.15 on Linux
read JSON nested 100,000 deep (stage E2c), so that the limit, not the version
of Python, decides. The JSON here is 300 deep, which every version reads, so
that a reader without the check fails these tests on every version.
"""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

from garmin_running_data_normalizer.common.json_depth import MAX_JSON_DEPTH, check_json_depth
from garmin_running_data_normalizer.intake import accounts, discovery
from garmin_running_data_normalizer.snapshot import merge, store
from tests.test_snapshot_unreadable_files import listed, one_snapshot
from tests.test_unreadable_files import export, write


def nested(depth: int) -> list[Any]:
    """Lists nested ``depth`` deep: ``[]`` is 1 deep."""
    value: list[Any] = []
    for _ in range(depth - 1):
        value = [value]
    return value


def nested_text(depth: int, inner: str = "") -> str:
    return "[" * depth + inner + "]" * depth


# A lone surrogate, which a reader repairs by following the value by
# recursion (stage A3d-2c-1).
LONE_SURROGATE = '"\\ud800"'


class CountTest(unittest.TestCase):
    def test_a_scalar_is_0_deep_and_an_empty_list_or_object_1_deep(self) -> None:
        for value in (None, 1, 1.5, "text", True):
            with self.subTest(value=value):
                check_json_depth(value, limit=0)
        check_json_depth([], limit=1)
        check_json_depth({}, limit=1)
        for value in ([[]], [{}], {"a": []}, {"a": {}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_json_depth(value, limit=1)

    def test_256_levels_are_read_and_257_are_not(self) -> None:
        self.assertEqual(MAX_JSON_DEPTH, 256)
        check_json_depth(nested(256))
        with self.assertRaisesRegex(ValueError, "nested more than 256 deep"):
            check_json_depth(nested(257))
        check_json_depth(json.loads(nested_text(256, LONE_SURROGATE)))
        with self.assertRaises(ValueError):
            check_json_depth(json.loads(nested_text(257)))

    def test_lists_and_objects_count_alike(self) -> None:
        value: Any = {}
        for index in range(256):
            value = [value] if index % 2 else {"inner": value}
        with self.assertRaises(ValueError):
            check_json_depth(value)
        check_json_depth(value["inner"] if isinstance(value, dict) else value[0])

    def test_the_count_uses_no_recursion(self) -> None:
        # With a limit far above the recursion limit of Python: under the
        # limit of 256, a count by recursion would stop before it.
        deep = nested(100_000)
        check_json_depth(deep, limit=100_000)
        with self.assertRaises(ValueError):
            check_json_depth(deep, limit=99_999)
        with self.assertRaises(ValueError):
            check_json_depth(deep)

    def test_a_large_shallow_value_is_counted_fast(self) -> None:
        records = [{"activityId": index, "laps": [{"distance": 1.0}, {"distance": 2.0}]} for index in range(200_000)]
        started = time.perf_counter()
        check_json_depth(records)
        self.assertLess(time.perf_counter() - started, 5.0)


class ReadersTest(unittest.TestCase):
    def test_a_json_file_of_an_export_is_checked_before_its_repair(self) -> None:
        deep = SimpleNamespace(data=nested_text(300, LONE_SURROGATE).encode())
        with mock.patch.object(discovery, "repair_json_text", side_effect=AssertionError("repaired before the check")):
            self.assertEqual(discovery._read_json(deep), (False, None))
        within = SimpleNamespace(data=nested_text(256, LONE_SURROGATE).encode())
        readable, value = discovery._read_json(within)
        self.assertTrue(readable)
        self.assertEqual(within._repaired_text_count, 1)

    def test_a_stored_copy_of_a_snapshot_is_checked_before_its_repair(self) -> None:
        repair = merge.repair_json_text

        def repair_only_what_was_checked(text: str, value: Any) -> Any:
            try:
                check_json_depth(value)
            except ValueError:
                raise AssertionError("repaired before the check") from None
            return repair(text, value)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = export(root / "export")
            write(source / "DI-Connect-Aggregator/UDSFile_deep.json", nested_text(300, LONE_SURROGATE).encode())
            with mock.patch.object(merge, "repair_json_text", side_effect=repair_only_what_was_checked):
                output = one_snapshot(root, source)
            self.assertIn(
                ("DI-Connect-Aggregator/UDSFile_deep.json", "json_not_readable"),
                [(item["source_path"], item["reason"]) for item in listed(output, "files_left_out")],
            )

    def test_an_account_file_more_than_256_deep_names_no_account(self) -> None:
        name = "DI-Connect-Aggregator/UDSFile_accounts.json"
        shallow = json.dumps([{"userProfileId": 123456}])
        self.assertTrue(accounts.account_values([(name, shallow.encode())]))
        deep = shallow[:-2] + ', "padding": ' + nested_text(300) + "}]"
        self.assertEqual(accounts.account_values([(name, deep.encode())]), set())

    def test_a_store_above_more_than_256_deep_is_no_store(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            holder = Path(directory) / "holder"
            inside = holder / "inside"
            inside.mkdir(parents=True)
            metadata = holder / "store.json"
            metadata.write_text(json.dumps({"format": store.STORE_FORMAT}), encoding="utf-8")
            self.assertTrue(store._store_above(inside))
            metadata.write_text(
                '{"format": "%s", "padding": %s}' % (store.STORE_FORMAT, nested_text(300)), encoding="utf-8"
            )
            self.assertFalse(store._store_above(inside))


if __name__ == "__main__":
    unittest.main()
