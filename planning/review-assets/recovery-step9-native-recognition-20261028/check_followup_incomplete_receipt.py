"""Pure eight-file follow-up receipt fixture; no real child or request."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE / "fetch_native_followup.py"
HELPER_SHA = "d9fe3d0807d997bc1c1493b518237b55f2e75f65cdc1a537caa896f5fdd57c47"
SCOPE = HERE / "FOLLOWUP-SOURCE-SCOPE.json"
SCOPE_SHA = "fa5b8290ae8d1b63f6a43d6234050e07ffb970eec79e46513aee4e5e7d62428d"
assert sys.flags.isolated and sys.dont_write_bytecode
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA
assert hashlib.sha256(SCOPE.read_bytes()).hexdigest() == SCOPE_SHA
spec = importlib.util.spec_from_file_location("fixed_eight_followup_under_test", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
denied = []


def audit(event, args):
    if event in ("subprocess.Popen", "os.system", "socket.__new__", "socket.connect", "socket.getaddrinfo"):
        denied.append(event)
        raise RuntimeError("Supplemental fixture permits no child or network")


sys.addaudithook(audit)
cache = ROOT / "data/cache" / ("r09-followup-incomplete-receipt-" + str(time.time_ns()))
journal = helper.RunJournal(cache, kind="build")
(cache / "attempts").mkdir()
(cache / "sources").mkdir()
calls = []
state = dict(dispatch_attempts=0, spawned_children=0, denied=[], active_argv=None)
expected = "0" * 64


def runner(entry, cache, protocol_sha, journal, state, deadline):
    calls.append(entry["index"])
    directory = cache / "attempts" / f"{entry['index']:02d}"
    directory.mkdir()
    owner = dict(pid=1234, parent_pid=os.getpid(), protocol_sha256=protocol_sha,
                 deadline_monotonic=123.0)
    helper.write_new(directory / "reservation.json", dict(parent_pid=os.getpid(),
        protocol_sha256=protocol_sha, deadline_monotonic=123.0,
        conservative_body_reservation_bytes=1048576))
    helper.write_new(directory / "spawned-worker.json", owner)
    helper.write_new(directory / "child-started.json", dict(**owner,
        base_executable=str(helper.BASE_EXE.resolve()),
        executable=str(helper.DEFAULT_PYTHON.resolve()), prefix=str(helper.DEFAULT_ENV.resolve()),
        isolated=True, dont_write_bytecode=True, asof_distribution_version="0.3.11"))
    child = dict(**entry, schema_version=1, status="failed_or_incomplete",
        retained_body_bytes=0, observed_body_bytes_at_least=0, unknown_received=False,
        source_bytes=None, source_sha256=None, protocol_sha256=protocol_sha,
        error_class="InterruptedError", error="Synthetic incomplete read with zero retained bytes")
    helper.write_new(directory / "child-result.json", child)
    helper.write_new(directory / "stdout.bin", child)
    with (directory / "stderr.bin").open("xb"):
        pass
    return dict(pid=1234, spawned=True, reaped=True, returncode=0, timed_out=False,
        cleanup_errors=[], full_process_elapsed_seconds=0.01, effective_seconds=20,
        streams={"stdout":dict(truncated=False,error_class=None),
                 "stderr":dict(truncated=False,error_class=None)})


try:
    records, retained = helper.collect({}, cache, expected, journal, state,
        time.monotonic() + 300, runner=runner)
finally:
    journal.close()

assert calls == [0] and retained == 0 and len(records) == 8
first = records[0]
assert first["error_class"] == "RuntimeError"
assert first["error"] == "Incomplete/unbound source receipt"
assert first["status"] == "failed_or_incomplete_unknown_receipt"
assert first["unknown_received"] is True
assert first["source_bytes"] is None and first["source_sha256"] is None
assert first["conservative_body_reservation_bytes"] == 1048576
assert first["reservation_disposition"] == "retained_unknown_not_zero_measured_transfer"
assert all(row["status"] == "not_attempted_after_unknown_receipt" for row in records[1:])
assert state["dispatch_attempts"] == state["spawned_children"] == 0 and denied == []
chain = helper.read_chain(cache / "journal.jsonl")
assert chain[-1]["event"] == "source_receipt_unknown_stop"
assert chain[-1]["details"]["error"] == "Incomplete/unbound source receipt"
assert chain[-1]["details"]["unknown_received"] is True
assert helper.sha(HELPER) == HELPER_SHA and helper.sha(SCOPE) == SCOPE_SHA

report = dict(schema_version=1,status="passed_incomplete_receipt_after_valid_identity_remaining_seven",
    helper_sha256=HELPER_SHA, followup_scope_sha256=SCOPE_SHA, fixture_sha256=helper.sha(__file__),
    actual_children=0, actual_network_requests=0, output=str(cache),
    simulated_child_reports=1, simulated_worker_pid=1234, valid_identity_metadata=True,
    intended_rejection=first["error"], actual_rejection=chain[-1]["details"]["error"],
    parent_unknown_received=True, parent_source_bytes=None, conservative_reservation_retained=1048576,
    remaining_not_dispatched=7, journal_sha256=helper.sha(cache / "journal.jsonl"),
    journal_tip_sha256=chain[-1]["sha256"], guards=denied,
    original_v3_supplement_sha256=helper.sha(HERE / "INCOMPLETE-RECEIPT-SUPPLEMENT-v3.json"),
    original_evidence_scope="Earlier v3 evidence preserved; this new helper has eight entries and the receipt failure must stop seven later entries.",
    scope="Pure stub only. No HTTP, worker execution, process-tree, native or scientific conformance claim.")
helper.write_new(HERE / "FOLLOWUP-INCOMPLETE-RECEIPT-CHECK.json", report)
print(json.dumps(dict(status=report["status"],actual_rejection=report["actual_rejection"],
    actual_children=0,actual_network_requests=0,remaining_not_dispatched=7)))
