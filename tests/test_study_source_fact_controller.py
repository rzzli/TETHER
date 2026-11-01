"""Fictional controller controls; never launch, read weights, or contact HTTP."""

import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, nullcontext
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, parse_json
from asof.study.source_fact_evaluation import TERMINALS
from asof.study.source_fact_reporting import literal_report
from tools.science import run_source_fact_pilot as pilot
from test_study_source_fact_reporting import packet


class FakeServer:
    entered = []
    fail_start = False
    fail_cleanup = False

    def __init__(self, spec, **kwargs):
        self.spec, self.kwargs = spec, kwargs
        self.record = dict(started=False, server_stopped=None)
        type(self).entered.append(self)

    @property
    def terminal_record(self):
        return self.record

    def __enter__(self):
        self.record["started"] = True
        if self.fail_start:
            self.record["server_stopped"] = True
            raise TimeoutError("fictional startup failure, retained handle cleaned")
        return self

    def __exit__(self, *args):
        self.record["server_stopped"] = not self.fail_cleanup
        if self.fail_cleanup:
            raise OSError("fictional owned cleanup failure")


class PilotControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-controller-", dir=pilot.ROOT / "data/cache")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.output_parent = self.directory / "runs"
        self.output_parent.mkdir()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(pilot, "OUTPUT_PARENT", self.output_parent))
        self.protocol = parse_json((pilot.ROOT / pilot.ASSETS / "EXECUTION-PROTOCOL-DRAFT-v1.json").read_bytes())
        self.protocol.update(status="READY", evaluation_seconds=3600,
            roots=dict(workspace=str(pilot.ROOT), approved_raw_root=str(pilot.RAW_ROOT),
                       generation=str(pilot.GENERATION_ROOT), reference=str(pilot.REFERENCE_ROOT),
                       output_parent=str(self.output_parent)), environment=pilot.capture_environment(),
            code_bundle={name: dict(sha256="0" * 64, bytes=0) for name in pilot.code_inventory()})
        for phase in ("source", "reference"):
            self.protocol[phase + "_journal_sha256"] = "1" * 64
            self.protocol[phase + "_journal_terminal_sha256"] = "2" * 64
        self.path = self.directory / "protocol.json"
        self.records = []
        self.source = packet()
        self.admitted = dict(packets={condition: self.source for condition in pilot.CONDITIONS},
                             preparation=dict(fictional=True), reference=dict(resources=dict(fictional=True)))
        self.verify_code = self.stack.enter_context(patch.object(pilot, "_verify_code_environment"))
        self.admit = self.stack.enter_context(patch.object(pilot, "_admit_inputs", return_value=self.admitted))
        self.stack.enter_context(patch.object(pilot, "_verified_bytes", return_value=b"fictional acquisition"))
        self.stack.enter_context(patch.object(pilot, "stable_files", side_effect=lambda *args, **kwargs: nullcontext()))
        self.evaluate = self.stack.enter_context(patch.object(pilot, "_evaluate", side_effect=self.fake_evaluate))
        self.popen = self.stack.enter_context(patch.object(pilot.subprocess, "Popen", side_effect=AssertionError("No real process")))
        self.http = self.stack.enter_context(patch.object(pilot.urllib.request, "build_opener", side_effect=AssertionError("No HTTP")))
        FakeServer.entered, FakeServer.fail_start, FakeServer.fail_cleanup = [], False, False

    def freeze(self):
        raw = canonical(self.protocol)
        self.path.write_bytes(raw)
        return pilot.digest(raw)

    def fake_cell(self, source, arm, *, cell_id, output, journal, client_factory, budget):
        self.records.append(cell_id)
        output.mkdir()
        raw = literal_report(source, always_abstain=arm == "always_abstain")
        pilot.write_bytes(output / "final-response.bin", raw)
        result = dict(raw_final=raw, terminal="returned", reason=None, dispatches=0,
                      measured_usage=dict(pilot.ZERO), estimated_usage=dict(pilot.ZERO),
                      stage_records=[], elapsed_seconds=0.01)
        journal.append("cell_terminal", cell_id=cell_id, arm=arm,
                       **{key: value for key, value in result.items() if key != "raw_final"})
        self.assertEqual(budget.max_seconds, 300)
        self.assertEqual(budget.max_retries, 0)
        return result

    def fake_evaluate(self, protocol, admitted, cells, output, journal):
        events = read_chain(journal.path)
        self.assertEqual(events[-1]["event"], "generation_ceased")
        if FakeServer.entered:
            self.assertIs(FakeServer.entered[-1].record["server_stopped"], True)
        self.assertEqual(set(cells), {cell["cell_id"] for cell in protocol["scheduled_cells"]})
        return dict(planned_cells=12, fixture_scoring_only=True), dict(fictional=True)

    def run_pilot(self, name="pilot", **kwargs):
        return pilot.run_pilot(self.path, self.freeze(), self.output_parent / name, execute=True,
                               server_factory=FakeServer, cell_runner=kwargs.pop("cell_runner", self.fake_cell), **kwargs)

    def test_draft_independent_hash_and_exact_model_schedule_caps_deny_before_launch(self):
        changes = [lambda p: p.update(status="DRAFT_NOT_EXECUTABLE"),
                   lambda p: p.update(schema_version=True), lambda p: p.update(seed=False),
                   lambda p: p["model"]["weights"][0].update(sha256="f" * 64),
                   lambda p: p["model"]["runtime_files"].pop(),
                   lambda p: p["scheduled_cells"].pop(),
                   lambda p: p["scheduled_cells"][0].update(arm="unknown_arm"),
                   lambda p: p["budgets_per_arm_cell"].update(max_calls=17),
                   lambda p: p["roots"].update(approved_raw_root="D:\\unexpected")]
        original = copy.deepcopy(self.protocol)
        for index, change in enumerate(changes):
            self.protocol = copy.deepcopy(original)
            change(self.protocol)
            with self.subTest(index=index), self.assertRaises(ContractError):
                self.run_pilot("denied-" + str(index))
        self.protocol = original
        self.freeze()
        with self.assertRaisesRegex(ContractError, "Protocol hash differs"):
            pilot.run_pilot(self.path, "f" * 64, self.output_parent / "hash", execute=True)
        self.assertEqual(FakeServer.entered, [])
        self.assertEqual(list(self.output_parent.iterdir()), [])
        self.popen.assert_not_called()

    def test_execute_flag_required_and_cli_validation_never_reserves(self):
        pin = self.freeze()
        with self.assertRaisesRegex(ContractError, "explicit --execute"):
            pilot.run_pilot(self.path, pin, self.output_parent / "absent")
        self.assertEqual(pilot.main(["--protocol", str(self.path), "--protocol-sha256", pin,
                                   "--output", str(self.output_parent / "absent")]), 0)
        self.assertFalse((self.output_parent / "absent").exists())

    def test_code_hash_denial_reserves_complete_schedule_but_no_launch(self):
        self.verify_code.side_effect = lambda *args: pilot._verify_code_environment_original(*args)
        with patch.object(pilot, "_verify_code_environment_original", self.real_code_verifier(), create=True), \
                patch.object(pilot, "_verified_bytes", REAL_VERIFIED_BYTES):
            result = self.run_pilot()
        self.assertEqual(result["status"], "partial_or_failed")
        self.assertEqual(result["terminal_counts"]["unexecuted"], 12)
        self.assertEqual(result["errors"][0]["stage"], "code_environment")
        self.admit.assert_not_called()
        self.assertEqual(FakeServer.entered, [])

    @staticmethod
    def real_code_verifier():
        # The implementation function is retained before setUp installs its mock.
        return REAL_CODE_VERIFIER

    def test_source_role_denial_happens_before_any_cell_or_launch(self):
        def reject(*args):
            pilot._admit_source_packets({}, {}, {}, {}, dict(role="evaluation_only"), {})
        self.admit.side_effect = reject
        result = self.run_pilot()
        self.assertEqual(result["status"], "partial_or_failed")
        self.assertEqual(result["terminal_counts"]["unexecuted"], 12)
        self.assertEqual(self.records, [])
        self.assertEqual(FakeServer.entered, [])
        self.evaluate.assert_not_called()

    def test_real_sealed_admission_metadata_and_source_only_boundary(self):
        # Only the eight generation files and reference SEAL/journal metadata are
        # read. No evaluator member, raw source, weight, or HTTP request is used.
        for phase, directory in (("source", pilot.GENERATION_ROOT), ("reference", pilot.REFERENCE_ROOT)):
            raw = (directory / "journal.jsonl").read_bytes()
            self.protocol[phase + "_journal_sha256"] = pilot.digest(raw)
            self.protocol[phase + "_journal_terminal_sha256"] = read_chain(directory / "journal.jsonl")[-1]["sha256"]
        raw = canonical(self.protocol)
        protocol = pilot.validate_protocol(raw, pilot.digest(raw))
        output = self.directory / "real-sealed-admission"
        output.mkdir()
        opened = []
        original_read = pilot.read_file
        def track(path, *args, **kwargs):
            opened.append(Path(path))
            return original_read(path, *args, **kwargs)
        with patch.object(pilot, "_verified_bytes", REAL_VERIFIED_BYTES), \
                patch.object(pilot, "read_file", side_effect=track):
            admitted = REAL_ADMIT_INPUTS(protocol, output, time.monotonic() + 30)
        self.assertEqual(set(admitted["packets"]), set(pilot.CONDITIONS))
        private_reads = [path.name for path in opened if path.parent == pilot.REFERENCE_ROOT]
        self.assertEqual(set(private_reads), {"SEAL.json", "journal.jsonl"})
        self.assertEqual(FakeServer.entered, [])
        self.popen.assert_not_called()
        self.http.assert_not_called()

        # A hash change in the immutable source seal cannot enter generation.
        wrong = dict(protocol)
        wrong["generation_seal_sha256"] = "f" * 64
        denied_output = self.directory / "denied-real-seal"
        denied_output.mkdir()
        with patch.object(pilot, "_verified_bytes", REAL_VERIFIED_BYTES), self.assertRaises(ContractError):
            REAL_ADMIT_INPUTS(wrong, denied_output, time.monotonic() + 30)

    def test_startup_failure_preserves_six_controls_and_all_six_model_cells(self):
        FakeServer.fail_start = True
        result = self.run_pilot()
        self.assertEqual(result["status"], "partial_or_failed")
        self.assertEqual(result["planned_cells"], 12)
        self.assertEqual(result["terminal_counts"]["returned"], 6)
        self.assertEqual(result["terminal_counts"]["unexecuted"], 6)
        self.assertEqual(set(result["terminal_counts"]), set(TERMINALS))
        self.assertEqual(len(result["cells"]), 12)
        self.assertEqual(len(self.records), 6)
        self.assertTrue(result["server"]["server_stopped"])
        self.evaluate.assert_called_once()
        self.assertIsNone(result["final_probability_features"])
        self.assertIsInstance(canonical(result), bytes)

    def test_success_has_exact_counterbalanced_order_and_verifiable_receipt(self):
        result = self.run_pilot()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.records, [cell["cell_id"] for cell in self.protocol["scheduled_cells"]])
        output = self.output_parent / "pilot"
        self.assertEqual((output / "protocol.json").read_bytes(), self.path.read_bytes())
        receipt = parse_json((output / "receipt.json").read_bytes())
        self.assertEqual(receipt["report"]["sha256"], pilot.digest((output / "report.json").read_bytes()))
        self.assertEqual(receipt["journal_sha256"], pilot.digest((output / "journal.jsonl").read_bytes()))
        self.assertEqual(result["actual_calls"], 0)
        self.assertTrue(result["server"]["server_stopped"])
        self.popen.assert_not_called()
        self.http.assert_not_called()

    def test_interruption_stops_dependent_cells_retains_accounting_and_cleans(self):
        def interrupted(source, arm, **kwargs):
            if kwargs["cell_id"] == self.protocol["scheduled_cells"][7]["cell_id"]:
                kwargs["journal"].append("cell_terminal", cell_id=kwargs["cell_id"], arm=arm,
                    terminal="interrupted", reason="fictional", dispatches=1,
                    measured_usage=dict(input_tokens=7, output_tokens=9, cost_usd=0),
                    estimated_usage=dict(pilot.ZERO), stage_records=[], elapsed_seconds=0.2)
                raise KeyboardInterrupt("fictional bounded interruption")
            return self.fake_cell(source, arm, **kwargs)
        result = self.run_pilot(cell_runner=interrupted)
        self.assertEqual(result["terminal_counts"]["returned"], 7)
        self.assertEqual(result["terminal_counts"]["interrupted"], 1)
        self.assertEqual(result["terminal_counts"]["unexecuted"], 4)
        self.assertEqual(result["actual_calls"], 1)
        self.assertEqual(result["measured_usage"]["input_tokens"], 7)
        self.assertTrue(result["server"]["server_stopped"])
        self.assertTrue((self.output_parent / "pilot/receipt.json").exists())

    def test_cleanup_failure_is_partial_after_cleanup_and_never_silent_success(self):
        FakeServer.fail_cleanup = True
        result = self.run_pilot()
        self.assertEqual(result["status"], "partial_or_failed")
        self.assertFalse(result["server"]["server_stopped"])
        self.assertEqual(result["terminal_counts"]["returned"], 12)
        self.assertTrue(any("cleanup" in item["error"] for item in result["errors"]))
        self.evaluate.assert_not_called()
        self.assertIsNone(result["scores"])

    def test_report_write_failure_leaves_terminal_journal_and_failure_receipt(self):
        original = pilot.write_bytes
        def fail_report(path, raw):
            if Path(path).name == "report.json":
                raise OSError("fictional disk publication failure")
            return original(path, raw)
        with patch.object(pilot, "write_bytes", side_effect=fail_report):
            result = self.run_pilot()
        self.assertEqual(result["status"], "partial_or_failed")
        output = self.output_parent / "pilot"
        events = read_chain(output / "journal.jsonl")
        self.assertEqual(events[-1]["event"], "run_failed")
        self.assertFalse((output / "receipt.json").exists())
        receipt = parse_json((output / "failure-receipt.json").read_bytes())
        self.assertEqual(sum(receipt["terminal_counts"].values()), 12)

    def test_atomic_output_reservation_denies_concurrent_owner(self):
        entered, release = threading.Event(), threading.Event()
        def pause(*args):
            entered.set()
            self.assertTrue(release.wait(5))
        self.verify_code.side_effect = pause
        pin = self.freeze()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(pilot.run_pilot, self.path, pin, self.output_parent / "contended",
                                 execute=True, server_factory=FakeServer, cell_runner=self.fake_cell)
            self.assertTrue(entered.wait(5))
            try:
                with self.assertRaises(FileExistsError):
                    pilot.run_pilot(self.path, pin, self.output_parent / "contended", execute=True,
                                    server_factory=FakeServer, cell_runner=self.fake_cell)
            finally:
                release.set()
            result = future.result(timeout=10)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(FakeServer.entered), 1)

    def test_netstat_callback_requires_retained_live_pid_and_retains_bounded_evidence(self):
        journal = RunJournal(self.directory / "ownership-run")
        self.addCleanup(journal.close)
        evidence = pilot.ListenerEvidence(journal.output / "ownership", journal, time.monotonic() + 5)
        evidence.process = SimpleNamespace(pid=1234, poll=lambda: None)
        raw = b"  TCP    127.0.0.1:55591    0.0.0.0:0    LISTENING    1234\r\n"
        with patch.object(pilot.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=raw, stderr=b"")) as run:
            self.assertTrue(evidence.owner(1234, "127.0.0.1", 55591))
        self.assertEqual(run.call_args.args[0], ["netstat", "-ano", "-p", "tcp"])
        self.assertEqual(run.call_args.kwargs["timeout"], 2)
        snapshot = journal.events[-1]
        self.assertEqual(snapshot["event"], "listener_snapshot")
        self.assertEqual(snapshot["details"]["stdout_sha256"], pilot.digest(raw))
        self.assertEqual((journal.output / snapshot["details"]["retained"]["path"]).read_bytes(), raw)
        evidence.ready = True
        with patch.object(pilot.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"", stderr=b"")), \
                self.assertRaisesRegex(ContractError, "disappeared"):
            evidence.owner(1234, "127.0.0.1", 55591)
        evidence.process = SimpleNamespace(pid=1234, poll=lambda: 1)
        with patch.object(pilot.subprocess, "run") as run, self.assertRaisesRegex(ContractError, "not live"):
            evidence.owner(1234, "127.0.0.1", 55591)
        run.assert_not_called()

    def test_netstat_interruption_survives_secondary_diagnostic_failure(self):
        journal = RunJournal(self.directory / "ownership-interrupted")
        self.addCleanup(journal.close)
        evidence = pilot.ListenerEvidence(journal.output / "ownership", journal, time.monotonic() + 5)
        evidence.process = SimpleNamespace(pid=1234, poll=lambda: None)
        interrupted = KeyboardInterrupt("fictional netstat interruption")
        with patch.object(pilot.subprocess, "run", side_effect=interrupted), \
                patch.object(pilot, "write_bytes", side_effect=OSError("fictional diagnostic failure")), \
                self.assertRaises(KeyboardInterrupt) as caught:
            evidence.owner(1234, "127.0.0.1", 55591)
        self.assertIs(caught.exception, interrupted)
        self.assertIn("OSError", interrupted.__notes__[0])


REAL_CODE_VERIFIER = pilot._verify_code_environment
REAL_VERIFIED_BYTES = pilot._verified_bytes
REAL_ADMIT_INPUTS = pilot._admit_inputs


if __name__ == "__main__":
    unittest.main()
