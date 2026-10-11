"""Write the v1.7.1 Snapshot Store fixture from synthetic Exports.

The fixture keeps a Snapshot Store exactly as version 1.7.1 wrote it, so that
tests can check that later versions read it without migration and use every
Snapshot. Run this script only with garmin-running-data-normalizer 1.7.1
installed, for example from PyPI in a new virtual environment:

    python tests/fixtures/snapshot_store_v1_7_1/make_store.py \\
        tests/fixtures/snapshot_store_v1_7_1/store_files.json

The store records fixed times, so version 1.7.1 writes the same bytes each
time. The store's files are written into one JSON document, text files as
text and other files in Base64, with their modes, so that the fixture can be
read and scanned like the rest of the repository. Every value is synthetic.
"""

from __future__ import annotations

import base64
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

import garmin_running_data_normalizer
from garmin_running_data_normalizer.snapshot import (
    initialize_store,
    register_snapshot,
    run_snapshot_all,
    verify_store,
)

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY))
from tests.fit_fixture_factory import synthetic_fit  # noqa: E402

VERSION = "1.7.1"
ACCOUNT_STORE_ID = "synthetic-account-boundary"
STORE_TIME = "2030-01-20T00:00:00+00:00"
ZIP_TIME = (2030, 1, 20, 0, 0, 0)
DESCRIPTION = (
    "The files of a Snapshot Store that garmin-running-data-normalizer 1.7.1 "
    "wrote from synthetic Exports; see README.md."
)


def _activity(activity_id: str, name: str, day: int) -> dict[str, object]:
    return {
        "activityId": activity_id,
        "activityType": "running",
        "sportType": "running",
        "distance": 500000,
        "duration": 1800000,
        "startTimeGmt": 1893456000000 + (day - 1) * 86400000,
        "startTimeLocal": f"2030-01-{day:02d}T09:00:00",
        "name": name,
        "synthetic": True,
    }


def _hill_score(day: int) -> dict[str, object]:
    return {
        "calendarDate": f"2030-01-{day:02d}",
        "overallScore": 70 + day,
        "strengthScore": 60 + day,
        "enduranceScore": 80 + day,
        "hillScoreClassificationId": 4,
        "hillScoreFeedbackPhraseId": 12,
    }


def _sleep(day: int) -> dict[str, object]:
    return {
        "calendarDate": f"2030-01-{day:02d}",
        "sleepStartTimestampGMT": f"2030-01-{day - 1:02d}T14:00:00Z",
        "sleepEndTimestampGMT": f"2030-01-{day - 1:02d}T22:00:00Z",
        "sleepTimeSeconds": 27000 + day,
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_export(
    root: Path,
    activities: list[dict[str, object]],
    gear_links: list[str],
    days: list[int],
) -> None:
    """Write one synthetic Export in the layout of a real one."""
    connect = root / "DI_CONNECT"
    fitness = connect / "DI-Connect-Fitness"
    _write_json(
        fitness / "synthetic_summarizedActivities.json",
        [{"summarizedActivitiesExport": activities}],
    )
    _write_json(
        fitness / "synthetic_gear.json",
        {
            "gearDTOS": [{"gearPk": "SYNTHETIC-GEAR-1", "displayName": "Synthetic Shoe"}],
            "gearActivityDTOs": {
                "SYNTHETIC-GEAR-1": [{"activityId": item} for item in gear_links]
            },
        },
    )
    _write_json(
        fitness / "synthetic_personalRecord.json",
        {
            "personalRecords": [
                {
                    "personalRecordId": "SYNTHETIC-PR-1",
                    "activityId": "SYNTHETIC-A1",
                    "personalRecordType": "synthetic_best",
                }
            ]
        },
    )
    uploaded = connect / "DI-Connect-Uploaded-Files"
    uploaded.mkdir(parents=True)
    archive_path = uploaded / "UploadedFiles_synthetic_Part1.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo("synthetic-session-1.fit", date_time=ZIP_TIME)
        archive.writestr(info, synthetic_fit())
    _write_json(
        connect / "DI-Connect-Metrics" / "HillScore_synthetic.json",
        [_hill_score(day) for day in days],
    )
    _write_json(
        connect / "DI-Connect-Wellness" / "synthetic_sleepData.json",
        [_sleep(day) for day in days],
    )
    (root / "synthetic-readme.txt").write_text("synthetic\n", encoding="utf-8")


def _register(store: Path, source: Path, label: str, day: int) -> None:
    register_snapshot(
        store,
        source,
        snapshot_label=label,
        export_requested_at=f"2030-01-{day:02d}T00:00:00+00:00",
        export_downloaded_at=f"2030-01-{day:02d}T01:00:00+00:00",
        export_observed_at=f"2030-01-{day:02d}T02:00:00+00:00",
        confirm_complete=True,
    )


def _entry(path: Path, relative: str) -> dict[str, str]:
    entry = {"path": relative, "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}
    if path.is_dir():
        return entry
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is not None and all(character.isprintable() or character in "\n\t" for character in text):
        entry["text"] = text
    else:
        entry["base64"] = base64.b64encode(data).decode("ascii")
    return entry


def _write_fixture(store: Path, output: Path) -> None:
    """Write the store's folders and files, with their modes, as one JSON document."""
    entries = [
        _entry(path, path.relative_to(store).as_posix()) for path in sorted(store.rglob("*"))
    ]
    document = {"description": DESCRIPTION, "entries": entries}
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    if garmin_running_data_normalizer.__version__ != VERSION:
        print(f"run this script with version {VERSION} installed", file=sys.stderr)
        return 2
    output = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as directory, mock.patch(
        "garmin_running_data_normalizer.snapshot.store._now_utc",
        return_value=STORE_TIME,
    ):
        root = Path(directory)
        store = root / "store"
        initialize_store(store, ACCOUNT_STORE_ID)
        first = root / "export-1"
        _write_export(
            first,
            [
                _activity("SYNTHETIC-A1", "Synthetic A1", 1),
                _activity("SYNTHETIC-A2", "Synthetic A2 before", 1),
            ],
            ["SYNTHETIC-A1"],
            [2],
        )
        _register(store, first, "S1", 1)
        second = root / "export-2"
        _write_export(
            second,
            [
                _activity("SYNTHETIC-A2", "Synthetic A2 after", 1),
                _activity("SYNTHETIC-A3", "Synthetic A3", 2),
            ],
            ["SYNTHETIC-A3"],
            [2, 3],
        )
        _register(store, second, "S2", 2)
        if verify_store(store)["status"] != "PASS":
            print("the store failed verification", file=sys.stderr)
            return 2
        run_snapshot_all(store, root / "output")
        _write_fixture(store, output)
    print(f"wrote {output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
