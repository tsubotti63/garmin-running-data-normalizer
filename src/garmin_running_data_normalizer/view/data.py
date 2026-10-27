"""What the view page reads of an output (stage G1).

The page shows the numbers of an output that this version made: how
normalization makes the numbers can change between versions. Before it reads
one, it checks it with the checks of the GUI (``checked_output``), which stop
for an output of another version with OUTPUT_OTHER_VERSION; an output of 1.3
passes them, and is refused with SERIES_OUTPUT_OTHER_VERSION, which the
series command gives as well (stage G2).

It keeps the bytes of run_manifest.json that it read before the checks, and
reads each file once, comparing its size and SHA-256 with that manifest. A
file, or the manifest, that changed after the checks stops the reading with
OUTPUT_CHANGED, rather than being read as checked. A file over the limits is
not read, and stops the reading with OUTPUT_NOT_AVAILABLE, as a manifest over
its limit does.

Of each file, only the dates and the values of the items are kept, in small
rows. A row without a date, and a row with a date after today in the output's
timezone, are counted and left out of the numbers: one date far ahead, from
a wrong clock, would stretch all the time of the output and leave its last
years empty.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from .. import __version__
from ..common.json_depth import check_json_depth
from ..common.time import TimezoneDataUnavailableError, TimezoneNameInvalidError, require_timezone_data
from ..output_check import OutputActionError, checked_output
from ..standalone import VERSION_FORM
from .items import ACTIVITIES, DATASETS, Dataset, dataset_fields

MANIFEST = "run_manifest.json"
# The manifest lists every file of the Export that the run read, so it grows
# with the Export; the checks read it whole as well.
MAX_MANIFEST_BYTES = 256 * 1024 * 1024
# The limits of what is read: one file, as one FIT file or one file in a ZIP
# file, and all the files of the page together.
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
DATE_FORM = re.compile(r"\d{4}-\d{2}-\d{2}")
# What a sleep needs to be used (wellness_metrics.md in the docs).
SLEEP_USED_STATUS = "available"
SLEEP_USED_FLAG = "sleep_source_available_for_analysis_flag"
SLEEP_REVIEW_STATUS = "needs_review"
# Windows marks junctions and links as reparse points.
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)


@dataclass(frozen=True, slots=True)
class Row:
    """A row that the view page keeps: the ordinal of its date, the values of
    the items as numbers or None, the fields whose values disagreed, and what
    else its file needs (``marks``): the activity type, the use of a sleep,
    the time and series of a record."""

    day: int
    values: dict[str, float | None]
    disagree: frozenset[str]
    marks: dict[str, Any]


@dataclass(frozen=True)
class ViewData:
    """The rows of one output that the view page reads, by file, sorted by
    their dates, and the rows that it left out: without a date, and after
    ``today``. The first and last days are those of all the rows kept;
    ``partial`` marks an output normalized with part of the input left out
    (exit code 3), which the view page says (stage G3b)."""

    version: str
    timezone: str
    today: int
    rows: dict[str, tuple[Row, ...]]
    no_date: dict[str, int]
    after_today: dict[str, int]
    first_day: int | None
    last_day: int | None
    partial: bool = False


def load_view_data(
    output: Path,
    *,
    today: date | None = None,
    max_file_bytes: int = MAX_FILE_BYTES,
    max_total_bytes: int = MAX_TOTAL_BYTES,
) -> ViewData:
    """Check an output as the GUI checks it, and read what the view page
    shows of it. ``today`` is the date of this computer in the output's
    timezone unless given. A check that fails raises ``OutputActionError``."""
    output = Path(output)
    kept = _plain_bytes(output / MANIFEST, MAX_MANIFEST_BYTES)
    handoff, report, legacy = checked_output(output)
    version = report.get("product_version")
    if legacy or version != __version__:
        named = version if isinstance(version, str) and VERSION_FORM.fullmatch(version) else None
        raise OutputActionError("SERIES_OUTPUT_OTHER_VERSION", named)
    # The manifest of the checks, unchanged since before them; the sizes and
    # the hashes come from it, never from a manifest read again.
    if kept is None:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE" if _over(output / MANIFEST, MAX_MANIFEST_BYTES) else "OUTPUT_CHANGED")
    if _plain_bytes(output / MANIFEST, MAX_MANIFEST_BYTES) != kept:
        raise OutputActionError("OUTPUT_CHANGED")
    manifest = _json_value(kept)
    if not isinstance(manifest, dict) or manifest.get("product_version") != version:
        raise OutputActionError("OUTPUT_CHANGED")
    timezone = manifest.get("local_timezone")
    if not isinstance(timezone, str):
        raise OutputActionError("OUTPUT_CHANGED")
    entries = _manifest_entries(manifest)
    sizes = [entries[dataset.path][0] for dataset in DATASETS]
    if any(size > max_file_bytes for size in sizes) or sum(sizes) > max_total_bytes:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE")
    day_today = (local_today(timezone) if today is None else today).toordinal()
    rows: dict[str, tuple[Row, ...]] = {}
    no_date: dict[str, int] = {}
    after_today: dict[str, int] = {}
    for dataset in DATASETS:
        data = _checked_bytes(output, dataset.path, *entries[dataset.path])
        records = _activity_records(data) if dataset.name == ACTIVITIES else _json_records(data)
        kept_rows, no_date[dataset.name], after_today[dataset.name] = _rows(dataset, records, day_today)
        rows[dataset.name] = kept_rows
    days = [row.day for kept_rows in rows.values() for row in kept_rows]
    return ViewData(
        version=version,
        timezone=timezone,
        today=day_today,
        rows=rows,
        no_date=no_date,
        after_today=after_today,
        first_day=min(days) if days else None,
        last_day=max(days) if days else None,
        partial=handoff.get("run_status") == "PARTIAL_SUCCESS",
    )


def _is_plain_file(path: Path) -> bool:
    """Whether ``path`` is a file itself, not a link or a junction."""
    status = os.lstat(path)
    return stat.S_ISREG(status.st_mode) and not getattr(status, "st_file_attributes", 0) & _REPARSE_POINT


def _plain_bytes(path: Path, limit: int) -> bytes | None:
    """The bytes of a plain file of at most ``limit`` bytes, or None."""
    try:
        if not _is_plain_file(path):
            return None
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError:
        return None
    return data if len(data) <= limit else None


def _over(path: Path, limit: int) -> bool:
    """Whether ``path`` is a plain file of more than ``limit`` bytes."""
    try:
        return _is_plain_file(path) and os.lstat(path).st_size > limit
    except OSError:
        return False


def _json_value(data: bytes) -> Any:
    """The JSON of a file of the output; one that is not JSON, or nests too
    deeply, means that the output changed."""
    try:
        value = json.loads(data.decode("utf-8"))
        check_json_depth(value)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise OutputActionError("OUTPUT_CHANGED") from exc
    return value


def _manifest_entries(manifest: dict[str, Any]) -> dict[str, tuple[int, str]]:
    """The size and SHA-256 that the manifest gives each file that the view
    page reads."""
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list):
        raise OutputActionError("OUTPUT_CHANGED")
    entries: dict[str, tuple[int, str]] = {}
    for item in outputs:
        if not isinstance(item, dict):
            raise OutputActionError("OUTPUT_CHANGED")
        path, size, digest = item.get("path"), item.get("bytes"), item.get("sha256")
        if isinstance(path, str) and isinstance(size, int) and not isinstance(size, bool) and size >= 0 and isinstance(digest, str):
            entries[path] = (size, digest)
    if any(dataset.path not in entries for dataset in DATASETS):
        raise OutputActionError("OUTPUT_CHANGED")
    return entries


def _checked_bytes(output: Path, relative: str, size: int, digest: str) -> bytes:
    """Read a file once, at most one byte more than the manifest gives, and
    compare it with the manifest."""
    path = output.joinpath(*PurePosixPath(relative).parts)
    try:
        if not _is_plain_file(path):
            raise OutputActionError("OUTPUT_NOT_AVAILABLE")
        with path.open("rb") as handle:
            data = handle.read(size + 1)
    except OSError as exc:
        raise OutputActionError("OUTPUT_NOT_AVAILABLE") from exc
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise OutputActionError("OUTPUT_CHANGED")
    return data


def local_today(timezone: str) -> date:
    """The date of this computer in ``timezone``: the rows after it are left
    out, and the view page reads an output again when it changes (stage
    G3b)."""
    try:
        zone = require_timezone_data(timezone)
    except TimezoneDataUnavailableError as exc:
        raise OutputActionError(exc.code) from exc
    except TimezoneNameInvalidError as exc:
        raise OutputActionError("OUTPUT_CHANGED") from exc
    return datetime.now(zone).date()


def _activity_records(data: bytes) -> list[dict[str, Any]]:
    """The rows of analysis/activities.csv, as text, with the field names of
    a cell of ``disagreeing_fields`` split at ``;``."""
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""))
        needed = {"activity_date_local", "activity_type", "disagreeing_fields", *dataset_fields(ACTIVITIES)}
        if reader.fieldnames is None or not needed <= set(reader.fieldnames):
            raise OutputActionError("OUTPUT_CHANGED")
        records = []
        for record in reader:
            cell = record.get("disagreeing_fields") or ""
            records.append({**record, "disagreeing_fields": [name for name in cell.split(";") if name]})
    except (UnicodeDecodeError, csv.Error) as exc:
        raise OutputActionError("OUTPUT_CHANGED") from exc
    return records


def _json_records(data: bytes) -> list[dict[str, Any]]:
    records = _json_value(data)
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise OutputActionError("OUTPUT_CHANGED")
    return records


def _day(value: Any) -> int | None:
    if not isinstance(value, str) or not DATE_FORM.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value).toordinal()
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    """A finite number of a JSON value, or of a cell of the CSV file; an
    empty cell, text, and a value that is not finite are None."""
    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            number = float(value) if value else None
        elif isinstance(value, (int, float)):
            number = float(value)
        else:
            return None
    except (ValueError, OverflowError):
        return None
    return number if number is not None and math.isfinite(number) else None


def _rows(dataset: Dataset, records: list[dict[str, Any]], today: int) -> tuple[tuple[Row, ...], int, int]:
    """The rows of a file that the view page keeps, sorted by date and then
    by the time of the record, and the counts of the rows without a date and
    after today."""
    fields = dataset_fields(dataset.name)
    kept: list[tuple[int, str, Row]] = []
    no_date = after_today = 0
    for record in records:
        day = _day(record.get(dataset.date_field))
        if day is None:
            no_date += 1
            continue
        if day > today:
            after_today += 1
            continue
        names = record.get("disagreeing_fields")
        disagree = frozenset(name for name in names if isinstance(name, str)) if isinstance(names, list) else frozenset()
        marks: dict[str, Any] = {}
        if dataset.name == ACTIVITIES:
            marks["type"] = record.get("activity_type") or ""
        if dataset.name == "sleep_daily":
            status = record.get("sleep_normalization_status")
            marks["used"] = status == SLEEP_USED_STATUS and record.get(SLEEP_USED_FLAG) is True
            marks["review"] = status == SLEEP_REVIEW_STATUS
        time = ""
        if dataset.observed:
            time = record.get("observation_timestamp") if isinstance(record.get("observation_timestamp"), str) else ""
            marks["time"] = time
        if dataset.series:
            marks["series"] = tuple(str(record.get(name) or "") for name in dataset.series)
        values = {name: _number(record.get(name)) for name in fields}
        kept.append((day, time, Row(day, values, disagree, marks)))
    kept.sort(key=lambda entry: (entry[0], entry[1]))
    return tuple(row for _day_, _time, row in kept), no_date, after_today


__all__ = [
    "MANIFEST",
    "MAX_FILE_BYTES",
    "MAX_TOTAL_BYTES",
    "Row",
    "ViewData",
    "load_view_data",
    "local_today",
]
