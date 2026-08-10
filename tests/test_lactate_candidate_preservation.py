from __future__ import annotations

import itertools
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from garmin_running_data_normalizer.run_all import run_all
from garmin_running_data_normalizer.snapshot.merge import (
    _lactate_malformed_conflicts,
    _lactate_power_conflicts,
    _merge_dataset,
)


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "examples/synthetic/garmin_export"


def _observation(
    power: object,
    *,
    snapshot: int = 1,
    family: str = "profile_state",
    timestamp: str | None = None,
    record_override: dict[str, object] | None = None,
) -> dict[str, object]:
    record: dict[str, object] = (
        {"functionalThresholdPower": power}
        if record_override is None
        else dict(record_override)
    )
    if timestamp is not None:
        record["metaData"] = {"calendarDate": timestamp}
    raw_key = (family, json.dumps(record, sort_keys=True, separators=(",", ":")))
    return {
        "dataset": "lactate_threshold_candidates",
        "record": record,
        "raw_key": raw_key,
        "snapshot_id": f"snapshot-{snapshot}",
        "logical_order": snapshot,
        "export_observed_at": f"2030-01-0{snapshot}T00:00:00+00:00",
        "source_relative_path": f"synthetic-{family}-{snapshot}.json",
        "source_record_index": 0,
        "source_object_sha256": f"source-{snapshot}",
    }


def _merge(observations: list[dict[str, object]]) -> tuple[list[dict], dict, list[dict]]:
    canonical, _provenance, _field_provenance, holds, conflicts, summary = _merge_dataset(
        "lactate_threshold_candidates", observations, 4
    )
    return canonical, summary, holds + conflicts


class LactateCandidatePreservationTest(unittest.TestCase):
    def test_18_case_matrix(self) -> None:
        cases = {
            "one_candidate": [_observation(100)],
            "two_exact_repeats": [_observation(100), _observation(100, snapshot=2)],
            "three_exact_repeats": [
                _observation(100), _observation(100, snapshot=2), _observation(100, snapshot=3)
            ],
            "two_distinct_valid": [_observation(100), _observation(110, snapshot=2)],
            "three_distinct_valid": [
                _observation(100), _observation(110, snapshot=2), _observation(120, snapshot=3)
            ],
            "repeats_plus_distinct": [
                _observation(100), _observation(100, snapshot=2), _observation(110, snapshot=3)
            ],
            "same_candidate_across_snapshots": [
                _observation(100, snapshot=1), _observation(100, snapshot=4)
            ],
            "distinct_candidates_across_snapshots": [
                _observation(100, snapshot=1), _observation(110, snapshot=4)
            ],
            "missing_reappearance": [
                _observation(100, snapshot=1), _observation(100, snapshot=3)
            ],
            "input_order_permutation": [
                _observation(100, snapshot=1), _observation(110, snapshot=2)
            ],
            "malformed_type": [_observation("not-a-number")],
            "malformed_structure": [
                _observation(None, record_override={"functionalThresholdPower": {"bad": True}})
            ],
            "authority_unresolved": [_observation(100), _observation(110, snapshot=2)],
            "stable_promotion_blocked": [_observation(100)],
            "no_winner": [_observation(100), _observation(110, snapshot=2)],
            "candidate_output_available": [_observation(100), _observation(110, snapshot=2)],
            "run_all_warning_nonfatal": [_observation(100), _observation(110, snapshot=2)],
            "existing_lactate_contract": [_observation(100)],
        }
        self.assertEqual(len(cases), 18)

        for name, observations in cases.items():
            if name in {"malformed_type", "malformed_structure"}:
                malformed = _lactate_malformed_conflicts(observations)
                self.assertEqual(len(malformed), 1, name)
                self.assertEqual(malformed[0]["severity"], "stop")
                continue
            canonical, summary, _holds = _merge(observations)
            self.assertGreaterEqual(len(canonical), 1, name)
            self.assertFalse(any("winner" in row for row in canonical), name)
            self.assertFalse(summary.get("automatic_winner", False), name)

        distinct = [_observation(100), _observation(110, snapshot=2)]
        _canonical, summary, reviews = _merge(distinct)
        review = _lactate_power_conflicts(distinct)
        self.assertEqual(len(review), 1)
        self.assertEqual(review[0]["severity"], "review")
        self.assertEqual(review[0]["candidate_status"], "multiple_observed_candidates")
        self.assertEqual(summary["canonical_record_count"], 2)
        self.assertEqual(len(reviews), 0)

    def test_snapshot_order_permutations_preserve_candidate_contract(self) -> None:
        base = [
            _observation(100, snapshot=1),
            _observation(100, snapshot=2),
            _observation(110, snapshot=3),
            _observation(100, snapshot=4),
        ]
        expected: tuple[set[str], tuple[int, int, int, int]] | None = None
        for order in itertools.permutations(range(4)):
            observations = [dict(base[index]) for index in order]
            canonical, summary, _ = _merge(observations)
            signatures = {
                json.dumps(row["raw_record"], sort_keys=True, separators=(",", ":"))
                for row in canonical
            }
            result = (
                signatures,
                (
                    int(summary["canonical_record_count"]),
                    int(summary["source_observation_count"]),
                    len(_lactate_power_conflicts(observations)),
                    int(summary["exact_repeat_count"]),
                ),
            )
            reviews = _lactate_power_conflicts(observations)
            self.assertEqual(
                (
                    reviews[0]["candidate_status"],
                    reviews[0]["authority_status"],
                    reviews[0]["stable_promotion_available"],
                ),
                ("multiple_observed_candidates", "unresolved", False),
            )
            expected = result if expected is None else expected
            self.assertEqual(result, expected)
        self.assertEqual(len(list(itertools.permutations(range(4)))), 24)

    def test_run_all_with_multiple_candidates_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_root = root / "input"
            shutil.copytree(SYNTHETIC, input_root)
            wellness = input_root / "DI-Connect-Wellness"
            wellness.mkdir()
            (wellness / "synthetic_userBioMetricProfileData.json").write_text(
                json.dumps(
                    [
                        {"functionalThresholdPower": 100},
                        {"functionalThresholdPower": 110},
                    ]
                ),
                encoding="utf-8",
            )
            result = run_all(input_root, root / "output")
            self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
            summary = json.loads(
                (root / "output" / "run_summary.json").read_text(encoding="utf-8")
            )
            candidate = summary["candidate_features"]["lactate_threshold"]
            self.assertFalse(candidate["public_promotion"])
            self.assertIn(
                "LACTATE_CANDIDATE_AUTHORITY_UNRESOLVED",
                {item["code"] for item in summary["warnings"]},
            )
            self.assertEqual(
                json.loads(
                    (root / "output" / "audit/lactate_threshold_candidates.json").read_text(
                        encoding="utf-8"
                    )
                )["public_promotion"],
                False,
            )


if __name__ == "__main__":
    unittest.main()
