"""Literal Win64 frame/expectation authoring; no decoder, SDK or OS queries."""
import copy
import hashlib
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "CAPTURED-JOB-BYTES-CONTRACT-v2.json"
TARGET = HERE / "CAPTURED-JOB-BYTES-FIXTURES-v1.json"
FREEZE = HERE / "CAPTURED-JOB-BYTES-FIXTURE-FREEZE-v1.json"
NAMES = ("TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime",
         "TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses")
PID = 1234


def accounting(values=(0, 0, 0, 0, 0, 0, 0, 0), ok=True, error=0, returned=48):
    return dict(ok=ok, error=error, returned_bytes=returned, raw_hex=struct.pack("<qqqqIIII", *values).hex(),
                decoded=dict(zip(NAMES, values)))


def pid_list(ids=(), assigned=None, listed=None, ok=True, error=0, returned=None, tail=0):
    assigned = len(ids) if assigned is None else assigned
    listed = len(ids) if listed is None else listed
    slots = tuple(ids) + (tail,) * (16 - len(ids))
    return dict(ok=ok, error=error, returned_bytes=8+8*len(ids) if returned is None else returned,
                raw_hex=struct.pack("<II16Q", assigned, listed, *slots).hex(), assigned_count=assigned,
                listed_count=listed, pids=list(ids[:min(listed, 16)]))


def capture(a=None, p=None):
    return dict(query_started_monotonic_ns=100, query_finished_monotonic_ns=100,
                accounting=accounting() if a is None else a, pid_list=pid_list() if p is None else p)


def expected(a, p, *, a_status="decoded", p_status="decoded", raw=True, views=True, window=True, present=True, extras=None):
    result = dict(capture_present=present, query_window_valid=window, raw_complete=raw, source_views_consistent=views,
                  atomic_snapshot=False, resource_qualified=False,
                  accounting=None if a_status is None else dict(status=a_status, fields=a),
                  pid_list=None if p_status is None else dict(status=p_status, fields=p))
    if extras:
        for key, value in extras.items(): result[key].update(value)
    return result


def phase(name, status, own=PID):
    return dict(expected_phase=name, own_pid=own, status=status, resource_qualified=False, non_atomic_race_possible=True)


def main():
    assert not TARGET.exists() and not FREEZE.exists()
    empty_a = dict(zip(NAMES, (0, 0, 0, 0, 0, 0, 0, 0)))
    live_a = dict(zip(NAMES, (0, 0, 0, 0, 0, 1, 1, 0)))
    done_a = dict(zip(NAMES, (0, 0, 0, 0, 0, 1, 0, 0)))
    empty_p = dict(assigned_count=0, listed_count=0, pids=[])
    live_p = dict(assigned_count=1, listed_count=1, pids=[PID])
    items = []
    def add(identity, purpose, snapshot, projected, phases=()):
        items.append(dict(id=identity, purpose=purpose, snapshot=snapshot, expected_projection=projected, phase_checks=list(phases)))
    add("empty_return8", "Legal0/0empty; timestamps equal do not prove atomicity.", capture(), expected(empty_a, empty_p),
        [phase("empty", "matched_selected_source_phase", 0)])
    add("assigned_return16", "Legal1/1ownPID and both permitted running/finished branches.",
        capture(accounting((0, 0, 0, 0, 0, 1, 1, 0)), pid_list((PID,))), expected(live_a, live_p),
        [phase("assigned", "matched_selected_source_phase"), phase("running_or_finished", "matched_selected_source_phase")])
    add("finished_return8", "Legal1/0empty after oneprocess; no overall exit/success inference.",
        capture(accounting((0, 0, 0, 0, 0, 1, 0, 0))), expected(done_a, empty_p),
        [phase("finished", "matched_selected_source_phase"), phase("running_or_finished", "matched_selected_source_phase")])
    add("non_atomic_live_accounting_empty_PIDs", "Individually valid sequential responses are not normalized into a legal pair.",
        capture(accounting((0, 0, 0, 0, 0, 1, 1, 0))), expected(live_a, empty_p),
        [phase("running_or_finished", "counter_or_PID_mismatch")])
    add("failed_zero_error_and_buffer", "Failed query with error0/zeroed allocation is undefined, never legalempty.",
        capture(accounting(ok=False, error=0, returned=0)),
        expected(None, empty_p, a_status="undefined", raw=False, views=None), [phase("empty", "unresolved", 0)])
    partial = pid_list(tuple(range(1, 17)), assigned=17, listed=16, ok=False, error=234, returned=144)
    add("failed_PID_partial_buffer", "Failed/truncated PID query preserves no authoritative membership set.",
        capture(accounting((0, 0, 0, 0, 0, 1, 1, 0)), partial),
        expected(live_a, None, p_status="undefined", raw=False, views=None), [phase("assigned", "unresolved")])
    add("accounting_wrong_return_length", "Successflag cannot authorize47bytes as48byte accounting.", capture(accounting(returned=47)),
        expected(None, empty_p, a_status="malformed", raw=False, views=None), [phase("empty", "unresolved", 0)])
    add("PID_return_does_not_cover_list", "Listed1needs16returned bytes despite fullallocated136byte frame.",
        capture(accounting((0, 0, 0, 0, 0, 1, 1, 0)), pid_list((PID,), returned=8)),
        expected(live_a, None, p_status="malformed", raw=False, views=None), [phase("assigned", "unresolved")])
    drift = capture(accounting((0, 0, 0, 0, 0, 1, 1, 0)), pid_list((PID,)))
    drift["accounting"]["decoded"]["ActiveProcesses"] = 0
    add("reported_view_disagrees_with_raw", "Bytes are decoded independently of an incorrect cached summary.", drift,
        expected(live_a, live_p, views=False), [phase("assigned", "unresolved")])
    boolean = capture(accounting((0, 0, 0, 0, 0, 1, 1, 0)), pid_list((PID,)))
    boolean["accounting"]["decoded"]["TotalUserTime"] = False
    add("source_summary_bool_is_not_integer_zero", "False==0 cannot make a source view match a decoded integer.", boolean,
        expected(live_a, live_p, views=False), [phase("assigned", "unresolved")])
    add("unused_PID_tail_not_members", "Nonzero unreturned tail bytes remain raw, not extraPIDs or a zero-padding requirement.",
        capture(accounting((0, 0, 0, 0, 0, 1, 0, 0)), pid_list(tail=0xFEDCBA9876543210)), expected(done_a, empty_p),
        [phase("finished", "matched_selected_source_phase")])
    add("missing_capture_not_empty", "Unobserved capture isNone, not a manufactured zero Job.", None,
        expected(None, None, a_status=None, p_status=None, raw=False, views=None, window=False, present=False),
        [phase("empty", "unresolved", 0)])
    quality_values = (-0x0102030405060708, 0x0112233445566778, -17, 0x0010203040506070,
                      0x89ABCDEF, 0xF1234567, 0x10203040, 0x55667788)
    quality_ids = (0xFEDCBA9876543210,)
    quality_a = dict(zip(NAMES, quality_values))
    quality_p = dict(assigned_count=1, listed_count=1, pids=list(quality_ids))
    add("discriminating_signed_unsigned_endian_fields", "Distinct signed64 times/u32counters/u64PID and tail; no CPU-time semanticclaim.",
        capture(accounting(quality_values), pid_list(quality_ids, tail=0x0102030405060708)), expected(quality_a, quality_p),
        [phase("assigned", "counter_or_PID_mismatch")])
    window = capture(); window["query_started_monotonic_ns"] = True
    add("malformed_window_preserves_query_data", "Malformed bool window isFalse/issue, not an outer-schema exception.", window,
        expected(empty_a, empty_p, raw=False, window=False), [phase("empty", "unresolved", 0)])
    missing = capture(); missing["accounting"] = None
    add("missing_component_is_None", "Missingaccounting does not erase definedPIDdata or become zero accounting.", missing,
        expected(None, empty_p, a_status=None, raw=False, views=None), [phase("empty", "unresolved", 0)])
    invalid = capture(); invalid["accounting"]["ok"] = 1; invalid["accounting"]["raw_hex"] = "00" * 200
    add("invalid_metadata_is_bounded_not_exported", "Integerflag/oversizedhex are not retained as plausible APIflag/frame.", invalid,
        expected(None, empty_p, a_status="malformed", raw=False, views=None, extras={"accounting": dict(ok=None, raw_hex=None)}),
        [phase("empty", "unresolved", 0)])
    assert len(items) == 16
    extra = capture(); extra["verified"] = True
    api = [dict(id="outer_schema_ready_flag_rejected", operation="decode_job_snapshot", input=extra,
                expected_exception="ValueError", expected_message="snapshot_schema"),
           dict(id="serialized_decoder_flags_rejected", operation="check_snapshot_phase", input=dict(raw_complete=True, source_views_consistent=True),
                expected_phase="finished", own_pid=PID, expected_exception="TypeError", expected_message="decoder_result_type"),
           dict(id="bool_own_PID_rejected", operation="check_snapshot_phase_fixture", fixture_id="assigned_return16",
                expected_phase="assigned", own_pid=True, expected_exception="ValueError")]
    raw_contract = CONTRACT.read_bytes()
    corpus = dict(schema_version=1, contract_sha256=hashlib.sha256(raw_contract).hexdigest(), captures=items, api_controls=api,
        synthetic_only=True, source_summary_expected_fields_authored=True,
        expected_projection_rule="Every specified key/value must match. All results keep resource_qualifiedFalse; issues are finite names, not copied arbitrary invalidmetadata.",
        no_live_sample_replay=True, no_OS_or_SDK_queries=True)
    raw = (json.dumps(corpus, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with TARGET.open("xb") as stream: stream.write(raw)
    frozen = dict(schema_version=1, status="frozen_actual_format_synthetic_Job_frames_before_decoder_implementation",
        contract=dict(path=str(CONTRACT.resolve()), bytes=len(raw_contract), sha256=hashlib.sha256(raw_contract).hexdigest()),
        fixtures=dict(path=str(TARGET.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()),
        author=dict(path=str(Path(__file__).resolve()), sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        counts=dict(captures=len(items), phase_checks=sum(len(item["phase_checks"]) for item in items), api_controls=len(api)),
        source_decoder_implemented=False, SDK_OS_native_calls=0, CPU_GGUF_oldpack_operations=0, resource_qualification=False)
    with FREEZE.open("x", encoding="utf-8", newline="\n") as stream: json.dump(frozen, stream, indent=2); stream.write("\n")
    print(json.dumps(dict(status=frozen["status"], fixtures_sha256=frozen["fixtures"]["sha256"], counts=frozen["counts"])))


if __name__ == "__main__": main()
