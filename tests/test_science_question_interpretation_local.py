"""Fake HTTP only: no server, model assets or scientific qualification."""
import base64
import copy
from dataclasses import replace
from http.client import IncompleteRead
import io
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from asof.contracts import Case
from asof.serde import ContractError,canonical,decode,encode,fingerprint,read_json,write_json
from asof.workflow import Budget
from tools.science.interpretation_questions import prepare_question
from tools.science import question_interpretation_local as local
from tools.science import question_interpretation_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]


class FakeOpener:
    def __init__(self,reply=None,error=None):self.reply=reply;self.error=error;self.calls=0
    def open(self,request,timeout):
        self.calls+=1
        if self.error:raise self.error
        return io.BytesIO(self.reply)


class QuestionLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.inputs=self.root/'inputs';shutil.copytree(ROOT/'src/asof/demo/v2',self.inputs)
        case=replace(decode(Case,read_json(self.inputs/'case.json')),task='T6',endpoint=None)
        write_json(self.inputs/'case.json',encode(case))
        full=prepare_question(self.inputs/'case.json',self.inputs/'snapshot.json','mechanism-report.v1').request
        self.ids=[full['source_request']['evidence'][0]['observation_id']]
        self.request=prepare_question(self.inputs/'case.json',self.inputs/'snapshot.json','mechanism-report.v1',observation_ids=self.ids).request
        self.config=dict(schema_version=1,endpoint='http://127.0.0.1:55589',model_id='fixture',
            model_provenance=dict(weights_sha256={'fixture.gguf':'0'*64},runtime_sha256='1'*64),
            max_prompt_bytes=14200,max_output_tokens=2048,timeout_seconds=30,seed=42)
        self.path=self.root/'config.json';write_json(self.path,self.config)
        self.backend=local.LocalQuestionInterpreter(self.path);self.out=self.root/'run'

    def native(self):
        payload=local.payload_for(self.request,self.config)
        wire=dict(answer_status='abstained',abstention_reason='Synthetic transport fixture; no scientific assessment.',claims=[])
        return dict(content=canonical(wire).decode(),tokens_evaluated=20,tokens_predicted=40,truncated=False,
            stop=True,stop_type='eos',stopping_word='',prompt=payload['prompt'],model='fixture',
            generation_settings={k:payload[k] for k in ('seed','temperature','n_predict','stop','stream')})

    def attach(self,native=None,raw=None,error=None):
        self.backend.opener=FakeOpener(raw if raw is not None else canonical(native or self.native()),error)
        return self.backend.opener

    def run_job(self,**kwargs):
        return runtime.run_question_interpretation(self.inputs/'case.json',self.inputs/'snapshot.json',
            'mechanism-report.v1',self.out,self.backend,observation_ids=self.ids,adapter_verifier=local.verify_local_execution,**kwargs)

    def check_archive(self,row=None,response=None,report=None):
        config=read_json(self.out/'configuration.json')
        execution=read_json(self.out/'backend-execution.json')
        if row is not None:execution['attempts'][0]=row
        local.verify_local_execution(self.request,config,response or read_json(self.out/'response.json'),
            execution,report or read_json(self.out/'report.json'))

    def test_success_and_offline_verification(self):
        opener=self.attach();report=self.run_job()
        self.assertEqual(opener.calls,1);self.assertEqual(report['measured_usage']['input_tokens'],20)
        verified=runtime.verify_question_interpretation(self.out,adapter_verifier=local.verify_local_execution)
        self.assertEqual(verified['scientific_validation'],'not_performed');self.assertEqual(opener.calls,1)

    def test_raw_and_translated_hashes_are_separate(self):
        self.attach();self.backend.generate(self.request,30);row=self.backend.records[0]
        raw=base64.b64decode(row['response_base64'])
        import hashlib
        self.assertEqual(row['native_response_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(row['native_response_sha256'],row['response_sha256'])

    def test_legacy_completion_is_accepted(self):
        native=self.native();native.pop('stop_type');native.update(stopped_limit=False,stopped_eos=True,stopped_word=False)
        self.attach(native);self.run_job();runtime.verify_question_interpretation(self.out,adapter_verifier=local.verify_local_execution)

    def test_conflicting_or_truncated_completion_is_rejected(self):
        for changes in [dict(truncated=True),dict(stop_type='limit'),dict(stopped_eos=False),dict(stopped_word=True),dict(stopping_word='bad')]:
            with self.subTest(changes=changes):
                native=self.native();native.update(changes)
                with self.assertRaises(ContractError):local.native_complete(native)

    def test_prompt_and_typed_settings_are_bound(self):
        for key in ['prompt','seed','stream']:
            native=self.native()
            if key=='prompt':native['prompt']+='changed'
            else:native['generation_settings'][key]=True if key=='seed' else 0
            self.backend=local.LocalQuestionInterpreter(self.path);self.attach(native)
            result=self.backend.generate(self.request,30)
            self.assertIn('rejected_native_question_response',result.content_json)
            self.assertEqual(self.backend.records[0]['measured_usage']['output_tokens'],40)

    def test_invalid_wire_retains_measured_failure(self):
        native=self.native();native['content']='{"claims":[]}'
        opener=self.attach(native)
        with self.assertRaises(ContractError):self.run_job()
        self.assertEqual(opener.calls,1);self.assertTrue((self.out/'failure.json').is_file())
        execution=read_json(self.out/'backend-execution.json')
        self.assertEqual(execution['attempts'][0]['measured_usage']['input_tokens'],20)
        self.assertFalse((self.out/'receipt.json').exists())

    def test_malformed_outer_retains_exact_raw(self):
        self.attach(raw=b'{broken')
        with self.assertRaises(ContractError):self.run_job()
        row=read_json(self.out/'backend-execution.json')['attempts'][0]
        self.assertEqual(base64.b64decode(row['response_base64']),b'{broken');self.assertNotIn('measured_usage',row)

    def test_timeout_is_not_retried(self):
        opener=self.attach(error=TimeoutError('fixture'))
        with self.assertRaises(TimeoutError):self.run_job()
        self.assertEqual(opener.calls,1);self.assertTrue((self.out/'failure.json').is_file())
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['calls'],1)

    def test_interruption_is_preserved(self):
        opener=self.attach(error=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):self.run_job()
        self.assertEqual(opener.calls,1);self.assertTrue((self.out/'failure.json').is_file())

    def test_partial_read_is_marked_incomplete(self):
        self.attach(error=IncompleteRead(b'partial',30))
        with self.assertRaises(IncompleteRead):self.backend.generate(self.request,30)
        row=self.backend.records[0];self.assertFalse(row['native_capture_complete'])
        self.assertEqual(base64.b64decode(row['response_base64']),b'partial')

    def test_oversized_native_retains_only_bounded_prefix(self):
        self.attach(raw=b'x'*(local.MAX_NATIVE_BYTES+100))
        with self.assertRaises(ContractError):self.backend.generate(self.request,30)
        row=self.backend.records[0];self.assertEqual(row['response_bytes_retained'],local.MAX_NATIVE_BYTES+1)
        self.assertFalse(row['native_capture_complete'])

    def test_one_use_even_after_timeout(self):
        opener=self.attach(error=TimeoutError())
        with self.assertRaises(TimeoutError):self.backend.generate(self.request,30)
        with self.assertRaises(ContractError):self.backend.generate(self.request,30)
        self.assertEqual(opener.calls,1)

    def test_nonloopback_or_credentialed_config_rejected(self):
        for endpoint in ['https://127.0.0.1:55589','http://localhost:55589','http://user@127.0.0.1:55589','http://127.0.0.1:55589?key=x']:
            config=copy.deepcopy(self.config);config['endpoint']=endpoint;write_json(self.path,config)
            with self.assertRaises(ContractError):local.LocalQuestionInterpreter(self.path)

    def test_native_archive_tampering_is_rejected(self):
        self.attach();self.run_job();original=read_json(self.out/'backend-execution.json')['attempts'][0]
        for key,value in [('response_base64','!'),('native_response_sha256','0'*64),('response_sha256','0'*64),
                          ('payload',{}),('native_response',{}),('measured_usage',{}),('native_capture_complete',False)]:
            with self.subTest(key=key):
                row=copy.deepcopy(original);row[key]=value
                with self.assertRaises(ContractError):self.check_archive(row)

    def test_budget_denial_verifies_without_transport(self):
        opener=self.attach();report=self.run_job(budget=Budget(max_calls=0))
        self.assertEqual(opener.calls,0);self.assertEqual(report['calls'],0)
        self.assertFalse((self.out/'backend-execution.json').exists())
        runtime.verify_question_interpretation(self.out,adapter_verifier=local.verify_local_execution)

    def test_response_and_accounting_tampering_rejected(self):
        self.attach();self.run_job()
        response=read_json(self.out/'response.json');response['abstention_reason']='Different assertion'
        with self.assertRaises(ContractError):self.check_archive(response=response)
        report=read_json(self.out/'report.json');report['measured_usage']['input_tokens']=21
        with self.assertRaises(ContractError):self.check_archive(report=report)

    def test_unknown_or_over_reserved_usage_cannot_succeed(self):
        for value in [True,-1,None,999999]:
            self.backend=local.LocalQuestionInterpreter(self.path);native=self.native();native['tokens_predicted']=value
            self.attach(native)
            if value==999999:
                result=self.backend.generate(self.request,30)
                self.assertIn('rejected_native_question_response',result.content_json)
            else:
                with self.assertRaises(ContractError):self.backend.generate(self.request,30)
            self.assertNotEqual(self.backend.records[0]['status'],'accepted')

    def test_answered_source_alias_translation_preserves_statement(self):
        native=self.native();row=self.request['source_request']['evidence'][0]
        prop=dict(subject='Fixture source',predicate='reports',object='synthetic association',negation=False,
            modal='possible',population=None,tissue=None,intervention=None,comparator=None,outcome=None,timing=None,orientation=None)
        wire=dict(answer_status='answered',abstention_reason=None,claims=[dict(claim_id='R1',kind='source_report',
            text=row['statement'],proposition=prop,quote_refs=[dict(source='E0',pointer='/statement')],
            limitations=[],applicability='uncertain')])
        native['content']=canonical(wire).decode();self.attach(native);self.run_job()
        response=read_json(self.out/'response.json');claim=response['claims'][0]
        self.assertEqual(claim['quotes'][0]['text'],row['statement'])
        self.assertEqual(claim['premise_ids'],[row['observation_id']]);self.assertEqual(response['features'],{})
        self.assertIsNone(response['clinical_probability'])
        runtime.verify_question_interpretation(self.out,adapter_verifier=local.verify_local_execution)

    def test_concurrent_generate_has_one_dispatch(self):
        opener=self.attach();barrier=threading.Barrier(2);original=self.backend.quote
        def synchronized_quote(request):
            result=original(request);barrier.wait(timeout=5);return result
        self.backend.quote=synchronized_quote
        def attempt():
            try:self.backend.generate(self.request,30);return 'accepted'
            except ContractError:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(sorted(results),['accepted','rejected']);self.assertEqual(opener.calls,1)
        self.assertEqual(len(self.backend.records),1)

    def test_close_failure_keeps_complete_read_bytes_and_usage(self):
        raw=canonical(self.native())
        class CloseFailure(io.BytesIO):
            def __exit__(self,*args):
                super().__exit__(*args);raise OSError('fixture close failed')
        class ClosingOpener:
            def open(self,request,timeout):return CloseFailure(raw)
        self.backend.opener=ClosingOpener()
        with self.assertRaises(ContractError):self.run_job()
        row=read_json(self.out/'backend-execution.json')['attempts'][0]
        self.assertEqual(base64.b64decode(row['response_base64']),raw)
        self.assertTrue(row['native_capture_complete']);self.assertEqual(row['error_class'],'OSError')
        self.assertEqual(row['measured_usage']['input_tokens'],20)

    def test_read_failure_survives_secondary_close_error(self):
        for original in [KeyboardInterrupt('fixture interrupt'),IncompleteRead(b'partial',30)]:
            self.backend=local.LocalQuestionInterpreter(self.path)
            class FailingResponse:
                def __enter__(self):return self
                def read(self,size):raise original
                def __exit__(self,*args):raise OSError('secondary close')
            class FailingOpener:
                def open(self,request,timeout):return FailingResponse()
            self.backend.opener=FailingOpener()
            with self.assertRaises(type(original)) as caught:self.backend.generate(self.request,30)
            self.assertIs(caught.exception,original)
            self.assertTrue(any('OSError' in note for note in original.__notes__))
            row=self.backend.records[0];self.assertEqual(row['error_class'],type(original).__name__)
            if isinstance(original,IncompleteRead):
                self.assertEqual(base64.b64decode(row['response_base64']),b'partial')
                self.assertFalse(row['native_capture_complete'])


if __name__=='__main__':unittest.main()
