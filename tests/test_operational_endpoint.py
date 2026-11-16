"""P12 source-observation rules; these tests do not qualify clinical labels."""
import copy
import unittest

from tools.science.operational_endpoint import reduce_endpoint


class OperationalEndpointTests(unittest.TestCase):
    def setUp(self):
        self.units=[dict(unit_id='u1',target_id='T1',disease_id='D1',policy_holds=[]),
                    dict(unit_id='u2',target_id='T2',disease_id='D2',policy_holds=[])]
        self.rows=[dict(id='e1',targetId='T1',diseaseId='D1',datasourceId='chembl',datatypeId='known_drug',
                        drugId='C1',clinicalPhase=3.0,studyStartDate='2025-03',nct_ids=['NCT00000001'])]

    def run_endpoint(self,rows=None,**kw):
        args=dict(origin='2025-01-01',horizon='2025-07-01',observation_freeze='2025-09-18',source_complete=True)
        args.update(kw)
        return reduce_endpoint(self.units,self.rows if rows is None else rows,**args)

    def test_positive_and_complete_source_negative_are_distinct_from_clinical_truth(self):
        r=self.run_endpoint()['units']
        self.assertEqual([x['source_state'] for x in r],['recorded_event','no_record_in_complete_source'])
        self.assertEqual([x['candidate_operational_label'] for x in r],[1,0])
        self.assertTrue(all(x['clinical_label'] is None and x['programme_label'] is None and x['qualified_label'] is None for x in r))

    def test_origin_boundary_included_horizon_boundary_excluded(self):
        for when,label in [('2025-01-01',1),('2025-06-30',1),('2025-07-01',0),('2024-12-31',0)]:
            self.rows[0]['studyStartDate']=when
            self.assertEqual(self.run_endpoint()['units'][0]['candidate_operational_label'],label)

    def test_partial_year_crosses_window_and_is_not_a_negative(self):
        self.rows[0]['studyStartDate']='2025'
        self.assertEqual(self.run_endpoint()['units'][0]['source_state'],'unresolved')

    def test_missing_malformed_and_datetime_dates_remain_unknown(self):
        for when in (None,'bad','2025-02-30','2025-01-02T00:00:00Z',True):
            self.rows[0]['studyStartDate']=when
            self.assertIsNone(self.run_endpoint()['units'][0]['candidate_operational_label'])

    def test_earlier_registration_does_not_disqualify_a_later_start(self):
        self.rows[0]['registered_before_origin']=True
        self.assertEqual(self.run_endpoint()['units'][0]['candidate_operational_label'],1)

    def test_combined_phase_is_held_but_definitely_outside_window_is_not(self):
        self.rows[0]['clinicalPhase']=2.5
        self.assertIsNone(self.run_endpoint()['units'][0]['candidate_operational_label'])
        self.rows[0]['studyStartDate']='2020'
        self.assertEqual(self.run_endpoint()['units'][0]['candidate_operational_label'],0)

    def test_phase4_skip_only_enters_named_sensitivity(self):
        self.rows[0]['clinicalPhase']=4
        r=self.run_endpoint()['units'][0]
        self.assertEqual(r['candidate_operational_label'],0)
        self.assertEqual(r['at_least_phase3_candidate_label'],1)

    def test_uninterpretable_phase_is_not_a_negative(self):
        for phase in ('3',True,None,float('nan'),3.7):
            self.rows[0]['clinicalPhase']=phase
            self.assertIsNone(self.run_endpoint()['units'][0]['candidate_operational_label'])

    def test_duplicate_and_conflicting_id_records(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        r=self.run_endpoint();self.assertEqual(r['duplicate_rows'],1)
        self.assertEqual(r['units'][0]['event_ids'],['e1'])
        self.rows[1]['studyStartDate']='2024-01-01'
        r=self.run_endpoint();self.assertIsNone(r['units'][0]['candidate_operational_label'])
        self.assertIn('conflicting_evidence_id',r['units'][0]['holds'])

    def test_incomplete_source_withholds_all_candidates(self):
        r=self.run_endpoint(source_complete=False)
        self.assertTrue(all(x['candidate_operational_label'] is None for x in r['units']))

    def test_immature_window_remains_censored(self):
        r=self.run_endpoint(observation_freeze='2025-05-01')
        self.assertTrue(all(x['source_state']=='right_censored' and x['candidate_operational_label'] is None for x in r['units']))

    def test_existing_reserve_policy_hold_is_separate_and_preserved(self):
        self.units[0]['policy_holds']=['reserve_bridge']
        r=self.run_endpoint()['units'][0]
        self.assertEqual(r['source_state'],'recorded_event')
        self.assertIsNone(r['candidate_operational_label']);self.assertEqual(r['policy_holds'],['reserve_bridge'])

    def test_shared_drugs_or_trials_connect_units_and_order_does_not_matter(self):
        row=dict(self.rows[0],id='e2',targetId='T2',diseaseId='D2',drugId='C2')
        self.rows.append(row);a=self.run_endpoint();self.rows.reverse();self.units.reverse();b=self.run_endpoint()
        self.assertEqual(a,b);self.assertEqual(a['dependence']['component_sizes'],[2])
        self.rows[0]['nct_ids']=[];self.rows[0]['drugId']='C1'
        self.assertEqual(self.run_endpoint()['dependence']['component_sizes'],[2])

    def test_missing_links_are_not_independence_evidence(self):
        self.rows[0]['nct_ids']=[];self.rows[0]['drugId']=None
        r=self.run_endpoint()['units'][0]
        self.assertIn('drug_link_missing',r['dependence_limits']);self.assertIn('trial_link_missing',r['dependence_limits'])

    def test_positive_with_an_additional_undated_event_is_existential(self):
        self.rows.append(dict(self.rows[0],id='e2',studyStartDate=None))
        r=self.run_endpoint()['units'][0];self.assertEqual(r['candidate_operational_label'],1)
        self.assertIn('phase3_date_unresolved',r['uncertainty'])

    def test_source_and_unit_contracts_fail_closed(self):
        self.rows[0]['datasourceId']='gwas_catalog'
        with self.assertRaises(ValueError):self.run_endpoint()
        self.rows[0]['datasourceId']='chembl';self.rows[0]['targetId']=None
        with self.assertRaises(ValueError):self.run_endpoint()
        self.rows[0]['targetId']='T1';self.units.append(copy.deepcopy(self.units[0]))
        with self.assertRaises(ValueError):self.run_endpoint()

    def test_cross_pair_reuse_of_evidence_id_is_a_conflict(self):
        self.rows.append(dict(self.rows[0],targetId='T2',diseaseId='D2'))
        self.assertTrue(all(x['candidate_operational_label'] is None for x in self.run_endpoint()['units']))

    def test_invalid_bounds_and_boolean_completeness_fail(self):
        for args in (dict(horizon='2025-01-01'),dict(origin='2025'),dict(source_complete=1)):
            with self.assertRaises(ValueError):self.run_endpoint(**args)

    def test_output_retains_exact_window_and_future_numeric_phase_is_unknown(self):
        r=self.run_endpoint()
        self.assertEqual(r['chronology'],dict(origin='2025-01-01',horizon='2025-07-01',observation_freeze='2025-09-18'))
        self.rows[0]['clinicalPhase']=10**400
        self.assertEqual(self.run_endpoint()['units'][0]['source_state'],'unresolved')


if __name__=='__main__':unittest.main()
