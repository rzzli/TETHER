"""Independent pure-data probes; no subject modules or frozen cases are loaded."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from shared_owner_snapshot_validator_v1 import (
    APIS, KINDS, QUALIFICATIONS, SnapshotValidationError, validate_snapshot,
)


def callback():
    return dict(attempted=False, return_observed=False, acknowledged=False,
                prepared_bytes=0, prepared_sha256=None,
                semantics="fictional_callback_not_physical_IO")


def atom(tag="UNOBSERVED", value=None):
    return dict(tag=tag, value=value)


def specimen():
    """Authored format specimen, not a predicted source state or fixture case."""
    file_path = "D:\\FictionalSharedOwnerCohort\\format_probe.py"
    file = dict(id=0, spec=dict(path=file_path, role="software", size=1, sha256="a" * 64, capture=True),
                early=True, open_state="reserved", handle_fact=atom(), identity_state="in_progress",
                identity_queries=[1, 2, 3, 4], open_invocations=0, read_invocations=0,
                read_scalar_returns=0, known_read_bytes=0, hashed_bytes=0, captured_bytes=0,
                read_count_unknown=False, hash_complete=False, capture_complete=False,
                actual_sha256=None, close_reserved=False, close_invocations=0,
                close_return_observed=False, close_success=None, close_state="not_attempted")
    calls = []
    for i, api in enumerate(APIS):
        calls.append(dict(ordinal=i, api=api, file_id=0, reserved=True, invocation_reserved=False,
                          raw_scalar=atom(), raw_count=atom(), raw_error=atom(), error_defined=False,
                          scalar_aux_ack=False, count_aux_ack=False, right_transfer_ack=False,
                          wrapper_return_observed=False, wrapper_state="not_returned", stopped=False,
                          count_defined=False, buffer_state="not_applicable", buffer_generation=None,
                          raw_buffer_bytes=None, raw_buffer_sha256=None))
    return dict(
        scope="pure_shared_owner_seam", status="ACTIVE", phase="PLAN", refusal_code=None,
        finalized=False, pure_seam_complete=False,
        origin=dict(start=100, now=100, work_end=395, hard_end=400, clock_state="ok"),
        plan=dict(N=1, B=1, M=1, R=17, C=23, E=202, calls_used=7, events_used=1,
                  capture_used=0, raw_storage_used=0, raw_storage_peak=0,
                  read_buffer_capacity=0, read_generation=0, output_reserved_bytes=0),
        files=[file], calls=calls,
        api_counters={api: dict(reserved=1, invocations=0, scalar_returns=0,
                                count_values=0, wrapper_returns=0) for api in APIS},
        byte_totals=dict(known_read_bytes=0, hashed_bytes=0, captured_bytes=0,
                         early_known_read_bytes=0, early_hashed_bytes=0, early_captured_bytes=0,
                         remaining_known_read_bytes=0, remaining_hashed_bytes=0,
                         remaining_captured_bytes=0, read_count_unknown=False,
                         early_reopens_after_claim=0, early_rehashes_after_claim=0),
        early_context=dict(file_ids=[0], captured_bytes=0, digests={file_path: "b" * 64}, complete=False),
        evidence_context=None,
        loader=dict(bound=True, attempted=["cohort_leaf"], returned=[], cache_hits=[],
                    records=[dict(module="cohort_leaf", state="reserved", return_observed=False, accepted=False)]),
        journal=dict(reservation=202, next_sequence=1, closed=False,
                     close_return_observed=False, close_acknowledged=False, tip=None,
                     events=[dict(sequence=0, event="source_open_reserved", stage=None, kind=None,
                                  file_id=0, module=None, elapsed=0, state="reserved",
                                  return_observed=False, acknowledged=False)]),
        outputs=dict(reservation=callback(), publications={kind: callback() for kind in KINDS},
                     journal_close=callback(), total_reserved_bytes=0),
        stages=[dict(name="authority_factory", state="reserved", return_observed=False,
                     accepted=False, verdict=None)],
        gates=[], errors=dict(primary=None, secondary=[]),
        terminal={key: False for key in (
            "started", "candidate_acknowledged", "original_closures_complete", "cleanup_acknowledged",
            "journal_closed", "receipt_acknowledged", "seal_acknowledged", "final_clock_passed",
            "pure_owner_ack", "result_issued")}, qualification={key: False for key in QUALIFICATIONS})


def set_at(value, path, replacement):
    cursor = value
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = replacement


def leaves(value, path=()):
    if type(value) is dict:
        for key, child in value.items():
            yield from leaves(child, path + (key,))
    elif type(value) is list:
        for i, child in enumerate(value):
            yield from leaves(child, path + (i,))
    else:
        yield path, value


def run():
    observations, failures = [], []

    def probe(name, value, accept=False, check=None):
        try:
            validate_snapshot(value, diagnostic_identity_check=check)
        except SnapshotValidationError as exc:
            observations.append(dict(probe=name, accepted=False, path=exc.path))
            if accept:
                failures.append(dict(probe=name, unexpected="SnapshotValidationError", path=exc.path))
        except BaseException as exc:
            failures.append(dict(probe=name, unexpected=type(exc).__name__, message=str(exc)))
        else:
            observations.append(dict(probe=name, accepted=True))
            if not accept:
                failures.append(dict(probe=name, unexpected="accepted malformed data"))

    base = specimen()
    probe("authored_partial_format", base, True)
    pre = deepcopy(base)
    pre["plan"] = None
    pre["journal"]["reservation"] = 0
    probe("pre_admission_partial_not_forced_empty", pre, True)
    finite = deepcopy(base)
    finite["origin"] = dict(start=1 << 400, now=1 << 400, work_end=(1 << 400) + 295,
                            hard_end=(1 << 400) + 300, clock_state="ok")
    probe("large_integer_time_no_float_conversion", finite, True)
    prepared = deepcopy(base)
    prepared["outputs"]["publications"]["candidate"].update(prepared_bytes=8192, prepared_sha256="c" * 64)
    probe("prepared_undispatched_callback_retained", prepared, True)
    for path, item in leaves(base):
        if type(item) is bool:
            bad = deepcopy(base)
            set_at(bad, path, 1)
            probe("bool_required:" + repr(path), bad)
        elif type(item) is int and path[0] != "origin" and path[-1] != "elapsed":
            for label, replacement in (("bool", True), ("float", float(item)), ("negative", -1), ("oversize", 1 << 400)):
                bad = deepcopy(base)
                set_at(bad, path, replacement)
                probe("integer_" + label + ":" + repr(path), bad)
    records = [(), ("origin",), ("plan",), ("files", 0), ("files", 0, "spec"),
               ("calls", 0), ("calls", 0, "raw_scalar"), ("api_counters",),
               ("api_counters", "ReadFile"), ("byte_totals",), ("early_context",),
               ("loader",), ("loader", "records", 0), ("journal",), ("journal", "events", 0),
               ("outputs",), ("outputs", "publications"), ("outputs", "reservation"),
               ("outputs", "publications", "seal"), ("stages", 0), ("errors",),
               ("terminal",), ("qualification",)]
    for path in records:
        for action in ("extra", "missing"):
            bad = deepcopy(base)
            record = bad
            for part in path:
                record = record[part]
            if action == "extra":
                record["producer_ready"] = True
            else:
                del record[next(iter(record))]
            probe("exactkeys_" + action + ":" + repr(path), bad)
    for key in ("start", "now", "work_end", "hard_end"):
        for replacement in (True, float("nan"), float("inf"), -float("inf"), "100"):
            bad = deepcopy(base)
            bad["origin"][key] = replacement
            probe("time_domain:" + key + ":" + type(replacement).__name__ + ":" + str(replacement), bad)
    for i, api in enumerate(APIS):
        tag = "HANDLE" if api == "CreateFileW" else "DWORD" if api in ("GetFileType", "GetFinalPathNameByHandleW") else "BOOL32"
        low, high = (0, (1 << 64) - 1) if tag == "HANDLE" else (0, (1 << 32) - 1) if tag == "DWORD" else (-(1 << 31), (1 << 31) - 1)
        for scalar in (low, high):
            good = deepcopy(base)
            good["calls"][i]["raw_scalar"] = atom(tag, scalar)
            probe("raw_scalar_boundary:" + api + ":" + str(scalar), good, True)
        for scalar in (True, 0.0, low - 1, high + 1):
            bad = deepcopy(base)
            bad["calls"][i]["raw_scalar"] = atom(tag, scalar)
            probe("raw_scalar_invalid:" + api + ":" + str(scalar), bad)
        if api != "ReadFile":
            bad = deepcopy(base)
            bad["calls"][i]["raw_count"] = atom("COUNT32", 0)
            probe("count_readfile_only:" + api, bad)
    for path, replacement in (
            (("scope",), "production"), (("gates",), ["hashes"]),
            (("calls", 0, "raw_scalar"), atom("UNOBSERVED", 0)),
            (("calls", 0, "raw_scalar"), atom("NULL", 0)),
            (("calls", 0, "raw_scalar"), atom("DWORD", 0)),
            (("calls", 5, "raw_count"), atom("COUNT32", 1 << 32)),
            (("calls", 5, "raw_error"), atom("DWORD", True)),
            (("calls", 5, "raw_buffer_bytes"), 65537),
            (("calls", 2, "raw_buffer_bytes"), 9),
            (("outputs", "publications", "seal", "prepared_bytes"), 8193),
            (("outputs", "publications", "seal", "acknowledged"), True),
            (("journal", "events", 0, "elapsed"), float("nan")),
            (("journal", "events", 0, "kind"), "receipt"),
            (("journal", "events", 0, "module"), "os"),
            (("loader", "attempted"), ["os"]),
            (("early_context", "file_ids"), [0, 0]),
            (("files", 0, "spec", "path"), "C:\\" + "\U00010000" * 2048),
            (("files", 0, "spec", "sha256"), "A" * 64),
            (("files", 0, "close_success"), 1),
            (("errors", "primary"), RuntimeError("must not escape into diagnostic data")),
            (("terminal", "result_issued"), object())):
        bad = deepcopy(base)
        set_at(bad, path, replacement)
        probe("closed_domain:" + repr(path), bad)

    token = object()
    diagnostic = dict(identity=token, phase="entry", class_name="RuntimeError", message="captured",
                      args_repr=["immutable captured argument"], format_failed=False)
    good = deepcopy(base)
    good["errors"]["primary"] = diagnostic
    check = lambda actual: actual is token
    probe("opaque_diagnostic_identity", good, True, check)
    probe("opaque_token_requires_callback", good)
    probe("opaque_token_callback_exact_true", good, check=lambda unused: 1)
    for key, replacement in (("phase", "case_label"), ("class_name", "x" * 129),
                             ("message", "x" * 257), ("args_repr", ["x"] * 9),
                             ("identity", RuntimeError("original")), ("format_failed", 0)):
        bad = deepcopy(base)
        bad["errors"]["primary"] = dict(diagnostic, **{key: replacement})
        probe("diagnostic_domain:" + key, bad, check=check)
    original = KeyboardInterrupt("identity callback original")
    try:
        def raise_original(unused):
            raise original
        validate_snapshot(good, diagnostic_identity_check=raise_original)
    except BaseException as caught:
        if caught is not original:
            failures.append(dict(probe="identity_callback_original_propagation", unexpected=type(caught).__name__))
        observations.append(dict(probe="identity_callback_original_propagation", original_preserved=caught is original))
    else:
        failures.append(dict(probe="identity_callback_original_propagation", unexpected="no exception"))

    source = Path(__file__).with_name("shared_owner_snapshot_validator_v1.py")
    return dict(schema_version=1, kind="independent_pure_validator_probes", source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                probe_count=len(observations), passed=not failures, failures=failures, observations=observations,
                subject_modules_imported=False, subject_outputs_read=False, frozen_expected_cases_read=False)


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    raise SystemExit(0 if result["passed"] else 1)
