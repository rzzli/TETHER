"""Synthetic contract tests; assertions are not biological reference labels."""
import copy
import tempfile
import unittest
from pathlib import Path

from asof.serde import ContractError, fingerprint, write_json
from tools.science.run_comparison import pin
from tools.science.t6_claim_audit import audit_claims, pointer


class AtomicClaimAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = {'rows': [{'target': 'TEST', 'association': True, 'tissue': 'liver'}]}
        self.path = self.root / 'original.json'
        write_json(self.path, self.raw)
        self.sources = [dict(source_id='s1', original=pin(self.path), format='json',
                             json_pointer='/rows/0', value_sha256=fingerprint(self.raw['rows'][0]))]
        question = dict(target_id='TEST', indication_id='DISEASE', intended_action='inhibit',
                        target_namespace_version='fixture-v1', indication_namespace_version='fixture-v1',
                        modality='antibody', tissue=None)
        self.manifest = dict(schema_version=1, role='evaluation_only', question=question,
            dossier_sha256='a' * 64, atomization_status='reviewed_complete', atomizer_id='atomizer-A',
            claims=[dict(claim_id='c1', statement='The source reports an association for TEST.',
                         kind='resource_observation', question_sha256=fingerprint(question),
                         atomicity_attested=True, cited_source_ids=['s1'])])
        self.review = dict(schema_version=1, role='evaluation_only', reviewer_id='reviewer-A',
            review_mode='blinded_source_review', therapeutic_truth='not_established',
            claims_sha256=fingerprint(self.manifest), sources_sha256=fingerprint(self.sources),
            claims=[dict(claim_id='c1', entailment='supported', applicability='not_claimed',
                         citation_status='supported',
                         reason='Synthetic original reports association only.', uncertainty='high',
                         evidence_source_ids=['s1'])])

    def run_audit(self, rebind=False):
        if rebind:
            self.review['claims_sha256'] = fingerprint(self.manifest)
            self.review['sources_sha256'] = fingerprint(self.sources)
        return audit_claims(self.manifest, self.review, self.sources, [self.root])

    def test_source_supported_does_not_certify_therapeutic_truth(self):
        result = self.run_audit()
        self.assertEqual(result['entailment']['supported'], 1)
        self.assertEqual(result['therapeutic_truth'], 'not_established')
        self.assertEqual(result['contradiction_fraction_assessable'], 0)

    def test_action_modality_and_tissue_cannot_reuse_question_binding(self):
        for key, value in [('intended_action', 'activate'), ('modality', 'ADC'), ('tissue', 'brain'),
                           ('target_namespace_version', 'v2'), ('indication_namespace_version', 'v2')]:
            with self.subTest(key=key):
                modified = copy.deepcopy(self.manifest)
                modified['question'][key] = value
                review = dict(self.review, claims_sha256=fingerprint(modified))
                with self.assertRaises(ContractError):
                    audit_claims(modified, review, self.sources, [self.root])

    def test_faithful_annotation_can_be_context_mismatch(self):
        self.review['claims'][0]['applicability'] = 'context_mismatch'
        result = self.run_audit()
        self.assertEqual(result['entailment']['supported'], 1)
        self.assertEqual(result['applicability']['context_mismatch'], 1)

    def test_genetics_to_efficacy_overreach_is_unsupported_not_automatically_false(self):
        self.manifest['claims'][0].update(kind='scientific_interpretation',
                                          statement='Inhibition will improve clinical efficacy.')
        self.review['claims'][0].update(entailment='unsupported', applicability='uncertain',
                                        citation_status='misattributed',
                                        reason='Association does not establish intervention efficacy.')
        result = self.run_audit(rebind=True)
        self.assertEqual(result['unsupported_fraction_assessable'], 1)
        self.assertEqual(result['contradiction_fraction_assessable'], 0)

    def test_unsupported_and_contradiction_are_separate(self):
        self.review['claims'][0]['entailment'] = 'contradicted'
        self.review['claims'][0]['citation_status'] = 'misattributed'
        result = self.run_audit()
        self.assertEqual(result['contradiction_fraction_assessable'], 1)
        self.assertEqual(result['unsupported_fraction_assessable'], 0)

    def test_unassessable_and_empty_do_not_become_zero_error(self):
        self.review['claims'][0].update(entailment='unassessable', evidence_source_ids=[],
                                        citation_status='unassessable')
        self.assertIsNone(self.run_audit()['contradiction_fraction_assessable'])
        self.manifest['claims'] = []
        self.review['claims'] = []
        result = self.run_audit(rebind=True)
        self.assertEqual(result['claim_count'], 0)
        self.assertIsNone(result['unsupported_fraction_assessable'])

    def test_substantive_judgment_requires_evidence(self):
        self.review['claims'][0]['evidence_source_ids'] = []
        with self.assertRaises(ContractError):
            self.run_audit()

    def test_unknown_foreign_or_duplicate_sources_fail(self):
        for field, ids in [('cited_source_ids', ['foreign']), ('cited_source_ids', ['s1', 's1'])]:
            value = copy.deepcopy(self.manifest)
            value['claims'][0][field] = ids
            review = dict(self.review, claims_sha256=fingerprint(value))
            with self.assertRaises(ContractError):
                audit_claims(value, review, self.sources, [self.root])
        self.review['claims'][0]['evidence_source_ids'] = ['foreign']
        with self.assertRaises(ContractError):
            self.run_audit()

    def test_duplicates_do_not_become_independent_source_units(self):
        self.sources.append(dict(self.sources[0], source_id='s2'))
        with self.assertRaises(ContractError):
            self.run_audit(rebind=True)

    def test_missing_duplicate_and_reordered_claims_fail(self):
        self.manifest['claims'].append(dict(self.manifest['claims'][0], claim_id='c2',
                                             statement='The source describes liver tissue.'))
        for rows in [[], [self.review['claims'][0]] * 2,
                     [dict(self.review['claims'][0], claim_id='c2'), self.review['claims'][0]]]:
            self.review['claims'] = rows
            with self.assertRaises(ContractError):
                self.run_audit(rebind=True)

    def test_omitted_context_cannot_skip_interpretation_applicability(self):
        self.manifest['claims'][0]['kind'] = 'scientific_interpretation'
        with self.assertRaises(ContractError):
            self.run_audit(rebind=True)

    def test_unattested_atomization_and_wrong_role_fail(self):
        for change in [dict(atomization_status='automatic_unreviewed'), dict(role='agent_visible'),
                       dict(schema_version=True)]:
            manifest = dict(self.manifest, **change)
            with self.assertRaises(ContractError):
                audit_claims(manifest, self.review, self.sources, [self.root])
        self.manifest['claims'][0]['atomicity_attested'] = False
        with self.assertRaises(ContractError):
            self.run_audit(rebind=True)

    def test_changed_source_and_changed_original_row_fail(self):
        write_json(self.path, {'rows': [{'association': False}]})
        with self.assertRaises(ContractError):
            self.run_audit()
        self.sources[0]['original'] = pin(self.path)
        with self.assertRaises(ContractError):
            self.run_audit(rebind=True)

    def test_foreign_root_fails(self):
        with self.assertRaises(ContractError):
            audit_claims(self.manifest, self.review, self.sources, [self.root / 'other'])

    def test_unqualified_columnar_and_pdf_adapters_fail_explicitly(self):
        for format_name in ['parquet', 'pdf', None]:
            self.sources[0]['format'] = format_name
            with self.assertRaisesRegex(ContractError, 'Unqualified source format'):
                self.run_audit(rebind=True)

    def test_invalid_pointer_forms_fail(self):
        for location in ['/rows/-1', '/rows/00', '/rows/99', '/rows/0/missing', '/rows/~2', 'rows']:
            with self.subTest(location=location), self.assertRaises(ContractError):
                pointer(self.raw, location)
        self.assertEqual(pointer({'a/b': {'~': 3}}, '/a~1b/~0'), 3)

    def test_review_binding_and_therapeutic_truth_promotion_fail(self):
        self.review['claims_sha256'] = 'b' * 64
        with self.assertRaises(ContractError):
            self.run_audit()
        self.review['therapeutic_truth'] = 'validated'
        with self.assertRaises(ContractError):
            self.run_audit(rebind=True)

    def test_size_bound_and_invalid_proof_fail(self):
        for size in [True, -1, 64 * 1024 * 1024 + 1]:
            self.sources[0]['original']['bytes'] = size
            with self.assertRaises(ContractError):
                self.run_audit(rebind=True)

    def test_input_reviews_are_not_mutated(self):
        original = copy.deepcopy((self.manifest, self.review, self.sources))
        self.run_audit()
        self.assertEqual(original, (self.manifest, self.review, self.sources))

    def test_repeated_statement_cannot_inflate_denominator(self):
        self.manifest['claims'].append(dict(self.manifest['claims'][0], claim_id='c2'))
        self.review['claims'].append(dict(self.review['claims'][0], claim_id='c2'))
        with self.assertRaisesRegex(ContractError, 'Repeated atomic statement'):
            self.run_audit(rebind=True)

    def test_true_but_uncited_claim_keeps_missing_citation(self):
        self.manifest['claims'][0]['cited_source_ids'] = []
        self.review['claims'][0]['citation_status'] = 'missing'
        result = self.run_audit(rebind=True)
        self.assertEqual(result['entailment']['supported'], 1)
        self.assertEqual(result['citation_status']['missing'], 1)

    def test_citation_support_requires_actual_cited_evidence(self):
        self.manifest['claims'][0]['cited_source_ids'] = []
        with self.assertRaises(ContractError):
            self.run_audit(rebind=True)

    def test_malformed_state_types_raise_contract_errors(self):
        for field in ('entailment', 'applicability', 'citation_status', 'uncertainty'):
            review = copy.deepcopy(self.review)
            review['claims'][0][field] = []
            with self.subTest(field=field), self.assertRaises(ContractError):
                audit_claims(self.manifest, review, self.sources, [self.root])


if __name__ == '__main__':
    unittest.main()
