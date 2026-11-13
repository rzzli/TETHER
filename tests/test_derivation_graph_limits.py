"""Bounded derivation input caching and truthful computed-node attribution."""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.contracts import Case, Snapshot
from tether_engine.provenance import InputGraph
from tether_engine.serde import ContractError, decode, read_json
from tests.derivation_fixtures import qualify_projection


FIXTURE = Path(__file__).resolve().parents[1] / "src/tether_engine/demo/v2"


class DerivationGraphLimitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name) / "fixture"
        shutil.copytree(FIXTURE, self.fixture)
        self.case = decode(Case, read_json(self.fixture / "case.json"))

    def graph_with_two_inputs(self):
        snapshot = decode(Snapshot, read_json(self.fixture / "snapshot.json"))
        first, second = b'{"value":1}', b'{"value":2}'
        nodes = []
        for index, payload in enumerate((first, second)):
            path = f"bounded-parent-{index}.json"
            (self.fixture / path).write_bytes(payload)
            nodes.append(replace(
                snapshot.sources[0], source_id=f"parent-{index}", path=path,
                sha256=hashlib.sha256(payload).hexdigest(),
            ))
        graph = InputGraph(replace(snapshot, sources=tuple(nodes)), self.fixture, None)
        return graph, first, second

    def test_distinct_parent_payloads_have_an_aggregate_cache_bound(self):
        graph, first, second = self.graph_with_two_inputs()
        with patch("tether_engine.provenance.MAX_DERIVATION_CACHE_BYTES",
                   len(first) + len(second) - 1):
            self.assertEqual(graph.payloads(("parent-0",), self.case)["parent-0"], first)
            # Repeated uses must reuse the cached payload, not consume the bound
            # twice or trigger an eviction/re-read cycle.
            self.assertEqual(graph.payloads(("parent-0",), self.case)["parent-0"], first)
            with self.assertRaisesRegex(ContractError, "Aggregate derivation input cache"):
                graph.payloads(("parent-1",), self.case)

    def test_exact_aggregate_boundary_allows_both_inputs(self):
        graph, first, second = self.graph_with_two_inputs()
        with patch("tether_engine.provenance.MAX_DERIVATION_CACHE_BYTES",
                   len(first) + len(second)):
            payloads = graph.payloads(("parent-0", "parent-1"), self.case)
            self.assertEqual(dict(payloads), {"parent-0": first, "parent-1": second})

    def test_per_input_bound_is_retained_independently_of_aggregate_bound(self):
        graph, first, _ = self.graph_with_two_inputs()
        with patch("tether_engine.provenance.MAX_NORMALIZED_JSON_BYTES", len(first) - 1):
            with self.assertRaisesRegex(ContractError, "64 MiB limit"):
                graph.payloads(("parent-0",), self.case)

    def test_computed_node_method_attribution_matches_registered_descriptor(self):
        observation = qualify_projection(self.fixture)
        snapshot = decode(Snapshot, read_json(self.fixture / "snapshot.json"))
        parent = snapshot.sources[0]
        recipe = replace(observation.derivation, output_schema="canonical_json.v1")
        node = replace(
            parent, source_id="computed-parent", path="not-opened-by-metadata.json",
            parents=(parent.source_id,), computed_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            method_id=recipe.method_id, method_version=recipe.method_version,
            derivation=recipe,
        )
        for changes in ({"method_id": "invented-method"}, {"method_version": "wrong-version"}):
            with self.subTest(changes=changes):
                forged = replace(node, **changes)
                graph = InputGraph(replace(snapshot, sources=snapshot.sources + (forged,)),
                                   self.fixture, None)
                with self.assertRaisesRegex(ContractError, "method identity"):
                    graph.exclusion((forged.source_id,), self.case)


if __name__ == "__main__":
    unittest.main()
