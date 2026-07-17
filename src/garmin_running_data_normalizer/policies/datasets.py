from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ALLOWED_MERGE_MODES = {
    "entity_upsert", "temporal_event_union", "immutable_blob_union", "preserve_only",
}
REQUIRED_FIELDS = {
    "name", "source_family", "record_grain", "stable_key", "merge_policy", "provenance_required",
}


def load_registry(path: str | Path) -> tuple[dict[str, Any], str]:
    data = Path(path).read_bytes()
    return json.loads(data.decode("utf-8")), hashlib.sha256(data).hexdigest()


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if registry.get("status") != "local_implementation_not_publication_ready":
        errors.append("registry status is not the local implementation status")
    datasets = registry.get("datasets")
    if not isinstance(datasets, list):
        return {"status": "FAIL", "dataset_count": 0, "errors": ["datasets must be a list"]}
    names: list[str] = []
    for index, policy in enumerate(datasets):
        if not isinstance(policy, dict):
            errors.append(f"dataset {index} is not an object")
            continue
        missing = sorted(REQUIRED_FIELDS - set(policy))
        if missing:
            errors.append(f"dataset {index} missing fields: {missing}")
            continue
        name = str(policy["name"])
        names.append(name)
        if policy["source_family"] != "garmin_account_export":
            errors.append(f"{name}: source_family must be garmin_account_export")
        if policy["merge_policy"] not in ALLOWED_MERGE_MODES:
            errors.append(f"{name}: unsupported merge_policy")
        if policy["merge_policy"] != "preserve_only" and not policy["stable_key"]:
            errors.append(f"{name}: stable_key must not be empty")
        if policy["provenance_required"] is not True:
            errors.append(f"{name}: provenance_required must be true")
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate dataset names: {duplicates}")
    return {"status": "PASS" if not errors else "FAIL", "dataset_count": len(datasets), "errors": errors}


def _is_null(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _canonical(value: Any) -> str:
    return "<NULL>" if _is_null(value) else json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _signature(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def inspect_records(
    records: Iterable[dict[str, Any]],
    *,
    stable_key: list[str],
    update_order: list[str] | None = None,
) -> dict[str, Any]:
    rows = list(records)
    order_fields = update_order or []
    keyed: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    null_key_rows = 0
    signatures = Counter(_signature(row) for row in rows)
    for row in rows:
        raw_key = [row.get(field) for field in stable_key]
        if any(_is_null(value) for value in raw_key):
            null_key_rows += 1
        else:
            keyed[tuple(_canonical(value) for value in raw_key)].append(row)
    duplicate_groups = 0
    ordered_update_groups = 0
    unresolved_conflict_groups = 0
    for group in keyed.values():
        if len(group) <= 1:
            continue
        duplicate_groups += 1
        if len({_signature(row) for row in group}) == 1:
            continue
        if not order_fields:
            unresolved_conflict_groups += 1
            continue
        orders = [tuple(_canonical(row.get(field)) for field in order_fields) for row in group]
        if any(any(row.get(field) is None for field in order_fields) for row in group) or len(set(orders)) != len(orders):
            unresolved_conflict_groups += 1
        else:
            ordered_update_groups += 1
    if unresolved_conflict_groups:
        status = "REVIEW_REQUIRED_UNRESOLVED_KEY_CONFLICT"
    elif null_key_rows:
        status = "WARNING_NULL_KEY_PRESERVED"
    elif ordered_update_groups:
        status = "PASS_ORDERED_UPDATES"
    else:
        status = "PASS"
    return {
        "status": status,
        "record_count": len(rows),
        "null_key_rows": null_key_rows,
        "unique_non_null_key_count": len(keyed),
        "duplicate_key_groups": duplicate_groups,
        "exact_duplicate_extra_rows": sum(max(count - 1, 0) for count in signatures.values()),
        "ordered_update_groups": ordered_update_groups,
        "unresolved_conflict_groups": unresolved_conflict_groups,
    }
