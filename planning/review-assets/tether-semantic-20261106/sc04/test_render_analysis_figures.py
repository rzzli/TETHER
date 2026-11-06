"""Presentation-layer controls; intentionally no model or statistical estimation."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('figure_reader',Path(__file__).with_name('render_analysis_figures.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ANALYSIS=ROOT/'data/cache/sc04-analysis-cli-qualification-attempt04'
ACCEPTED=Path(__file__).parent/'analysis-root-acceptance-fictional03'
ANALYSIS_SHA='acfd87731d44ba1b632bd8b33c4f85ecf8547e256f5dd9300f3047bc94570816'
ACCEPTED_SHA='fbdc09d48dd25ea1265cab5d920f91eca792813d2679dffc437cc2b30fa5ef8c'


class Figures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp=ROOT/'data/cache/sc04-figure-tests';temp.mkdir(exist_ok=True);tempfile.tempdir=str(temp)
    def setUp(self):
        self.results=m.load(ANALYSIS/'worker/RESULTS.json');self.acceptance=m.load(ACCEPTED/'ROOT-ACCEPTANCE.json')
    def extract(self):return m.extract(self.results,self.acceptance,True)
    def test_anchored_actual_fictional_inputs(self):
        data,sources=m.inputs(ANALYSIS,ANALYSIS_SHA,ACCEPTED,ACCEPTED_SHA,True)
        self.assertEqual(data['scheduled_questions'],2);self.assertEqual(len(data['arms']),5)
        self.assertEqual(len(data['contrasts']),2);self.assertEqual(len(data['contrasts'][0]['contrasts']),6)
        self.assertIsNone(data['contrasts'][0]['contrasts'][0]['ci95']);self.assertEqual(sources['results'],m.proof(ANALYSIS/'worker/RESULTS.json'))
    def test_fictional_never_production(self):
        with self.assertRaises(ValueError):m.extract(self.results,self.acceptance,False)
    def test_missing_arm(self):
        self.results['arms'].pop('L/R')
        with self.assertRaises(ValueError):self.extract()
    def test_incomplete_schedule(self):
        self.results['arms']['L/O']['scheduled_count']=1
        with self.assertRaises(ValueError):self.extract()
    def test_rate_count_mismatch(self):
        self.results['arms']['L/O']['raw_metrics']['accuracy']=1
        with self.assertRaises(ValueError):self.extract()
    def test_nonfinite_metric(self):
        self.results['arms']['L/O']['raw_metrics']['accuracy']=float('nan')
        with self.assertRaises(ValueError):self.extract()
    def test_zero_denominator_precision_undefined(self):
        a=self.results['arms']['L/O'];a['counts']['raw_answered']=0;a['raw_metrics']['coverage']=0
        a['counts']['raw_correct']=0;a['raw_metrics']['accuracy']=0
        a['raw_metrics']['precision']=0;a['statistical_raw_precision']=None;a['raw_precision_defined']=False
        for panel in self.results['paired']['metrics']['raw_accuracy'].values():
            for key,v in dict(expansion_at_lexical=.5,ranking_at_lexical=.5,combined_vs_lexical=.5,interaction=-.5,marginal_expansion=.25,marginal_ranking=.25).items():panel['contrasts'][key]['estimate']=v
        self.assertIsNone(self.extract()['arms'][0]['substantive_precision'])
    def test_zero_precision_cannot_be_presented_as_defined(self):
        a=self.results['arms']['L/O'];a['counts']['raw_answered']=0;a['raw_metrics']['coverage']=0;a['statistical_raw_precision']=0
        a['counts']['raw_correct']=0;a['raw_metrics']['accuracy']=0
        with self.assertRaises(ValueError):self.extract()
    def test_correct_cannot_exceed_substantive_answers(self):
        a=self.results['arms']['L/O'];a['counts']['raw_answered']=0;a['raw_metrics']['coverage']=0
        a['statistical_raw_precision']=None;a['raw_precision_defined']=False
        with self.assertRaises(ValueError):self.extract()
    def test_precision_must_match_count_ratio(self):
        a=self.results['arms']['L/O'];a['statistical_raw_precision']=a['raw_metrics']['precision']=.25
        with self.assertRaises(ValueError):self.extract()
    def test_contrast_must_match_arm_rates(self):
        self.results['paired']['metrics']['raw_accuracy']['question_sensitivity']['contrasts']['interaction']['estimate']=.5
        with self.assertRaises(ValueError):self.extract()
    def test_missing_contrast(self):
        self.results['paired']['metrics']['raw_accuracy']['question_sensitivity']['contrasts'].pop('interaction')
        with self.assertRaises(ValueError):self.extract()
    def test_one_group_interval_cannot_be_fabricated(self):
        self.results['paired']['metrics']['raw_accuracy']['publication_components']['contrasts']['interaction']['ci95']=[0,0]
        with self.assertRaises(ValueError):self.extract()
    def test_interval_reversal(self):
        self.results['paired']['metrics']['raw_accuracy']['question_sensitivity']['contrasts']['interaction']['ci95']=[1,-1]
        with self.assertRaises(ValueError):self.extract()
    def test_interval_does_not_have_to_contain_point(self):
        # Percentile intervals can exclude the original estimate; render endpoints, not signed xerr.
        p=self.results['paired']['metrics']['raw_accuracy']['question_sensitivity']['contrasts']['interaction'];p['estimate']=0;p['ci95']=[.1,.2]
        self.assertEqual(self.extract()['contrasts'][1]['contrasts'][3]['ci95'],[.1,.2])
    def test_source_pair_denominator(self):
        self.results['source_metrics']['supplied']['selected']['annotated_source_count']=1
        with self.assertRaises(ValueError):self.extract()
    def test_source_rate_mismatch(self):
        self.results['source_metrics']['supplied']['selected']['annotated_source_recall']=.5
        with self.assertRaises(ValueError):self.extract()
    def test_source_nesting(self):
        v=self.results['source_metrics']['supplied']['retained'];v['matched_annotated_source_count']=0;v['annotated_source_recall']=0
        with self.assertRaises(ValueError):self.extract()
    def test_incomplete_receipt_and_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m.write(root/'data.json',dict(a=1));m.write(root/'RECEIPT.json',dict(status='complete',files=m.inventory(root)))
            anchor=m.proof(root/'RECEIPT.json')['sha256'];m.receipt(root,anchor)
            (root/'data.json').write_text('{}')
            with self.assertRaises(ValueError):m.receipt(root,anchor)
    def test_wrong_external_anchor(self):
        with self.assertRaises(ValueError):m.receipt(ACCEPTED,'0'*64)
    def test_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            args=['--analysis',str(ANALYSIS),'--analysis-sha256',ANALYSIS_SHA,'--acceptance',str(ACCEPTED),'--acceptance-sha256',ACCEPTED_SHA,
                  '--environment','missing','--environment-sha256','0'*64,'--output',d,'--fictional']
            with self.assertRaises(FileExistsError):m.main(args)
    def test_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'fresh'
            args=['--analysis',str(ANALYSIS),'--analysis-sha256',ANALYSIS_SHA,'--acceptance',str(ACCEPTED),'--acceptance-sha256',ACCEPTED_SHA,
                  '--environment','missing','--environment-sha256','0'*64,'--output',str(out),'--fictional']
            with self.assertRaises(FileNotFoundError):m.main(args)
            self.assertEqual(m.load(out/'FAILURE.json')['status'],'failed');self.assertFalse((out/'RECEIPT.json').exists())
    def test_svg_png_fictional_labels_and_zero_precision(self):
        data=self.extract();data['arms'][0]['substantive_precision']=None
        # Deliberately invented renderer-only interval outside its point estimate.
        # Tests finite interval caps without resampling or changing sealed metrics.
        data['contrasts'][1]['contrasts'][3]['ci95']=[.1,.2]
        with tempfile.TemporaryDirectory() as d:
            files=m.render(data,Path(d));self.assertEqual(len(files),6)
            for name in ('01-answer-performance','02-raw-accuracy-contrasts','03-annotated-doi-coverage'):
                svg=(Path(d)/(name+'.svg')).read_text(encoding='utf-8');self.assertIn('FICTIONAL QUALIFICATION',svg)
                self.assertTrue((Path(d)/(name+'.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertIn('Undefined',(Path(d)/'01-answer-performance.svg').read_text(encoding='utf-8'))
            self.assertIn('95% intervals undefined',(Path(d)/'02-raw-accuracy-contrasts.svg').read_text(encoding='utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Figures))
    (a.output/'TESTS.txt').write_text(stream.getvalue(),encoding='utf-8')
    q=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
           helper=m.proof(Path(__file__).with_name('render_analysis_figures.py')),tests_code=m.proof(__file__),analysis_receipt_sha256=ANALYSIS_SHA,acceptance_receipt_sha256=ACCEPTED_SHA)
    m.write(a.output/'QUALIFICATION.json',q);print(stream.getvalue());print(json.dumps(q));raise SystemExit(not result.wasSuccessful())
