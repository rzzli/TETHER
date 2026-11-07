import copy
import unittest
from tools.feasibility.extract_phase3_followup import query, validate_extract, TABLES
from tools.feasibility.assess_phase3_link import assess_timing


class Phase3FollowupTests(unittest.TestCase):
    def fixture(self):
        plan={'restore_root':'D:/example','expected_studies':10,'port':55433,
              'nct_ids':['NCT06203210'],'snapshot_date':'2025-01-01'}
        record={t:[] for t in TABLES}
        record['study']={'nct_id':'NCT06203210','study_first_posted_date':'2024-01-11',
            'last_update_posted_date':'2024-12-03','start_date':'2024-07-01','start_date_type':'ACTUAL'}
        data={'database':'aact_snapshot','data_directory':'D:/example/pgdata','port':'55433',
              'studies_count':10,'transaction_read_only':'on','records':[record]}
        return plan,data

    def test_query_rejects_injection_duplicates_and_unbounded_ids(self):
        for ids in [[],['NCT06203210']*2,["NCT06203210'; DROP TABLE studies;"],['NCT00000000']*11]:
            with self.assertRaises(ValueError):query(ids)
        sql=query(['NCT06203210']);self.assertIn('REPEATABLE READ READ ONLY',sql)
        self.assertTrue(sql.endswith('ROLLBACK;\n'))

    def test_extract_requires_original_database_and_complete_selected_ids(self):
        plan,data=self.fixture();validate_extract(data,plan)
        for field,value in [('transaction_read_only','off'),('data_directory','D:/other'),
                            ('studies_count',11),('port','55432'),('database','other'),('records',[])]:
            changed=copy.deepcopy(data);changed[field]=value
            with self.assertRaises(ValueError):validate_extract(changed,plan)

    def test_later_posting_and_cross_trial_links_rejected(self):
        plan,data=self.fixture();bad=copy.deepcopy(data)
        bad['records'][0]['study']['last_update_posted_date']='2025-01-02'
        with self.assertRaises(ValueError):validate_extract(bad,plan)
        bad=copy.deepcopy(data);bad['records'][0]['conditions']=[{'nct_id':'NCT00000000'}]
        with self.assertRaises(ValueError):validate_extract(bad,plan)
        bad=copy.deepcopy(data);bad['records'][0]['design_group_interventions']=[
            {'nct_id':'NCT06203210','design_group_id':1,'intervention_id':2}]
        with self.assertRaises(ValueError):validate_extract(bad,plan)

    def test_actual_enrollment_is_a_bound_not_an_exact_dose_date(self):
        study={'phase':'PHASE3','start_date':'2024-05-21','start_date_type':'ACTUAL',
               'study_first_posted_date':'2024-01-12','last_update_posted_date':'2024-12-04'}
        result=assess_timing(study,'2024-08-01','2023-01-01','2025-01-01')
        self.assertTrue(result['phase3_enrollment_within_window'])
        self.assertEqual(result['conditional_trial_dosing_interval'],{'lower':'2024-05-21','upper':'2024-08-01'})
        self.assertIsNone(result['exact_first_dose_date'])
        self.assertIsNone(result['clinical_training_label'])
        self.assertFalse(result['strict_historical_event_certified'])
        for changed in [{**study,'start_date_type':'ESTIMATED'},{**study,'start_date':None},
                        {**study,'phase':'PHASE2'},{**study,'start_date':'2022-12-01'}]:
            self.assertIsNone(assess_timing(changed,'2024-08-01','2023-01-01','2025-01-01')['conditional_trial_dosing_interval'])
        self.assertIsNone(assess_timing(study,None,'2023-01-01','2025-01-01')['conditional_trial_dosing_interval'])

    def test_timing_rejects_conflict_and_later_posting(self):
        study={'phase':'PHASE3','start_date':'2024-08-02','start_date_type':'ACTUAL'}
        with self.assertRaises(ValueError):assess_timing(study,'2024-08-01','2023-01-01','2025-01-01')
        study['start_date']='2024-05-21';study['last_update_posted_date']='2025-01-02'
        with self.assertRaises(ValueError):assess_timing(study,'2024-08-01','2023-01-01','2025-01-01')


if __name__=='__main__':unittest.main()
