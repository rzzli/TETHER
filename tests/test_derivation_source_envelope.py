"""Projection cannot erase restrictions carried by its typed source envelope."""

from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest

from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Snapshot
from tether_engine.artifacts import verify_run, write_run
from tether_engine.agents import ExtractiveBackend
from tether_engine.serde import ContractError, decode, read_json, sha256_file, write_json
from tether_engine.workflow import run_workflow
from tests.derivation_fixtures import qualify_projection, reseal_observation
from tests.test_computed_derivations import SpyBackend


FIXTURE = Path(__file__).resolve().parents[1] / "src/tether_engine/demo/v2"


class DerivationSourceEnvelopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name) / "fixture"
        shutil.copytree(FIXTURE, self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))
        self.computed = qualify_projection(self.fixture)

    def change_source_envelope(self, **changes):
        snapshot_path = self.fixture / "snapshot.json"
        snapshot = decode(Snapshot, read_json(snapshot_path))
        source = snapshot.sources[0]
        raw = read_json(self.fixture / source.path)
        raw["observations"][0].update(changes)
        write_json(self.fixture / source.path, raw)
        source = replace(source, sha256=sha256_file(self.fixture / source.path))
        computed = replace(self.computed, derivation=replace(
            self.computed.derivation, inputs={source.source_id: source.sha256}
        ))
        reseal_observation(self.fixture, computed)
        snapshot = decode(Snapshot, read_json(snapshot_path))
        write_json(snapshot_path, replace(snapshot, sources=(source,) + snapshot.sources[1:]))

    def assert_rejected_before_actor(self):
        backend = SpyBackend()
        with self.assertRaises(ContractError):
            store = load_snapshot(self.fixture / "snapshot.json", self.case)
            run_workflow(self.case, store, backend)
        self.assertEqual(backend.events, [])

    def test_projection_cannot_erase_embedded_future_lineage(self):
        # The source itself declares this future ancestor. Replacing the output
        # envelope with a reference to its containing old file must not erase it.
        self.change_source_envelope(input_refs=["demo-future-input"])
        self.assert_rejected_before_actor()

    def test_projection_cannot_launder_clinical_features_as_computed(self):
        # Category/features are unchanged: source_kind carries the clinical
        # feature prohibition and must be validated before replacing it.
        self.change_source_envelope(source_kind="clinical")
        self.assert_rejected_before_actor()

    def test_projection_cannot_certify_an_unsupported_embedded_computation(self):
        self.change_source_envelope(
            source_kind="computed", computed_at="2090-01-01T00:00:00+00:00", derivation=None
        )
        self.assert_rejected_before_actor()

    def test_outputs_only_does_not_verify_a_primary_observations_computed_ancestor(self):
        snapshot_path = self.fixture / "snapshot.json"
        snapshot = decode(Snapshot, read_json(snapshot_path))
        original = snapshot.sources[0]
        projected = read_json(self.fixture / original.path)["observations"][0]
        node_path = self.fixture / "computed-parent.json"
        write_json(node_path, projected)
        recipe = replace(self.computed.derivation, output_schema="canonical_json.v1")
        node = replace(
            original, source_id="computed-parent", path=node_path.name,
            sha256=sha256_file(node_path), parents=(original.source_id,),
            computed_at=self.computed.computed_at, method_id=recipe.method_id,
            method_version=recipe.method_version, derivation=recipe,
        )
        observation = replace(self.computed, source_kind="primary", computed_at=None,
                              derivation=None, input_refs=(node.source_id,))
        write_json(snapshot_path, replace(
            snapshot, sources=snapshot.sources + (node,),
            artifacts=(replace(snapshot.artifacts[0], input_refs=(node.source_id,)),)
                      + snapshot.artifacts[1:],
        ))
        reseal_observation(self.fixture, observation)
        store = load_snapshot(snapshot_path, self.case)
        result = run_workflow(self.case, store, ExtractiveBackend())
        output = self.fixture.parent / "run"
        write_run(output, result, store, None)
        self.assertEqual(verify_run(output)["derivation_verification"], "verified")
        node_path.unlink()
        with self.assertRaises(ContractError):
            verify_run(output)
        limited = verify_run(output, verify_sources=False)
        self.assertEqual(limited["derivation_verification"], "not_checked_outputs_only")
        self.assertNotEqual(limited["semantic_consistency"], "verified")


if __name__ == "__main__":
    unittest.main()
