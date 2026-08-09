from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "validate_platform_alignment.py"
RECORD_PATH = ROOT / "docs" / "reference" / "platform_standard_adoption_v0_9.json"

SPEC = importlib.util.spec_from_file_location("validate_platform_alignment", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class PlatformAlignmentOwnershipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))

    def test_current_ownership_model_passes(self) -> None:
        result = VALIDATOR.validate(self.record)

        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(
            sorted(VALIDATOR.PRODUCT_OWNED_ENTRYPOINT_OVERRIDES),
            result["product_owned_entrypoint_overrides"],
        )
        self.assertTrue(result["historical_standard_baseline_evidence_preserved"])

    def test_historical_baseline_hashes_are_preserved(self) -> None:
        baselines = {entry["path"]: entry for entry in self.record["standard_files"]}

        for override in self.record["product_owned_entrypoint_overrides"]:
            baseline = baselines[override["path"]]
            expected = VALIDATOR.PRODUCT_OWNED_ENTRYPOINT_BASELINES[override["path"]]
            self.assertEqual(expected["bytes"], baseline["bytes"])
            self.assertEqual(expected["sha256"], baseline["sha256"])
            self.assertEqual(baseline["bytes"], override["baseline_bytes"])
            self.assertEqual(baseline["sha256"], override["baseline_sha256"])

            current = (ROOT / override["path"]).read_bytes()
            self.assertNotEqual(baseline["sha256"], hashlib.sha256(current).hexdigest())

    def test_unapproved_override_fails_closed(self) -> None:
        record = copy.deepcopy(self.record)
        record["product_owned_entrypoint_overrides"].append({
            "baseline_bytes": 0,
            "baseline_sha256": "0" * 64,
            "ownership": "product",
            "path": "README.md",
            "reason": "Unapproved",
        })

        result = VALIDATOR.validate(record)

        self.assertEqual("FAIL", result["status"])
        self.assertIn(
            "unapproved override: README.md",
            result["invalid_product_owned_entrypoint_overrides"],
        )

    def test_changed_baseline_evidence_fails_closed(self) -> None:
        record = copy.deepcopy(self.record)
        record["product_owned_entrypoint_overrides"][0]["baseline_sha256"] = "0" * 64

        result = VALIDATOR.validate(record)

        self.assertEqual("FAIL", result["status"])
        self.assertTrue(
            any(
                "baseline SHA-256 does not match Standard evidence" in issue
                or "baseline SHA-256 does not match approved evidence" in issue
                for issue in result["invalid_product_owned_entrypoint_overrides"]
            )
        )


if __name__ == "__main__":
    unittest.main()
