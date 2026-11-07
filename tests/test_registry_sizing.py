import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.feasibility.registry_extract import frame_query,validate_row
from tools.feasibility.registry_cohort import arm_facts,start_bounds,build,stratified_sample
from tether_engine.serde import sha256_file
from tools.feasibility.registry_audit import source_check,audit


class RegistryExtractionTests(unittest.TestCase):
    def row(self):
        return {'study':{'nct_id':'NCT06203210','study_first_posted_date':'2024-01-12','last_update_posted_date':'2024-12-04'},
            'conditions':[],'interventions':[{'id':1,'nct_id':'NCT06203210'}],
            'design_groups':[{'id':2,'nct_id':'NCT06203210'}],
            'design_group_interventions':[{'nct_id':'NCT06203210','design_group_id':2,'intervention_id':1}]}

    def test_source_temporal_and_arm_link_failures(self):
        row=self.row();self.assertEqual(validate_row(row,'2025-01-01'),'NCT06203210')
        bad=copy.deepcopy(row);bad['study']['last_update_posted_date']='2025-01-02'
        with self.assertRaises(ValueError):validate_row(bad,'2025-01-01')
        bad=copy.deepcopy(row);bad['design_group_interventions'][0]['intervention_id']=9
        with self.assertRaises(ValueError):validate_row(bad,'2025-01-01')
        bad=copy.deepcopy(row);bad['conditions']=[{'nct_id':'NCT00000000'}]
        with self.assertRaises(ValueError):validate_row(bad,'2025-01-01')

    def test_read_only_scope_preserves_prior_phase_and_late_disclosure(self):
        origin=frame_query('2023-01-01','2023-01-01','2025-01-01')
        followup=frame_query('2025-01-01','2023-01-01','2025-01-01')
        self.assertIn('REPEATABLE READ READ ONLY',origin)
        self.assertIn('PHASE4',origin)
        self.assertIn('WITH selected AS MATERIALIZED',origin)
        self.assertNotIn('WHERE t.nct_id=s.nct_id',origin)
        self.assertIn("s.study_first_posted_date>DATE '2023-01-01'",followup)
        self.assertTrue(followup.endswith('ROLLBACK;\n'))
        with self.assertRaises(ValueError):frame_query("2025-01-01'; SELECT 1",'2023-01-01','2025-01-01')


def trial(nct='NCT00000001',drug='ExampleA',phase='Phase 2',status='Recruiting',start='2022-02-01',kind='Actual',posted='2022-01-01'):
    return {'study':{'nct_id':nct,'brief_title':'Synthetic study','official_title':'Synthetic study','study_type':'Interventional',
        'phase':phase,'overall_status':status,'start_date':start,'start_month_year':start,'start_date_type':kind,
        'study_first_posted_date':posted,'last_update_posted_date':posted},
        'conditions':[{'id':1,'nct_id':nct,'name':'Condition X'}],
        'interventions':[{'id':1,'nct_id':nct,'name':drug,'intervention_type':'Drug','description':'Study treatment'}],
        'intervention_other_names':[],
        'design_groups':[{'id':2,'nct_id':nct,'group_type':'Experimental','title':drug,'description':'Study treatment'}],
        'design_group_interventions':[{'id':3,'nct_id':nct,'design_group_id':2,'intervention_id':1}],
        'sponsors':[],'brief_summaries':[]}


class RegistryCohortTests(unittest.TestCase):
    def aliases(self):return {'examplea':{'CHEMBL-A'},'exampleb':{'CHEMBL-B'},'examplec':{'CHEMBL-C'}}

    def test_comparator_rescue_multidrug_and_conflicting_alias_cannot_resolve(self):
        row=trial();self.assertEqual(arm_facts(row,self.aliases())[0]['resolved_drug_id'],'CHEMBL-A')
        variants=[]
        c=copy.deepcopy(row);c['design_groups'][0]['group_type']='Active comparator';variants.append(c)
        c=copy.deepcopy(row);c['interventions'][0]['description']='Rescue medication for cytokine release syndrome';variants.append(c)
        c=copy.deepcopy(row);c['interventions'].append({'id':4,'nct_id':'NCT00000001','name':'ExampleB','intervention_type':'Drug','description':None});c['design_group_interventions'].append({'id':5,'nct_id':'NCT00000001','design_group_id':2,'intervention_id':4});variants.append(c)
        c=copy.deepcopy(row);c['design_groups'][0]['title']='ExampleA plus chemotherapy';variants.append(c)
        c=copy.deepcopy(row);c['design_groups'][0]['description']='ExampleA in addition to prednisone at 30 mg daily';variants.append(c)
        c=copy.deepcopy(row);c['design_groups'][0]['description']='ExampleA daily and single doses of drug cocktail on day 2';variants.append(c)
        c=copy.deepcopy(row);c['interventions'][0]['description']='A micro-dose added at the same site as insulin is injected';variants.append(c)
        c=copy.deepcopy(row);c['interventions'][0]['intervention_type']='Combination Product';variants.append(c)
        for variant in variants:self.assertIsNone(arm_facts(variant,self.aliases())[0]['resolved_drug_id'])
        aliases=self.aliases();aliases['examplea'].add('CHEMBL-C')
        self.assertIsNone(arm_facts(row,aliases)[0]['resolved_drug_id'])

    def test_month_precision_preserved_at_cutoff(self):
        self.assertEqual(start_bounds('2023-01-01','January 2023'),('2023-01-01','2023-01-31','month'))
        self.assertEqual(start_bounds('2024-02-01','2024-02'),('2024-02-01','2024-02-29','month'))
        self.assertEqual(start_bounds('2024-01-01',None),(None,None,'unknown'))

    def build_fixture(self,root,extra_origin=None,transform=None):
        from collections import defaultdict
        policy={'protocol_id':'registry-sizing-development-v0.4','role':'evaluation_only','origin':'2023-01-01','occurrence_endpoint':'2025-01-01','mapping_inputs':[]}
        pp=root/'policy.json';pp.write_text(json.dumps(policy))
        origin=[trial(),trial('NCT00000002','ExampleB')]+(extra_origin or [])
        early=trial('NCT00000003','ExampleA','Phase 3',start='2024-02-01',kind='Anticipated',posted='2023-12-01')
        later=trial('NCT00000003','ExampleA','PHASE3',start='2024-02-01',kind='ACTUAL',posted='2023-12-01')
        later['study']['last_update_posted_date']='2024-03-01'
        if transform:transform(later)
        frames=[]
        for date,rows in [('2023-01-01',origin),('2024-01-01',[early]),('2025-01-01',[later])]:
            path=root/(date+'.jsonl');path.write_text(''.join(json.dumps(r)+'\n' for r in sorted(rows,key=lambda r:r['study']['nct_id'])))
            frames.append({'snapshot_date':date,'path':str(path),'records':len(rows),'sha256':sha256_file(path)})
        fp=root/'frames.json';fp.write_text(json.dumps({'protocol_sha256':sha256_file(pp),'snapshots':frames}))
        output=root/'output'
        with patch('tools.feasibility.registry_cohort.mapping',return_value=(self.aliases(),{'CHEMBL-A':'ExampleA','CHEMBL-B':'ExampleB'},defaultdict(set))):build(fp,pp,output)
        return output

    def test_estimated_becomes_actual_and_format_change_is_not_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            out=self.build_fixture(Path(d));events=json.loads((out/'candidate-events.json').read_text())
            self.assertEqual(events[0]['status'],'recorded_next_phase_start')
            self.assertEqual(events[0]['first_observed_snapshot'],'2025-01-01')
            self.assertEqual(len(events[0]['source_versions']),2)
            cohort=[json.loads(line) for line in (out/'cohort.jsonl').read_text().splitlines()]
            b=next(p for p in cohort if p['drug_id']=='CHEMBL-B')
            self.assertEqual(b['label_state'],'no_recorded_transition_by_cutoff')
            self.assertIsNone(b['training_label']);self.assertIsNone(b['individual_censoring_date'])

    def test_already_advanced_origin_program_is_not_at_risk(self):
        advanced=trial('NCT00000004','ExampleA','Phase 3','Completed','2021-01-01','Actual','2020-01-01')
        with tempfile.TemporaryDirectory() as d:
            out=self.build_fixture(Path(d),[advanced]);cohort=[json.loads(line) for line in (out/'cohort.jsonl').read_text().splitlines()]
            self.assertNotIn('CHEMBL-A',[p['drug_id'] for p in cohort])

    def test_withdrawn_actual_start_and_unresolved_roles_are_held(self):
        for transform,reason in [
            (lambda r:r['study'].update(overall_status='Withdrawn'),'withdrawn_study_actual_start_contradiction'),
            (lambda r:r['study'].update(last_update_posted_date='2023-12-01'),'actual_start_after_source_update'),
            (lambda r:r['design_groups'][0].update(title='Unspecified experimental treatment'),'next_phase_role_or_alias_unresolved')]:
            with tempfile.TemporaryDirectory() as d:
                out=self.build_fixture(Path(d),transform=transform)
                events=json.loads((out/'candidate-events.json').read_text())
                self.assertTrue(all(e['status']=='candidate_unresolved' for e in events))
                self.assertTrue(any(reason in e['holds'] for e in events))

    def test_heterogeneous_platform_conditions_do_not_leak_to_every_arm(self):
        a=trial();b=trial(drug='ExampleB')
        a['conditions'].append({'id':7,'nct_id':'NCT00000001','name':'Condition Y'})
        a['interventions'].append({**b['interventions'][0],'id':4})
        a['design_groups'].append({**b['design_groups'][0],'id':5})
        a['design_group_interventions'].append({'id':6,'nct_id':'NCT00000001','design_group_id':5,'intervention_id':4})
        facts=arm_facts(a,self.aliases())
        self.assertTrue(all(f['resolved_drug_id'] is None for f in facts))
        self.assertTrue(all('multi_program_study_condition_scope_unqualified' in f['reasons'] for f in facts))

    def test_audit_sample_membership_probabilities_and_seed(self):
        import random
        rows=[{'program_id':str(i),'stratum':i%3} for i in range(20)]
        a=stratified_sample(rows,lambda p:p['stratum'],8,random.Random(20261017))
        b=stratified_sample(list(reversed(rows)),lambda p:p['stratum'],8,random.Random(20261017))
        self.assertEqual(a,b);self.assertEqual(len(a),8)
        self.assertEqual({k for p,k,n,t in a},{0,1,2})
        self.assertTrue(all(0<t/n<=1 for p,k,n,t in a))
        with self.assertRaises(ValueError):stratified_sample(rows,lambda p:p['stratum'],2,random.Random(1))

    def test_original_row_audit_rejects_phase_comparator_and_date_changes(self):
        row=trial('NCT00000003',phase='Phase 3',start='2024-02-01',posted='2024-03-01')
        p={'origin_phase':2,'origin_trials':['NCT00000001'],'condition':'condition x'}
        e={'nct_id':'NCT00000003','source_arm_id':2,'status':'recorded_next_phase_start','source_proof':{'snapshot':'2025-01-01'}}
        self.assertEqual(source_check(p,e,row,'2023-01-01','2025-01-01'),[])
        row['design_groups'][0]['group_type']='Active comparator'
        self.assertIn('experimental_arm_mismatch',source_check(p,e,row,'2023-01-01','2025-01-01'))
        row['study'].update(phase='Phase 2',start_date_type='Anticipated')
        errors=source_check(p,e,row,'2023-01-01','2025-01-01')
        self.assertIn('phase_mismatch',errors);self.assertIn('actual_window_mismatch',errors)

    def test_source_audit_and_changed_frame_detection(self):
        from collections import defaultdict
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=self.build_fixture(root)
            with patch('tools.feasibility.registry_audit.mapping',return_value=(self.aliases(),{},defaultdict(set))):
                audit(root/'frames.json',out,root/'policy.json',root/'audit')
                report=json.loads((root/'audit/technical-audit.json').read_text())
                self.assertEqual(report['programs_source_checked'],2)
                self.assertEqual(report['controls_with_relaxed_followup_leads'],0)
                self.assertIsNone(report['recall']);self.assertEqual(report['independent_human_annotations'],0)
                with (root/'2025-01-01.jsonl').open('a') as f:f.write('\n')
                with self.assertRaises(ValueError):audit(root/'frames.json',out,root/'policy.json',root/'bad-audit')


if __name__=='__main__':unittest.main()
