"""Invented corruption/uncertainty controls for planning-only root acceptance."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
r=module(HERE/'accept_analysis.py','root_acceptance')
metrics=module(ROOT/'experiments/litqa_analysis/metrics.py','frozen_metrics_for_invented_fixture')
FIXTURE=ROOT/'data/cache/sc04-analysis-cli-qualification-attempt04'


class RootAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        w=FIXTURE/'worker'
        cls.fixture_data={key:r.load(w/name) for key,name in dict(summary='RESULTS.json',inputs='INPUTS.json',primary='PRIMARY-RECONSTRUCTION.json',
            supplied='SUPPLIED-RECONSTRUCTION.json',percase='PER-CASE.json',native='NATIVE-AGREEMENT.json').items()}
    def data(self):return deepcopy(self.__class__.fixture_data)
    def validate(self,data=None,intervals=False):return r.validate_summary(**(self.data() if data is None else data),recompute_intervals=intervals)

    def test_complete_fictional_summary_reconciles(self):
        result=self.validate(intervals=True);self.assertEqual(result['answer_records'],10);self.assertEqual(result['publication_groups'],1)
    def test_tampered_accuracy_count_rejected(self):
        d=self.data();d['summary']['arms']['L/O']['counts']['raw_correct']=2
        with self.assertRaisesRegex(ValueError,'All-scheduled native counts'):self.validate(d)
    def test_incomplete_five_arm_family_rejected(self):
        d=self.data();del d['summary']['arms']['E/R']
        with self.assertRaisesRegex(ValueError,'five-arm'):self.validate(d)
    def test_tampered_source_coverage_rejected(self):
        d=self.data();d['summary']['source_metrics']['L/O']['selected']['matched_annotated_source_count']=1
        with self.assertRaisesRegex(ValueError,'Source-layer coverage'):self.validate(d)
    def test_budget_violation_rejected_after_output_crossjoins(self):
        d=self.data();d['primary']['source_cases']['E/R'][0]['logical_model_usage']['generation_calls']=4
        d['summary']['source_cases']['E/R']=deepcopy(d['primary']['source_cases']['E/R']);d['percase']['E/R']['sources']=deepcopy(d['primary']['source_cases']['E/R'])
        with self.assertRaisesRegex(ValueError,'Logical arm model budget'):self.validate(d)
    def test_source_projection_counts_do_not_promote_fictional_to_production(self):
        with self.assertRaisesRegex(ValueError,'original input schedule'):r.validate_inputs(self.data()['inputs'],False)
    def test_original_fictional_answer_key_is_fixed(self):
        d=self.data();d['inputs']['references'][1]['answer_index']=0
        with self.assertRaisesRegex(ValueError,'fictional answer keys'):r.validate_inputs(d['inputs'],True)
    def test_missing_contrast_rejected(self):
        d=self.data();del d['summary']['paired']['metrics']['raw_accuracy']['publication_components']['contrasts']['interaction']
        with self.assertRaisesRegex(ValueError,'six contrast family'):self.validate(d)
    def test_unequal_multigroup_varied_outcomes_full_intervals(self):
        ids=list('abcdef');groups=[list('abc'),list('de'),['f']]
        flags={'L/O':[1,0,0,0,0,0],'E/O':[0,1,1,1,0,0],'L/R':[1,1,0,1,1,0],'E/R':[0,0,1,0,0,1]}
        report=metrics.paired_bootstrap(ids,flags,groups,replicates=10000,seed=20261106)
        r.bootstrap_check(report,ids,groups,flags)
        self.assertEqual(report['completed_replicates'],10000)
        self.assertEqual(len(report['contrasts']),6)
        self.assertAlmostEqual(report['contrasts']['interaction']['estimate'],-4/6)
        self.assertTrue(any(v['ci95'][0]!=v['ci95'][1] for v in report['contrasts'].values()))
        sensitive=metrics.paired_bootstrap(ids,flags,[[i] for i in ids],replicates=10000,seed=20261106)
        r.bootstrap_check(sensitive,ids,[[i] for i in ids],flags)
        self.assertNotEqual(report['contrasts']['interaction']['ci95'],sensitive['contrasts']['interaction']['ci95'])
        report['contrasts']['interaction']['ci95'][0]+=.01
        with self.assertRaisesRegex(ValueError,'paired interval'):r.bootstrap_check(report,ids,groups,flags)
    def test_single_group_uncertainty_is_not_zero_width(self):
        d=self.data();report=d['summary']['paired']['metrics']['raw_accuracy']['publication_components']
        report['contrasts']['interaction']['ci95']=[0.,0.]
        ids=[q['id'] for q in d['inputs']['queries']];flags={a:[1,0] for a in r.ARMS}
        with self.assertRaisesRegex(ValueError,'one-component'):r.bootstrap_check(report,ids,[ids],flags)
    def test_zero_attempt_precision_native_zero_statistical_null(self):
        d=self.data();q=d['inputs']['queries'];refs=d['inputs']['references']
        records=[dict(id=x['id'],producer_status='produced',check_status='accepted',prediction=dict(answer_index=1,evidence_ids=[]),reason=None) for x in q]
        actual=r.score(q,refs,records,{x['id']:[] for x in q})
        self.assertEqual(actual['raw_metrics']['precision'],0.)
        self.assertFalse(actual['raw_precision_defined']);self.assertIsNone(actual['statistical_raw_precision'])
        self.assertEqual(actual['counts']['native_unsure'],2)
    def test_wrong_external_receipt_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError,'receipt anchor'):r.receipt(FIXTURE,'0'*64)
    def test_changed_sealed_file_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'one.json').write_bytes(b'{}');record=dict(status='complete',files=r.inventory(root))
            (root/'RECEIPT.json').write_bytes(r.canonical(record));anchor=r.sha((root/'RECEIPT.json').read_bytes())
            (root/'one.json').write_bytes(b'{"changed":true}')
            with self.assertRaisesRegex(ValueError,'sealed inventory'):r.receipt(root,anchor)
    def test_physical_total_budget_and_phase_totals_reconciled(self):
        d=self.data();p=d['primary'];frame=r.load(FIXTURE/'FRAME.json');original=Path(frame['primary']['root'])
        exp=dict(root=original,complete=r.load(original/'COMPLETE.json'))
        r.physical_accounting(exp,p,True)
        p['resources']['physical_model']['generation_calls']+=1
        with self.assertRaisesRegex(ValueError,'Physical model sum'):r.physical_accounting(exp,p,True)
    def test_failure_is_not_silently_unsure(self):
        d=self.data();q=d['inputs']['queries'];refs=d['inputs']['references']
        rows=[dict(id=x['id'],producer_status='parse_failure',check_status='not_run',prediction=None,reason='codec_failure') for x in q]
        scored=r.score(q,refs,rows,{x['id']:[] for x in q})
        self.assertEqual(scored['counts']['parse_failures'],2);self.assertEqual(scored['counts']['native_unsure'],0)
        self.assertEqual(scored['raw_metrics']['accuracy'],0.)
    def test_renderer_preserves_unknown_memory_measurement(self):
        d=self.data();report=r.load(HERE/'analysis-root-acceptance-fictional02/ROOT-ACCEPTANCE.json')
        resources=r.load(FIXTURE/'worker/RESOURCES.json');resources['analysis_process']=None
        text=r.render(report,d['summary'],d['inputs'],resources)
        self.assertIn('process peak working set: unavailable',text)
        self.assertIn('Fictional controls only',text)


if __name__=='__main__':
    import io,json
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    temp=ROOT/'data/cache/sc04-root-acceptance-tests';temp.mkdir(exist_ok=True);tempfile.tempdir=str(temp)
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RootAcceptanceTests))
    (args.output/'TEST-RESULTS.txt').write_text(log.getvalue(),encoding='utf-8')
    report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skipped=len(result.skipped),
        acceptance_source=r.proof(HERE/'accept_analysis.py'),test_source=r.proof(Path(__file__)),scope='Fictional retained outputs and invented corruption/multigroup uncertainty controls only; no production scoring.')
    (args.output/'QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    if not result.wasSuccessful():print(log.getvalue());raise SystemExit(1)
