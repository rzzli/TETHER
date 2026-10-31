"""Read retained files only; no helper imports, process/API calls, or native loads."""
from __future__ import annotations

import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import stat
import struct

ROOT = Path(r"D:\Projects\drug_target_agents")
PHASE = ROOT / "planning/review-assets/recovery-step9-native-recognition-20261028"
RUN = ROOT / "data/cache/r09-detached-ABI-observation-v2-20261028T233241Z"
PROTOCOL_SHA = "58154061a1a2dff9e3369a01662cb2b8be601012ba16c2b694f98255067adf6d"
DECISION_SHA = "077108c22c3642271f282e527ac02957b74117ad3b161a5d8e6c5fd52e788978"


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


def main():
    protocol = load(RUN / "effective-protocol.json")
    assert sha(RUN / "effective-protocol.json") == PROTOCOL_SHA
    assert sha(PHASE / "DETACHED-ABI-OBSERVATION-PROTOCOL-v2.json") == PROTOCOL_SHA
    decision = PHASE / "DETACHED-ABI-OBSERVATION-ROOT-DECISION-v2.json"
    assert sha(decision) == DECISION_SHA
    assert len(protocol["inputs"]) == 202
    assert len({p["path"].casefold() for p in protocol["inputs"]}) == 202
    # Explicit approved-input universe: never inspect any guessed unknown module.
    for p in protocol["inputs"]:
        assert not p["path"].lower().endswith(".gguf")
        assert Path(p["path"]).name.lower() != "ggml-cpu.dll"
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
    assert pid == 37796
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
    # All reservations with real returns are independently bound to the journal.
    call_events = [e for e in events if e["event"] == "detached_ABI_terminal_call_reserved"]
    assert len(call_events) == 3
    memory = report["memory_limits_and_peaks"]
    assert memory == {"active_limit": 1, "flags": 8968, "job_commit": 268435456,
                      "process_commit": 268435456, "peak_job_commit": 2166784, "peak_process_commit": 2166784}
    for stream, expected_bytes in (("stdout", 62), ("stderr", 0)):
        cap = report["captures"][stream]
        assert cap == {"eof": True, "observed_bytes_at_least": expected_bytes,
                       "retained_bytes": expected_bytes, "truncated": False}
        assert (RUN / (stream + ".bin")).stat().st_size == expected_bytes
    assert report["counters_instrumented"] is False
    assert report["parent_GGUF_reads"] == 0 and report["model_paths_supplied_to_child"] is False
    assert report["dependency_initializers_may_have_effects"] is True
    assert len(report["lease_ownership"]) == len(cleanup["outcomes"]) == 408
    owned = collections.Counter((x["path"], x["handle"]) for x in report["lease_ownership"])
    closed = collections.Counter((x["path"], x["handle"]) for x in cleanup["outcomes"])
    assert owned == closed
    assert len({x["path"] for x in report["lease_ownership"]}) == 204
    assert all(x["closed_after"] and x["close_error"] is None for x in cleanup["outcomes"])
    assert all(x["validation"] == "passed" for x in cleanup["outcomes"])
    recheck = report["final_input_recheck"]
    assert {k: v for k, v in recheck.items() if k != "outcomes"} == {
        "closed_recheck_leases": 204, "new_read_leases": 204, "status": "completed"}
    assert len(recheck["outcomes"]) == 204
    assert all(x["return_observed"] and x["close_return_observed"] for x in recheck["outcomes"])
    child = RUN / "execution/child"
    attempt = load(child / "attempt.json"); failure = load(child / "failure.json")
    partial = [json.loads(x) for x in (child / "result.partial.jsonl").read_text().splitlines()]
    assert attempt == {"schema_version": 1, "mode": "--abi", "status": "claimed_before_native_load", "draft": True}
    assert failure["message"] == "unapproved_non_native_module" and failure["status"] == "failed"
    assert failure["token_budget_used"] == failure["apply_calls"] == failure["accept_calls"] == 0
    assert len(partial) == 2 and partial[1] == failure
    assert partial[0] == {"event": "before_explicit_required_OpenMP_dependency_load", "dependency_native_initialization_possible": True}
    assert json.loads((RUN / "stdout.bin").read_text()) == {"status": "failed", "message": "unapproved_non_native_module"}
    assert names[-1] == "detached_ABI_terminal" and events[-1]["details"]["status"] == "failed"

    source = PHASE / "typed_public_c_recognizer_v4.cpp"
    assert sha(source) == "2f34035545c6d7bd742b8932a95449aeb76ebc48084e8dc170cbea6b740794ae"
    lines = source.read_text(encoding="utf-8").splitlines()
    assert 'Api api(llama, ggml, base)' in lines[376]
    assert 'runtime.modules()' in lines[376] and 'api.llama_version()' in lines[377]
    assert 'unapproved_non_native_module' in lines[187]
    outputs = [pin(p) | {"relative_path": p.relative_to(RUN).as_posix()} for p in files]
    result = {
        "schema_version": 1,
        "status": "verified_retained_negative_ABI_module_policy_failure",
        "review_type": "AI read-only engineering evidence verification; not scientific or human review",
        "verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run": str(RUN), "protocol": pin(RUN / "effective-protocol.json"), "root_decision": pin(decision),
        "verifier": pin(Path(__file__)), "inputs_verified": 202,
        "runtime_DLL_pins": 4, "system_candidate_pins": 16,
        "file_count": 13, "directory_count_excluding_root": 2,
        "journal_events": 17, "journal_tip_sha256": previous,
        "owned_child": {"pid": pid, "returncode": 2, "reaped": True, "creation_flags": "0x0008040C",
                        "full_process_elapsed_seconds": report["child_full_process_elapsed_seconds"],
                        "CreateProcess_attempts": 1, "ResumeThread_attempts": 1},
        "snapshots": decoded, "memory_limits_and_peaks": memory, "captures": report["captures"],
        "lease_records": 408, "unique_leased_paths": 204, "final_recheck": {
            "status": "completed", "opened_and_closed": 204},
        "terminal_observation": {"complete": True, "meaning": "bounded observations complete; ABI failed",
            "scope": terminal["scope"], "capture_polls_reserved": 1, "terminal_call_reservations": 3,
            "independent_errors": [], "raw_job_and_peaks_before_owner_cleanup": True},
        "parent_seconds_before_terminal_seal": seal["parent_elapsed_before_terminal_seal_seconds"],
        "child_failure": failure,
        "source_inference": {"source": pin(source), "module_policy_failure_line": 188,
            "Api_and_inventory_line": 377, "first_explicit_version_call_line": 378,
            "explicit_version_and_default_queries_reached": 0,
            "basis": "Named failure is emitted by runtime.modules() before its row and subsequent explicit queries; counts not instrumented.",
            "export_resolution": "Source ordering places successful Api construction before rejected module enumeration; not a finalized ABI observation."},
        "unavailable": ["identity/path/hash of unapproved module", "complete observed module inventories",
            "llama_version result", "typed model defaults", "ABI layouts row", "final child result.jsonl",
            "initialization side-effect instrumentation", "vocabulary/grammar/EOG/model/inference qualification"],
        "scope": {"review_actual_API_calls": 0, "review_actual_children": 0,
                  "review_native_loads": 0, "review_GGUF_reads": 0,
                  "approved_input_files_read_for_hashing": True,
                  "unknown_module_guessed_or_allowlist_expanded": False,
                  "scientific_validation": "not established"},
        "outputs": outputs,
        "next_gate": "Prospective bounded diagnostics must retain the rejected module identity before failing closed; no guessed allowlist addition or automatic repeat."
    }
    target = PHASE / "DETACHED-ABI-V2-RESULT-VERIFICATION.json"
    with target.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps({"status": result["status"], "report": str(target), "sha256": sha(target),
                      "inputs": 202, "files": 13, "events": 17, "leases": 408, "pid": pid}))


if __name__ == "__main__":
    main()
