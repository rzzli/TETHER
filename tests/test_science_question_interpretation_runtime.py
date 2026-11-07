"""Durability/tamper fixtures only; no model execution or scientific validation."""
from pathlib import Path
from dataclasses import replace
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from tether_engine.agents import Usage
from tether_engine.contracts import Case
from tether_engine.journal import RunJournal,read_chain
from tether_engine.serde import ContractError,canonical,decode,encode,fingerprint,read_json,write_json
from tether_engine.workflow import Budget
from tools.science.bounded_interpretation import Generated
from tools.science.interpretation_questions import prepare_question
from tools.science.run_comparison import pin
from tools.science import question_interpretation_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
FAMILY='mechanism-report.v1'
VERIFIER_CALLS=[]


def fixture_execution_verifier(request,config,response,execution,report):
    VERIFIER_CALLS.append(request['question_key'])
    if execution!={'fixture':'execution'}:raise ContractError('Fixture execution differs')


def rejecting_execution_verifier(request,config,response,execution,report):
    raise ContractError('Fixture callback rejects execution')


class FixtureBackend:
    backend_id='synthetic-question-runtime-fixture'
    def __init__(self,response,usage=Usage(20,10,0),error=None,quote=None):
        self.response=response;self.usage=usage;self.error=error;self.calls=0;self.reservation=quote or usage
    def quote(self,request):return self.reservation
    def generate(self,request,timeout_seconds):
        self.calls+=1
        if self.error:raise self.error
        return Generated(self.response,self.usage)


class QuestionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.inputs=self.root/'inputs';shutil.copytree(ROOT/'src/tether_engine/demo/v2',self.inputs)
        case=replace(decode(Case,read_json(self.inputs/'case.json')),task='T6',endpoint=None)
        write_json(self.inputs/'case.json',encode(case));self.prepared=self.prepare();self.out=self.root/'run'

    def prepare(self):return prepare_question(self.inputs/'case.json',self.inputs/'snapshot.json',FAMILY)

    def response(self):
        request=self.prepared.request;row=request['source_request']['evidence'][0]
        prop=dict(subject='Fixture source',predicate='reports',object='invented association',negation=False,
            modal='possible',population=None,tissue=None,intervention=None,comparator=None,outcome=None,timing=None,orientation=None)
        return dict(schema_version=2,kind='question_interpretation',request_sha256=fingerprint(request),
            hypothesis_key=request['hypothesis_key'],question_key=request['question_key'],answer_status='answered',
            claims=[dict(claim_id='F1',kind='caution',text='The invented fixture has limited scope.',proposition=prop,
                premise_ids=[row['observation_id']],quotes=[dict(observation_id=row['observation_id'],pointer='/statement',
                text=row['statement'],span=dict(start=0,end=len(row['statement'].encode('utf-8'))))],
                limitations=['This is a synthetic contract test.'],applicability='uncertain')],
            abstention_reason=None,features={},clinical_probability=None)

    def backend(self,**kwargs):return FixtureBackend(canonical(self.response()).decode(),**kwargs)

    def run_job(self,backend=None,**kwargs):
        return runtime.run_question_interpretation(self.inputs/'case.json',self.inputs/'snapshot.json',FAMILY,
            self.out,backend or self.backend(),**kwargs)

    def reseal(self,events=None):
        if events is None:events=encode(read_chain(self.out/'journal.jsonl'))
        # Repair the terminal report proof, then rebuild the journal and receipt hashes.
        if events[-1]['event']=='build_completed':events[-1]['details']['report']=pin(self.out/'report.json')
        previous=None
        for index,event in enumerate(events):
            event.update(sequence=index,previous_sha256=previous);event.pop('sha256',None)
            event['sha256']=fingerprint(event);previous=event['sha256']
        (self.out/'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))
        receipt=read_json(self.out/'receipt.json')
        for name in receipt['outputs']:receipt['outputs'][name]=pin(self.out/name)
        write_json(self.out/'receipt.json',receipt)

    def test_success_replays_sources_and_seals_journal_without_cycle(self):
        report=self.run_job();verified=runtime.verify_question_interpretation(self.out)
        self.assertEqual(verified['source_admission'],'replayed');self.assertEqual(verified['scientific_validation'],'not_performed')
        receipt=read_json(self.out/'receipt.json');self.assertIn('journal.jsonl',receipt['outputs'])
        last=read_chain(self.out/'journal.jsonl')[-1];self.assertNotIn('receipt',last['details'])
        self.assertEqual(report['calls'],1)
        with self.assertRaises(TypeError):report['measured_usage']['input_tokens']=99

    def test_partial_and_abstained_answers_preserved(self):
        for state in ['partial','abstained']:
            self.out=self.root/state;response=self.response();response.update(answer_status=state,abstention_reason='Additional source context not supplied.')
            if state=='abstained':response['claims']=[]
            self.run_job(FixtureBackend(canonical(response).decode()))
            runtime.verify_question_interpretation(self.out)
            self.assertEqual(read_json(self.out/'response.json')['answer_status'],state)

    def test_exact_recorded_replay_and_exhaustion(self):
        document=dict(schema_version=2,request_sha256=fingerprint(self.prepared.request),response=self.response(),usage=encode(Usage(20,10,0)))
        replay=self.root/'replay.json';replay.write_bytes(json.dumps(document,indent=3).encode())
        backend=runtime.RecordedQuestionInterpreter(replay);self.run_job(backend)
        self.assertEqual(runtime.verify_question_interpretation(self.out)['adapter_verification'],'exact_recorded_replay_not_model_execution')
        replay.unlink();runtime.verify_question_interpretation(self.out)
        with self.assertRaises(ContractError):backend.generate(self.prepared.request,30)

    def test_recorded_wrong_request_and_invalid_schema_rejected(self):
        document=dict(schema_version=2,request_sha256='foreign',response=self.response(),usage=encode(Usage(1,1,0)))
        replay=self.root/'replay.json';write_json(replay,document);backend=runtime.RecordedQuestionInterpreter(replay)
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertFalse(backend.used)
        document['schema_version']=1;write_json(replay,document)
        with self.assertRaises(ContractError):runtime.RecordedQuestionInterpreter(replay)

    def test_budget_abstention_has_zero_dispatch_and_usage(self):
        backend=self.backend();report=self.run_job(backend,budget=Budget(max_calls=0))
        self.assertEqual(backend.calls,0);self.assertEqual(report['calls'],0)
        runtime.verify_question_interpretation(self.out)

    def test_timeout_preserves_estimate_and_never_retries(self):
        backend=self.backend(error=TimeoutError('fixture timeout'))
        with self.assertRaises(TimeoutError):self.run_job(backend)
        summary=runtime.inspect_question_interpretation(self.out)
        self.assertEqual(backend.calls,1);self.assertEqual(summary['calls'],1)
        self.assertEqual(summary['estimated_upper_usage'],encode(backend.reservation))
        self.assertEqual(summary['last_event'],'build_failed');self.assertFalse((self.out/'receipt.json').exists())

    def test_interruption_is_terminal_and_accounted(self):
        backend=self.backend(error=KeyboardInterrupt('fixture interruption'))
        with self.assertRaises(KeyboardInterrupt):self.run_job(backend)
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['last_event'],'build_interrupted')

    def test_malformed_json_retains_exact_raw_before_validation(self):
        backend=FixtureBackend('{not valid JSON')
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertEqual((self.out/'raw-response.txt').read_text(),'{not valid JSON')
        summary=runtime.inspect_question_interpretation(self.out)
        self.assertEqual(summary['measured_usage'],encode(backend.usage))
        self.assertEqual(summary['estimated_upper_usage'],encode(Usage(0,0,0)))

    def test_over_cap_response_retained_and_complete_flag_explicit(self):
        for cap,expected in [(100,False),(1000,True)]:
            self.out=self.root/str(cap);backend=FixtureBackend('x'*300)
            with patch.object(runtime,'MAX_RESPONSE_BYTES',200),patch.object(runtime,'MAX_RAW_BYTES',cap):
                with self.assertRaises(ContractError):self.run_job(backend)
            capture=next(e['details'] for e in read_chain(self.out/'journal.jsonl') if e['event']=='question_response_captured')
            self.assertIs(capture['complete'],expected);self.assertEqual(capture['content_bytes'],300)
            self.assertEqual((self.out/'raw-response.txt').stat().st_size,min(300,cap))

    def test_invalid_usage_still_retains_raw_and_uses_estimate(self):
        backend=self.backend(usage=Usage(-1,1,0),quote=Usage(20,10,0))
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertTrue((self.out/'raw-response.txt').is_file())
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['estimated_upper_usage'],encode(backend.reservation))

    def test_raw_write_failure_accounts_known_usage(self):
        original=Path.open
        def fail(path,*args,**kwargs):
            if path.name=='raw-response.txt':raise OSError('fixture raw write failure')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',fail):
            with self.assertRaises(OSError):self.run_job()
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['measured_usage'],encode(Usage(20,10,0)))

    def test_archive_failure_does_not_mask_timeout_or_repeat_hook(self):
        backend=self.backend(error=TimeoutError('original timeout'));calls=[]
        def archive():calls.append(1);return {'fixture':'raw native placeholder'}
        backend.execution_document=archive;original=runtime.write_json
        def fail(path,value):
            if path.name=='backend-execution.json':raise OSError('archive failure')
            return original(path,value)
        with patch.object(runtime,'write_json',side_effect=fail):
            with self.assertRaises(TimeoutError):self.run_job(backend)
        self.assertEqual(len(calls),1);self.assertEqual(runtime.inspect_question_interpretation(self.out)['failure']['error_class'],'TimeoutError')

    def test_receipt_write_failure_leaves_failed_journal(self):
        original=runtime.write_json
        def fail(path,value):
            if path.name=='receipt.json':raise OSError('receipt write failed')
            return original(path,value)
        with patch.object(runtime,'write_json',side_effect=fail):
            with self.assertRaises(OSError):self.run_job()
        self.assertEqual(read_chain(self.out/'journal.jsonl')[-1]['event'],'build_failed')
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_output_race_dispatches_only_once(self):
        backend=self.backend()
        def run():
            try:self.run_job(backend);return 'completed'
            except FileExistsError:return 'reserved'
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:run(),range(2)))
        self.assertEqual(sorted(results),['completed','reserved']);self.assertEqual(backend.calls,1)
        runtime.verify_question_interpretation(self.out)

    def test_unresolved_attempt_inspection_is_conservative_and_read_only(self):
        journal=RunJournal(self.out,kind='build');journal.append('question_dispatch',attempt_id='unresolved',request_sha256='fixture',reserved=encode(Usage(12,7,0)));journal.close()
        with (self.out/'journal.jsonl').open('ab') as stream:stream.write(b'{incomplete')
        before=(self.out/'journal.jsonl').read_bytes();summary=runtime.inspect_question_interpretation(self.out)
        self.assertEqual(summary['unresolved_attempts'],['unresolved']);self.assertEqual(summary['estimated_upper_usage'],encode(Usage(12,7,0)))
        self.assertEqual((self.out/'journal.jsonl').read_bytes(),before)

    def test_evaluator_parent_and_future_program_fail_before_quote(self):
        for kind in ['evaluator','future']:
            with self.subTest(kind=kind):
                self.out=self.root/kind;backend=self.backend()
                if kind=='evaluator':
                    snapshot=read_json(self.inputs/'snapshot.json');snapshot['sources'][0]['role']='evaluation_only';write_json(self.inputs/'snapshot.json',snapshot)
                else:
                    shutil.copyfile(ROOT/'src/tether_engine/demo/v2/snapshot.json',self.inputs/'snapshot.json')
                    case=read_json(self.inputs/'case.json');case['program']['availability']['annotation_public_at']='2024-01-01';write_json(self.inputs/'case.json',case)
                with self.assertRaises(ContractError):self.run_job(backend)
                self.assertEqual(backend.calls,0);self.assertEqual(runtime.inspect_question_interpretation(self.out)['calls'],0)

    def test_finalization_rechecks_parent_bytes(self):
        backend=self.backend();original=backend.generate
        # Locate the source input rather than assume a demo filename.
        source=self.prepared.archive['source_archive']['source_proofs'][0]
        def change(request,timeout_seconds):
            result=original(request,timeout_seconds);path=Path(source['path']);path.write_bytes(path.read_bytes()+b' ');return result
        backend.generate=change
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertFalse((self.out/'receipt.json').exists())

    def test_report_usage_and_call_tamper_not_rescued_by_resealing(self):
        self.run_job();report=read_json(self.out/'report.json');report['calls']=2;write_json(self.out/'report.json',report);self.reseal()
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_raw_and_accepted_response_cannot_disagree(self):
        self.run_job();response=read_json(self.out/'response.json');response['claims'][0]['text']='Changed after generation.'
        write_json(self.out/'response.json',response);report=read_json(self.out/'report.json');report['response_sha256']=fingerprint(response);write_json(self.out/'report.json',report)
        events=encode(read_chain(self.out/'journal.jsonl'));next(e for e in events if e['event']=='question_response_accepted')['details']['response_sha256']=fingerprint(response);self.reseal(events)
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_configuration_and_journal_identity_cannot_diverge(self):
        self.run_job();config=read_json(self.out/'configuration.json');config['request_sha256']='foreign';write_json(self.out/'configuration.json',config);self.reseal()
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_missing_code_parent_proof_rejected_after_reseal(self):
        self.run_job();config=read_json(self.out/'configuration.json');config['code'].pop();write_json(self.out/'configuration.json',config)
        events=encode(read_chain(self.out/'journal.jsonl'));events[2]['details']['configuration_sha256']=fingerprint(config);self.reseal(events)
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_typed_runtime_marker_cannot_be_resealed_as_float(self):
        self.run_job();events=encode(read_chain(self.out/'journal.jsonl'))
        events[1]['details']['schema_version']=2.0;self.reseal(events)
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_wrong_question_source_scope_and_view_rejected(self):
        self.run_job();view=read_json(self.out/'scientific-view.json');view['request_context']['question']['text']='Rewritten question';write_json(self.out/'scientific-view.json',view);self.reseal()
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_quote_overrun_preserves_actual_measured_usage_and_fails(self):
        backend=self.backend(usage=Usage(30,20,0),quote=Usage(20,10,0))
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['measured_usage'],encode(Usage(30,20,0)))

    def test_zero_provider_budget_cannot_be_raised(self):
        backend=self.backend()
        with self.assertRaises(ContractError):self.run_job(backend,budget=Budget(max_cost_usd=1))
        self.assertEqual(backend.calls,0)

    def test_explicit_callback_runs_before_sealing_and_during_verification(self):
        VERIFIER_CALLS.clear();backend=self.backend();backend.provenance={'kind':'explicit_future_fixture'}
        backend.execution_document=lambda:{'fixture':'execution'}
        self.run_job(backend,adapter_verifier=fixture_execution_verifier)
        self.assertEqual(len(VERIFIER_CALLS),1)
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)
        runtime.verify_question_interpretation(self.out,adapter_verifier=fixture_execution_verifier)
        self.assertEqual(len(VERIFIER_CALLS),2)

    def test_rejected_callback_cannot_finalize(self):
        backend=self.backend();backend.provenance={'kind':'explicit_future_fixture'}
        backend.execution_document=lambda:{'fixture':'execution'}
        with self.assertRaises(ContractError):self.run_job(backend,adapter_verifier=rejecting_execution_verifier)
        self.assertFalse((self.out/'receipt.json').exists())
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['last_event'],'build_failed')

    def test_different_callback_cannot_verify_original_run(self):
        backend=self.backend();backend.provenance={'kind':'explicit_future_fixture'}
        backend.execution_document=lambda:{'fixture':'execution'}
        self.run_job(backend,adapter_verifier=fixture_execution_verifier)
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out,adapter_verifier=rejecting_execution_verifier)

    def test_primary_timeout_survives_terminal_journal_failure(self):
        original=RunJournal.append
        def fail(journal,event,**details):
            if event=='build_failed':raise OSError('secondary terminal failure')
            return original(journal,event,**details)
        with patch.object(RunJournal,'append',fail):
            with self.assertRaisesRegex(TimeoutError,'primary timeout'):self.run_job(self.backend(error=TimeoutError('primary timeout')))
        summary=runtime.inspect_question_interpretation(self.out)
        self.assertEqual(summary['failure']['error_class'],'TimeoutError')
        self.assertTrue((self.out/'failure.json').is_file())

    def test_primary_timeout_survives_archive_notice_failure(self):
        backend=self.backend(error=TimeoutError('primary timeout'))
        def archive():raise OSError('archive hook failure')
        backend.execution_document=archive;original=RunJournal.append
        def fail(journal,event,**details):
            if event=='question_execution_archive_failed':raise OSError('secondary archive notice failure')
            return original(journal,event,**details)
        with patch.object(RunJournal,'append',fail):
            with self.assertRaisesRegex(TimeoutError,'primary timeout'):self.run_job(backend)
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['failure']['error_class'],'TimeoutError')

    def test_primary_timeout_survives_accounting_and_notice_failure(self):
        original=RunJournal.append
        def fail(journal,event,**details):
            if event in {'question_accounted','question_accounting_failed'}:raise OSError('secondary accounting failure')
            return original(journal,event,**details)
        with patch.object(RunJournal,'append',fail):
            with self.assertRaisesRegex(TimeoutError,'primary timeout'):self.run_job(self.backend(error=TimeoutError('primary timeout')))
        summary=runtime.inspect_question_interpretation(self.out)
        self.assertEqual(len(summary['unresolved_attempts']),1)
        self.assertEqual(summary['estimated_upper_usage']['input_tokens'],20)

    def test_primary_timeout_survives_close_failure(self):
        original=RunJournal.close
        def fail(journal):original(journal);raise OSError('secondary close failure')
        with patch.object(RunJournal,'close',fail):
            with self.assertRaisesRegex(TimeoutError,'primary timeout'):self.run_job(self.backend(error=TimeoutError('primary timeout')))
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['failure']['error_class'],'TimeoutError')

    def test_close_failure_after_seal_is_not_verified_as_success(self):
        original=RunJournal.close
        def fail(journal):original(journal);raise OSError('close failed')
        with patch.object(RunJournal,'close',fail):
            with self.assertRaises(OSError):self.run_job()
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)
        self.assertEqual(runtime.inspect_question_interpretation(self.out)['failure']['error_class'],'OSError')

    def test_resealed_replay_must_obey_constructor_field_contract(self):
        replay=self.root/'replay.json';document=dict(schema_version=2,request_sha256=fingerprint(self.prepared.request),response=self.response(),usage=encode(Usage(20,10,0)))
        write_json(replay,document);self.run_job(runtime.RecordedQuestionInterpreter(replay))
        config=read_json(self.out/'configuration.json');document['unaccepted_extra']='outside replay contract';raw=canonical(document)
        config['adapter_provenance'].update(document=document,original_utf8=raw.decode(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        write_json(self.out/'configuration.json',config);events=encode(read_chain(self.out/'journal.jsonl'))
        events[2]['details']['configuration_sha256']=fingerprint(config);self.reseal(events)
        replay.write_bytes(raw)
        with self.assertRaises(ContractError):runtime.RecordedQuestionInterpreter(replay)
        with self.assertRaises(ContractError):runtime.verify_question_interpretation(self.out)

    def test_code_closure_includes_package_initializers(self):
        closure=set(runtime.code_paths())
        for relative in ['src/tether_engine/__init__.py','tools/__init__.py','tools/science/__init__.py']:
            path=ROOT/relative
            if path.is_file():self.assertIn(path.resolve(),closure)

    def test_unknown_or_null_adapter_provenance_requires_verifier_before_dispatch(self):
        for index,provenance in enumerate([None,{'kind':'future_adapter_without_verifier'}]):
            self.out=self.root/('provenance-'+str(index));backend=self.backend();backend.provenance=provenance
            with self.assertRaises(ContractError):self.run_job(backend)
            self.assertEqual(backend.calls,0)

    def test_reserved_recorded_kind_requires_complete_provenance_before_dispatch(self):
        backend=self.backend();backend.provenance={'kind':'recorded_question_response'}
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertEqual(backend.calls,0)

    def test_reserved_recorded_kind_requires_builtin_code_identity_before_dispatch(self):
        replay=self.root/'replay.json';write_json(replay,dict(schema_version=2,
            request_sha256=fingerprint(self.prepared.request),response=self.response(),usage=encode(Usage(20,10,0))))
        recorded=runtime.RecordedQuestionInterpreter(replay)
        backend=self.backend();backend.provenance=recorded.provenance;backend.backend_id=recorded.backend_id
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertEqual(backend.calls,0)


if __name__=='__main__':unittest.main()
