"""Independent hand-computed synthetic feature/scorer controls."""
from copy import deepcopy
import math
import unittest
import reconstruct as b
import fixture_semantics as f


class FixtureSemanticsTests(unittest.TestCase):
    def setUp(self):
        h={'target_id':'target','indication_id':'disease','target_namespace_version':'v1','indication_namespace_version':'v1',
           'intended_action':'inhibit','modality':'small_molecule','tissue':'fiction'}
        self.case={'case_id':'fiction','origin':'2024-01-01','task':'T1','hypothesis':h,'program':{'phase_at_origin':2},
                   'endpoint':{'name':'phase_2_to_3','horizon_months':24}}
        self.scorer={'kind':'synthetic_demo','model_id':'fixture','feature_schema':'asof-features-v2',
            'aggregation':'mean_of_unique_dependency_groups_v2','coefficients':{'genetic_support':0.8},'intercept':0.25,
            'required_features':['genetic_support'],'missing_values':{},'minimum_coverage':1.0,'calibration':'none',
            'endpoint':'phase_2_to_3','horizon_months':24,'phases':[2],'modalities':['small_molecule'],'intended_actions':['inhibit'],
            'target_namespace_versions':['v1'],'indication_namespace_versions':['v1']}
        self.claims=[{'evidence':{'observation':{'observation_id':'a','features':{'genetic_support':0.75},
            'feature_scope':b.fingerprint(h),'dependency_group':'group-A','study_id':'study','context':{'cohort_ids':['cohort']}}}}]

    def compute(self,status='completed'):
        return f.rebuild(self.case,'synthetic_demo',self.scorer,self.claims,status)

    def test_duplicate_source_dependency_is_not_double_counted(self):
        second=deepcopy(self.claims[0]);second['evidence']['observation']['observation_id']='b';self.claims.append(second)
        features,prediction=self.compute()
        support=features['values']['genetic_support']
        self.assertEqual(support['value'],0.75);self.assertEqual(support['dependency_groups'],1)
        self.assertEqual(support['observation_ids'],['a','b'])
        self.assertEqual(prediction['contributions']['genetic_support']['log_odds'],0.8*0.75)
        self.assertAlmostEqual(prediction['probability'],1/(1+math.exp(-0.85)))

    def test_disjoint_groups_mean_and_conflicting_group_exclusion(self):
        second=deepcopy(self.claims[0]);obs=second['evidence']['observation'];obs.update(observation_id='b',dependency_group='group-B',study_id='different')
        obs['context']['cohort_ids']=[];obs['features']['genetic_support']=0.25;self.claims.append(second)
        self.assertEqual(self.compute()[0]['values']['genetic_support']['value'],0.5)
        obs['context']['cohort_ids']=['cohort']
        features,prediction=self.compute();support=features['values']['genetic_support']
        self.assertIsNone(support['value']);self.assertEqual(support['status'],'conflicting')
        self.assertEqual(support['excluded_groups'],['group-A']);self.assertEqual(prediction['reason'],'required_features_missing')

    def test_action_modality_tissue_scope_suppresses_feature(self):
        for key in ('intended_action','modality','tissue'):
            case=deepcopy(self.case);case['hypothesis'][key]='different'
            features,_=f.rebuild(case,'synthetic_demo',self.scorer,self.claims,'completed')
            self.assertIsNone(features['values']['genetic_support']['value'])
            self.assertEqual(features['values']['genetic_support']['missing_reasons'],['outside_applicability'])

    def test_prefix_abstention_has_no_contribution_or_probability(self):
        features,prediction=self.compute('budget_exhausted')
        self.assertEqual(features['values']['genetic_support']['value'],0.75)
        self.assertEqual(prediction['reason'],'run_incomplete');self.assertIsNone(prediction['probability'])
        self.assertEqual(prediction['contributions'],{});self.assertIsNone(prediction['feature_coverage'])

    def test_resealed_wrong_feature_and_contribution_reject(self):
        features,prediction=self.compute()
        commit={'claims':self.claims,'features':features,'prediction':prediction,'status':'completed'}
        f.verify(self.case,'synthetic_demo',self.scorer,commit)
        bad=deepcopy(commit);bad['features']['values']['genetic_support']['value']=0.9
        with self.assertRaises(ValueError):f.verify(self.case,'synthetic_demo',self.scorer,bad)
        bad=deepcopy(commit);bad['prediction']['contributions']['genetic_support']['log_odds']=9.0
        with self.assertRaises(ValueError):f.verify(self.case,'synthetic_demo',self.scorer,bad)

    def test_broader_features_are_explicitly_unqualified(self):
        self.claims[0]['evidence']['observation']['features']['expression_relevance']=0.5
        with self.assertRaises(ValueError):self.compute()


if __name__=='__main__':unittest.main()
