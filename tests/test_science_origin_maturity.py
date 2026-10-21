import copy
import json
from pathlib import Path
import tempfile
import unittest

from asof.serde import ContractError
from tools.science.origin_maturity import select_candidates,maturity_reasons,select_mature
from tests import test_science_origin_review as origin_fixture


class OriginMaturityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='origin-maturity-tests-')
        cls.root=Path(cls.temp.name).resolve()
        freeze,_,_=origin_fixture.OriginReviewTests().fixture(cls.root,number=6)
        cls.records=[json.loads(line) for line in (freeze.parent/'origin-programs.jsonl').read_text(encoding='utf-8').splitlines()]

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def source(self,name,rows):
        path=self.root/name;path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8');return path

    def metadata(self,nct,raw='June 2025',kind='ANTICIPATED'):
        return {'study':{'nct_id':nct,'primary_completion_month_year':raw,'primary_completion_date_type':kind},
            'design_outcomes':[{'outcome_type':'PRIMARY','measure':'Planned objective; efficacy interpretation unreviewed'}]}

    def validation(self,candidates,held=()):
        rows=[self.metadata(c['nct_id']) for c in candidates if c['nct_id'] not in held]
        for row in rows:row['study'].update(last_update_posted_date='2024-12-20',last_update_posted_date_type='ACTUAL',
            study_first_posted_date='2020-01-01')
        return {'status':'study_rows_validated','version_dispositions':[{'nct_id':c['nct_id'],
            'version_eligibility':{'status':'held_boundary_uncertain' if c['nct_id'] in held else 'eligible_reconstructed_date_bound'}} for c in candidates],
            'eligible_reconstructed_rows':rows}

    def test_fixed_hash_order_independent_of_source_iteration_and_old_ids_excluded(self):
        excluded=[self.records[0]['nct_id']]
        a,report=select_candidates(self.source('a.jsonl',self.records),excluded,salt='fixed',maximum=4)
        b,_=select_candidates(self.source('b.jsonl',list(reversed(self.records))),excluded,salt='fixed',maximum=4)
        self.assertEqual([c['nct_id'] for c in a],[c['nct_id'] for c in b])
        self.assertNotIn(excluded[0],[c['nct_id'] for c in a]);self.assertEqual(5,report['eligible_trials_after_exclusion'])
        self.assertFalse(report['followup_used_for_selection'])

    def test_duplicate_program_and_unrequested_expansion_fail(self):
        with self.assertRaisesRegex(ContractError,'Duplicate'):
            select_candidates(self.source('duplicate.jsonl',self.records+[self.records[0]]),[],salt='s',maximum=1)
        with self.assertRaisesRegex(ContractError,'Insufficient'):
            select_candidates(self.source('small.jsonl',self.records[:2]),[],salt='s',maximum=3)

    def test_multiple_arms_cannot_inflate_trial_count(self):
        original=self.records[0];other=copy.deepcopy(original);other['program_id']='another-scope'
        with self.assertRaisesRegex(ContractError,'Insufficient'):
            select_candidates(self.source('two-arms.jsonl',[original,other]),[],salt='s',maximum=2)

    def test_future_or_label_canaries_fail_before_selection(self):
        for extra in ({'followup_status':'success'},{'outcome_label':0},{'clinical_outcome':1}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                select_candidates(self.source('canary.jsonl',[{**self.records[0],**extra}]),[],salt='s',maximum=1)

    def test_planned_year_month_day_precision_preserved_as_maturity_only(self):
        for raw,precision in [('2025','year'),('June 2025','month'),('June 15, 2025','day')]:
            reasons,interval=maturity_reasons(self.metadata('NCT00000100',raw))
            self.assertEqual([],reasons);self.assertEqual(precision,interval['precision']);self.assertFalse(interval['event_inferred'])

    def test_actual_missing_outside_window_or_missing_primary_does_not_qualify(self):
        for raw,kind in [('2024','ANTICIPATED'),('2026','ANTICIPATED'),(None,'ANTICIPATED'),('June 2025','ACTUAL'),('June 2025',None)]:
            self.assertTrue(maturity_reasons(self.metadata('NCT00000100',raw,kind))[0])
        row=self.metadata('NCT00000100');row['design_outcomes'][0]['outcome_type']='SECONDARY'
        self.assertIn('no_recorded_planned_primary_outcome',maturity_reasons(row)[0])

    def test_reported_results_or_followup_fields_are_rejected_even_when_empty(self):
        for field,value in [('outcomes',[]),('outcome_measurements',[]),('outcome_analyses',[])]:
            row=self.metadata('NCT00000100');row[field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):maturity_reasons(row)
        for field in ('results_first_posted_date','why_stopped','clinical_outcome'):
            row=self.metadata('NCT00000100');row['study'][field]=None
            with self.subTest(field=field),self.assertRaises(ContractError):maturity_reasons(row)

    def test_imputed_aact_completion_date_cannot_refine_raw_planned_interval(self):
        row=self.metadata('NCT00000100',raw=None);row['study']['primary_completion_date']='2025-06-01'
        self.assertIn('planned_primary_completion_not_wholly_calendar2025',maturity_reasons(row)[0])

    def test_mature_selection_uses_frozen_order_without_rule_or_favorable_text_ranking(self):
        candidates,_=select_candidates(self.source('ordered.jsonl',self.records),[],salt='s',maximum=4)
        v=self.validation(candidates);v['eligible_reconstructed_rows'][0]['design_outcomes'][0]['measure']='Safety only; unreviewed'
        chosen,screen=select_mature(candidates,v,requested=2)
        self.assertEqual([c['nct_id'] for c in candidates[:2]],[c['candidate']['nct_id'] for c in chosen])
        self.assertTrue(all(c['clinical_label'] is None and c['scientific_qualification'] is False for c in chosen))
        self.assertEqual(4,len(screen));self.assertTrue(all(s['clinical_eligibility']=='unreviewed' for s in screen))

    def test_held_missing_and_immature_dispositions_retained_without_replacements(self):
        candidates,_=select_candidates(self.source('held.jsonl',self.records),[],salt='s',maximum=4)
        v=self.validation(candidates,held=[candidates[0]['nct_id']])
        chosen,screen=select_mature(candidates,v,requested=2)
        self.assertEqual(['origin_version_held'],screen[0]['reasons'])
        self.assertEqual(candidates[1]['nct_id'],chosen[0]['candidate']['nct_id'])
        with self.assertRaisesRegex(ContractError,'Insufficient'):select_mature(candidates,v,requested=4)

    def test_source_membership_and_eligible_payload_contradictions_fail(self):
        candidates,_=select_candidates(self.source('scope.jsonl',self.records),[],salt='s',maximum=2)
        v=self.validation(candidates);v['eligible_reconstructed_rows'].pop()
        with self.assertRaisesRegex(ContractError,'differ'):select_mature(candidates,v,requested=1)
        v=self.validation(candidates);v['version_dispositions'].append(copy.deepcopy(v['version_dispositions'][0]))
        with self.assertRaisesRegex(ContractError,'membership'):select_mature(candidates,v,requested=1)
        v=self.validation(candidates);v['eligible_reconstructed_rows'][0]['study']['nct_id']='NCT99999999'
        with self.assertRaisesRegex(ContractError,'membership'):select_mature(candidates,v,requested=1)


if __name__=='__main__':unittest.main()
