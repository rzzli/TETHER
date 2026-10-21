from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError, sha256_file
from tools.science.qualification import (ENDPOINTS, STAGES, validate_feature_chronology,
    validate_outcome, validate_reference, validate_register)


def reference():
    return {'schema_version': 1, 'reference_id': 'fixture', 'case_id': 'fixture',
        'hypothesis_sha256': 'a' * 64, 'source_row_sha256': 'b' * 64,
        'statement': 'Fictional fixture source reports an association.', 'answer': 'supported',
        'context': {'tissue': None, 'modality_relevance': 'uncertain'},
        'source_evidence': [{'artifact_sha256': 'c' * 64, 'locator': 'row:1',
            'url': 'https://example.org/fictional-fixture', 'retrieved_at': '2026-10-18'}],
        'reviews': [{'reviewer_id': name, 'reviewer_kind': 'ai_agent',
            'model_provenance': 'explicit-fictional-test-agent', 'blinded_to_arm_outputs': True}
            for name in ('reviewer-a', 'reviewer-b')],
        'adjudication': {'rationale': 'Two fixture reviews cite the same fictional source fact.'},
        'reference_level': 'ai_source_adjudicated', 'role': 'evaluation_only',
        'validation_claim': 'source_grounded_ai_reference',
        'version_applicability': {'status': 'exact'}}


def outcome(endpoint='registry_next_phase_actual_start', value=1):
    return {'schema_version': 1, 'case_id': 'fixture', 'endpoint_id': endpoint,
        'value': value, 'status': 'resolved', 'origin_at': '2025-01-01T00:00:00Z',
        'horizon_at': '2026-01-01T00:00:00Z', 'ascertainment_at': '2026-04-01T00:00:00Z',
        'event_at': '2025-06-01T00:00:00Z' if value else None,
        'publicly_available_at': '2025-06-03T00:00:00Z' if value else '2026-02-01T00:00:00Z',
        'observed_until': '2026-03-01T00:00:00Z', 'source_evidence': reference()['source_evidence'],
        'same_program_scope': True, 'negative_ascertainment': 'fixture complete registry-window audit' if not value else None,
        'reference_level': 'ai_source_adjudicated'}


def register():
    return {'schema_version': 1, 'provider_spend_usd': 0,
        'created_at_utc': '2026-10-18T00:00:00Z', 'endpoints': {e: {} for e in ENDPOINTS},
        'original_H1_endpoint': 'clinical_success',
        'stages': [{'id': stage, 'status': 'pending', 'depends_on': list(STAGES[:index]),
            'acceptance_checks': ['fixture validation'], 'deliverables': ['fixture report'], 'proofs': []}
            for index, stage in enumerate(STAGES)]}


class ScienceQualificationTests(unittest.TestCase):
    def test_register_validity_does_not_imply_scientific_readiness(self):
        result = validate_register(register())
        self.assertEqual(result['scientific_validation'], 'not_inferred_from_contract_validation')
        self.assertEqual(set(result['stages'].values()), {'pending'})

    def test_endpoint_substitution_stage_order_and_unproven_pass_rejected(self):
        mutations = [lambda r: r.update(original_H1_endpoint='registry_next_phase_actual_start'),
            lambda r: r['endpoints'].pop('clinical_success'),
            lambda r: r['stages'].reverse(),
            lambda r: r['stages'][0].update(status='passed'),
            lambda r: r['stages'][0].update(status='deferred')]
        for mutate in mutations:
            doc = register(); mutate(doc)
            with self.assertRaises(ContractError): validate_register(doc)

    def test_later_stage_cannot_pass_with_unmet_dependencies(self):
        doc = register(); doc['stages'][1].update(status='passed', proofs=[{'path':'irrelevant','sha256':'a'*64}])
        with self.assertRaisesRegex(ContractError, 'unmet dependencies'):
            validate_register(doc, verify_proofs=False)

    def test_passed_stage_proof_rehashed_and_future_dependency_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); proof = root / 'proof'; proof.write_bytes(b'fixture validation')
            doc = register(); doc['stages'][0].update(status='passed', proofs=[{'path':'proof','sha256':sha256_file(proof)}])
            self.assertEqual(validate_register(doc, root)['stages']['science_1'], 'passed')
            proof.write_bytes(b'changed')
            with self.assertRaises(ContractError): validate_register(doc, root)
        doc = register(); doc['stages'][0]['depends_on'] = ['science_7']
        with self.assertRaises(ContractError): validate_register(doc)

    def test_ai_panel_can_qualify_source_reference_without_independent_truth_claim(self):
        result = validate_reference(reference())
        self.assertTrue(result['eligible_for_source_grounded_comparison'])
        self.assertFalse(result['eligible_for_independent_scientific_claim'])

    def test_multiple_ai_agents_do_not_become_external_scientific_validation(self):
        doc = reference(); doc['reference_level'] = 'independently_adjudicated'
        doc['adjudication']['independence_evidence'] = 'Different context windows only'
        with self.assertRaises(ContractError): validate_reference(doc)
        doc = reference(); doc['validation_claim'] = 'independently_validated_scientific_truth'
        with self.assertRaises(ContractError): validate_reference(doc)

    def test_stale_reference_not_promoted_by_external_reviewer_metadata(self):
        doc = reference(); doc['reference_level'] = 'independently_adjudicated'
        doc['reviews'][0]['reviewer_kind'] = 'curated_external'
        doc['adjudication']['independence_evidence'] = 'Fixture-only external qualification record'
        self.assertTrue(validate_reference(doc)['eligible_for_independent_scientific_claim'])
        doc['version_applicability']['status'] = 'stale'
        self.assertFalse(validate_reference(doc)['eligible_for_independent_scientific_claim'])

    def test_missing_source_identity_duplicate_reviewer_and_unlabeled_model_fail(self):
        for mutate in [lambda d: d.update(role='agent_evidence'),
                       lambda d: d.update(source_row_sha256=None),
                       lambda d: d['reviews'].append(d['reviews'][0]),
                       lambda d: d['reviews'][0].pop('model_provenance'),
                       lambda d: d.update(source_evidence=[])]:
            doc = reference(); mutate(doc)
            with self.assertRaises((ContractError, KeyError)): validate_reference(doc)

    def test_registry_positive_is_not_dosing_or_success(self):
        self.assertTrue(validate_outcome(outcome())['binary_eligible'])
        for endpoint in ('verified_experimental_dosing', 'clinical_success'):
            with self.assertRaises(ContractError): validate_outcome(outcome(endpoint))

    def test_unreviewed_outcome_not_admitted_and_unstructured_source_rejected(self):
        doc = outcome(); doc['reference_level'] = 'unreviewed'
        self.assertFalse(validate_outcome(doc)['binary_eligible'])
        doc = outcome(); doc['source_evidence'] = ['unqualified string']
        with self.assertRaises(ContractError): validate_outcome(doc)

    def test_success_or_dosing_needs_endpoint_specific_evidence(self):
        doc = outcome('clinical_success'); doc['success_criterion_evidence'] = 'Fictional prespecified clinical result'
        self.assertTrue(validate_outcome(doc)['binary_eligible'])
        doc = outcome('verified_experimental_dosing'); doc['dosing_evidence'] = 'Fictional first dose source'
        self.assertTrue(validate_outcome(doc)['binary_eligible'])

    def test_registry_negative_requires_complete_ascertainment_and_scope(self):
        self.assertTrue(validate_outcome(outcome(value=0))['binary_eligible'])
        for field, value in [('negative_ascertainment', None), ('same_program_scope', False),
                ('observed_until', '2025-12-01T00:00:00Z'), ('publicly_available_at', '2025-12-01T00:00:00Z')]:
            doc = outcome(value=0); doc[field] = value
            with self.assertRaises(ContractError): validate_outcome(doc)
        with self.assertRaises(ContractError): validate_outcome(outcome('clinical_success', 0))

    def test_structured_negative_rejects_explicitly_incomplete_ascertainment(self):
        doc = outcome(value=0)
        doc['negative_ascertainment'] = {'qualified': False, 'complete': False,
            'observation_cutoff': None, 'absence_of_record_used_as_negative': False}
        with self.assertRaises(ContractError): validate_outcome(doc)

    def test_structured_negative_requires_explicit_qualified_source_and_window(self):
        valid = {'qualified': True, 'complete': True,
            'observation_cutoff': '2026-02-01T00:00:00Z',
            'absence_of_record_used_as_negative': False,
            'source_evidence': reference()['source_evidence']}
        doc = outcome(value=0); doc['negative_ascertainment'] = valid
        result = validate_outcome(doc)
        self.assertTrue(result['binary_eligible'])
        self.assertEqual(result['negative_ascertainment_status'], 'structured_declaration_valid')
        for key, value in [('qualified', False), ('qualified', 1), ('complete', False),
                ('complete', 1), ('observation_cutoff', None),
                ('observation_cutoff', '2025-12-31T00:00:00Z'),
                ('observation_cutoff', '2026-03-02T00:00:00Z'),
                ('observation_cutoff', '2026-02-02T00:00:00Z'),
                ('absence_of_record_used_as_negative', True),
                ('absence_of_record_used_as_negative', None),
                ('source_evidence', []), ('source_evidence', ['unqualified string'])]:
            with self.subTest(key=key, value=value):
                bad = deepcopy(doc); bad['negative_ascertainment'][key] = value
                with self.assertRaises(ContractError): validate_outcome(bad)
        for key in valid:
            bad = deepcopy(doc); bad['negative_ascertainment'].pop(key)
            with self.subTest(missing=key):
                with self.assertRaises(ContractError): validate_outcome(bad)

    def test_legacy_negative_string_is_explicitly_unverified_and_other_types_rejected(self):
        result = validate_outcome(outcome(value=0))
        self.assertEqual(result['negative_ascertainment_status'], 'legacy_declaration_unverified')
        self.assertEqual(result['negative_ascertainment_validation'],
            'Contract declarations do not independently verify clinical follow-up.')
        for bad in ('', '   ', True, 1, ['not evidence'], {}):
            doc = outcome(value=0); doc['negative_ascertainment'] = bad
            with self.subTest(value=bad):
                with self.assertRaises(ContractError): validate_outcome(doc)

    def test_unknown_censoring_competing_events_never_binary_negative(self):
        for state in ('unresolved', 'censored', 'competing_event'):
            doc = outcome(value=0); doc['status'] = state
            with self.assertRaises(ContractError): validate_outcome(doc)
            doc['value'] = None
            self.assertFalse(validate_outcome(doc)['binary_eligible'])

    def test_outcome_dates_conflicts_and_boolean_labels_rejected(self):
        for field, value in [('event_at', '2026-02-01T00:00:00Z'), ('value', True),
                ('publicly_available_at', '2026-05-01T00:00:00Z'), ('ascertainment_at', '2025-12-01T00:00:00Z'),
                ('origin_at', '2025-01-01')]:
            doc = outcome(); doc[field] = value
            with self.assertRaises(ContractError): validate_outcome(doc)

    def test_new_computation_from_old_inputs_allowed_but_new_information_not(self):
        inputs = [{'sha256': 'a' * 64, 'available_by': '2022-12-01T00:00:00Z', 'role': 'agent_evidence'}]
        self.assertTrue(validate_feature_chronology('2023-01-01T00:00:00Z', inputs)['new_computation_on_old_inputs_allowed'])
        for modified in [[], [{**inputs[0], 'available_by': '2023-01-02T00:00:00Z'}],
                         [{**inputs[0], 'role': 'evaluation_only'}]]:
            with self.assertRaises(ContractError): validate_feature_chronology('2023-01-01T00:00:00Z', modified)

    def test_training_and_calibration_check_each_origin_not_test_origin_only(self):
        inputs = [{'sha256': 'a' * 64, 'available_by': '2022-12-01T00:00:00Z', 'role': 'agent_evidence'}]
        model = {'weights_sha256': 'b' * 64, 'released_by': '2024-09-20T00:00:00Z'}
        with self.assertRaises(ContractError):
            validate_feature_chronology('2023-01-01T00:00:00Z', inputs, [model])
        self.assertEqual(validate_feature_chronology('2025-01-01T00:00:00Z', inputs, [model])['status'], 'feature_chronology_valid')
        with self.assertRaises(ContractError):
            validate_feature_chronology('2023-01-01T00:00:00Z', inputs,
                label_available_at='2025-02-01T00:00:00Z', prediction_origin_at='2025-01-01T00:00:00Z')
        validate_feature_chronology('2023-01-01T00:00:00Z', inputs,
            label_available_at='2024-04-01T00:00:00Z', prediction_origin_at='2025-01-01T00:00:00Z')


if __name__ == '__main__': unittest.main()
