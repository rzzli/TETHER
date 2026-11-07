"""Invented evaluator controls; no released questions, keys or native calls.

Authority unit tests explicitly mock capability issuance. They qualify ordering
and byte bindings only; the independent reader owns actual execution issuance.
"""
import copy
import inspect
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode, freeze
from experiments.labbench.evaluate import evaluate_schedule
from experiments.litqa_analysis.test_scoring import fixture, failure
from . import evaluation as e


def values(size=6):
    queries, references, baseline, offered = fixture(size)
    repair = copy.deepcopy(baseline)
    removal = copy.deepcopy(baseline)
    for row in removal:
        row['prediction'] = dict(answer_index=2, evidence_ids=[])
    ids = [q['id'] for q in queries]
    sources = [dict(id=key, retained_dois=[], pool_dois=[], selected_dois=[],
        original_retained_dois=[], original_pool_dois=[], original_selected_dois=[],
        source_context_changed=False, refinement_available=False) for key in ids]
    report = dict(purpose='production' if size == 199 else 'fictional_qualification', queries=queries,
        records=dict(one_pass=baseline, repair=repair, removal=removal),
        evidence_ids=dict(one_pass=offered, repair=offered, removal={key: [] for key in ids}),
        critics=[dict(id=key, native_status='completed', decoded=dict(support='insufficient')) for key in ids],
        source_cases=sources, case_products=[dict(id=key, provenance='invented new cells') for key in ids],
        method_identity='a' * 64,
        incremental_resources=dict(scope='new calls only', measured_input_tokens=60, measured_output_tokens=12),
        logical_resources=dict(scope='overlapping attribution; historical critic plus new model'))
    inputs = dict(kind=e.FICTIONAL_INPUT_KIND, role='evaluation_only', queries=queries,
        references=references, groups=[[key] for key in ids], annotations={key: [] for key in ids})
    if size == 199:
        inputs['groups'] = [[key] for key in ids[:176]]
        inputs['groups'] += [ids[i:i + 2] for i in range(176, 190, 2)]
        inputs['groups'] += [ids[i:i + 3] for i in range(190, 199, 3)]
    return report, inputs


def independent_interval(ids, left, right, groups):
    """Direct case-list resampling; independent of the production sampler."""
    index = {key: i for i, key in enumerate(ids)}
    rng = random.Random(20261106)
    samples = []
    for _ in range(10000):
        selected = [key for _ in groups for key in groups[rng.randrange(len(groups))]]
        a = sum(left[index[key]] for key in selected) / len(selected)
        b = sum(right[index[key]] for key in selected) / len(selected)
        samples.append(b - a)
    samples.sort()
    def percentile(p):
        position = (len(samples) - 1) * p
        lo = int(position); hi = min(lo + 1, len(samples) - 1)
        return samples[lo] + (samples[hi] - samples[lo]) * (position - lo)
    return [percentile(.025), percentile(.975)]


class EvidenceFirstScoringTests(unittest.TestCase):
    def test_full_199_186_has_14_fixed_intervals_and_no_old_failure_override(self):
        report, inputs = values(199)
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        self.assertEqual(result['scheduled_count'], 199)
        self.assertEqual(result['publication_component_count'], 186)
        self.assertEqual(result['native']['repair']['counts']['raw_correct'], 199)
        self.assertTrue(result['native']['repair']['case_results'][184]['raw_correct'])
        intervals = [item for endpoints in result['primary_contrasts'].values()
                     for estimates in endpoints.values() for item in estimates.values()]
        intervals += list(result['removal_diagnostic']['raw_accuracy_removal_minus_repair'].values())
        self.assertEqual(len(intervals), 14)
        self.assertTrue(all(row['seed'] == 20261106 and row['requested_replicates'] ==
                            row['completed_replicates'] == 10000 for row in intervals))
        self.assertFalse(result['provenance_validated'])
        self.assertFalse(result['scientific_support_verified'])
        self.assertNotIn('original_failure_preserved', result)

    def test_all_14_intervals_equal_independent_case_resampling(self):
        report, inputs = values()
        failure(report['records']['repair'][0], 'input_unavailable', 'capacity')
        report['records']['repair'][1]['prediction']['answer_index'] = 1
        report['records']['one_pass'][2]['prediction']['answer_index'] = 1
        report['critics'][0]['decoded']['support'] = 'supported'
        report['critics'][2]['decoded']['support'] = 'supported'
        ids = [q['id'] for q in inputs['queries']]
        inputs['groups'] = [ids[:3], ids[3:5], ids[5:]]
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        for name, left, right in e.statistics.CONTRASTS:
            for endpoint, flag in (('raw_accuracy', 'raw_correct'), ('correct_retained_yield', 'correct_retained')):
                a = [row[flag] for row in result['conditions'][left]['case_results']]
                b = [row[flag] for row in result['conditions'][right]['case_results']]
                for scope, groups in (('publication_components', inputs['groups']),
                                       ('question_sensitivity', [[key] for key in ids])):
                    self.assertEqual(list(result['primary_contrasts'][name][endpoint][scope]['ci95']),
                                     independent_interval(ids, a, b, groups))
        a = [row['raw_correct'] for row in result['native']['repair']['case_results']]
        b = [row['raw_correct'] for row in result['removal_diagnostic']['native']['case_results']]
        for scope, groups in (('publication_components', inputs['groups']),
                               ('question_sensitivity', [[key] for key in ids])):
            self.assertEqual(list(result['removal_diagnostic']['raw_accuracy_removal_minus_repair'][scope]['ci95']),
                             independent_interval(ids, a, b, groups))

    def test_new_capacity_failure_keeps_denominator_without_becoming_unsure(self):
        report, inputs = values()
        failure(report['records']['repair'][0], 'input_unavailable', 'capacity')
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        row = result['native']['repair']['case_results'][0]
        self.assertIsNone(row['prediction']); self.assertIsNone(row['native_unsure'])
        self.assertEqual(result['conditions']['repair']['raw_accuracy'], 5 / 6)
        self.assertEqual(result['conditions']['repair']['scheduled_count'], 6)
        self.assertIsNone(result['conditions']['critique_only']['statistical_retained_precision'])
        self.assertEqual(result['removal_diagnostic']['native']['counts']['correct_and_admitted'], 0)

    def test_source_product_membership_flags_and_native_parity_reject_substitutions(self):
        for change in ('source_missing', 'source_reordered', 'product_missing', 'product_reordered', 'integer_flag', 'query'):
            report, inputs = values()
            if change == 'source_missing': report['source_cases'].pop()
            if change == 'source_reordered': report['source_cases'].reverse()
            if change == 'product_missing': report['case_products'].pop()
            if change == 'product_reordered': report['case_products'].reverse()
            if change == 'integer_flag': report['source_cases'][0]['refinement_available'] = 0
            if change == 'query': inputs['queries'] = copy.deepcopy(inputs['queries']); inputs['queries'][0]['question'] = 'Changed'
            with self.subTest(change=change), self.assertRaises(ValueError):
                e.score_records(report, inputs, native_scorer=evaluate_schedule)
        def wrong(*args, **kwargs):
            result = encode(evaluate_schedule(*args, **kwargs)); result['counts']['raw_correct'] += 1
            return result
        report, inputs = values()
        with self.assertRaisesRegex(ValueError, 'Independent/native'):
            e.score_records(report, inputs, native_scorer=wrong)

    def test_pure_helper_does_not_mutate_or_attest_resources(self):
        report, inputs = values(); before = copy.deepcopy((report, inputs))
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        self.assertEqual((report, inputs), before)
        self.assertEqual(encode(result['incremental_resources']), report['incremental_resources'])
        self.assertFalse(result['provenance_validated'])
        with self.assertRaises(TypeError): result['incremental_resources']['measured_input_tokens'] = 99


class EvidenceFirstAuthorityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.report, self.inputs = values()
        self.value = SimpleNamespace(root=str(self.root / 'new-condition'), receipt_sha256='a' * 64,
            report=freeze(self.report), envelope=freeze(dict(
                producer=dict(root=str(self.root / 'new-condition'), receipt_sha256='a' * 64,
                    controller=dict(root=str(self.root / 'controller'), receipt_sha256='c' * 64)),
                original_producer_descriptor=dict(inspection='invented immutable failed exposure'),
                original_started_at_utc='2090-01-01T00:00:00Z', new_started_at_utc='2100-01-01T00:00:00Z',
                baseline_acceptance=dict(scope='invented baseline'),
                resources=dict(original_failed_exposure=dict(old_repair_calls=2), new_phases=dict(calls=12)))))

    def write(self, name, value):
        path = self.root / name; path.write_bytes(canonical(value))
        return e.native.proof(path)

    def authority(self, endpoint_date='2080-01-01T00:00:00Z', method_date='2099-01-01T00:00:00Z'):
        note = self.write('NOTE.json', dict(scope='invented protocol'))
        addendum = self.write('ADDENDUM.json', dict(scope='invented endpoints'))
        endpoints = e.original_evaluation.endpoint_contract(endpoint_date, note, addendum)
        ep = self.write('ENDPOINTS.json', endpoints)
        method_value = dict(kind='invented_method', revision=1)
        method = dict(proof=self.write('METHOD.json', method_value), identity=e.n.digest(canonical(method_value)))
        keys = self.write('KEYS.json', self.inputs)
        protocol = self.write('PROTOCOL.json', dict(kind='sc05_evidence_first_protocol_v1',
            created_at_utc=method_date, method=method['proof'], endpoints=ep, original_inputs=keys))
        report = encode(self.value.report); report['method_identity'] = method['identity']; self.value.report = freeze(report)
        envelope = encode(self.value.envelope)
        envelope.update(method=method, protocol=protocol, protocol_declared_at_utc=method_date,
                        endpoint_freeze=ep, original_inputs=keys)
        self.value.envelope = freeze(envelope)
        dependency_paths = {inspect.getsourcefile(evaluate_schedule.__globals__[key]) for key in
            ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
        authority = dict(kind=e.AUTHORITY_KIND, role='evaluation_only', purpose='fictional_qualification',
            created_at_utc='2101-01-01T00:00:00Z',
            producer=envelope['producer'],
            native_scorer=e.native.proof(Path(inspect.getsourcefile(evaluate_schedule))),
            native_scorer_dependencies=[e.native.proof(Path(p)) for p in sorted(dependency_paths)], native_scorer_archive=None,
            **{key: envelope[key] for key in ('baseline_acceptance', 'original_producer_descriptor', 'original_inputs',
                                            'endpoint_freeze', 'method', 'protocol')})
        return self.write('AUTHORITY.json', authority), authority

    def test_capability_failure_precedes_authority_and_key_reads(self):
        with patch.object(e, '_revalidate', side_effect=ValueError('not issued')), \
             patch.object(e, '_authority') as authority, patch.object(e, '_inputs') as keys:
            with self.assertRaisesRegex(ValueError, 'not issued'):
                e.evaluate(object(), {}, native_scorer=evaluate_schedule)
            authority.assert_not_called(); keys.assert_not_called()

    def test_genuine_reader_rejects_unissued_or_copied_object_before_keys(self):
        from . import reconstruct
        forged_capability = reconstruct.VerifiedEvidenceFirst(
            self.value.root, self.value.receipt_sha256, self.value.report, self.value.envelope)
        copied_capability = copy.copy(forged_capability)
        object.__setattr__(copied_capability, 'receipt_sha256', 'b' * 64)
        for forged in (self.value, encode(self.value.report), object(), forged_capability, copied_capability):
            with self.subTest(kind=type(forged).__name__), patch.object(e, '_inputs') as keys:
                with self.assertRaises(ValueError): e.evaluate(forged, {}, native_scorer=evaluate_schedule)
                keys.assert_not_called()

    def test_authority_substitutions_reject_before_keys(self):
        descriptor, original = self.authority()
        for change in ('parent', 'producer', 'controller', 'missing_controller', 'baseline', 'role', 'keys', 'method', 'protocol', 'endpoint', 'missing_dependency', 'duplicate_dependency'):
            changed = copy.deepcopy(original)
            if change == 'parent': changed['original_producer_descriptor'] = {}
            if change == 'producer': changed['producer']['receipt_sha256'] = 'b' * 64
            if change == 'controller': changed['producer']['controller']['receipt_sha256'] = 'd' * 64
            if change == 'missing_controller': changed['producer'].pop('controller')
            if change == 'baseline': changed['baseline_acceptance'] = {}
            if change == 'role': changed['role'] = 'actor'
            if change == 'keys': changed['original_inputs'] = self.write('OTHER-KEYS.json', self.inputs)
            if change == 'method': changed['method']['identity'] = 'b' * 64
            if change == 'protocol': changed['protocol'] = self.write('OTHER-PROTOCOL.json', {})
            if change == 'endpoint': changed['endpoint_freeze'] = self.write('OTHER-ENDPOINTS.json', {})
            if change == 'missing_dependency': changed['native_scorer_dependencies'].pop()
            if change == 'duplicate_dependency': changed['native_scorer_dependencies'].append(changed['native_scorer_dependencies'][0])
            descriptor = self.write('AUTHORITY.json', changed)
            with self.subTest(change=change), patch.object(e, '_revalidate', return_value=self.value), \
                 patch.object(e, '_inputs') as keys:
                with self.assertRaises(ValueError): e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
                keys.assert_not_called()

    def test_old_endpoints_and_new_method_have_different_chronology_bounds(self):
        for ep, method in (('2095-01-01T00:00:00Z', '2099-01-01T00:00:00Z'),
                           ('2080-01-01T00:00:00Z', '2102-01-01T00:00:00Z')):
            descriptor, _ = self.authority(ep, method)
            with self.subTest(endpoint=ep, method=method), patch.object(e, '_revalidate', return_value=self.value), \
                 patch.object(e, '_inputs') as keys:
                with self.assertRaisesRegex(ValueError, 'must precede'):
                    e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
                keys.assert_not_called()

    def test_valid_authority_keeps_new_result_and_failed_exposure_separate(self):
        descriptor, _ = self.authority()
        with patch.object(e, '_revalidate', return_value=self.value) as validate:
            result = e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(result['native']['repair']['counts']['raw_correct'], 6)
        self.assertTrue(result['provenance_validated'])
        self.assertFalse(result['old_repair_outputs_adopted'])
        self.assertEqual(result['execution_proof'], self.value.envelope['producer'])
        self.assertEqual(result['historical_and_logical_resources']['original_failed_exposure']['old_repair_calls'], 2)
        self.assertEqual(result['incremental_resources']['measured_input_tokens'], 60)
        with self.assertRaises(TypeError): result['method']['identity'] = 'changed'

    def test_fictional_reference_membership_cannot_use_old_two_case_manifest(self):
        descriptor, authority = self.authority()
        for count in (2, 5, 7):
            data = copy.deepcopy(self.inputs); data['queries'] = (data['queries'] * 2)[:count]
            authority['original_inputs'] = self.write('KEYS.json', data)
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'Exactly six'):
                e._inputs(authority, None, '2090-01-01T00:00:00Z')

    def test_postscore_source_authority_and_protocol_mutations_are_not_accepted(self):
        descriptor, authority = self.authority()
        original_score = e.score_records
        for proof in (authority['original_inputs'], authority['protocol'], authority['method']['proof'], descriptor):
            path = Path(proof['path']); saved = path.read_bytes()
            def changing(*args, **kwargs):
                result = original_score(*args, **kwargs); path.write_bytes(saved + b' ')
                return result
            with self.subTest(path=path.name), patch.object(e, '_revalidate', return_value=self.value), \
                 patch.object(e, 'score_records', side_effect=changing):
                with self.assertRaises(ValueError): e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
            path.write_bytes(saved)
        with patch.object(e, '_revalidate', side_effect=[self.value, ValueError('source changed')]):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)


if __name__ == '__main__':
    unittest.main()
