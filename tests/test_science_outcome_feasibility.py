import copy
import unittest

from tether_engine.serde import ContractError
from tests import test_science_qualification as fixtures
from tools.science.outcome_feasibility import assess
from tools.science.qualification import ENDPOINTS

ADVANCE='registry_next_phase_actual_start'


def program(pid,nct,*,values=None,states=None,drug=None,target=None,sponsor=None,events=None,risk=None):
    rows=[]
    for endpoint in sorted(ENDPOINTS):
        value=(values or {}).get(endpoint)
        row=fixtures.outcome(endpoint,value if value is not None else 0)
        row.update(program_id=pid,case_id=pid,nct_id=nct,drug_ids=[drug] if drug else [],
            target_ids=[target] if target else [],lead_sponsors=[sponsor] if sponsor else [],
            event_id=(events or {}).get(endpoint),origin_risk_qualified=(True if value is not None else risk))
        if value is None:
            row.update(value=None,status=(states or {}).get(endpoint,'unresolved'),event_at=None,
                publicly_available_at=None,source_evidence=[],same_program_scope=None,negative_ascertainment=None)
        elif endpoint=='clinical_success':
            row['success_criterion_evidence' if value else 'failure_criterion_evidence']='Fictional endpoint-specific criterion'
        elif endpoint=='verified_experimental_dosing' and value:
            row['dosing_evidence']='Fictional experimental-arm dosing proof'
        rows.append(row)
    return rows


def scores(rows,endpoint=ADVANCE):
    return [{'program_id':r['program_id'],'endpoint_id':endpoint,'score':.7 if r['value']==1 else .2,
        'qualified':True,'scorer_id':'fictional-frozen-scorer','source_evidence':fixtures.reference()['source_evidence']}
        for r in rows if r['endpoint_id']==endpoint and r['value'] is not None]


class OutcomeFeasibilityTests(unittest.TestCase):
    def test_unknown_censored_and_competing_stay_null_and_endpoints_are_not_nodes(self):
        rows=program('p1','NCT00000001')
        rows+=program('p2','NCT00000002',states={e:'censored' for e in ENDPOINTS})
        rows+=program('p3','NCT00000003',states={e:'competing_event' for e in ENDPOINTS})
        original=copy.deepcopy(rows);report=assess(rows,expected_program_ids=['p1','p2','p3'])
        self.assertEqual(rows,original);self.assertEqual(report['programs'],3);self.assertEqual(report['outcome_rows'],9)
        for endpoint in ENDPOINTS:
            result=report['endpoints'][endpoint]
            self.assertEqual(result['counts'],{'qualified_positive':0,'qualified_negative':0,'resolved_unqualified':0,
                'unresolved':1,'censored':1,'competing_event':1,'qualified_binary':0,'total':3})
            self.assertEqual(result['origin_risk_unknown'],3)
            self.assertIsNone(result['power']['estimated_power']);self.assertFalse(result['fitting']['fit_allowed'])
        self.assertTrue(all(r['analysis_value'] is None and r['source_value'] is None for r in report['observations']))
        self.assertEqual(report['dependence_profiles']['core']['component_sizes'],[1,1,1])

    def test_complete_program_endpoint_membership_and_consistent_origin_metadata(self):
        rows=program('p1','NCT00000001')
        for bad in (rows+rows[:1],rows[:-1]):
            with self.assertRaises(ContractError):assess(bad)
        with self.assertRaisesRegex(ContractError,'membership'):assess(rows,expected_program_ids=['p1','p2'])
        bad=copy.deepcopy(rows);bad[0]['drug_ids']=['different-drug']
        with self.assertRaisesRegex(ContractError,'metadata differs'):assess(bad)
        bad=copy.deepcopy(rows);bad[0]['horizon_at']='2025-12-31T00:00:00Z'
        with self.assertRaisesRegex(ContractError,'Mixed scientific observation'):assess(bad)

    def test_binary_positive_or_negative_requires_origin_risk_true(self):
        for value in (0,1):
            rows=program('p1','NCT00000001',values={ADVANCE:value})
            for risk in (False,None,1):
                bad=copy.deepcopy(rows);next(r for r in bad if r['endpoint_id']==ADVANCE)['origin_risk_qualified']=risk
                with self.assertRaisesRegex(ContractError,'origin risk|Origin-risk'):assess(bad)
        bad=program('p1','NCT00000001');bad[0]['value']=0
        with self.assertRaises(ContractError):assess(bad)

    def test_trial_drug_and_canonical_event_graph_with_separate_sensitivities(self):
        rows=program('p1','NCT00000001',drug='D1',target='T1',sponsor='S1')
        rows+=program('p2','NCT00000002',drug='D1',target='T2',sponsor='S2',events={ADVANCE:'event:shared'})
        rows+=program('p3','NCT00000003',drug='D3',target='T3',sponsor='S3',events={'clinical_success':'event:shared'})
        rows+=program('p4','NCT00000003',drug='D4',target='T4',sponsor='Sponsor X')
        rows+=program('p5','NCT00000005',drug='D5',target='T1',sponsor='S5')
        rows+=program('p6','NCT00000006',drug='D6',target='T6',sponsor='sponsor  x')
        graphs=assess(rows)['dependence_profiles']
        self.assertEqual(graphs['core']['component_sizes'],[4,1,1])
        self.assertEqual(graphs['target_sensitivity']['component_sizes'],[5,1])
        self.assertEqual(graphs['sponsor_sensitivity']['component_sizes'],[5,1])
        self.assertEqual(graphs['target_sponsor_sensitivity']['component_sizes'],[6])
        self.assertEqual(graphs['core']['program_nodes'],6);self.assertEqual(graphs['core']['outcome_rows'],18)
        self.assertEqual({k['kind'] for k in graphs['core']['shared_keys']},{'trial','drug','canonical_event'})
        self.assertIsNone(graphs['core']['effective_sample_size'])

    def binary_fixture(self):
        rows=[]
        for i,value in enumerate((1,0,1,0),1):
            rows+=program('p'+str(i),'NCT'+str(i).zfill(8),values={ADVANCE:value},drug='shared' if i<=2 else 'D'+str(i))
        return rows

    def test_mixed_class_component_has_no_or_label_or_false_power(self):
        rows=self.binary_fixture();report=assess(rows,features_qualified=True,labels_qualified=True,scorer_qualified=True)
        endpoint=report['endpoints'][ADVANCE];self.assertEqual(endpoint['counts']['qualified_positive'],2)
        self.assertEqual(endpoint['counts']['qualified_negative'],2)
        mixed=next(c for c in report['dependence_profiles']['core']['components'] if c['program_count']==2)
        self.assertTrue(mixed['mixed_qualified_classes'][ADVANCE]);self.assertIsNone(mixed['component_analysis_label'])
        self.assertEqual(mixed['endpoint_class_composition'][ADVANCE]['qualified_positive'],1)
        self.assertEqual(mixed['endpoint_class_composition'][ADVANCE]['qualified_negative'],1)
        self.assertEqual(endpoint['power']['status'],'requires_dependence_aware_design');self.assertIsNone(endpoint['power']['estimated_power'])
        self.assertIn('no_qualified_scores',endpoint['empirical_prediction_readiness']['reasons']);self.assertFalse(endpoint['fitting']['fit_allowed'])
        self.assertFalse(endpoint['power']['observed_prediction_scores_required_for_prospective_planning'])
        self.assertEqual(endpoint['power']['target_power'],.8);self.assertEqual(endpoint['power']['target_auroc_difference'],.05)

    def test_qualified_score_coverage_is_not_dependence_aware_power_or_calibration(self):
        rows=self.binary_fixture();report=assess(rows,qualified_scores=scores(rows),features_qualified=True,labels_qualified=True,scorer_qualified=True)
        endpoint=report['endpoints'][ADVANCE]
        self.assertEqual(endpoint['qualified_scored_binary_observations'],4)
        self.assertEqual(endpoint['power']['status'],'requires_dependence_aware_design')
        self.assertFalse(endpoint['power']['estimable']);self.assertIsNone(endpoint['power']['estimated_power'])
        self.assertEqual(endpoint['power']['simulations_performed'],0)
        self.assertIn('power_not_qualified',endpoint['fitting']['reasons']);self.assertFalse(endpoint['fitting']['fit_allowed'])
        self.assertIsNone(endpoint['calibration_precision']['estimate'])

    def test_score_duplicates_unknowns_unqualified_nonfinite_and_partial_coverage(self):
        rows=self.binary_fixture();good=scores(rows)
        for bad in (good+good[:1],[{**good[0],'program_id':'unknown'}],[{**good[0],'score':float('nan')}],
                    [{**good[0],'score':True}],[{**good[0],'score':None}],[{**good[0],'source_evidence':[]}],
                    [good[0],{**good[1],'scorer_id':'different-scorer'}]):
            with self.assertRaises(ContractError):assess(rows,qualified_scores=bad)
        report=assess(rows,qualified_scores=good[:1])
        self.assertIn('qualified_score_coverage_incomplete',report['endpoints'][ADVANCE]['empirical_prediction_readiness']['reasons'])
        unqualified=[{**r,'qualified':False} for r in good]
        report=assess(rows,qualified_scores=unqualified)
        self.assertEqual(report['endpoints'][ADVANCE]['qualified_scored_binary_observations'],0)

    def test_unreviewed_resolved_claim_remains_unqualified_not_a_binary_negative(self):
        rows=program('p1','NCT00000001',values={ADVANCE:1})
        next(r for r in rows if r['endpoint_id']==ADVANCE)['reference_level']='unreviewed'
        report=assess(rows);endpoint=report['endpoints'][ADVANCE]
        self.assertEqual(endpoint['counts']['resolved_unqualified'],1)
        self.assertEqual(endpoint['counts']['qualified_binary'],0)
        observation=next(r for r in report['observations'] if r['endpoint_id']==ADVANCE)
        self.assertEqual(observation['source_value'],1);self.assertIsNone(observation['analysis_value'])

    def test_reproducible_profiles_do_not_depend_on_record_order_or_utc_spelling(self):
        rows=self.binary_fixture();expected=assess(rows)
        equivalent=copy.deepcopy(rows)
        for field in ('origin_at','horizon_at','ascertainment_at'):
            equivalent[0][field]=equivalent[0][field].replace('Z','+00:00')
        self.assertEqual(assess(list(reversed(equivalent))),expected)


if __name__=='__main__':unittest.main()
