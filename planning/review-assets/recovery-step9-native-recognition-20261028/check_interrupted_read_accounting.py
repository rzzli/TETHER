"""One no-network stub check; never dispatch the fixed source fetcher."""

import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
need_isolated = bool(sys.flags.isolated and sys.dont_write_bytecode)
assert need_isolated
spec = importlib.util.spec_from_file_location("fixed_reference_fetcher_under_test", HERE / "fetch_native_references.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
denied = []


def audit(event, args):
    if event in ("subprocess.Popen", "os.system", "socket.__new__", "socket.connect", "socket.getaddrinfo"):
        denied.append(event)
        raise RuntimeError("No network or process in the accounting fixture")


sys.addaudithook(audit)
output = ROOT / "data/cache" / ("r09-native-source-accounting-fault-" + str(time.time_ns()))
journal = helper.RunJournal(output, kind="build")
(output / "attempts").mkdir()
(output / "sources").mkdir()
calls = []
state = dict(dispatch_attempts=0, spawned_children=0, denied=[], active_argv=None)
expected = "0" * 64


def interrupted_read(entry, cache, protocol_sha, journal, state, deadline):
    calls.append(entry["index"])
    directory = cache / "attempts" / f"{entry['index']:02d}"
    directory.mkdir()
    # Simulate an unreliable child claiming zero retained bytes and no unknown
    # receipt despite an incomplete read. No real process or HTTP call occurs.
    child = dict(**entry, schema_version=1, status="failed_or_incomplete",
                 retained_body_bytes=0, observed_body_bytes_at_least=0,
                 unknown_received=False, error_class="InterruptedError",
                 error="Synthetic read interruption, not a network observation",
                 protocol_sha256=protocol_sha)
    helper.write_new(directory / "child-result.json", child)
    helper.write_new(directory / "stdout.bin", child)
    with (directory / "stderr.bin").open("xb"):
        pass
    return dict(spawned=True, reaped=True, returncode=0, timed_out=False,
                cleanup_errors=[], full_process_elapsed_seconds=0.01,
                effective_seconds=20, streams={
                    "stdout": dict(truncated=False, error_class=None),
                    "stderr": dict(truncated=False, error_class=None),
                })


try:
    records, retained = helper.collect({}, output, expected, journal, state,
                                      time.monotonic() + 300, runner=interrupted_read)
finally:
    journal.close()
assert calls == [0] and retained == 0
assert len(records) == 12
first = records[0]
assert first["status"] == "failed_or_incomplete_unknown_receipt"
assert first["unknown_received"] is True
assert first["source_bytes"] is None and first["source_sha256"] is None
assert first["conservative_body_reservation_bytes"] == 1048576
assert first["reservation_disposition"] == "retained_unknown_not_zero_measured_transfer"
assert all(row["status"] == "not_attempted_after_unknown_receipt" for row in records[1:])
assert denied == [] and state["dispatch_attempts"] == state["spawned_children"] == 0
chain = helper.read_chain(output / "journal.jsonl")
assert chain[-1]["event"] == "source_receipt_unknown_stop"
assert chain[-1]["details"]["unknown_received"] is True
assert chain[-1]["details"]["conservative_body_reservation_bytes"] == 1048576
report = dict(schema_version=1, status="passed_interrupted_zero_retained_unknown_receipt_stop",
    helper_sha256=helper.sha(HERE / "fetch_native_references.py"),
    fixture_sha256=helper.sha(__file__), output=str(output), actual_children=0,
    actual_network_requests=0, simulated_child_reports=1, remaining_not_dispatched=11,
    input_reported_retained_body_bytes=0, parent_unknown_received=True,
    parent_source_bytes=None, retained_conservative_reservation_bytes=1048576,
    actual_known_qualified_source_bytes=retained, guards=denied,
    journal_sha256=helper.sha(output / "journal.jsonl"), journal_tip_sha256=chain[-1]["sha256"],
    scope="Stub accounting/control flow only; zero qualified source bytes is not proof of zero received transfer")
helper.write_new(HERE / "INTERRUPTED-READ-FAULT-CHECK.json", report)
print(json.dumps(dict(status=report["status"], actual_children=0, actual_network_requests=0,
                     remaining_not_dispatched=11, protocol_output_not_consumed=True)))
