"""Fictional-only P05 experiment qualification; never open native values/gold."""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import inspect
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("p05_experiment", ROOT / "tools/science/run_source_validation_experiment.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = ROOT / "data/cache"
        cache.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="p05-experiment-fictional-", dir=cache)
        cls.work = Path(cls.temporary.name)
        cls.fixture_root = cls.work / "fixtures"
        cls.manifest = b.author_fictional_fixtures(cls.fixture_root)
        cls.output = cls.work / "qualification"
        cls.output.mkdir()
        cls.bounds = b.Bounds(cls.output, seconds=300)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def documents(self, key):
        return b.load_fictional(self.fixture_root, key, self.manifest, self.bounds)

    def evaluate(self, key):
        scenario, packet = self.documents(key)
        raw = b.fictional_candidate(packet, key)
        return scenario, packet, raw, b.evaluate_fictional(scenario, packet, raw, self.bounds, approved_fixture_root=self.fixture_root)

    def test_schedule_explicit_38_outputs_90_paired_decisions(self):
        schedule = b.schedule()
        self.assertEqual(len(schedule["output_cells"]), 38)
        self.assertEqual(len(schedule["decision_cells"]), 90)
        self.assertEqual(len({x["cell_id"] for x in schedule["output_cells"]}), 38)
        self.assertEqual(len({x["decision_id"] for x in schedule["decision_cells"]}), 90)
        self.assertEqual({x["output_cell_id"] for x in schedule["decision_cells"]}, {x["cell_id"] for x in schedule["output_cells"]})
        declared = b.parse_json(b.PLAN_PATH.read_bytes())["schedule"]
        self.assertEqual([x["cell_id"] for x in schedule["output_cells"]], [x["cell_id"] for x in declared["output_cells"]])
        self.assertEqual([x["decision_id"] for x in schedule["decision_cells"]], [x["decision_id"] for x in declared["decision_cells"]])

    def test_fixture_authoring_creates_no_candidate_or_result(self):
        self.assertFalse(self.manifest["candidate_outputs_created"])
        self.assertEqual(set(self.manifest["scenarios"]), set(b.SCENARIOS))
        self.assertFalse(any(x.name in ("ledger.json", "references.json") or x.parent.name == "raw" for x in self.fixture_root.rglob("*")))
        self.assertEqual(self.manifest["code_sha256"], b.code_pins())
        self.assertFalse(self.documents("C02")[0]["fixture_is_native_P05_build"])

    def test_all_fourteen_actual_guard_paths_against_hand_declared_oracle(self):
        oracle = b.fictional_oracle()["rows"]
        for key in b.SCENARIOS:
            with self.subTest(scenario=key):
                _, _, _, result = self.evaluate(key)
                self.assertEqual({x["policy"]: x["verdict"] for x in result["decisions"]}, oracle[key]["expected_by_policy"])
                full = result["decisions"][0]
                self.assertEqual(full["first_failure_stage"], oracle[key]["first_full_failure"])
                self.assertEqual(result["scientific_validation"], "not_established")

    def test_C01_independently_written_native_values_and_types(self):
        _, _, raw, result = self.evaluate("C01")
        output = b.parse_json(raw)
        actual = {x["source"]["field"]: x for x in output["facts"]}
        expected = {"beta": (1.25, float), "standardError": (0.25, float), "pValueMantissa": (2.0, float), "pValueExponent": (-6, int)}
        for name, (value, kind) in expected.items():
            self.assertEqual(actual[name]["value"], value)
            self.assertIs(type(actual[name]["value"]), kind)
            self.assertIsNone(actual[name]["unknown_reason"])
            self.assertIsNone(actual[name]["unit"])
        self.assertEqual(result["primary_coverage"], 1.0)
        self.assertTrue(result["measurement_completion"])

    def test_C02_null_empty_and_absent_are_distinct_core_controls(self):
        _, _, raw, result = self.evaluate("C02")
        actual = {x["source"]["field"]: x for x in b.parse_json(raw)["facts"]}
        self.assertEqual(actual["beta"]["unknown_reason"], "null_source_value")
        self.assertEqual(actual["standardError"]["unknown_reason"], "field_not_in_schema")
        self.assertEqual(actual["pValueMantissa"]["unknown_reason"], "empty_source_value")
        self.assertEqual(result["reference_counts"]["measurement_answerable_facts"], 1)
        self.assertTrue(result["measurement_completion"])

    def test_C03_all_physical_matches_and_unqualified_negative_SE_retained(self):
        _, _, raw, result = self.evaluate("C03")
        facts = b.parse_json(raw)["facts"]
        self.assertEqual(len(facts), 22)
        self.assertEqual([x["value"] for x in facts if x["source"]["field"] == "standardError"], [0.25, -0.5])
        self.assertEqual(result["reference_counts"]["measurement_answerable_groups"], 2)
        self.assertEqual(result["decisions"][0]["verdict"], "admitted")
        self.assertEqual(result["scientific_validation"], "not_established")

    def test_C04_exact_source_report_admitted_with_null_measurement_completion(self):
        _, _, _, result = self.evaluate("C04")
        self.assertEqual(result["decisions"][0]["verdict"], "admitted")
        self.assertIsNone(result["primary_coverage"])
        self.assertFalse(result["measurement_completion"])
        self.assertEqual(result["reference_counts"]["measurement_answerable_facts"], 0)

    def test_unknown_omission_is_not_exact_even_when_core_completion_passes(self):
        scenario, packet = self.documents("C02")
        output = b.parse_json(b.literal_report(packet))
        output["facts"] = [x for x in output["facts"] if x["source"]["field"] != "beta"]
        result = b.evaluate_fictional(scenario, packet, b.canonical(output), self.bounds, approved_fixture_root=self.fixture_root)
        self.assertEqual(result["score"]["critical_errors"], ())
        self.assertEqual(result["primary_coverage"], 1.0)
        self.assertTrue(result["measurement_completion"])
        self.assertEqual(result["decisions"][0]["verdict"], "rejected")

    def test_full_facts_partial_status_is_not_strict_exact_report(self):
        scenario, packet = self.documents("C01")
        output = b.parse_json(b.literal_report(packet))
        output.update(status="partial", reason="Fictional partial-status control.")
        result = b.evaluate_fictional(scenario, packet, b.canonical(output), self.bounds, approved_fixture_root=self.fixture_root)
        self.assertTrue(result["measurement_completion"])
        self.assertEqual(result["decisions"][0]["verdict"], "rejected")

    def test_always_abstain_no_facts_no_completion_no_errors(self):
        scenario, packet = self.documents("C01")
        raw = b.literal_report(packet, always_abstain=True)
        self.assertEqual(b.parse_json(raw)["facts"], [])
        result = b.evaluate_fictional(scenario, packet, raw, self.bounds, approved_fixture_root=self.fixture_root)
        self.assertFalse(result["measurement_completion"])
        self.assertEqual(result["score"]["primary"]["coverage"], 0.0)
        self.assertEqual(result["score"]["critical_errors"], ())
        self.assertEqual(result["decisions"][0]["verdict"], "rejected")

    def test_F02_bad_node_is_a_real_ancestor_and_actual_core_rejects(self):
        scenario, _, _, result = self.evaluate("F02")
        selected = next(x for x in scenario["snapshot"]["sources"] if x["source_id"] == "fiction-gwas")
        self.assertEqual(selected["parents"], ["fiction-forbidden"])
        self.assertIsNotNone(selected["computed_at"])
        self.assertEqual(result["stages"]["G1"]["error_class"], "ContractError")
        self.assertIn("role denied", result["stages"]["G1"]["reason"])
        self.assertIsNone(result["score"])

    def test_F03_F04_real_residual_core_guards_pass_without_wrapper(self):
        for key in ("F03", "F04"):
            with self.subTest(scenario=key):
                _, _, _, result = self.evaluate(key)
                self.assertEqual(result["stages"]["G2"]["status"], "rejected")
                self.assertEqual(result["stages"]["G3"]["status"], "pass")
                self.assertEqual(result["stages"]["G4"]["status"], "pass")
                self.assertEqual(result["decisions"][1]["verdict"], "admitted")

    def test_F09_Boolean_is_schema_valid_but_core_rejects_native_measurement(self):
        _, _, _, result = self.evaluate("F09")
        self.assertEqual(result["stages"]["G3"]["status"], "rejected")
        self.assertIn("Boolean", result["stages"]["G3"]["reason"])
        self.assertEqual(result["adapter_status"], "scorable")
        self.assertIsNone(result["score"])

    def test_malformed_and_oversize_retained_without_repair(self):
        for key in ("F08", "F10"):
            with self.subTest(scenario=key):
                _, _, raw, result = self.evaluate(key)
                self.assertEqual(result["raw_terminal"], "malformed")
                self.assertEqual(result["adapter_status"], "malformed")
                if key == "F10":
                    self.assertEqual(len(raw), 262145)

    def test_generation_has_no_reference_parameter_or_file_reads(self):
        self.assertEqual(list(inspect.signature(b.literal_report).parameters), ["packet", "always_abstain"])
        _, packet = self.documents("C01")
        with patch.object(b, "read_file", side_effect=AssertionError("pure generator attempted file read")), \
             patch.object(b, "compile_reference", side_effect=AssertionError("pure generator attempted reference compilation")), \
             patch.object(b, "verify_reference", side_effect=AssertionError("pure generator attempted reference replay")):
            self.assertEqual(len(b.parse_json(b.literal_report(packet))["facts"]), 15)
            self.assertEqual(b.parse_json(b.literal_report(packet, always_abstain=True))["facts"], [])
        altered = deepcopy(packet)
        altered["reference"] = {"forbidden": "invented"}
        with self.assertRaises(b.ContractError):
            b.literal_report(altered)

    def test_native_generation_reads_only_exact_packet_allowlist(self):
        _, packet = self.documents("C01")
        packet = deepcopy(packet)
        packet["case_id"] = "p05-01"
        native_root = self.work / "generation-only"
        packet_root = native_root / (b.source_inputs.OUTPUT_PREFIX + "20000101T000000Z")
        packet_path = packet_root / "packets/p05-01.json"
        packet_path.parent.mkdir(parents=True)
        raw = b.canonical(packet)
        packet_path.write_bytes(raw)
        spec = dict(path=str(packet_path), sha256=b.digest(raw), task_sha256=packet["task_sha256"], blocked_reason=None)
        actual_read = b.read_file
        observed = []
        def allowlisted(path, deadline, maximum):
            observed.append(Path(path))
            self.assertEqual(Path(path), packet_path)
            return actual_read(path, deadline, maximum)
        with patch.object(b, "OUTPUT_ROOT", native_root), patch.object(b, "read_file", side_effect=allowlisted):
            literal, abstain = b.generate_native_case("p05-01", spec, self.bounds)
        self.assertEqual(observed, [packet_path])
        self.assertEqual(len(b.parse_json(literal)["facts"]), 15)
        self.assertEqual(b.parse_json(abstain)["facts"], [])
        with self.assertRaises(b.ContractError):
            b.generate_native_case("p05-01", dict(spec, reference_sha256="a" * 64), self.bounds)

    def test_native_signed_zero_float_type_and_unknown_context_preserved(self):
        _, packet = self.documents("C01")
        packet = deepcopy(packet)
        packet["source_records"][1]["values"]["beta"] = -0.0
        raw = b.literal_report(packet)
        fact = next(x for x in b.parse_json(raw)["facts"] if x["source"]["field"] == "beta")
        self.assertIs(type(fact["value"]), float)
        self.assertEqual(b.canonical(fact["value"]), b"-0.0")
        self.assertEqual(packet["unknown_context"], b.source_inputs.UNKNOWN_CONTEXT)

    def test_unavailable_reference_cannot_be_scored_or_wire_fabricated(self):
        with self.assertRaises(b.ContractError):
            b.report_exactness({}, b"{}", cell_id="invented")
        _, _, _, result = self.evaluate("F09")
        self.assertIsNone(result["score"])
        self.assertEqual(result["decisions"][2]["verdict"], "admitted")

    def test_actual_Windows_memory_api_works_without_optional_psutil(self):
        self.assertEqual(sys.platform, "win32")
        with patch.dict(sys.modules, {"psutil": None}):
            rss, lifetime_peak = b.memory_reading()
        self.assertGreater(rss, 0)
        self.assertGreaterEqual(lifetime_peak, rss)

    def test_memory_unknown_and_exceeded_bounds_fail_closed(self):
        with patch.object(b, "memory_reading", return_value=(None, None)):
            with self.assertRaises(b.ContractError):
                self.bounds.check()
        with patch.object(b, "memory_reading", return_value=(b.LIMITS["memory_bytes"] + 1, b.LIMITS["memory_bytes"] + 1)):
            with self.assertRaises(b.ContractError):
                self.bounds.check()

    def test_expired_deadline_stops_before_further_read(self):
        expired = b.Bounds(self.output, seconds=-1)
        with self.assertRaises(TimeoutError):
            expired.check()

    def test_real_concurrent_reservation_has_one_owner(self):
        from concurrent.futures import ThreadPoolExecutor
        output = self.work / "concurrent-output"
        def reserve():
            try:
                journal = b.RunJournal(output, kind="build")
                journal.close()
                return "owned"
            except FileExistsError:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(lambda _: reserve(), range(2)))
        self.assertEqual(sorted(result), ["owned", "rejected"])
        self.assertEqual(len(b.read_chain(output / "journal.jsonl")), 1)

    def test_unknown_extra_reference_fields_and_duplicate_slots_are_rejected(self):
        _, packet = self.documents("C01")
        packet = deepcopy(packet)
        packet["fact_skeleton"].append(deepcopy(packet["fact_skeleton"][0]))
        with self.assertRaises(b.ContractError):
            b.literal_report(packet)

    def test_serialized_fixture_cannot_grant_its_own_source_root(self):
        scenario, packet = self.documents("C01")
        scenario = deepcopy(scenario)
        scenario["snapshot"]["raw_root"] = str(self.work / "forbidden")
        with self.assertRaises(b.ContractError):
            b.evaluate_fictional(scenario, packet, b.literal_report(packet), self.bounds, approved_fixture_root=self.fixture_root)

    def test_raw_optional_scope_fields_cannot_create_anchor_authority(self):
        _, packet = self.documents("C01")
        packet = deepcopy(packet)
        packet["source_records"][1]["values"].update(targetId="ENSG_FICTIONAL", diseaseId="EFO_FICTIONAL")
        _, _, anchors, _, _ = b.packet_view(packet)
        self.assertEqual(anchors, {"gwas-0000"})

    def test_publication_new_leaf_and_no_clobber_use_real_path_helpers(self):
        folder = self.work / "publication"
        folder.mkdir()
        bounds = b.Bounds(folder, seconds=10)
        bounds.publish("fresh/child.json", b"{}")
        self.assertEqual((folder / "fresh/child.json").read_bytes(), b"{}")
        with self.assertRaises(OSError):
            bounds.publish("fresh/child.json", b"changed")
        self.assertEqual((folder / "fresh/child.json").read_bytes(), b"{}")

    def test_fictional_end_to_end_retains_real_raw_bytes_journal_and_all_cells(self):
        output = self.work / "full-fictional-qualification"
        manifest_hash = b.digest((self.fixture_root / "manifest.json").read_bytes())
        result = b.qualify_fictional_fixtures(self.fixture_root, output, expected_manifest_sha256=manifest_hash)
        self.assertEqual(result["status"], "PASS_FICTIONAL_QUALIFICATION_ONLY")
        self.assertEqual(result["native_outputs_executed"], 0)
        self.assertEqual(len(result["output_cells"]), 38)
        self.assertEqual(len(result["decision_cells"]), 90)
        self.assertEqual(sum(x["received_terminal"] == "returned" for x in result["output_cells"]), 14)
        self.assertEqual(sum(x["terminal"] == "malformed" for x in result["output_cells"]), 2)
        self.assertEqual(sum(x["verdict"] != "no_decision" for x in result["decision_cells"]), 42)
        for cell in result["output_cells"]:
            if cell["raw_path"]:
                raw = (output / cell["raw_path"]).read_bytes()
                self.assertEqual(b.digest(raw), cell["raw_sha256"])
                self.assertEqual(len(raw), cell["raw_bytes"])
        self.assertEqual(len(result["fictional_references"]), 14)
        self.assertTrue((output / "seal.json").is_file())
        self.assertEqual(b.read_chain(output / "journal.jsonl")[-1]["event"], "experiment_completed")
        with self.assertRaises(FileExistsError):
            b.qualify_fictional_fixtures(self.fixture_root, output, expected_manifest_sha256=manifest_hash)

    def terminal_fixture(self, name):
        output = self.work / name
        journal = b.RunJournal(output, kind="build")
        outputs, decisions = b.blank_ledgers()
        ledger = dict(status="COMPLETED_PENDING_INDEPENDENT_AUDIT", failure=None,
            output_cells=list(outputs.values()), decision_cells=list(decisions.values()))
        return output, journal, ledger

    def test_terminal_ledger_failure_still_retains_emergency_38_90_and_failure_seal(self):
        output, journal, ledger = self.terminal_fixture("ledger-io-failure")
        actual = b.publish_bytes
        def fail_ledger(path, raw, **kwargs):
            if Path(path).name == "ledger.json":
                raise OSError("fictional ledger storage error")
            return actual(path, raw, **kwargs)
        with patch.object(b, "publish_bytes", side_effect=fail_ledger):
            failed, errors = b.finalize_ledger(output, journal, ledger)
        self.assertTrue(failed)
        saved = b.parse_json((output / "emergency-ledger.json").read_bytes())
        self.assertEqual(len(saved["output_cells"]), 38)
        self.assertEqual(len(saved["decision_cells"]), 90)
        self.assertTrue((output / "failure-seal.json").is_file())
        self.assertEqual(errors[0]["stage"], "terminal_ledger_publication")

    def test_terminal_journal_append_and_close_errors_do_not_qualify_success(self):
        for fault in ("append", "close"):
            with self.subTest(fault=fault):
                output, journal, ledger = self.terminal_fixture("journal-" + fault + "-failure")
                actual_append, actual_close = journal.append, journal.close
                fired = [False]
                def append(event, **details):
                    if event == "cell_terminal" and not fired[0]:
                        fired[0] = True
                        raise OSError("fictional append error")
                    return actual_append(event, **details)
                def close():
                    actual_close()
                    raise OSError("fictional close error after real handle close")
                with patch.object(journal, fault, side_effect=append if fault == "append" else close):
                    failed, errors = b.finalize_ledger(output, journal, ledger)
                self.assertTrue(failed)
                self.assertTrue(errors)
                self.assertTrue((output / "failure-seal.json").is_file())
                self.assertFalse((output / "seal.json").exists())
                saved = b.parse_json((output / "ledger.json").read_bytes())
                self.assertEqual(len(saved["output_cells"]), 38)
                self.assertEqual(len(saved["decision_cells"]), 90)

    def test_success_seal_write_failure_attempts_independent_failure_seal(self):
        output, journal, ledger = self.terminal_fixture("seal-io-failure")
        actual = b.publish_bytes
        def fail_success(path, raw, **kwargs):
            if Path(path).name == "seal.json":
                raise OSError("fictional success-seal storage error")
            return actual(path, raw, **kwargs)
        with patch.object(b, "publish_bytes", side_effect=fail_success):
            failed, errors = b.finalize_ledger(output, journal, ledger)
        self.assertTrue(failed)
        self.assertEqual(errors[-1]["stage"], "terminal_seal_publication")
        emergency = b.parse_json((output / "failure-seal.json").read_bytes())
        self.assertEqual(len(emergency["output_cells"]), 38)
        self.assertEqual(len(emergency["decision_cells"]), 90)

    def test_aggregate_failure_is_secondary_and_cannot_erase_outer_schedule(self):
        with patch.object(b, "aggregate_cells", side_effect=b.ContractError("fictional aggregate failure")):
            aggregate, failure = b.terminal_aggregate([{"fictional": True}], [])
        self.assertIsNone(aggregate)
        self.assertEqual(failure["stage"], "terminal_core_aggregation")
        output, journal, ledger = self.terminal_fixture("aggregate-failure")
        ledger.update(failure=failure, core_aggregate=None)
        failed, _ = b.finalize_ledger(output, journal, ledger)
        self.assertTrue(failed)
        saved = b.parse_json((output / "ledger.json").read_bytes())
        self.assertEqual(len(saved["output_cells"]), 38)
        self.assertEqual(len(saved["decision_cells"]), 90)
        self.assertTrue((output / "failure-seal.json").is_file())

    def test_nonserializable_or_oversize_metadata_keeps_minimal_terminal_frame(self):
        for name, value in (("not-json", object()), ("oversize", "x" * (16 * 1024**2))):
            with self.subTest(fault=name):
                output, journal, ledger = self.terminal_fixture("serialization-" + name)
                ledger["optional_metadata"] = value
                failed, errors = b.finalize_ledger(output, journal, ledger)
                self.assertTrue(failed)
                self.assertEqual(errors[0]["stage"], "terminal_full_ledger_serialization")
                saved = b.parse_json((output / "ledger.json").read_bytes())
                self.assertEqual(saved["status"], "FAILED_PARTIAL_NOT_QUALIFIED")
                self.assertEqual(len(saved["output_cells"]), 38)
                self.assertEqual(len(saved["decision_cells"]), 90)
                self.assertTrue((output / "failure-seal.json").is_file())

    def test_terminal_resource_failure_stays_unknown_and_unqualified(self):
        with patch.object(self.bounds, "report", side_effect=OSError("fictional resource report error")):
            resources, failure = b.terminal_resources(self.bounds)
        self.assertEqual(resources["status"], "unknown_terminal_resource_report")
        self.assertEqual(failure["stage"], "terminal_resource_report")

    def test_interrupted_qualification_preserves_partial_and_unexecuted_cells(self):
        output = self.work / "interrupt-qualification"
        original = b.fictional_candidate
        def interrupt(packet, key):
            if key == "C02":
                raise KeyboardInterrupt()
            return original(packet, key)
        with patch.object(b, "fictional_candidate", side_effect=interrupt):
            with self.assertRaises(b.ContractError):
                b.qualify_fictional_fixtures(self.fixture_root, output,
                    expected_manifest_sha256=b.digest((self.fixture_root / "manifest.json").read_bytes()))
        saved = b.parse_json((output / "ledger.json").read_bytes())
        self.assertEqual(len(saved["output_cells"]), 38)
        self.assertEqual(len(saved["decision_cells"]), 90)
        by_id = {x["cell_id"]: x for x in saved["output_cells"]}
        self.assertEqual(by_id["S-C01"]["terminal"], "returned")
        self.assertEqual(by_id["S-C02"]["terminal"], "interrupted")
        self.assertEqual(by_id["S-C03"]["terminal"], "unexecuted")
        self.assertTrue((output / "failure-seal.json").is_file())

    def test_no_decision_is_not_successful_rejection(self):
        stages = {key: dict(status="unexecuted", reason="not_attempted") for key in b.STAGES}
        stages["G4"]["schema_status"] = "pass"
        decision = b.project_decision(stages, "FULL", decision_id="fiction")
        self.assertEqual(decision["verdict"], "no_decision")
        self.assertEqual(decision["terminal"], "unexecuted")

    def test_wrong_ready_fails_before_source_dispatch_and_all_terminals_remain(self):
        parent = self.work / "failure-output"
        parent.mkdir()
        plan, ready = self.work / "fiction-plan.json", self.work / "fiction-ready.json"
        plan.write_bytes(b"{}")
        ready.write_bytes(b"{}")
        output = parent / (b.OUTPUT_PREFIX + "20000101T000000Z")
        with patch.object(b, "OUTPUT_ROOT", parent), patch.object(b, "PLAN_PATH", plan), patch.object(b, "READY_PATH", ready), \
             patch.object(b, "verify_native_references", side_effect=AssertionError("unauthorized native replay")):
            with self.assertRaises(b.ContractError):
                b.execute(output, expected_ready_sha256="0" * 64)
        ledger = b.parse_json((output / "ledger.json").read_bytes())
        self.assertEqual(len(ledger["output_cells"]), 38)
        self.assertEqual(len(ledger["decision_cells"]), 90)
        self.assertEqual({x["terminal"] for x in ledger["output_cells"]}, {"unexecuted"})
        self.assertEqual({x["verdict"] for x in ledger["decision_cells"]}, {"no_decision"})
        self.assertTrue((output / "failure-seal.json").is_file())
        chain = b.read_chain(output / "journal.jsonl")
        self.assertEqual(sum(x["event"] == "cell_terminal" for x in chain), 38)
        self.assertEqual(sum(x["event"] == "decision_terminal" for x in chain), 90)
        self.assertFalse(any(x["event"] == "dispatch" for x in chain))
        with patch.object(b, "OUTPUT_ROOT", parent):
            with self.assertRaises(b.ContractError):
                b.reserve_output(output)


if __name__ == "__main__":
    unittest.main()
