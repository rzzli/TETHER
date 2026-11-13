"""Computed evidence must be qualified before any of its content reaches an actor.

These regression-first tests deliberately avoid a proposed derivation API. The
fixtures exercise unsupported computations through the existing public entry
points. Separate positive tests will use the registered derivation contract.
"""

from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import shutil
import tempfile
import unittest

from tether_engine.agents import ExtractiveBackend
from tether_engine.chrono import EvidenceStore, load_snapshot
from tether_engine.contracts import Case, Category, EvidencePacket, Snapshot
from tether_engine.ledger import EvidenceLedger
from tether_engine.serde import (
    ContractError,
    canonical,
    decode,
    encode,
    fingerprint,
    freeze,
    read_json,
    sha256_file,
    write_json,
)
from tether_engine.workflow import run_workflow


FIXTURE = Path(__file__).resolve().parents[1] / "src/tether_engine/demo/v2"

# Captured from the unchanged v2 fixture before the RP02 contract migration.
# Dataclass defaults are part of its canonical form even when absent in JSON.
LEGACY_CANONICAL = {
    "case.json": (
        Case,
        "9af9a879ce374806d22d925fbbed94297396d9844b5852b530d6e276d51b05a8",
        "e340fac52c09697e5b658e033d976e2f16c22c065e6df7f0658bd6039c48bba1",
    ),
    "snapshot.json": (
        Snapshot,
        "d57871fbe5b7e273f66ae58ee66a1eb99dc0254d51c6011676fbabec707eff47",
        "3f68d3e5535ab73f89de749ff1ea37bca50b4c09535d5970904de35ba1775c6e",
    ),
    "evidence.json": (
        EvidencePacket,
        "734fc7288ccc1b87e49e5df5ed355c819e05942a95831d8044e8823432156972",
        "3f3ea281cbb4d084bc2fe3c3a76203ca8e8951ba37ce9414269d67a53526444f",
    ),
}


class SpyBackend(ExtractiveBackend):
    def __init__(self):
        self.events = []

    def prepare_request(self, request):
        self.events.append("prepare")
        return request, {}

    def quote(self, request):
        self.events.append("quote")
        return super().quote(request)

    def select(self, request):
        self.events.append("select")
        return super().select(request)


class ComputedDerivationRegressionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name) / "fixture"
        shutil.copytree(FIXTURE, self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))

    def store(self):
        return load_snapshot(self.fixture / "snapshot.json", self.case)

    @staticmethod
    def future_availability(availability):
        return replace(
            availability,
            first_public_at=date(2029, 1, 1),
            release_public_at=date(2029, 1, 1),
            record_public_at=date(2029, 1, 1),
            annotation_public_at=date(2029, 1, 1),
            retrieved_at=date(2030, 1, 1),
        )

    def unsupported_observation(self, observation, *, empty_features=False):
        changes = {
            "source_kind": "computed",
            "computed_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
            "availability": self.future_availability(observation.availability),
            "statement": "UNSUPPORTED_COMPUTED_CONTEXT_MUST_NOT_REACH_AN_ACTOR",
        }
        if empty_features:
            changes.update(features={}, feature_scope=None)
        return replace(observation, **changes)

    def replace_packet_observation(self, *, empty_features=False):
        path = self.fixture / "evidence.json"
        packet = decode(EvidencePacket, read_json(path))
        changed = self.unsupported_observation(
            packet.observations[0], empty_features=empty_features
        )
        packet = replace(packet, observations=(changed,) + packet.observations[1:])
        write_json(path, packet)
        snapshot_path = self.fixture / "snapshot.json"
        snapshot = read_json(snapshot_path)
        snapshot["artifacts"][0]["sha256"] = sha256_file(path)
        write_json(snapshot_path, snapshot)
        return changed.observation_id

    def assert_not_admitted(self, observation_id):
        try:
            store = self.store()
        except ContractError:
            return
        visible = {
            row.observation.observation_id
            for category in Category
            for row in store.query(self.case, category)
        }
        self.assertNotIn(
            observation_id, visible, "Unsupported computed content was admitted"
        )

    def forged_store(self):
        original = self.store()
        records = [
            row
            for category in Category
            for row in original.query(self.case, category)
        ]
        record = records[0]
        records[0] = replace(
            record, observation=self.unsupported_observation(record.observation)
        )
        store = EvidenceStore(
            original.snapshot,
            tuple(records),
            original.exclusions,
            original.source_proofs,
            original.catalog_policy,
            snapshot_base=self.fixture,
        )
        return store, records[0].observation

    def test_future_observation_cannot_be_admitted_by_relabelling_computed(self):
        self.assert_not_admitted(self.replace_packet_observation())

    def test_empty_features_do_not_make_unverified_computed_prose_safe(self):
        self.assert_not_admitted(
            self.replace_packet_observation(empty_features=True)
        )

    def test_computed_source_node_requires_a_qualified_derivation(self):
        path = self.fixture / "snapshot.json"
        snapshot = decode(Snapshot, read_json(path))
        original = snapshot.sources[0]
        eligible_parent = replace(original, source_id="old-eligible-parent")
        forged = replace(
            original,
            availability=self.future_availability(original.availability),
            parents=(eligible_parent.source_id,),
            computed_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            method_id="unsupported-projection",
            method_version="1",
        )
        write_json(
            path,
            replace(
                snapshot,
                sources=(forged, eligible_parent) + snapshot.sources[1:],
            ),
        )
        self.assert_not_admitted("demo-genetics-1")

    def test_direct_store_is_rejected_before_request_preparation_or_backend_calls(self):
        store, _ = self.forged_store()
        backend = SpyBackend()
        rejected = False
        try:
            run_workflow(self.case, store, backend)
        except ContractError:
            rejected = True
        self.assertEqual(backend.events, [], "Actor accessed an unqualified store")
        self.assertTrue(rejected, "A directly forged execution store was accepted")

    def test_query_cache_cannot_expose_content_different_from_admitted_records(self):
        store = self.store()
        index = dict(store._query_index)
        key = next(iter(index))
        original = index[key][0]
        replacement = replace(
            original,
            observation=self.unsupported_observation(original.observation, empty_features=True),
        )
        index[key] = (replacement,) + tuple(index[key][1:])
        store._query_index = freeze(index)
        backend = SpyBackend()
        rejected = False
        try:
            run_workflow(self.case, store, backend)
        except ContractError:
            rejected = True
        self.assertEqual(backend.events, [], "Actor accessed inconsistent cached evidence")
        self.assertTrue(rejected, "Execution accepted a query cache inconsistent with its source records")

    def test_ledger_cannot_append_an_unsupported_computed_observation(self):
        store, observation = self.forged_store()
        ledger = EvidenceLedger(self.case, store)
        with self.assertRaises(ContractError):
            ledger.append(observation.category, observation.observation_id)

    def test_legacy_v2_fixture_bytes_and_canonical_objects_are_unchanged(self):
        for name, (kind, byte_digest, canonical_digest) in LEGACY_CANONICAL.items():
            with self.subTest(fixture=name):
                path = FIXTURE / name
                self.assertEqual(sha256_file(path), byte_digest)
                decoded = decode(kind, read_json(path))
                self.assertEqual(fingerprint(decoded), canonical_digest)
                self.assertEqual(
                    canonical(decode(kind, encode(decoded))), canonical(decoded)
                )


if __name__ == "__main__":
    unittest.main()
