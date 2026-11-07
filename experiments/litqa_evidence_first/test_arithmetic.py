"""Invented independent-arithmetic controls; reference facts are fixture-only."""
import copy
import unittest

from tether_engine.serde import encode
from experiments.labbench.evaluate import evaluate_schedule
from . import arithmetic as a
from . import evaluation as e
from .test_evaluation import values, independent_interval


def invented_report(size=6):
    report, inputs = values(size)
    for i, critic in enumerate(report['critics']):
        critic['decoded']['support'] = 'supported' if i % 2 else 'insufficient'
    for i, source in enumerate(report['source_cases']):
        doi = '10.99999/invented-arithmetic-' + str(i)
        inputs['annotations'][source['id']] = [doi]
        for key in ('retained_dois', 'pool_dois', 'selected_dois'):
            source[key] = [doi] if i % 2 else []
    result = encode(e.score_records(report, inputs, native_scorer=evaluate_schedule))
    result.update(provenance_validated=True, earlier_failed_condition_preserved=True,
                  old_repair_outputs_adopted=False)
    for score in result['native'].values(): score['provenance_validated'] = True
    result['removal_diagnostic']['native']['provenance_validated'] = True
    products = []
    for i, query in enumerate(report['queries']):
        decision = 'keep' if i % 2 else 'withhold'
        reason = 'critic_supported' if i % 2 else 'critic_insufficient'
        products.append(dict(id=query['id'], original=report['records']['one_pass'][i],
            repair=report['records']['repair'][i], removal=report['records']['removal'][i],
            critic=report['critics'][i], semantic_selection=dict(decision=decision, reason=reason,
                native_candidate_unchanged=True, retained_prediction=report['records']['one_pass'][i]['prediction'] if i % 2 else None,
                scientific_correctness='unevaluated'),
            physical_execution_ids={phase: phase + '-invented-' + str(i) for phase in ('repair', 'removal')},
            accounting={phase: dict(generation_calls=1, measured_input_tokens=12, measured_output_tokens=3,
                reserved_input_tokens=16128, reserved_output_tokens=256, source_http_requests=0,
                measured_response_bytes=0, safety_accounted_bytes=0) for phase in ('repair', 'removal')}))
    result['case_products'] = products
    measured = {phase: {key: sum(row['accounting'][phase][key] for row in products) for key in a.FIELDS}
                for phase in ('repair', 'removal')}
    result['incremental_resources'] = dict(by_phase=measured,
        physical_totals={key: sum(row[key] for row in measured.values()) for key in a.FIELDS},
        provider_cost_usd=0, reused_original_work_included=False)
    old = {phase: dict.fromkeys(a.FIELDS, 0) for phase in ('critic', 'refinement_collect', 'pair_prepare', 'repair', 'removal')}
    prior = dict(verified_by_phase=old, physical_totals=dict.fromkeys(a.FIELDS, 0), unverified_native=[],
                 actual_prior_model_calls=0, scope='Invented zero-cost ancestry')
    baseline = [dict(id=row['id'], logical_model_usage=dict.fromkeys(a.MODEL_FIELDS, 0),
                     logical_http_usage=dict.fromkeys(a.HTTP_FIELDS, 0)) for row in products]
    if size == 199:
        old['critic'].update(generation_calls=1, measured_input_tokens=10, measured_output_tokens=5,
                             reserved_input_tokens=16128, reserved_output_tokens=256)
        old['refinement_collect'].update(source_http_requests=1, measured_response_bytes=20, safety_accounted_bytes=20)
        old['repair'].update(generation_calls=1, measured_input_tokens=30, measured_output_tokens=6,
                             reserved_input_tokens=16128, reserved_output_tokens=256)
        prior['physical_totals'] = {key: sum(row[key] for row in old.values()) for key in a.FIELDS}
        prior.pop('actual_prior_model_calls')
        prior['unverified_native'] = [dict(kind='sc05_authenticated_native_limit_failure_v1',
            status='authenticated_limit_failure', producer_status='error', check_status='not_run', prediction=None,
            original_usage_verified=False, qualified_usage=None, raw_usage_checked=True, execution_id='old-invented-limit',
            raw_reported_usage=dict(input_tokens=40, output_tokens=256, cost_usd=0),
            conservative_reservation=dict(input_tokens=16128, output_tokens=256, cost_usd=0))]
        for row in baseline:
            row['logical_model_usage'].update(generation_calls=1, measured_input_tokens=3, measured_output_tokens=1,
                                              reserved_input_tokens=16128, reserved_output_tokens=256)
    reused = {phase: old[phase] for phase in ('critic', 'refinement_collect', 'pair_prepare')}
    history = dict(reused_prerequisites=reused, original_failed_exposure=prior, baseline_resources=baseline,
                   original_resources=None, original_phase_resources=None)
    result['historical_and_logical_resources'] = dict(phases={}, new_work_wall_seconds=1, history=history,
                                                     historical_work_reexecuted=False, old_repair_outputs_adopted=False)
    result['logical_condition_resources'] = e.original_evaluation._logical_resources(
        dict(frame=dict(schedule=[row['id'] for row in products]), resources=dict(baseline_resources=baseline)),
        dict(reused, **measured))
    return result, inputs


class ArithmeticPrimitiveTests(unittest.TestCase):
    def test_independent_sampler_matches_direct_case_sampling_and_is_not_mutably_cached(self):
        ids = ['a', 'b', 'c', 'd', 'e', 'f']; groups = [ids[:3], ids[3:5], ids[5:]]
        left = [True, False, True, False, False, True]
        right = [False, True, True, True, False, False]
        expected = independent_interval(ids, left, right, groups)
        result = a._interval(ids, left, right, groups)
        self.assertEqual(result['ci95'], expected)
        self.assertEqual(result['completed_replicates'], 10000)
        result['ci95'][0] = 99
        self.assertEqual(a._interval(ids, left, right, groups)['ci95'], expected)

    def test_one_component_preserves_unestimable_uncertainty(self):
        result = a._interval(['a', 'b'], [True, False], [False, True], [['a', 'b']])
        self.assertIsNone(result['ci95']); self.assertFalse(result['uncertainty_estimable'])
        self.assertEqual(result['completed_replicates'], 0)

    def test_native_counter_rejects_changed_flags_status_and_bool_counts(self):
        report, _ = invented_report()
        native = report['native']['repair']; ids = [row['id'] for row in native['case_results']]
        a.equal(native, a._native(native['case_results'], ids), 'valid native fixture')
        for change in ('flag', 'failure_prediction', 'reason', 'bool'):
            mutated = copy.deepcopy(native)
            if change == 'flag': mutated['case_results'][0]['checked_answered'] = False
            if change == 'failure_prediction': mutated['case_results'][0]['producer_status'] = 'error'
            if change == 'reason': mutated['case_results'][0]['reason'] = 'contradictory'
            if change == 'bool': mutated['counts']['parse_failures'] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                a.equal(mutated, a._native(mutated['case_results'], ids), 'mutated native fixture')


class ReportArithmeticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.inputs = invented_report()
        cls.ids = [row['id'] for row in cls.inputs['queries']]

    def audit(self, report):
        return a.audit_report(report, expected_ids=self.ids, expected_groups=self.inputs['groups'])

    def test_full_invented_report_matches_without_issuing_acceptance(self):
        before = copy.deepcopy(self.report)
        result = self.audit(self.report)
        self.assertEqual(result['intervals_recomputed'], 14)
        self.assertEqual(result['resources']['new_physical_totals']['generation_calls'], 12)
        self.assertFalse(result['reference_truth_checked_here'])
        self.assertFalse(result['acceptance_issued'])
        self.assertEqual(self.report, before)

    def test_full_199_186_preserves_all_intervals_and_sunk_cost_partition(self):
        report, inputs = invented_report(199)
        result = a.audit_report(report, expected_ids=[row['id'] for row in inputs['queries']], expected_groups=inputs['groups'])
        self.assertEqual(result['scheduled_count'], 199)
        self.assertEqual(result['publication_component_count'], 186)
        self.assertEqual(result['intervals_recomputed'], 14)
        resource = result['resources']
        self.assertEqual(resource['new_physical_totals']['generation_calls'], 398)
        self.assertEqual(resource['earlier_verified_totals']['generation_calls'], 2)
        self.assertEqual(resource['earlier_sunk_repair_verified']['generation_calls'], 1)
        self.assertEqual(resource['earlier_unverified_attempts'], 1)
        self.assertEqual(resource['earlier_reported_unverified']['output_tokens'], 256)
        self.assertFalse(resource['raw_unverified_usage_added_to_measurements'])
        changed = copy.deepcopy(report)
        changed['logical_condition_resources']['conditions']['repair']['model_usage']['measured_output_tokens'] += 6
        with self.assertRaisesRegex(ValueError, 'Logical overlap'):
            a.audit_report(changed, expected_ids=[row['id'] for row in inputs['queries']], expected_groups=inputs['groups'])

    def test_every_interval_rejects_an_altered_bound_or_draw_count(self):
        paths = [(('primary_contrasts', name, endpoint, scope)) for name, _, _ in a.CONTRASTS
                 for endpoint in ('raw_accuracy', 'correct_retained_yield')
                 for scope in ('publication_components', 'question_sensitivity')]
        paths += [('removal_diagnostic', 'raw_accuracy_removal_minus_repair', scope)
                  for scope in ('publication_components', 'question_sensitivity')]
        self.assertEqual(len(paths), 14)
        for index, path in enumerate(paths):
            changed = copy.deepcopy(self.report); interval = changed
            for part in path: interval = interval[part]
            if index % 2: interval['completed_replicates'] = 9999
            else: interval['ci95'][0] += .125
            with self.subTest(path=path), self.assertRaises(ValueError): self.audit(changed)

    def test_missing_reordered_or_duplicated_cases_and_wrong_external_groups_fail(self):
        for change in ('missing', 'reordered', 'duplicated', 'physical'):
            altered = copy.deepcopy(self.report)
            if change == 'missing': altered['case_products'].pop()
            if change == 'reordered': altered['native']['repair']['case_results'].reverse()
            if change == 'duplicated': altered['source_cases'][1] = altered['source_cases'][0]
            if change == 'physical': altered['case_products'][0]['physical_execution_ids']['repair'] = altered['case_products'][1]['physical_execution_ids']['repair']
            with self.subTest(change=change), self.assertRaises(ValueError): self.audit(altered)
        with self.assertRaises(ValueError):
            a.audit_report(self.report, expected_ids=self.ids, expected_groups=[self.ids])

    def test_counts_selection_transitions_dois_and_native_comparisons_are_recomputed(self):
        for change in ('count', 'selection', 'transition', 'doi', 'comparison', 'compare_duplicate', 'flag'):
            altered = copy.deepcopy(self.report)
            if change == 'count': altered['native']['repair']['counts']['raw_correct'] -= 1
            if change == 'selection': altered['semantic_selection']['false_withholding'] += 1
            if change == 'transition': altered['repair_transitions']['counts']['damaged_correct'] += 1
            if change == 'doi': altered['source_metrics']['selected']['matched_annotated_source_count'] += 1
            if change == 'comparison': altered['native_agreement']['comparisons'][0]['native']['counts']['raw_correct'] += 1
            if change == 'compare_duplicate': altered['native_agreement']['comparisons'][1] = altered['native_agreement']['comparisons'][0]
            if change == 'flag': altered['source_cases'][0]['refinement_available'] = 0
            with self.subTest(change=change), self.assertRaises(ValueError): self.audit(altered)
        reordered = copy.deepcopy(self.report); reordered['native_agreement']['comparisons'].reverse()
        self.audit(reordered)  # Membership, not serialization order, defines this mapping.

    def test_resources_reject_bool_nonfinite_new_http_and_changed_cell_or_aggregate(self):
        for change in ('bool', 'nan', 'http', 'cell', 'aggregate', 'reused', 'exposure', 'logical', 'adoption'):
            altered = copy.deepcopy(self.report)
            if change == 'bool': altered['case_products'][0]['accounting']['repair']['generation_calls'] = True
            if change == 'nan': altered['incremental_resources']['provider_cost_usd'] = float('nan')
            if change == 'http': altered['case_products'][0]['accounting']['repair']['source_http_requests'] = 1
            if change == 'cell': altered['case_products'][0]['accounting']['repair']['measured_output_tokens'] += 1
            if change == 'aggregate': altered['incremental_resources']['physical_totals']['generation_calls'] += 1
            if change == 'reused': altered['historical_and_logical_resources']['history']['reused_prerequisites']['critic'] = dict.fromkeys(a.FIELDS, 1)
            if change == 'exposure': altered['historical_and_logical_resources']['history']['original_failed_exposure']['physical_totals']['generation_calls'] = 1
            if change == 'logical': altered['logical_condition_resources']['conditions']['repair']['model_usage']['generation_calls'] += 1
            if change == 'adoption': altered['old_repair_outputs_adopted'] = True
            with self.subTest(change=change), self.assertRaises(ValueError): self.audit(altered)

    def test_raw_rejected_usage_remains_separate_and_cannot_reidentify_new_work(self):
        # Exercise resource arithmetic directly on small invented dimensions.
        report = copy.deepcopy(self.report); report['purpose'] = 'production'
        exposure = report['historical_and_logical_resources']['history']['original_failed_exposure']
        exposure.pop('actual_prior_model_calls')
        descriptor = dict(kind='sc05_authenticated_native_limit_failure_v1', status='authenticated_limit_failure',
            producer_status='error', check_status='not_run', prediction=None, original_usage_verified=False,
            qualified_usage=None, raw_usage_checked=True, execution_id='earlier-invented-native-limit',
            raw_reported_usage=dict(input_tokens=55, output_tokens=256, cost_usd=0),
            conservative_reservation=dict(input_tokens=16128, output_tokens=256, cost_usd=0))
        exposure['unverified_native'] = [descriptor]
        resource = a._resources(report, self.ids)
        self.assertEqual(resource['earlier_reported_unverified']['input_tokens'], 55)
        self.assertEqual(resource['new_physical_totals']['measured_input_tokens'], 144)
        for change in ('verified', 'qualified', 'prediction', 'cost', 'overflow', 'repeated', 'new_identity'):
            altered = copy.deepcopy(report)
            rows = altered['historical_and_logical_resources']['history']['original_failed_exposure']['unverified_native']
            row = rows[0]
            if change == 'verified': row['original_usage_verified'] = True
            if change == 'qualified': row['qualified_usage'] = dict(input_tokens=55, output_tokens=256, cost_usd=0)
            if change == 'prediction': row['prediction'] = dict(answer_index=0, evidence_ids=[])
            if change == 'cost': row['raw_reported_usage']['cost_usd'] = False
            if change == 'overflow': row['raw_reported_usage']['input_tokens'] = 16129
            if change == 'repeated': rows.append(copy.deepcopy(row))
            if change == 'new_identity': row['execution_id'] = altered['case_products'][0]['physical_execution_ids']['repair']
            with self.subTest(change=change), self.assertRaises(ValueError): a._resources(altered, self.ids)

    def test_retained_full_critic_body_has_only_its_status_and_support_in_arithmetic(self):
        altered = copy.deepcopy(self.report)
        for row in altered['case_products']:
            previous = row['critic']
            row['critic'] = dict(kind='model_generated_critique_context_v1', query_sha256='1' * 64,
                candidate_sha256='2' * 64, source_context_sha256='3' * 64, native_call_sha256='4' * 64,
                is_scientific_evidence=False, native_status=previous['native_status'],
                decoded=dict(previous['decoded'], evidence_ids=[], criticism='Invented control text',
                             refinement_query=dict(required_terms=['invented'], optional_terms=[])))
        self.audit(altered)
        altered['case_products'][0]['critic']['decoded']['support'] = 'supported'
        with self.assertRaises(ValueError): self.audit(altered)


if __name__ == '__main__':
    unittest.main()
