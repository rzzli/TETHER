"""Pure captured Win64 Job-frame decoding; no report or resource qualification.

Times/counters/PIDs are literal byte fields. Sequential query results never
constitute an atomic Job snapshot, process ownership, or OS enforcement proof.
"""
from dataclasses import dataclass
import re
import struct


_ACCOUNTING_NAMES = (
    "TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime",
    "ThisPeriodTotalKernelTime", "TotalPageFaultCount", "TotalProcesses",
    "ActiveProcesses", "TotalTerminatedProcesses",
)
_OUTER = frozenset(("query_started_monotonic_ns", "query_finished_monotonic_ns", "accounting", "pid_list"))
_A_KEYS = frozenset(("ok", "error", "returned_bytes", "raw_hex", "decoded"))
_P_KEYS = frozenset(("ok", "error", "returned_bytes", "raw_hex", "assigned_count", "listed_count", "pids"))
_PHASES = ("empty", "assigned", "running_or_finished", "finished")


def _uint32(value):
    return type(value) is int and 0 <= value <= 0xFFFFFFFF


def _export_fields(fields):
    if fields is None:
        return None
    return {key: list(value) if type(value) is tuple else value for key, value in fields}


@dataclass(frozen=True, slots=True)
class DecodedQuery:
    status: str
    ok: bool | None
    error: int | None
    returned_bytes: int | None
    raw_hex: str | None
    fields: tuple | None
    source_view_matches: bool | None
    issues: tuple

    def to_dict(self):
        return dict(status=self.status, ok=self.ok, error=self.error,
                    returned_bytes=self.returned_bytes, raw_hex=self.raw_hex,
                    fields=_export_fields(self.fields),
                    source_view_matches=self.source_view_matches, issues=list(self.issues))


@dataclass(frozen=True, slots=True)
class DecodedJobSnapshot:
    capture_present: bool
    query_window_valid: bool
    accounting: DecodedQuery | None
    pid_list: DecodedQuery | None
    issues: tuple

    @property
    def raw_complete(self):
        return (self.capture_present and self.query_window_valid and
                self.accounting is not None and self.accounting.status == "decoded" and
                self.pid_list is not None and self.pid_list.status == "decoded")

    @property
    def source_views_consistent(self):
        if (self.accounting is None or self.accounting.status != "decoded" or
                self.pid_list is None or self.pid_list.status != "decoded"):
            return None
        return self.accounting.source_view_matches is True and self.pid_list.source_view_matches is True

    @property
    def atomic_snapshot(self):
        return False

    @property
    def resource_qualified(self):
        return False

    def to_dict(self):
        return dict(capture_present=self.capture_present, query_window_valid=self.query_window_valid,
                    accounting=None if self.accounting is None else self.accounting.to_dict(),
                    pid_list=None if self.pid_list is None else self.pid_list.to_dict(),
                    raw_complete=self.raw_complete, source_views_consistent=self.source_views_consistent,
                    issues=list(self.issues), atomic_snapshot=False, resource_qualified=False)


@dataclass(frozen=True, slots=True)
class SnapshotPhaseCheck:
    status: str
    expected_phase: str
    observed_state: tuple | None
    issues: tuple

    @property
    def non_atomic_race_possible(self):
        return True

    @property
    def resource_qualified(self):
        return False

    def to_dict(self):
        return dict(status=self.status, expected_phase=self.expected_phase,
                    observed_state=_export_fields(self.observed_state), issues=list(self.issues),
                    non_atomic_race_possible=True, resource_qualified=False)


def _query(source, kind):
    """Only bounded scalar/frame metadata crosses this output boundary."""
    if source is None:
        return None
    issues = []
    keys, size = (_A_KEYS, 48) if kind == "accounting" else (_P_KEYS, 136)
    if type(source) is not dict:
        return DecodedQuery("malformed", None, None, None, None, None, None, ("component_schema",))
    schema_ok = source.keys() == keys
    if not schema_ok:
        issues.append("component_schema")
    flag = source.get("ok")
    ok = flag if type(flag) is bool else None
    if ok is None:
        issues.append("ok_type")
    error = source.get("error")
    if not _uint32(error):
        error = None
        issues.append("error_uint32")
    returned = source.get("returned_bytes")
    if not _uint32(returned):
        returned = None
        issues.append("returned_bytes_uint32")
    raw = source.get("raw_hex")
    if type(raw) is not str or len(raw) != 2 * size or re.fullmatch("[0-9a-f]+", raw) is None:
        raw = None
        issues.append("raw_frame_shape")
    # A false return never defines fields, including error0 and plausible bytes.
    if ok is False:
        issues.append("query_returned_false")
        return DecodedQuery("undefined", ok, error, returned, raw, None, None, tuple(issues))
    if error is not None and error != 0:
        issues.append("success_error_nonzero")
    if not schema_ok or ok is not True or error != 0 or returned is None or raw is None:
        return DecodedQuery("malformed", ok, error, returned, raw, None, None, tuple(issues))
    if kind == "accounting":
        if returned != 48:
            issues.append("accounting_returned_length")
            return DecodedQuery("malformed", ok, error, returned, raw, None, None, tuple(issues))
        values = struct.unpack("<qqqqIIII", bytes.fromhex(raw))
        fields = tuple(zip(_ACCOUNTING_NAMES, values))
        reported = source.get("decoded")
        same = type(reported) is dict and reported.keys() == frozenset(_ACCOUNTING_NAMES)
        if not same:
            issues.append("source_decoded_schema")
        else:
            for name, value in fields:
                if type(reported[name]) is not int or reported[name] != value:
                    same = False
                    issues.append("source_decoded_mismatch:" + name)
    else:
        values = struct.unpack("<II16Q", bytes.fromhex(raw))
        assigned, listed = values[:2]
        if assigned != listed or listed > 16:
            issues.append("pid_counts_incomplete")
        if not 8 + 8 * listed <= returned <= 136:
            issues.append("pid_returned_length")
        if issues:
            return DecodedQuery("malformed", ok, error, returned, raw, None, None, tuple(issues))
        ids = tuple(values[2:2 + listed])
        fields = (("assigned_count", assigned), ("listed_count", listed), ("pids", ids))
        same = True
        for name, value in fields[:2]:
            if type(source.get(name)) is not int or source[name] != value:
                same = False
                issues.append("source_pid_mismatch:" + name)
        reported_ids = source.get("pids")
        if (type(reported_ids) is not list or len(reported_ids) != listed or
                any(type(value) is not int for value in reported_ids) or tuple(reported_ids) != ids):
            same = False
            issues.append("source_pid_mismatch:pids")
    return DecodedQuery("decoded", ok, error, returned, raw, fields, same, tuple(issues))


def decode_job_snapshot(snapshot):
    """Decode a captured source-shaped record; never issue an OS query."""
    if snapshot is None:
        return DecodedJobSnapshot(False, False, None, None, ("capture_missing",))
    if type(snapshot) is not dict or snapshot.keys() != _OUTER:
        raise ValueError("snapshot_schema")
    start, finish = snapshot["query_started_monotonic_ns"], snapshot["query_finished_monotonic_ns"]
    window = type(start) is int and type(finish) is int and 0 <= start <= finish
    issues = [] if window else ["query_window_invalid"]
    a, p = _query(snapshot["accounting"], "accounting"), _query(snapshot["pid_list"], "pid_list")
    if a is None:
        issues.append("accounting_missing")
    if p is None:
        issues.append("pid_list_missing")
    return DecodedJobSnapshot(True, window, a, p, tuple(issues))


def check_snapshot_phase(decoded, expected_phase, own_pid):
    """Check only selected source tuples, not process identity or resource limits."""
    if type(decoded) is not DecodedJobSnapshot:
        raise TypeError("decoder_result_type")
    if type(expected_phase) is not str or expected_phase not in _PHASES:
        raise ValueError("expected_phase")
    if expected_phase == "empty":
        if own_pid is not None and (not _uint32(own_pid) or own_pid != 0):
            raise ValueError("own_pid")
    elif not _uint32(own_pid) or own_pid == 0:
        raise ValueError("own_pid")
    if not decoded.raw_complete or decoded.source_views_consistent is not True:
        return SnapshotPhaseCheck("unresolved", expected_phase, None, ("raw_or_source_view_unresolved",))
    accounting, pids = dict(decoded.accounting.fields), dict(decoded.pid_list.fields)
    state = (("TotalProcesses", accounting["TotalProcesses"]),
             ("ActiveProcesses", accounting["ActiveProcesses"]),
             ("TotalTerminatedProcesses", accounting["TotalTerminatedProcesses"]), ("pids", pids["pids"]))
    observed = tuple(value for _, value in state)
    empty, live, done = (0, 0, 0, ()), (1, 1, 0, (own_pid,)), (1, 0, 0, ())
    choices = {"empty": (empty,), "assigned": (live,), "running_or_finished": (live, done), "finished": (done,)}
    matched = observed in choices[expected_phase]
    return SnapshotPhaseCheck("matched_selected_source_phase" if matched else "counter_or_PID_mismatch",
                              expected_phase, state, () if matched else ("selected_tuple_mismatch",))
