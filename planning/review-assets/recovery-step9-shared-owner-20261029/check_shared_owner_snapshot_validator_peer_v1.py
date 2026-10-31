"""Finite independent format probes of the harness validator, never a subject run.

Only the pinned validator is executed. Specimens below are independently authored
DATA-shape examples, not fixture predictions or source-produced snapshots.
"""

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SOURCE = "shared_owner_snapshot_validator_v1.py"
SOURCE_SHA = "afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc"
DATA_SHA = "50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6"
APIS = ("CreateFileW", "GetFileType", "GetFileInformationByHandleEx",
        "GetFinalPathNameByHandleW", "GetFileSizeEx", "ReadFile", "CloseHandle")
KINDS = ("candidate", "cleanup", "failure", "receipt", "seal")
TERMINAL = ("started", "candidate_acknowledged", "original_closures_complete",
            "cleanup_acknowledged", "journal_closed", "receipt_acknowledged",
            "seal_acknowledged", "final_clock_passed", "pure_owner_ack", "result_issued")
QUALIFICATION = ("FFI_registration_proven", "originals_authenticated",
                 "production_owner_bound", "profile_qualified", "real_checkers_bound",
                 "runtime_authorized", "verification_complete")


def callback():
    return dict(attempted=False, return_observed=False, acknowledged=False,
                prepared_bytes=0, prepared_sha256=None,
                semantics="fictional_callback_not_physical_IO")


def atom(tag="UNOBSERVED", value=None):
    return dict(tag=tag, value=value)


def specimen(populated=False):
    """A format-only specimen; no hypothetical lifecycle correctness is claimed."""
    data = dict(
        scope="pure_shared_owner_seam", status="ACTIVE", phase="CREATED",
        refusal_code=None, finalized=False, pure_seam_complete=False,
        origin=dict(start=9, now=9, work_end=304, hard_end=309, clock_state="ok"),
        plan=None, files=[], calls=[],
        api_counters={api: dict(reserved=0, invocations=0, scalar_returns=0,
                                count_values=0, wrapper_returns=0) for api in APIS},
        byte_totals=dict(known_read_bytes=0, hashed_bytes=0, captured_bytes=0,
                         early_known_read_bytes=0, early_hashed_bytes=0,
                         early_captured_bytes=0, remaining_known_read_bytes=0,
                         remaining_hashed_bytes=0, remaining_captured_bytes=0,
                         read_count_unknown=False, early_reopens_after_claim=0,
                         early_rehashes_after_claim=0),
        early_context=None, evidence_context=None,
        loader=dict(bound=False, attempted=[], returned=[], cache_hits=[], records=[]),
        journal=dict(reservation=0, next_sequence=0, closed=False,
                     close_return_observed=False, close_acknowledged=False,
                     tip=None, events=[]),
        outputs=dict(reservation=callback(), publications={k: callback() for k in KINDS},
                     journal_close=callback(), total_reserved_bytes=0),
        stages=[], gates=[], errors=dict(primary=None, secondary=[]),
        terminal={k: False for k in TERMINAL}, qualification={k: False for k in QUALIFICATION})
    if populated:
        data["phase"] = "EARLY_CAPTURE"
        data["plan"] = dict(N=1, B=1, M=1, R=17, C=23, E=202, calls_used=1,
                            events_used=1, capture_used=0, raw_storage_used=0,
                            raw_storage_peak=0, read_buffer_capacity=0,
                            read_generation=0, output_reserved_bytes=0)
        data["files"] = [dict(
            id=0, spec=dict(path="D:\\FictionalFormatOnly\\input.py", role="software",
                            size=1, sha256="0" * 64, capture=True), early=True,
            open_state="reserved", handle_fact=atom(), identity_state="not_attempted",
            identity_queries=[], open_invocations=0, read_invocations=0,
            read_scalar_returns=0, known_read_bytes=0, hashed_bytes=0,
            captured_bytes=0, read_count_unknown=False, hash_complete=False,
            capture_complete=False, actual_sha256=None, close_reserved=False,
            close_invocations=0, close_return_observed=False, close_success=None,
            close_state="not_attempted")]
        data["calls"] = [dict(
            ordinal=0, api="ReadFile", file_id=0, reserved=True,
            invocation_reserved=False, raw_scalar=atom(), raw_count=atom(),
            raw_error=atom(), error_defined=False, scalar_aux_ack=False,
            count_aux_ack=False, right_transfer_ack=False,
            wrapper_return_observed=False, wrapper_state="not_returned",
            stopped=False, count_defined=False, buffer_state="not_applicable",
            buffer_generation=None, raw_buffer_bytes=None, raw_buffer_sha256=None)]
        data["api_counters"]["ReadFile"]["reserved"] = 1
        data["early_context"] = dict(file_ids=[0], captured_bytes=0, digests={}, complete=False)
        data["loader"] = dict(bound=True, attempted=["cohort_entry"], returned=[],
                              cache_hits=[], records=[dict(module="cohort_entry", state="reserved",
                                                           return_observed=False, accepted=False)])
        data["journal"].update(reservation=202, next_sequence=1, events=[dict(
            sequence=0, event="source_hash_reserved", stage=None, kind=None,
            file_id=0, module=None, elapsed=0, state="reserved",
            return_observed=False, acknowledged=False)])
        data["stages"] = [dict(name="authority_factory", state="reserved",
                               return_observed=False, accepted=False, verdict=None)]
    return data


def at(value, path):
    for key in path:
        value = value[key]
    return value


def main():
    names = (SOURCE, "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json",
             "SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json",
             "SHARED-OWNER-SNAPSHOT-VALIDATOR-PURE-PROBES-FIRST-v1.json",
             "check_shared_owner_snapshot_validator_v1.py",
             "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json",
             "SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json",
             Path(__file__).name)
    captured = {name: (ROOT / name).read_bytes() for name in names}
    pins = {name: dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            for name, raw in captured.items()}
    assert pins[SOURCE]["sha256"] == SOURCE_SHA
    assert pins[names[1]]["sha256"] == DATA_SHA
    assert pins[names[2]]["sha256"] == "4db8622f185edb1488a0066205b6248f0eb37b539e0806d04d748f277ea8e6ee"
    namespace = {"__name__": "peer_only_validator", "__file__": str(ROOT / SOURCE)}
    audit_active, denied = True, []

    def audit(event, args):
        if audit_active and (event == "open" or event.startswith(("os.", "subprocess.", "socket.", "ctypes."))):
            denied.append(event)
            raise RuntimeError("peer validator I/O denied: " + event)

    sys.addaudithook(audit)
    observations, failures = [], []
    try:
        exec(compile(captured[SOURCE], str(ROOT / SOURCE), "exec"), namespace)
        validate = namespace["validate_snapshot"]
        error = namespace["SnapshotValidationError"]

        def probe(name, value, *, accept=False, identity=None, original=None):
            try:
                result = validate(value, diagnostic_identity_check=identity)
            except BaseException as caught:
                if original is not None:
                    ok = caught is original
                    outcome = "same_original_exception" if ok else type(caught).__name__
                else:
                    ok = not accept and type(caught) is error
                    outcome = type(caught).__name__
                observations.append(dict(name=name, passed=ok, outcome=outcome))
                if not ok:
                    failures.append(name)
            else:
                ok = accept and original is None and result is None
                observations.append(dict(name=name, passed=ok, outcome="accepted"))
                if not ok:
                    failures.append(name)

        empty, populated = specimen(), specimen(True)
        probe("independent_empty_format", empty, accept=True)
        probe("independent_partial_format", populated, accept=True)
        record_paths = ((), ("origin",), ("plan",), ("files", 0), ("files", 0, "spec"),
                        ("calls", 0), ("calls", 0, "raw_count"), ("api_counters", "ReadFile"),
                        ("early_context",), ("loader", "records", 0), ("journal", "events", 0),
                        ("outputs", "publications", "candidate"), ("stages", 0), ("terminal",))
        for path in record_paths:
            data = deepcopy(populated)
            at(data, path)["caller_ready"] = True
            probe("closed_keys:" + repr(path), data)
        for path in (("plan", "C"), ("files", 0, "id"), ("files", 0, "spec", "size"),
                     ("calls", 0, "ordinal"), ("api_counters", "ReadFile", "reserved"),
                     ("journal", "events", 0, "sequence"),
                     ("outputs", "publications", "candidate", "prepared_bytes")):
            data = deepcopy(populated)
            at(data, path[:-1])[path[-1]] = True
            probe("bool_is_not_integer:" + repr(path), data)
        for number in (-(1 << 31), -1, 2, (1 << 31) - 1):
            data = deepcopy(populated)
            data["calls"][0]["raw_scalar"] = atom("BOOL32", number)
            probe("signed_nonzero_BOOL32:" + str(number), data, accept=True)
        for tag, number in (("BOOL32", True), ("BOOL32", 1 << 31), ("COUNT32", 1 << 32)):
            data = deepcopy(populated)
            data["calls"][0]["raw_count" if tag == "COUNT32" else "raw_scalar"] = atom(tag, number)
            probe("raw_atom_outside_domain:" + str(tag) + ":" + str(number), data)
        for path, bad in ((("phase",), "COMPLETE"), (("calls", 0, "buffer_state"), "ready"),
                          (("journal", "events", 0, "kind"), "seal"),
                          (("stages", 0, "verdict"), True),
                          (("qualification", "runtime_authorized"), True),
                          (("files", 0, "close_success"), 0)):
            data = deepcopy(populated)
            at(data, path[:-1])[path[-1]] = bad
            probe("closed_enum_flag_or_nullable:" + repr(path), data)
        huge = 10 ** 1000
        data = deepcopy(empty)
        data["origin"] = dict(start=huge, now=huge, work_end=huge + 295,
                              hard_end=huge + 300, clock_state="ok")
        probe("large_integer_time_no_float_coercion", data, accept=True)
        for number in (True, float("nan"), float("inf")):
            data = deepcopy(empty)
            data["origin"]["now"] = number
            probe("invalid_time:" + repr(number), data)
        for suffix, accept in (("\U00010000" * 2046 + "x", True),
                               ("\U00010000" * 2047, False), ("\ud800", False)):
            data = deepcopy(populated)
            data["files"][0]["spec"]["path"] = "D:\\" + suffix
            probe("UTF16_path_units:" + str(len(suffix)) + ":" + str(accept), data, accept=accept)
        data = deepcopy(populated)
        data["outputs"]["publications"]["candidate"].update(prepared_bytes=8192, prepared_sha256="a" * 64)
        probe("prepared_undispatched_8192", data, accept=True)
        data["outputs"]["publications"]["candidate"]["prepared_bytes"] = 8193
        probe("prepared_8193_refused", data)

        token = object()
        diagnostic = dict(identity=token, phase="entry", class_name="Error", message="captured",
                          args_repr=["retained"], format_failed=False)
        data = deepcopy(empty)
        data["errors"]["primary"] = diagnostic
        probe("diagnostic_resolved_exact_true", data, accept=True, identity=lambda t: t is token)
        probe("diagnostic_resolver_one_not_true", data, identity=lambda t: 1)
        for original in (ValueError("callback"), OverflowError("callback"), MemoryError("callback"),
                         KeyboardInterrupt("callback"), SystemExit("callback"), error("callback")):
            def raise_original(unused, original=original):
                raise original
            probe("callback_identity:" + type(original).__name__, data,
                  identity=raise_original, original=original)
        probe("callback_specimen_unchanged", data, accept=True, identity=lambda t: t is token)
    finally:
        audit_active = False
    result = dict(schema_version=1, status="passed" if not failures and not denied else "failed",
                  scope="independent_harness_validator_format_only", inputs=pins,
                  probe_count=len(observations), observations=observations,
                  failures=failures, denied_operation_attempts=denied,
                  reviewed_subject_modules_imported=0, subject_outputs_read=0,
                  fixture_expected_cases_read=0, actual_API_calls=0,
                  original_or_payload_operations=0, helper_source_executed=SOURCE,
                  subject_snapshot_or_lifecycle_qualified=False, runtime_authorized=False,
                  profile_qualified=False, verification_complete=False)
    destination = ROOT / "SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PROOF-v1.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    raw = destination.read_bytes()
    print(json.dumps(dict(path=str(destination), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                          status=result["status"], probes=len(observations), failures=failures,
                          denied_operation_attempts=denied), sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
