"""Corpus construction tests; do not use either implementation as an oracle."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.equal_policy import cases


class CorpusTests(unittest.TestCase):
    def test_complete_unique_schedule_and_obligation_coverage(self):
        records = cases.case_specs()
        self.assertEqual(len(records), 108)
        self.assertEqual([row["control_id"] for row in records], [f"EP{i:03d}" for i in range(1, 109)])
        covered = {name for row in records for name in row["oracle"]["obligation_ids"]}
        self.assertEqual(covered, set(cases.POLICY_IDS))
        for row in records:
            self.assertTrue(row["oracle"]["rationale"])
            self.assertIn(row["oracle"]["decision"], {"accept", "reject", "inspect_only"})
            self.assertIn(row["construction_stratum"], {"exposed_regression", "new_synthetic_construction"})

    def test_manifests_and_calls_are_independently_owned(self):
        first = cases.case_specs()
        first[0]["oracle"]["observables"]["admitted_observation_ids"].append("injected")
        self.assertEqual(cases.case_specs()[0]["oracle"]["observables"]["admitted_observation_ids"], ["obs-1"])
        self.assertEqual(cases.case_manifest(), cases.case_manifest())
        self.assertEqual(cases.oracle_manifest(), cases.oracle_manifest())
        self.assertEqual(cases.oracle_manifest()["status"], "construction_not_frozen")

    def test_case_module_does_not_import_validators_or_test_fixtures(self):
        tree = ast.parse(Path(cases.__file__).read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertTrue(set(imports) <= {"__future__", "copy", "hashlib", "json", "pathlib"})

    def test_base_has_complete_fictional_lineage_and_sealed_bytes(self):
        docs = cases.prepare_documents(cases.case_specs()[0])
        sources = docs["snapshot"]["sources"]
        self.assertEqual(sources[1]["parents"], [sources[0]["source_id"]])
        self.assertEqual(docs["evidence"]["observations"][0]["input_refs"], [sources[1]["source_id"]])
        for document, pin in (("source", sources[0]["sha256"]), ("mapping", sources[1]["sha256"]),
                              ("receipt", sources[0]["receipt_sha256"]),
                              ("evidence", docs["snapshot"]["artifacts"][0]["sha256"])):
            self.assertEqual(hashlib.sha256(cases.file_bytes(docs[document])).hexdigest(), pin)
        self.assertEqual(docs["receipt"]["bytes"], len(cases.file_bytes(docs["source"])))
        for node in sources:
            self.assertTrue(node["source_url"].startswith("https://example.invalid/"))

    def test_hash_scope_preserves_incompatible_hypothesis_control(self):
        base = cases.prepare_documents(cases.case_specs()[0])
        changed = cases.prepare_documents(cases.case_specs()[34])
        self.assertEqual(base["evidence"]["observations"][0]["feature_scope"], changed["evidence"]["observations"][0]["feature_scope"])
        self.assertNotEqual(cases.fingerprint({k: changed["case"]["hypothesis"][k] for k in cases.HYPOTHESIS_FIELDS}),
                            changed["evidence"]["observations"][0]["feature_scope"])

    def test_dependency_constructions_are_distinct(self):
        values = {row["control_id"]: cases.prepare_documents(row) for row in cases.case_specs()[43:46]}
        independent = values["EP044"]["evidence"]["observations"]
        conflict = values["EP045"]["evidence"]["observations"]
        cohort = values["EP046"]["evidence"]["observations"]
        self.assertNotEqual(independent[0]["context"]["cohort_ids"], independent[1]["context"]["cohort_ids"])
        self.assertEqual(conflict[0]["dependency_group"], conflict[1]["dependency_group"])
        self.assertNotEqual(conflict[0]["features"], conflict[1]["features"])
        self.assertEqual(cohort[0]["context"]["cohort_ids"], cohort[1]["context"]["cohort_ids"])
        self.assertNotEqual(cohort[0]["study_id"], cohort[1]["study_id"])

    def test_descriptor_excludes_oracle_and_reports_pending_recipes(self):
        cache = Path(__file__).resolve().parents[2] / "data/cache/equal-policy-corpus-tests"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            root = Path(temporary)
            plain, pending = cases.write_source_bundle(root / "plain", cases.case_specs()[0])
            self.assertEqual(pending, {})
            self.assertEqual(set(plain), {"schema_version", "control_id", "operation", "variant", "paths", "options", "anchors"})
            self.assertNotIn("oracle", cases.canonical(plain).decode())
            for path in plain["paths"].values():
                self.assertFalse(Path(path).is_absolute())
                self.assertTrue((root / "plain" / path).is_file())
            sealed, pending = cases.write_source_bundle(root / "sealed", cases.case_specs()[58])
            self.assertEqual(pending, dict(sealed_producer="valid_scored", sealed_mutation="none"))
            policy, pending = cases.write_source_bundle(root / "policy", cases.case_specs()[77])
            self.assertEqual(pending, dict(policy_recipe="none"))
            with self.assertRaises(FileExistsError):
                cases.write_source_bundle(root / "plain", cases.case_specs()[0])

    def test_file_faults_preserve_stale_pins_and_never_escape_fresh_root(self):
        cache = Path(__file__).resolve().parents[2] / "data/cache/equal-policy-corpus-tests"
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            root = Path(temporary)
            for identifier in ("EP012", "EP017", "EP018", "EP057"):
                spec = next(row for row in cases.case_specs() if row["control_id"] == identifier)
                destination = root / identifier
                cases.write_source_bundle(destination, spec)
                raw = destination / "input/source.json"
                if identifier == "EP012":
                    payload = (destination / "input/case.json").read_text()
                    self.assertEqual(payload.count('"schema_version"'), 2)
                elif identifier == "EP017":
                    doc = json.loads((destination / "input/snapshot.json").read_bytes())
                    self.assertNotEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), doc["sources"][0]["sha256"])
                elif identifier == "EP018":
                    self.assertFalse(raw.exists())
                else:
                    self.assertTrue(raw.is_dir())

    def test_mutations_are_explicit_and_unknown_operation_fails(self):
        documents = {"doc": {"a": [1], "b": 2}}
        cases.apply_changes(documents, [cases.change("doc", ["a"], 3, op="append"),
                                        cases.change("doc", ["b"], None, op="delete")])
        self.assertEqual(documents, {"doc": {"a": [1, 3]}})
        with self.assertRaises(ValueError):
            cases.apply_changes(documents, [cases.change("doc", ["a"], 0, op="invented")])

    def test_preparation_never_claims_executed_scoring_or_selection(self):
        permitted = {"admitted_observation_ids", "eligible_observation_ids", "scorer_preflight", "exclusion_reasons"}
        for item in cases.case_specs():
            if item["operation"] == "prepare_run":
                self.assertLessEqual(set(item["oracle"]["observables"]), permitted, item["control_id"])
            if item["operation"] == "verify_run":
                self.assertTrue(set(item["preparation"]["recipe"]) & {"sealed_producer", "policy_recipe"})

    def test_local_configuration_and_runtime_witnesses_are_explicit_fictions(self):
        docs = cases.prepare_documents(next(row for row in cases.case_specs() if row["control_id"] == "EP094"))
        self.assertIn("fictional", docs["local_model"]["model_id"])
        self.assertEqual(docs["local_model"]["endpoint"], "http://127.0.0.1:59999")
        self.assertEqual(len(cases.runtime_witness_specs()), 3)
        self.assertTrue(all(row["expected"] for row in cases.runtime_witness_specs()))


if __name__ == "__main__":
    unittest.main()
