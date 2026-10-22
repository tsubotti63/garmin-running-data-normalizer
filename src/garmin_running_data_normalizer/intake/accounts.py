"""Tell whether the records of an Export belong to one account.

Some files of an Export name the account that owns their records: Activities
with ``userProfileId``, Gear and the daily metrics with ``userProfilePk`` or
``userProfilePK``. Only these files are used: other files of an Export, such
as those about connections, groups, or challenges, name other people's
accounts. The values are compared within the run only and are never written
to an output.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from ..common.identity import identity_token
from ..common.json_depth import check_json_depth
from ..normalizers.source_records import is_mark

ACCOUNT_FIELDS = frozenset({"userProfileId", "userProfilePk", "userProfilePK"})
# Source families whose records name the account that owns them.
ACCOUNT_FAMILIES = frozenset(
    {
        "activities",
        "gear",
        "hill_score",
        "endurance_score",
        "race_prediction",
        "uds",
        "acute_training_load",
        "training_readiness",
        "vo2max",
        "training_history",
    }
)


def _account(value: Any) -> str | None:
    # Read as every identifier is (stage A3d-1b): a text of more digits than a
    # run reads names no account, instead of stopping the run.
    return identity_token(value)


def _records(value: Any) -> list[dict[str, Any]]:
    """The records of a file: the objects in its top list (or the top object),
    and the objects in the lists that those hold, as Activities and Gear do."""
    tops = [value] if isinstance(value, dict) else value if isinstance(value, list) else []
    records: list[dict[str, Any]] = []
    for item in tops:
        # The mark of an item that is not a record, which a Snapshot build
        # writes in its place (stage A3d-2c-2), is no record: its value is
        # not read, as the item itself is not.
        if not isinstance(item, dict) or is_mark(item):
            continue
        records.append(item)
        for inner in item.values():
            if isinstance(inner, list):
                records.extend(entry for entry in inner if isinstance(entry, dict))
    return records


def names_account(logical_name: str) -> bool:
    """Whether a JSON file is of a kind whose records name their account."""
    from ..diagnostics.detector import classify_source_name

    return classify_source_name(logical_name, "json") in ACCOUNT_FAMILIES


def payload_accounts(payload: Any) -> set[str]:
    """Return the accounts that the records of one parsed JSON file name."""
    found: set[str] = set()
    for record in _records(payload):
        for key in ACCOUNT_FIELDS & record.keys():
            account = _account(record[key])
            if account is not None:
                found.add(account)
    return found


def account_values(files: Iterable[tuple[str, bytes]]) -> set[str]:
    """Return the accounts that the given JSON files name, as (logical name, content).

    Files outside the account families, and files that cannot be read as JSON,
    are passed over; the run leaves them out (stage A3c).
    """
    found: set[str] = set()
    for logical_name, data in files:
        if not names_account(logical_name):
            continue
        try:
            payload = json.loads(data.decode("utf-8-sig"))
            check_json_depth(payload)
        except (UnicodeError, ValueError, RecursionError):
            # The same errors as the run leaves a file out for: not UTF-8,
            # not JSON, nested too deeply, or a number with too many digits.
            continue
        found |= payload_accounts(payload)
    return found


def asset_accounts(assets: Iterable[Any]) -> set[str]:
    """Return the accounts that the JSON files of an open Export reading name.

    Only the files whose records name their account are read again.
    """
    return account_values(
        (asset.member_path or asset.source_path, asset.data)
        for asset in assets
        if asset.kind == "json" and names_account(asset.member_path or asset.source_path)
    )


__all__ = [
    "ACCOUNT_FAMILIES",
    "ACCOUNT_FIELDS",
    "account_values",
    "asset_accounts",
    "names_account",
    "payload_accounts",
]
