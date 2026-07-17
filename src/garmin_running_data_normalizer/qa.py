from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from typing import Any


def deterministic_records_digest(records: Iterable[dict[str, Any]]) -> str:
    canonical = sorted(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        for record in records
    )
    return hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest()


def summarize_records(records: Iterable[dict[str, Any]], *, key_field: str) -> dict[str, Any]:
    rows = list(records)
    keys = [row.get(key_field) for row in rows]
    missing = sum(value in (None, "") for value in keys)
    duplicates = sum(max(count - 1, 0) for count in Counter(str(value) for value in keys if value not in (None, "")).values())
    serializable = True
    try:
        json.dumps(rows, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        serializable = False
    status = "PASS" if not missing and not duplicates and serializable else "FAIL"
    return {
        "status": status,
        "record_count": len(rows),
        "missing_key_count": missing,
        "duplicate_key_count": duplicates,
        "json_serializable": serializable,
        "records_sha256": deterministic_records_digest(rows),
    }
