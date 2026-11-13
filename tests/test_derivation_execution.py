"""Strict derivation is replayed before actors and when results are verified."""

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from datetime import date
import io
from pathlib import Path
import shutil
import tempfile
import unittest

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.cli import main
from tether_engine.contracts import Case, Category, Snapshot
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, decode, fingerprint, read_json, sha256_file, write_json
from tether_engine.workflow import run_workflow
from tests.derivation_fixtures import qualify_projection, reseal_observation


FIXTURE = Path(__file__).resolve().parents[1] / "src/tether_engine/demo/v2"


class DerivationExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = self.root / "fixture"
        shutil.copytree(FIXTURE, self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))
        self.model = decode(ScorerArtifact, read_json(self.fixture / "scorer.json"))
        self.computed = qualify_projection(self.fixture)

    def store(self):
        return load_snapshot(self.fixture / "snapshot.json", self.case)

    def execute(self):
        store = self.store()
        result = run_workflow(self.case, store, ExtractiveBackend(), self.model)
        output = self.root / "run"
        write_run(output, result, store, self.model)
        return result, output

    def test_new_computation_on_old_information_executes_and_verifies(self):
        result, output = self.execute()
        self.assertEqual(result.features.values["genetic_support"].value, 0.8)
        self.assertEqual(result.configuration["admission_policy"], "tether.derivation.v1")
        verification = verify_run(output)
        self.assertEqual(verification["semantic_consistency"], "verified")
        self.assertNotIn("unavailable", verification["derivation_verification"])

    def test_resealed_changes_to_each_information_field_are_rejected(self):
        variants = {
            "text": replace(self.computed, statement="Fabricated future result"),
            "context": replace(self.computed, context=replace(self.computed.context, tissue="invented tissue")),
            "feature": replace(self.computed, features={"genetic_support": 0.1}),
            "quantity": replace(self.computed, quantitative=replace(self.computed.quantitative, effect=0.123)),
            "scope": replace(self.computed, feature_scope="different-hypothesis"),
            "programme": replace(self.computed, program_id="unrelated-programme"),
            "method_prose": replace(self.computed, method=replace(self.computed.method, limitations=("future result",))),
            "availability": replace(self.computed, availability=replace(
                self.computed.availability, record_public_at=date(2020, 1, 1))),
        }
        for field, forged in variants.items():
            with self.subTest(field=field):
                reseal_observation(self.fixture, forged)
                with self.assertRaises(ContractError):
                    self.store()
        reseal_observation(self.fixture, self.computed)

    def test_wrong_method_and_binding_are_rejected(self):
        recipe = self.computed.derivation
        for forged in (replace(recipe, method_id="arbitrary-python"),
                       replace(recipe, method_version="999"),
                       replace(recipe, implementation_sha256="0" * 64),
                       replace(recipe, parameters_sha256="0" * 64),
                       replace(recipe, output_schema="free_text"),
                       replace(recipe, inputs={"demo-original-input": "0" * 64})):
            with self.subTest(recipe=forged):
                reseal_observation(self.fixture, replace(self.computed, derivation=forged))
                with self.assertRaises(ContractError):
                    self.store()

    def test_historical_method_mode_rejects_new_method_at_old_origin(self):
        recipe = replace(self.computed.derivation, mode="historical_method_simulation")
        reseal_observation(self.fixture, replace(self.computed, derivation=recipe))
        with self.assertRaises(ContractError):
            self.store()

    def test_future_input_excludes_computed_content(self):
        path = self.fixture / "snapshot.json"
        snapshot = decode(Snapshot, read_json(path))
        source = snapshot.sources[0]
        source = replace(source, availability=replace(source.availability,
                         annotation_public_at=date(2024, 1, 1)))
        write_json(path, replace(snapshot, sources=(source,) + snapshot.sources[1:]))
        self.assertEqual(self.store().query(self.case, Category.GENETICS), ())

    def test_source_change_after_admission_fails_finalization(self):
        store = self.store()
        result = run_workflow(self.case, store, ExtractiveBackend(), self.model)
        (self.fixture / "raw-inputs.json").write_text('{}\n', encoding="utf-8")
        with self.assertRaises(ContractError):
            write_run(self.root / "run", result, store, self.model)

    def test_computed_ancestor_is_rederived_even_after_every_hash_is_updated(self):
        snapshot_path = self.fixture / "snapshot.json"
        snapshot = decode(Snapshot, read_json(snapshot_path))
        original = snapshot.sources[0]
        projected = read_json(self.fixture / original.path)["observations"][0]
        node_path = self.fixture / "computed-source.json"
        write_json(node_path, projected)
        node_recipe = replace(self.computed.derivation, output_schema="canonical_json.v1")
        node = replace(original, source_id="computed-input", path=node_path.name,
                       sha256=sha256_file(node_path), parents=(original.source_id,),
                       computed_at=self.computed.computed_at,
                       method_id=node_recipe.method_id, method_version=node_recipe.method_version,
                       derivation=node_recipe)
        parameters = {"input": node.source_id, "pointer": ""}
        recipe = replace(self.computed.derivation, parameters=parameters,
                         parameters_sha256=fingerprint(parameters), inputs={node.source_id: node.sha256})
        computed = replace(self.computed, input_refs=(node.source_id,), derivation=recipe)
        write_json(snapshot_path, replace(snapshot, sources=snapshot.sources + (node,),
                   artifacts=(replace(snapshot.artifacts[0], input_refs=(node.source_id,)),)
                             + snapshot.artifacts[1:]))
        reseal_observation(self.fixture, computed)
        self.assertEqual(self.store().lookup(computed.observation_id).observation, computed)

        projected["statement"] = "Forged intermediate result with resealed hashes"
        write_json(node_path, projected)
        node = replace(node, sha256=sha256_file(node_path))
        snapshot = decode(Snapshot, read_json(snapshot_path))
        write_json(snapshot_path, replace(snapshot, sources=snapshot.sources[:-1] + (node,)))
        computed = replace(computed, statement=projected["statement"], derivation=replace(
            recipe, inputs={node.source_id: node.sha256}))
        reseal_observation(self.fixture, computed)
        with self.assertRaises(ContractError):
            self.store()

    def test_information_assets_are_eligible_even_when_not_selected_by_pointer(self):
        snapshot_path = self.fixture / "snapshot.json"
        snapshot = decode(Snapshot, read_json(snapshot_path))
        original = snapshot.sources[0]
        asset_path = self.fixture / "mapping.json"
        write_json(asset_path, {"mapping": "fictional"})
        asset = replace(original, source_id="mapping-asset", path=asset_path.name,
                        sha256=sha256_file(asset_path), role="reference")
        recipe = replace(self.computed.derivation, assets={asset.source_id: asset.sha256})
        computed = replace(self.computed, input_refs=(original.source_id, asset.source_id),
                           derivation=recipe)
        write_json(snapshot_path, replace(snapshot, sources=snapshot.sources + (asset,),
                   artifacts=(replace(snapshot.artifacts[0], input_refs=computed.input_refs),)
                             + snapshot.artifacts[1:]))
        reseal_observation(self.fixture, computed)
        self.assertEqual(self.store().lookup(computed.observation_id).observation, computed)
        snapshot = decode(Snapshot, read_json(snapshot_path))
        future = replace(asset, availability=replace(asset.availability,
                                                    annotation_public_at=date(2024, 1, 1)))
        write_json(snapshot_path, replace(snapshot, sources=snapshot.sources[:-1] + (future,)))
        self.assertEqual(self.store().query(self.case, Category.GENETICS), ())

    def test_outputs_only_does_not_claim_derivation_replay(self):
        _, output = self.execute()
        (self.fixture / "raw-inputs.json").write_text('{}\n', encoding="utf-8")
        with self.assertRaises(ContractError):
            verify_run(output)
        limited = verify_run(output, verify_sources=False)
        self.assertEqual(limited["derivation_verification"], "not_checked_outputs_only")
        self.assertNotEqual(limited["semantic_consistency"], "verified")

    def test_cli_executes_registered_projection_and_refuses_changed_parent(self):
        output = self.root / "cli-run"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = main(["run", "--case", str(self.fixture / "case.json"),
                           "--snapshot", str(self.fixture / "snapshot.json"),
                           "--output", str(output)])
        self.assertEqual(status, 0)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["verify", "--run-dir", str(output)]), 0)
        (self.fixture / "raw-inputs.json").write_text('{}\n', encoding="utf-8")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertNotEqual(main(["verify", "--run-dir", str(output)]), 0)


if __name__ == "__main__":
    unittest.main()
