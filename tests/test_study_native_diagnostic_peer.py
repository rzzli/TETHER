"""Independent parent-seal contradictions with actual prepared fixture validation.

Only server creation is faked. Source/model files are explicitly invented inert
test data; no real source admission, native process or network is performed.
"""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.serde import ContractError, canonical, fingerprint, parse_json
from asof.study import native_diagnostic as diagnostic
from tests import test_study_native_diagnostic as diagnostic_tests
from tests.test_study_native_diagnostic import fixture_inputs


class NativeDiagnosticPeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = fixture_inputs(self.root)
        self.counter = 0

    def prepared(self):
        self.counter += 1
        output = self.root / str(self.counter)
        proof = diagnostic.prepare(output, **self.inputs)
        diagnostic._validate(parse_json(Path(proof["path"]).read_bytes()), [self.root])
        return output, proof

    def failed_start(self):
        output, proof = self.prepared()
        with patch.object(
            diagnostic,
            "OwnedServer",
            side_effect=RuntimeError("explicit fake startup refusal"),
        ):
            seal = diagnostic.execute(proof["path"], proof["sha256"], [self.root])
        result = diagnostic.verify(output, seal["sha256"], [self.root])
        self.assertEqual(result["cell_dispatch_reservations"], 0)
        return output

    def contradict(self, mutation):
        """Refresh byte proofs to exercise semantic reconciliation independently."""
        output = self.failed_start()
        report = parse_json((output / "execution-report.json").read_bytes())
        seal = parse_json((output / "terminal-seal.json").read_bytes())
        events = [
            parse_json(line)
            for line in (output / "execution/journal.jsonl").read_bytes().splitlines()
        ]
        mutation(report, seal, events)
        (output / "execution-report.json").write_bytes(canonical(report) + b"\n")
        events[-1]["details"]["report"] = diagnostic.pin(
            output / "execution-report.json"
        )
        previous = None
        for sequence, event in enumerate(events):
            event.pop("sha256", None)
            event.update(sequence=sequence, previous_sha256=previous)
            event["sha256"] = fingerprint(event)
            previous = event["sha256"]
        (output / "execution/journal.jsonl").write_bytes(
            b"".join(canonical(e) + b"\n" for e in events)
        )
        seal["files"] = {name: diagnostic.pin(output / name) for name in seal["files"]}
        (output / "terminal-seal.json").write_bytes(canonical(seal) + b"\n")
        return output, diagnostic.pin(output / "terminal-seal.json")["sha256"]

    def rejects(self, mutation):
        output, anchor = self.contradict(mutation)
        with self.assertRaises(ContractError):
            diagnostic.verify(output, anchor, [self.root])

    def test_empty_terminal_inventory_cannot_attest_unanchored_report_or_journal(self):
        self.rejects(lambda report, seal, events: seal.update(files={}))

    def test_report_schema_kind_status_and_science_claims_are_checked(self):
        for changes in (
            {"schema_version": 999},
            {"kind": "unrelated"},
            {"status": "scientifically_validated"},
            {"scientific_acceptance": "passed"},
            {"provider_spend_usd": 12},
            {"elapsed_seconds": -1},
        ):
            with self.subTest(changes=changes):
                self.rejects(lambda report, seal, events: report.update(changes))

    def test_terminal_seal_schema_and_role_are_checked(self):
        for changes in (
            {"schema_version": 999},
            {"kind": "unrelated"},
            {"human_scientific_review": "completed"},
        ):
            with self.subTest(changes=changes):
                self.rejects(lambda report, seal, events: seal.update(changes))

    def test_report_plan_must_match_external_plan_anchor(self):
        def mutation(report, seal, events):
            report["plan"]["sha256"] = "0" * 64

        self.rejects(mutation)

    def test_result_case_and_interface_cannot_change_while_cell_id_stays(self):
        for field in ("case_id", "interface"):
            with self.subTest(field=field):
                self.rejects(
                    lambda report, seal, events: report["cells"][0].update(
                        {field: "foreign"}
                    )
                )

    def test_undispatched_cells_cannot_hide_parent_terminal_claims(self):
        def mutation(report, seal, events):
            events.insert(
                -1,
                dict(
                    event="native_cell_terminal",
                    details=dict(report["cells"][0], status="failed"),
                ),
            )

        self.rejects(mutation)

    def test_server_started_claim_requires_ownership_journal_evidence(self):
        def mutation(report, seal, events):
            report["server"] = dict(
                started=True, pid=12345, server_stopped=True, exit_code=0
            )

        self.rejects(mutation)

    def test_failed_start_cannot_be_promoted_to_qualified_terminal(self):
        def mutation(report, seal, events):
            report.update(
                status="technical_terminal_pending_human_review", error_class=None
            )
            report["server"]["server_stopped"] = True

        self.rejects(mutation)

    def test_cell_id_traversal_and_source_omission_fail_real_preflight(self):
        output, proof = self.prepared()
        baseline = parse_json(Path(proof["path"]).read_bytes())
        for mutation in (
            lambda p: p["cells"][0].update(cell_id="../../outside"),
            lambda p: p.update(source_inputs=[]),
        ):
            changed = json.loads(json.dumps(baseline))
            mutation(changed)
            with self.assertRaises(ContractError):
                diagnostic._validate(changed, [self.root])

    def test_archive_proof_omission_and_rebound_bytes_fail_real_preflight(self):
        for field in ("package_archive", "compiler_data_archive"):
            with self.subTest(field=field):
                output, proof = self.prepared()
                baseline = parse_json(Path(proof["path"]).read_bytes())
                missing = json.loads(json.dumps(baseline))
                missing[field] = []
                with self.assertRaises(ContractError):
                    diagnostic._validate(missing, [self.root])
                changed = json.loads(json.dumps(baseline))
                member = Path(changed[field][0]["path"])
                member.write_bytes(b"different inert archived code")
                changed[field][0] = diagnostic.pin(member)
                with self.assertRaises(ContractError):
                    diagnostic._validate(changed, [self.root])

    def test_duplicate_compiler_member_cannot_replace_another_required_file(self):
        gate_path, archive_path = (
            self.inputs["source_gate_path"],
            self.inputs["compiler_archive_path"],
        )
        gate, archive = (
            parse_json(gate_path.read_bytes()),
            parse_json(archive_path.read_bytes()),
        )
        second = gate_path.parent / "second-compiler.py"
        second.write_bytes(b"second required inert compiler file")
        gate["source_compiler_code_proofs"].append(diagnostic.pin(second))
        gate_path.write_bytes(canonical(gate))
        archive["source_gate"] = diagnostic.pin(gate_path)
        archive["files"].append(dict(archive["files"][0]))
        archive_path.write_bytes(canonical(archive))
        with self.assertRaises(ContractError):
            self.prepared()


class NativeDiagnosticBudgetPeerTests(unittest.TestCase):
    """Fake HTTP bodies retain real session accounting and parent verification."""

    setUp = diagnostic_tests.NativeDiagnosticTests.setUp
    prepare = diagnostic_tests.NativeDiagnosticTests.prepare
    run_fake_native = diagnostic_tests.NativeDiagnosticTests.run_fake_native

    def test_last_arm_excess_usage_stops_before_next_case(self):
        original_response = diagnostic_tests.Response
        response_count = 0

        def response(body):
            nonlocal response_count
            response_count += 1
            if response_count == 2:
                value = parse_json(body)
                value["tokens_evaluated"] = 32001
                body = canonical(value)
            return original_response(body)

        with patch.object(diagnostic_tests, "Response", side_effect=response):
            connections, verified, report = self.run_fake_native()
        self.assertEqual(len(connections), 2)
        self.assertEqual(verified["cell_dispatch_reservations"], 2)
        self.assertEqual(report["cells"][1]["status"], "failed")
        self.assertEqual(
            report["cells"][1]["inspection"]["measured_usage"]["input_tokens"],
            32001,
        )
        self.assertTrue(
            all(cell["status"] == "undispatched" for cell in report["cells"][2:])
        )
        self.assertTrue(report["server"]["server_stopped"])


if __name__ == "__main__":
    unittest.main()
