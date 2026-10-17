"""Read-only pre-run and post-run Export Evidence Doctor."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .. import __version__
from ..common.time import (
    DEFAULT_TIMEZONE,
    TimezoneDataUnavailableError,
    TimezoneNameInvalidError,
    require_timezone_data,
    resolve_timezone_name,
)
from ..intake.accounts import asset_accounts
from ..intake.discovery import read_export
from ..intake.roots import MixedExportsError
from ..intake.source import (
    CorruptArchiveError,
    ExportTooLargeError,
    InputNotReadableError,
    TempSpaceError,
    is_zip_input,
)
from ..normalizers.activities import normalize_activities
from ..normalizers.records import merge_repeated_records
from ..run_all import left_out_files
from ..standalone import StandaloneHandoffError, validate_standalone_handoff
from ..stops import NEXT_ACTIONS, finding_next_step
from .contracts import (
    DOCTOR_FORMAT,
    DOCTOR_SCHEMA_VERSION,
    SAFE_WARNING_CODES,
    exit_code_for_status,
    interpretation_for_status,
)
from .detector import reads_record_file


class DoctorError(ValueError):
    """A fixed-code Doctor validation failure without private evidence text."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


def _finding(
    code: str,
    *,
    severity: str,
    actionability: str,
    safe_message_id: str,
    next_action_id: str,
    authority_reference: str,
    evidence_reference: str,
    not_evaluated_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "actionability": actionability,
        "safe_message_id": safe_message_id,
        "next_action_id": next_action_id,
        "authority_reference": authority_reference,
        "evidence_reference": evidence_reference,
        "not_evaluated_reason": not_evaluated_reason,
    }


def _base(
    *,
    product_version: str,
    mode: str,
    product_status: str | None,
    product_exit_code: int | None,
    availability: str,
    completion_state: str,
    usability_scope: str,
    boundary_class: str,
    actionability: str,
    severity: str,
    findings: list[dict[str, Any]],
    authority_references: list[str],
) -> dict[str, Any]:
    if product_status == "PASS":
        known_boundary = False
        affected_scopes: list[str] = []
        unaffected_scopes = ["NORMALIZED_OUTPUTS_WITHIN_DECLARED_CONTRACT"]
        doctor_next_action_id = "OPTIONAL_CONFIRMATION"
        support_bundle_suggested = False
    elif product_status == "PASS_WITH_WARNINGS":
        known_boundary = True
        affected_scopes = ["SCOPES_NAMED_BY_REGISTERED_WARNING_CODES"]
        unaffected_scopes = ["VALID_NORMALIZED_OUTPUTS"]
        doctor_next_action_id = "REVIEW_WARNING_CODES_AND_AFFECTED_SCOPES"
        support_bundle_suggested = True
    elif product_status == "PARTIAL_SUCCESS":
        known_boundary = True
        affected_scopes = ["EXCLUDED_OR_INCOMPLETE_FIT_DERIVED_SCOPE"]
        unaffected_scopes = ["VALID_ACTIVITIES_OUTPUT"]
        doctor_next_action_id = "REVIEW_EXCLUDED_FIT_EVIDENCE"
        support_bundle_suggested = True
    elif completion_state == "NOT_COMPLETED":
        known_boundary = True
        affected_scopes = ["RUN_ALL_OUTPUT"]
        unaffected_scopes = []
        doctor_next_action_id = "RUN_PRE_RUN_DOCTOR"
        support_bundle_suggested = False
    else:
        known_boundary = False
        affected_scopes = []
        unaffected_scopes = []
        doctor_next_action_id = (
            "CORRECT_PRE_RUN_CONDITION"
            if actionability == "ACTION_REQUIRED"
            else "RUN_ALL"
        )
        support_bundle_suggested = False
    return {
        "format": DOCTOR_FORMAT,
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "product_version": product_version,
        "mode": mode,
        "product_status": product_status,
        "product_exit_code": product_exit_code,
        "diagnostic_contract_availability": availability,
        "completion_state": completion_state,
        "usability_scope": usability_scope,
        "boundary_class": boundary_class,
        "actionability": actionability,
        "severity": severity,
        "known_boundary": known_boundary,
        "affected_scopes": affected_scopes,
        "unaffected_scopes": unaffected_scopes,
        "doctor_next_action_id": doctor_next_action_id,
        "support_bundle_suggested": support_bundle_suggested,
        "findings": findings,
        "authority_references": authority_references,
    }


def doctor_input(
    root: str | Path,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> dict[str, Any]:
    """Inspect bounded input readiness without predicting a run's warnings.

    Every file is read for its digest, as at the start of a run, and the
    Activities files are read as a run reads them (stage A5a), so that the
    check tells when a run would stop because no Activities record can be
    kept. The files of the other datasets are not read: a run leaves out
    what it cannot read of them and goes on.

    The report of the check also gives counts of the input
    (``input_counts``, stage B3b): the Activities records that a run keeps,
    the FIT files, the files that a run reads, those that the check found it
    cannot read, and those that are not read. It is None when the Export
    could not be read.
    """
    try:
        timezone_name = resolve_timezone_name(timezone_name)
    except TimezoneNameInvalidError as exc:
        raise DoctorError(exc.code, exc.safe_message) from exc
    except TimezoneDataUnavailableError:
        pass  # Reported below as the bounded timezone-data finding.
    requested = Path(root)
    findings: list[dict[str, Any]] = []
    counts: dict[str, Any] | None = None
    if requested.is_symlink() or not (requested.is_dir() or is_zip_input(requested)):
        findings.append(
            _finding(
                "INPUT_DIRECTORY_INVALID",
                severity="ERROR",
                actionability="ACTION_REQUIRED",
                safe_message_id="INPUT_DIRECTORY_MUST_BE_LOCAL_DIRECTORY",
                next_action_id="SELECT_VALID_EXPORT_DIRECTORY",
                authority_reference="doctor_contract#pre-run-mode",
                evidence_reference="diagnostic:input-boundary",
            )
        )
    else:
        timezone_ready = True
        try:
            require_timezone_data(timezone_name)
        except TimezoneDataUnavailableError:
            timezone_ready = False
            findings.append(
                _finding(
                    "TIMEZONE_DATA_UNAVAILABLE",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="INSTALL_REQUIRED_TIMEZONE_DATA",
                    next_action_id="REPAIR_RUNTIME_ENVIRONMENT",
                    authority_reference="product:timezone-boundary",
                    evidence_reference="diagnostic:timezone-data",
                )
            )
        try:
            # Every file is read for its digest, as at the start of a run,
            # without keeping its content. The accounts that the records name
            # are compared as at the start of a run, and never reported.
            with read_export(requested) as reading:
                assets = reading.assets
                same_export_count = reading.same_export_count
                mixed_accounts = len(asset_accounts(assets)) > 1
                activity_assets = [
                    asset
                    for asset in assets
                    if asset.kind == "json"
                    and reads_record_file(asset.member_path or asset.source_path, "activities")
                ]
                # The Activities files are read as a run reads them (stage
                # A5a): a run stops when none of their records can be kept.
                # A run of mixed Exports, or without the timezone data, stops
                # before it reads them, and the check does not count them.
                activity_record_count: int | None = None
                if not activity_assets:
                    activity_record_count = 0
                if activity_assets and not mixed_accounts and timezone_ready:
                    # The run keeps one row of an activity that the files
                    # give more than once (stage A3b), and counts the rows
                    # after that (stage B3b).
                    activity_record_count = len(
                        merge_repeated_records(
                            "activities",
                            normalize_activities(
                                str(requested),
                                timezone_name,
                                assets=activity_assets,
                                left_out=Counter(),
                            ),
                        ).rows
                    )
                # Files that cannot be read are left out of the run, which
                # goes on (stage A3c): a damaged ZIP, a file over the limit,
                # and from stage A5a an Activities file that is not JSON.
                left_out = list(reading.left_out)
                # The counts of the input, as the run counts them: the files
                # that it reads are its input_asset_count, and those not read
                # its files_not_read. A run also leaves out the JSON files of
                # the other datasets that are not JSON, which the check does
                # not read (stage B3b).
                input_counts = {
                    "activity_records": activity_record_count,
                    "fit_files": sum(1 for asset in assets if asset.kind == "fit"),
                    "files_read": len(assets),
                    "files_left_out": len(left_out),
                    "files_not_read": len(reading.not_read) + len(reading.outside_files),
                }
            if mixed_accounts:
                raise MixedExportsError()
            counts = input_counts
        except MixedExportsError:
            findings.append(
                _finding(
                    "INPUT_MULTIPLE_EXPORTS",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="INPUT_HOLDS_MORE_THAN_ONE_EXPORT",
                    next_action_id="SELECT_ONE_EXPORT_OR_USE_SNAPSHOTS",
                    authority_reference="product:intake-discovery",
                    evidence_reference="diagnostic:source-discovery",
                )
            )
        except CorruptArchiveError:
            findings.append(
                _finding(
                    "INPUT_ZIP_CORRUPT",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="INPUT_ZIP_DAMAGED_OR_INCOMPLETE",
                    next_action_id="DOWNLOAD_EXPORT_AGAIN",
                    authority_reference="product:intake-discovery",
                    evidence_reference="diagnostic:source-discovery",
                )
            )
        except ExportTooLargeError:
            findings.append(
                _finding(
                    "INPUT_TOO_LARGE",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="INPUT_ZIP_TOO_LARGE_TO_READ_DIRECTLY",
                    next_action_id="EXTRACT_EXPORT_AND_SELECT_FOLDER",
                    authority_reference="product:intake-discovery",
                    evidence_reference="diagnostic:source-discovery",
                )
            )
        except (InputNotReadableError, PermissionError):
            # A folder or file that this app may not open stops a run
            # (stage A3d-3a); which one, the run says where it is started.
            findings.append(
                _finding(
                    "INPUT_NOT_READABLE",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="INPUT_FOLDER_OR_FILE_CANNOT_BE_OPENED",
                    next_action_id="ALLOW_INPUT_ACCESS_OR_SELECT_EXPORT_FOLDER",
                    authority_reference="product:intake-discovery",
                    evidence_reference="diagnostic:source-discovery",
                )
            )
        except TempSpaceError:
            findings.append(
                _finding(
                    "TEMP_SPACE_INSUFFICIENT",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="TEMP_FOLDER_SPACE_INSUFFICIENT",
                    next_action_id="FREE_TEMP_SPACE_OR_SELECT_EXTRACTED_FOLDER",
                    authority_reference="product:intake-discovery",
                    evidence_reference="diagnostic:source-discovery",
                )
            )
        except Exception:
            findings.append(
                _finding(
                    "INPUT_DISCOVERY_FAILED",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="INPUT_COULD_NOT_BE_SAFELY_DISCOVERED",
                    next_action_id="OBTAIN_COMPLETE_READABLE_EXPORT",
                    authority_reference="product:intake-discovery",
                    evidence_reference="diagnostic:source-discovery",
                )
            )
        else:
            if same_export_count:
                findings.append(
                    _finding(
                        "INPUT_DUPLICATE_SOURCES",
                        severity="WARNING",
                        actionability="NONE",
                        safe_message_id="INPUT_HOLDS_THE_SAME_EXPORT_MORE_THAN_ONCE",
                        next_action_id="RUN_ALL",
                        authority_reference="product:intake-discovery",
                        evidence_reference="diagnostic:source-discovery",
                    )
                )
            if left_out:
                findings.append(
                    _finding(
                        "DATA_FILE_LEFT_OUT",
                        severity="WARNING",
                        actionability="NONE",
                        safe_message_id="INPUT_FILES_CANNOT_BE_READ_AND_WILL_BE_LEFT_OUT",
                        next_action_id="RUN_ALL",
                        authority_reference="product:intake-discovery",
                        evidence_reference="diagnostic:source-discovery",
                    )
                )
            has_activities = bool(activity_assets)
            activities_left_out = any(
                item["family"] == "activities" for item in left_out_files(left_out)
            )
            if not has_activities and activities_left_out:
                # The Export has Activities files, but none can be read: the
                # run stops with ACTIVITIES_EMPTY, as here.
                findings.append(
                    _finding(
                        "ACTIVITIES_EMPTY",
                        severity="ERROR",
                        actionability="ACTION_REQUIRED",
                        safe_message_id="ACTIVITIES_FILES_CANNOT_BE_READ",
                        next_action_id="OBTAIN_COMPLETE_READABLE_EXPORT",
                        authority_reference="product:run-all-required-input",
                        evidence_reference="diagnostic:activities-presence",
                    )
                )
            elif not has_activities:
                findings.append(
                    _finding(
                        "ACTIVITIES_NOT_FOUND",
                        severity="ERROR",
                        actionability="ACTION_REQUIRED",
                        safe_message_id="REQUIRED_ACTIVITIES_SOURCE_NOT_OBSERVED",
                        next_action_id="SELECT_EXPORT_WITH_ACTIVITIES",
                        authority_reference="product:run-all-required-input",
                        evidence_reference="diagnostic:activities-presence",
                    )
                )
            elif activity_record_count == 0 and activities_left_out:
                # No Activities record can be kept, and Activities files
                # could not be read: the run stops with ACTIVITIES_EMPTY and
                # names the files that cannot be read (stage A5a).
                findings.append(
                    _finding(
                        "ACTIVITIES_EMPTY",
                        severity="ERROR",
                        actionability="ACTION_REQUIRED",
                        safe_message_id="ACTIVITIES_FILES_CANNOT_BE_READ",
                        next_action_id="OBTAIN_COMPLETE_READABLE_EXPORT",
                        authority_reference="product:run-all-required-input",
                        evidence_reference="diagnostic:activities-presence",
                    )
                )
            elif activity_record_count == 0:
                # The Activities files can be read but hold no record that a
                # run keeps, such as an empty list, or only rows without a
                # usable identifier: the run stops with ACTIVITIES_EMPTY
                # (stage A5a).
                findings.append(
                    _finding(
                        "ACTIVITIES_EMPTY",
                        severity="ERROR",
                        actionability="ACTION_REQUIRED",
                        safe_message_id="ACTIVITIES_FILES_HOLD_NO_RECORDS",
                        next_action_id="SELECT_EXPORT_WITH_ACTIVITIES",
                        authority_reference="product:run-all-required-input",
                        evidence_reference="diagnostic:activities-presence",
                    )
                )
            else:
                findings.append(
                    _finding(
                        "RUN_ALL_NOT_EVALUATED",
                        severity="INFO",
                        actionability="NONE",
                        safe_message_id="INPUT_READY_FOR_BOUNDED_RUN_ALL_ATTEMPT",
                        next_action_id="RUN_ALL",
                        authority_reference="doctor_contract#pre-run-mode",
                        evidence_reference="diagnostic:pre-run-only",
                        not_evaluated_reason="RUN_ALL_NOT_EXECUTED",
                    )
                )
    actionable = any(item["actionability"] == "ACTION_REQUIRED" for item in findings)
    report = _base(
        product_version=__version__,
        mode="PRE_RUN",
        product_status=None,
        product_exit_code=None,
        availability="NOT_EVALUATED",
        completion_state="NOT_EVALUATED",
        usability_scope="NOT_EVALUATED",
        boundary_class="ACTIONABLE_CONDITION" if actionable else "NOT_EVALUATED",
        actionability="ACTION_REQUIRED" if actionable else "NONE",
        severity="ERROR" if actionable else "INFO",
        findings=findings,
        authority_references=["doctor_contract#pre-run-mode", "product:intake-discovery"],
    )
    # Only the report of the check has counts; the report after a run keeps
    # its fields, which the Support Bundle requires exactly (stage B3b).
    report["input_counts"] = counts
    return report


def _json_object(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise DoctorError("DOCTOR_AUTHORITY_INVALID", "required diagnostic authority is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError("DOCTOR_AUTHORITY_INVALID", "required diagnostic authority is invalid") from exc
    if not isinstance(value, dict):
        raise DoctorError("DOCTOR_AUTHORITY_INVALID", "required diagnostic authority is invalid")
    return value


def _major_minor(version: Any) -> tuple[int, int] | None:
    if not isinstance(version, str):
        return None
    parts = version.split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


def doctor_run_output(root: str | Path) -> dict[str, Any]:
    """Interpret a completed handoff, preserving version-aware authority."""
    requested = Path(root)
    output_root = requested.resolve()
    marker = output_root / "run_summary.json"
    if requested.is_symlink() or not marker.is_file():
        return _base(
            product_version=__version__,
            mode="POST_RUN",
            product_status=None,
            product_exit_code=None,
            availability="NOT_EVALUATED",
            completion_state="NOT_COMPLETED",
            usability_scope="NONE",
            boundary_class="FATAL_BOUNDARY",
            actionability="ACTION_REQUIRED",
            severity="ERROR",
            findings=[
                _finding(
                    "COMPLETION_MARKER_MISSING",
                    severity="ERROR",
                    actionability="ACTION_REQUIRED",
                    safe_message_id="NO_COMPLETED_RUN_EVIDENCE",
                    next_action_id="RUN_PRE_RUN_DOCTOR",
                    authority_reference="product:completion-marker",
                    evidence_reference="diagnostic:completion-marker",
                    not_evaluated_reason="COMPLETION_MARKER_MISSING",
                )
            ],
            authority_references=["run_summary.json"],
        )
    summary = _json_object(output_root, "run_summary.json")
    version = summary.get("product_version")
    parsed_version = _major_minor(version)
    if parsed_version is None or parsed_version[0] < 1:
        raise DoctorError("DOCTOR_VERSION_UNSUPPORTED", "handoff Product version is not recognized")
    try:
        validate_standalone_handoff(output_root)
    except StandaloneHandoffError as exc:
        raise DoctorError("DOCTOR_AUTHORITY_INVALID", "completed handoff integrity validation failed") from exc
    status = str(summary.get("status"))
    interpretation = interpretation_for_status(status)
    product_exit = exit_code_for_status(status)
    if parsed_version < (1, 4):
        reason = "V1_4_DIAGNOSTICS_NOT_AVAILABLE_FOR_LEGACY_HANDOFF"
        return _base(
            product_version=str(version),
            mode="POST_RUN",
            product_status=status,
            product_exit_code=product_exit,
            availability="LEGACY_NOT_AVAILABLE",
            completion_state=interpretation["completion_state"],
            usability_scope=interpretation["usability_scope"],
            boundary_class=interpretation["boundary_class"],
            actionability=interpretation["actionability"],
            severity=interpretation["severity"],
            findings=[
                _finding(
                    "V1_4_DIAGNOSTICS_NOT_AVAILABLE",
                    severity="INFO",
                    actionability=interpretation["actionability"],
                    safe_message_id="LEGACY_HANDOFF_PRESERVED_WITHOUT_V1_4_DIAGNOSTICS",
                    next_action_id="USE_RECORDED_LEGACY_RESULT",
                    authority_reference="doctor_contract#legacy-handoff",
                    evidence_reference="run_summary.json#/product_version",
                    not_evaluated_reason=reason,
                )
            ],
            authority_references=["run_summary.json", "run_manifest.json"],
        )
    completeness = _json_object(output_root, "diagnostics/source_completeness.json")
    quality = _json_object(output_root, "diagnostics/run_quality.json")
    if (
        quality.get("run_status") != status
        or quality.get("exit_code") != product_exit
        or quality.get("product_version") != version
        or completeness.get("product_version") != version
    ):
        raise DoctorError("DOCTOR_AUTHORITY_INVALID", "diagnostic authorities disagree")
    findings: list[dict[str, Any]] = []
    for warning in quality.get("warnings", []):
        if not isinstance(warning, dict) or warning.get("code") not in SAFE_WARNING_CODES:
            raise DoctorError("DOCTOR_UNREGISTERED_DIAGNOSTIC", "an unregistered diagnostic code was observed")
        findings.append(
            _finding(
                str(warning["code"]),
                severity="WARNING",
                actionability=interpretation["actionability"],
                safe_message_id=f"{warning['code']}_MESSAGE",
                next_action_id="REVIEW_RUN_QUALITY",
                authority_reference="diagnostics/run_quality.json#/warnings",
                evidence_reference="diagnostic:registered-warning",
            )
        )
    return _base(
        product_version=str(version),
        mode="POST_RUN",
        product_status=status,
        product_exit_code=product_exit,
        availability="CURRENT",
        completion_state=interpretation["completion_state"],
        usability_scope=interpretation["usability_scope"],
        boundary_class=interpretation["boundary_class"],
        actionability=interpretation["actionability"],
        severity=interpretation["severity"],
        findings=findings,
        authority_references=[
            "run_summary.json",
            "run_manifest.json",
            "diagnostics/source_completeness.json",
            "diagnostics/run_quality.json",
        ],
    )


def render_doctor_human(report: dict[str, Any]) -> str:
    """Render fixed, privacy-safe human output from the machine report."""
    lines = [
        f"Doctor: {report['mode']}",
        f"Completion: {report['completion_state']}",
        f"Usability: {report['usability_scope']}",
        f"Action: {report['actionability']}",
    ]
    # The counts of the input, before a run (stage B3b).
    counts = report.get("input_counts")
    if report["mode"] == "PRE_RUN" and isinstance(counts, dict):
        activities = counts["activity_records"]
        lines.append(
            "Counts: "
            f"activities={'not_counted' if activities is None else activities} "
            f"fit_files={counts['fit_files']} "
            f"files_read={counts['files_read']} "
            f"files_left_out={counts['files_left_out']} "
            f"files_not_read={counts['files_not_read']}"
        )
    if report["product_status"] is not None:
        lines.append(f"Product result: {report['product_status']} / exit {report['product_exit_code']}")
        lines.append(
            {
                "PASS": "Completed. Outputs are available within the declared Product contract.",
                "PASS_WITH_WARNINGS": (
                    "Completed with warnings. Outputs are available; review the warning "
                    "codes and affected scopes before use."
                ),
                # Exit 3 leaves out files and rows as well as FIT data (stage
                # B2b).
                "PARTIAL_SUCCESS": (
                    "Completed with bounded exclusions (PARTIAL_SUCCESS, exit 3). "
                    "This is not a fatal run failure. Outputs are available; review "
                    "what was left out before use."
                ),
            }[report["product_status"]]
        )
    elif report["completion_state"] == "NOT_COMPLETED":
        lines.append(
            "Run not completed (exit 2). No completed Run-All output was published. "
            "Run Doctor on the input and correct the reported condition."
        )
    # Each finding and the report give their next step in words, as the GUI
    # does (stage A5b); a finding whose code is a stop gives the next step of
    # that stop, as the run does (stage B2b). The identifiers stay first, for
    # programs that read the lines.
    for item in report["findings"]:
        step = finding_next_step(str(item.get("code")), str(item.get("next_action_id")))
        lines.append(f"Finding: {item['code']}" + (f" (next: {step})" if step else ""))
    next_id = str(report["doctor_next_action_id"])
    step = NEXT_ACTIONS.get(next_id)
    lines.append(f"Next: {next_id}" + (f" ({step})" if step else ""))
    return "\n".join(lines)


__all__ = ["DoctorError", "doctor_input", "doctor_run_output", "render_doctor_human"]
