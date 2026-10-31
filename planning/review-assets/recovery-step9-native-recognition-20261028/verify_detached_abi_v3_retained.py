"""Read retained files only; no helper imports, process/API calls, or native loads."""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import math
import ntpath
import re
from pathlib import Path
import stat
import struct

ROOT = Path(r"D:\Projects\drug_target_agents")
PHASE = ROOT / "planning/review-assets/recovery-step9-native-recognition-20261028"
RUN = ROOT / "data/cache/r09-detached-ABI-observation-v3-20261029T001629Z"
PROTOCOL_SHA = "88672320d5969c5dbd32e265155353f31b187b51aeaad39396f40788fdda1fb8"
DECISION_SHA = "40978ab1f166c29a7e52c835fb921c2543bf9eead5138fd97d6881fde204ac69"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pin(path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def check_pin(record, path=None):
    p = path or Path(record["path"])
    for part in (p, *p.parents):
        s = part.lstat()
        assert not s.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT, str(part)
    assert p.is_file()
    assert p.stat().st_size == record["bytes"], str(p)
    assert sha(p) == record["sha256"], str(p)


def load(path):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            assert k not in d, (str(path), k)
            d[k] = v
        return d
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def decode_wide(record, cap):
    assert set(record) == {"utf16_units", "prefix_utf16_units", "truncated", "pair_cut_adjusted", "utf8_conversion", "utf8", "utf16_code_units_hex"}
    total, count = record["utf16_units"], record["prefix_utf16_units"]
    assert type(total) is type(count) is int and 0 <= count <= min(total, cap)
    assert type(record["truncated"]) is type(record["pair_cut_adjusted"]) is bool
    assert record["truncated"] == (count < total)
    assert count == min(total, cap) - int(record["pair_cut_adjusted"])
    assert not record["pair_cut_adjusted"] or total > cap
    numeric_hex = record["utf16_code_units_hex"]
    assert type(numeric_hex) is str and len(numeric_hex) == count * 4 and re.fullmatch("[0-9a-f]*", numeric_hex)
    # Each four hex digits encode a numeric wchar_t, not a little-endian buffer hex dump.
    units = [int(numeric_hex[i:i+4], 16) for i in range(0, len(numeric_hex), 4)]
    raw = b"".join(unit.to_bytes(2, "little") for unit in units)
    assert record["utf8_conversion"] == "returned" and type(record["utf8"]) is str
    decoded = raw.decode("utf-16-le", errors="strict")
    assert decoded == record["utf8"] and len(decoded.encode("utf-16-le")) // 2 == count
    assert not record["truncated"] and not record["pair_cut_adjusted"]  # Actual evidence, not a general formatter claim.
    return decoded


def validate_diagnostic(event, marker, stdout):
    assert set(event) == {"event", "module_policy"} and event["event"] == "module_policy_rejection"
    context = marker["module_policy"]
    assert context == stdout["module_policy"]
    assert set(context) == {"context_status", "original_tag", "branch", "enumeration_index", "path_representation",
                            "name", "path", "system_directory_matches", "system_basename_listed", "diagnostic_row_publication"}
    assert context["context_status"] == "built" and context["original_tag"] == "unapproved_non_native_module"
    assert context["branch"] == "non_native_system_policy"
    assert type(context["enumeration_index"]) is int and context["enumeration_index"] == 5
    assert context["path_representation"] == "GetModuleFileNameW_then_existing_GetFullPathNameW_lexical_normalization"
    assert type(context["system_directory_matches"]) is type(context["system_basename_listed"]) is bool
    assert context["system_directory_matches"] is True and context["system_basename_listed"] is False
    assert not (context["system_directory_matches"] and context["system_basename_listed"])
    assert context["diagnostic_row_publication"] == "returned"
    expected_event = dict(context, diagnostic_row_publication="attempt_reserved")
    assert event["module_policy"] == expected_event
    name, path = decode_wide(context["name"], 256), decode_wide(context["path"], 2048)
    assert name == "apphelp.dll" and path == r"C:\Windows\SYSTEM32\apphelp.dll"
    assert ntpath.basename(path) == name
    return {"reported_name": name, "reported_lexical_path": path, "enumeration_index": 5,
            "name_UTF16_units": context["name"]["utf16_units"], "path_UTF16_units": context["path"]["utf16_units"],
            "numeric_UTF16_hex_matches_UTF8": True, "truncated": False, "pair_cut_adjusted": False,
            "system_directory_matches": True, "system_basename_listed": False,
            "publication": {"diagnostic_row": "attempt_reserved", "failure_marker_and_stdout": "returned",
                            "complete_diagnostic_row_retained": True},
            "scope": "Reported metadata of this new run only; not image authenticity, full census, causal evidence or historical identity.",
            "reported_image_file_opened_by_verifier": False}


def main():
    protocol = load(RUN / "effective-protocol.json")
    assert sha(RUN / "effective-protocol.json") == PROTOCOL_SHA
    assert sha(PHASE / "DETACHED-ABI-OBSERVATION-PROTOCOL-v3.json") == PROTOCOL_SHA
    decision = PHASE / "DETACHED-ABI-OBSERVATION-ROOT-DECISION-v3.json"
    assert sha(decision) == DECISION_SHA
    assert len(protocol["inputs"]) == 243
    assert len({p["path"].casefold() for p in protocol["inputs"]}) == 243
    # Explicit approved-input universe: never inspect any guessed unknown module.
    for p in protocol["inputs"]:
        assert not p["path"].lower().endswith(".gguf")
        assert Path(p["path"]).name.lower() not in {"ggml-cpu.dll", "ggml-cpu-x64.dll", "apphelp.dll"}
        check_pin(p)
    assert len(protocol["runtime_pins"]) == 4
    assert len(protocol["system_candidates"]) == 16
    assert protocol["creation_flags"] == 0x8040C
    assert protocol["recognition_enabled"] is False
    assert protocol["maximum_attempts"] == 1 and protocol["automatic_retry"] is False
    assert protocol["no_model_or_CPU_paths_supplied"] is True
    assert protocol["expected_version"] == ""

    files = sorted(p for p in RUN.rglob("*") if p.is_file())
    relative = {p.relative_to(RUN).as_posix() for p in files}
    expected = {"effective-protocol.json", "failure.json", "parent-report.json",
                "parent-reservation.json", "post-lease-cleanup.json", "receipt.json",
                "stderr.bin", "stdout.bin", "terminal-seal.json", "execution/journal.jsonl",
                "execution/child/attempt.json", "execution/child/failure.json",
                "execution/child/result.partial.jsonl"}
    assert relative == expected
    assert len(files) == 13
    receipt = load(RUN / "receipt.json")
    seal = load(RUN / "terminal-seal.json")
    cleanup = load(RUN / "post-lease-cleanup.json")
    report = load(RUN / "parent-report.json")
    primary = load(RUN / "failure.json")
    for d, count, excluded in ((receipt, 10, {"receipt.json", "post-lease-cleanup.json", "terminal-seal.json"}),
                               (seal, 12, {"terminal-seal.json"})):
        assert d["status"] == "failed"
        assert len(d["outputs"]) == count
        assert set(d["outputs"]) == expected - excluded
        for name, record in d["outputs"].items():
            check_pin(record, RUN / name)
    assert receipt["protocol_sha256"] == PROTOCOL_SHA
    assert seal["required"] is True and seal["late_failure_marker"] is None
    for k in ("earlier_receipt", "cleanup_artifact", "primary_failure_marker"):
        check_pin(seal[k])
    check_pin(cleanup["earlier_receipt"])
    check_pin(cleanup["primary_failure_marker"])
    assert cleanup["primary_failure"] == report["failure"]
    assert primary["authoritative"] is True and primary["automatic_retry"] is False
    assert report["failure"] == {"error": "ABI child failed", "error_class": "RuntimeError"}
    assert report["status"] == "failed" and report["returncode"] == 2 and report["reaped"] is True
    assert report["attempt_reserved"] is True and report["call_return_observed"] is True
    assert not report["cleanup_errors"] and not report["finalization_errors"]
    assert cleanup["parent_deadline_exceeded"] is False and not cleanup["close_errors"]
    for v, bound in ((report["child_full_process_elapsed_seconds"], 30),
                     (report["elapsed_before_early_receipt_seconds"], 60),
                     (cleanup["parent_elapsed_after_leases_seconds"], 60),
                     (seal["parent_elapsed_before_terminal_seal_seconds"], 60)):
        assert type(v) in (int, float) and math.isfinite(v) and 0 <= v < bound

    events = [json.loads(line) for line in (RUN / "execution/journal.jsonl").read_text().splitlines()]
    assert len(events) == 17
    previous = None
    for i, e in enumerate(events):
        assert e["sequence"] == i and e["previous_sha256"] == previous
        body = {k: v for k, v in e.items() if k != "sha256"}
        canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        assert hashlib.sha256(canonical).hexdigest() == e["sha256"]
        previous = e["sha256"]
    names = [e["event"] for e in events]
    assert names.count("abi_CreateProcessW_reserved") == names.count("abi_created_suspended") == 1
    assert names.count("abi_resume_reserved") == names.count("abi_resume_returned") == 1
    pid = next(e["details"]["pid"] for e in events if e["event"] == "abi_created_suspended")
    assert pid == 21828
    assigned = next(e["details"] for e in events if e["event"] == "abi_assigned_before_resume")
    assert assigned["assigned_during_CreateProcessW"] is True and assigned["manual_assignment_fallback"] is False
    assert assigned["identity"]["pid"] == pid
    assert report["resumption"]["previous_suspend_count"] == 1
    snapshots = [e["details"] for e in events if e["event"] == "abi_job_snapshot_observed"]
    assert [s["stage"] for s in snapshots] == ["configured_empty", "before_resume", "running_first", "after_wait"]
    decoded = []
    for i, row in enumerate(snapshots):
        s = row["snapshot"]; a = s["accounting"]; p = s["pid_list"]
        assert a["ok"] is True and a["error"] == 0 and a["returned_bytes"] == 48
        raw = bytes.fromhex(a["raw_hex"]); assert len(raw) == 48
        vals = struct.unpack("<qqqqIIII", raw)
        keys = ("TotalUserTime", "TotalKernelTime", "ThisPeriodTotalUserTime", "ThisPeriodTotalKernelTime",
                "TotalPageFaultCount", "TotalProcesses", "ActiveProcesses", "TotalTerminatedProcesses")
        assert dict(zip(keys, vals)) == a["decoded"]
        pr = bytes.fromhex(p["raw_hex"]); assert len(pr) == 136
        assigned_count, listed_count = struct.unpack_from("<II", pr)
        pids = list(struct.unpack_from("<" + "Q" * listed_count, pr, 8)) if listed_count else []
        assert p["ok"] is True and p["error"] == 0
        assert (assigned_count, listed_count, pids) == (p["assigned_count"], p["listed_count"], p["pids"])
        total, active = ((0, 0), (1, 1), (1, 1), (1, 0))[i]
        assert (vals[5], vals[6], vals[7], pids) == (total, active, 0, [pid] if active else [])
        decoded.append({"stage": row["stage"], "total": total, "active": active, "terminated": 0, "pids": pids})
    assert report["final_job_snapshot"] == snapshots[-1]["snapshot"]
    terminal = report["terminal_observation"]
    assert terminal["complete"] is True and terminal["exit_observed"] is True
    assert terminal["scope"] == "after_observed_owned_exit_before_cleanup"
    assert not terminal["errors"] and not report["terminal_observation_errors"]
    assert terminal["interrupted"] is False and terminal["capture_polls_reserved"] == 1
    observations = terminal["observations"]
    assert observations["job_snapshot"]["raw"] == observations["job_snapshot"]["value"] == report["final_job_snapshot"]
    assert observations["job_snapshot"]["predicate"] == "passed"
    assert observations["job_snapshot"]["raw_publication"] == "returned"
    assert observations["memory_limits_and_peaks"]["value"] == report["memory_limits_and_peaks"]
    for item in (observations["job_snapshot"], observations["memory_limits_and_peaks"], *observations["capture_drain"]["stdout"]["calls"]):
        assert item["attempt_reserved"] is item["call_attempted"] is item["return_observed"] is True
        assert item["status"] == "returned"
        assert terminal["started_at"] <= item["started_at"] <= item["returned_at"] <= terminal["ended_at"] < terminal["work_deadline"]
    # All reservations with real returns are independently bound to the journal.
    call_events = [e for e in events if e["event"] == "detached_ABI_terminal_call_reserved"]
    assert len(call_events) == 3
    memory = report["memory_limits_and_peaks"]
    assert memory == {"active_limit": 1, "flags": 8968, "job_commit": 268435456,
                      "process_commit": 268435456, "peak_job_commit": 2166784, "peak_process_commit": 2166784}
    for stream, expected_bytes in (("stdout", 939), ("stderr", 0)):
        cap = report["captures"][stream]
        assert cap == {"eof": True, "observed_bytes_at_least": expected_bytes,
                       "retained_bytes": expected_bytes, "truncated": False}
        assert (RUN / (stream + ".bin")).stat().st_size == expected_bytes
    assert report["counters_instrumented"] is False
    assert report["parent_GGUF_reads"] == 0 and report["model_paths_supplied_to_child"] is False
    assert report["dependency_initializers_may_have_effects"] is True
    assert len(report["lease_ownership"]) == len(cleanup["outcomes"]) == 490
    owned = collections.Counter((x["path"], x["handle"]) for x in report["lease_ownership"])
    closed = collections.Counter((x["path"], x["handle"]) for x in cleanup["outcomes"])
    assert owned == closed
    assert len({x["path"] for x in report["lease_ownership"]}) == 245
    assert all(x["closed_after"] and x["close_error"] is None for x in cleanup["outcomes"])
    assert all(x["validation"] == "passed" for x in cleanup["outcomes"])
    recheck = report["final_input_recheck"]
    assert {k: v for k, v in recheck.items() if k != "outcomes"} == {
        "closed_recheck_leases": 245, "new_read_leases": 245, "status": "completed"}
    assert len(recheck["outcomes"]) == 245
    assert all(x["return_observed"] and x["close_return_observed"] for x in recheck["outcomes"])
    child = RUN / "execution/child"
    attempt = load(child / "attempt.json"); failure = load(child / "failure.json")
    partial = [json.loads(x) for x in (child / "result.partial.jsonl").read_text().splitlines()]
    assert attempt == {"schema_version": 1, "mode": "--abi", "status": "claimed_before_native_load", "draft": True}
    assert failure["message"] == "unapproved_non_native_module" and failure["status"] == "failed"
    assert failure["token_budget_used"] == failure["apply_calls"] == failure["accept_calls"] == 0
    assert len(partial) == 3 and partial[2] == failure
    assert partial[0] == {"event": "before_explicit_required_OpenMP_dependency_load", "dependency_native_initialization_possible": True}
    stdout = json.loads((RUN / "stdout.bin").read_text())
    assert set(stdout) == {"status", "message", "module_policy"}
    assert stdout["status"] == "failed" and stdout["message"] == "unapproved_non_native_module"
    diagnostic = validate_diagnostic(partial[1], failure, stdout)
    assert names[-1] == "detached_ABI_terminal" and events[-1]["details"]["status"] == "failed"

    source = PHASE / "typed_public_c_recognizer_v5.cpp"
    assert sha(source) == "c2b802507dd135c33df512a386250d0781bbee0673ed6276bb5512f42adead8c"
    lines = source.read_text(encoding="utf-8").splitlines()
    assert 'Api api(llama, ggml, base)' in lines[414]
    assert 'runtime.modules(*out)' in lines[414] and 'api.llama_version()' in lines[415]
    assert 'BridgeError rejection("unapproved_non_native_module")' in lines[189]
    prior_verification = load(PHASE / "DETACHED-ABI-V2-RESULT-VERIFICATION.json")
    assert sha(PHASE / "DETACHED-ABI-V2-RESULT-VERIFICATION.json") == "4b2a3cd7b09c14a8dc3d444ea6e815c8fefeeb9952cfa9724615af77769e9c24"
    for record in prior_verification["outputs"]:
        check_pin(record)
    assert prior_verification["unavailable"][0] == "identity/path/hash of unapproved module"
    old_outputs_checked = len(prior_verification["outputs"])
    outputs = [pin(p) | {"relative_path": p.relative_to(RUN).as_posix()} for p in files]
    result = {
        "schema_version": 1,
        "status": "verified_retained_negative_ABI_module_policy_failure",
        "review_type": "AI read-only engineering evidence verification; not scientific or human review",
        "verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run": str(RUN), "protocol": pin(RUN / "effective-protocol.json"), "root_decision": pin(decision),
        "verifier": pin(Path(__file__)), "inputs_verified": 243,
        "runtime_DLL_pins": 4, "system_candidate_pins": 16,
        "file_count": 13, "directory_count_excluding_root": 2,
        "journal_events": 17, "journal_tip_sha256": previous,
        "owned_child": {"pid": pid, "returncode": 2, "reaped": True, "creation_flags": "0x0008040C",
                        "full_process_elapsed_seconds": report["child_full_process_elapsed_seconds"],
                        "CreateProcess_attempts": 1, "ResumeThread_attempts": 1},
        "snapshots": decoded, "memory_limits_and_peaks": memory, "captures": report["captures"],
        "lease_records": 490, "unique_leased_paths": 245, "final_recheck": {
            "status": "completed", "opened_and_closed": 245},
        "terminal_observation": {"complete": True, "meaning": "bounded observations complete; ABI failed",
            "scope": terminal["scope"], "capture_polls_reserved": 1, "terminal_call_reservations": 3,
            "independent_errors": [], "raw_job_and_peaks_before_owner_cleanup": True},
        "parent_seconds_before_terminal_seal": seal["parent_elapsed_before_terminal_seal_seconds"],
        "child_failure": failure,
        "reported_current_run_module": diagnostic,
        "old_v2_offender": "unknown; no retrospective identity attribution",
        "old_v2_original_outputs_verified_unchanged": old_outputs_checked,
        "source_inference": {"source": pin(source), "module_policy_failure_line": 190,
            "Api_and_inventory_line": 415, "first_explicit_version_call_line": 416,
            "explicit_version_and_default_queries_reached": 0,
            "basis": "Named failure is emitted by runtime.modules() before its row and subsequent explicit queries; counts not instrumented.",
            "export_resolution": "Source ordering places successful Api construction before rejected module enumeration; not a finalized ABI observation."},
        "unavailable": ["image authenticity/hash of reported unapproved module", "complete observed module inventories",
            "llama_version result", "typed model defaults", "ABI layouts row", "final child result.jsonl",
            "initialization side-effect instrumentation", "vocabulary/grammar/EOG/model/inference qualification"],
        "scope": {"review_actual_API_calls": 0, "review_actual_children": 0,
                  "review_native_loads": 0, "review_GGUF_reads": 0,
                  "approved_input_files_read_for_hashing": True,
                  "unknown_module_guessed_or_allowlist_expanded": False,
                  "scientific_validation": "not established"},
        "outputs": outputs,
        "next_gate": "Review scoped current-run module-policy evidence before proposing any policy change; no allowlist expansion, unknown image opens or automatic repeat."
    }
    target = PHASE / "DETACHED-ABI-V3-RESULT-VERIFICATION.json"
    with target.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps({"status": result["status"], "report": str(target), "sha256": sha(target),
                      "inputs": 243, "files": 13, "events": 17, "leases": 490, "pid": pid}))


if __name__ == "__main__":
    main()
