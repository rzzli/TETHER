"""Finite ordinary-loopback typed-report transport, separate from native v2/v3.

No source lookup, launcher, model qualification, grammar conversion, retries or
implicit writes. Constructing a client never dispatches. The caller retains source
packets, validates typed content separately, and owns the server process handle.
"""

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from asof.serde import ContractError, Frozen, canonical, freeze, parse_json


MAX_NETSTAT_BYTES = 1024 * 1024
MAX_ENVELOPE_BYTES = 2 * 1024 * 1024
CONTEXT_TOKENS = 16384
MAX_OUTPUT_TOKENS = 2048
TOKEN_MARGIN = 32
MAX_TIMEOUT_SECONDS = 300
_DECIMAL = re.compile(r"[1-9][0-9]*\Z")
_NONLISTEN_STATES = frozenset((
    "CLOSED", "SYN_SENT", "SYN_RECEIVED", "SYN_RECV", "ESTABLISHED", "FIN_WAIT_1",
    "FIN_WAIT_2", "CLOSE_WAIT", "CLOSING", "LAST_ACK", "TIME_WAIT", "DELETE_TCB", "BOUND",
))


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _port(port):
    _need(type(port) is int and 1 <= port <= 65535, "Invalid explicit listener port")


def parse_netstat_listener(raw: bytes, port: int):
    """Parse one canonical IPv4 loopback listener; absence is not ownership.

    This is an explicitly selected method for the new reporting path, not a
    fallback inside a prior verifier. Unrelated ports and known non-listening
    connections do not contribute owners. Unsupported targeted states and every
    targeted duplicate or wildcard/IPv6 listener fail.
    """
    _port(port)
    _need(type(raw) is bytes and len(raw) <= MAX_NETSTAT_BYTES,
          "Invalid or oversized retained netstat output")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as error:
        raise ContractError("Netstat output must be UTF-8") from error
    owners = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if len(parts) == 5 and parts[0] == "TCP" and parts[3] in _NONLISTEN_STATES:
            continue
        if len(parts) < 2 or ":" not in parts[1]:
            _need("LISTENING" not in parts, "Malformed listening row")
            continue
        local_port = parts[1].rsplit(":", 1)[1]
        _need(local_port.isascii() and local_port.isdecimal(),
              "Malformed listening port")
        try:
            number = int(local_port)
        except ValueError as error:
            raise ContractError("Malformed listening port") from error
        _need(1 <= number <= 65535, "Malformed listening port")
        if number != port:
            continue
        _need(len(parts) == 5 and parts[0] == "TCP"
              and parts[1] == f"127.0.0.1:{port}" and parts[2] == "0.0.0.0:0"
              and parts[3] == "LISTENING", "Noncanonical targeted listening row")
        _need(_DECIMAL.fullmatch(parts[4]) is not None and len(parts[4]) <= 10,
              "Invalid targeted listener PID")
        owner = int(parts[4])
        _need(owner <= 0xFFFFFFFF, "Targeted listener PID exceeds Windows range")
        owners.append(owner)
        _need(len(owners) == 1, "Duplicate or ambiguous targeted listeners")
    return owners[0] if owners else None


def prepare_completion(prompt: str, maximum: int = 2048, seed: int = 0):
    """Preserve the caller's exact prompt in an unconstrained ordinary payload."""
    _need(type(prompt) is str, "Completion prompt must be text")
    try:
        size = len(prompt.encode("utf-8"))
    except UnicodeError as error:
        raise ContractError("Completion prompt must be valid UTF-8") from error
    _need(type(maximum) is int and 1 <= maximum <= MAX_OUTPUT_TOKENS,
          "Invalid completion output cap")
    _need(type(seed) is int, "Completion seed must be an integer")
    _need(size + maximum + TOKEN_MARGIN <= CONTEXT_TOKENS,
          "Complete prompt/output reservation exceeds context cap")
    return freeze(dict(prompt=prompt, n_predict=maximum, temperature=0.0, seed=seed,
                       cache_prompt=False, stream=False, stop=["<|im_end|>"]))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ContractError("Typed-report redirects are forbidden")


@contextmanager
def _response(manager):
    """A secondary close failure must not replace an active interruption."""
    response = manager.__enter__()
    try:
        yield response
    except BaseException as primary:
        try:
            manager.__exit__(type(primary), primary, primary.__traceback__)
        except BaseException as secondary:
            primary.add_note("Secondary response close failure: " + type(secondary).__name__)
        raise
    else:
        manager.__exit__(None, None, None)


@dataclass(frozen=True)
class TransportResult(Frozen):
    status: str
    error: str | None
    dispatched: bool
    raw_request: bytes
    raw_envelope: bytes
    content: bytes | None
    measured_usage: Mapping | None
    estimated_usage: Mapping
    request_sha256: str
    response_sha256: str | None
    content_sha256: str | None
    envelope_complete: bool


def _usage(native):
    _need(type(native) is dict, "Completion envelope must be an object")
    _need(all(type(native.get(key)) is int and native[key] >= 0
              for key in ("tokens_evaluated", "tokens_predicted")),
          "Completion usage requires measured nonnegative integer token counts")
    return dict(input_tokens=native["tokens_evaluated"],
                output_tokens=native["tokens_predicted"], cost_usd=0.0)


def _binding(native, payload):
    _need(type(native.get("prompt")) is str and native["prompt"] == payload["prompt"],
          "Completion prompt echo differs")
    model = native.get("model")
    _need(type(model) is str and bool(model.strip()), "Completion model identity is missing")
    try:
        model.encode("utf-8")
    except UnicodeError as error:
        raise ContractError("Completion model identity has invalid Unicode") from error
    settings = native.get("generation_settings")
    _need(type(settings) is dict, "Completion settings echo is missing")
    for key in ("seed", "temperature", "n_predict", "stop", "stream"):
        _need(key in settings and canonical(settings[key]) == canonical(payload[key]),
              "Completion generation setting differs: " + key)


def _complete(native):
    _need(native.get("truncated") is False, "Completion prompt is truncated or unqualified")
    for key in ("stop", "stopped_limit", "stopped_eos", "stopped_word"):
        _need(key not in native or type(native[key]) is bool,
              "Completion stop metadata must be Boolean")
    _need(native.get("stop") is not False and native.get("stopped_limit") is not True,
          "Completion explicitly incomplete or limited")
    _need(not (native.get("stopped_eos") is True and native.get("stopped_word") is True),
          "Completion stop causes conflict")
    _need(native.get("stopped_word") is not True or native.get("stopping_word") == "<|im_end|>",
          "Completion word cause requires the requested stopping word")
    if "stop_type" in native:
        cause = native["stop_type"]
        _need(type(cause) is str and cause in ("eos", "word")
              and native.get("stop") is True, "Completion stop type is unqualified")
        for key, expected in (("stopped_eos", "eos"), ("stopped_word", "word")):
            _need(key not in native or native[key] is (cause == expected),
                  "Completion stop causes conflict")
        _need(native.get("stopping_word") == "<|im_end|>" if cause == "word"
              else native.get("stopping_word") in (None, ""),
              "Completion stopping word differs")
    elif "stopping_word" in native:
        _need(native["stopping_word"] == "<|im_end|>" if native.get("stopped_word") is True
              else native["stopping_word"] in (None, ""),
              "Completion stopping word conflicts")


def _error(error):
    message = str(error).encode("utf-8", "backslashreplace").decode("utf-8")[:240]
    return type(error).__name__ + ": " + message


class TypedReportingClient:
    """One-use client with trusted ownership and durable-retention callbacks.

    ``ownership_check(pid, host, port)`` must return exactly True. ``retain`` gets
    immutable ``attempt`` and ``terminal`` events; terminal includes TransportResult.
    The attempt callback must succeed before dispatch. Configuration/ownership
    callback failures and interruptions propagate after best-effort terminal
    retention. Expected transport failures return a structured result. Token
    estimates remain separate from actual measured usage, including rejected calls.
    """

    def __init__(self, endpoint: str, *, expected_pid: int, ownership_check,
                 opener=None, retain=None):
        _need(type(endpoint) is str, "Explicit loopback endpoint is required")
        try:
            parsed = urllib.parse.urlsplit(endpoint)
            port = parsed.port
        except ValueError as error:
            raise ContractError("Invalid loopback endpoint") from error
        _port(port)
        _need(endpoint in (f"http://127.0.0.1:{port}", f"http://127.0.0.1:{port}/"),
              "Endpoint must be canonical explicit IPv4 loopback HTTP")
        _need(type(expected_pid) is int and 1 <= expected_pid <= 0xFFFFFFFF,
              "Expected owned PID must be a positive Windows PID")
        _need(callable(ownership_check) and (retain is None or callable(retain)),
              "Trusted ownership and retention callbacks are required")
        if opener is None:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        _need(callable(getattr(opener, "open", None)), "Invalid trusted HTTP opener")
        self.endpoint, self.port, self.expected_pid = endpoint.rstrip("/"), port, expected_pid
        self.ownership_check, self.opener, self.retain = ownership_check, opener, retain
        self._used, self._lock = False, threading.Lock()

    def execute(self, prompt: str, *, maximum: int = 2048, seed: int = 0,
                timeout_seconds: float = 300):
        with self._lock:
            _need(not self._used, "Typed-report client is one-use; no retry")
            self._used = True
        state = dict(status="failed", error=None, dispatched=False, raw_request=b"",
                     raw_envelope=b"", content=None, measured_usage=None,
                     estimated_usage={}, request_sha256=hashlib.sha256(b"").hexdigest(),
                     response_sha256=None, content_sha256=None, envelope_complete=False)
        phase, primary = "configuration", None
        try:
            _need(type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds)
                  and 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS,
                  "Invalid bounded completion timeout")
            payload = prepare_completion(prompt, maximum, seed)
            raw_request = canonical(payload)
            state.update(raw_request=raw_request,
                request_sha256=hashlib.sha256(raw_request).hexdigest(),
                estimated_usage=dict(input_tokens=len(prompt.encode("utf-8")) + TOKEN_MARGIN,
                                     output_tokens=maximum, cost_usd=0.0))
            phase = "ownership"
            owned = self.ownership_check(self.expected_pid, "127.0.0.1", self.port)
            if owned is not True:
                state["error"] = "Ownership check did not affirm the pinned loopback listener"
            else:
                phase = "attempt_retention"
                if self.retain is not None:
                    self.retain(freeze(dict(event="attempt", endpoint=self.endpoint,
                        expected_pid=self.expected_pid, raw_request=raw_request,
                        request_sha256=state["request_sha256"],
                        estimated_usage=state["estimated_usage"], dispatched=False)))
                request = urllib.request.Request(self.endpoint + "/completion", data=raw_request,
                    headers={"Content-Type": "application/json"}, method="POST")
                phase = "transport"
                state["dispatched"] = True
                with _response(self.opener.open(request, timeout=timeout_seconds)) as response:
                    _need(getattr(response, "status", None) == 200, "Unexpected completion HTTP status")
                    _need(response.geturl() == self.endpoint + "/completion",
                          "Completion response URL differs; redirects are forbidden")
                    captured = response.read(MAX_ENVELOPE_BYTES + 1)
                    _need(type(captured) is bytes, "Completion response capture must be bytes")
                    raw = captured[:MAX_ENVELOPE_BYTES + 1]
                    state.update(raw_envelope=raw,
                        response_sha256=hashlib.sha256(raw).hexdigest(),
                        envelope_complete=len(captured) <= MAX_ENVELOPE_BYTES)
                    _need(state["envelope_complete"], "Completion envelope exceeds 2 MiB")
                    native = parse_json(raw)
                    state["measured_usage"] = _usage(native)
                    _need(type(native.get("content")) is str, "Completion content must be text")
                    content = native["content"].encode("utf-8")
                    state.update(content=content, content_sha256=hashlib.sha256(content).hexdigest())
                    _binding(native, payload)
                    _complete(native)
                    _need(state["measured_usage"]["input_tokens"] <= state["estimated_usage"]["input_tokens"]
                          and state["measured_usage"]["output_tokens"] <= maximum,
                          "Measured completion usage exceeds its reservation")
                state["status"] = "returned"
        except BaseException as error:
            partial = getattr(error, "partial", None)
            if type(partial) is bytes and state["response_sha256"] is None:
                retained = partial[:MAX_ENVELOPE_BYTES + 1]
                state.update(raw_envelope=retained, response_sha256=hashlib.sha256(retained).hexdigest(),
                             envelope_complete=False)
            state["error"] = _error(error)
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                state["status"], primary = "interrupted", error
            else:
                reason = getattr(error, "reason", None)
                state["status"] = "timeout" if isinstance(error, TimeoutError) or isinstance(reason, TimeoutError) else "failed"
                if phase in ("configuration", "ownership", "attempt_retention"):
                    primary = error
        finally:
            result = TransportResult(**state)
            if self.retain is not None:
                try:
                    self.retain(freeze(dict(event="terminal", result=result)))
                except BaseException as secondary:
                    if primary is None:
                        primary = secondary
                    else:
                        primary.add_note("Secondary terminal-retention failure: " + type(secondary).__name__)
        if primary is not None:
            raise primary
        return result
