import copy
from pathlib import Path
import tempfile
import unittest

from tools.science.fresh_cases import dependency_groups, freeze, resolve_cases


class FreshCaseTests(unittest.TestCase):
    def inputs(self):
        proposal = {'symbol': 'GENE', 'requested_disease_name': 'disease',
                    'intended_action': 'inhibit', 'modality': 'antibody', 'tissue': None}
        gene = {'symbol': 'GENE', 'status': 'Approved', 'ensembl_gene_id': 'ENSG1',
                'hgnc_id': 'HGNC:1', 'gene_group_id': '10|20', '_locator': {'row': 1}}
        target = {'id': 'ENSG1', 'approvedSymbol': 'GENE', '_locator': {'row': 2}}
        disease = {'id': 'EFO_1', 'name': 'disease', 'synonyms': {}, '_locator': {'row': 3}}
        return [proposal], [gene], [target], [disease]

    def test_exact_identity_preserved(self):
        cases = resolve_cases(*self.inputs())
        self.assertEqual(cases[0]['target_id'], 'ENSG1')
        self.assertIsNone(cases[0]['tissue'])
        self.assertEqual(cases[0]['hgnc_gene_group_ids'], ['10', '20'])
        self.assertEqual(len(cases[0]['scope_sha256']), 64)

    def test_missing_or_ambiguous_gene_fails(self):
        for mode in ['missing', 'duplicate', 'unapproved']:
            args = self.inputs()
            if mode == 'missing':
                args[1].clear()
            elif mode == 'duplicate':
                args[1].append(copy.deepcopy(args[1][0]))
            else:
                args[1][0]['status'] = 'Withdrawn'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                resolve_cases(*args)

    def test_wrong_or_duplicate_target_fails(self):
        for mode in ['wrong', 'missing', 'duplicate']:
            args = self.inputs()
            if mode == 'wrong':
                args[2][0]['approvedSymbol'] = 'OTHER'
            elif mode == 'missing':
                args[2].clear()
            else:
                args[2].append(copy.deepcopy(args[2][0]))
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                resolve_cases(*args)

    def test_ambiguous_disease_requires_explicit_choice_and_reason(self):
        args = self.inputs()
        args[3].append({**args[3][0], 'id': 'HP_1'})
        with self.assertRaises(ValueError):
            resolve_cases(*args)
        args[0][0]['disease_id'] = 'EFO_1'
        with self.assertRaises(ValueError):
            resolve_cases(*args)
        args[0][0]['identity_choice_reason'] = 'Disease namespace rather than phenotype alias'
        case = resolve_cases(*args)[0]
        self.assertEqual(case['resolution_provenance']['disease_exact_match_alternatives'], ['EFO_1', 'HP_1'])

    def test_wrong_explicit_or_missing_disease_fails(self):
        args = self.inputs()
        args[0][0]['disease_id'] = 'EFO_WRONG'
        with self.assertRaises(ValueError):
            resolve_cases(*args)
        args = self.inputs()
        args[3].clear()
        with self.assertRaises(ValueError):
            resolve_cases(*args)

    def test_duplicates_and_exposed_targets_fail(self):
        args = self.inputs()
        args[0].append(copy.deepcopy(args[0][0]))
        with self.assertRaises(ValueError):
            resolve_cases(*args)
        with self.assertRaises(ValueError):
            resolve_cases(*self.inputs(), exposed=[('GENE', 'EFO_OLD', 'activate', 'peptide')])

    def test_family_dependency_transitive_not_case_count_independence(self):
        case = resolve_cases(*self.inputs())[0]
        second = {**case, 'case_id': 'second', 'target_id': 'ENSG2', 'disease_id': 'EFO_2', 'hgnc_gene_group_ids': ['20', '30']}
        third = {**case, 'case_id': 'third', 'target_id': 'ENSG3', 'disease_id': 'EFO_3', 'hgnc_gene_group_ids': ['30']}
        result = dependency_groups([case, second, third])
        self.assertEqual(len(result['groups']), 1)
        self.assertEqual(len(result['links']), 2)
        self.assertIn('not ten proven independent', result['unmeasured_dependence'])

    def test_action_and_tissue_fail_closed(self):
        for key, value in [('tissue', 'brain'), ('intended_action', ''), ('modality', '')]:
            args = self.inputs()
            args[0][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                resolve_cases(*args)

    def test_frozen_reexecution_refused_before_source_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'casepack.json'
            marker.write_text('existing', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                freeze('missing', 'missing', 'missing', root)
            self.assertEqual(marker.read_text(encoding='utf-8'), 'existing')


if __name__ == '__main__':
    unittest.main()
