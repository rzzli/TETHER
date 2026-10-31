"""Retain synthetic peer failures without importing old writers or archives."""
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).parent


def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    expectations = {
        "captured_journal_v1.py": "5b86f70a57dd1b51d7fe74829b032ddd954f656075ec585c062d5c6dc5e3cf37",
        "check_captured_journal_v1.py": "dc5c7b4d9ff98c9d84f4f117a586bfcd5eb9fff9f134ad62905c830252753856",
        "CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v1.json": "7f87a5bdfc05f4443074e743df6ab5dbb0608b04e0202483bb7478cf8bd06076",
        "CAPTURED-JOURNAL-CONTRACT-v1.json": "2993cf83b8768f2324feb495bae65217d627135f0ce4d20fb341d537893d71ff",
        "CAPTURED-JOURNAL-FIXTURE-FREEZE-v1.json": "cd4f6b3f381a837d790dfcad84e92231111456e3eb6648a0ebd7617c84980140",
        "CAPTURED-JOURNAL-FIXTURES-v1.json": "1448873002dc5350be8ca835254ff283b734d04bda88382273b1c4b4319fe28c",
    }
    artifacts = {name: pin(name) for name in expectations}
    assert all(artifacts[name]["sha256"] == sha for name, sha in expectations.items())
    spec = importlib.util.spec_from_file_location("journal_independent_probes", HERE / "check_captured_journal_peer_v1.py")
    checker = importlib.util.module_from_spec(spec); sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    output = io.StringIO(); started = time.monotonic()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(checker.PeerChecks))
    elapsed = time.monotonic() - started
    assert result.testsRun == 7 and len(result.failures) == 5 and not result.errors
    assert len(checker.FALSE_POSITIVES) == 5
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="HOLD_KNOWN_LAUNCHED_TERMINAL_COMPLETENESS_SOURCE_PURE_ONLY",
        artifacts=artifacts, independent_checker=pin("check_captured_journal_peer_v1.py"),
        recorder=pin(Path(__file__).name),
        methods=result.testsRun, failing_methods=2, assertion_failures=len(result.failures), errors=len(result.errors),
        elapsed_seconds=elapsed, test_output=output.getvalue(), incorrect_acceptances=checker.FALSE_POSITIVES,
        bounded_passes=["All30frozen chain/native-policy fixture expectations reproduced",
                        "Rechained duplicate resume/unknown event/protocol mismatch/bool resume attacks rejected",
                        "Raw Unicode separators preserved; missing LF/BOM/CRLF/blank/duplicate JSON/bool sequence rejected",
                        "Required callback deadline exceptions propagated by identity at early/middle/final checkpoints",
                        "Frozen nested results detached from inputs; no filesystem callback invoked by either API"],
        finding=dict(scope="One known-launched source-terminal completeness family, not byte-chain/raw-resource/profile truth",
                     problem="terminal.complete/EOF flags can override contradictory errors, invalid/missing drain status/poll metadata and a non-EOF terminal availability result.",
                     confirmed=["nonempty terminal.errors", "drain.statusfailed", "polls_reservedTrue", "missing status/polls_reserved",
                                "observed_pipe_EOF with known nonempty calls ending available0 instead ofNone"],
                     EOF_probe="Uses normal observed_pipe_EOF, call.statusreturned, valid contiguouspoll1, correct rechained matching capture_available event and exact updated journal digest. No raw resource truth was inferred.",
                     consequence="The API returns source_order_validatedTrue/statuscomplete_known_launched_native_journal for internally inconsistent terminal bindings. profile_qualified/resource_semantics_validated remainFalse, limiting the false claim but not repairing it.",
                     correction="Version a narrow terminal-projection rule: require empty errors; required source-normal statuses and strict poll counts; alreadyEOF zero calls; observed_pipe_EOF nonempty known calls with final availabilityNone and no earlierNone; retain exact flag/type/call/reference checks. Preserve chain-only/raw-resource/profile boundaries."),
        chain_only_disposition="No material blocker found in this bounded chain-only review; not live qualification or a formal proof of every input.",
        author_proof_disposition="Original9-method/30fixture pass remains preserved as baseline evidence; it did not exercise these five contradictory nested terminal cases.",
        activity=dict(author_source_or_fixture_edits=0, old_archive_replays=0, old_source_closure_or_original_rehashes=0,
                      CPU_GGUF_pack_model_operations=0, SDK_native_target_compiler_calls=0,
                      only_new_pure_component_and_synthetic_fixture_bytes=True),
        current_or_future_profile_qualified=False, previous_negative_and_timeout_unchanged=True)
    raw = (json.dumps(record, indent=2, allow_nan=False) + "\n").encode("utf-8")
    out = HERE / "CAPTURED-JOURNAL-INDEPENDENT-PEER-v1.json"
    with out.open("xb") as stream: stream.write(raw)
    print(json.dumps(pin(out.name)))


if __name__ == "__main__":
    main()
