import unittest
from tools.feasibility.compare_clinical_snapshots import compare


class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.origin = {'nct_id':'NCT12345678','overall_status':'Active, not recruiting',
                       'phase':'Phase 2','conditions':['Example disease']}
        self.selected = [{'candidate_id':'P01','target_anchor':'GENE','drug_anchor':'drug',
                          'origin_record':self.origin}]
        self.reviews = [{'nct_id':self.origin['nct_id'],'decision':'exclude_as_anchor_program',
                         'review_note':'Comparator only'}]
        self.new = {**self.origin,'overall_status':'COMPLETED',
                    'study_first_posted_date':'2020-01-01','last_update_posted_date':'2024-12-20',
                    'results_first_posted_date':None}

    def run_compare(self, rows):
        return compare(self.selected,rows,self.reviews,'2023-01-01','2025-01-01')[0]

    def test_completed_and_stopped_never_become_clinical_labels(self):
        for status in ('COMPLETED','TERMINATED','WITHDRAWN'):
            result = self.run_compare([{**self.new,'overall_status':status,'why_stopped':'Business decision'}])
            for key in ('therapeutic_success','clinical_failure','event_date','event_publication_date','censoring_date'):
                self.assertIsNone(result[key])
            self.assertEqual(result['origin_mapping_decision'],'exclude_as_anchor_program')

    def test_future_public_information_rejected_but_planned_dates_preserved(self):
        for field in ('study_first_posted_date','last_update_posted_date','results_first_posted_date'):
            with self.assertRaises(ValueError):
                self.run_compare([{**self.new,field:'2025-01-02'}])
        result=self.run_compare([{**self.new,'completion_date':'2030-01-01','completion_date_type':'Anticipated'}])
        self.assertEqual(result['followup_registry_record']['completion_date'],'2030-01-01')
        self.assertFalse(any('reported_actual' in x for x in result['observations']))

    def test_missing_duplicate_and_unselected_records_are_explicit(self):
        self.assertIn('missing_followup_record_not_failure_or_censoring', self.run_compare([])['observations'])
        with self.assertRaises(ValueError): self.run_compare([self.new,self.new])
        with self.assertRaises(ValueError): self.run_compare([{**self.new,'nct_id':'NCT99999999'}])

    def test_status_formatting_and_early_results_do_not_invent_events(self):
        result=self.run_compare([{**self.new,'overall_status':'ACTIVE_NOT_RECRUITING',
                                 'phase':'PHASE2',
                                 'results_first_posted_date':'2021-08-24'}])
        self.assertNotIn('registry_status_changed_not_program_outcome',result['observations'])
        self.assertNotIn('phase_field_changed_not_proven_transition',result['observations'])
        self.assertIn('results_posted_before_origin',result['observations'])
        self.assertIsNone(result['event_date'])


if __name__ == '__main__':
    unittest.main()
