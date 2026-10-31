"""Write new-phase source/pure evidence only; no original/archive/payload reads."""
import datetime
import hashlib
import importlib.util
import io
import json
import pathlib
import sys
import time
import unittest

HERE = pathlib.Path(__file__).parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pin(filename):
    path = HERE / filename
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write_new(filename, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    with (HERE / filename).open("xb") as stream:
        stream.write(raw)
    return pin(filename)


def run_suite(suite):
    output = io.StringIO()
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    return dict(methods=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                elapsed_seconds=time.monotonic() - started, passed=result.wasSuccessful(),
                output=output.getvalue(),
                failures_detail=[dict(test=str(test), traceback=detail) for test, detail in result.failures],
                errors_detail=[dict(test=str(test), traceback=detail) for test, detail in result.errors])


def main():
    checker = load("recovery_checker", "check_deterministic_verifier_v1.py")
    corrected = checker.v
    initial = load("recovery_initial", "deterministic_verifier_initial_draft.py")
    selected = (
        "test_context_immutable_nonserializable_foreign",
        "test_read_late_failed_and_unreturned",
        "test_late_checker_return_and_clock_primary",
        "test_shape_before_output_and_failed_reservations",
        "test_close_false_unknown_late_no_retry",
        "test_hash_fault_and_late_digest",
    )
    checker.v = initial
    before = run_suite(unittest.TestSuite(checker.Checks(name) for name in selected))
    checker.v = corrected
    require = lambda condition: None if condition else (_ for _ in ()).throw(RuntimeError("proof expectation failed"))
    require(not before["passed"] and before["methods"] == len(selected))
    before_record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         status="PRESERVED_INITIAL_DRAFT_DEFECTS_REPRODUCED_SYNTHETIC_ONLY",
                         chronology="Post-review replay executed after corrected draft's first17-method pass; this is not a historically before-fix test run.",
                         source=pin("deterministic_verifier_initial_draft.py"),
                         checker=pin("check_deterministic_verifier_v1.py"), selected_methods=list(selected), result=before,
                         old_original_or_payload_reads=0, SDK_or_native_or_compiler_calls=0,
                         real_profile_or_previous_gate_qualification=False)
    before_pin = write_new("VERIFIER-INITIAL-DRAFT-REGRESSION-REPLAY-v1.json", before_record)
    final = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(checker.Checks))
    require(final["passed"] and final["methods"] == 19)
    proof = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 status="SOURCE_PURE_ORCHESTRATION_TESTS_PASS_INDEPENDENT_REVIEW_PENDING",
                 scope="In-memory fake leases/bytes/sink/clock and trusted synthetic checkers only. No real archive/core checker correctness, live adapter/bootstrap fit, old gate or scientific claim.",
                 source=pin("deterministic_verifier_v1.py"), checker=pin("check_deterministic_verifier_v1.py"),
                 retention_writer=pin(pathlib.Path(__file__).name),
                 approved_contract=pin("VERIFIER-RECOVERY-DESIGN-CONTRACT-v2.json"),
                 source_addendum=pin("VERIFIER-RECOVERY-SOURCE-ADDENDUM-v1.md"), initial_replay=before_pin,
                 result=final,
                 bounds=dict(total_seconds=300, work_seconds=295, reserved_finalization_seconds=5,
                             maximum_files=256, maximum_events=2048, joint_reservation=1728),
                 critical_checks=["first owner clock before trusted factories", "pure output shape before factory and reserve",
                                  "known reservation required for terminal writes", "required typed owner-local gates",
                                  "immutable nonserializable captured bytes", "late returned handle/count retained before checks",
                                  "undefined and unreturned read outcomes remain unknown", "known bytes separate from hash-updated bytes",
                                  "durable bounded finalization and seal reservations", "known failed/uncertain/late close no retry",
                                  "primary preserved across journal/close/clock/veto faults", "no complete before final same-clock gate",
                                  "consistent source negative never profile pass", "joint event and file cap admission before original open"],
                 old_original_or_payload_reads=0, SDK_or_native_or_compiler_calls=0, real_filesystem_adapter=False,
                 author_self_clearance=False, future_integration="Requires separately reviewed source-bound real checker ports, first-clock bootstrap and original-file adapter. No current authorization.")
    proof_pin = write_new("VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v1.json", proof)
    print(json.dumps(dict(initial_replay=before_pin, proof=proof_pin, methods=final["methods"], elapsed_seconds=final["elapsed_seconds"])))


if __name__ == "__main__":
    main()
