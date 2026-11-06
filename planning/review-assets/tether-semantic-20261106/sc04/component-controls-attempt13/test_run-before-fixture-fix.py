from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from asof.serde import canonical,encode,parse_json
from experiments.litqa_comparison import run as r,qualification_fixtures as f


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.pins={'fixture.py':'a'*64}
        answers=f.queries();source=[dict(id=q['id'],question=q['question']) for q in answers]
        products={}
        for key,rows in (('source_queries',source),('answer_queries',answers)):
            path=self.root/(key+'.json');r.write(path,rows);products[key]=r.pipeline.proof(path)
        self.frame=dict(kind='sc04_primary_execution_v1',purpose='fictional_qualification',count=2,
            schedule=[q['id'] for q in answers],phases=list(r.PHASES),
            conditions=['L/O','E/O','L/R','E/R','supplied_source_pending_separate_execution'],
            provider_spend_usd=0,automatic_retry=False,code_pins=self.pins,python=r.pipeline.proof(sys.executable),
            python_version=sys.version,generation_configuration=encode(r.codecs.CONFIG),
            phase_seconds=dict(expand=600,collect=300,rank=600,answer=900),replay_seconds=180,
            port=55628,alias='tether-sc04-primary-qwen14b-v1',model_receipt=dict(sha256=r.RECEIPT_SHA),
            query_products=products,policy=encode(r.acquisition.legacy.DEFAULT_POLICY))

    def load(self):
        path=self.root/'FRAME.json';r.write(path,self.frame)
        with patch.object(r,'code_pins',return_value=self.pins):
            return r.load_frame(path,r.pipeline.proof(path)['sha256'])

    def test_frame_and_separate_product_validation(self):
        frame=self.load();r.validate_products(frame)
        with patch.object(r.pipeline,'read',side_effect=AssertionError('Task read during frame loading')):
            self.load()

    def test_invalid_deadline_rejected_before_dispatch(self):
        for value in (0,True,float('inf'),21601):
            self.frame['phase_seconds']['answer']=value
            with self.assertRaises((ValueError,TypeError)):self.load()

    def test_unqualified_model_and_incomplete_schedule_rejected(self):
        self.frame['model_receipt']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'model receipt'):self.load()
        self.frame['model_receipt']['sha256']=r.RECEIPT_SHA
        self.frame['schedule']=self.frame['schedule'][:1]
        with self.assertRaisesRegex(ValueError,'schedule'):self.load()

    def test_question_projection_mismatch_fails(self):
        path=Path(self.frame['query_products']['source_queries']['path'])
        value=parse_json(path.read_bytes());value[0]['question']='A substituted question?'
        r.write(path,value);self.frame['query_products']['source_queries']=r.pipeline.proof(path)
        with self.assertRaisesRegex(ValueError,'projections differ'):r.validate_products(self.load())

    def test_source_role_rejects_choices(self):
        self.frame['query_products']['source_queries']=self.frame['query_products']['answer_queries']
        with self.assertRaises(ValueError):r.queries(self.frame,'rank')

    def test_invalid_frame_leaves_failure_and_no_dispatch(self):
        args=SimpleNamespace(frame=self.root/'missing.json',frame_sha256='0'*64,output=self.root/'attempt')
        with patch.object(r,'execute_phase') as dispatch:
            with self.assertRaises(ValueError):r.execute(args)
        dispatch.assert_not_called()
        failure=parse_json((args.output/'FAILURE.json').read_bytes())
        self.assertFalse(failure['automatic_retry']);self.assertEqual(failure['completed_phases'],[])

    def test_existing_output_not_reused(self):
        output=self.root/'attempt';output.mkdir();r.write(output/'original.json',dict(preserve=True))
        args=SimpleNamespace(frame=self.root/'missing.json',frame_sha256='0'*64,output=output)
        with patch.object(r,'load_frame') as load:
            with self.assertRaises(FileExistsError):r.execute(args)
        load.assert_not_called();self.assertEqual(len(list(output.iterdir())),1)

    def test_package_inventory_detects_added_and_changed_files(self):
        root=self.root/'package';root.mkdir();r.write(root/'a.json',dict(a=1))
        r.write(root/'PACKAGE-RECEIPT.json',dict(files=r.inventory(root)))
        sha=r.pipeline.proof(root/'PACKAGE-RECEIPT.json')['sha256']
        r.verify_package(root,sha)
        r.write(root/'extra.json',dict(extra=True))
        with self.assertRaisesRegex(ValueError,'inventory'):r.verify_package(root,sha)

    def test_supervisor_error_retains_capture_no_retry(self):
        error=TimeoutError('invented timeout')
        error.result=SimpleNamespace(stdout=b'partial output',stderr=b'failure',returncode=124,supervision={'status':'timeout'})
        with patch.object(r,'supervise_command',side_effect=error) as call:
            with self.assertRaises(TimeoutError):r.supervised(['invented'],r.ProcessLimits(timeout_seconds=1),self.root,'test')
        self.assertEqual(call.call_count,1)
        self.assertEqual((self.root/'test-stdout.txt').read_bytes(),b'partial output')
        self.assertEqual(parse_json((self.root/'test-SUPERVISION.json').read_bytes())['returncode'],124)

    def test_failed_worker_stops_phase_before_replay(self):
        error=RuntimeError('invented worker failure')
        with patch.object(r,'supervised',side_effect=error) as calls:
            with self.assertRaises(RuntimeError):r.execute_phase(self.root/'frame.json','a'*64,self.frame,'expand',self.root/'phase',{},None)
        self.assertEqual(calls.call_count,1)
        self.assertFalse((self.root/'phase/REPLAY.json').exists())
        self.assertFalse(parse_json((self.root/'phase/FAILURE.json').read_bytes())['automatic_retry'])


if __name__=='__main__':unittest.main()
