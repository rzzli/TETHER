"""Closed derivations bind complete outputs to eligible, exact parent bytes."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import unittest

from tether_engine.contracts import Derivation, Observation, SourceNode
from tether_engine.derivations import (
    POLICY, information_payload, project, registry_entry,
    validate_descriptor, verify_observation,
)
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint, read_json


ROOT = Path(__file__).resolve().parents[1]


class DerivationRegistryTests(unittest.TestCase):
    def setUp(self):
        fixture = ROOT / "src/tether_engine/demo/v2"
        self.original = decode(Observation, read_json(fixture / "evidence.json")["observations"][0])
        self.node = decode(SourceNode, read_json(fixture / "snapshot.json")["sources"][0])
        self.payload = canonical({"observations": [replace(self.original, input_refs=("parent",))]})
        self.parent = replace(self.node, source_id="parent", sha256=hashlib.sha256(self.payload).hexdigest())
        self.parameters = {"input": "parent", "pointer": "/observations/0"}
        registered = registry_entry()
        self.recipe = Derivation(
            schema_version=1, method_id="tether.json_projection", method_version="1",
            implementation_sha256=registered["implementation_sha256"],
            parameters_sha256=fingerprint(self.parameters), parameters=self.parameters,
            inputs={"parent": self.parent.sha256}, assets={}, output_schema="observation.v2",
            method_available_at=registered["method_available_at"],
            mode="contemporary_method_retrospective",
        )
        self.cutoff = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.result = replace(self.original, source_kind="computed", computed_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
                              input_refs=("parent",), derivation=self.recipe)

    def test_registry_has_only_the_qualified_method(self):
        self.assertEqual(POLICY, "tether.derivation.v1")
        self.assertEqual(registry_entry()["method_available_at"], datetime(2026, 11, 13, 7, 48, 48, tzinfo=timezone.utc))
        self.assertEqual(registry_entry()["availability_basis"],
                         "local_source_registration_not_authenticated_public_release")
        for method, version in (("arbitrary.python", "1"), ("tether.json_projection", "2")):
            with self.subTest(method=method, version=version), self.assertRaises(ContractError):
                registry_entry(method, version)

    def test_late_deterministic_projection_preserves_complete_old_information(self):
        validate_descriptor(self.recipe, ("parent",), {"parent": self.parent}, self.cutoff)
        verify_observation(self.result, self.recipe, {"parent": self.payload})
        self.assertEqual(canonical(information_payload(self.result)), canonical(information_payload(self.original)))

    def test_historical_method_mode_requires_registered_method_availability(self):
        recipe = replace(self.recipe, mode="historical_method_simulation")
        with self.assertRaisesRegex(ContractError, "method.*cutoff|method.*origin"):
            validate_descriptor(recipe, ("parent",), {"parent": self.parent}, self.cutoff)
        validate_descriptor(recipe, ("parent",), {"parent": self.parent}, datetime(2027, 1, 1, tzinfo=timezone.utc))

    def test_submitted_identity_dates_and_parameters_cannot_override_registry(self):
        changes = (
            {"implementation_sha256": "0" * 64}, {"parameters_sha256": "0" * 64},
            {"method_available_at": self.cutoff}, {"schema_version": 2},
            {"mode": "legacy"}, {"output_schema": "arbitrary"},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ContractError):
                validate_descriptor(replace(self.recipe, **change), ("parent",), {"parent": self.parent}, self.cutoff)

    def test_parameters_cannot_supply_replacement_information(self):
        parameters = dict(self.parameters, statement="future information")
        recipe = replace(self.recipe, parameters=parameters, parameters_sha256=fingerprint(parameters))
        with self.assertRaises(ContractError):
            project(recipe, {"parent": self.payload})

    def test_missing_or_mismatched_parent_and_assets_fail_closed(self):
        asset_bytes = b'{"annotation":"eligible"}'
        asset = replace(self.parent, source_id="asset", sha256=hashlib.sha256(asset_bytes).hexdigest())
        recipe = replace(self.recipe, assets={"asset": asset.sha256})
        validate_descriptor(recipe, ("parent", "asset"), {"parent": self.parent, "asset": asset}, self.cutoff)
        with self.assertRaises(ContractError):
            project(recipe, {"parent": self.payload})
        with self.assertRaises(ContractError):
            project(recipe, {"parent": self.payload, "asset": b"changed"})
        with self.assertRaises(ContractError):
            validate_descriptor(recipe, ("parent",), {"parent": self.parent, "asset": asset}, self.cutoff)
        with self.assertRaises(ContractError):
            validate_descriptor(self.recipe, ("parent",), {"parent": replace(self.parent, sha256="0" * 64)}, self.cutoff)
        project(recipe, {"parent": self.payload, "asset": asset_bytes})

    def test_forged_whole_output_fields_are_detected(self):
        mutations = (
            {"statement": "The future trial succeeded."}, {"observation_id": "substitute"},
            {"target_id": "OTHER"}, {"features": {"genetic_support": 0.9}},
            {"context": replace(self.original.context, tissue="other")},
            {"method": replace(self.original.method, parameters={"future": "annotation"})},
            {"availability": replace(self.original.availability, record_public_at=datetime(2029, 1, 1).date())},
            {"source_metrics": {"future_score": 1}}, {"missingness": {"hidden": "changed"}},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                verify_observation(replace(self.result, **mutation), self.recipe, {"parent": self.payload})

    def test_source_observation_unknown_fields_are_not_silently_dropped(self):
        original = encode(self.original)
        original["unregistered_field"] = "hidden information"
        payload = canonical({"observations": [original]})
        recipe = replace(self.recipe, inputs={"parent": hashlib.sha256(payload).hexdigest()})
        with self.assertRaisesRegex(ContractError, "unknown fields"):
            verify_observation(replace(self.result, derivation=recipe), recipe, {"parent": payload})

    def test_source_policy_envelope_cannot_be_laundered_by_projection(self):
        for changes in (
            {"input_refs": ("future-source",)}, {"source_kind": "clinical"},
            {"source_kind": "computed", "computed_at": datetime(2030, 1, 1, tzinfo=timezone.utc)},
            {"derivation": self.recipe},
            {"computed_at": datetime(2030, 1, 1, tzinfo=timezone.utc)},
        ):
            source = replace(self.original, input_refs=("parent",), **changes) if "input_refs" not in changes else replace(self.original, **changes)
            payload = canonical({"observations": [source]})
            recipe = replace(self.recipe, inputs={"parent": hashlib.sha256(payload).hexdigest()})
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                verify_observation(replace(self.result, derivation=recipe), recipe, {"parent": payload})

    def test_projection_pointer_is_strict_and_supports_escaped_members(self):
        payload = b'{"a/b":{"~":[3,4]}}'
        parameters = {"input": "parent", "pointer": "/a~1b/~0/1"}
        recipe = replace(self.recipe, output_schema="canonical_json.v1", parameters=parameters,
                         parameters_sha256=fingerprint(parameters), inputs={"parent": hashlib.sha256(payload).hexdigest()})
        self.assertEqual(project(recipe, {"parent": payload}), 4)
        for pointer in ("a", "/a~2b", "/a~1b/~0/01", "/a~1b/~0/-", "/missing"):
            parameters = {"input": "parent", "pointer": pointer}
            with self.subTest(pointer=pointer), self.assertRaises(ContractError):
                project(replace(recipe, parameters=parameters, parameters_sha256=fingerprint(parameters)), {"parent": payload})

    def test_parent_bytes_are_rehashed_and_json_is_strict(self):
        with self.assertRaises(ContractError):
            project(self.recipe, {"parent": self.payload + b" "})
        for payload in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[] trailing'):
            parameters = {"input": "parent", "pointer": ""}
            recipe = replace(self.recipe, parameters=parameters, parameters_sha256=fingerprint(parameters),
                             inputs={"parent": hashlib.sha256(payload).hexdigest()})
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                project(recipe, {"parent": payload})

    def test_projection_depth_and_array_index_bounds_fail_as_contract_errors(self):
        for payload, pointer in ((b'{"x":[1]}', "/x/" + "9" * 1000),
                                 (b"[" * 1100 + b"0" + b"]" * 1100, "")):
            parameters = {"input": "parent", "pointer": pointer}
            recipe = replace(self.recipe, parameters=parameters, parameters_sha256=fingerprint(parameters),
                             inputs={"parent": hashlib.sha256(payload).hexdigest()})
            with self.subTest(pointer=pointer[:20]), self.assertRaises(ContractError):
                project(recipe, {"parent": payload})

    def test_recipe_and_projected_data_are_copied_and_frozen(self):
        self.parameters["pointer"] = "/changed"
        self.assertEqual(self.recipe.parameters["pointer"], "/observations/0")
        with self.assertRaises(TypeError):
            self.recipe.inputs["parent"] = "0" * 64
        projected = project(self.recipe, {"parent": self.payload})
        with self.assertRaises(TypeError):
            projected["context"]["tissue"] = "changed"

    def test_legacy_encoding_and_fingerprints_are_unchanged(self):
        self.assertNotIn("derivation", encode(self.original))
        self.assertNotIn("derivation", encode(self.node))
        self.assertEqual(fingerprint(self.original), "eedc2410b14422416c9fd8e574dcb96e9e00e52f6ffa57ac2b8fe8254b08e463")
        self.assertEqual(fingerprint(self.node), "ecb597fbf1b2b7a9618f94edae30b9d2cafe914f6bc64870cbd1febf3e472e24")
        self.assertIn("derivation", encode(self.result))

    def test_only_explicitly_marked_null_fields_are_omitted(self):
        @dataclass
        class Sample:
            ordinary: str | None = None
            extension: str | None = field(default=None, metadata={"omit_if_none": True})
        self.assertEqual(encode(Sample()), {"ordinary": None})
        self.assertEqual(encode(Sample(extension="v")), {"ordinary": None, "extension": "v"})


if __name__ == "__main__":
    unittest.main()
