"""Invented scoring and authority controls, without any released answer keys.

Authority-order tests isolate the outer capability through a mock. They do not
qualify recovery issuance; the independent reader and integration tests do that.
The native scorer, fixed estimands and all file proofs run without replacement.
"""
import copy
import inspect
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode, freeze
from experiments.labbench.evaluate import evaluate_schedule
from experiments.litqa_analysis.test_scoring import fixture, failure
from . import evaluation as e


def values(size=2):
    queries, references, baseline, evidence = fixture(size)
    repaired = copy.deepcopy(baseline)
    failure(repaired[184 if size == 199 else 0], 'error', 'inherited_unqualified_native_completion')
    removed = copy.deepcopy(baseline)
    for row in removed:
        row['prediction']['evidence_ids'] = []
        row.update(check_status='rejected', reason='raw_source_removal')
    sources = [dict(id=q['id'], retained_dois=[], pool_dois=[], selected_dois=[],
        original_retained_dois=[], original_pool_dois=[], original_selected_dois=[],
        source_context_changed=False, refinement_available=False) for q in queries]
    usage = dict(qualified_measured=dict(input_tokens=100, output_tokens=20),
        unverified_reported=dict(input_tokens=50, output_tokens=256),
        failed_reservation=dict(input_tokens=16128, output_tokens=256),
        physical_generation_attempts=2, provider_cost_usd=0)
    report = dict(purpose='production' if size == 199 else 'fictional_qualification', queries=queries,
        records=dict(one_pass=baseline, repair=repaired, removal=removed),
        evidence_ids=dict(one_pass=evidence, repair=evidence,
                          removal={q['id']: [] for q in queries}),
        critics=[dict(id=q['id'], native_status='completed',
                      decoded=dict(support='insufficient')) for q in queries],
        source_cases=sources, case_products=[], incremental_resources=usage,
        logical_resources=dict(scope='invented overlapping condition attribution'))
    inputs = dict(kind='sc05_fictional_evaluation_inputs_v1', role='evaluation_only',
        queries=queries, references=references, groups=[[q['id']] for q in queries],
        annotations={q['id']: [] for q in queries})
    if size == 199:
        ids = [q['id'] for q in queries]
        inputs['groups'] = [[key] for key in ids[:176]]
        inputs['groups'] += [ids[i:i+2] for i in range(176, 190, 2)]
        inputs['groups'] += [ids[i:i+3] for i in range(190, 199, 3)]
    return report, inputs


class RecoveryScoringTests(unittest.TestCase):
    def test_invented_full_size_keeps_all_199_cases_186_groups_and_14_intervals(self):
        # Synthetic dimensions only: this cannot confer production authority.
        report, inputs = values(199)
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        self.assertEqual(result['scheduled_count'], 199)
        self.assertEqual(result['publication_component_count'], 186)
        self.assertEqual(result['native']['repair']['counts']['raw_correct'], 198)
        self.assertEqual(result['native']['repair']['producer_status_counts']['error'], 1)
        self.assertIsNone(result['native']['repair']['case_results'][184]['native_unsure'])
        intervals = [interval for endpoints in result['primary_contrasts'].values()
                     for estimates in endpoints.values() for interval in estimates.values()]
        intervals.extend(result['removal_diagnostic']['raw_accuracy_removal_minus_repair'].values())
        self.assertEqual(len(intervals), 14)
        self.assertTrue(all(item['completed_replicates'] == 10000 for item in intervals))
        self.assertEqual(result['seed'], 20261106)
        self.assertFalse(result['provenance_validated'])

    def test_failed_attempt_keeps_denominator_and_is_neither_unsure_nor_codec(self):
        report, inputs = values()
        before = copy.deepcopy((report, inputs))
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        native = result['native']['repair']
        self.assertEqual(native['scheduled_count'], 2)
        self.assertEqual(native['counts']['raw_correct'], 1)
        self.assertEqual(native['counts']['producer_failures'], 1)
        self.assertEqual(native['producer_status_counts']['error'], 1)
        self.assertEqual(native['raw_metrics']['accuracy'], .5)
        self.assertIsNone(native['case_results'][0]['native_unsure'])
        self.assertEqual(result['repair_transitions']['counts']['damaged_correct'], 1)
        self.assertFalse(result['provenance_validated'])
        self.assertFalse(result['scientific_support_verified'])
        self.assertEqual(result['native_agreement']['status'], 'PASS')
        self.assertEqual((report, inputs), before)

    def test_unverified_usage_and_reservations_remain_separate_and_immutable(self):
        report, inputs = values()
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        self.assertEqual(encode(result['incremental_resources']), report['incremental_resources'])
        report['incremental_resources']['unverified_reported']['output_tokens'] = 0
        self.assertEqual(result['incremental_resources']['unverified_reported']['output_tokens'], 256)
        with self.assertRaises(TypeError):
            result['incremental_resources']['qualified_measured']['output_tokens'] = 276
        self.assertEqual(result['logical_condition_resources']['scope'],
                         'invented overlapping condition attribution')

    def test_empty_retention_precision_remains_undefined_and_removal_diagnostic_separate(self):
        report, inputs = values()
        result = e.score_records(report, inputs, native_scorer=evaluate_schedule)
        self.assertIsNone(result['conditions']['critique_only']['statistical_retained_precision'])
        self.assertFalse(result['conditions']['critique_only']['retained_precision_defined'])
        self.assertEqual(result['removal_diagnostic']['native']['counts']['correct_and_admitted'], 0)
        self.assertEqual(result['native']['one_pass'], result['native']['critique_only'])
        self.assertEqual(result['original_source_metrics']['selected']['scheduled_count'], 2)

    def test_source_schedule_must_remain_complete_and_ordered(self):
        for change in ('missing', 'reorder'):
            report, inputs = values()
            if change == 'missing': report['source_cases'].pop()
            else: report['source_cases'].reverse()
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'ordered source'):
                e.score_records(report, inputs, native_scorer=evaluate_schedule)

    def test_native_disagreement_and_changed_query_fail(self):
        report, inputs = values()
        def wrong(*args, **kwargs):
            result = encode(evaluate_schedule(*args, **kwargs))
            result['counts']['raw_correct'] += 1
            return result
        with self.assertRaisesRegex(ValueError, 'native recovery score mismatch'):
            e.score_records(report, inputs, native_scorer=wrong)
        inputs['queries'] = copy.deepcopy(inputs['queries'])
        inputs['queries'][0]['choices'][0] = '(A) A different option'
        with self.assertRaisesRegex(ValueError, 'options, order or membership'):
            e.score_records(report, inputs, native_scorer=evaluate_schedule)

    def test_inherited_failure_cannot_have_a_prediction_or_admission(self):
        for field, value in (('prediction', dict(answer_index=0, evidence_ids=['s0'])),
                             ('check_status', 'accepted')):
            report, inputs = values()
            report['records']['repair'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                e.score_records(report, inputs, native_scorer=evaluate_schedule)


class RecoveryAuthorityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.report, self.inputs = values()
        self.value = SimpleNamespace(root=str(self.root/'recovery'), receipt_sha256='a'*64,
            report=freeze(self.report), envelope=freeze(dict(
                original_producer_descriptor=dict(inspection='fictional inspection',
                    source_archive='fictional source archive', original_frame='fictional frame',
                    original_failure='fictional failure'),
                original_started_at_utc='2090-01-01T00:00:00Z',
                baseline_acceptance=dict(fictional_only=True), resources=dict(scope='invented'))))

    def write(self, name, value):
        path = self.root/name
        path.write_bytes(canonical(value))
        return e.native.proof(path)

    def authority(self, declared='2080-01-01T00:00:00Z'):
        note = self.write('NOTE.json', dict(scope='invented protocol'))
        addendum = self.write('ADDENDUM.json', dict(scope='invented endpoint freeze'))
        endpoints = e.original_evaluation.endpoint_contract(declared, note, addendum)
        dependency_paths = {inspect.getsourcefile(evaluate_schedule.__globals__[key]) for key in
            ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
        authority = dict(kind=e.AUTHORITY_KIND, role='evaluation_only', purpose='fictional_qualification',
            created_at_utc='2100-01-01T00:00:00Z',
            producer=dict(root=self.value.root, receipt_sha256=self.value.receipt_sha256),
            baseline_acceptance=encode(self.value.envelope['baseline_acceptance']),
            original_producer_descriptor=encode(self.value.envelope['original_producer_descriptor']),
            original_inputs=self.write('KEYS.json', self.inputs),
            endpoint_freeze=self.write('ENDPOINTS.json', endpoints),
            native_scorer=e.native.proof(Path(inspect.getsourcefile(evaluate_schedule))),
            native_scorer_dependencies=[e.native.proof(Path(p)) for p in sorted(dependency_paths)],
            native_scorer_archive=None)
        return self.write('AUTHORITY.json', authority), authority

    def test_capability_failure_precedes_authority_and_keys(self):
        with patch.object(e, '_revalidate', side_effect=ValueError('not issued')), \
             patch.object(e, '_authority') as authority, \
             patch.object(e.original_evaluation, '_inputs') as keys:
            with self.assertRaisesRegex(ValueError, 'not issued'):
                e.evaluate(object(), {}, native_scorer=evaluate_schedule)
            authority.assert_not_called(); keys.assert_not_called()

    def test_genuine_reader_rejects_unissued_types_before_keys(self):
        from . import reconstruct
        forged = reconstruct.VerifiedRecovery(self.value.root, self.value.receipt_sha256,
            self.value.report, self.value.envelope, '0'*64, reconstruct._TOKEN)
        for value in (self.value, forged, encode(self.value.report)):
            with self.subTest(kind=type(value).__name__), \
                 patch.object(e.original_evaluation, '_inputs') as keys:
                with self.assertRaisesRegex(ValueError, 'Issued independent recovery capability'):
                    e.evaluate(value, {}, native_scorer=evaluate_schedule)
                keys.assert_not_called()

    def test_original_parent_authority_roles_and_dependencies_precede_keys(self):
        descriptor, authority = self.authority()
        for change in ('parent', 'producer', 'baseline', 'role', 'missing_dependency', 'duplicate_dependency'):
            changed = copy.deepcopy(authority)
            if change == 'parent': changed['original_producer_descriptor']['original_failure'] = 'substitution'
            elif change == 'producer': changed['producer']['receipt_sha256'] = 'b'*64
            elif change == 'baseline': changed['baseline_acceptance'] = {}
            elif change == 'role': changed['role'] = 'agent_evidence'
            elif change == 'missing_dependency': changed['native_scorer_dependencies'].pop()
            else: changed['native_scorer_dependencies'].append(changed['native_scorer_dependencies'][0])
            current = self.write('AUTHORITY.json', changed)
            with self.subTest(change=change), patch.object(e, '_revalidate', return_value=self.value), \
                 patch.object(e.original_evaluation, '_inputs') as keys:
                with self.assertRaises(ValueError): e.evaluate(self.value, current, native_scorer=evaluate_schedule)
                keys.assert_not_called()

    def test_endpoints_between_original_and_recovery_are_too_late(self):
        descriptor, _ = self.authority(declared='2095-01-01T00:00:00Z')
        with patch.object(e, '_revalidate', return_value=self.value), \
             patch.object(e.original_evaluation, '_inputs') as keys:
            with self.assertRaisesRegex(ValueError, 'precede original production'):
                e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
            keys.assert_not_called()

    def test_valid_unit_authority_retains_parent_failure_and_frozen_result(self):
        descriptor, _ = self.authority()
        with patch.object(e, '_revalidate', return_value=self.value) as revalidate:
            result = e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
        self.assertEqual(revalidate.call_count, 2)
        self.assertTrue(result['provenance_validated'])
        self.assertTrue(result['original_failure_preserved'])
        self.assertFalse(result['completed_or_entered_calls_repeated'])
        self.assertEqual(result['kind'], e.REPORT_KIND)
        self.assertEqual(result['original_producer_descriptor'], self.value.envelope['original_producer_descriptor'])
        with self.assertRaises(TypeError): result['source_cases'][0]['id'] = 'changed'

    def test_final_revalidation_failure_never_returns_a_report(self):
        descriptor, _ = self.authority()
        with patch.object(e, '_revalidate', side_effect=[self.value, ValueError('source changed')]):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)

    def test_input_or_authority_mutation_during_scoring_is_rejected(self):
        descriptor, authority = self.authority()
        original_score = e.score_records
        for target in (authority['original_inputs']['path'], descriptor['path']):
            path = Path(target); saved = path.read_bytes()
            def changing_score(*args, **kwargs):
                result = original_score(*args, **kwargs)
                path.write_bytes(saved+b' ')
                return result
            with self.subTest(target=path.name), patch.object(e, '_revalidate', return_value=self.value), \
                 patch.object(e, 'score_records', side_effect=changing_score):
                with self.assertRaises(ValueError):
                    e.evaluate(self.value, descriptor, native_scorer=evaluate_schedule)
            path.write_bytes(saved)


if __name__ == '__main__':
    unittest.main()
