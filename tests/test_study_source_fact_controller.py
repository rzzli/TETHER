"""Fictional controller controls; never launch, read weights, or contact HTTP."""

import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, nullcontext
from datetime import datetime, timezone
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from tether_engine.journal import RunJournal, read_chain
from tether_engine.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json
from tether_engine.study.source_fact_evaluation import TERMINALS
from tether_engine.study.source_fact_inputs import make_packet
from tether_engine.study.source_fact_reporting import literal_report
from tools.science import run_source_fact_pilot as pilot
from tools.history import read_checkpoint
if __package__:
    from .test_study_source_fact_reporting import packet
else:
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
        self.temp = tempfile.TemporaryDirectory(prefix="fictional-controller-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.output_parent = self.directory / "runs"
        self.output_parent.mkdir()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(pilot, "OUTPUT_PARENT", self.output_parent))
        self.stack.enter_context(patch.object(pilot, "capture_environment", return_value={
            "fictional_environment": True, "dependencies": {"pyarrow": "21.0.0"}}))
        self.protocol = parse_json(read_checkpoint((Path(pilot.ASSETS) / "EXECUTION-PROTOCOL-DRAFT-v1.json").as_posix()))
        # checked_path runs before the mocked stable reader. Supply every code
        # input in an isolated workspace instead of relying on private files in
        # the repository. Archived preparation code is data here, never executed.
        workspace = self.directory / "fixture-workspace"
        for name in pilot.code_inventory():
            raw = (read_checkpoint(name) if name.startswith(pilot.ASSETS)
                   else (pilot.ROOT / name).read_bytes())
            destination = workspace / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        # Acquisition verification is mocked below; only an explicit fictional
        # locator is needed for the unmodified path/existence safety checks.
        acquisition = workspace / self.protocol["model"]["acquisition"]["path"].replace("\\", "/")
        acquisition.parent.mkdir(parents=True, exist_ok=True)
        acquisition.write_bytes(b"fictional acquisition")
        self.stack.enter_context(patch.object(pilot, "ROOT", workspace))
        # Construct a current, explicitly invented controller fixture from the
        # historical shape. Original protocol/proof bytes remain untouched.
        previous_arms = {row['arm'] for row in self.protocol['scheduled_cells']}
        replacements = dict(zip(sorted(previous_arms-set(pilot.ARMS)),
                                sorted(set(pilot.ARMS)-previous_arms)))
        for row in self.protocol['scheduled_cells']:
            prior = row['arm']
            if prior in replacements:
                row['arm'] = replacements[prior]
                row['cell_id'] = row['cell_id'].replace(prior, row['arm'])
        budgets = self.protocol['budgets_per_arm_cell']
        self.protocol['budgets_per_arm_cell'] = {replacements.get(k,k):v for k,v in budgets.items()}
        self.stack.enter_context(patch.object(pilot, 'PINNED_COMPONENTS', {
            **pilot.PINNED_COMPONENTS,
            'scheduled_cells':fingerprint(self.protocol['scheduled_cells']),
            'budgets_per_arm_cell':fingerprint(self.protocol['budgets_per_arm_cell'])}))
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
        self.assertIn("Pinned input bytes differ", result["errors"][0]["error"])
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

    def fictional_admission_fixture(self, stack):
        """Invented111-node metadata; real hashes, journals and admission guards."""
        root = self.directory / "fictional-workspace"
        generation, reference, raw_root = root / "generation", root / "reference", root / "originals"
        assets = "fixture-manifests/"
        (root / assets).mkdir(parents=True)
        for name, value in (("ROOT", root), ("GENERATION_ROOT", generation), ("REFERENCE_ROOT", reference),
                            ("RAW_ROOT", raw_root), ("ASSETS", assets)):
            stack.enter_context(patch.object(pilot, name, value))
        observed = datetime(2000, 1, 1, tzinfo=timezone.utc)
        cutoff = datetime(2001, 1, 1, tzinfo=timezone.utc)
        nodes, proofs, source_nodes = {}, [], []
        identifiers = ["raw-evidence", "raw-hgnc", "raw-target"] + [f"invented-{i:03d}" for i in range(108)]
        for index, sid in enumerate(identifiers):
            dataset = "hgnc_symbols" if sid == "raw-hgnc" else "ot_target" if sid == "raw-target" else "ot_evidence"
            receipt_hash = pilot.digest((sid + "-invented-receipt").encode())
            availability = Availability(None, None, None, None, observed.date(), "public_download_receipt", "Invented fixture only", observed, receipt_hash)
            node = SourceNode(sid, dataset, "25.09", "invented/" + sid + ".json", pilot.digest(sid.encode()),
                "reference" if sid == "raw-hgnc" else "agent_evidence", availability, TemporalClass.CONTEMPORARY,
                "https://example.invalid/" + sid, receipt_path="invented/" + sid + ".receipt.json", receipt_sha256=receipt_hash)
            nodes[sid] = encode(node)
            source_nodes.append(node)
            # Symbolic metadata satisfies the controller's fixed legacy inventory;
            # no source payload of this size is created or opened.
            proofs.append(dict(source_id=sid, bytes=8216226905 - 110 if index == 0 else 1,
                **{key: nodes[sid][key] for key in ("sha256", "dataset_id", "release_id", "path", "receipt_path", "receipt_sha256")}))
        catalog = dict(schema_version=1, datasets=[dict(dataset_id=key, roles=[role]) for key, role in
            (("ot_evidence", "agent_evidence"), ("ot_target", "agent_evidence"), ("hgnc_symbols", "reference"))])
        catalog_path = root / "data/catalog/sources.json"
        catalog_path.parent.mkdir(parents=True)
        catalog_raw = canonical(catalog)
        catalog_path.write_bytes(catalog_raw)
        catalog_hash = pilot.digest(catalog_raw)
        plan = dict(source_policy=dict(catalog_sha256=catalog_hash, primary_families=["identity_linkage", "reported_context"]))
        plan_hash = fingerprint(plan)
        snapshot = Snapshot(2, "invented-controller", Profile.CONTEMPORARY, cutoff.date(), False, (),
            tuple(source_nodes), str(raw_root), {}, cutoff)
        packets, tasks = {}, {}
        for condition in pilot.CONDITIONS:
            case = dict(case_id="invented", target_symbol="CONTROL", indication_id="EFO_CONTROL", action=None, modality=None, tissue=None)
            missing = condition.endswith("controlled-missing")
            condition_spec = dict(id=condition, kind="synthetic_input_withholding" if missing else "real_selected_sources",
                records_available=0, collection_status="incomplete", biological_absence=False)
            resolution = dict(target_id="CONTROL", mappings=[dict(source_id=key, locator=dict(format="json", pointer=""), row={}) for key in ("raw-hgnc", "raw-target")])
            selected = [dict(source_id="raw-evidence", locator=dict(format="parquet", row_group=0, row=7), row=dict(id="invented-record",
                targetId="CONTROL", diseaseId="EFO_CONTROL", datasourceId="europepmc", datatypeId="literature", publicationDate="2000-01-01", cellType=None))]
            packets[condition] = make_packet(case, condition_spec, resolution, selected, nodes, proofs, cutoff=cutoff.isoformat(), plan_sha256=plan_hash)
            tasks[condition] = packets[condition]["neutral_task"]
        inventory = dict(role="agent_evidence", agent_visible=True, reference_inputs=[], plan_sha256=plan_hash,
            source_snapshot=encode(snapshot), inventory_proofs=proofs)
        payloads = {condition + suffix: canonical(packets[condition] if suffix == ".packet.json" else tasks[condition])
                    for condition in pilot.CONDITIONS for suffix in (".packet.json", ".task.json")}
        payloads.update({"source-inventory.json": canonical(inventory), "preparation-summary.json": canonical(dict(evaluator_artifacts_read=False, reference_inputs=[], blocked_cases={}))})
        protocol = copy.deepcopy(self.protocol)
        seals = {}
        for phase, directory in (("source", generation), ("reference", reference)):
            with_journal = RunJournal(directory, kind="build")
            if phase == "source":
                for name, raw in payloads.items(): (directory / name).write_bytes(raw)
                seal = dict(model_calls=0, phase="generation_inputs_sealed_before_evaluator_reference_creation", reference_inputs=[], generation_authority=False,
                    plan_sha256=plan_hash, files={name: dict(sha256=pilot.digest(raw), bytes=len(raw)) for name, raw in payloads.items()})
            else:
                (directory / "never-read-evaluator.json").write_bytes(b'{"invented_evaluator_only":true}')
                seal = dict(model_calls=0, phase="source_only_evaluator_references_sealed_before_model_calls", role="evaluation_only", agent_visible=False,
                    generation_seal_sha256=seals["generation_seal_sha256"], reference_count=3, source_inclusive_replays_per_reference=1)
            seal_raw = canonical(seal)
            (directory / "SEAL.json").write_bytes(seal_raw)
            seals["generation_seal_sha256" if phase == "source" else "reference_seal_sha256"] = pilot.digest(seal_raw)
            with_journal.append("build_completed", seal_sha256=pilot.digest(seal_raw))
            with_journal.close()
            protocol[phase + "_journal_sha256"] = pilot.digest((directory / "journal.jsonl").read_bytes())
            protocol[phase + "_journal_terminal_sha256"] = read_chain(directory / "journal.jsonl")[-1]["sha256"]
        conditions = {key: dict(task_sha256=fingerprint(tasks[key]), reference_sha256=pilot.digest(("invented-ref-" + key).encode()), fact_slots=len(packets[key]["fact_skeleton"])) for key in pilot.CONDITIONS}
        manifests = dict(generation_manifest=dict(status="sealed_source_inputs", role="agent_evidence", agent_visible=True, blocked_cases={}, reference_inputs=[],
            evaluator_artifacts_read=False, generation_authority=False, model_calls=0, original_value_output=generation.relative_to(root).as_posix(),
            catalog_sha256=catalog_hash, cutoff=cutoff.isoformat(), plan_sha256=plan_hash, inventory=dict(source_bytes=8216226905), conditions=conditions),
            reference_manifest=dict(status="sealed_source_only_references", role="evaluation_only", agent_visible=False, output=reference.relative_to(root).as_posix(),
                pins=dict(approved_raw_root=str(raw_root), catalog_sha256=catalog_hash), conditions=conditions), input_plan=plan)
        manifest_pins = {}
        for key, document in manifests.items():
            name, raw = key + ".json", canonical(document)
            (root / assets / name).write_bytes(raw)
            manifest_pins[key] = (name, pilot.digest(raw), len(raw))
            protocol[key] = dict(path=assets + name, sha256=pilot.digest(raw), bytes=len(raw))
        protocol.update(seals, roots=dict(workspace=str(root), approved_raw_root=str(raw_root), generation=str(generation), reference=str(reference), output_parent=str(pilot.OUTPUT_PARENT)),
            code_bundle={name: dict(sha256="0" * 64, bytes=0) for name in pilot.code_inventory()})
        for cell in protocol["scheduled_cells"]:
            cell.update({key: conditions[cell["condition"]][key] for key in ("task_sha256", "reference_sha256")})
        for name, value in (("MANIFEST_PINS", manifest_pins), ("SEALS", seals), ("PINNED_COMPONENTS", {key: fingerprint(protocol[key]) for key in pilot.PINNED_COMPONENTS})):
            stack.enter_context(patch.object(pilot, name, value))
        raw = canonical(protocol)
        return pilot.validate_protocol(raw, pilot.digest(raw)), root, reference, catalog_path

    def test_real_sealed_admission_metadata_and_source_only_boundary(self):
        with ExitStack() as stack:
            protocol, root, reference, catalog_path = self.fictional_admission_fixture(stack)
            opened = []
            original_read = pilot.read_file
            def track(path, *args, **kwargs):
                opened.append(Path(path))
                return original_read(path, *args, **kwargs)
            output = self.directory / "fictional-sealed-admission"
            output.mkdir()
            with patch.object(pilot, "_verified_bytes", REAL_VERIFIED_BYTES), patch.object(pilot, "read_file", side_effect=track):
                admitted = REAL_ADMIT_INPUTS(protocol, output, time.monotonic() + 30)
            self.assertEqual(set(admitted["packets"]), set(pilot.CONDITIONS))
            self.assertTrue(all(path.is_relative_to(root) for path in opened))
            self.assertEqual({path.name for path in opened if path.parent == reference}, {"SEAL.json", "journal.jsonl"})
            self.assertEqual(FakeServer.entered, [])
            self.popen.assert_not_called()
            self.http.assert_not_called()
            wrong = dict(protocol, generation_seal_sha256="f" * 64)
            for name, candidate, message in (("denied-seal", wrong, "seal hash differs"), ("denied-catalog", protocol, "catalog pin differs")):
                if name == "denied-catalog": catalog_path.write_bytes(b'{"fictional_catalog_changed":true}')
                denied = self.directory / name
                denied.mkdir()
                with patch.object(pilot, "_verified_bytes", REAL_VERIFIED_BYTES), self.assertRaisesRegex(ContractError, message):
                    REAL_ADMIT_INPUTS(candidate, denied, time.monotonic() + 30)

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
