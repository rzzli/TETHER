import json
from pathlib import Path
import tempfile
import unittest
from statistics import mean,variance

from asof.serde import sha256_file
from tools.feasibility.registry_power import paired_stats,placements,wilson,simulate,dependency_profile,run


def program(pid,component,state,target=None,sponsor=None):
    return {'program_id':pid,'dependency_component_id':component,'label_state':state,
            'target_ids':[target] if target else [],'origin_lead_sponsors':[sponsor] if sponsor else []}


class RegistryPowerTests(unittest.TestCase):
    def test_paired_auc_and_covariance_match_brute_force_with_ties(self):
        pa,na,pb,nb=[1,2,2],[0,2,3],[0,2,3],[1,1,2]
        def kernel(x,y):return 1.0 if x>y else .5 if x==y else 0.0
        matrix=[[kernel(b,d)-kernel(a,c) for c,d in zip(na,nb)] for a,b in zip(pa,pb)]
        rows=[mean(row) for row in matrix];cols=[mean(col) for col in zip(*matrix)]
        result=paired_stats(pa,na,pb,nb)
        self.assertAlmostEqual(result['difference'],mean(rows))
        self.assertAlmostEqual(result['variance'],variance(rows)/3+variance(cols)/3)
        self.assertAlmostEqual(mean(placements(pa,na)[0]),mean(placements(pa,na)[1]))
        self.assertEqual(paired_stats(pa,na,pa,na)['z'],0)

    def test_invalid_paired_scores_and_intervals_fail(self):
        with self.assertRaises(ValueError):paired_stats([1],[0],[1],[0])
        with self.assertRaises(ValueError):paired_stats([1,float('nan')],[0,1],[1,2],[0,1])
        with self.assertRaises(ValueError):wilson(1,0)
        with self.assertRaises(ValueError):wilson(5,4)
        self.assertEqual(wilson(0,10)[0],0)
        self.assertGreater(wilson(0,10)[1],0)

    def test_dependency_stress_and_missing_ids_do_not_invent_connections(self):
        ps=[program('a','ca','recorded_next_phase_start','T1','S1'),
            program('b','cb','no_recorded_transition_by_cutoff','T1','S2'),
            program('c','cc','unresolved_transition','T2','S2'),
            program('d','cd','no_recorded_transition_by_cutoff')]
        self.assertEqual(dependency_profile(ps,'v04_component')['units'],4)
        self.assertEqual(dependency_profile(ps,'shared_target_connections')['units'],3)
        merged=dependency_profile(ps,'shared_target_and_sponsor_connections')
        self.assertEqual(merged['units'],2)
        self.assertEqual(merged['states'],{'proxy_recorded_start':1,'proxy_no_recorded_start':1})
        with self.assertRaises(ValueError):dependency_profile(ps+[ps[0]],'v04_component')

    def test_null_identical_predictions_determinism_and_insufficient_units(self):
        noise={'case_to_control':0.,'control_to_case':0.}
        a=simulate(10,30,.65,0,1,noise,40,100)
        self.assertEqual(a['rejections'],0);self.assertEqual(a['valid_replicates'],40)
        self.assertEqual(a,simulate(10,30,.65,0,1,noise,40,100))
        self.assertFalse(simulate(1,30,.65,.05,.7,noise,40,100)['estimable'])
        with self.assertRaises(ValueError):simulate(10,30,.65,.05,2,noise,40,100)

    def test_full_pipeline_small_synthetic_fixture_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'cohort-v04').mkdir();scope=root/'scope';scope.mkdir()
            ps=[program('a','ca','recorded_next_phase_start'),program('b','cb','recorded_next_phase_start'),
                program('c','cc','no_recorded_transition_by_cutoff'),program('d','cd','no_recorded_transition_by_cutoff')]
            data=root/'cohort-v04/cohort.jsonl';data.write_text(''.join(json.dumps(p)+'\n' for p in ps))
            sd=scope/'program-scope.json';sd.write_text(json.dumps([{'program_id':p['program_id'],'prior_risk_alerts':[],
                'clinical_scope':'requires_population_review'} for p in ps]))
            pins=[]
            for i,(folder,member) in enumerate([(root,data),(scope,sd)]):
                seal=folder/'seal.json';seal.write_text(json.dumps({'files':[{'path':member.relative_to(folder).as_posix(),'sha256':sha256_file(member)}]}))
                anchor=root/f'anchor{i}.json';anchor.write_text(json.dumps({'canonical_manifest':{'path':str(seal),'sha256':sha256_file(seal)}}))
                pins.append({'path':str(anchor),'sha256':sha256_file(anchor)})
            policy={'protocol_id':'registry-feasibility-power-v0.1','role':'evaluation_only','analysis_units':['v04_component'],
                'primary_replicates':20,'grid_replicates':20,'null_replicates':20,'seed':20261017,'alpha':.05,'target_power':.8,
                'baseline_auc':[.65],'auc_difference':.05,'within_class_score_correlation':[.7],
                'label_error':[{'case_to_control':0.,'control_to_case':0.}],
                'hypothetical_positive_units':[],'hypothetical_no_recorded_units':1000,
                'annotation_cost_scenarios':{'cases':[185],'reviewers':2,'minutes_per_case':[5]}}
            pp=root/'policy.json';pp.write_text(json.dumps(policy));freeze=root/'freeze.json'
            freeze.write_text(json.dumps({'protocol':{'sha256':sha256_file(pp)},'parents':pins}))
            run(pp,freeze,root/'result');summary=json.loads((root/'result/summary.json').read_text())
            self.assertEqual(summary['training_labels'],0);self.assertEqual(summary['scenario_rows'],2)
            with data.open('a') as f:f.write('\n')
            with self.assertRaises(ValueError):run(pp,freeze,root/'bad')
            self.assertTrue((root/'bad/failure.json').exists())


if __name__=='__main__':unittest.main()
