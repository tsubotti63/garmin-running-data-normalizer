"""Local HTTP server for the GUI.

The server listens on 127.0.0.1 only, on a port chosen by the operating
system. It serves the packaged page from a fixed table and answers a small JSON
API. Every API request must carry the per-launch key in the X-Launch-Key
header. The key reaches the page in the URL fragment, which browsers never send
to a server. No cookie is used, because browsers send the cookies of a host to
every port on it, including servers that other programs or accounts run.
"""
from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
import time
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any

from .. import __version__
from ..common.json_depth import check_json_depth
from ..common.time import DEFAULT_TIMEZONE
from ..diagnostics.doctor import DoctorError, doctor_input
from ..intake.source import is_zip_input, place_can_be_shown
from ..stops import STOPS, stop_line
from .chooser import Chooser, ChooserError
from .folders import FolderError, list_folders
from ..run_all import RUN_ALL_VERSION
from .outputs import (
    OutputActionError,
    check_output,
    earlier_outputs,
    make_support_bundle,
    open_output,
    output_summary,
)
from .places import cloud_kind, default_folder, default_store
from .report import report_values
from .runs import (
    MAX_TIMEZONE_LENGTH,
    RunActiveError,
    RunManager,
    RunRequestError,
    absolute_path,
    output_name_problem,
)
from .layouts import BUILT_IN_IDS, USER_LAYOUT_ID, LayoutChangeError, built_in_answer
from .settings import (
    SHELF_STATES,
    THEMES,
    change_layouts,
    forget_settings,
    launch_settings,
    recent_outputs,
    remember_hints,
    remember_theme,
    remember_view,
)
from .stores import check_store, download_time, open_store, store_place, unlock_store
from .views import ViewNotOpenError, ViewRequestError, Views, grain_ok, item_table, period_choice, series_request, types_ok
from ..view.items import ITEMS_BY_KEY
from ..view.series import MAX_ANSWER_BYTES, MAX_PANELS, activity_types, coverage, default_items, view_answer


HOST = "127.0.0.1"
LAUNCH_KEY_HEADER = "X-Launch-Key"
LANGUAGES = ("en", "ja")
# The page sends a heartbeat every 30 seconds. Browsers may slow the timers of
# background tabs to once a minute, and Safari stops those of a window hidden
# with Command-H a few minutes later: with 10 minutes, the GUI stopped about
# 14 minutes after Safari was hidden (stage G5p). So the server waits an hour;
# a page that was closed leaves it running for that long.
IDLE_TIMEOUT_SECONDS = 3600.0
MAX_REQUEST_BYTES = 64 * 1024
REQUEST_TIMEOUT_SECONDS = 30.0

# Content types are fixed here instead of coming from mimetypes: Windows can
# map .js to text/plain through the registry, and nosniff then blocks scripts.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
    "/flow.mjs": ("flow.mjs", "text/javascript; charset=utf-8"),
    "/i18n.mjs": ("i18n.mjs", "text/javascript; charset=utf-8"),
    # The classic script that sets the colors before the page is drawn
    # (stage G3a).
    "/theme.js": ("theme.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    # The key of a launch and the calls of the API, which both pages share,
    # and the view page, in a tab of its own (stage G3b).
    "/launch.mjs": ("launch.mjs", "text/javascript; charset=utf-8"),
    "/view": ("view.html", "text/html; charset=utf-8"),
    "/view.mjs": ("view.mjs", "text/javascript; charset=utf-8"),
    "/view_flow.mjs": ("view_flow.mjs", "text/javascript; charset=utf-8"),
    "/view_chart.mjs": ("view_chart.mjs", "text/javascript; charset=utf-8"),
    "/view.css": ("view.css", "text/css; charset=utf-8"),
    "/i18n/en.json": ("i18n/en.json", "application/json"),
    "/i18n/ja.json": ("i18n/ja.json", "application/json"),
    # The picture of the app in the tab of the browser (stage E1i): SVG, and
    # PNG for a browser that shows no SVG there.
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/favicon.png": ("favicon.png", "image/png"),
}

SECURITY_HEADERS = (
    (
        "Content-Security-Policy",
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'none'",
    ),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("Cache-Control", "no-store"),
)

ERROR_CODES = {
    HTTPStatus.BAD_REQUEST: "BAD_REQUEST",
    HTTPStatus.FORBIDDEN: "FORBIDDEN",
    HTTPStatus.NOT_FOUND: "NOT_FOUND",
    HTTPStatus.METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    HTTPStatus.LENGTH_REQUIRED: "LENGTH_REQUIRED",
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE: "REQUEST_TOO_LARGE",
    HTTPStatus.REQUEST_URI_TOO_LONG: "URI_TOO_LONG",
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE: "HEADERS_TOO_LARGE",
    HTTPStatus.INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    HTTPStatus.NOT_IMPLEMENTED: "NOT_IMPLEMENTED",
    HTTPStatus.HTTP_VERSION_NOT_SUPPORTED: "HTTP_VERSION_NOT_SUPPORTED",
}

API_ROUTES = {
    "/api/status": "_api_status",
    "/api/heartbeat": "_api_heartbeat",
    "/api/shutdown": "_api_shutdown",
    "/api/folders": "_api_folders",
    "/api/choose": "_api_choose",
    "/api/choose/status": "_api_choose_status",
    "/api/check-input": "_api_check_input",
    "/api/store/open": "_api_store_open",
    "/api/store/place": "_api_store_place",
    "/api/store/check": "_api_store_check",
    "/api/store/unlock": "_api_store_unlock",
    "/api/place": "_api_place",
    "/api/run/start": "_api_run_start",
    "/api/run/status": "_api_run_status",
    "/api/run/cancel": "_api_run_cancel",
    "/api/outputs": "_api_outputs",
    "/api/check-output": "_api_check_output",
    "/api/support-bundle": "_api_support_bundle",
    "/api/open-output": "_api_open_output",
    "/api/settings/hints": "_api_settings_hints",
    "/api/settings/theme": "_api_settings_theme",
    "/api/settings/view": "_api_settings_view",
    "/api/settings/layouts": "_api_settings_layouts",
    "/api/settings/forget": "_api_settings_forget",
    # The view page (stage G3b): an output opened, and its numbers.
    "/api/view/open": "_api_view_open",
    "/api/view/series": "_api_view_series",
}


class ApiError(Exception):
    """An API answer other than 200, given to the page as a short code, and
    for an output that another version made, that version (stage B5b)."""

    def __init__(self, status: int, code: str, version: str | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.version = version


def _choosable_path(input_path: Path, place: str) -> str | None:
    """The full place of an Export found in a chosen folder, which the page
    can offer to choose (stage B3c): never in a ZIP file, never the input
    itself, and never outside the input. Links are not followed; choosing it
    checks it as any chosen place."""
    if not input_path.is_dir() or not place:
        return None
    parts = place.split("/")
    if place.startswith("/") or any(part in ("", ".", "..") for part in parts):
        return None
    return str(input_path.joinpath(*parts))


def _exports_found(input_path: Path, found: Any) -> list[dict[str, Any]]:
    """The Exports of a mixed input for the page: each place, or None for a
    name that cannot be shown, whether it is a ZIP file, the number of the
    first one with the same files, and the full place to choose it."""
    if not isinstance(found, list):
        return []
    places = [item["place"] for item in found]
    exports = []
    for item in found:
        place = item["place"]
        shown = place_can_be_shown(place)
        same = item["same_as"]
        exports.append(
            {
                "place": place if shown else None,
                "zip": bool(item["zip"]),
                "same_as": places.index(same) if same in places else None,
                "path": _choosable_path(input_path, place) if shown else None,
            }
        )
    return exports


def _not_readable(places: Any) -> dict[str, Any] | None:
    """The first folder or file that cannot be opened, and how many more, as
    the page shows them after a run (stage B3c)."""
    if not isinstance(places, list) or not places:
        return None
    first = places[0]
    return {"place": first if place_can_be_shown(first) else None, "more": len(places) - 1}


def _iso(day: int | None) -> str | None:
    return None if day is None else date.fromordinal(day).isoformat()


def _command_failed() -> ApiError:
    """The answer to an unexpected error of a check, the Support Bundle, or
    opening the output: the code with which the CLI's commands stop for one
    (stage A5b-2). The server's own errors answer INTERNAL_ERROR."""
    return ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "COMMAND_FAILED")


def json_body(payload: dict[str, Any]) -> bytes:
    """The bytes of an answer, as the server sends it."""
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def load_static_files() -> dict[str, tuple[bytes, str]]:
    """Read every file in STATIC_FILES from the installed package."""
    root = files(__package__).joinpath("static")
    loaded: dict[str, tuple[bytes, str]] = {}
    for url_path, (resource, content_type) in STATIC_FILES.items():
        node = root
        for part in resource.split("/"):
            node = node.joinpath(part)
        loaded[url_path] = (node.read_bytes(), content_type)
    return loaded


def _json_object(body: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(body.decode("utf-8"))
        check_json_depth(value)
    except (UnicodeDecodeError, ValueError, RecursionError):
        # Not UTF-8, not JSON, nested too deeply, or a number with too many
        # digits, the same on every version of Python (stage E2d).
        return None
    return value if isinstance(value, dict) else None


class GuiServer(ThreadingHTTPServer):
    """Serve one GUI launch on 127.0.0.1 with a port chosen by the operating system."""

    daemon_threads = True

    def __init__(
        self,
        *,
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
        runs: RunManager | None = None,
        chooser: Chooser | None = None,
    ) -> None:
        if idle_timeout <= 0:
            raise ValueError("idle_timeout must be positive")
        self.static_files = load_static_files()
        self.runs = runs if runs is not None else RunManager()
        self.chooser = chooser if chooser is not None else Chooser()
        self.launch_key = secrets.token_urlsafe(32)
        # The Support Bundle that this server made last, which the page may
        # show in its folder (stage B5a).
        self.bundle: Path | None = None
        # The outputs of earlier runs that the page may choose, by their
        # number in the last list that it was given, and the mark of that list
        # (stage B5b).
        self.earlier: tuple[int, list[Path]] = (0, [])
        # The outputs that the view page opened, by their tickets, and what
        # it read of them, in memory only (stage G3b).
        self.views = Views()
        self.idle_timeout = idle_timeout
        self._last_request = time.monotonic()
        self._lock = threading.Lock()
        super().__init__((HOST, 0), GuiRequestHandler)
        self.origin = f"http://{HOST}:{self.server_port}"
        self.expected_host = f"{HOST}:{self.server_port}"

    @property
    def url(self) -> str:
        """Return the address to open; the key stays in the fragment."""
        return f"{self.origin}/#key={self.launch_key}"

    def server_bind(self) -> None:
        # Bind without address reuse, and on Windows for exclusive use, so that
        # no other program can listen on the same port. The host name lookup in
        # HTTPServer.server_bind is skipped; the address is always 127.0.0.1.
        exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
        if exclusive is not None:
            self.socket.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        self.server_name = HOST
        self.server_port = self.server_address[1]

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Ignore connection errors; the server writes nothing to the terminal."""

    def record_request(self) -> None:
        with self._lock:
            self._last_request = time.monotonic()

    def idle_seconds(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_request

    def stop_soon(self) -> None:
        """Stop serve_forever from a request thread without waiting for it."""
        threading.Thread(target=self.shutdown, daemon=True).start()


class GuiRequestHandler(BaseHTTPRequestHandler):
    """Answer the requests of one GuiServer; every response has SECURITY_HEADERS."""

    server: GuiServer
    timeout = REQUEST_TIMEOUT_SECONDS
    # An error found before the request line gives a version is answered as
    # HTTP/1.0, so that it also has a status line and SECURITY_HEADERS.
    default_request_version = "HTTP/1.0"

    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        if len(self.requestline.split()) != 3:
            status = HTTPStatus.BAD_REQUEST
        elif self.request_version not in ("HTTP/1.0", "HTTP/1.1"):
            status = HTTPStatus.HTTP_VERSION_NOT_SUPPORTED
        else:
            return True
        # An HTTP/0.9 answer has no status line or headers, so a refused
        # request is always answered as HTTP/1.0.
        self.request_version = self.default_request_version
        self.send_error(status)
        return False

    def log_message(self, format: str, *args: Any) -> None:
        """Write nothing, so that paths and keys never reach the terminal."""

    def end_headers(self) -> None:
        for name, value in SECURITY_HEADERS:
            self.send_header(name, value)
        super().end_headers()

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        """Answer an error with a short JSON code; request text is never echoed."""
        self._send_json(code, {"error": ERROR_CODES.get(code, "HTTP_ERROR")}, close=True)

    def do_GET(self) -> None:
        if not self._host_allowed():
            self.send_error(HTTPStatus.FORBIDDEN)
        elif self.path in self.server.static_files:
            body, content_type = self.server.static_files[self.path]
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in API_ROUTES:
            self._method_not_allowed("POST")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        body = self._read_body()
        if body is None:
            return
        if not self._host_allowed():
            self.send_error(HTTPStatus.FORBIDDEN)
        elif self.path in self.server.static_files:
            self._method_not_allowed("GET")
        elif self.path not in API_ROUTES:
            self.send_error(HTTPStatus.NOT_FOUND)
        elif not (self._origin_allowed() and self._launch_key_valid()):
            self.send_error(HTTPStatus.FORBIDDEN)
        elif not self._json_content_type():
            self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        else:
            payload = _json_object(body)
            if payload is None:
                self.send_error(HTTPStatus.BAD_REQUEST)
            else:
                self._answer_api(payload)

    def _host_allowed(self) -> bool:
        return self.headers.get_all("Host") == [self.server.expected_host]

    def _origin_allowed(self) -> bool:
        origins = self.headers.get_all("Origin")
        return origins is None or origins == [self.server.origin]

    def _launch_key_valid(self) -> bool:
        values = self.headers.get_all(LAUNCH_KEY_HEADER) or []
        return len(values) == 1 and hmac.compare_digest(
            values[0].encode("utf-8"), self.server.launch_key.encode("ascii")
        )

    def _json_content_type(self) -> bool:
        content_type = self.headers.get("Content-Type") or ""
        return content_type.split(";", 1)[0].strip().lower() == "application/json"

    def _read_body(self) -> bytes | None:
        """Return the request body, or answer the error and return None.

        The body is read before any other check: closing a connection with
        unread data can reset it and cut off the error answer. A body over
        MAX_REQUEST_BYTES is not read, so its sender may see a reset instead of
        413; the page itself sends only small bodies.
        """
        lengths = self.headers.get_all("Content-Length") or []
        if not lengths:
            self.send_error(HTTPStatus.LENGTH_REQUIRED)
            return None
        if len(lengths) != 1 or not (lengths[0].isascii() and lengths[0].isdigit()):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return None
        length = int(lengths[0])
        if length > MAX_REQUEST_BYTES:
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return None
        return self.rfile.read(length)

    def _answer_api(self, payload: dict[str, Any]) -> None:
        self.server.record_request()
        try:
            result = getattr(self, API_ROUTES[self.path])(payload)
        except ApiError as exc:
            answer: dict[str, Any] = {"error": exc.code}
            if exc.version is not None:
                answer["version"] = exc.version
            self._send_json(exc.status, answer)
            return
        except Exception:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json(HTTPStatus.OK, result)
        if self.path == "/api/shutdown":
            self.server.stop_soon()

    def _api_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The page takes the product's default timezone from here, so that
        # it has no default of its own (stage A5a).
        # The default places, which only the GUI has (stage B4a).
        # The settings of an earlier launch (stage B4c), read when the page
        # starts: the places of the last run that made its output, whether
        # the tips show, and what to tell of the file.
        # This computer's values of the GitHub report, which the help panel
        # shows before the person opens it (stage B5c).
        return {
            "default_output_parent": str(default_folder()),
            "default_store": str(default_store()),
            "default_timezone": DEFAULT_TIMEZONE,
            "languages": list(LANGUAGES),
            "product_version": __version__,
            "report": report_values(),
            "settings": launch_settings(),
        }

    def _api_heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok"}

    def _api_shutdown(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.server.runs.active():
            raise ApiError(HTTPStatus.CONFLICT, "RUN_ACTIVE")
        return {"status": "stopping"}

    def _api_folders(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return list_folders(payload.get("path"), zips=payload.get("zips") is True)
        except FolderError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc

    def _api_choose(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The operating system's own dialog (stage B3a). The request returns
        # once the dialog opens; the page asks for its answer.
        try:
            self.server.chooser.start(payload.get("kind"))
        except ChooserError as exc:
            status = HTTPStatus.CONFLICT if exc.code == "CHOOSER_BUSY" else HTTPStatus.UNPROCESSABLE_ENTITY
            raise ApiError(status, exc.code) from exc
        return {"state": "open"}

    def _api_choose_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.server.chooser.status()

    def _api_check_input(self, payload: dict[str, Any]) -> dict[str, Any]:
        timezone_name = payload.get("timezone", DEFAULT_TIMEZONE)
        if (
            not isinstance(timezone_name, str)
            or not timezone_name
            or len(timezone_name) > MAX_TIMEZONE_LENGTH
        ):
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "TIMEZONE_INVALID")
        # The places that the check found, for the page only (stage B3c).
        details: dict[str, Any] = {}
        try:
            input_path = absolute_path(payload.get("input"), "INPUT_PATH_INVALID")
            report = doctor_input(input_path, timezone_name=timezone_name, details=details)
        except (RunRequestError, DoctorError) as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        except Exception as exc:
            raise _command_failed() from exc
        # Whether the input is a ZIP file or a folder, for the confirmation
        # that a folder was extracted completely (stage B3a).
        kind = "zip" if is_zip_input(input_path) else "folder" if input_path.is_dir() else None
        findings = [
            {
                "code": finding["code"],
                "severity": finding["severity"],
                "message_id": finding["safe_message_id"],
                "next_action_id": finding["next_action_id"],
            }
            for finding in report["findings"]
        ]
        # The counts of the input, numbers only, as the CLI's Doctor gives
        # them (stage B3b).
        counts = report.get("input_counts")
        # The download time that an import proposes, and where it came from
        # (stage B4b-1).
        downloaded_at, downloaded_from = download_time(input_path) if kind is not None else (None, None)
        return {
            "downloaded_at": downloaded_at,
            "downloaded_from": downloaded_from,
            "ready": all(finding["severity"] != "ERROR" for finding in findings),
            "input_kind": kind,
            "counts": dict(counts) if isinstance(counts, dict) else None,
            "exports_found": _exports_found(input_path, details.get("exports_found")),
            "not_readable": _not_readable(details.get("not_readable_places")),
            "findings": findings,
        }

    def _store_answer(self, payload: dict[str, Any], action: Any) -> dict[str, Any]:
        # The Snapshot Store (stage B4a): a problem of the store is an
        # answer, which the page shows beside the store; only a request that
        # is not valid, or an unexpected error, is refused.
        try:
            path = absolute_path(payload.get("path"), "PATH_INVALID")
        except RunRequestError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        try:
            return action(path)
        except Exception as exc:
            raise _command_failed() from exc

    def _api_store_open(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._store_answer(payload, open_store)

    def _api_store_place(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._store_answer(payload, store_place)

    def _api_store_check(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._store_answer(payload, check_store)

    def _api_store_unlock(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The lock file that a stopped import left (stage B4b-2): never while
        # a run of this app could hold it, and only with the person's check
        # that no other command uses the store.
        if self.server.runs.active():
            raise ApiError(HTTPStatus.CONFLICT, "RUN_ACTIVE")
        return self._store_answer(payload, lambda path: unlock_store(path, payload.get("confirmed")))

    def _api_place(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The folder for the output: whether it is there, whether it is the
        # default place, which a run makes, and whether a cloud may copy it;
        # with a name, what keeps it from being a new output there, as the
        # start of a run checks it (stage B5a).
        name = payload.get("name")

        def look(path: Path) -> dict[str, Any]:
            try:
                exists: bool | None = path.is_dir()
            except OSError:
                exists = None
            answer: dict[str, Any] = {"default": path == default_folder(), "exists": exists, "cloud": cloud_kind(path)}
            if name is not None:
                answer["name_problem"] = output_name_problem(path, name)
            return answer

        return self._store_answer(payload, look)

    def _api_run_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.server.runs.start(payload)
        except RunActiveError as exc:
            raise ApiError(HTTPStatus.CONFLICT, exc.code) from exc
        except RunRequestError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        except OSError as exc:
            raise ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "RUN_START_FAILED") from exc

    def _api_run_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.server.runs.status()

    def _api_run_cancel(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.server.runs.cancel()

    def _finished_output(self) -> Path:
        # Output actions use only the folder that this server's last run
        # published; the page never names a path for them.
        output = self.server.runs.finished_output()
        if output is None:
            raise ApiError(HTTPStatus.CONFLICT, "NO_FINISHED_OUTPUT")
        return output

    def _api_outputs(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The outputs that earlier runs made, which the page may choose for the
        # check and the Support Bundle, by their number in this list and its
        # mark; and the output before the last run, with the counts that the
        # page compares a run with (stage B5b). A list given to another tab
        # since then makes a number of this one refused.
        found = earlier_outputs(recent_outputs(), self.server.runs.finished_output())
        # A list of the same outputs keeps its mark, so that the numbers that
        # the other tab was given still name them (stage G3b: the view page is
        # always another tab); a changed list gets a new mark.
        with self.server._lock:
            mark, given = self.server.earlier
            if found != given:
                mark += 1
            self.server.earlier = (mark, found)
        previous = None
        for index, output in enumerate(found):
            summary = output_summary(output)
            if summary is not None:
                previous = {"index": index, **summary}
                break
        return {
            "list": mark,
            "outputs": [{"index": index, "name": output.name, "path": str(output)} for index, output in enumerate(found)],
            "previous": previous,
            "current": {"version": __version__, "run_all_version": RUN_ALL_VERSION},
        }

    def _target_output(self, payload: dict[str, Any]) -> Path:
        # The output of an action (stage B5b): the one that this server's last
        # run published (the default), one of the list of earlier outputs by
        # its number and the list's mark, or a folder that the person chose,
        # which the check of the output then takes or refuses.
        kind = payload.get("output", "run")
        if kind == "run":
            return self._finished_output()
        if kind == "earlier":
            index, mark = payload.get("index"), payload.get("list")
            with self.server._lock:
                current, found = self.server.earlier
            if not isinstance(index, int) or isinstance(index, bool) or not isinstance(mark, int) or isinstance(mark, bool):
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
            if mark != current:
                raise ApiError(HTTPStatus.CONFLICT, "OUTPUT_LIST_CHANGED")
            if not 0 <= index < len(found):
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
            return found[index]
        if kind == "chosen":
            try:
                return absolute_path(payload.get("path"), "PATH_INVALID")
            except RunRequestError as exc:
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")

    def _api_check_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        output = self._target_output(payload)
        try:
            return check_output(output)
        except OutputActionError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code, exc.version) from exc
        except Exception as exc:
            raise _command_failed() from exc

    def _api_support_bundle(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Next to the output, or in the folder that the person chose, which the
        # CLI's checks of the place of a Support Bundle take (stage B5a); for
        # the output of the action (stage B5b).
        output = self._target_output(payload)
        folder: Path | None = None
        if payload.get("folder") is not None:
            try:
                folder = absolute_path(payload.get("folder"), "PATH_INVALID")
            except RunRequestError as exc:
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        try:
            answer = make_support_bundle(output, folder)
        except OutputActionError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code, exc.version) from exc
        except Exception as exc:
            raise _command_failed() from exc
        self.server.bundle = Path(answer["path"])
        return answer

    def _api_open_output(self, payload: dict[str, Any]) -> dict[str, Any]:
        output = self._finished_output()
        try:
            open_output(output, payload.get("target"), self.server.bundle)
        except OutputActionError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        except Exception as exc:
            raise _command_failed() from exc
        return {"status": "opened"}

    def _api_settings_hints(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The person switched the tips; the next launch shows them so too
        # (stage B4c).
        on = payload.get("on")
        if not isinstance(on, bool):
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
        notice = remember_hints(on)
        return {"remembered": notice is None, "notice": notice}

    def _api_settings_theme(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The person chose the colors of the page, and the next launch opens
        # in them (stage G3a); "auto" follows the colors that the browser
        # reports, and is remembered as no choice.
        theme = payload.get("theme")
        if theme != "auto" and theme not in THEMES:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
        notice = remember_theme(None if theme == "auto" else theme)
        return {"remembered": notice is None, "notice": notice}

    def _api_settings_view(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The items that the view page shows and whether its item shelf is
        # open, which its next opening shows again (stage G3b); and from
        # v2.2.0 (stage K1), when the page gives them, the layout used last
        # (None for none), the period, the grouping, and the activity types
        # (None for those counted at first), by the rules of a request of the
        # numbers.
        items, shelf = payload.get("items"), payload.get("shelf")
        if (
            not isinstance(items, list)
            or len(items) > MAX_PANELS
            or any(not isinstance(key, str) or key not in ITEMS_BY_KEY for key in items)
            or len(set(items)) != len(items)
            or shelf not in SHELF_STATES
        ):
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
        view: dict[str, Any] = {}
        if "layout" in payload:
            layout = payload["layout"]
            if layout is not None and not (isinstance(layout, str) and (layout in BUILT_IN_IDS or USER_LAYOUT_ID.fullmatch(layout))):
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
            view["layout"] = layout
        if "period" in payload:
            if period_choice(payload["period"]) is None:
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
            view["period"] = payload["period"]
        if "grain" in payload:
            if not grain_ok(payload["grain"]):
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
            view["grain"] = payload["grain"]
        if "types" in payload:
            if payload["types"] is not None and not types_ok(payload["types"]):
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
            view["types"] = payload["types"]
        notice = remember_view(items, shelf, view)
        return {"remembered": notice is None, "notice": notice}

    def _api_settings_layouts(self, payload: dict[str, Any]) -> dict[str, Any]:
        # One change of the layouts of the view page (stage K1 of v2.2.0):
        # the layouts after it, or as they were when it was not written; a
        # change that cannot be made answers its code.
        try:
            layouts, notice = change_layouts(payload)
        except LayoutChangeError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code) from exc
        return {
            "remembered": notice is None,
            "notice": notice,
            "layouts": layouts["layouts"],
            "hidden": layouts["hidden"],
            "layout": layouts["current"],
        }

    def _api_view_open(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The view page opens an output as an action of the fourth box
        # chooses one (stage B5b), and checks it as the check of an output
        # does; the answer names the output by its ticket, never by its
        # place (stage G3b).
        output = self._target_output(payload)
        try:
            ticket, data = self.server.views.open(output)
        except OutputActionError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code, exc.version) from exc
        except Exception as exc:
            raise _command_failed() from exc
        return {
            "view": ticket,
            "name": output.name,
            "version": data.version,
            "partial": data.partial,
            "first_day": _iso(data.first_day),
            "last_day": _iso(data.last_day),
            "items": item_table(),
            "types": activity_types(data),
            "first_items": default_items(data),
            # The built-in layouts (stage K1 of v2.2.0).
            "layouts": built_in_answer(),
            "coverage": coverage(data),
        }

    def _api_view_series(self, payload: dict[str, Any]) -> dict[str, Any]:
        # The numbers of the view page for an output that it opened (stage
        # G3b), with the bars of the item shelf for the activity types.
        ticket = payload.get("view")
        try:
            if not isinstance(ticket, str):
                raise ViewRequestError("view")
            items, period, grain, types = series_request(payload)
        except ViewRequestError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID") from exc
        try:
            data = self.server.views.data(ticket)
        except ViewNotOpenError as exc:
            raise ApiError(HTTPStatus.CONFLICT, "VIEW_NOT_OPEN") from exc
        except OutputActionError as exc:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, exc.code, exc.version) from exc
        except Exception as exc:
            raise _command_failed() from exc
        if types is not None and not set(types) <= {entry["name"] for entry in activity_types(data)}:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "REQUEST_INVALID")
        answer = view_answer(data, items, period, grain, types)
        answer["coverage"] = coverage(data, types)
        if len(json_body(answer)) > MAX_ANSWER_BYTES:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "VIEW_ANSWER_TOO_LARGE")
        return answer

    def _api_settings_forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Forget the remembered settings (stage B4c): never while a run of
        # this page is active, which remembers its places when it ends. The
        # stores and the outputs stay.
        if self.server.runs.active():
            raise ApiError(HTTPStatus.CONFLICT, "RUN_ACTIVE")
        # Whether there was anything to forget tells the page what to say
        # (stage C1); "forgotten" says that no file is left.
        notice, present = forget_settings()
        return {"forgotten": notice is None, "had_settings": present, "notice": notice}

    def _method_not_allowed(self, allow: str) -> None:
        self._send_json(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {"error": ERROR_CODES[HTTPStatus.METHOD_NOT_ALLOWED]},
            allow=allow,
            close=True,
        )

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
        *,
        allow: str | None = None,
        close: bool = False,
    ) -> None:
        body = json_body(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if allow is not None:
            self.send_header("Allow", allow)
        if close:
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def serve_until_stopped(
    server: GuiServer, *, poll_interval: float = 0.5
) -> dict[str, Any] | None:
    """Serve until Ctrl+C, /api/shutdown, or idle_timeout without an API request.

    The server does not stop for idleness while a run is active, and
    /api/shutdown is refused then. On Ctrl+C an active run is cancelled
    first, and its status is returned, for ``cancel_report`` (stage A5c);
    otherwise None. The listening socket is closed before this function
    returns.
    """
    stopped: dict[str, Any] | None = None
    finished = threading.Event()

    def stop_when_idle() -> None:
        check_interval = min(server.idle_timeout / 4, 5.0)
        while not finished.wait(check_interval):
            # A run keeps the server alive even when no page asks for news.
            if server.idle_seconds() > server.idle_timeout and not server.runs.active():
                server.shutdown()
                return

    try:
        # Ctrl+C before the server serves stops it as after the Quit button
        # (stage D1).
        threading.Thread(target=stop_when_idle, daemon=True).start()
        server.serve_forever(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass
    finally:
        finished.set()
        # A dialog that is still open closes with the server.
        server.chooser.stop()
        active = server.runs.active()
        server.runs.stop()
        if active:
            stopped = server.runs.status()
        server.server_close()
    return stopped


def cancel_report(status: dict[str, Any]) -> list[str]:
    """The lines for the terminal about the run that Ctrl+C stopped with the
    server: the content that the CLI prints for a cancelled command, and the
    names of the staging folders that it left, one on a line (stage A5c)."""
    state = status.get("state")
    if state == "finished_after_cancel":
        lines = [
            stop_line(
                "RUN_CANCELLED_AFTER_OUTPUT",
                "the run of the GUI was cancelled with Ctrl+C after it wrote its output",
            )
        ]
    elif state == "cancelled":
        lines = [stop_line("RUN_CANCELLED", "the run of the GUI was cancelled with Ctrl+C")]
    elif state == "failed" and status.get("error_code") in STOPS:
        code = str(status["error_code"])
        lines = [stop_line(code, STOPS[code].what)]
    else:
        return []
    for name in status.get("staging_folders") or []:
        lines.append(f"left next to the output: {name}")
    return lines


__all__ = [
    "GuiServer",
    "IDLE_TIMEOUT_SECONDS",
    "LANGUAGES",
    "LAUNCH_KEY_HEADER",
    "STATIC_FILES",
    "cancel_report",
    "load_static_files",
    "serve_until_stopped",
]
