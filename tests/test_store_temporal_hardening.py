"""Regressions for publication precision and execution-base preflight."""
import tempfile
import os
import shutil
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import EvidenceStore, load_snapshot, observation_exclusion, publication_exclusion
from tether_engine.contracts import Case, Category, FEATURE_CATEGORIES, Profile, TemporalClass
from tether_engine.derivations import registry_entry
from tether_engine.journal import RunJournal
from tether_engine.provenance import InputGraph
from tether_engine.serde import ContractError, canonical, decode, fingerprint, read_json, sha256_file, write_json
from tether_engine.workflow import run_workflow
from tests.derivation_fixtures import qualify_projection

FIXTURE = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class SpyBackend(ExtractiveBackend):
    def __init__(self):
        self.events = []
        self.requests = []

    def quote(self, request):
        self.events.append('quote')
        self.requests.append(request)
        return super().quote(request)

    def prepare_request(self, request):
        self.events.append('prepare')
        return request, {'selected_ids': [item.observation_id for item in request.evidence]}

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

    def test_overlapping_publication_year_is_unresolved_not_known_future(self):
        self.assertEqual(self.publication(publication_year=self.case.origin.year, publication_date=None),
                         'publication_timing_unresolved')

    def test_publication_day_cannot_supply_intraday_precision(self):
        case = replace(self.case, origin_at=datetime(2023, 1, 1, 12, tzinfo=timezone.utc))
        observation = replace(self.records[0].observation, publication_date=case.origin,
                              publication_year=case.origin.year)
        self.assertEqual(publication_exclusion(observation, case), 'publication_timing_unresolved')
        self.assertIsNone(publication_exclusion(observation, self.case))

    def test_precise_publication_date_takes_precedence_over_consistent_year(self):
        case = replace(self.case, origin=date(2023, 6, 1), origin_at=None)
        observation = replace(self.records[0].observation, publication_date=date(2023, 1, 1),
                              publication_year=2023)
        self.assertIsNone(publication_exclusion(observation, case))
        self.assertIsNone(self.publication(publication_year=2022, publication_date=None))
        end_year = replace(self.case, origin=date(2023, 12, 31), origin_at=None)
        self.assertIsNone(publication_exclusion(replace(observation, publication_date=None), end_year))

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
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / 'fixture'
            shutil.copytree(FIXTURE, fixture)
            computed = qualify_projection(fixture)
            store = load_snapshot(fixture / 'snapshot.json', self.case)
            self.assertGreater(computed.computed_at, self.case.cutoff)
            self.assertEqual(store.lookup(computed.observation_id).observation, computed)

    def test_future_artifact_information_is_excluded_before_packet_read(self):
        from unittest.mock import patch
        from tether_engine.chrono import admit_snapshot
        artifact = self.store.snapshot.artifacts[0]
        future = date(self.case.origin.year + 1, 1, 1)
        availability = replace(artifact.availability, first_public_at=future,
                               release_public_at=future, record_public_at=future,
                               annotation_public_at=future, retrieved_at=future)
        snapshot = replace(self.store.snapshot, artifacts=(replace(artifact, availability=availability),))
        original_open = Path.open

        def guarded(path, *args, **kwargs):
            if path == FIXTURE / artifact.path:
                raise AssertionError('Future packet was opened')
            return original_open(path, *args, **kwargs)

        with patch.object(Path, 'open', guarded):
            store = admit_snapshot(snapshot, self.case, FIXTURE)
        self.assertFalse(any(store.query(self.case, category) for category in Category))
        self.assertEqual([(e.item_id, e.reason) for e in store.exclusions],
                         [(artifact.artifact_id, 'available_after_origin')])
        from tether_engine.chrono import required_source_proofs
        self.assertEqual(required_source_proofs(snapshot, self.case, FIXTURE), ())

    def test_unverified_artifact_cannot_inherit_verified_parent_status(self):
        from tether_engine.chrono import admit_snapshot
        artifact = replace(self.store.snapshot.artifacts[0], temporal_classification=TemporalClass.UNVERIFIED)
        snapshot = replace(self.store.snapshot, artifacts=(artifact,))
        store = admit_snapshot(snapshot, self.case, FIXTURE)
        self.assertFalse(any(store.query(self.case, category) for category in Category))
        self.assertEqual(store.exclusions[0].reason, 'temporal_classification_unverified')
        graph = InputGraph(snapshot, FIXTURE, None)
        self.assertEqual(observation_exclusion(self.records[0].observation, artifact, graph, self.case),
                         'temporal_classification_unverified')

    def test_historical_artifact_classification_uses_the_lineage_policy(self):
        from tether_engine.chrono import eligible_artifacts
        for classification, allowed, expected in (
            (TemporalClass.HISTORICAL, False, None),
            (TemporalClass.CONTEMPORARY, False, 'not_verified_historical'),
            (TemporalClass.RECONSTRUCTED, False, 'reconstructed_history_not_approved'),
            (TemporalClass.RECONSTRUCTED, True, None),
        ):
            with self.subTest(classification=classification, allow_reconstructed=allowed):
                artifact = replace(self.store.snapshot.artifacts[0], temporal_classification=classification)
                snapshot = replace(self.store.snapshot, artifacts=(artifact,), profile=Profile.HISTORICAL,
                                   allow_reconstructed=allowed)
                graph = InputGraph(snapshot, FIXTURE, None)
                self.assertEqual(list(eligible_artifacts(snapshot, graph, self.case)), [(artifact, expected)])

    def test_every_category_withholds_future_content_from_all_actor_surfaces(self):
        # Fictional packet fixtures test temporal enforcement, not biological validity.
        # A positive record in every category prevents a reject-all implementation
        # from passing. Both annotation clocks and transitive ancestors are covered.
        for mode in ('annotation', 'ancestor', 'publication'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                snapshot = read_json(FIXTURE / 'snapshot.json')
                snapshot['artifacts'] = snapshot['artifacts'][:1]
                snapshot['sources'] = snapshot['sources'][:1]
                source = snapshot['sources'][0]
                source['path'] = 'original.json'
                template = read_json(FIXTURE / 'evidence.json')['observations'][0]
                good, withheld = [], []
                for category in Category:
                    item = deepcopy(template)
                    item.update(observation_id='eligible-' + category.value, category=category.value,
                                statement='ELIGIBLE_CONTENT_' + category.value, features={})
                    item['source_locator'] = {'source_id': source['source_id'],
                                              'fixture_observation_id': item['observation_id']}
                    good.append(item)
                    bad = deepcopy(item)
                    bad.update(observation_id='withheld-' + category.value,
                               statement='WITHHELD_CONTENT_' + category.value,
                               features={key: 1.0 for key, value in FEATURE_CATEGORIES.items()
                                         if value == category})
                    if mode == 'annotation':
                        bad['availability']['annotation_public_at'] = '2025-01-01'
                    elif mode == 'publication':
                        bad['publication_date'] = '2025-01-01'
                    else:
                        bad['input_refs'] = ['eligible-parent-of-future']
                    withheld.append(bad)
                write_json(root / source['path'], {'fictional_records': good + withheld})
                source['sha256'] = sha256_file(root / source['path'])
                artifact = snapshot['artifacts'][0]
                artifact['path'] = 'packet.json'
                write_json(root / artifact['path'], {'schema_version': 2,
                           'observations': good if mode == 'ancestor' else good + withheld})
                artifact['sha256'] = sha256_file(root / artifact['path'])
                if mode == 'ancestor':
                    future = deepcopy(source)
                    future.update(source_id='future-annotation')
                    future['availability']['annotation_public_at'] = '2025-01-01'
                    parent = deepcopy(source)
                    registered = registry_entry()
                    parameters = {'input': 'future-annotation', 'pointer': ''}
                    parent.update(source_id='eligible-parent-of-future', parents=['future-annotation'],
                                  computed_at='2030-01-01T00:00:00Z',
                                  method_id='tether.json_projection', method_version='1',
                                  derivation={'schema_version': 1, 'method_id': 'tether.json_projection',
                                              'method_version': '1',
                                              'implementation_sha256': registered['implementation_sha256'],
                                              'parameters': parameters, 'parameters_sha256': fingerprint(parameters),
                                              'inputs': {'future-annotation': future['sha256']}, 'assets': {},
                                              'output_schema': 'canonical_json.v1',
                                              'method_available_at': registered['method_available_at'],
                                              'mode': 'contemporary_method_retrospective'})
                    snapshot['sources'].extend([future, parent])
                    late_packet = deepcopy(artifact)
                    late_packet.update(artifact_id='ancestor-packet', path='ancestor-packet.json',
                                       input_refs=['eligible-parent-of-future'])
                    write_json(root / late_packet['path'], {'schema_version': 2, 'observations': withheld})
                    late_packet['sha256'] = sha256_file(root / late_packet['path'])
                    snapshot['artifacts'].append(late_packet)
                write_json(root / 'snapshot.json', snapshot)
                store = load_snapshot(root / 'snapshot.json', self.case)
                for category in Category:
                    self.assertEqual([r.observation.observation_id for r in store.query(self.case, category)],
                                     ['eligible-' + category.value])
                reasons = {e.reason for e in store.exclusions}
                self.assertEqual(reasons, {'publication_after_origin' if mode == 'publication'
                                          else 'available_after_origin'})
                backend = SpyBackend()
                journal = RunJournal(root / 'run')
                try:
                    result = run_workflow(self.case, store, backend, journal=journal)
                    anchor = write_run(root / 'run', result, store, None, journal)
                finally:
                    journal.close()
                self.assertEqual({claim.evidence.observation.observation_id for claim in result.claims},
                                 {item['observation_id'] for item in good})
                self.assertTrue(all(feature.value is None for feature in result.features.values.values()))
                for category in Category:
                    marker = ('WITHHELD_CONTENT_' + category.value).encode()
                    self.assertNotIn(marker, canonical(backend.requests))
                    self.assertNotIn(marker, canonical(result))
                    for filename in ('journal.jsonl', 'trace.jsonl', 'ledger.json', 'features.json', 'dossier.md'):
                        self.assertNotIn(marker, (root / 'run' / filename).read_bytes())
                self.assertEqual(verify_run(root / 'run', anchor)['assurance'], 'source_inclusive_semantics')


if __name__ == '__main__':
    unittest.main()
