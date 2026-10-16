"""What each stop means and what to do next, by code (stage A5b).

Every ``ERROR`` line of the CLI reads ``ERROR [CODE]: <what happened>; <next
step>``. The message of the stop says what happened, with the details that it
may give, such as the place inside the input that cannot be opened; the next
step comes from this table, so that it is the same wherever a command stops
with the code. ``what`` gives the meaning of the code in one sentence, for the
documents and for the texts of the GUI.

The texts are fixed: they never name a folder, a file, an account, or a value.
"""

from __future__ import annotations

from typing import NamedTuple


class Stop(NamedTuple):
    what: str
    next_step: str


# The next steps that several codes share.
_DEFECT = (
    "no output was written; this is a defect of this app, so please report the code"
)
_AGAIN = "run the command again; if it stops again, please report the code"
_NEW_OUTPUT = "do not change the files of an output; run Run-All again into a new folder"
_NOT_READABLE = (
    "allow this app to read it (on a Mac, in System Settings > Privacy & Security; "
    "on Windows, in the Security tab of its Properties)"
)
_STORE_RESTORE = (
    "do not change the files inside the store; restore it from a backup that "
    "passed snapshot verify, or make a new store and register the Exports again"
)
_BUNDLE_REFUSED = "the Support Bundle was not made; please report the code"

STOPS: dict[str, Stop] = {
    # The input.
    "INPUT_SYMLINK": Stop(
        "the input is a symbolic link",
        "select the Export folder or ZIP file itself, not a link to it",
    ),
    "INPUT_NOT_DIRECTORY": Stop(
        "the input is not an existing folder or ZIP file",
        "select the Export folder, or the ZIP file downloaded from Garmin",
    ),
    "INPUT_NOT_READABLE": Stop(
        "this app may not open a folder or file of the input",
        f"{_NOT_READABLE}, or select the Export folder itself",
    ),
    "INPUT_CHANGED": Stop(
        "the input changed while it was read",
        "run the command again when no other program changes the input",
    ),
    "INPUT_ZIP_CORRUPT": Stop(
        "the Export ZIP file is damaged or incomplete",
        "download the Export ZIP file again; if it is damaged again, request a new "
        "Export from Garmin",
    ),
    "INPUT_TOO_LARGE": Stop(
        "the Export ZIP file is too large to read directly",
        "extract it, and select the extracted folder",
    ),
    "INPUT_MULTIPLE_EXPORTS": Stop(
        "the input holds more than one Export, or Exports of more than one account",
        "select one Export, or register each Export into a Snapshot Store for its "
        "own account",
    ),
    "INPUT_DISCOVERY_FAILED": Stop(
        "the input could not be read safely",
        "download or extract the Export again; if it stops again, please report the code",
    ),
    "TEMP_SPACE_INSUFFICIENT": Stop(
        "the temporary folder does not have enough free space",
        "free some space on its drive; an Export ZIP file can also be extracted and "
        "its folder selected",
    ),
    "TIMEZONE_INVALID": Stop(
        "the timezone is not an exact IANA timezone name",
        "give an exact IANA timezone name, such as Asia/Tokyo or America/New_York",
    ),
    "TIMEZONE_DATA_UNAVAILABLE": Stop(
        "the timezone data is not installed",
        "reinstall the package in a clean environment, so that the timezone data is "
        "installed",
    ),
    "ACTIVITIES_NOT_FOUND": Stop(
        "the input holds no Activities file",
        "select an Export that contains your Activities",
    ),
    "ACTIVITIES_EMPTY": Stop(
        "the input holds no Activities record that can be kept",
        "obtain a complete, readable Export that contains your Activities",
    ),
    "GOLDEN_PATH_DATA_NEEDS_RUN_ALL": Stop(
        "the Activities hold data that normalize-activities has no place for",
        "use run-all, which goes on and reports what it leaves out, keeps, or repairs",
    ),
    # The output.
    "OUTPUT_SYMLINK": Stop(
        "the output is a symbolic link",
        "choose a new folder for the output, not a link",
    ),
    "OUTPUT_EXISTS": Stop(
        "the output folder is there already",
        "choose another name for the output",
    ),
    "OUTPUT_INSIDE_INPUT": Stop(
        "the output is inside the input",
        "choose a place for the output outside the Export",
    ),
    "OUTPUT_PARENT_NOT_FOUND": Stop(
        "the folder for the output does not exist or is not a folder",
        "choose an existing folder for the output, or create it first",
    ),
    "OUTPUT_PARENT_NOT_WRITABLE": Stop(
        "this app cannot write in the folder for the output",
        "choose another folder, or allow this app to write in it",
    ),
    "OUTPUT_NAME_INVALID": Stop(
        "the output folder name is too long or cannot be used on every system",
        "choose a name of at most 200 bytes that does not start with a dot, end with "
        'a dot or a space, hold any of <>:"/\\|?*, or name a device of Windows',
    ),
    "OUTPUT_PATH_TOO_LONG": Stop(
        "the output path is too long",
        "choose a shorter folder or name, or on Windows turn on long paths",
    ),
    "OUTPUT_SPACE_INSUFFICIENT": Stop(
        "the place for the output does not have enough free space",
        "free some space, or choose another folder",
    ),
    "OUTPUT_PUBLISH_FAILED": Stop(
        "the output could not be written",
        "check the free space and the permissions of the folder for the output, and "
        "run the command again",
    ),
    # The Snapshot Store.
    "SNAPSHOT_STORE_NOT_WRITABLE": Stop(
        "this app cannot write in the Snapshot Store, or create it there",
        "allow this app to write in its folder, or for a new store choose another "
        "folder; then run the command again",
    ),
    "SNAPSHOT_STORE_SPACE_INSUFFICIENT": Stop(
        "the drive of the Snapshot Store does not have enough free space",
        "free some space, or for a new store choose another folder; then run the "
        "command again",
    ),
    "SNAPSHOT_STORE_LOCKED": Stop(
        "the Snapshot Store has a lock file (.single-writer.lock): a registration is "
        "running, or one stopped before it ended",
        "if no snapshot command is running, delete that file, then run the command again",
    ),
    "SNAPSHOT_REGISTRATION_INCOMPLETE": Stop(
        "a registration in the Snapshot Store was interrupted",
        "register the same Export, or another complete Export, again, which completes "
        "the store",
    ),
    "SNAPSHOT_STORE_NOT_READABLE": Stop(
        "this app may not open a folder or file of the Snapshot Store",
        f"{_NOT_READABLE}; this app must be able to read the whole store folder",
    ),
    "SNAPSHOT_STORE_INVALID": Stop(
        "the Snapshot Store is damaged, or a Snapshot that it lists is missing",
        _STORE_RESTORE,
    ),
    "SNAPSHOT_STORE_VERSION_UNSUPPORTED": Stop(
        "a newer version of this app made the Snapshot Store",
        "use a newer version of this app, and do not change the files inside the store",
    ),
    "SNAPSHOT_LIFECYCLE_FAILED": Stop(
        "a snapshot command cannot do what it was asked",
        "correct the command or its input as the message says, and run it again; for "
        "a store that fails snapshot verify, follow the next step that it gives",
    ),
    # The checks of an output and the Support Bundle.
    "HANDOFF_INVALID": Stop("the output does not pass the checks of its files", _NEW_OUTPUT),
    "DOCTOR_AUTHORITY_INVALID": Stop(
        "the diagnostics of the output are missing, invalid, or disagree", _NEW_OUTPUT
    ),
    "DOCTOR_UNREGISTERED_DIAGNOSTIC": Stop(
        "the output holds a diagnostic code that this version of the app does not know",
        "use the version of this app that made the output, or run Run-All again into "
        "a new folder",
    ),
    "DOCTOR_VERSION_UNSUPPORTED": Stop(
        "a version of this app that this version does not know made the output",
        "use the version of this app that made the output, or run Run-All again into "
        "a new folder",
    ),
    "SUPPORT_BUNDLE_PATH_UNSAFE": Stop(
        "the run output is not a folder, or the place for the Support Bundle is not new",
        "give the folder of a completed run, and a new file for the Support Bundle",
    ),
    "SUPPORT_BUNDLE_AUTHORITY_INVALID": Stop(
        "the diagnostics of the run output do not allow a Support Bundle",
        "run Run-All again into a new folder, and make the Support Bundle from it",
    ),
    "SUPPORT_BUNDLE_ARCHIVE_VALIDATION_FAILED": Stop(
        "the Support Bundle did not pass its check after it was written", _BUNDLE_REFUSED
    ),
    "SUPPORT_BUNDLE_MEMBER_SET_INVALID": Stop(
        "the Support Bundle would not hold exactly its six members", _BUNDLE_REFUSED
    ),
    "SUPPORT_BUNDLE_PRIVACY_SCAN_FAILED": Stop(
        "the privacy scan of the Support Bundle found a forbidden text", _BUNDLE_REFUSED
    ),
    "SUPPORT_BUNDLE_SIZE_LIMIT_EXCEEDED": Stop(
        "the Support Bundle would be larger than its limit", _BUNDLE_REFUSED
    ),
    "SUPPORT_BUNDLE_UNCLASSIFIED_FIELD": Stop(
        "the Support Bundle would hold a field that is not classified as safe",
        _BUNDLE_REFUSED,
    ),
    "SUPPORT_BUNDLE_UNREGISTERED_DIAGNOSTIC": Stop(
        "the Support Bundle would hold a diagnostic code that is not registered",
        _BUNDLE_REFUSED,
    ),
    # Internal checks that data cannot trigger: a stop before any output is
    # written (stage A5b checks it).
    "ACTIVITIES_NORMALIZATION_FAILED": Stop("the Activities could not be normalized", _DEFECT),
    "GEAR_NORMALIZATION_FAILED": Stop("the Gear could not be normalized", _DEFECT),
    "PERSONAL_RECORDS_NORMALIZATION_FAILED": Stop(
        "the Personal Records could not be normalized", _DEFECT
    ),
    "DAILY_METRICS_NORMALIZATION_FAILED": Stop(
        "the daily datasets could not be normalized", _DEFECT
    ),
    "PERFORMANCE_METRICS_NORMALIZATION_FAILED": Stop(
        "the performance metrics could not be normalized", _DEFECT
    ),
    "FIT_PROCESSING_FAILED": Stop("the FIT files could not be audited", _DEFECT),
    "DATASET_TABLE_INVALID": Stop("the table of the datasets of this app is invalid", _DEFECT),
    "DATASET_NOT_SERIALIZABLE": Stop("a normalized dataset could not be written as JSON", _DEFECT),
    "DIVERGENT_DUPLICATE": Stop(
        "a normalized dataset holds two rows with the same key", _DEFECT
    ),
    "STABLE_KEY_MISSING": Stop("a normalized row has no stable key", _DEFECT),
    "RELATIONSHIP_CONTRACT_FAILED": Stop(
        "a relationship between the datasets failed its check", _DEFECT
    ),
    "PROVENANCE_MISMATCH": Stop(
        "the provenance of the output does not match the input that was read", _DEFECT
    ),
    "OUTPUT_CONTRACT_INVALID": Stop("the output does not match its contract", _DEFECT),
    "OUTPUT_EXPERIENCE_FAILED": Stop("the documents of the output could not be made", _DEFECT),
    "SNAPSHOT_CONTEXT_INVALID": Stop(
        "the input built from the Snapshot Store does not match the build", _DEFECT
    ),
    "COMMAND_UNSUPPORTED": Stop("the command is not supported", _DEFECT),
    # Stops that no code describes.
    "RUN_ALL_FAILED": Stop("Run-All stopped unexpectedly", _AGAIN),
    "GOLDEN_PATH_FAILED": Stop("normalize-activities stopped unexpectedly", _AGAIN),
    "COMMAND_FAILED": Stop("the command stopped unexpectedly", _AGAIN),
}

# The next steps of the pre-run check and of the check of an output, by the
# identifier that their reports give (stage A5b).
NEXT_ACTIONS: dict[str, str] = {
    "SELECT_VALID_EXPORT_DIRECTORY": "select the Export folder, or the ZIP file downloaded from Garmin",
    "REPAIR_RUNTIME_ENVIRONMENT": STOPS["TIMEZONE_DATA_UNAVAILABLE"].next_step,
    "OBTAIN_COMPLETE_READABLE_EXPORT": STOPS["ACTIVITIES_EMPTY"].next_step,
    "ALLOW_INPUT_ACCESS_OR_SELECT_EXPORT_FOLDER": STOPS["INPUT_NOT_READABLE"].next_step,
    "DOWNLOAD_EXPORT_AGAIN": STOPS["INPUT_ZIP_CORRUPT"].next_step,
    "EXTRACT_EXPORT_AND_SELECT_FOLDER": STOPS["INPUT_TOO_LARGE"].next_step,
    "FREE_TEMP_SPACE_OR_SELECT_EXTRACTED_FOLDER": STOPS["TEMP_SPACE_INSUFFICIENT"].next_step,
    "SELECT_EXPORT_WITH_ACTIVITIES": STOPS["ACTIVITIES_NOT_FOUND"].next_step,
    "SELECT_ONE_EXPORT_OR_USE_SNAPSHOTS": STOPS["INPUT_MULTIPLE_EXPORTS"].next_step,
    "RUN_ALL": "run Run-All",
    "CORRECT_PRE_RUN_CONDITION": "correct what the findings name, and check the input again",
    "RUN_PRE_RUN_DOCTOR": (
        "check the input with doctor --input, correct what it reports, and run Run-All again"
    ),
    "REVIEW_RUN_QUALITY": (
        "read the warning in diagnostics/run_quality.json, which names the data that it affects"
    ),
    "USE_RECORDED_LEGACY_RESULT": (
        "use the result that the version which made the output recorded, or run Run-All "
        "again for the diagnostics of this version"
    ),
    "OPTIONAL_CONFIRMATION": "nothing is required; START_HERE.md explains the output",
    "REVIEW_WARNING_CODES_AND_AFFECTED_SCOPES": (
        "before you use the outputs, read the warnings and check which data they affect"
    ),
    "REVIEW_EXCLUDED_FIT_EVIDENCE": (
        "before you use the outputs made from FIT files, check the files that were left out"
    ),
}


def stop_line(code: str, message: str) -> str:
    """The CLI's line for a stop: what happened, as ``message`` says it, and
    the next step of ``code``."""
    return f"ERROR [{code}]: {message}; {STOPS[code].next_step}"


def stop_text(code: str) -> str:
    """What a code means and what to do next, as one text, for a notice of
    the same problem that does not stop a command."""
    stop = STOPS[code]
    return f"{stop.what}; {stop.next_step}"


__all__ = ["NEXT_ACTIONS", "STOPS", "Stop", "stop_line", "stop_text"]
