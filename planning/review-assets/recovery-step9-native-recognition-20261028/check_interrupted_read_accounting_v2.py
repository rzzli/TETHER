"""Two fixed no-network fixtures; no fetch, subprocess or actual source data."""

import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
assert sys.flags.isolated and sys.dont_write_bytecode
spec = importlib.util.spec_from_file_location("fixed_reference_fetcher_v2_under_test", HERE / "fetch_native_references_v2.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
denied = []


def audit(event, args):
    if event in ("subprocess.Popen", "os.system", "socket.__new__", "socket.connect", "socket.getaddrinfo"):
        denied.append(event)
        raise RuntimeError("No network or child in accounting fixtures")


sys.addaudithook(audit)
output = ROOT / "data/cache" / ("r09-native-source-accounting-fault-v2-" + str(time.time_ns()))
output.mkdir(exist_ok=False)
results = []
for scenario in ("interrupted_read_zero_retained", "completed_child_parent_interrupt"):
    cache = output / scenario
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
        child = dict(**entry, schema_version=1, status="failed_or_incomplete",
            retained_body_bytes=0, observed_body_bytes_at_least=0, unknown_received=False,
            error_class="InterruptedError", error="Synthetic read interruption",
            protocol_sha256=protocol_sha)
        attempt = dict(spawned=True, reaped=True, returncode=0, timed_out=False,
            cleanup_errors=[], full_process_elapsed_seconds=0.01, effective_seconds=20,
            streams={"stdout": dict(truncated=False,error_class=None),
                     "stderr": dict(truncated=False,error_class=None)})
        if scenario == "completed_child_parent_interrupt":
            # An otherwise successful source/capture/exit must still be rejected.
            target = cache / "sources" / entry["path"]
            target.parent.mkdir(parents=True)
            target.write_bytes(b"Synthetic fixture text only.\n")
            child.update(status="retained_utf8_text",unknown_received=False,
                source_path=str(target),source_bytes=target.stat().st_size,
                source_sha256=helper.sha(target),retained_body_bytes=target.stat().st_size)
            child.pop("error_class");child.pop("error")
            attempt.update(error_class="KeyboardInterrupt",interrupted=True)
        helper.write_new(directory / "child-result.json", child)
        helper.write_new(directory / "stdout.bin", child)
        with (directory / "stderr.bin").open("xb"):
            pass
        return attempt

    try:
        records, retained = helper.collect({},cache,expected,journal,state,
                                          time.monotonic()+300,runner=runner)
    finally:
        journal.close()
    assert calls == [0] and retained == 0 and len(records) == 12
    first = records[0]
    assert first["status"] == "failed_or_incomplete_unknown_receipt"
    assert first["unknown_received"] is True
    assert first["source_bytes"] is None and first["source_sha256"] is None
    assert first["conservative_body_reservation_bytes"] == 1048576
    assert first["reservation_disposition"] == "retained_unknown_not_zero_measured_transfer"
    assert all(row["status"] == "not_attempted_after_unknown_receipt" for row in records[1:])
    assert state["dispatch_attempts"] == state["spawned_children"] == 0
    chain = helper.read_chain(cache / "journal.jsonl")
    assert chain[-1]["event"] == "source_receipt_unknown_stop"
    assert chain[-1]["details"]["unknown_received"] is True
    results.append(dict(scenario=scenario,status="passed",simulated_child_reports=1,
        actual_children=0,actual_network_requests=0,remaining_not_dispatched=11,
        parent_unknown_received=True,parent_source_bytes=None,
        conservative_reservation_retained=1048576,journal_sha256=helper.sha(cache/"journal.jsonl"),
        journal_tip_sha256=chain[-1]["sha256"]))
assert denied == []
report = dict(schema_version=1,status="passed_unknown_receipt_and_parent_interrupt_stops",
    helper_sha256=helper.sha(HERE/"fetch_native_references_v2.py"),
    fixture_sha256=helper.sha(__file__),actual_children=0,actual_network_requests=0,
    output=str(output),cases=results,guards=denied,
    scope="No-network stubs only; zero qualified bytes never proves zero transfer")
helper.write_new(HERE/"INTERRUPTED-READ-FAULT-CHECK-v2.json",report)
print(json.dumps(dict(status=report["status"],cases=2,actual_children=0,actual_network_requests=0,
                     acquisition_output_not_consumed=True)))
