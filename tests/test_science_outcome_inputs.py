import copy
import json
import unittest

from asof.serde import ContractError, fingerprint
from tools.science.outcome_inputs import (BEGIN, CHILD_COLUMNS, FOLLOWUP_COLUMNS, ORIGIN_COLUMNS,
    candidate_query, normalized_alias, parse_jsonl, regenerate_request, schema_from_audit,
    study_query, validate_candidates, validate_study_rows)


A = 'NCT00000001'
B = 'NCT00000002'


def schema():
    return {'studies': list(FOLLOWUP_COLUMNS), **{t:list(c) for t,c in CHILD_COLUMNS.items()}}


def study(request, nct=A, **values):
    result = {'study':dict.fromkeys(request['projection']['studies'])}
    result['study'].update(nct_id=nct, last_update_posted_date='2024-12-27',
        study_first_posted_date='2010-01-01', last_update_posted_date_type='Actual')
    result['study'].update(values)
    result.update({t:[] for t in request['projection'] if t!='studies'})
    return result


def candidate(nct=A, owner=A, term="o'brien (a)-2"):
    return {'origin_nct_id':owner,'nct_id':nct,'matches':[{'intervention_id':1,
        'intervention_type':'Drug','source_name':" O'Brien (A)-2 ",'alias':term}]}


class OutcomeInputsTests(unittest.TestCase):
    def test_explicit_origin_and_followup_projection_transaction_and_no_results(self):
        for day in ('2025-01-01','2026-01-01','2026-04-01'):
            request=study_query([B,A],day,schema())
            self.assertEqual(request['nct_ids'],[A,B])
            self.assertTrue(request['sql'].startswith(BEGIN))
            self.assertTrue(request['sql'].endswith('ROLLBACK;'))
            self.assertNotIn('row_to_json',request['sql'])
            self.assertNotIn('SELECT *',request['sql'])
            self.assertNotIn('ctgov.outcome_measurements',request['sql'])
            self.assertEqual(request,regenerate_request(json.loads(json.dumps(request))))
            self.assertEqual(request['projection']['studies'],list(ORIGIN_COLUMNS if day=='2025-01-01' else FOLLOWUP_COLUMNS))
            self.assertFalse(request['results_tables_included'])

    def test_strict_ids_dates_projection_and_dependency_closure(self):
        for ids in ([],[A,A],["NCT00000001'); DROP TABLE ctgov.studies;--"],['nct00000001'],['NCT1'],[None]):
            with self.subTest(ids=ids),self.assertRaises(ContractError):study_query(ids,'2025-01-01',schema())
        for day in ('2025-01-02','2024-01-01',None):
            with self.assertRaises(ContractError):study_query([A],day,schema())
        for cols in ({'studies':['nct_id','unknown']},{'studies':['nct_id','nct_id']},
                     {'studies':['nct_id',[]]},{'studies':['nct_id'],'outcomes':['id','nct_id']},
                     {'studies':['nct_id'],'intervention_other_names':['id','nct_id','intervention_id']},
                     {'studies':['nct_id'],'intervention_other_names':['id','nct_id']}):
            with self.assertRaises(ContractError):study_query([A],'2025-01-01',schema(),requested_columns=cols)
        with self.assertRaises(ContractError):study_query([A],'2025-01-01',schema(),cutoff_at='2026-04-01T00:00:00Z')

    def test_schema_missingness_explicit_and_never_silently_replaced(self):
        source=schema();source.pop('provided_documents');source['studies'].remove('start_month_year')
        request=study_query([A,B],'2025-01-01',source)
        report=validate_study_rows([study(request)],request)
        self.assertEqual(report['missing_nct_ids'],[B])
        self.assertEqual(report['missing_source_columns']['provided_documents'],list(CHILD_COLUMNS['provided_documents']))
        self.assertIn('start_month_year',report['missing_source_columns']['studies'])
        self.assertEqual(report['version_dispositions'][0]['source_date_intervals']['start']['precision'],'unknown')
        self.assertFalse(report['absence_claim']);self.assertIsNone(report['clinical_label'])
        self.assertFalse(report['origin_membership_changed'])
        bad=schema();bad['interventions'].remove('nct_id')
        with self.assertRaises(ContractError):study_query([A],'2025-01-01',bad)

    def test_request_rehash_does_not_bless_free_sql_or_changed_projection(self):
        for builder in (lambda:study_query([A],'2025-01-01',schema()),
                        lambda:candidate_query({A:["O'Brien (A)-2"]},'2026-04-01',schema())):
            request=builder();expected=request['request_sha256']
            request['sql']=request['sql'].replace('ROLLBACK;','SELECT 1; ROLLBACK;')
            request['request_sha256']=fingerprint({k:v for k,v in request.items() if k!='request_sha256'})
            with self.assertRaises(ContractError):regenerate_request(request)
            with self.assertRaises(ContractError):regenerate_request(request,expected_request_sha256=expected)
        request=study_query([A],'2025-01-01',schema());request['projection']['studies'].append('why_stopped')
        with self.assertRaises(ContractError):validate_study_rows([],request)

    def test_alias_sql_escaping_exact_ascii_punctuation_and_all_phase_inclusion(self):
        request=candidate_query({A:[" O'Brien (A)-2 ","x');select 1;--"]},'2026-04-01',schema(),
            per_origin_cap=5000,total_cap=20000)
        self.assertIn("o''brien (a)-2",request['sql'])
        self.assertIn("x'');select 1;--",request['sql'])
        self.assertIn('n.intervention_id=i.id AND n.nct_id=i.nct_id',request['sql'])
        self.assertIn("IN ('drug','biological')",request['sql'])
        for forbidden in ('LIMIT ','phase','start_date','overall_status','NOT IN',' <> '):
            self.assertNotIn(forbidden,request['sql'])
        self.assertEqual(normalized_alias(' A-B (C)  D '),'a-b (c)  d')
        self.assertEqual(validate_candidates([candidate()],request)['candidate_nct_ids'],[A])
        for alias in ('','  ','é','A\x00B','A\nB'):
            with self.assertRaises(ContractError):candidate_query({A:[alias]},'2026-04-01',schema())
        with self.assertRaises(ContractError):candidate_query({A:['ABC',' abc ']},'2026-04-01',schema())

    def test_candidate_caps_fail_preserve_raw_and_zero_is_not_absence(self):
        request=candidate_query({A:["O'Brien (A)-2"],B:['different']},'2026-04-01',schema(),per_origin_cap=1,total_cap=1)
        rows=[candidate(),candidate(B)]
        original=copy.deepcopy(rows)
        with self.assertRaises(ContractError):validate_candidates(rows,request)
        self.assertEqual(rows,original)
        empty=validate_candidates([],request)
        self.assertEqual(empty['per_origin_counts'],{A:0,B:0})
        self.assertFalse(empty['absence_claim']);self.assertIsNone(empty['clinical_label'])
        report=validate_candidates([candidate()],request)
        report['quarantined_candidates'][0]['matches'][0]['alias']='changed'
        self.assertEqual(rows,original)

    def test_candidate_duplicate_out_of_order_wrong_scope_or_nonexact_match_rejected(self):
        request=candidate_query({A:["O'Brien (A)-2"]},'2026-04-01',schema())
        cases=[[candidate(),candidate()], [candidate(B),candidate()], [candidate(owner=B)]]
        for field,value in (('source_name','OBrien (A)-2'),('intervention_type','Procedure'),('alias','different'),('intervention_id',True)):
            row=candidate();row['matches'][0][field]=value;cases.append([row])
        row=candidate();row['matches'].append(copy.deepcopy(row['matches'][0]));cases.append([row])
        row=candidate();row['matches'][0]['unexpected']=1;cases.append([row])
        for rows in cases:
            with self.assertRaises(ContractError):validate_candidates(rows,request)

    def test_shared_candidate_counts_once_for_distinct_trial_cap(self):
        request=candidate_query({A:["O'Brien (A)-2"],B:["O'Brien (A)-2"]},'2026-04-01',schema(),
            per_origin_cap=1,total_cap=1)
        result=validate_candidates([candidate(),candidate(owner=B)],request)
        self.assertEqual(result['candidate_pairs'],2)
        self.assertEqual(result['total_distinct_trials'],1)
        self.assertEqual(result['per_origin_counts'],{A:1,B:1})

    def test_study_duplicate_order_bound_unknown_columns_and_cross_trial_children(self):
        request=study_query([A,B],'2025-01-01',schema(),max_ids=2)
        cases=[[study(request),study(request)],[study(request,B),study(request,A)],
               [study(request),study(request,B),study(request,'NCT00000003')]]
        row=study(request);row['study']['unknown']=1;cases.append([row])
        row=study(request);row['interventions']=[dict.fromkeys(request['projection']['interventions'])]
        row['interventions'][0].update(id=1,nct_id=B);cases.append([row])
        row=study(request);row['conditions']=[{'id':2,'nct_id':A,'name':'x'},{'id':1,'nct_id':A,'name':'y'}];cases.append([row])
        row=study(request);row['conditions']=[{'id':1,'nct_id':A,'name':'x'}]*2;cases.append([row])
        for rows in cases:
            with self.assertRaises(ContractError):validate_study_rows(rows,request)

    def test_child_foreign_keys_must_resolve_within_same_study(self):
        request=study_query([A],'2025-01-01',schema());row=study(request)
        row['intervention_other_names']=[{'id':5,'nct_id':A,'intervention_id':1,'name':'x'}]
        with self.assertRaises(ContractError):validate_study_rows([row],request)
        intervention=dict.fromkeys(request['projection']['interventions']);intervention.update(id=1,nct_id=A)
        row['interventions']=[intervention]
        validate_study_rows([row],request)
        row['design_group_interventions']=[{'id':6,'nct_id':A,'intervention_id':1,'design_group_id':2}]
        with self.assertRaises(ContractError):validate_study_rows([row],request)
        arm=dict.fromkeys(request['projection']['design_groups']);arm.update(id=2,nct_id=A)
        row['design_groups']=[arm]
        validate_study_rows([row],request)

    def test_latest_version_not_backdated_and_boundary_kept_quarantined(self):
        request=study_query([A],'2026-04-01',schema())
        for day,expected in [('2026-03-30','eligible_reconstructed_date_bound'),
                             ('2026-03-31','held_boundary_uncertain'),('2026-04-01','held_boundary_uncertain'),
                             ('2026-04-02','held_posting_date_after_source_snapshot'),(None,'held_missing_version_date'),
                             ('2026-03','held_missing_version_date')]:
            row=study(request,last_update_posted_date=day)
            report=validate_study_rows([row],request)
            self.assertEqual(report['version_dispositions'][0]['version_eligibility']['status'],expected)
            self.assertEqual(report['quarantined_rows'],[row])
            self.assertEqual(bool(report['eligible_reconstructed_rows']),expected.startswith('eligible'))
            self.assertFalse(report['absence_claim']);self.assertIsNone(report['clinical_label'])
        with self.assertRaises(ContractError):validate_study_rows([study(request)],request,cutoff_at='2026-04-02T00:00:00Z')
        report=validate_study_rows([study(request,last_update_posted_date_type='Anticipated')],request)
        self.assertEqual(report['version_dispositions'][0]['version_eligibility']['status'],'held_unqualified_posting_date_type')
        report=validate_study_rows([study(request,last_update_posted_date_type=None)],request)
        self.assertEqual(report['version_dispositions'][0]['version_eligibility']['status'],'held_unqualified_posting_date_type')
        january=study_query([A],'2026-01-01',schema())
        report=validate_study_rows([study(january,last_update_posted_date='2026-02-01')],january)
        self.assertEqual(report['version_dispositions'][0]['version_eligibility']['status'],'held_posting_date_after_source_snapshot')

    def test_original_start_precision_never_refined_by_imputed_date(self):
        request=study_query([A],'2025-01-01',schema())
        for raw,precision in [(None,'unknown'),('January 2024','month'),('2024','year'),('January 12, 2024','day')]:
            row=study(request,start_date='2024-01-12',start_month_year=raw,start_date_type='Actual')
            result=validate_study_rows([row],request)['version_dispositions'][0]['source_date_intervals']['start']
            self.assertEqual(result['precision'],precision)
            self.assertFalse(result['event_inferred'])

    def test_jsonl_rejects_duplicate_keys_nonfinite_noise_and_nonobjects(self):
        self.assertEqual(parse_jsonl(' {"id":1}\n\n{"id":2}\n'),[{'id':1},{'id':2}])
        for text in ('{"id":1,"id":2}','{"x":{"k":1,"k":2}}','{"n":NaN}','BEGIN\n{}','[]','null','{bad}'):
            with self.assertRaises(ContractError):parse_jsonl(text)

    def test_schema_metadata_only_ctgov_and_duplicate_columns_fail(self):
        records=[{'table_schema':'ctgov','table_name':'studies','column_name':'nct_id'},
                 {'table_schema':'public','table_name':'secrets','column_name':'value'}]
        self.assertEqual(schema_from_audit({'columns':records}),{'studies':['nct_id']})
        with self.assertRaises(ContractError):schema_from_audit({'columns':records+[records[0]]})


if __name__=='__main__':unittest.main()
