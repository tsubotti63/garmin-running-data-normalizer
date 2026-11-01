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
        "this app is not allowed to open a folder or file of the input",
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
        "if no snapshot command is running, remove that file with snapshot unlock "
        "--confirm-no-other-command, then run the command again",
    ),
    "SNAPSHOT_REGISTRATION_INCOMPLETE": Stop(
        "a registration in the Snapshot Store was interrupted",
        "register the same Export, or another complete Export, again, which completes "
        "the store",
    ),
    "SNAPSHOT_STORE_NOT_READABLE": Stop(
        "this app is not allowed to open a folder or file of the Snapshot Store",
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
    "SNAPSHOT_STORE_NOT_FOUND": Stop(
        "there is no Snapshot Store in the folder given for it",
        "check the folder given with --store; for a new store, run snapshot init first",
    ),
    "SNAPSHOT_STORE_EMPTY": Stop(
        "the Snapshot Store holds no Snapshot yet",
        "register an Export with snapshot register first",
    ),
    # The place of the store (stage B4a).
    "SNAPSHOT_STORE_SYMLINK": Stop(
        "the Snapshot Store is a symbolic link",
        "give the folder of the store itself with --store, not a link to it",
    ),
    "SNAPSHOT_STORE_PARENT_NOT_FOUND": Stop(
        "the folder that should hold the new Snapshot Store does not exist",
        "check the place given with --store, or make the folder that holds it first; no "
        "folder is made above a new store",
    ),
    "SNAPSHOT_STORE_NOT_EMPTY": Stop(
        "the place given for a new Snapshot Store is a file, or a folder that holds other files",
        "give the place of a new folder, or of an empty one, with --store; to use a store, "
        "give the folder of the store itself",
    ),
    "SNAPSHOT_STORE_INSIDE_STORE": Stop(
        "the place given for a new Snapshot Store is inside another Snapshot Store",
        "give a place outside the other store with --store",
    ),
    # The paths inside a store on Windows without long paths (stage B6c).
    "SNAPSHOT_STORE_PATH_TOO_LONG": Stop(
        "the paths inside the Snapshot Store would be too long for this computer",
        "give a store in a shorter folder with --store, or on Windows turn on long paths",
    ),
    # A registration (stage B4b-1).
    # Removing the lock file that a stopped registration left (stage B4b-2).
    "SNAPSHOT_UNLOCK_NOT_CONFIRMED": Stop(
        "the lock file is removed only when no snapshot command uses the Snapshot Store",
        "check that no normalization or snapshot command uses the store, then run snapshot "
        "unlock again with --confirm-no-other-command",
    ),
    "SNAPSHOT_LOCK_NOT_FOUND": Stop(
        "the Snapshot Store has no lock file",
        "nothing needs to be removed; run the command that stopped again",
    ),
    "SNAPSHOT_LOCK_INVALID": Stop(
        "the lock file of the Snapshot Store is not one that this app writes, or it changed "
        "while it was checked",
        "check that no snapshot command is running, and look at the file .single-writer.lock "
        "in the store; this app removes only its own lock file",
    ),
    "SNAPSHOT_LABEL_INVALID": Stop(
        "the label of the Snapshot is not one that this app takes",
        "give a label of 1 to 64 letters, digits, dots, underscores, or hyphens that starts "
        "with a letter or a digit, with --label",
    ),
    "SNAPSHOT_LABEL_EXISTS": Stop(
        "another Snapshot in the store has this label",
        "give another label with --label",
    ),
    "SNAPSHOT_TIME_INVALID": Stop(
        "a time of the Export cannot be read, or the times are not in order",
        "give each time with its offset from UTC, such as 2030-01-01T02:00:00+00:00, with the "
        "request no later than the download, and the download no later than the observation",
    ),
    "SNAPSHOT_INPUT_INSIDE_STORE": Stop(
        "the Export and the Snapshot Store are the same folder, or one is inside the other",
        "keep the Export and the store in separate folders",
    ),
    # The stops of the store's contract that no code above describes, such
    # as an argument that is not valid; a damaged store is always
    # SNAPSHOT_STORE_INVALID (stage A5b-2).
    "SNAPSHOT_LIFECYCLE_FAILED": Stop(
        "a snapshot command cannot do what it was asked",
        "correct the command or its input as the message says, and run it again",
    ),
    # The checks of an output and the Support Bundle.
    "HANDOFF_INVALID": Stop(
        "the folder is not the output of a run, or the files of the output do not pass "
        "their checks",
        "check that the folder is the output of Run-All; if it is, do not change its "
        "files, and run Run-All again into a new folder",
    ),
    # An output that another version of this app made (stage B5b): one of 1.0
    # to 1.2, or of 1.4 or later that is not this version; until then,
    # HANDOFF_INVALID, DOCTOR_AUTHORITY_INVALID, or
    # SUPPORT_BUNDLE_AUTHORITY_INVALID.
    "OUTPUT_OTHER_VERSION": Stop(
        "the output was made by another version of this app, which this version cannot check",
        "normalize again with this version into a new folder",
    ),
    # The reading of an output for the numbers of the view page, which the
    # series command and the GUI share (stage G2); until then only the GUI
    # gave these two codes.
    "OUTPUT_CHANGED": Stop(
        "the files of the output changed after they were checked, or do not have the form "
        "that this version writes",
        "if you did not change the folder, please report the code; if you did, run Run-All "
        "again into a new folder",
    ),
    "OUTPUT_NOT_AVAILABLE": Stop(
        "a file of the output is missing, was replaced by a link, or is too large for this "
        "app to read",
        "check that the output folder is still where it was; if a file is too large, please "
        "report the code",
    ),
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
        "the run output is a link or not an existing folder",
        "give the folder of a completed run",
    ),
    "SUPPORT_BUNDLE_EXISTS": Stop(
        "a file or a link is there already in the place of the Support Bundle",
        "move or rename it, or give another file for the Support Bundle",
    ),
    # The place of a Support Bundle, as for the output (stage B5a).
    "SUPPORT_BUNDLE_PARENT_NOT_FOUND": Stop(
        "the folder for the Support Bundle does not exist or is not a folder",
        "give a file in an existing folder for the Support Bundle, or create the folder first",
    ),
    "SUPPORT_BUNDLE_INSIDE_OUTPUT": Stop(
        "the place of the Support Bundle is inside the run output",
        "give a file outside the run output for the Support Bundle, such as next to it",
    ),
    "SUPPORT_BUNDLE_NOT_WRITTEN": Stop(
        "the Support Bundle could not be written",
        "check that the folder for it is still there and that this app can write in it",
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
    # The numbers of the view page in a new CSV file (stage G2). An output of
    # 1.3 passes its checks, but its numbers are not given.
    "SERIES_OUTPUT_OTHER_VERSION": Stop(
        "the output passed its checks, but was made by another version of this app, and "
        "this version gives the numbers of its own outputs only",
        "normalize again with this version into a new folder",
    ),
    # The place of the CSV file, as for a Support Bundle.
    "SERIES_PARENT_NOT_FOUND": Stop(
        "the folder for the CSV file does not exist or is not a folder",
        "give a file in an existing folder for the CSV file, or create the folder first",
    ),
    "SERIES_INSIDE_OUTPUT": Stop(
        "the place of the CSV file is inside the run output",
        "give a file outside the run output for the CSV file, such as next to it",
    ),
    "SERIES_EXISTS": Stop(
        "a file or a link is there already in the place of the CSV file",
        "move or rename it, or give another file for the CSV file",
    ),
    "SERIES_NOT_WRITTEN": Stop(
        "the CSV file could not be written",
        "check that the folder for it is still there and that this app can write in it",
    ),
    "SERIES_ITEM_UNKNOWN": Stop(
        "an item key that this app does not know was given",
        "give the keys of the items as the help of the series command lists them",
    ),
    "SERIES_TYPE_UNKNOWN": Stop(
        "an activity type that the output does not have was given",
        "give a name of the column activity_type of analysis/activities.csv in the output "
        "as it is written there, or --all-types",
    ),
    "SERIES_RANGE_INVALID": Stop(
        "the period that was given is not a range of dates",
        "give --from and --to together as YYYY-MM-DD, with --from not after --to, and "
        "without --period",
    ),
    # The icon that gui --create-shortcut makes before the GUI opens (stage
    # E1d); the GUI does not open when it cannot be made.
    "SHORTCUT_NOT_SUPPORTED": Stop(
        "an icon that starts the GUI can be made only on macOS and Windows",
        "start the GUI with garmin-running-data-normalizer gui, without --create-shortcut",
    ),
    "SHORTCUT_PLACE_TAKEN": Stop(
        "a file that this app did not make has the name of the icon that starts the GUI",
        "rename or move that file and run the command again, or start the GUI with "
        "garmin-running-data-normalizer gui, without --create-shortcut",
    ),
    "SHORTCUT_NOT_CREATED": Stop(
        "the icon that starts the GUI could not be made",
        "check that this app may write on the desktop (on a Mac, allow the Terminal in "
        "System Settings > Privacy & Security > Files and Folders) and run the command "
        "again, or start the GUI with garmin-running-data-normalizer gui, without "
        "--create-shortcut",
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
    # Ctrl+C, which ends a command with exit 130 (stage A5c).
    "RUN_CANCELLED": Stop(
        "the command was cancelled with Ctrl+C before it finished",
        "run the command again when you need its result, and when no command runs, "
        "delete what the lines after this one name, if any",
    ),
    "RUN_CANCELLED_AFTER_OUTPUT": Stop(
        "the command was cancelled with Ctrl+C after it wrote its output, which is complete",
        "use the output as it is, and check it first with validate-handoff if it is the "
        "output of a run; running the command again stops with OUTPUT_EXISTS",
    ),
    # Stops that no code describes.
    "RUN_ALL_FAILED": Stop("Run-All stopped unexpectedly", _AGAIN),
    "GOLDEN_PATH_FAILED": Stop("normalize-activities stopped unexpectedly", _AGAIN),
    "COMMAND_FAILED": Stop("the command stopped unexpectedly", _AGAIN),
}

# The next steps of the pre-run check and of the check of an output, by the
# identifier that their reports give (stage A5b). A finding whose code is a
# stop gives the next step of that stop instead (``finding_next_step``).
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
    # Exit 3 leaves out files and rows as well as FIT data (stage B2b); the
    # identifier stays, as the JSON report gives it.
    "REVIEW_EXCLUDED_FIT_EVIDENCE": (
        "before you use the outputs, check what was left out, such as files, rows, or FIT "
        "data, in START_HERE.md"
    ),
}


# The codes that only the GUI gives: its server, its folder list, and the
# actions on a finished output (stage B2a). The CLI never stops with them.
# The page shows their words, as it shows those of STOPS.
_ENTRIES = Stop("the entries could not be read", "check the entries and press the button again")
PAGE_STOPS: dict[str, Stop] = {
    "PATH_NOT_ABSOLUTE": Stop(
        "the place is not a full path",
        "choose it with a button that says Choose, or paste a place that starts with / "
        "on a Mac or Linux, or with a drive such as C:\\ on Windows",
    ),
    "PATH_INVALID": _ENTRIES,
    "INPUT_PATH_INVALID": _ENTRIES,
    "OUTPUT_PARENT_INVALID": _ENTRIES,
    "REQUEST_INVALID": _ENTRIES,
    # Conditions on the activities of another form (stage T1 of v2.2.0).
    "CONDITIONS_INVALID": Stop(
        "the conditions could not be read",
        "check the words of the name, the distance, and the duration in the window of “Conditions…”",
    ),
    "FOLDER_NOT_FOUND": Stop(
        "the folder does not exist", "check the place, or choose the folder with Choose…"
    ),
    "NOT_A_FOLDER": Stop("this is a file, not a folder", "choose a folder"),
    "FOLDER_NOT_READABLE": Stop(
        "this app is not allowed to open this folder",
        "on a Mac, allow it when you are asked, or in System Settings > Privacy & Security",
    ),
    "RUN_ACTIVE": Stop(
        "a normalization is running in another tab or window", "wait for it to finish, or cancel it"
    ),
    "RUN_START_FAILED": Stop(
        "the normalization could not be started",
        "press Run normalization again; if it stops again, please report the code",
    ),
    "NO_FINISHED_OUTPUT": Stop(
        "there is no finished output to check yet", "normalize first, or choose an earlier output"
    ),
    # The list of earlier outputs that another tab was given since (stage B5b).
    "OUTPUT_LIST_CHANGED": Stop(
        "the list of earlier outputs changed since the page showed it",
        "choose the output again from the list",
    ),
    # The view page (stage G3b): an output that the server no longer keeps,
    # and an answer over the limit of its size.
    "VIEW_NOT_OPEN": Stop(
        "the output that the page shows is no longer open in this app", "choose the output again"
    ),
    "VIEW_ANSWER_TOO_LARGE": Stop(
        "there are too many numbers to show at once",
        "choose a shorter period, or group by week or month",
    ),
    "OPEN_NOT_AVAILABLE": Stop(
        "no program to open it (xdg-open) was found",
        "open the output folder from your file manager, such as Finder or File Explorer",
    ),
    "OPEN_FAILED": Stop(
        "this computer could not open it",
        "open the output folder from your file manager, such as Finder or File Explorer",
    ),
    # The system's own dialog to choose an Export (stage B3a).
    "CHOOSER_NOT_AVAILABLE": Stop(
        "this system's dialog to choose could not be opened",
        "choose from the list below, or paste the place",
    ),
    "CHOOSER_TIMEOUT": Stop(
        "the dialog to choose was not answered in time",
        "press Choose ZIP file… or Choose extracted folder… again",
    ),
    "CHOOSER_BUSY": Stop(
        "another dialog to choose is open", "choose in it or close it, and press the button again"
    ),
}

# The words of the page for codes of STOPS whose words name what the CLI does
# (its commands, Run-All, registering, or a file to give) or what the page
# cannot do yet (stage B2a). The meaning is the same as in STOPS.
PAGE_WORDING: dict[str, Stop] = {
    "INPUT_CHANGED": Stop(
        "the input changed while it was read",
        "press Run normalization again when no other app changes the Export",
    ),
    # Snapshots cannot be used on the page until stage B4.
    "INPUT_MULTIPLE_EXPORTS": Stop(
        "the input holds more than one Export, or Exports of more than one account",
        "select one Export to normalize",
    ),
    "OUTPUT_PUBLISH_FAILED": Stop(
        "the output could not be written",
        "check the free space and the permissions of the folder for the output, and press "
        "Run normalization again",
    ),
    "RUN_ALL_FAILED": Stop(
        "the normalization stopped unexpectedly",
        "press Run normalization again; if it stops again, please report the code",
    ),
    "COMMAND_FAILED": Stop(
        "this app stopped unexpectedly while it did this",
        "press the button again; if it stops again, please report the code",
    ),
    # The two codes of the reading of an output, which the CLI gives too from
    # stage G2: the page keeps its words.
    "OUTPUT_CHANGED": Stop(
        "the output folder does not match what the normalization wrote",
        "if you did not change the folder, please report the code; if you did, normalize again",
    ),
    "OUTPUT_NOT_AVAILABLE": Stop(
        "the output folder or a file in it is missing, or was replaced by a link",
        "check that the output folder is still where it was",
    ),
    # The page checks the output that it made, and from stage B5b one that the
    # person chose.
    "HANDOFF_INVALID": Stop(
        "the folder is not the output of a normalization, or the files of the output do "
        "not pass their checks",
        "choose the folder of an output; if it is one, do not change its files, and "
        "normalize again into a new folder",
    ),
    "DOCTOR_AUTHORITY_INVALID": Stop(
        "the diagnostics of the output are missing, invalid, or disagree",
        "do not change the files of an output; normalize again into a new folder",
    ),
    "DOCTOR_UNREGISTERED_DIAGNOSTIC": Stop(
        "the output holds a diagnostic code that this version of the app does not know",
        "use the version of this app that made the output, or normalize again into a new folder",
    ),
    "DOCTOR_VERSION_UNSUPPORTED": Stop(
        "a version of this app that this version does not know made the output",
        "use the version of this app that made the output, or normalize again into a new folder",
    ),
    "SUPPORT_BUNDLE_AUTHORITY_INVALID": Stop(
        "the diagnostics of the output do not allow a Support Bundle",
        "normalize again into a new folder, and make the Support Bundle from that output",
    ),
    # The page makes the Support Bundle next to the output or in a folder that
    # the person chose (stage B5a).
    "SUPPORT_BUNDLE_EXISTS": Stop(
        "a file or a link is there already in the place of the Support Bundle",
        "move or rename it, or choose another place, and press the button again",
    ),
    "SUPPORT_BUNDLE_PARENT_NOT_FOUND": Stop(
        "the folder for the Support Bundle is not there",
        "choose another place with Choose…, and press the button again",
    ),
    "SUPPORT_BUNDLE_INSIDE_OUTPUT": Stop(
        "the place for the Support Bundle is inside the output folder",
        "choose a place outside the output folder, such as next to it",
    ),
    "SUPPORT_BUNDLE_PATH_UNSAFE": Stop(
        "the output folder is a link or is no longer there",
        "check that the output folder is still where it was",
    ),
    # The Snapshot Store, which the page opens, lists, and checks, and for
    # which it chooses the place of a new one (stage B4a). The page does not
    # import into a store until stage B4b.
    "SNAPSHOT_STORE_NOT_FOUND": Stop(
        "there is no Snapshot Store in the chosen folder",
        "choose the folder of the store, or choose where to create a new one",
    ),
    "SNAPSHOT_STORE_INVALID": Stop(
        "the Snapshot Store is damaged, or a Snapshot that it lists is missing",
        "do not change the files inside the store; restore it from a backup that passed "
        "Check the Snapshots",
    ),
    "SNAPSHOT_STORE_SYMLINK": Stop(
        "the Snapshot Store is a symbolic link",
        "choose the folder of the store itself, not a link to it",
    ),
    "SNAPSHOT_STORE_PARENT_NOT_FOUND": Stop(
        "the folder that should hold the new Snapshot Store does not exist",
        "choose a folder that exists",
    ),
    "SNAPSHOT_STORE_NOT_EMPTY": Stop(
        "the place for the new Snapshot Store is a file, or a folder that holds other files",
        "choose another folder for the new store",
    ),
    "SNAPSHOT_STORE_INSIDE_STORE": Stop(
        "the place for the new Snapshot Store is inside another Snapshot Store",
        "choose a folder outside the other store",
    ),
    "SNAPSHOT_STORE_PATH_TOO_LONG": Stop(
        "the paths inside the Snapshot Store would be too long for this computer",
        "choose a store in a shorter folder, or on Windows turn on long paths",
    ),
    "SNAPSHOT_STORE_LOCKED": Stop(
        "the Snapshot Store has a lock file (.single-writer.lock): an import is running, "
        "or one stopped before it ended",
        "if no other normalization or snapshot command is running, check the box below and "
        "press Remove the lock file; only that file is removed, and the Snapshots stay",
    ),
    # Removing the lock file from the page (stage B4b-2).
    "SNAPSHOT_UNLOCK_NOT_CONFIRMED": Stop(
        "the lock file is removed only when no other normalization or snapshot command uses "
        "the store",
        "check that none is running, then check the box",
    ),
    "SNAPSHOT_LOCK_NOT_FOUND": Stop(
        "the lock file is not there any more",
        "press Run normalization to import",
    ),
    "SNAPSHOT_LOCK_INVALID": Stop(
        "the lock file is not one that this app writes, or it changed while it was checked",
        "check that no other normalization or snapshot command is running; this app removes "
        "only its own lock file, so remove the file .single-writer.lock in the store by hand",
    ),
    "SNAPSHOT_REGISTRATION_INCOMPLETE": Stop(
        "an import into the Snapshot Store was interrupted",
        "the next import completes the store",
    ),
    # An import from the page (stage B4b-1), which names its fields.
    "SNAPSHOT_LABEL_INVALID": Stop(
        "the name of the Snapshot is not one that this app takes",
        "use 1 to 64 letters, digits, dots, underscores, or hyphens that start with a letter "
        "or a digit",
    ),
    "SNAPSHOT_LABEL_EXISTS": Stop(
        "another Snapshot in the store has this name",
        "change the name of the Snapshot",
    ),
    "SNAPSHOT_TIME_INVALID": Stop(
        "the download time cannot be read",
        "enter the date and the time, such as 2030-01-01 02:00",
    ),
    "SNAPSHOT_INPUT_INSIDE_STORE": Stop(
        "the Export and the Snapshot Store are the same folder, or one is inside the other",
        "choose an Export outside the store, or another store",
    ),
    "SNAPSHOT_STORE_NOT_WRITABLE": Stop(
        "this app cannot write in the Snapshot Store, or create it there",
        "allow this app to write in its folder, or for a new store choose another folder; then "
        "press Run normalization again",
    ),
    "SNAPSHOT_STORE_SPACE_INSUFFICIENT": Stop(
        "the drive of the Snapshot Store does not have enough free space",
        "free some space, or for a new store choose another folder; then press Run "
        "normalization again",
    ),
    "SNAPSHOT_STORE_EMPTY": Stop(
        "the Snapshot Store holds no Snapshot yet",
        "import an Export into it first",
    ),
    "SNAPSHOT_LIFECYCLE_FAILED": Stop(
        "this app could not do this with the Snapshot Store",
        "check what you chose and entered, and press the button again; if it stops again, "
        "please report the code",
    ),
}


# The three cases of INPUT_MULTIPLE_EXPORTS (stage B4b-2): the code stays the
# same, and what happened and the next step say which. The input itself is
# the case of the table above; the Export of another account than the
# Snapshots of a store stops a registration, and a store that holds the
# Exports of more than one account stops its build.
MIX_KINDS = ("input", "other_account", "store")
MIX_STOPS: dict[str, Stop] = {
    "other_account": Stop(
        "the Export belongs to another account than the Snapshots in this Snapshot Store",
        "choose an Export of this account, or make another Snapshot Store for this Export",
    ),
    "store": Stop(
        "the Snapshot Store holds the Exports of more than one account",
        "make a new Snapshot Store for each account, and register each Export into it again",
    ),
}
# The page's words of the three cases, which name no command.
PAGE_MIX_WORDING: dict[str, Stop] = {
    "other_account": MIX_STOPS["other_account"],
    "store": Stop(
        MIX_STOPS["store"].what,
        "make a new Snapshot Store for each account, and import each Export into it again",
    ),
}


def stop_line(code: str, message: str, next_step: str | None = None) -> str:
    """The CLI's line for a stop: what happened, as ``message`` says it, and
    the next step of ``code``, or ``next_step`` for a case of the code that
    has its own (stage B4b-2)."""
    return f"ERROR [{code}]: {message}; {next_step or STOPS[code].next_step}"


def finding_next_step(code: str, next_action_id: str) -> str | None:
    """The next step of a Doctor finding in words: that of the stop of its
    code, so that the check and the run say the same about the same problem
    (stage B2b), or else that of its next action. The JSON report keeps the
    identifier of the next action."""
    stop = STOPS.get(code)
    return stop.next_step if stop is not None else NEXT_ACTIONS.get(next_action_id)


def stop_text(code: str) -> str:
    """What a code means and what to do next, as one text, for a notice of
    the same problem that does not stop a command."""
    stop = STOPS[code]
    return f"{stop.what}; {stop.next_step}"


__all__ = [
    "MIX_KINDS",
    "MIX_STOPS",
    "NEXT_ACTIONS",
    "PAGE_MIX_WORDING",
    "PAGE_STOPS",
    "PAGE_WORDING",
    "STOPS",
    "Stop",
    "finding_next_step",
    "stop_line",
    "stop_text",
]
