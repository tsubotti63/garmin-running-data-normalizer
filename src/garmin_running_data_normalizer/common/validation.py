from __future__ import annotations

from collections.abc import Iterable, Mapping


def require_fields(record: Mapping[str, object], required: Iterable[str]) -> None:
    missing = sorted(set(required) - set(record))
    if missing:
        raise ValueError(f"Missing required fields: {missing}")


def require_unique(records: Iterable[Mapping[str, object]], fields: Iterable[str]) -> None:
    field_names = tuple(fields)
    seen: set[tuple[object, ...]] = set()
    for record in records:
        key = tuple(record.get(field) for field in field_names)
        if key in seen:
            raise ValueError(f"Duplicate key for fields {field_names}: {key}")
        seen.add(key)
