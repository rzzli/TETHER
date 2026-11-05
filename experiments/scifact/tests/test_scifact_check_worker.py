"""Fictional native checker integration; no actual benchmark fitting or scoring."""
import copy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from asof.serde import ContractError, canonical, parse_json
from experiments.scifact.check_worker import run
from experiments.scifact.tether_adapter import NativeSession, inspect_session
import test_scifact_policy as policy_fixtures


class CheckWorkerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = policy_fixtures.CandidatePolicyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.addCleanup(self.fixture.doCleanups)
        # The worker consumes the actual native two-file layout; contents stay fictional.
        assets = []
        for name, raw in (("model.json", b'{"fictional":true}'), ("arrays.npz", b"fictional numeric bytes")):
            path = self.fixture.modelroot / name
            path.write_bytes(raw)
            assets.append({"path": name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)})
        self.fixture.model["files"] = assets
        fit_output = self.fixture.root / "native-layout-fit"
        with NativeSession(fit_output, ["fit"], {}) as session:
            inputs = {key: {"path": str(self.fixture.prep / self.fixture.manifest["products"][key]["path"]), **proof}
                      for key, proof in self.fixture.model["input_product_proofs"].items()}
            session.begin("fit", {"inputs": inputs})
            session.finish("fit", {"files": assets}, policy_fixtures.resources())
            receipt = session.finalize()
        self.fixture.model["fit_execution"] = {"path": str(fit_output), "receipt_sha256": receipt["sha256"], "cell_id": "fit"}
        self.fixture.model["computed_at"] = datetime.now(timezone.utc).isoformat()
        self.fixture.context = self.fixture.build()
        self.root, self.context = self.fixture.root, self.fixture.context
        _, prediction, envelope = self.fixture.candidate("CONTRADICT")
        self.records = [{"schema_version": 1, "cell_id": "2", "status": "completed",
                         "session_elapsed_seconds": .1, "resources": envelope["resources"],
                         "result": {"prediction": prediction, "retrieved": envelope["retrieved"],
                                    "source_bindings": envelope["source_bindings"], "pair_scores": []}}]
        self.template_record = copy.deepcopy(self.records[0])
        self.producer_query = dict(self.context.queries[2])
        self.producer_configuration = dict(self.context.model["configuration"])
        self.recipe = {"schema_version": 1, "preparation_root": str(self.context.preparation_root),
                       "preparation_manifest_sha256": self.context.preparation_manifest_sha256,
                       "model_root": str(self.context.model_root), "model_manifest_sha256": self.context.model_manifest_sha256,
                       "cutoff": self.context.cutoff, "workspace_root": str(self.root),
                       "container_admission": self.context.container_admission, "policy_sha256": self.context.policy_sha256,
                       "configuration": self.context.model["configuration"], "schedule": [2],
                       "limits": {"phase_seconds": 30, "query_seconds": 10, "memory_bytes": 8 * 1024**3}}

    def prepare(self):
        producer = self.root / ("producer-" + str(len(list(self.root.glob("producer-*")))))
        with NativeSession(producer, ["setup", "2"], self.context.model["configuration"]) as session:
            inputs = {logical: {"path": str(self.context.model_root / name), "sha256": item["sha256"], "bytes": item["bytes"]}
                      for logical, name in (("model_json", "model.json"), ("model_arrays", "arrays.npz"))
                      for item in self.context.model["files"] if item["path"] == name}
            query = self.context.manifest["products"]["queries_dev"]
            inputs["queries"] = {"path": str(self.context.preparation_root / query["path"]),
                                 "sha256": query["sha256"], "bytes": query["bytes"]}
            session.begin("setup", {"mode": "predict", "inputs": inputs})
            session.finish("setup", {"kind": "native_model_loaded"}, policy_fixtures.resources())
            session.begin("2", {"query": self.producer_query, "configuration": self.producer_configuration})
            normal = len(self.records) == 1 and self.records[0]["cell_id"] == "2"
            value = self.records[0] if normal else self.template_record
            record = session.finish("2", value["result"], value["resources"])
            receipt = session.finalize()
        if normal:
            self.records = [record]
        self.recipe["producer_session"] = {"path": str(producer), "receipt_sha256": receipt["sha256"]}
        path = self.root / "candidates.json"
        raw = canonical(self.records)
        path.write_bytes(raw)
        self.recipe["candidates"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        recipe = self.root / "checker-recipe.json"
        recipe.write_bytes(canonical(self.recipe))
        return recipe, self.root / "checks"

    def test_actual_policy_acceptance_replays_sources_without_inference(self):
        recipe, output = self.prepare()
        run(recipe, output)
        dispositions = parse_json((output / "dispositions.json").read_bytes())
        self.assertEqual(dispositions[0]["check_status"], "accepted")
        self.assertEqual(dispositions[0]["prediction"]["evidence"]["10"]["label"], "CONTRADICT")
        complete = parse_json((output / "COMPLETE.json").read_bytes())
        self.assertEqual(complete["policy_sha256"], self.context.policy_sha256)
        self.assertEqual(complete["candidate_input_sha256"], self.recipe["candidates"]["sha256"])
        self.assertIsNone(complete["setup_resources"]["model_input_tokens"])
        cell = parse_json(next((output / "session/cells").glob("*.json")).read_bytes())
        self.assertEqual(cell["result"]["envelope"]["resources"], self.records[0]["resources"])
        verification = parse_json((output / "verification.json").read_bytes())
        self.assertEqual(verification["terminal_cells"], 1)

    def test_bad_sentence_hash_is_retained_policy_rejection(self):
        self.records[0]["result"]["source_bindings"][0]["text_sha256"] = "f" * 64
        recipe, output = self.prepare()
        run(recipe, output)
        dispositions = parse_json((output / "dispositions.json").read_bytes())
        self.assertEqual(dispositions[0]["check_status"], "rejected")
        self.assertIn("sentence checksum", dispositions[0]["reason"])
        self.assertTrue((output / "verification.json").is_file())

    def test_candidate_hash_change_fails_before_case_dispatch(self):
        recipe, output = self.prepare()
        (self.root / "candidates.json").write_bytes(b"[]")
        with self.assertRaises(ContractError):
            run(recipe, output)
        self.assertFalse((output / "session").exists())
        self.assertTrue((output / "FAILED.json").is_file())

    def test_resealed_candidate_cannot_replace_original_producer_bytes(self):
        recipe, output = self.prepare()
        path = self.root / "candidates.json"
        changed = parse_json(path.read_bytes())
        changed[0]["result"]["prediction"]["evidence"]["10"]["label"] = "SUPPORT"
        raw = canonical(changed)
        path.write_bytes(raw)
        self.recipe["candidates"].update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        recipe.write_bytes(canonical(self.recipe))
        with self.assertRaisesRegex(ContractError, "original producer terminal"):
            run(recipe, output)
        self.assertFalse((output / "session").exists())

    def test_missing_duplicate_or_foreign_candidate_records_rejected(self):
        for name, records in (("missing", []), ("duplicate", self.records * 2),
                              ("foreign", [dict(self.records[0], cell_id="9")])):
            with self.subTest(name=name):
                self.records = records
                recipe, output = self.prepare()
                with self.assertRaisesRegex(ContractError, "identities/order"):
                    run(recipe, output.with_name(name))

    def test_wrong_configuration_or_policy_fails_before_case_dispatch(self):
        for field, value in (("policy_sha256", "f" * 64), ("configuration", {"k": 9})):
            original = self.recipe.get(field)
            self.recipe[field] = value
            recipe, output = self.prepare()
            with self.subTest(field=field), self.assertRaises(ContractError):
                run(recipe, output.with_name(field))
            self.assertFalse((output.with_name(field) / "session").exists())
            self.recipe[field] = original

    def test_original_producer_query_or_configuration_cannot_be_relabelled(self):
        for mode in ("claim_text", "configuration"):
            self.producer_query = dict(self.context.queries[2])
            self.producer_configuration = dict(self.context.model["configuration"])
            if mode == "claim_text":
                self.producer_query["claim"] = "A different fictional claim"
            else:
                self.producer_configuration["k"] = 99
            recipe, output = self.prepare()
            with self.subTest(mode=mode), self.assertRaisesRegex(ContractError, "Producer query/configuration"):
                run(recipe, output.with_name(mode))
            self.assertFalse((output.with_name(mode) / "session").exists())

    def test_unexpected_check_failure_preserves_attempt_without_retry(self):
        recipe, output = self.prepare()
        with patch("experiments.scifact.check_worker.verify_candidate", side_effect=RuntimeError("injected checker failure")) as check:
            with self.assertRaisesRegex(RuntimeError, "injected"):
                run(recipe, output)
        self.assertEqual(check.call_count, 1)
        self.assertEqual(inspect_session(output / "session")["attempted_cells"], ["2"])
        self.assertFalse((output / "COMPLETE.json").exists())
        self.assertEqual(parse_json((output / "FAILED.json").read_bytes())["active_cell"], "2")

    def test_existing_output_is_not_reused(self):
        recipe, output = self.prepare()
        output.mkdir()
        sentinel = output / "existing"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            run(recipe, output)
        self.assertEqual(sentinel.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
