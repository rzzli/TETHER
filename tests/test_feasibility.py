"""Guard scientific selection and allele direction, without requiring private data."""
import copy
import unittest
from tools.feasibility.audit_clinical_origin import select
from tools.feasibility.qc_genetics_region import effect_orientation, valid_stats


class FeasibilityTests(unittest.TestCase):
    def fixture(self):
        protocol={'seed_targets_and_drug_terms':{'GENE':['drug']},
            'eligible_phases':['Phase 2'],'eligible_origin_states':['RECRUITING'],
            'origin_date':'2023-01-01','requested_programs':24}
        row={'nct_id':'NCT00000001','overall_status':'Recruiting','study_type':'Interventional',
            'phase':'Phase 2','study_first_posted_date':'2020-01-01',
            'last_update_posted_date':'2022-01-01','conditions':['Disease'],
            'interventions':[{'name':'Drug','aliases':[]}]}
        return protocol,row

    def test_future_origin_update_and_missing_first_posted_are_excluded(self):
        p,r=self.fixture();r['last_update_posted_date']='2023-01-02'
        chosen,excluded=select([r],p)
        self.assertEqual(chosen,[])
        self.assertIn('future_origin_record_update',excluded[0]['reasons'])
        r['last_update_posted_date']='2022-01-01';r['study_first_posted_date']=None
        self.assertEqual(select([r],p)[0],[])

    def test_followup_outcomes_cannot_label_or_change_selection(self):
        p,r=self.fixture();before=select([r],p)[0]
        r['current_status']='COMPLETED';r['current_result']='positive'
        after=select([r],p)[0]
        self.assertEqual(before[0]['selection_hash'],after[0]['selection_hash'])
        self.assertIsNone(after[0]['therapeutic_success'])
        self.assertIsNone(after[0]['clinical_failure'])
        self.assertIsNone(after[0]['event_date'])

    def test_duplicate_program_and_input_order_do_not_inflate_sample(self):
        p,r=self.fixture();other=copy.deepcopy(r);other['nct_id']='NCT00000002'
        a=select([r,other],p)[0];b=select([other,r],p)[0]
        self.assertEqual(len(a),1)
        self.assertEqual(a,b)

    def test_swapped_gwas_effect_allele_changes_beta_sign(self):
        self.assertEqual(effect_orientation('A','C','C','A'),1)
        self.assertEqual(effect_orientation('A','C','A','C'),-1)

    def test_ambiguous_and_unmatched_alleles_are_not_aligned(self):
        for alleles in [('A','T','T','A'),('C','G','G','C'),('A','C','G','T'),('A','AC','AC','A')]:
            self.assertIsNone(effect_orientation(*alleles))

    def test_invalid_statistics_fail_qc(self):
        for values in [('nan','1','0.5'),('1','0','0.5'),('1','-1','0.5'),('1','1','2'),('1','NA','0.1')]:
            self.assertFalse(valid_stats(*values))
        self.assertTrue(valid_stats('0.1','0.02','0.001'))

    def test_identical_ref_alt_cannot_be_an_oriented_snp(self):
        for allele in 'ACGT':
            with self.subTest(allele=allele):
                self.assertIsNone(effect_orientation(allele, allele, allele, allele))

    def test_identical_effect_other_alleles_are_not_aligned(self):
        for alleles in [('A', 'C', 'A', 'A'), ('A', 'C', 'C', 'C')]:
            self.assertIsNone(effect_orientation(*alleles))


if __name__=='__main__':unittest.main()
