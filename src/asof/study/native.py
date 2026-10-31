"""One-use owned-loopback native transport and pure replay verification.

No discovery by backend ID, redirects, proxies, automatic retry or model loading.
The caller owns launch proofs and the process. Raw native bytes are never replaced
by translated claims; partial captures remain explicitly incomplete.
"""

import base64
import hashlib
import http.client
import math
from pathlib import Path
import re
import socket
import struct
from threading import Lock, Timer
import time
from urllib.parse import urlsplit

from asof.agents import Usage
from asof.atomic import publish_bytes
from asof.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json
from .diagnostic import REQUIRED_RESOURCES, prepare_payload, validate_output
from .session import BackendCapabilities, GeneratedBytes, _identity, need

PROTOCOL = "owned-loopback-native-wrapper-v1"
MAX_ORIGINAL_RESPONSE = 512 * 1024
MAX_WRAPPER_RESPONSE = 1024 * 1024
WRAPPER_FIELDS = {
    "schema_version",
    "kind",
    "request_sha256",
    "payload_sha256",
    "owner_pid",
    "endpoint",
    "http_status",
    "body_base64",
    "body_sha256",
    "complete",
    "error_class",
    "elapsed_seconds",
}


def windows_listener_owner(pid, host, port):
    """Read the Windows IPv4 listener table; access errors never imply ownership."""
    import ctypes
    from ctypes import wintypes
    import os

    need(
        os.name == "nt"
        and type(pid) is int
        and pid > 0
        and host == "127.0.0.1"
        and type(port) is int
        and 1 <= port <= 65535,
        "Invalid Windows listener query",
    )
    function = ctypes.WinDLL("iphlpapi", use_last_error=True).GetExtendedTcpTable
    function.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.BOOL,
        wintypes.ULONG,
        ctypes.c_int,
        wintypes.ULONG,
    ]
    function.restype = wintypes.DWORD
    size = wintypes.DWORD(0)
    status = function(None, ctypes.byref(size), False, socket.AF_INET, 3, 0)
    if status not in (0, 122):
        raise OSError(int(status), "Listener table size query failed")
    need(4 <= size.value <= 1024 * 1024, "Listener table exceeds inspection bound")
    buffer = ctypes.create_string_buffer(size.value)
    status = function(buffer, ctypes.byref(size), False, socket.AF_INET, 3, 0)
    if status != 0:
        raise OSError(int(status), "Listener table read failed; no fallback")
    count = struct.unpack_from("<I", buffer.raw)[0]
    need(4 + 24 * count <= min(len(buffer), size.value), "Incomplete listener table")
    matches = []
    for index in range(count):
        state, address, raw_port, _, _, owner = struct.unpack_from(
            "<6I", buffer.raw, 4 + index * 24
        )
        if socket.ntohs(raw_port & 0xFFFF) == port:
            matches.append((state, socket.inet_ntoa(struct.pack("<I", address)), owner))
    return matches == [(2, host, pid)]


def _watchdog(transport_socket, deadline):
    # A socket timeout alone can reset on each internal header read. A bounded
    # watchdog closes only this retained connection at the absolute deadline.
    def expire():
        try:
            transport_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            transport_socket.close()

    timer = Timer(_remaining(deadline), expire)
    timer.daemon = True
    timer.start()
    return timer


def bounded_health_probe(host, port, timeout):
    """OwnedServer must establish listener ownership before calling this GET."""
    need(
        host == "127.0.0.1"
        and type(port) is int
        and 1 <= port <= 65535
        and type(timeout) in (int, float)
        and math.isfinite(timeout)
        and timeout > 0,
        "Invalid bounded health query",
    )
    deadline = time.monotonic() + timeout
    connection = http.client.HTTPConnection(host, port, timeout=_remaining(deadline))
    response = timer = None
    try:
        connection.connect()
        need(connection.sock is not None, "Missing health transport socket")
        timer = _watchdog(connection.sock, deadline)
        connection.request("GET", "/health")
        response = connection.getresponse()
        _remaining(deadline)
        return type(response.status) is int and response.status == 200
    finally:
        import sys

        primary = sys.exception()
        cleanup_error = None
        actions = [timer.cancel] if timer is not None else []
        actions += ([response.close] if response is not None else []) + [
            connection.close
        ]
        for action in actions:
            try:
                action()
            except BaseException as error:
                if primary is not None:
                    primary.add_note(
                        "Health transport close failed: " + type(error).__name__
                    )
                elif cleanup_error is None:
                    cleanup_error = error
        if cleanup_error is not None:
            raise cleanup_error


def _endpoint(value):
    need(isinstance(value, str), "Explicit loopback endpoint required")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ContractError("Invalid loopback endpoint") from error
    need(
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and type(port) is int
        and 1 <= port <= 65535
        and not parsed.username
        and not parsed.password
        and parsed.path in ("", "/")
        and not parsed.query
        and not parsed.fragment,
        "Native endpoint must be explicit IPv4 loopback",
    )
    return f"http://127.0.0.1:{port}", port


def _model(value):
    value = encode(value)
    need(
        isinstance(value, dict)
        and {"weights_sha256", "runtime_sha256"} <= set(value)
        and set(value)
        <= {
            "weights_sha256",
            "runtime_sha256",
            "asset_manifest_sha256",
            "model_id",
            "revision",
        },
        "Invalid native model provenance",
    )
    weights = value["weights_sha256"]
    need(
        isinstance(weights, dict)
        and weights
        and all(isinstance(k, str) and k.strip() for k in weights),
        "Missing native weights provenance",
    )
    digests = list(weights.values()) + [value["runtime_sha256"]]
    if "asset_manifest_sha256" in value:
        digests.append(value["asset_manifest_sha256"])
    need(
        all(isinstance(v, str) and re.fullmatch("[0-9a-f]{64}", v) for v in digests),
        "Invalid native asset digest",
    )
    need(
        all(
            isinstance(value[k], str) and value[k].strip()
            for k in ("model_id", "revision")
            if k in value
        ),
        "Invalid native model identity",
    )
    return freeze(value)


def _alias(value):
    need(
        isinstance(value, str)
        and value.strip()
        and len(value) <= 256
        and not any(ord(c) < 32 for c in value),
        "Invalid native model alias",
    )
    return value


def _check_owner(owner, port, expected_pid=None):
    """Bind readiness to this transport endpoint, not merely any owned server."""
    need(
        callable(getattr(owner, "assert_ready", None)),
        "Explicit owned-server guard required",
    )
    for check_ready in (True, False):
        spec = getattr(owner, "spec", None)
        need(
            getattr(spec, "host", None) == "127.0.0.1"
            and type(getattr(spec, "port", None)) is int
            and spec.port == port,
            "Native endpoint differs from owned-server specification",
        )
        if check_ready:
            owner.assert_ready()
    pid = owner.terminal_record.get("pid")
    need(
        type(pid) is int and pid > 0 and (expected_pid is None or pid == expected_pid),
        "Owned process identity missing or changed",
    )
    return pid


def _usage(native):
    need(isinstance(native, dict), "Native response must be an object")
    usage = Usage(native.get("tokens_evaluated"), native.get("tokens_predicted"), 0.0)
    usage.validate()
    return usage


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Native absolute deadline exceeded")
    return remaining


def _complete(native):
    need(native.get("truncated") is False, "Native prompt completeness unqualified")
    for key in ("stopped_eos", "stopped_word", "stopped_limit", "stop"):
        need(key not in native or type(native[key]) is bool, "Invalid native stop flag")
    need(native.get("stopped_limit") is not True, "Native output hit token limit")
    if "stop_type" in native:
        cause = native["stop_type"]
        need(
            cause in ("eos", "word") and native.get("stop") is True,
            "Unqualified native completion cause",
        )
        for key, expected in (
            ("stopped_eos", cause == "eos"),
            ("stopped_word", cause == "word"),
        ):
            need(
                key not in native or native[key] is expected,
                "Conflicting native stop causes",
            )
    else:
        need(
            native.get("stopped_limit") is False
            and (
                (
                    native.get("stopped_eos") is True
                    and native.get("stopped_word") is not True
                )
                or (
                    native.get("stopped_word") is True
                    and native.get("stopped_eos") is not True
                )
            )
            and native.get("stop", True) is True,
            "No positive native completion cause",
        )
        cause = "word" if native.get("stopped_word") is True else "eos"
    need(
        native.get("stopping_word") == "<|im_end|>"
        if cause == "word"
        else native.get("stopping_word") in (None, ""),
        "Unexpected native stopping word",
    )


def _wrapper(content, request, payload):
    need(
        isinstance(content, bytes) and len(content) <= MAX_WRAPPER_RESPONSE,
        "Native wrapper exceeds cap",
    )
    wrapper = parse_json(content)
    need(
        isinstance(wrapper, dict)
        and set(wrapper) == WRAPPER_FIELDS
        and type(wrapper["schema_version"]) is int
        and wrapper["schema_version"] == 1
        and wrapper["kind"] == PROTOCOL,
        "Invalid native wrapper",
    )
    need(
        wrapper["request_sha256"] == fingerprint(request)
        and wrapper["payload_sha256"] == fingerprint(payload),
        "Native wrapper request/payload differs",
    )
    need(
        type(wrapper["owner_pid"]) is int
        and wrapper["owner_pid"] > 0
        and _endpoint(wrapper["endpoint"])[0] == wrapper["endpoint"],
        "Invalid native wrapper owner/endpoint",
    )
    need(
        type(wrapper["elapsed_seconds"]) in (int, float)
        and math.isfinite(wrapper["elapsed_seconds"])
        and wrapper["elapsed_seconds"] >= 0
        and type(wrapper["complete"]) is bool
        and (wrapper["http_status"] is None or type(wrapper["http_status"]) is int)
        and (
            wrapper["error_class"] is None
            or isinstance(wrapper["error_class"], str)
            and wrapper["error_class"]
        ),
        "Invalid native wrapper transport state",
    )
    need(isinstance(wrapper["body_base64"], str), "Missing original native bytes")
    try:
        body = base64.b64decode(wrapper["body_base64"], validate=True)
    except ValueError as error:
        raise ContractError("Invalid native body encoding") from error
    need(
        len(body) <= MAX_ORIGINAL_RESPONSE
        and base64.b64encode(body).decode() == wrapper["body_base64"]
        and hashlib.sha256(body).hexdigest() == wrapper["body_sha256"],
        "Native body bytes differ",
    )
    need(
        wrapper["http_status"] == 200
        and wrapper["complete"] is True
        and wrapper["error_class"] is None,
        "Native HTTP body is failed or incomplete",
    )
    return wrapper, body


def _native(content, request, payload, model_alias):
    wrapper, body = _wrapper(content, request, payload)
    native = parse_json(body)
    need(
        isinstance(native, dict)
        and native.get("prompt") == payload["prompt"]
        and native.get("model") == model_alias,
        "Native echoed prompt/model differs",
    )
    settings = native.get("generation_settings")
    keys = ("seed", "temperature", "n_predict", "stop", "stream")
    need(
        isinstance(settings, dict)
        and all(k in settings for k in keys)
        and canonical({k: settings[k] for k in keys})
        == canonical({k: payload[k] for k in keys}),
        "Native generation settings differ",
    )
    _complete(native)
    usage = _usage(native)
    need(
        usage.input_tokens <= len(payload["prompt"].encode()) + 32
        and usage.output_tokens <= payload["n_predict"],
        "Native usage exceeds reservation",
    )
    need(isinstance(native.get("content"), str), "Missing native assistant content")
    return wrapper, native, usage


class LocalBackend:
    """Exactly one explicit POST to a caller-owned loopback server."""

    backend_id = "owned-local-native-study-v1"

    def __init__(
        self,
        endpoint,
        interface,
        model_provenance,
        model_alias,
        owner,
        failure_directory,
    ):
        self.endpoint, self.port = _endpoint(endpoint)
        need(interface in ("current", "simplified"), "Unknown native interface")
        self.interface, self.alias = interface, _alias(model_alias)
        pid = _check_owner(owner, self.port)
        self.owner, self.pid = owner, pid
        self.failure_directory = Path(failure_directory)
        need(
            self.failure_directory.is_dir(),
            "Failure capture directory must be reserved",
        )
        self.capabilities = BackendCapabilities(
            interface_version=interface, max_response_bytes=MAX_WRAPPER_RESPONSE
        )
        self.provenance = freeze(
            dict(
                kind=PROTOCOL,
                endpoint=self.endpoint,
                interface=interface,
                model_alias=self.alias,
                model_provenance=_model(model_provenance),
                owner_pid=pid,
                max_original_response_bytes=MAX_ORIGINAL_RESPONSE,
                provider_cost_usd=0,
            )
        )
        self._used = False
        self._lock = Lock()

    def quote(self, request, payload):
        need(not self._used, "Native backend already consumed")
        need(
            canonical(prepare_payload(request, self.interface)) == canonical(payload),
            "Native payload differs",
        )
        return Usage(len(payload["prompt"].encode()) + 32, payload["n_predict"], 0.0)

    def _execution_deadline(self, start, timeout_seconds):
        """Default transport clock; bounded adapters may clamp an earlier parent."""
        return start + timeout_seconds

    def generate(self, request, payload, *, timeout_seconds):
        need(
            type(timeout_seconds) in (int, float)
            and math.isfinite(timeout_seconds)
            and timeout_seconds > 0,
            "No finite native time remains",
        )
        self.quote(request, payload)
        with self._lock:
            need(not self._used, "Native backend already consumed")
            self._used = True
        start = time.monotonic()
        deadline = self._execution_deadline(start, timeout_seconds)
        body, status, complete = bytearray(), None, False
        connection = response = timer = None
        wrapper = dict(
            schema_version=1,
            kind=PROTOCOL,
            request_sha256=fingerprint(request),
            payload_sha256=fingerprint(payload),
            owner_pid=self.pid,
            endpoint=self.endpoint,
            http_status=None,
            body_base64="",
            body_sha256=hashlib.sha256(b"").hexdigest(),
            complete=False,
            error_class=None,
            elapsed_seconds=0.0,
        )

        def capture(error=None):
            wrapper.update(
                http_status=status,
                body_base64=base64.b64encode(body).decode(),
                body_sha256=hashlib.sha256(body).hexdigest(),
                complete=complete,
                error_class=type(error).__name__ if error is not None else None,
                elapsed_seconds=max(0.0, time.monotonic() - start),
            )
            return canonical(wrapper)

        def persist_failure(primary):
            try:
                raw = capture(primary)
            except BaseException as secondary:
                primary.add_note(
                    "Native capture metadata failed: " + type(secondary).__name__
                )
                wrapper.update(
                    http_status=status,
                    body_base64=base64.b64encode(body).decode(),
                    body_sha256=hashlib.sha256(body).hexdigest(),
                    complete=False,
                    error_class=type(primary).__name__,
                    elapsed_seconds=None,
                )
                raw = canonical(wrapper)
            for name, retained in (
                ("native-failure-body.bin", bytes(body)),
                ("native-failure-wrapper.json", raw),
            ):
                try:
                    publish_bytes(self.failure_directory / name, retained)
                except BaseException as secondary:
                    primary.add_note(
                        "Native failure capture failed: " + type(secondary).__name__
                    )

        try:
            _check_owner(self.owner, self.port, self.pid)
            # http.client uses no environment proxy and never follows redirects.
            connection = http.client.HTTPConnection(
                "127.0.0.1", self.port, timeout=_remaining(deadline)
            )
            connection.connect()
            transport_socket = connection.sock
            need(transport_socket is not None, "Missing connected transport socket")
            timer = _watchdog(transport_socket, deadline)
            transport_socket.settimeout(_remaining(deadline))
            _check_owner(self.owner, self.port, self.pid)
            connection.request(
                "POST",
                "/completion",
                body=canonical(payload),
                headers={"Content-Type": "application/json"},
            )
            transport_socket.settimeout(_remaining(deadline))
            response = connection.getresponse()
            status = response.status
            reader_socket = connection.sock
            if reader_socket is None:
                reader_socket = getattr(
                    getattr(getattr(response, "fp", None), "raw", None), "_sock", None
                )
            need(
                reader_socket is transport_socket,
                "Unsupported detached native response socket",
            )
            while True:
                reader_socket.settimeout(_remaining(deadline))
                chunk = response.read1(
                    min(65536, MAX_ORIGINAL_RESPONSE + 1 - len(body))
                )
                if chunk:
                    remaining_capacity = MAX_ORIGINAL_RESPONSE - len(body)
                    body.extend(chunk[:remaining_capacity])
                    need(
                        len(chunk) <= remaining_capacity,
                        "Native response exceeds original-byte cap",
                    )
                _remaining(deadline)
                if not chunk:
                    if response.length not in (None, 0):
                        raise http.client.IncompleteRead(b"", response.length)
                    complete = True
                    break
            raw = capture()
            usage = None
            try:
                usage = _usage(parse_json(bytes(body)))
            except (ContractError, TypeError, ValueError):
                pass
            return GeneratedBytes(raw, usage)
        except BaseException as primary:
            partial = getattr(primary, "partial", None)
            if isinstance(partial, bytes):
                body.extend(partial[: MAX_ORIGINAL_RESPONSE - len(body)])
            persist_failure(primary)
            raise
        finally:
            # Closing transport must never suppress an active interruption/error.
            import sys

            primary = sys.exception()
            cleanup_error = None
            if timer is not None:
                try:
                    timer.cancel()
                except BaseException as error:
                    if primary is not None:
                        primary.add_note(
                            "Native deadline cleanup failed: " + type(error).__name__
                        )
                    else:
                        cleanup_error = error
            for resource in (response, connection):
                if resource is not None:
                    try:
                        resource.close()
                    except BaseException as error:
                        if primary is not None:
                            primary.add_note(
                                "Native transport close failed: " + type(error).__name__
                            )
                        elif cleanup_error is None:
                            cleanup_error = error
            if cleanup_error is not None:
                persist_failure(cleanup_error)
                raise cleanup_error


class NativeVerifier:
    """Pure native replay checks; no connection or archived symbol loading."""

    required_resources = REQUIRED_RESOURCES

    def __init__(self, interface, model_alias):
        need(interface in ("current", "simplified"), "Unknown native interface")
        self.interface, self.alias = interface, _alias(model_alias)

    def validate_payload(self, request, payload):
        need(
            canonical(prepare_payload(request, self.interface)) == canonical(payload),
            "Frozen native payload differs",
        )

    def validate_response(self, request, content):
        payload = prepare_payload(request, self.interface)
        _, native, _ = _native(content, request, payload, self.alias)
        return validate_output(request, self.interface, parse_json(native["content"]))

    def verify_execution(self, request, payload, content, configuration, usage):
        self.validate_payload(request, payload)
        need(
            encode(configuration["adapter_code"]) == _identity(LocalBackend),
            "Native adapter code identity differs",
        )
        provenance = encode(configuration["adapter_provenance"])
        need(
            isinstance(provenance, dict)
            and set(provenance)
            == {
                "kind",
                "endpoint",
                "interface",
                "model_alias",
                "model_provenance",
                "owner_pid",
                "max_original_response_bytes",
                "provider_cost_usd",
            }
            and provenance["kind"] == PROTOCOL
            and provenance["interface"] == self.interface
            and provenance["model_alias"] == self.alias
            and provenance["max_original_response_bytes"] == MAX_ORIGINAL_RESPONSE
            and type(provenance["max_original_response_bytes"]) is int
            and type(provenance["provider_cost_usd"]) is int
            and provenance["provider_cost_usd"] == 0,
            "Native provenance differs",
        )
        _model(provenance["model_provenance"])
        wrapper, _, expected_usage = _native(content, request, payload, self.alias)
        need(
            wrapper["endpoint"] == provenance["endpoint"]
            and wrapper["owner_pid"] == provenance["owner_pid"]
            and type(provenance["owner_pid"]) is int,
            "Native wrapper ownership binding differs",
        )
        need(
            isinstance(usage, Usage) and canonical(usage) == canonical(expected_usage),
            "Native measured usage differs",
        )
        need(
            canonical(configuration["backend_capabilities"])
            == canonical(
                BackendCapabilities(
                    interface_version=self.interface,
                    max_response_bytes=MAX_WRAPPER_RESPONSE,
                )
            ),
            "Native capabilities differ",
        )
