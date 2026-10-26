"""Frozen question-pilot preparation/lifecycle fixtures; no native execution."""
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_science_question_interpretation_local as fixtures
from asof.serde import ContractError,canonical,fingerprint,read_json,write_json,encode
from asof.journal import RunJournal,read_chain
from asof.agents import Usage
from tools.science.run_comparison import pin,check_pin
from tools.science import run_question_development as launch
from tools.science import question_interpretation_runtime as runtime


class QuestionDevelopmentTests(unittest.TestCase):
    def setUp(self):fixtures.QuestionLocalTests.setUp(self)

    def prepare(self):
        receipt=self.inputs/'receipt.json';reference=self.inputs/'reference.json'
        acceptance=self.inputs/'acceptance.json';protocol=self.inputs/'protocol.md'
        write_json(receipt,dict(status='downloaded_hash_verified_not_inference_validated',root=str(self.root/'models'),
            revision='synthetic',runtime_files=[dict(path='runtime/llama-server.exe',sha256='1'*64)],
            items=[dict(name='synthetic.gguf',sha256='0'*64)]))
        write_json(reference,dict(role='evaluation_only',secret='Must never enter a model request'))
        guard=self.inputs/'guard.json';report=self.inputs/'full-report.json'
        code=['tools/science/'+name for name in ['question_interpretation_local.py','question_interpretation_render.py',
            'question_interpretation_runtime.py','interpretation_questions.py','bounded_interpretation.py',
            'local_interpretation.py','run_interpretation_development.py']]
        write_json(guard,dict(status='passed',code_unchanged=True,code_pins={name:pin(launch.ROOT/name)['sha256'] for name in code}))
        write_json(report,dict(mode='full',status='passed',tests=dict(run=1239,failures=0,errors=0,skipped=[]),
            required_probes_exit_code=0,packaging=dict(dependency_free_demo='passed')))
        write_json(acceptance,dict(status='passed_native_renderer_and_transport_mechanics_only',native_pilot_executed=False,
            proofs=[pin(guard),pin(report)]))
        protocol.write_text('Synthetic protocol; not scientific permission.')
        specs=[dict(task_id=task_id,family=family,observation_ids=self.ids) for task_id,family in launch.TASKS]
        return launch.prepare(self.root/'pilot',self.inputs/'case.json',self.inputs/'snapshot.json',None,specs,
            receipt,reference,acceptance,protocol)

    def test_plan_has_exact_question_pack_and_no_evaluator_input(self):
        plan=read_json(check_pin(self.prepare()));launch.validate_plan(plan)
        self.assertEqual(tuple((t['task_id'],t['family']) for t in plan['tasks']),launch.TASKS)
        for task in plan['tasks']:
            request=read_json(check_pin(task['request']))
            self.assertNotIn('reference_seal',request);self.assertNotIn('Must never enter',str(request))
            self.assertEqual(request['source_request']['bounds']['max_claims'],2)

    def test_existing_preparation_and_execution_are_not_repeated(self):
        proof=self.prepare()
        with self.assertRaises(FileExistsError):self.prepare()
        out=self.root/'pilot';journal=RunJournal(out/'execution',kind='build');journal.close()
        with patch.object(launch,'_start') as start:
            with self.assertRaises(FileExistsError):launch.execute(proof)
            start.assert_not_called()

    def test_plan_boundaries_and_budget_are_strict(self):
        original=read_json(check_pin(self.prepare()))
        for key,value in [('schema_version',True),('max_claims',3),('automatic_generation_retries',True),
                          ('fresh_holdout',True),('evaluator_content_in_model_requests',True),('provider_spend_usd',False)]:
            plan=copy.deepcopy(original);plan[key]=value
            with self.subTest(key=key),self.assertRaises(ContractError):launch.validate_plan(plan)
        plan=copy.deepcopy(original);plan['budget']['max_input_tokens']+=1
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_code_request_and_model_pins_reject_resealing(self):
        original=read_json(check_pin(self.prepare()))
        plan=copy.deepcopy(original);plan['code']=plan['code'][1:]
        with self.assertRaises(ContractError):launch.validate_plan(plan)
        path=check_pin(original['tasks'][0]['request']);request=read_json(path);request['question_key']='wrong'
        write_json(path,request);plan=copy.deepcopy(original);plan['tasks'][0]['request']=pin(path)
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_model_config_cannot_grow_budget_or_change_weights(self):
        plan=read_json(check_pin(self.prepare()));path=check_pin(plan['model_config']);config=read_json(path)
        config['model_provenance']['weights_sha256']['synthetic.gguf']='f'*64
        write_json(path,config);plan['model_config']=pin(path)
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_changed_or_omitted_task_family_rejected(self):
        original=read_json(check_pin(self.prepare()))
        for tasks in [original['tasks'][:1],list(reversed(original['tasks'])),original['tasks']*2]:
            plan=copy.deepcopy(original);plan['tasks']=tasks
            with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_failed_plan_never_starts_server_and_keeps_primary(self):
        proof=self.prepare();original=launch.write_json
        def fail_report(path,value):
            if path.name=='execution-report.json':raise OSError('fixture report failure')
            original(path,value)
        with (patch.object(launch,'validate_plan',side_effect=ContractError('primary plan error')),
              patch.object(launch,'_start') as start,patch.object(launch,'write_json',side_effect=fail_report)):
            with self.assertRaisesRegex(ContractError,'primary plan error'):launch.execute(proof)
            start.assert_not_called()
        events=read_chain(self.root/'pilot/execution/journal.jsonl')
        self.assertEqual(events[-1]['details']['error_class'],'ContractError')

    def process(self):
        class Process:
            pid=1234;stopped=False
            def poll(self):return 0 if self.stopped else None
            def terminate(self):self.stopped=True
            def wait(self,timeout):self.stopped=True;return 0
        return Process()

    def test_startup_failure_stops_owned_process(self):
        proof=self.prepare();process=self.process()
        with (patch.object(launch,'_start',return_value=process),patch.object(launch,'_ready',side_effect=TimeoutError('startup')),
              patch.object(launch,'run_question_interpretation') as run):
            with self.assertRaises(TimeoutError):launch.execute(proof)
            run.assert_not_called()
        self.assertTrue(process.stopped)

    def test_timeout_keeps_estimated_usage_and_stops_without_second_task(self):
        proof=self.prepare();process=self.process()
        def failed_task(case,snapshot,family,job,*args,**kwargs):
            journal=RunJournal(job,kind='build')
            journal.append('question_dispatch',attempt_id='fixture',reserved=encode(Usage(30,40,0.0)))
            journal.fail(TimeoutError('native timeout'),'dispatch');journal.close();raise TimeoutError('native timeout')
        with (patch.object(launch,'_start',return_value=process),patch.object(launch,'_ready'),
              patch.object(launch,'_owned_listener',return_value=True),
              patch.object(launch,'run_question_interpretation',side_effect=failed_task) as run):
            with self.assertRaisesRegex(TimeoutError,'native timeout'):launch.execute(proof)
            self.assertEqual(run.call_count,1)
        self.assertTrue(process.stopped);report=read_json(self.root/'pilot/execution-report.json')
        self.assertEqual(report['calls'],1);self.assertEqual(report['estimated_usage']['output_tokens'],40)
        self.assertFalse((self.root/'pilot/predictions-seal.json').exists())

    def fake_pair(self):
        proof=self.prepare();process=self.process();budgets=[]
        def fake_start(plan,output,journal,ownership):
            write_json(output/'server-command.json',dict(fixture=True))
            for name in ['server.stdout.log','server.stderr.log']:(output/name).write_bytes(b'fake process only')
            return process
        def fake_http_run(case,snapshot,family,job,backend,catalog,**kwargs):
            budgets.append(kwargs['budget'])
            request=launch.prepare_question(case,snapshot,family,catalog,max_claims=2,observation_ids=self.ids).request
            payload=launch.payload_for(request,backend.config)
            native=dict(content=canonical(dict(answer_status='abstained',claims=[],abstention_reason='Synthetic fixture.')).decode(),
                tokens_evaluated=20,tokens_predicted=40,truncated=False,stop=True,stop_type='eos',stopping_word='',
                prompt=payload['prompt'],model='fixture',generation_settings={k:payload[k] for k in ('seed','temperature','n_predict','stop','stream')})
            class Opener:
                def open(self,*args,**kwargs):return io.BytesIO(canonical(native))
            backend.inner.opener=Opener()
            return runtime.run_question_interpretation(case,snapshot,family,job,backend,catalog,**kwargs)
        with (patch.object(launch,'_start',side_effect=fake_start),patch.object(launch,'_ready'),
              patch.object(launch,'_owned_listener',return_value=True),
              patch.object(launch,'run_question_interpretation',side_effect=fake_http_run)):
            seal=read_json(check_pin(launch.execute(proof)))
        return process,budgets,seal

    def test_two_fake_http_tasks_share_budget_and_seal_after_stop(self):
        process,budgets,seal=self.fake_pair()
        self.assertTrue(process.stopped);self.assertEqual(len(seal['tasks']),2)
        report=read_json(check_pin(seal['execution_report']))
        self.assertTrue(report['server_stopped']);self.assertEqual(report['calls'],2)
        self.assertEqual(report['measured_usage']['input_tokens'],40)
        self.assertEqual(budgets[1].max_input_tokens,31980);self.assertEqual(budgets[1].max_output_tokens,7960)
        self.assertEqual(budgets[1].max_calls,15)
        result=launch.verify_predictions(pin(self.root/'pilot/predictions-seal.json'))
        self.assertEqual(result['scientific_validation'],'not_performed');self.assertEqual(result['calls'],2)

    def test_cleanup_failure_does_not_mask_primary_timeout(self):
        proof=self.prepare();process=self.process()
        process.terminate=lambda:(_ for _ in ()).throw(OSError('cleanup fixture'))
        with (patch.object(launch,'_start',return_value=process),
              patch.object(launch,'_ready',side_effect=TimeoutError('primary startup timeout'))):
            with self.assertRaisesRegex(TimeoutError,'primary startup timeout'):launch.execute(proof)
        report=read_json(self.root/'pilot/execution-report.json')
        self.assertFalse(report['server_stopped']);self.assertEqual(report['error_class'],'TimeoutError')
        self.assertEqual(report['secondary_failures'][0]['stage'],'server_cleanup')

    def test_acceptance_label_without_retained_code_and_tests_is_rejected(self):
        plan=read_json(check_pin(self.prepare()));path=check_pin(plan['mechanics_acceptance'])
        acceptance=read_json(path);acceptance['proofs']=[];write_json(path,acceptance)
        plan['mechanics_acceptance']=pin(path)
        with self.assertRaisesRegex(ContractError,'unchanged-code'):launch.validate_plan(plan)

    def test_unowned_listener_cannot_dispatch_and_owned_process_is_stopped(self):
        proof=self.prepare();process=self.process()
        with (patch.object(launch,'_start',return_value=process),patch.object(launch,'_ready'),
              patch.object(launch,'_owned_listener',return_value=False),patch.object(launch,'run_question_interpretation') as run):
            with self.assertRaisesRegex(ContractError,'Owned server unavailable'):launch.execute(proof)
            run.assert_not_called()
        self.assertTrue(process.stopped)

    def test_spawn_handle_survives_log_close_failure(self):
        proof=self.prepare();process=self.process();server=self.root/'fake-server.exe';server.write_bytes(b'not executed')
        original_open=Path.open;original_sha=launch.sha256_file
        class ClosingStream:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self.stream
            def __exit__(self,*args):self.stream.close();raise OSError('injected log close')
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return ClosingStream(stream) if path.name=='server.stdout.log' else stream
        def digest(path):return '1'*64 if Path(path)==server else original_sha(path)
        with (patch.object(launch,'verify_model',return_value=(server,self.root/'fake.gguf')),
              patch.object(launch,'sha256_file',side_effect=digest),patch.object(launch.socket,'socket'),
              patch.object(launch.subprocess,'Popen',return_value=process),patch.object(Path,'open',opened)):
            with self.assertRaisesRegex(OSError,'injected log close'):launch.execute(proof)
        self.assertTrue(process.stopped)
        self.assertTrue(read_json(self.root/'pilot/execution-report.json')['server_stopped'])

    def test_case_drift_after_last_plan_check_fails_before_dispatch(self):
        proof=self.prepare();process=self.process()
        def changed_request(case,snapshot,family,job,backend,catalog,**kwargs):
            case=Path(case);case_doc=read_json(case);case_doc['case_id']='changed-after-plan-check';write_json(case,case_doc)
            request=launch.prepare_question(case,snapshot,family,catalog,max_claims=2,observation_ids=self.ids).request
            backend.quote(request)
            raise AssertionError('Backend accepted a changed frozen request')
        with (patch.object(launch,'_start',return_value=process),patch.object(launch,'_ready'),
              patch.object(launch,'_owned_listener',return_value=True),
              patch.object(launch,'run_question_interpretation',side_effect=changed_request)):
            with self.assertRaisesRegex(ContractError,'Frozen.*request'):launch.execute(proof)
        self.assertTrue(process.stopped);self.assertFalse((self.root/'pilot/predictions-seal.json').exists())

    def test_prediction_seal_failure_retains_terminal_cause(self):
        original=launch.write_json
        def failed_seal(path,value):
            if path.name=='predictions-seal.json':raise OSError('prediction seal disk failure')
            return original(path,value)
        with patch.object(launch,'write_json',side_effect=failed_seal):
            with self.assertRaisesRegex(OSError,'prediction seal disk failure'):self.fake_pair()
        report=read_json(self.root/'pilot/execution-report.json')
        self.assertEqual(report['status'],'failed');self.assertEqual(report['error_class'],'OSError')
        events=read_chain(self.root/'pilot/execution/journal.jsonl')
        self.assertEqual(events[-1]['event'],'build_failed')
        self.assertTrue((self.root/'pilot/failure.json').is_file())

    def test_known_failure_blocks_a_retained_prediction_seal(self):
        self.fake_pair();write_json(self.root/'pilot/failure.json',dict(fixture='retained failure'))
        with self.assertRaises(ContractError):launch.verify_predictions(pin(self.root/'pilot/predictions-seal.json'))

    def test_resealed_aggregate_accounting_cannot_pass_bundle_verifier(self):
        self.fake_pair();path=self.root/'pilot/execution-report.json';report=read_json(path)
        report['measured_usage']['input_tokens']+=1;write_json(path,report)
        seal_path=self.root/'pilot/predictions-seal.json';seal=read_json(seal_path)
        seal['execution_report']=pin(path);write_json(seal_path,seal)
        with self.assertRaises(ContractError):launch.verify_predictions(pin(seal_path))

    def test_config_read_race_fails_before_native_dispatch(self):
        proof=self.prepare();process=self.process();original=launch.LocalQuestionInterpreter
        def changed_config(path):
            path=Path(path);raw=path.read_bytes();config=read_json(path);config['seed']=43;write_json(path,config)
            try:return original(path)
            finally:path.write_bytes(raw)
        def no_dispatch(case,snapshot,family,job,backend,catalog,**kwargs):
            request=launch.prepare_question(case,snapshot,family,catalog,max_claims=2,observation_ids=self.ids).request
            backend.quote(request)
            raise AssertionError('Backend accepted config differing from frozen plan')
        with (patch.object(launch,'_start',return_value=process),patch.object(launch,'_ready'),
              patch.object(launch,'_owned_listener',return_value=True),
              patch.object(launch,'LocalQuestionInterpreter',side_effect=changed_config),
              patch.object(launch,'run_question_interpretation',side_effect=no_dispatch)):
            with self.assertRaisesRegex(ContractError,'Frozen.*config'):launch.execute(proof)
        self.assertTrue(process.stopped)

    def test_payload_hash_gate_prevents_quote_and_generation(self):
        backend=launch.FrozenLocalQuestionInterpreter(self.path,fingerprint(self.request),'f'*64,pin(self.path)['sha256'])
        opener=fixtures.FakeOpener(error=AssertionError('must not dispatch'));backend.inner.opener=opener
        with self.assertRaisesRegex(ContractError,'Frozen payload'):backend.quote(self.request)
        with self.assertRaisesRegex(ContractError,'Frozen payload'):backend.generate(self.request,30)
        self.assertEqual(opener.calls,0);self.assertEqual(backend.inner.records,[])

    def test_task_reconciliation_rejects_different_configured_budget(self):
        _,budgets,seal=self.fake_pair();plan=read_json(check_pin(seal['plan']));task=plan['tasks'][0]
        job=self.root/'pilot/tasks'/task['task_id'];path=job/'configuration.json';config=read_json(path)
        config['budget']['max_input_tokens']=64000;write_json(path,config)
        with self.assertRaisesRegex(ContractError,'budget'):
            launch._match_task(plan,task,job,read_json(job/'report.json'),budgets[0])

    def test_launch_interruption_survives_log_close_failure(self):
        proof=self.prepare();server=self.root/'fake-server.exe';server.write_bytes(b'not executed')
        original_open=Path.open;original_sha=launch.sha256_file;primary=KeyboardInterrupt('primary launch interrupt')
        class ClosingStream:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self.stream
            def __exit__(self,*args):self.stream.close();raise OSError('secondary log close')
        def opened(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return ClosingStream(stream) if path.name=='server.stdout.log' else stream
        def digest(path):return '1'*64 if Path(path)==server else original_sha(path)
        with (patch.object(launch,'verify_model',return_value=(server,self.root/'fake.gguf')),
              patch.object(launch,'sha256_file',side_effect=digest),patch.object(launch.socket,'socket'),
              patch.object(launch.subprocess,'Popen',side_effect=primary),patch.object(Path,'open',opened)):
            with self.assertRaises(KeyboardInterrupt) as caught:launch.execute(proof)
        self.assertIs(caught.exception,primary)
        self.assertEqual(read_chain(self.root/'pilot/execution/journal.jsonl')[-1]['event'],'build_interrupted')

    def test_health_interruption_survives_response_close_failure(self):
        plan=read_json(check_pin(self.prepare()));process=self.process();primary=KeyboardInterrupt('health interrupt')
        class Health:
            def __enter__(self):return self
            @property
            def status(self):raise primary
            def __exit__(self,*args):raise OSError('secondary health close')
        class Opener:
            def open(self,*args,**kwargs):return Health()
        with (patch.object(launch.urllib.request,'build_opener',return_value=Opener()),
              patch.object(launch.time,'monotonic',side_effect=[0,1,200]),patch.object(launch.time,'sleep')):
            with self.assertRaises(KeyboardInterrupt) as caught:launch._ready(plan,process)
        self.assertIs(caught.exception,primary)


if __name__=='__main__':unittest.main()
