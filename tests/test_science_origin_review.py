import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_science_origin_programs as fixtures
from tools.science.origin_programs import mapping_revision, seal_frame, sha
from tools.science.origin_review import InsufficientPool, build, eligibility, rank, select, source_rows, verify_selected


class OriginReviewTests(unittest.TestCase):
    def fixture(self,root,number=5):
        base=root/'mapping-base';base.mkdir()
        _,manifest,rules=fixtures.OriginProgramsTests().mapping_fixture(base)
        origin=root/'origin';origin.mkdir();frame=origin/'origin-frame.stdout.log'
        rows=[fixtures.trial('NCT'+str(100+i).zfill(8),phase='Phase 2') for i in range(number)]
        rows[0]['eligibilities'][0]['criteria']='Adults with disease X — β-marker ≥1'
        frame.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
        for name in ('origin-query.sql','origin-contract.json','executed-origin-programs.py'):(origin/name).write_text('fixture')
        seal_frame(frame,origin,[])
        revision=root/'revision';mapping_revision(origin/'origin-freeze.json',manifest,revision,rules)
        return revision/'origin-freeze.json',manifest,frame

    def test_frozen_criteria_precede_scan_and_repeat_ids_packet_fingerprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,_,_=self.fixture(root)
            output=root/'pack-a';original=select
            def inspect_criteria(*args,**kwargs):
                contract=json.loads((output/'criteria-freeze.json').read_text())
                self.assertFalse(contract['followup_sources_allowed']);self.assertEqual(contract['sample_size_distinct_trials'],3)
                return original(*args,**kwargs)
            with patch('tools.science.origin_review.select',side_effect=inspect_criteria):
                first=build(origin,sha(origin),output,count=3)
            second=build(origin,sha(origin),root/'pack-b',count=3)
            self.assertEqual(first['trial_ids'],second['trial_ids']);self.assertEqual(len(set(first['trial_ids'])),3)
            self.assertEqual(first['trial_ids'],sorted(first['trial_ids'],key=lambda n:(rank('trial',n),n)))
            a=json.loads((output/'selection.json').read_text());b=json.loads((root/'pack-b/selection.json').read_text())
            self.assertEqual([x['packet_sha256'] for x in a['selection']],[x['packet_sha256'] for x in b['selection']])
            for chosen in a['selection']:
                packet=json.loads(Path(chosen['packet']).read_text(encoding='utf-8'))
                self.assertEqual(packet['clinical_labels'],[]);self.assertFalse(packet['followup_sources_read'])
                self.assertIn('same_program_scope_not_established',packet['origin_scope']['qualification_holds'])
                source=packet['original_origin_source'];proof=source['proof']
                with Path(proof['path']).open('rb') as f:f.seek(proof['byte_offset']);raw=f.read(proof['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(),proof['sha256']);self.assertEqual(json.loads(raw),source['record'])
                self.assertEqual(packet['origin_scope']['population_source'],source['record']['eligibilities'])
            seal=json.loads((output/'pack-freeze.json').read_text())
            for pin in seal['files']:self.assertEqual(sha(pin['path']),pin['sha256'])

    def test_insufficient_pool_retains_frozen_criteria_and_no_relaxation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,_,_=self.fixture(root,number=2);output=root/'pack'
            with self.assertRaises(InsufficientPool):build(origin,sha(origin),output,count=3)
            self.assertTrue((output/'criteria-freeze.json').exists());self.assertFalse((output/'pack-freeze.json').exists())
            failure=json.loads((output/'failure.json').read_text())
            self.assertEqual(failure['pool']['eligible_distinct_trials'],2);self.assertFalse(failure['criteria_relaxed'])

    def test_scope_criteria_are_strict_and_labels_or_future_fields_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,_,_=self.fixture(root,number=1)
            with (origin.parent/'origin-programs.jsonl').open(encoding='utf-8') as f:rec=json.loads(f.readline())
            self.assertEqual(eligibility(rec),[])
            for key,value in [('origin_phase',1),('target_ids',[]),('drug_ids',['D1','D2']),('source_products',[]),
                    ('start_interval',{'lower_date':'2021-12-31','upper_date':'2022-01-01','precision':'day'})]:
                bad=copy.deepcopy(rec);bad[key]=value;self.assertTrue(eligibility(bad),key)
            bad=copy.deepcopy(rec);bad['qualification_holds'].append('multiple_conditions_arm_assignment_unqualified')
            self.assertIn('not_single_condition_assignment',eligibility(bad))
            for addition in ({'clinical_outcome':1},{'followup_status':'success'},{'outcome_label':0}):
                with self.assertRaises(ValueError):eligibility({**rec,**addition})

    def test_duplicate_programs_rejected_and_multiple_scopes_do_not_inflate_trials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,_,_=self.fixture(root,number=1)
            with (origin.parent/'origin-programs.jsonl').open(encoding='utf-8') as f:rec=json.loads(f.readline())
            path=root/'duplicate.jsonl';path.write_text((json.dumps(rec)+'\n')*2)
            with self.assertRaisesRegex(ValueError,'Duplicate parent program'):select(path,1)
            other={**rec,'program_id':'other-origin-arm'};path.write_text(json.dumps(rec)+'\n'+json.dumps(other)+'\n')
            with self.assertRaises(InsufficientPool) as caught:select(path,2)
            self.assertEqual(caught.exception.report['eligible_scopes'],2)
            self.assertEqual(caught.exception.report['eligible_distinct_trials'],1)

    def test_source_fingerprint_and_duplicate_trial_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,_,frame=self.fixture(root,number=1);nct='NCT00000100'
            with self.assertRaisesRegex(ValueError,'fingerprint changed'):source_rows(frame,{nct},'0'*64)
            raw=frame.read_bytes();frame.write_bytes(raw+raw)
            with self.assertRaisesRegex(ValueError,'Duplicate origin source NCT'):source_rows(frame,{nct},sha(frame))

    def test_original_population_and_date_precision_must_match_selected_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,_,frame=self.fixture(root,number=1)
            with (origin.parent/'origin-programs.jsonl').open(encoding='utf-8') as f:rec=json.loads(f.readline())
            original=source_rows(frame,{rec['nct_id']},sha(frame))[rec['nct_id']]
            verify_selected(rec,original)
            for field,value in [('population_source',[]),('start_interval',{'lower_date':'2024-01-01','upper_date':'2024-01-01','precision':'day'})]:
                bad=copy.deepcopy(rec);bad[field]=value
                with self.assertRaisesRegex(ValueError,'projection mismatch'):verify_selected(bad,original)

    def test_changed_transitive_source_prevents_final_pack_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);origin,manifest,_=self.fixture(root,number=2);output=root/'pack'
            raw=Path(json.loads(manifest.read_text())['files'][0]['path']);original=select
            def mutate_after_selection(*args,**kwargs):
                result=original(*args,**kwargs);raw.write_bytes(b'mutated raw ancestor');return result
            with patch('tools.science.origin_review.select',side_effect=mutate_after_selection):
                with self.assertRaisesRegex(ValueError,'Changed bound ancestor'):build(origin,sha(origin),output,count=2)
            self.assertFalse((output/'pack-freeze.json').exists())
            self.assertTrue((output/'failure.json').exists())


if __name__=='__main__':unittest.main()
