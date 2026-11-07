import copy
import unittest

from tether_engine.serde import ContractError,fingerprint
from tools.science.outcome_results import RESULT_FIELDS,STUDY_FIELDS,results_query,regenerate_results,validate_result_rows


class ReportedResultsTests(unittest.TestCase):
    def setUp(self):
        self.ids=[f'NCT{i:08d}' for i in range(1,13)]
        self.schema={'studies':list(STUDY_FIELDS),**{k:list(v) for k,v in RESULT_FIELDS.items()}}
        self.request=results_query(self.ids,'2026-04-01',self.schema)

    def envelope(self,nct=None):
        study={c:None for c in STUDY_FIELDS}
        study.update(nct_id=nct or self.ids[0],last_update_posted_date='2026-02-01',
            last_update_posted_date_type='ACTUAL',study_first_posted_date='2023-01-02',
            results_first_posted_date='2026-02-01',results_first_posted_date_type='ACTUAL')
        row={'study':study,**{t:[] for t in RESULT_FIELDS}}
        for index,table in enumerate(RESULT_FIELDS,1):
            c={name:None for name in RESULT_FIELDS[table]}
            c.update(id=index,nct_id=study['nct_id'])
            if 'outcome_id' in c:c['outcome_id']=1
            if 'result_group_id' in c:c['result_group_id']=2
            if 'outcome_analysis_id' in c:c['outcome_analysis_id']=3
            row[table]=[c]
        return row

    def test_explicit_frozen_results_projection_has_no_significance_filter_or_truncation(self):
        self.assertEqual(self.request,regenerate_results(self.request))
        self.assertTrue(self.request['sql'].startswith('BEGIN TRANSACTION'))
        self.assertNotIn('SELECT *',self.request['sql']);self.assertNotIn(' LIMIT ',self.request['sql'])
        self.assertIn("'overflow',true",self.request['sql'])
        self.assertEqual(set(RESULT_FIELDS)|{'studies'},set(self.request['projection']))
        for field in ('p_value_raw','ci_lower_limit_raw','non_inferiority_description','method_description'):
            self.assertIn(field,self.request['projection']['outcome_analyses'])

    def test_request_self_hash_cannot_bless_injected_sql_projection_or_role(self):
        for key,value in [('sql',self.request['sql'].replace('ROLLBACK;','COMMIT;')),
            ('role','agent_evidence'),('cutoff_at','2027-01-01T00:00:00Z'),('automatic_labels',True)]:
            r=copy.deepcopy(self.request);r[key]=value
            r['request_sha256']=fingerprint({k:v for k,v in r.items() if k!='request_sha256'})
            with self.subTest(key=key),self.assertRaises(ContractError):regenerate_results(r)

    def test_twelve_members_followup_dates_and_row_bound_are_required(self):
        for ids,date,cap in [(self.ids[:11],'2026-04-01',10),(self.ids+[self.ids[0]],'2026-04-01',10),
            (self.ids,'2025-01-01',10),(self.ids,'2026-04-01',True),(self.ids,'2026-04-01',100001)]:
            with self.subTest(date=date,cap=cap),self.assertRaises(ContractError):results_query(ids,date,self.schema,max_rows_per_trial=cap)

    def test_actual_format_nulls_and_raw_numeric_text_are_retained_without_labels(self):
        row=self.envelope();row['outcome_analyses'][0].update(p_value_raw='<0.001',p_value=None)
        report=validate_result_rows([row],self.request)
        self.assertEqual(row,report['eligible_reconstructed_rows'][0])
        self.assertIsNone(report['clinical_label']);self.assertFalse(report['absence_claim'])
        self.assertFalse(report['prespecified_success_rule_checked'])
        self.assertEqual(11,len(report['missing_nct_ids']))

    def test_missing_result_rows_and_missing_source_table_are_not_negatives(self):
        row=self.envelope()
        for table in RESULT_FIELDS:row[table]=[]
        report=validate_result_rows([row],self.request)
        self.assertFalse(report['version_dispositions'][0]['reported_results_present'])
        self.assertIsNone(report['clinical_label'])
        schema=copy.deepcopy(self.schema);schema.pop('outcome_analysis_groups')
        r=results_query(self.ids,'2026-04-01',schema)
        self.assertIn('outcome_analysis_groups',r['missing_source_columns'])

    def test_temporally_held_payloads_never_enter_eligible_results(self):
        for date,date_type in [('2026-03-31','ACTUAL'),('2026-04-01','ACTUAL'),
            ('2026-01-02','ESTIMATED'),(None,'ACTUAL')]:
            row=self.envelope();row['study'].update(last_update_posted_date=date,last_update_posted_date_type=date_type)
            r=validate_result_rows([row],self.request)
            self.assertEqual([],r['eligible_reconstructed_rows']);self.assertEqual([row],r['quarantined_rows'])
        row=self.envelope();row['study'].update(last_update_posted_date='2026-01-02',results_first_posted_date='2025-12-01')
        r=results_query(self.ids,'2026-01-01',self.schema)
        self.assertEqual('held_posting_date_after_source_snapshot',validate_result_rows([row],r)['version_dispositions'][0]['version_eligibility']['status'])

    def test_duplicate_cross_trial_child_and_unprojected_fields_fail(self):
        for kind in ('duplicate','cross_trial','extra'):
            row=self.envelope()
            if kind=='duplicate':row['outcomes']*=2
            if kind=='cross_trial':row['outcomes'][0]['nct_id']=self.ids[1]
            if kind=='extra':row['outcomes'][0]['inferred_success']=True
            with self.subTest(kind=kind),self.assertRaises(ContractError):validate_result_rows([row],self.request)

    def test_broken_foreign_keys_and_group_outcome_scope_fail(self):
        for table,field in [('outcome_analyses','outcome_id'),('outcome_measurements','result_group_id'),
            ('outcome_analysis_groups','outcome_analysis_id'),('result_groups','outcome_id')]:
            row=self.envelope();row[table][0][field]=999
            with self.subTest(table=table),self.assertRaises(ContractError):validate_result_rows([row],self.request)
        row=self.envelope();extra=copy.deepcopy(row['outcomes'][0]);extra['id']=99;row['outcomes'].append(extra)
        row['result_groups'][0]['outcome_id']=99
        with self.assertRaises(ContractError):validate_result_rows([row],self.request)

    def test_overflow_is_explicit_failure_not_partial_success(self):
        with self.assertRaises(ContractError):validate_result_rows([{'overflow':True,'nct_id':self.ids[0],'result_rows':100001}],self.request)
        r=results_query(self.ids,'2026-04-01',self.schema,max_rows_per_trial=5)
        with self.assertRaises(ContractError):validate_result_rows([self.envelope()],r)

    def test_missing_parent_table_and_missing_identity_are_rejected(self):
        schema=copy.deepcopy(self.schema);schema.pop('outcomes')
        with self.assertRaises(ContractError):results_query(self.ids,'2026-04-01',schema)
        schema=copy.deepcopy(self.schema);schema['outcome_counts'].remove('result_group_id')
        with self.assertRaises(ContractError):results_query(self.ids,'2026-04-01',schema)

    def test_membership_order_and_unrequested_trial_fail(self):
        row=self.envelope('NCT99999999')
        with self.assertRaises(ContractError):validate_result_rows([row],self.request)
        with self.assertRaises(ContractError):validate_result_rows([self.envelope(self.ids[1]),self.envelope()],self.request)
        with self.assertRaises(ContractError):validate_result_rows([self.envelope(),self.envelope()],self.request)


if __name__=='__main__':unittest.main()
