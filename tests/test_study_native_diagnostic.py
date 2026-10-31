"""Fixed diagnostic control-flow fixtures; no native process or network."""

import http.client
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from asof.serde import ContractError, canonical
from asof.study import native_diagnostic as diagnostic
from asof.study import native
from asof.study.diagnostic import (
    load_synthetic_request,
    prepare_payload,
    request_from_payload,
)
from tests.test_study_native import Response


def fixture_inputs(root):
    """Entirely invented source/asset files for the real preparation validator."""
    root = Path(root)
    source = root / "input-fixture"
    source.mkdir()
    assets = []
    for name in (
        "llama-server.exe",
        "one-00001-of-00003.gguf",
        "one-00002-of-00003.gguf",
        "one-00003-of-00003.gguf",
        "runtime.dll",
    ):
        path = source / name
        path.write_bytes(b"Fixture data only; never execute or load. " + name.encode())
        assets.append(diagnostic.pin(path))
    inventory = source / "inventory.json"
    inventory.write_bytes(canonical(dict(assets=assets)))
    rows = []
    for case_id, template in zip(
        diagnostic.CASE_IDS,
        ("synthetic-orientation", "synthetic-orientation", "synthetic-context"),
    ):
        request = load_synthetic_request(template)
        req_path = source / (case_id + "-request.json")
        req_path.write_bytes(canonical(request))
        arms = []
        for interface in diagnostic.INTERFACES:
            payload = prepare_payload(request, interface)
            path = source / (case_id + "-" + interface + ".json")
            path.write_bytes(canonical(payload))
            arms.append(dict(http_payload=diagnostic.pin(path)))
        rows.append(
            dict(
                case_id=case_id,
                request=diagnostic.pin(req_path),
                arms=arms,
                basis="synthetic_test_only",
            )
        )
    r05 = source / "paired.json"
    r05.write_bytes(canonical(dict(cases=rows)))
    code = source / "compiler.py"
    code.write_text(
        "raise AssertionError('Code is inert fixture data')\n", encoding="utf-8"
    )
    code_copy = source / "compiler-copy.py"
    code_copy.write_bytes(code.read_bytes())
    gate = source / "source-gate.json"
    request_hash = rows[0]["request"]["sha256"]
    gate.write_bytes(
        canonical(
            dict(
                status="passed",
                all_six_payloads_unchanged=True,
                evaluator_answers_read=False,
                clinical_outcome_contents_read=False,
                expected_request_sha256=request_hash,
                request_sha256=request_hash,
                source_compiler_code_proofs=[diagnostic.pin(code)],
                authoritative_input_proofs=[rows[0]["request"]],
            )
        )
    )
    archive = source / "compiler-archive.json"
    archive.write_bytes(
        canonical(
            dict(
                source_gate=diagnostic.pin(gate),
                archived_code_executed=False,
                files=[
                    dict(
                        original=diagnostic.pin(code), archive=diagnostic.pin(code_copy)
                    )
                ],
            )
        )
    )
    return dict(
        r05_path=r05,
        inventory_path=inventory,
        source_gate_path=gate,
        compiler_archive_path=archive,
        approved_roots=[root],
    )


class NativeDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = fixture_inputs(self.root)

    def prepare(self, name="run"):
        return diagnostic.prepare(self.root / name, **self.inputs)

    def test_preparation_freezes_six_exact_payloads_and_inert_code(self):
        proof = self.prepare()
        plan = json.loads(Path(proof["path"]).read_bytes())
        self.assertEqual(len(plan["cells"]), 6)
        self.assertEqual(plan["argv"][-2:], ["-lv", "4"])
        diagnostic._validate(plan, [self.root])
        self.assertTrue((self.root / "run/source-compiler-data/000.py").is_file())

    def test_existing_output_rejects_before_native_start(self):
        self.prepare()
        with (
            patch.object(diagnostic, "OwnedServer") as server,
            self.assertRaises(FileExistsError),
        ):
            self.prepare()
        server.assert_not_called()

    def test_launch_arguments_and_omitted_assets_fail_before_server(self):
        proof = self.prepare()
        baseline = json.loads(Path(proof["path"]).read_bytes())
        for mutate in (
            lambda p: p["argv"].extend(["--model", "unverified.gguf"]),
            lambda p: p["assets"].pop(),
            lambda p: p.update(alias="other"),
        ):
            plan = json.loads(json.dumps(baseline))
            mutate(plan)
            with self.assertRaises(ContractError):
                diagnostic._validate(plan, [self.root])

    def test_unsafe_input_root_or_changed_source_fails(self):
        args = dict(self.inputs)
        args["approved_roots"] = [self.root / "other"]
        with self.assertRaises(ContractError):
            diagnostic.prepare(self.root / "rejected", **args)
        proof = self.prepare()
        plan = json.loads(Path(proof["path"]).read_bytes())
        Path(plan["source_inputs"][0]["path"]).write_bytes(b"changed")
        with self.assertRaises(ContractError):
            diagnostic._validate(plan, [self.root])

    def test_failed_start_retains_six_undispatched_cells_and_terminal_seal(self):
        proof = self.prepare()
        with patch.object(
            diagnostic, "OwnedServer", side_effect=RuntimeError("Fake startup refusal")
        ):
            seal = diagnostic.execute(proof["path"], proof["sha256"], [self.root])
        result = diagnostic.verify(self.root / "run", seal["sha256"], [self.root])
        self.assertEqual(result["cell_dispatch_reservations"], 0)
        report = json.loads((self.root / "run/execution-report.json").read_bytes())
        self.assertEqual(report["status"], "incomplete_execution")
        self.assertEqual(len(report["cells"]), 6)
        self.assertTrue(all(c["status"] == "undispatched" for c in report["cells"]))

    def test_execution_never_reuses_reserved_output_or_wrong_anchor(self):
        proof = self.prepare()
        with self.assertRaises(ContractError):
            diagnostic.execute(proof["path"], "0" * 64, [self.root])
        with patch.object(
            diagnostic, "OwnedServer", side_effect=RuntimeError("Fake startup refusal")
        ):
            diagnostic.execute(proof["path"], proof["sha256"], [self.root])
        with (
            self.assertRaises(FileExistsError),
            patch.object(diagnostic, "OwnedServer") as server,
        ):
            diagnostic.execute(proof["path"], proof["sha256"], [self.root])
        server.assert_not_called()

    def run_fake_native(self, *, first_malformed=False, first_incomplete=False):
        proof = self.prepare()
        connections = []

        class FakeOwner:
            def __init__(self, spec, *, output, journal, **kwargs):
                self.spec, self.output, self.journal = spec, output, journal
                self._process = SimpleNamespace()
                self.record = dict(started=True, pid=4321, server_stopped=False)

            @property
            def terminal_record(self):
                return dict(self.record)

            def assert_ready(self):
                if self.record["server_stopped"]:
                    raise ContractError("Fake owner stopped")

            def __enter__(self):
                diagnostic.put(self.output / "server-command.json", self.spec)
                (self.output / "server.stderr.log").write_text(
                    "n_slots = 1, n_ctx_slot = 16384\n", encoding="utf-8"
                )
                self.journal.append("server_started", pid=4321)
                self.journal.append("server_ready", pid=4321)
                return self

            def __exit__(self, *args):
                self.record["server_stopped"] = True
                self.journal.append("server_terminal", **self.terminal_record)

        class FakeConnection:
            def __init__(self, *args, **kwargs):
                self.sock = Mock()
                self.index = len(connections)
                connections.append(self)

            def connect(self):
                pass

            def request(self, method, path, *, body, headers):
                self.payload = json.loads(body)

            def getresponse(self):
                if first_incomplete and self.index == 0:
                    raise http.client.IncompleteRead(b"partial native fixture", 5)
                payload = self.payload
                interface = (
                    "simplified"
                    if payload["json_schema"] == {"type": "object"}
                    else "current"
                )
                request = request_from_payload(payload, interface)
                literal = request["source_request"]["evidence"][0]["statement"]
                if interface == "simplified":
                    doc = dict(
                        answer_status="answered",
                        claims=[
                            dict(
                                kind="source_report",
                                text=literal,
                                source_ids=["E0"],
                                quote_pointers=["/statement"],
                                limitations=[],
                            )
                        ],
                        unresolved=[],
                        abstention_reason=None,
                    )
                else:
                    prop = dict(
                        subject="Fixture source",
                        predicate="reports",
                        object="source fact",
                        negation=False,
                        modal="asserted",
                        orientation=None,
                        population=None,
                        tissue=None,
                        intervention=None,
                        comparator=None,
                        outcome=None,
                        timing=None,
                    )
                    doc = dict(
                        answer_status="answered",
                        claims=[
                            dict(
                                claim_id="C1",
                                kind="source_report",
                                text=literal,
                                proposition=prop,
                                quote_refs=[dict(source="E0", pointer="/statement")],
                                limitations=[],
                                applicability="not_assessed",
                            )
                        ],
                        abstention_reason=None,
                    )
                if first_malformed and self.index == 0:
                    doc = {}
                raw = dict(
                    prompt=payload["prompt"],
                    model=diagnostic.ALIAS,
                    generation_settings={
                        k: payload[k]
                        for k in ("seed", "temperature", "n_predict", "stop", "stream")
                    },
                    truncated=False,
                    stop=True,
                    stop_type="eos",
                    stopped_limit=False,
                    stopping_word="",
                    tokens_evaluated=100,
                    tokens_predicted=20,
                    content=canonical(doc).decode(),
                )
                return Response(canonical(raw))

            def close(self):
                pass

        with (
            patch.object(diagnostic, "OwnedServer", FakeOwner),
            patch.object(native.http.client, "HTTPConnection", FakeConnection),
            patch.object(native, "Timer"),
        ):
            seal = diagnostic.execute(proof["path"], proof["sha256"], [self.root])
        verified = diagnostic.verify(self.root / "run", seal["sha256"], [self.root])
        return (
            connections,
            verified,
            json.loads((self.root / "run/execution-report.json").read_bytes()),
        )

    def test_all_six_fake_native_cells_seal_and_replay(self):
        connections, verified, report = self.run_fake_native()
        self.assertEqual(len(connections), 6)
        self.assertEqual(verified["cell_dispatch_reservations"], 6)
        self.assertTrue(report["server"]["server_stopped"])
        self.assertTrue(
            all(
                c["status"] == "contract_verified_not_scientific_validation"
                for c in report["cells"]
            )
        )

    def test_incomplete_transport_is_retained_and_other_declared_cells_run(self):
        connections, verified, report = self.run_fake_native(first_incomplete=True)
        self.assertEqual(len(connections), 6)
        self.assertEqual(verified["cell_dispatch_reservations"], 6)
        self.assertEqual(report["cells"][0]["status"], "failed")
        self.assertEqual(
            report["cells"][0]["inspection"]["measured_usage"]["input_tokens"], 0
        )
        self.assertGreater(
            report["cells"][0]["inspection"]["estimated_usage"]["input_tokens"], 0
        )
        capture = (
            self.root
            / "run/cells"
            / report["cells"][0]["cell_id"]
            / "native-failure-body.bin"
        )
        self.assertEqual(capture.read_bytes(), b"partial native fixture")

    def test_malformed_fake_cell_remains_failed_while_other_declared_cells_run(self):
        connections, verified, report = self.run_fake_native(first_malformed=True)
        self.assertEqual(len(connections), 6)
        self.assertEqual(verified["cell_dispatch_reservations"], 6)
        self.assertEqual(report["cells"][0]["status"], "failed")
        self.assertEqual(
            report["cells"][0]["inspection"]["measured_usage"]["input_tokens"], 100
        )
        self.assertFalse(
            (
                self.root / "run/cells" / report["cells"][0]["cell_id"] / "receipt.json"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
