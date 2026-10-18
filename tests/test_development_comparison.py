from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.agents import EvidenceView, SpecialistRequest
from asof.contracts import Category
from asof.serde import ContractError, canonical, encode, fingerprint, read_json, sha256_file, write_json
from tools.framework.compare_development import (ablation_masks, analyze_attempt,
    checked_request, compare, pilot_wire_format, select_baseline, selection_comparison, validate_protocol, verify_comparison)


def request(scores=(0.3, 0.9, 0.7, 0.1), sources=None):
    views = []
    for index, score in enumerate(scores):
        oid = f'id-{index}'
        record = {'observation_id': oid, 'statement': f'Target disease annotation {index}',
            'target_id': 'ENSG1', 'indication_id': 'EFO_1', 'category': 'genetics',
            'features': {}, 'status': 'observed',
            'source_locator': {'datasource_id': sources[index] if sources else 'same_source'},
            'source_metrics': {'score': score}}
        views.append(EvidenceView(oid, record['statement'], 'sealed-packet', canonical(record).decode()))
    return SpecialistRequest(canonical({'case_id': 'fixture', 'task': 'T6',
        'hypothesis': {'target_id': 'ENSG1', 'indication_id': 'EFO_1'}}).decode(),
        Category.GENETICS, tuple(views), 'Select approved IDs only', ())


def entry(req=None, selected=('id-0',)):
    req = req or request()
    response = {'truncated': False, 'content': canonical({'observation_ids': list(selected)}).decode(),
        'tokens_evaluated': 100, 'tokens_predicted': 10}
    return {'status': 'completed', 'request': encode(req), 'request_sha256': fingerprint(req),
        'response': response, 'response_sha256': fingerprint(response), 'selection': list(selected),
        'measured_usage': {'input_tokens': 100, 'output_tokens': 10, 'cost_usd': 0}}


class DevelopmentComparisonTests(unittest.TestCase):
    def test_protocol_caps_budget_and_duplicate_groups_checked(self):
        protocol = read_json(Path('planning/protocols/development-comparison-v0.1.json'))
        validate_protocol(protocol)
        for field, value in [('selection_cap', 4), ('new_model_calls', 1), ('clinical_labels_read', True), ('baselines', [])]:
            changed = deepcopy(protocol); changed[field] = value
            with self.assertRaises(ContractError): validate_protocol(changed)
        protocol['pilots'].append(protocol['pilots'][0])
        with self.assertRaises(ContractError): validate_protocol(protocol)

    def test_full_report_failure_retention_and_output_reservation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); pilot = root / 'pilot'; case = pilot / 'fixture'; case.mkdir(parents=True)
            protocol = read_json(Path('planning/protocols/development-comparison-v0.1.json'))
            protocol['pilots'] = [{'id': 'fixture_group', 'path': str(pilot), 'case_count': 1, 'seal_sha256': 'a' * 64}]
            protocol_path = root / 'protocol.json'; write_json(protocol_path, protocol)
            write_json(pilot / 'pilot-report.json', {'cases': [{'case_id': 'fixture', 'receipt_sha256': 'b' * 64}]})
            write_json(case / 'inputs.json', {'configuration': {'backend_provenance': {'config': {'retrieval': {}}}}})
            write_json(case / 'backend-execution.json', {'attempts': [entry()]})
            resource = {k: 0 for k in ('calls', 'input_tokens', 'output_tokens', 'native_prompt_and_generation_seconds_sum')}
            with patch('tools.framework.compare_development.summarize', return_value=resource), patch(
                    'tools.framework.compare_development.verify_run', return_value={'source_binding': 'archived_fingerprints_only'}):
                output = root / 'output'; result = compare(protocol_path, output)
                self.assertEqual(result['groups'][0]['case_count'], 1)
                self.assertFalse(result['task6_complete'])
                for pin in read_json(output / 'evidence-manifest.json')['files']:
                    self.assertEqual(sha256_file(output / pin['path']), pin['sha256'])
                seal = output / 'evidence-manifest.json'
                self.assertEqual(verify_comparison(output, sha256_file(seal))['paired_requests_regenerated'], 1)
                with self.assertRaises(ContractError): verify_comparison(output, 'f' * 64)
                changed = read_json(output / 'comparison.json')
                changed['groups'][0]['request_count'] += 1
                write_json(output / 'comparison.json', changed)
                pins = read_json(seal)
                for pin in pins['files']:
                    path = output / pin['path']; pin.update(bytes=path.stat().st_size, sha256=sha256_file(path))
                write_json(seal, pins)
                with self.assertRaisesRegex(ContractError, 'accounting mismatch'):
                    verify_comparison(output, sha256_file(seal))
                with self.assertRaises(FileExistsError): compare(protocol_path, output)
                data = entry(); data['request_sha256'] = 'c' * 64
                write_json(case / 'backend-execution.json', {'attempts': [data]})
                failed = root / 'failed'
                with self.assertRaises(ContractError): compare(protocol_path, failed)
                self.assertEqual(read_json(failed / 'status.json')['status'], 'failed')
                self.assertFalse((failed / 'evidence-manifest.json').exists())

    def test_older_canonical_report_uses_verified_archived_transport(self):
        config = {'backend_provenance': {'config': {'retrieval': {}}}}
        self.assertEqual(pilot_wire_format({}, config), 'canonical')
        with self.assertRaises(ContractError): pilot_wire_format({'wire_format': 'invented'}, config)

    def test_actual_selection_and_simple_baselines_are_paired(self):
        row = analyze_attempt(entry())
        self.assertEqual(row['baselines']['provider_score_top_k']['selected_ids'], ['id-1', 'id-2', 'id-0'])
        self.assertEqual(row['baselines']['lexical_top_k']['selected_ids'], ['id-0', 'id-1', 'id-2'])
        self.assertFalse(row['baselines']['extractive_all']['comparison']['same_selection_set'])
        self.assertTrue(row['candidate_count_exceeds_selection_cap'])
        self.assertEqual(row['baseline_model_calls'], 0)

    def test_one_candidate_is_uninformative_agreement_not_accuracy(self):
        row = analyze_attempt(entry(request((0.1,))))
        for result in row['baselines'].values():
            self.assertTrue(result['comparison']['same_selection_set'])
            self.assertEqual(result['comparison']['interpretation'], 'selection_agreement_only_not_accuracy')
        self.assertFalse(row['candidate_count_exceeds_selection_cap'])

    def test_provider_scales_never_silently_merged(self):
        result = select_baseline(request(sources=['a', 'b', 'a', 'a']), 'provider_score_top_k')
        self.assertEqual(result['status'], 'inapplicable')
        self.assertIsNone(result['selected_ids'])
        self.assertEqual(select_baseline(request(sources=[None] * 4), 'provider_score_top_k')['status'], 'inapplicable')

    def test_missing_bool_and_nonfinite_scores_abstain(self):
        for score in [None, True, float('inf'), float('nan'), '0.9']:
            # JSON forbids nonfinite scientific records before even selecting.
            if type(score) is float and not __import__('math').isfinite(score):
                with self.assertRaises((ContractError, ValueError)):
                    request((score,))
            else:
                self.assertEqual(select_baseline(request((score,)), 'provider_score_top_k')['status'], 'inapplicable')

    def test_ties_stable_and_inputs_immutable(self):
        req = request((0.5,) * 4)
        before = fingerprint(req)
        self.assertEqual(select_baseline(req, 'provider_score_top_k')['selected_ids'], ['id-0', 'id-1', 'id-2'])
        self.assertEqual(fingerprint(req), before)
        self.assertEqual(select_baseline(replace(req, evidence=tuple(reversed(req.evidence))),
            'provider_score_top_k')['selected_ids'], ['id-0', 'id-1', 'id-2'])

    def test_invalid_top_k_and_method_rejected(self):
        for cap in [0, 4, True, 1.5]:
            with self.assertRaises(ContractError): select_baseline(request(), 'lexical_top_k', cap)
        with self.assertRaises(ContractError): select_baseline(request(), 'invented')

    def test_candidate_identity_scope_and_features_checked(self):
        for field, value in [('observation_id', 'other'), ('statement', 'changed'), ('target_id', 'wrong'),
                             ('category', 'literature'), ('features', {'unvalidated': 1}), ('status', 'unavailable')]:
            req = request(); data = encode(req)
            from asof.serde import parse_json
            record = parse_json(data['evidence'][0]['scientific_record_json']); record[field] = value
            data['evidence'][0]['scientific_record_json'] = canonical(record).decode()
            with self.assertRaises(ContractError): checked_request(data)

    def test_duplicate_ids_and_clinical_requests_rejected(self):
        req = request()
        with self.assertRaises(ContractError):
            checked_request(encode(replace(req, evidence=(req.evidence[0], req.evidence[0]))))
        from asof.serde import parse_json
        case = parse_json(req.case_json); case['task'] = 'T1'
        with self.assertRaises(ContractError): checked_request(encode(replace(req, case_json=canonical(case).decode())))

    def test_request_response_selection_usage_tampering_fails(self):
        for key, value in [('request_sha256', '0' * 64), ('response_sha256', '0' * 64),
                           ('selection', ['id-1']), ('measured_usage', {'input_tokens': 101, 'output_tokens': 10, 'cost_usd': 0}),
                           ('status', 'timeout')]:
            data = entry(); data[key] = value
            with self.assertRaises(ContractError): analyze_attempt(data)

    def test_unknown_duplicate_or_truncated_selections_fail(self):
        for ids in [('future-id',), ('id-0', 'id-0'), ('id-0', 'id-1', 'id-2', 'id-3')]:
            with self.assertRaises(ContractError): analyze_attempt(entry(selected=ids))
        data = entry(); data['response']['truncated'] = True
        data['response_sha256'] = fingerprint(data['response'])
        with self.assertRaises(ContractError): analyze_attempt(data)

    def test_empty_agreement_is_not_one_and_inapplicability_not_zero(self):
        self.assertIsNone(selection_comparison([], [], {'status': 'computed', 'selected_ids': []})['jaccard'])
        self.assertEqual(selection_comparison(['a'], [], {'status': 'inapplicable', 'reason': 'missing'})['status'], 'inapplicable')
        with self.assertRaises(ContractError): selection_comparison(['a'], ['b'], {'status': 'computed', 'selected_ids': ['a']})
        with self.assertRaises(ContractError): selection_comparison(['a'], [], {'status': 'computed', 'selected_ids': ['b']})

    def test_ablations_are_separate_explicit_masks_not_model_effects(self):
        rows = [{'category': 'literature', 'model_selected_ids': ['a']},
                {'category': 'genetics', 'model_selected_ids': ['b']}]
        before = deepcopy(rows); masked = ablation_masks(rows)
        self.assertEqual(masked['no_literature']['retained_ids'], ['b'])
        self.assertEqual(masked['no_literature']['removed_ids'], ['a'])
        self.assertEqual(masked['no_perturbation']['removed_ids'], [])
        self.assertIsNone(masked['no_literature']['scientific_effect'])
        self.assertEqual(rows, before)


if __name__ == '__main__': unittest.main()
