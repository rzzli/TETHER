"""Fictional JSON only; independent expected decisions never enter production."""
from dataclasses import replace
import hashlib
import inspect
import tempfile
import time
from pathlib import Path
import unittest
from unittest.mock import patch

from asof.serde import ContractError, canonical, parse_json
from asof.study.source_fact_evaluation import ScoredCell
from asof_p05_replay import controls_v1 as c


class ControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Test invocation supplies workspace TEMP/TMP; no native data is opened.
        cls.temporary = tempfile.TemporaryDirectory(prefix="p05-portable-controls-")
        cls.work = Path(cls.temporary.name)
        cls.deadline = time.monotonic() + 300
        cls.scenarios = c.prepare_controls(cls.work / "fixtures", cls.deadline)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def evaluate(self, key, raw=None):
        scenario = self.scenarios[key]
        raw = c.generate_control(scenario, self.deadline) if raw is None else raw
        return raw, c.evaluate_control(scenario, raw, self.deadline)

    def test_fresh_source_only_authoring_and_fixed_schedule(self):
        self.assertEqual(tuple(self.scenarios), tuple([f"C{n:02d}" for n in range(1, 5)] + [f"F{n:02d}" for n in range(1, 11)]))
        self.assertFalse(any(p.name in ("oracle.json", "ledger.json", "output.json") for p in (self.work / "fixtures").rglob("*")))
        for key, scenario in self.scenarios.items():
            self.assertEqual(scenario.cell_id, "S-" + key)
            self.assertEqual(len(scenario.generation_snapshot.sources), 3)
            self.assertTrue(all(not n.parents and n.computed_at is None for n in scenario.generation_snapshot.sources))
        with self.assertRaises(FileExistsError):
            c.prepare_controls(self.work / "fixtures", self.deadline)

    def test_all_fourteen_retained_actual_guards_and_42_decisions(self):
        expected_failures = {"F01": "G0", "F02": "G1", "F03": "G2", "F04": "G2", "F09": "G3"}
        ids = []
        for key in c.SCENARIOS:
            with self.subTest(control=key):
                _, result = self.evaluate(key)
                expected = {"FULL": "admitted" if key.startswith("C") else "rejected",
                    "WITHOUT_WRAPPER": "admitted" if key.startswith("C") or key in ("F03", "F04") else "rejected",
                    "WIRE_ONLY": "rejected" if key in ("F01", "F08", "F10") else "admitted"}
                self.assertEqual({d["policy"]: d["verdict"] for d in result["decisions"]}, expected)
                self.assertEqual(result["decisions"][0]["first_failure_stage"],
                    None if key.startswith("C") else expected_failures.get(key, "G4"))
                ids.extend(d["decision_id"] for d in result["decisions"])
                self.assertEqual(result["scientific_validation"], "not_established")
                if result["score"] is not None:
                    self.assertIsInstance(result["score"], ScoredCell)
                    self.assertEqual(result["score"]["cell_id"], "S-" + key)
        self.assertEqual(len(ids), 42)
        self.assertEqual(len(set(ids)), 42)
        self.assertEqual(ids, [f"D-S-{key}-{p}" for key in c.SCENARIOS for p in c.POLICIES])

    def test_C02_absent_null_empty_are_generic_JSON_controls(self):
        raw, result = self.evaluate("C02")
        fields = {f["source"]["field"]: f for f in parse_json(raw)["facts"]}
        self.assertEqual(fields["beta"]["unknown_reason"], "null_source_value")
        self.assertEqual(fields["standardError"]["unknown_reason"], "field_not_in_schema")
        self.assertEqual(fields["pValueMantissa"]["unknown_reason"], "empty_source_value")
        self.assertEqual(result["reference_counts"]["measurement_answerable_facts"], 1)
        self.assertEqual(result["stages"]["G2"]["status"], "pass")

    def test_C03_all_physical_matches_and_negative_finite_SE_are_technical(self):
        raw, result = self.evaluate("C03")
        facts = parse_json(raw)["facts"]
        self.assertEqual(len(facts), 22)
        self.assertEqual([f["value"] for f in facts if f["source"]["field"] == "standardError"], [0.25, -0.5])
        self.assertEqual(result["reference_counts"]["measurement_answerable_groups"], 2)
        self.assertEqual(result["decisions"][0]["verdict"], "admitted")

    def test_C04_exact_unknown_report_admits_but_coverage_is_undefined(self):
        _, result = self.evaluate("C04")
        self.assertEqual(result["decisions"][0]["verdict"], "admitted")
        self.assertIsNone(result["primary_coverage"])
        self.assertFalse(result["measurement_completion"])
        self.assertEqual(result["reference_counts"]["measurement_answerable_facts"], 0)

    def test_F02_denial_is_actual_core_role_ancestry_and_generation_stays_flat(self):
        scenario = self.scenarios["F02"]
        self.assertEqual(scenario.generation_snapshot.sources[0].parents, ())
        self.assertEqual(scenario.evaluation_snapshot.sources[0].parents, ("fiction-forbidden",))
        self.assertEqual(len(scenario.evaluation_snapshot.sources), 4)
        _, result = self.evaluate("F02")
        self.assertEqual(result["stages"]["G1"]["error_class"], "ContractError")
        self.assertIn("role denied", result["stages"]["G1"]["reason"])
        self.assertIsNone(result["score"])

    def test_F03_F04_wrapper_rejects_and_actual_residual_guards_admit(self):
        for key in ("F03", "F04"):
            with self.subTest(control=key):
                _, result = self.evaluate(key)
                self.assertEqual(result["stages"]["G2"]["status"], "rejected")
                self.assertEqual(result["stages"]["G3"]["status"], "pass")
                self.assertEqual(result["stages"]["G4"]["status"], "pass")
                self.assertEqual(result["decisions"][1]["verdict"], "admitted")
                self.assertIsInstance(result["score"], ScoredCell)

    def test_F09_Boolean_is_schema_valid_but_core_rejects_measurement(self):
        _, result = self.evaluate("F09")
        self.assertEqual(result["stages"]["G3"]["status"], "rejected")
        self.assertIn("Boolean", result["stages"]["G3"]["reason"])
        self.assertEqual(result["adapter_status"], "scorable")
        self.assertIsNone(result["score"])

    def test_F08_duplicate_keys_and_F10_oversize_retained_unrepaired(self):
        for key in ("F08", "F10"):
            with self.subTest(control=key):
                raw, result = self.evaluate(key)
                self.assertEqual(result["adapter_status"], "malformed")
                self.assertEqual(result["raw_terminal"], "malformed")
                base = c.literal_report(self.scenarios[key].task, self.scenarios[key].generation_snapshot,
                                        self.scenarios[key].groups)
                if key == "F08":
                    self.assertEqual(raw, base[:-1] + b',"status":"answered"}')
                    self.assertEqual(raw.count(b'"status":"answered"'), 2)
                else:
                    self.assertEqual(len(raw), 262145)
                    self.assertEqual(raw, base + b" " * (262145 - len(base)))

    def test_all_raw_bytes_match_frozen_fictional_qualification_pins(self):
        # Metadata-only SHA/length projection of the fourteen invented outputs
        # in qualification ledger fadf013f8fdb2f196c191561b1bafe96ef542f95b07a8deae05dd94f781ce7f7.
        # These historical byte pins are test assertions, never generator input.
        expected = {
            "C01": (5392, "7c668d0b620a6a4b721ea3256e148c3903ebaeb1e1b7b601b1040d7a7fd0f9d3"),
            "C02": (5441, "e733e891d9cd2ea284521a56d5cd3ba5c5101967baeda327d7101840f23f43d7"),
            "C03": (7790, "5c0c12c0a5bdf780762fe5e573e571af88d0303740ddd0ec0aee6f8c37ede7ae"),
            "C04": (5455, "c2086854f0c7fc21a15602c4eeb3b2e61304c5ce82b189b207bb890c181a710b"),
            "F01": (5392, "49a9b3125ed1d7ff2dff2c12d453e1c90de560dec4b82c3b435ce7471ddb6797"),
            "F02": (5392, "bf0633823fb5f256c0879dbebfa520f4ea457aba4dcd55a5f825000a11fbbf8a"),
            "F03": (5392, "b4565e87b87dd744d662a748b2928dab9c1cf2f5602a1f829a6fa12dba743964"),
            "F04": (5392, "d16e165e563c4efd64c5d4e3e8038f6968cdcc1103915ce222e8fac7d44accd9"),
            "F05": (5392, "2191ea666443dcbb3ef760ca42c0898be9b026dfce5fc62e1443d8dd2f39f078"),
            "F06": (5394, "41c1c63aecd67053b9a8ae6ac46e594b95f2af6d7a9daf854a6a72a62f8b6ec5"),
            "F07": (5443, "12abea71ece455bff867816b552033114317b24e8f8a1d0856b11b005e202138"),
            "F08": (5412, "82d3e865d281fed1fb7457e3f338f0a08ae3a0b789c06e1187056582597f732f"),
            "F09": (5392, "791d65bbb6a400161581573ae049197bbd7ed20a9e69321117208e584cb58921"),
            "F10": (262145, "d2f27b8f77785d4b4b43b6176430f04e5a5add5f84f94a74d136091acbe6d7fa"),
        }
        for key in c.SCENARIOS:
            with self.subTest(control=key):
                raw = c.generate_control(self.scenarios[key], self.deadline)
                self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), expected[key])

    def test_strict_exactness_rejects_unknown_omission_despite_completion(self):
        raw = c.generate_control(self.scenarios["C02"], self.deadline)
        output = parse_json(raw)
        output["facts"] = [f for f in output["facts"] if f["source"]["field"] != "beta"]
        _, result = self.evaluate("C02", canonical(output))
        self.assertEqual(result["score"]["critical_errors"], ())
        self.assertTrue(result["measurement_completion"])
        self.assertEqual(result["primary_coverage"], 1.0)
        self.assertEqual(result["decisions"][0]["verdict"], "rejected")

    def test_strict_exactness_requires_answered_status(self):
        raw = c.generate_control(self.scenarios["C01"], self.deadline)
        output = parse_json(raw)
        output.update(status="partial", reason="Fictional partial-status control.")
        _, result = self.evaluate("C01", canonical(output))
        self.assertTrue(result["measurement_completion"])
        self.assertEqual(result["decisions"][0]["verdict"], "rejected")

    def test_pure_generation_never_accesses_evaluator_or_files(self):
        scenario = replace(self.scenarios["F02"], evaluation_snapshot=None, catalog=None,
                           fixture_root=None, original_source_anchors=None)
        with patch.object(c, "read_file", side_effect=AssertionError("generation read source")), \
             patch.object(c, "compile_reference", side_effect=AssertionError("generation compiled gold")), \
             patch.object(c, "verify_reference", side_effect=AssertionError("generation replayed gold")), \
             patch.object(Path, "open", side_effect=AssertionError("generation opened file")):
            raw = c.generate_control(scenario, self.deadline)
        self.assertEqual(len(parse_json(raw)["facts"]), 15)
        self.assertEqual(list(inspect.signature(c.generate_control).parameters), ["scenario", "deadline"])

    def test_evaluator_root_is_anchored_outside_snapshot_claim(self):
        scenario = self.scenarios["C01"]
        foreign = replace(scenario.evaluation_snapshot, raw_root=str(self.work))
        with self.assertRaisesRegex(ContractError, "cannot grant a raw root"):
            c.evaluate_control(replace(scenario, evaluation_snapshot=foreign),
                               c.generate_control(scenario, self.deadline), self.deadline)

    def test_deadline_rejects_before_authoring_or_generation(self):
        with self.assertRaises(TimeoutError):
            c.prepare_controls(self.work / "expired", time.monotonic() - 1)
        self.assertFalse((self.work / "expired").exists())
        with self.assertRaises(TimeoutError):
            c.generate_control(self.scenarios["C01"], time.monotonic() - 1)

    def test_module_has_no_old_tool_import_or_native_path(self):
        source = inspect.getsource(c)
        self.assertNotIn("import prepare_source", source)
        self.assertNotIn("tools/science", source)
        self.assertNotIn("gold_evidence", source)
        self.assertNotIn("data/derived", source)


if __name__ == "__main__":
    unittest.main()
