import copy
import unittest
from tools.feasibility.advancement_rules import evaluate, group_shared_events, ALLOWED


def policy():
    return {'protocol_id':'program-advancement-development-v0.3','role':'evaluation_only',
        'clinical_training_labels':False,'allowed_phase_edges':[[1,2],[2,3]],
        'origin':'2023-01-01','endpoint':'2025-01-01','identity_rules':{
            'allowed_product':sorted(ALLOWED['product_relation']),
            'allowed_regimen':sorted(ALLOWED['regimen_relation']),
            'allowed_dose':sorted(ALLOWED['dose_relation']),
            'allowed_population':sorted(ALLOWED['population_relation'])}}


def evidence():
    # Deliberately synthetic; this is not a real clinical adjudication.
    return {'candidate_id':'SYNTHETIC-A','product_relation':'same_product',
        'regimen_relation':'same_composition_route_schedule','dose_relation':'same_dose',
        'population_relation':'same_core_population','origin_active':True,'origin_at_risk':True,
        'origin_stage':2,'next_stage':3,'event_kind':'experimental_regimen_first_dose',
        'event_interval':{'lower':'2024-05-21','upper':'2024-05-21'},'bounds_quality':'supported',
        'report_date':'2024-08-01','historical_content':'verified','canonical_event_id':'synthetic:trial:arm:first-dose',
        'event_linkage':'reviewed','role':'evaluation_only'}


class AdvancementRuleTests(unittest.TestCase):
    def test_qualified_fixture_does_not_become_training_label(self):
        f=evidence();before=copy.deepcopy(f);result=evaluate(f,policy())
        self.assertEqual(result['primary_qualification'],'qualified')
        self.assertIsNone(result['clinical_training_label']);self.assertEqual(f,before)

    def test_origin_nested_population_and_selected_dose_preserve_narrowing(self):
        f={**evidence(),'population_relation':'origin_documented_nested_stratum','dose_relation':'selection_from_origin_options'}
        r=evaluate(f,policy());self.assertEqual(r['primary_qualification'],'qualified')
        self.assertEqual(r['scope_relation'],'admissible_with_narrower_coverage')
        self.assertFalse(r['strict_same_population_and_dose'])

    def test_product_partner_new_population_and_unknown_cannot_silently_match(self):
        for key,value in [('product_relation','different_product_or_payload'),
                          ('regimen_relation','changed_partner_route_or_schedule'),
                          ('population_relation','new_or_expanded_population'),
                          ('population_relation','unknown'),('dose_relation','outside_origin_options')]:
            with self.subTest(key=key):
                result=evaluate({**evidence(),key:value},policy())
                self.assertNotEqual(result['primary_qualification'],'qualified')

    def test_any_arm_and_enrollment_do_not_establish_experimental_dosing(self):
        for event in ['trial_any_arm_first_dose','enrollment_only','none']:
            r=evaluate({**evidence(),'event_kind':event},policy())
            self.assertIn('experimental_regimen_receipt_not_established',r['blocking_reasons'])

    def test_mixed_stage_skipped_phase_and_risk_set_are_explicit_gates(self):
        for key,value in [('origin_stage',None),('origin_stage',1),('origin_active',None),
                          ('origin_active',False),('origin_at_risk',None),('origin_at_risk',False)]:
            self.assertNotEqual(evaluate({**evidence(),key:value},policy())['primary_qualification'],'qualified')
        with self.assertRaises(ValueError):evaluate({**evidence(),'origin_stage':'1/2'},policy())

    def test_conditional_missing_or_preorigin_bounds_and_late_reports(self):
        variants=[{'bounds_quality':'conditional'},{'event_interval':{'lower':None,'upper':'2024-05-21'}},
                  {'event_interval':{'lower':'2022-12-31','upper':'2024-05-21'}},
                  {'report_date':'2025'},{'historical_content':'conditional'},{'event_linkage':'candidate'}]
        for change in variants:self.assertNotEqual(evaluate({**evidence(),**change},policy())['primary_qualification'],'qualified')

    def test_contradictory_dates_and_unknown_schema_values_rejected(self):
        with self.assertRaises(ValueError):evaluate({**evidence(),'report_date':'2024-04-01'},policy())
        with self.assertRaises(ValueError):evaluate({**evidence(),'dose_relation':'roughly_same'},policy())
        with self.assertRaises(ValueError):evaluate({**evidence(),'origin_active':'true'},policy())

    def test_shared_event_count_once_and_split_dependency_retained(self):
        a=evidence();b={**a,'candidate_id':'SYNTHETIC-B'}
        groups=group_shared_events([a,b],[evaluate(a,policy()),evaluate(b,policy())])
        self.assertEqual(len(groups),1);self.assertEqual(groups[0]['qualified_unique_event_count'],1)
        self.assertEqual(len(groups[0]['qualified_candidate_ids']),2)
        self.assertFalse(groups[0]['count_as_independent_per_predecessor'])

    def test_disagreeing_event_claims_are_not_silently_deduplicated(self):
        a=evidence();b={**a,'candidate_id':'SYNTHETIC-B','event_interval':{'lower':'2024-05-22','upper':'2024-05-22'}}
        g=group_shared_events([a,b],[evaluate(a,policy()),evaluate(b,policy())])[0]
        self.assertTrue(g['reconciliation_required']);self.assertEqual(g['qualified_unique_event_count'],0)

    def test_policy_changes_and_non_evaluator_role_fail(self):
        p=policy();p['allowed_phase_edges'].append([1,3])
        with self.assertRaises(ValueError):evaluate(evidence(),p)
        with self.assertRaises(ValueError):evaluate({**evidence(),'role':'agent_visible'},policy())
        with self.assertRaises(ValueError):group_shared_events([evidence(),evidence()],[])


if __name__=='__main__':unittest.main()
