"""Regressions for publication precision and execution-base preflight."""
import tempfile
import os
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import write_run
from tether_engine.chrono import EvidenceStore, load_snapshot, observation_exclusion
from tether_engine.contracts import Case, Category
from tether_engine.provenance import InputGraph
from tether_engine.serde import ContractError, decode, read_json
from tether_engine.workflow import run_workflow

FIXTURE = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class SpyBackend(ExtractiveBackend):
    def __init__(self):
        self.events = []

    def quote(self, request):
        self.events.append('quote')
        return super().quote(request)

    def prepare_request(self, request):
        self.events.append('prepare')
        return request, {}

    def select(self, request):
        self.events.append('select')
        return super().select(request)


class StoreTemporalHardeningTests(unittest.TestCase):
    def setUp(self):
        self.case = decode(Case, read_json(FIXTURE/'case.json'))
        self.store = load_snapshot(FIXTURE/'snapshot.json', self.case)
        self.records = tuple(r for category in Category for r in self.store.query(self.case, category))

    def direct(self, **kwargs):
        return EvidenceStore(self.store.snapshot, self.records, self.store.exclusions,
                             self.store.source_proofs, self.store.catalog_policy, **kwargs)

    def test_query_only_store_has_explicit_unbased_state(self):
        store = self.direct()
        self.assertIsNone(store.snapshot_base)
        self.assertEqual(store.query(self.case, Category.GENETICS), self.store.query(self.case, Category.GENETICS))

    def test_unbased_store_fails_before_backend_use(self):
        backend = SpyBackend()
        with self.assertRaisesRegex(ContractError, 'snapshot base'):
            run_workflow(self.case, self.direct(), backend)
        self.assertEqual(backend.events, [])

    def test_missing_directory_base_fails_before_backend_use(self):
        with tempfile.TemporaryDirectory() as temporary:
            backend = SpyBackend()
            with self.assertRaises(ContractError):
                run_workflow(self.case, self.direct(snapshot_base=Path(temporary)/'missing'), backend)
            self.assertEqual(backend.events, [])

    def test_explicit_based_store_executes_and_finalizes(self):
        store = self.direct(snapshot_base=FIXTURE)
        result = run_workflow(self.case, store, ExtractiveBackend())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'run'
            write_run(output, result, store, None)
            self.assertTrue((output/'receipt.json').is_file())

    def test_direct_finalization_without_base_fails_before_output(self):
        result = run_workflow(self.case, self.store, ExtractiveBackend())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'run'
            with self.assertRaisesRegex(ContractError, 'snapshot base'):
                write_run(output, result, self.direct(), None)
            self.assertFalse(output.exists())

    def test_explicit_relative_base_is_captured_as_absolute(self):
        store = self.direct(snapshot_base=Path(os.path.relpath(FIXTURE)))
        self.assertEqual(store.snapshot_base, FIXTURE.resolve())
        result = run_workflow(self.case, store, ExtractiveBackend())
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'run'
            write_run(output, result, store, None)
            self.assertTrue(Path(read_json(output/'inputs.json')['snapshot_base']).is_absolute())

    def publication(self, **values):
        observation = replace(self.records[0].observation, **values)
        graph = InputGraph(self.store.snapshot, FIXTURE, None)
        artifact = self.store.snapshot.artifacts[0]
        return observation_exclusion(observation, artifact, graph, self.case)

    def test_inconsistent_publication_date_and_year_excluded(self):
        self.assertEqual(self.publication(publication_date=date(self.case.origin.year-1, 1, 1),
                                          publication_year=self.case.origin.year),
                         'publication_metadata_inconsistent')

    def test_same_year_with_eligible_information_is_not_invented_leakage(self):
        self.assertIsNone(self.publication(publication_year=self.case.origin.year, publication_date=None))

    def test_explicit_future_date_or_year_excluded(self):
        self.assertEqual(self.publication(publication_date=date(self.case.origin.year+1, 1, 1),
                                          publication_year=None), 'publication_after_origin')
        self.assertEqual(self.publication(publication_year=self.case.origin.year+1, publication_date=None),
                         'publication_after_origin')

    def test_boolean_publication_year_is_contract_error(self):
        with self.assertRaises(ContractError):
            self.publication(publication_year=True, publication_date=None)

    def test_missing_publication_does_not_hide_eligible_context(self):
        self.assertIsNone(self.publication(publication_year=None, publication_date=None))

    def test_new_computation_can_use_older_eligible_information(self):
        unknown = replace(self.records[0].observation.availability, first_public_at=None,
                          release_public_at=None, record_public_at=None, annotation_public_at=None,
                          known_public_by=None, evidence_ref=None)
        self.assertIsNone(self.publication(source_kind='computed', computed_at=datetime(2090, 1, 1, tzinfo=timezone.utc),
                                          availability=unknown, publication_date=None, publication_year=None))


if __name__ == '__main__':
    unittest.main()
