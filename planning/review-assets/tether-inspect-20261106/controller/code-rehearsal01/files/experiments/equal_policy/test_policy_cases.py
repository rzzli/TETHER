"""Schema2 corpus-construction controls without either policy validator."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.equal_policy import cases, policy_cases


class PolicyCorpusTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[2] / "data/cache/equal-policy-policy-case-tests"
        cache.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def construct(self, recipe):
        spec = next(row for row in cases.case_specs() if row["preparation"]["recipe"].get("policy_recipe") == recipe)
        root = self.root / spec["control_id"]
        descriptor, pending = cases.write_source_bundle(root, spec)
        self.assertEqual(pending, {"policy_recipe": recipe})
        original = {p.name: p.read_bytes() for p in (root / "input").iterdir()}
        result, mutation = policy_cases.prepare_policy_sources(root, spec, descriptor)
        self.assertEqual(original, {p.name: p.read_bytes() for p in (root / "input").iterdir()})
        load = lambda key: json.loads((root / result["paths"][key]).read_bytes())
        return root, spec, result, mutation, load

    def test_all_scheduled_policy_recipes_materialize_without_dropping(self):
        seen = set()
        for recipe in sorted(policy_cases.POLICY_RECIPES):
            root, spec, descriptor, mutation, load = self.construct(recipe)
            seen.add(spec["control_id"])
            self.assertEqual(mutation, recipe if recipe in policy_cases.OUTER_RECIPES else None)
            self.assertNotIn("oracle", descriptor)
            self.assertNotIn("decision", descriptor)
            self.assertEqual(load("catalog_policy")["schema_version"], 2)
            for path in descriptor["paths"].values():
                self.assertFalse(Path(path).is_absolute())
                self.assertTrue((root / path).is_file())
            with self.assertRaises(FileExistsError):
                policy_cases.prepare_policy_sources(root, spec, descriptor)
        self.assertEqual(len(seen), 16)

    def test_positive_policy_has_complete_identity_grant_and_byte_closure(self):
        root, spec, descriptor, mutation, load = self.construct("none")
        snapshot, policy, case, roots = (load(key) for key in ("snapshot", "catalog_policy", "case", "policy_roots"))
        aliases = roots["roots"]
        self.assertEqual(len(set(aliases.values())), 3)
        self.assertEqual(snapshot["raw_root"], aliases["raw"])
        self.assertEqual((root / descriptor["paths"]["snapshot"]).parent, Path(aliases["snapshot"]))
        use = policy["uses"][0]
        self.assertEqual(use["case_fingerprint"], cases.fingerprint(case))
        self.assertEqual(use["snapshot_fingerprint"], cases.fingerprint(snapshot))
        self.assertEqual(use["frame_sha256"], descriptor["anchors"]["frame_sha256"])
        ids = {row["artifact_id"] for row in policy["artifacts"]}
        self.assertEqual(ids, {row["artifact_id"] for row in use["grants"]})
        self.assertEqual(len(ids), len(snapshot["sources"]) + len(snapshot["artifacts"]))
        for row in policy["artifacts"]:
            self.assertEqual(row["artifact_id"], "artifact-" + cases.fingerprint({key: row[key] for key in policy_cases.IDENTITY_FIELDS}))
            payload = (Path(aliases[row["root_alias"]]) / row["relative_path"]).read_bytes()
            self.assertEqual((row["bytes"], row["sha256"]), (len(payload), hashlib.sha256(payload).hexdigest()))
            self.assertLessEqual(set(row["parents"]), ids)
            for proof in row["provenance"]["evidence"]:
                self.assertEqual(hashlib.sha256((Path(aliases["metadata"]) / proof["path"]).read_bytes()).hexdigest(), proof["sha256"])
        catalog_bytes = (Path(aliases["metadata"]) / policy["source_catalog"]["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(catalog_bytes).hexdigest(), policy["source_catalog"]["sha256"])

    def test_receipt_faults_do_not_collapse_into_unintended_hash_errors(self):
        for recipe in ("used_receipt_late", "unused_receipt_late", "unused_receipt_url", "unused_receipt_ref"):
            root, spec, descriptor, mutation, load = self.construct(recipe)
            snapshot = load("snapshot")
            node = next(node for node in snapshot["sources"] if node["source_id"] == ("source-1" if recipe == "used_receipt_late" else "unused-source"))
            payload = (Path(snapshot["raw_root"]) / node["receipt_path"]).read_bytes()
            receipt = json.loads(payload)
            self.assertEqual(node["receipt_sha256"], hashlib.sha256(payload).hexdigest())
            if recipe.endswith("late"):
                self.assertGreater(receipt["completed_at_utc"], node["availability"]["known_public_by"])
                self.assertEqual(node["availability"]["evidence_ref"], node["receipt_sha256"])
            elif recipe.endswith("url"):
                self.assertNotEqual(receipt["url"], node["source_url"])
            else:
                self.assertNotEqual(node["availability"]["evidence_ref"], node["receipt_sha256"])

    def test_alternative_basis_and_equivalent_timestamp_are_distinct_controls(self):
        root, spec, descriptor, mutation, load = self.construct("alternative_basis_later_download")
        snapshot = load("snapshot")
        raw = snapshot["sources"][0]
        receipt = json.loads((Path(snapshot["raw_root"]) / raw["receipt_path"]).read_bytes())
        self.assertEqual(raw["availability"]["basis"], "fictional_release_documentation")
        self.assertIsNone(raw["availability"]["known_public_by"])
        self.assertGreater(receipt["completed_at_utc"][:10], cases.ORIGIN)
        root, spec, descriptor, mutation, load = self.construct("receipt_utc_alias")
        snapshot = load("snapshot")
        raw = snapshot["sources"][0]
        receipt = json.loads((Path(snapshot["raw_root"]) / raw["receipt_path"]).read_bytes())
        self.assertTrue(receipt["completed_at_utc"].endswith("Z"))
        self.assertTrue(raw["availability"]["known_public_by"].endswith("+00:00"))

    def test_invalid_grants_frame_and_evaluator_are_intentional(self):
        for recipe in ("missing_grant", "ungranted_source"):
            root, spec, descriptor, mutation, load = self.construct(recipe)
            policy = load("catalog_policy")
            self.assertEqual(len(policy["artifacts"]) - len(policy["uses"][0]["grants"]), 1)
        root, spec, descriptor, mutation, load = self.construct("wrong_frame")
        self.assertNotEqual(descriptor["anchors"]["frame_sha256"], load("catalog_policy")["uses"][0]["frame_sha256"])
        root, spec, descriptor, mutation, load = self.construct("evaluator_product")
        product = next(row for row in load("catalog_policy")["products"] if row["dataset_id"] == "fixture_answers")
        self.assertEqual(product["agent_use_policy"], "denied_evaluator_product")
        self.assertEqual(load("snapshot")["sources"][0]["dataset_id"], "fixture_answers")
        root, spec, descriptor, mutation, load = self.construct("unsupported_scorer")
        self.assertEqual(load("scorer")["kind"], "frozen_model")

    def test_materializer_imports_no_validator_or_oracle_implementation(self):
        tree = ast.parse(Path(policy_cases.__file__).read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)
        self.assertTrue(set(imports) <= {"__future__", "copy", "hashlib", "json", "pathlib", "cases"})
        called = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertFalse(called & {"validate_policy", "authorize_snapshot", "admit_snapshot", "case_specs"})


if __name__ == "__main__":
    unittest.main()
