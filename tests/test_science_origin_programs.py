import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.science.origin_programs import arm_records, mapping_revision, query, read_bound_json, seal_frame, sha, start_bounds, trial_facts, validate, verify_pins
from tools.science.historical_inputs import BASE, NOTICE, PROJECTIONS, project, verify_manifest


def trial(nct='NCT00000001',phase='Phase 1'):
    row={'study':{'nct_id':nct,'phase':phase,'overall_status':'Recruiting','study_type':'Interventional',
        'start_date':'2024-06-01','start_month_year':'June 2024','start_date_type':'Actual',
        'study_first_posted_date':'2024-01-01','last_update_posted_date':'2024-12-27'}}
    for table in ('conditions','interventions','intervention_other_names','design_groups','design_group_interventions','sponsors','brief_summaries','eligibilities','designs'):row[table]=[]
    row['conditions']=[{'id':1,'nct_id':nct,'name':'Disease X'}]
    row['interventions']=[{'id':1,'nct_id':nct,'intervention_type':'Drug','name':'Drug A','description':'Oral'}]
    row['design_groups']=[{'id':2,'nct_id':nct,'group_type':'Experimental','title':'Drug A','description':'Adults'}]
    row['design_group_interventions']=[{'id':1,'nct_id':nct,'design_group_id':2,'intervention_id':1}]
    row['eligibilities']=[{'id':1,'nct_id':nct,'criteria':'Adults with disease X','minimum_age':'18 Years'}]
    row['sponsors']=[{'id':1,'nct_id':nct,'lead_or_collaborator':'lead','name':'Sponsor'}]
    return row


class OriginProgramsTests(unittest.TestCase):
    def test_partial_date_bounds_do_not_refine_using_imputed_date(self):
        self.assertEqual(start_bounds('2024-02'),('2024-02-01','2024-02-29','month'))
        self.assertEqual(start_bounds('2024'),('2024-01-01','2024-12-31','year'))
        self.assertEqual(start_bounds('2025-02-30'),(None,None,'unknown'))
        row=trial();row['study']['start_date']='2024-01-01';row['study']['start_month_year']='January 2025'
        self.assertIn('actual_start_interval_not_wholly_pre_origin',trial_facts(row)['reasons'])
        row['study']['start_month_year']='2024';self.assertNotIn('actual_start_interval_not_wholly_pre_origin',trial_facts(row)['reasons'])
        row['study']['start_month_year']=None;self.assertIn('actual_start_interval_not_wholly_pre_origin',trial_facts(row)['reasons'])

    def test_exact_origin_postings_and_cross_trial_children_rejected(self):
        row=trial();validate(row)
        for key in ('study_first_posted_date','last_update_posted_date'):
            bad=copy.deepcopy(row);bad['study'][key]='2025-01-01'
            with self.assertRaises(ValueError):validate(bad)
        row['conditions'][0]['nct_id']='NCT99999999'
        with self.assertRaises(ValueError):validate(row)

    def test_mixed_phase_not_rounded_to_lower_phase_and_inactive_excluded(self):
        for phase in ('Phase 1/Phase 2','Phase 2/Phase 3','Phase 3','Early Phase 1'):
            self.assertEqual(next(arm_records(trial(phase=phase)))['scope_status'],'excluded')
        row=trial();row['study']['overall_status']='Completed'
        self.assertEqual(next(arm_records(row))['scope_status'],'excluded')

    def test_combination_all_source_products_retained_without_invented_targets(self):
        row=trial();row['interventions'].append({'id':3,'nct_id':row['study']['nct_id'],'name':'Drug B','intervention_type':'Biological'})
        row['design_group_interventions'].append({'id':2,'nct_id':row['study']['nct_id'],'design_group_id':2,'intervention_id':3})
        rec=next(arm_records(row))
        self.assertEqual(rec['active_product_names'],['drug a','drug b'])
        self.assertIn('combination_regimen_roles_unqualified',rec['qualification_holds'])
        self.assertEqual(rec['target_ids'],[]);self.assertEqual(rec['drug_ids'],[])
        self.assertIsNone(rec['clinical_outcome']);self.assertFalse(rec['clinical_ready'])

    def test_population_scope_not_silently_merged_across_arms_or_conditions(self):
        row=trial();row['conditions'].append({'id':2,'nct_id':row['study']['nct_id'],'name':'Disease Y'})
        records=list(arm_records(row));self.assertEqual(len(records),2)
        self.assertNotEqual(records[0]['program_id'],records[1]['program_id'])
        self.assertEqual(records[0]['population_source'],row['eligibilities'])
        self.assertIn('multiple_conditions_arm_assignment_unqualified',records[0]['qualification_holds'])
        self.assertIn('same_program_scope_not_established',records[0]['qualification_holds'])

    def test_query_includes_eligibility_same_snapshot_and_no_endpoint_tables(self):
        sql=query();self.assertIn('ctgov.eligibilities',sql);self.assertIn('REPEATABLE READ READ ONLY',sql)
        self.assertNotIn('2026',sql)
        for forbidden in ('reported_events','outcomes','result_groups','calculated_values'):
            self.assertNotIn('ctgov.'+forbidden,sql)

    def test_source_only_seal_prior_alerts_and_retained_row_proofs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);frame=root/'origin-frame.stdout.log'
            rows=[trial(),trial('NCT00000002','Phase 3')]
            frame.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
            for name in ('origin-query.sql','origin-contract.json','executed-origin-programs.py'):(root/name).write_text('fixture')
            result=seal_frame(frame,root,[])
            self.assertEqual(result['conditional_origin_candidates'],1)
            rec=json.loads((root/'origin-programs.jsonl').read_text())
            self.assertEqual(rec['prior_higher_phase_verbatim_alerts'][0]['nct_id'],'NCT00000002')
            seal=json.loads((root/'origin-freeze.json').read_text())
            self.assertEqual(seal['endpoint_rows_queried'],0);self.assertFalse(seal['origin_date_qualified'])
            self.assertFalse(seal['mapping_qualified']);self.assertTrue(seal['selection_sealed'])
            for asset in seal['files']:self.assertEqual(asset['sha256'],sha(asset['path']))
            with frame.open('rb') as f:
                f.seek(rec['source_proof']['byte_offset']);raw=f.read(rec['source_proof']['bytes'])
            self.assertEqual(json.loads(raw),rows[0])
            with self.assertRaises(FileExistsError):seal_frame(frame,root,[])

    def mapping_fixture(self,root,ambiguous=False):
        origin=root/'origin';origin.mkdir();frame=origin/'origin-frame.stdout.log'
        frame.write_text(json.dumps(trial())+'\n',encoding='utf-8')
        for name in ('origin-query.sql','origin-contract.json','executed-origin-programs.py'):(origin/name).write_text('fixture')
        seal_frame(frame,origin,[])
        history=root/'history';history.mkdir();raw=history/'p.parquet';raw.write_bytes(b'source ancestor')
        receipt=history/'receipt.json';receipt.write_text(json.dumps({'sha256':sha(raw),'source_url':BASE+'output/p.parquet'}))
        notice=history/'release-notice.json';notice.write_text(json.dumps({'post_stream':{'posts':[{'created_at':'2024-09-18T13:36:32.754Z','cooked':'Released 24.09'}]}}))
        notice_receipt=history/'notice-receipt.json';notice_receipt.write_text(json.dumps({'sha256':sha(notice),'source_url':NOTICE}))
        source={'path':'output/p.parquet','row_group':0,'row':0,'sha256':sha(raw)}
        records={'molecule':[{'id':'CHEMBL1','name':'Drug A','synonyms':[],'tradeNames':[]}],
            'mechanismOfAction':[{'chemblIds':['CHEMBL1'],'targets':['ENSG1'],'actionType':'INHIBITOR'}],
            'targets':[{'id':'ENSG1'}],
            'diseases':[{'id':'EFO1','name':'Disease X','synonyms':{'hasExactSynonym':[]}}]}
        if ambiguous:records['molecule'].append({'id':'CHEMBL2','name':'Drug A','synonyms':[],'tradeNames':[]})
        products=[]
        for name,rows in records.items():
            path=history/(name+'.jsonl');path.write_text(''.join(json.dumps({'record':project(r,name),'source':source})+'\n' for r in rows),encoding='utf-8')
            schema=history/(name+'-schemas.json');schema.write_text('[]')
            products.append({'product':name,'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size,'rows':len(rows),'approved_columns':list(PROJECTIONS[name]),'schema_path':str(schema),'schema_sha256':sha(schema)})
        manifest=history/'manifest.json';manifest.write_text(json.dumps({'status':'qualified_mapping_projections_only','release_id':'24.09','origin_at':'2025-01-01T00:00:00Z','future_fallback':False,'available_by':'2024-09-19T00:00:00Z','clinical_outcome_queries':0,'metadata':[{'path':str(notice),'sha256':sha(notice),'bytes':notice.stat().st_size,'source_url':NOTICE,'receipt_path':str(notice_receipt),'receipt_sha256':sha(notice_receipt)}],'files':[{'path':str(raw),'sha256':sha(raw),'bytes':raw.stat().st_size,'source_url':BASE+'output/p.parquet','receipt_path':str(receipt),'receipt_sha256':sha(receipt)}],'products':products}))
        rules=root/'rules.md';rules.write_text('Exploratory only')
        return origin,manifest,rules

    def test_mapping_revision_keeps_membership_and_resource_annotation_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root)
            result=mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)
            self.assertEqual(result['programs'],1)
            mapped=json.loads((root/'revision/origin-programs.jsonl').read_text())
            parent=json.loads((origin/'origin-programs.jsonl').read_text())
            self.assertEqual(mapped['program_id'],parent['program_id'])
            self.assertEqual(mapped['drug_ids'],['CHEMBL1']);self.assertEqual(mapped['target_ids'],['ENSG1'])
            self.assertIn('historical_annotation_does_not_establish_therapeutic_target_or_scope',mapped['qualification_holds'])
            seal=json.loads((root/'revision/origin-freeze.json').read_text())
            self.assertTrue(seal['mapping_qualified']);self.assertFalse(seal['origin_date_qualified'])
            self.assertFalse(seal['clinical_ready']);self.assertEqual(seal['endpoint_rows_queried'],0)
            self.assertEqual(seal['parent_origin_seal']['sha256'],sha(origin/'origin-freeze.json'))
            self.assertTrue(seal['historical_ancestor_pins']);self.assertTrue(seal['origin_ancestor_pins'])

    def test_ambiguous_mapping_never_invents_drug_or_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root,ambiguous=True)
            mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)
            mapped=json.loads((root/'revision/origin-programs.jsonl').read_text())
            self.assertEqual(mapped['drug_ids'],[]);self.assertEqual(mapped['target_ids'],[])
            self.assertEqual(mapped['historical_mapping_slots'][0]['candidate_drug_ids'],['CHEMBL1','CHEMBL2'])

    def test_future_mapping_or_mutated_origin_is_rejected_before_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root)
            m=json.loads(manifest.read_text());m['available_by']='2025-01-01T00:00:00Z';manifest.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'availability'):mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)
            m['available_by']='2024-09-19T00:00:00Z';manifest.write_text(json.dumps(m))
            (origin/'origin-programs.jsonl').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Changed bound'):mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)

    def test_clinical_phase_annotation_rejected_even_if_projection_claims_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root)
            m=json.loads(manifest.read_text());product=next(p for p in m['products'] if p['product']=='molecule')
            path=Path(product['path']);item=json.loads(path.read_text());item['record']['maximumClinicalTrialPhase']=4
            path.write_text(json.dumps(item)+'\n');product['sha256']=sha(path);product['approved_columns'].append('maximumClinicalTrialPhase')
            manifest.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Projection column boundary|Unapproved historical'):mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)

    def test_changed_raw_parent_rejected_before_any_mapping_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root)
            m=json.loads(manifest.read_text());Path(m['files'][0]['path']).write_bytes(b'changed physical ancestor')
            # Projection bytes, declarations and receipts remain untouched.
            with self.assertRaisesRegex(ValueError,'Historical ancestor changed'):
                mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)
            self.assertFalse((root/'revision').exists())

    def test_raw_parent_changed_after_validation_prevents_qualified_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root)
            raw=Path(json.loads(manifest.read_text())['files'][0]['path']);calls=[]
            def change_after_initial_check(*args,**kwargs):
                result=verify_manifest(*args,**kwargs);calls.append(kwargs)
                if len(calls)==1:raw.write_bytes(b'changed after successful closure verification')
                return result
            with patch('tools.science.historical_inputs.verify_manifest',side_effect=change_after_initial_check):
                with self.assertRaisesRegex(ValueError,'Historical ancestor changed'):
                    mapping_revision(origin/'origin-freeze.json',manifest,root/'revision',rules)
            self.assertTrue((root/'revision/origin-programs.jsonl').exists())
            self.assertFalse((root/'revision/origin-freeze.json').exists())
            self.assertEqual(calls[0]['expected_manifest_sha256'],sha(manifest))

    def test_origin_restore_receipt_changed_during_mapping_prevents_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,rules=self.mapping_fixture(root)
            receipt=root/'origin-restore-verification.json';receipt.write_text('{"status":"passed"}')
            parent=origin/'origin-freeze.json';freeze=json.loads(parent.read_text())
            freeze['source_receipts']=[{'path':str(receipt),'sha256':sha(receipt)}];parent.write_text(json.dumps(freeze))
            calls=[]
            def change_receipt(*args,**kwargs):
                result=verify_manifest(*args,**kwargs);calls.append(kwargs)
                if len(calls)==1:receipt.write_text('{"status":"changed"}')
                return result
            with patch('tools.science.historical_inputs.verify_manifest',side_effect=change_receipt):
                with self.assertRaisesRegex(ValueError,'Changed bound ancestor'):
                    mapping_revision(parent,manifest,root/'revision',rules)
            self.assertEqual(len(calls),2)
            self.assertFalse((root/'revision/origin-freeze.json').exists())

    def test_read_bound_json_hashes_exact_parsed_bytes_before_path_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bound.json';path.write_bytes(b'{"version":"original"}')
            original_digest=sha(path);read_bytes=Path.read_bytes
            def swap_after_read(target):
                raw=read_bytes(target)
                if target==path.resolve():path.write_bytes(b'{"version":"replacement"}')
                return raw
            with patch.object(Path,'read_bytes',swap_after_read):
                value,pin=read_bound_json(path)
            self.assertEqual(value,{'version':'original'});self.assertEqual(pin['sha256'],original_digest)
            with self.assertRaisesRegex(ValueError,'Changed bound ancestor'):verify_pins([pin])


if __name__=='__main__':unittest.main()
