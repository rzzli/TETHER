"""Invented owned HTTP captures only; no server, model or benchmark is opened."""
import base64
from contextlib import contextmanager
import copy
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.alce import producer as p, prompts
from experiments.labbench.tests.test_model import Response, Connection, Timer
from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json


def digest(raw):return hashlib.sha256(raw).hexdigest()


class Partial(Response):
    def __init__(self,error):super().__init__(b'invented partial bytes');self.error=error;self.first=True
    def read1(self,limit):
        if self.first:self.first=False;return super().read1(min(limit,8))
        raise self.error


class ProducerTests(unittest.TestCase):
    def setUp(self):
        workspace=Path(__file__).resolve().parents[1]/'data/cache'
        workspace.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=workspace.resolve(),prefix='alce-producer-invented-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        assets=self.root/'assets';(assets/'runtime').mkdir(parents=True)
        items=[];runtime=[]
        for name in ('fictional.gguf','runtime/llama-server.exe','runtime/library.dll'):
            raw=('invented '+name).encode();(assets/name).write_bytes(raw)
            target=runtime if name.startswith('runtime/') else items
            target.append({('path' if name.startswith('runtime/') else 'name'):name,'bytes':len(raw),'sha256':digest(raw)})
        receipt=assets/'acquisition.json'
        receipt.write_bytes(canonical(dict(root=str(assets),items=items,runtime_files=runtime,
            model_id='invented-model-for-HTTP-tests',revision='invented-v1')))
        self.spec,self.bindings,self.model=p.shared.make_server_spec(receipt,digest(receipt.read_bytes()),
            port=55599,alias='invented-alce',context_tokens=16384)
        self.owner=SimpleNamespace(spec=self.spec,bindings=self.bindings,terminal_record={'pid':24680},assert_ready=lambda:None)
        self.case=dict(id='invented-case',question='Which imaginary lamp?',docs=[dict(title='Imaginary',text='The imaginary lamp is cobalt.',
            source_id='alce:'+'a'*64,citation_position=1)])
        self.configuration=dict(schema_version=1,kind=prompts.CONFIG_KIND,status='declared_configuration',family='asqa',
            model=prompts.MODEL,max_new_tokens=768,temperature=0,top_p=1,seed=47)
        self.request=prompts.build_request(self.case,family='asqa',input_byte_limit=20000,configuration=self.configuration)
        self.call,self.payload=p.make_call(self.request,self.model,limits=p.Limits(16384,20))
        self.calls=[];self.connections=[]

    def body(self,**changes):
        value=dict(prompt=self.payload['prompt'],model='invented-alce',generation_settings=encode(self.payload),
            content='Plain text [9].\nMore raw text without JSON.',tokens_evaluated=50,tokens_predicted=18,
            truncated=False,stop=True,stop_type='eos',stopped_eos=True,stopped_word=False,stopped_limit=False,stopping_word='')
        value.update(changes);return canonical(value)

    @contextmanager
    def wire(self,*,generation=None,tokenization=None,connection_class=Connection):
        pending=[Response(canonical(dict(tokens=list(range(50))))) if tokenization is None else tokenization,
                 Response(self.body()) if generation is None else generation]
        def connect(*args,**kw):
            self.assertTrue(pending,'Unexpected retry or extra dispatch')
            connection=connection_class(pending.pop(0),self.calls);self.connections.append(connection);return connection
        with patch.object(p.native.http.client,'HTTPConnection',side_effect=connect), \
             patch.object(p.native,'_watchdog',return_value=Timer()):yield pending

    def execute(self,root=None,**kw):
        return p.execute_once(self.owner,self.call,self.payload,output=root or self.root/'attempt',
            deadline=time.monotonic()+20,alias='invented-alce',execution_id='invented-physical-1',**kw)

    def replay(self,value):
        return p.verify_attempt(value['root'],value['receipt_sha256'],call=self.call,payload=self.payload,
            owner_pid=24680,alias='invented-alce',server_spec=self.spec,bindings=self.bindings,deadline=time.monotonic()+20)

    def reseal(self,value):
        root=Path(value['root']);receipt=parse_json((root/'RECEIPT.json').read_bytes())
        for name in receipt['files']:
            raw=(root/name).read_bytes();receipt['files'][name].update(bytes=len(raw),sha256=digest(raw))
        raw=canonical(receipt);(root/'RECEIPT.json').write_bytes(raw)
        return dict(value,receipt_sha256=digest(raw))

    def rewrite_chain(self,root,change):
        events=[encode(e) for e in read_chain(root/'journal.jsonl')];change(events)
        previous=None
        for event in events:
            event['previous_sha256']=previous;event.pop('sha256',None);event['sha256']=fingerprint(event);previous=event['sha256']
        (root/'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))

    def test_raw_text_above_mcq_budget_preserved_and_independently_verified(self):
        with self.wire() as pending:value=self.execute();self.assertFalse(pending)
        self.assertEqual([c['path'] for c in self.calls],['/tokenize','/completion'])
        payload=parse_json(self.calls[1]['body'])
        self.assertEqual(payload['n_predict'],768);self.assertNotIn('grammar',payload)
        self.assertEqual(payload['prompt'].encode(),self.request['prompt'].encode())
        result=value['result'];verified=result['verified']
        self.assertEqual(verified['decoded']['raw_text'],'Plain text [9].\nMore raw text without JSON.')
        self.assertEqual(verified['decoded']['native_output'],'Plain text [9].')
        self.assertEqual(verified['decoded']['raw_citations']['out_of_range_count'],1)
        self.assertEqual(verified['usage']['input_tokens'],50)
        self.assertEqual(verified['conservative_reservation']['input_tokens'],len(payload['prompt'].encode())+32)
        self.assertEqual(self.replay(value)['status'],'wire_and_usage_verified')
        inputs=parse_json((Path(value['root'])/'INPUT.json').read_bytes())
        self.assertTrue({'producer.py','prompts.py','data_views.py','agents.py'}<=
                        {Path(source['path']).name for source in inputs['sources']})
        before=len(self.calls)
        with self.wire() as pending:
            with self.assertRaises(FileExistsError):self.execute()
            self.assertEqual(len(pending),2)
        self.assertEqual(len(self.calls),before)

    def test_fixed_token_limit_is_scored_observation_eos_and_word_distinct(self):
        for ordinal,cause in enumerate(('limit','word','eos')):
            changes=dict(stop_type=cause,stopped_eos=cause=='eos',stopped_word=cause=='word',stopped_limit=cause=='limit',
                stopping_word='<|im_end|>' if cause=='word' else '',tokens_predicted=768 if cause=='limit' else 18)
            with self.subTest(cause=cause),self.wire(generation=Response(self.body(**changes))):
                value=self.execute(self.root/f'finish-{ordinal}')
            verified=self.replay(value)['result']['verified']
            self.assertEqual(verified['finish_reason'],cause)
            self.assertEqual(verified['output_limit_reached'],cause=='limit')
            self.assertEqual(verified['decoded']['raw_text'],'Plain text [9].\nMore raw text without JSON.')

    def test_missing_legacy_stop_type_requires_one_positive_cause(self):
        body=parse_json(self.body());body.pop('stop_type')
        with self.wire(generation=Response(canonical(body))):value=self.execute()
        self.assertEqual(self.replay(value)['result']['verified']['finish_reason'],'eos')

    def test_native_float_sampling_echo_matches_exact_integer_request(self):
        before=(fingerprint(self.call),fingerprint(self.payload))
        settings=dict(encode(self.payload),temperature=0.0,top_p=1.0)
        with self.wire(generation=Response(self.body(generation_settings=settings))):value=self.execute()
        checked=self.replay(value)['result']['verified']
        self.assertEqual(checked['usage']['input_tokens'],50)
        self.assertEqual((fingerprint(self.call),fingerprint(self.payload)),before)
        self.assertIs(type(self.payload['temperature']),int)
        self.assertIs(type(self.payload['top_p']),int)
        self.assertEqual([x['path'] for x in self.calls],['/tokenize','/completion'])

    def test_numeric_sampling_echo_rejects_bool_nonfinite_and_changed_values(self):
        variants=[('temperature',False),('top_p',True),('temperature','0'),('top_p','1'),
            ('temperature',1e-15),('top_p',1-1e-15)]
        variants += [(key,value) for key in ('temperature','top_p') for value in (float('nan'),float('inf'),float('-inf'))]
        for ordinal,(key,value) in enumerate(variants):
            body=parse_json(self.body());body['generation_settings'][key]=value
            # Intentionally emit invalid JSON nonfinite values as hostile native
            # wire bytes, bypassing the fixture's strict canonical serializer.
            raw=json.dumps(body,allow_nan=True).encode()
            root=self.root/f'numeric-invalid-{ordinal}'
            with self.subTest(key=key,value=value),self.wire(generation=Response(raw)):
                with self.assertRaises(ContractError):self.execute(root)
            self.assertFalse((root/'RECEIPT.json').exists())

    def test_other_generation_settings_keep_exact_canonical_types(self):
        for ordinal,(key,value) in enumerate((('seed',47.0),('n_predict',768.0),('stream',0),('stop','<|im_end|>'))):
            settings=dict(encode(self.payload));settings[key]=value
            root=self.root/f'other-setting-{ordinal}'
            with self.subTest(key=key),self.wire(generation=Response(self.body(generation_settings=settings))):
                with self.assertRaises(ContractError):self.execute(root)
            self.assertFalse((root/'RECEIPT.json').exists())

    def test_input_truncation_unknown_conflicting_stops_usage_and_settings_fail(self):
        variants=[dict(truncated=True),dict(stop_type='unknown'),dict(stopped_word=True),dict(stop=False),
            dict(stop_type='limit',stopped_eos=False,stopped_limit=True,tokens_predicted=767),
            dict(tokens_evaluated=49),dict(tokens_evaluated=True),dict(tokens_predicted=769),dict(content=None),
            dict(prompt='substituted'),dict(model='wrong'),
            dict(generation_settings=dict(encode(self.payload),top_p=.5)),
            dict(generation_settings=dict(encode(self.payload),grammar='json'))]
        for index,changes in enumerate(variants):
            root=self.root/f'bad-{index}'
            with self.subTest(changes=changes),self.wire(generation=Response(self.body(**changes))):
                with self.assertRaises(ContractError):self.execute(root)
            self.assertTrue((root/'native-response.bin').is_file())
            self.assertTrue((root/'FAILURE.json').is_file());self.assertFalse((root/'RECEIPT.json').exists())

    def test_full_input_and_config_binding_rejects_reference_fields_and_codec(self):
        request=encode(self.request);request['case']['answers']=['FORBIDDEN_REFERENCE']
        with self.assertRaises(ContractError):p.make_call(request,self.model,limits=p.Limits(16384,20))
        for key,value in [('grammar','json'),('n_predict',256),('prompt','changed')]:
            changed=dict(self.payload);changed[key]=value
            with self.assertRaises(ContractError):p.validate_call(self.call,changed)
        for context,seconds in [(True,20),(16385,20),(512,0),(16384,float('inf')),(16384,True)]:
            with self.assertRaises(ContractError):p.Limits(context,seconds)
        with self.assertRaises(prompts.InputBudgetError):
            prompts.build_request(self.case,family='asqa',input_byte_limit=10,configuration=self.configuration)
        self.assertEqual(self.calls,[])

    def test_exact_context_capacity_prevents_generation_without_truncation(self):
        count=16384-768+1
        with self.wire(tokenization=Response(canonical(dict(tokens=list(range(count)))))) as pending:
            with self.assertRaises(p.ContextCapacityError):self.execute()
            self.assertEqual(len(pending),1)
        self.assertEqual([c['path'] for c in self.calls],['/tokenize'])
        failure=parse_json((self.root/'attempt/FAILURE.json').read_bytes())
        self.assertFalse(failure['generation_entered']);self.assertIsNone(failure['reported_usage'])

    def test_context_uses_exact_quote_not_conservative_byte_charge(self):
        config=dict(self.configuration,max_new_tokens=256)
        request=prompts.build_request(self.case,family='asqa',input_byte_limit=20000,configuration=config)
        call,payload=p.make_call(request,self.model,limits=p.Limits(512,20))
        body=canonical(dict(tokens=list(range(50))))
        quote=dict(kind='labbench_tokenization_v1',payload_sha256=fingerprint(payload),endpoint='http://127.0.0.1:55599',owner_pid=24680,
            tokenizer_request=dict(content=payload['prompt'],add_special=True,parse_special=True,with_pieces=False),body_base64=base64.b64encode(body).decode(),
            body_sha256=digest(body),http_status=200,complete=True,error_class=None,elapsed_seconds=.01,token_count=50)
        count,reserve=p._quote(quote,payload,call,pid=24680,endpoint=quote['endpoint'])
        self.assertEqual(count,50);self.assertGreater(reserve.input_tokens,512)

    def test_tokenizer_timeout_generation_timeout_and_interruption_retain_no_retry(self):
        for ordinal,(target,error) in enumerate([('tokenization',TimeoutError('quote failed')),
                ('generation',TimeoutError('completion failed')),('generation',KeyboardInterrupt('interrupted'))]):
            root=self.root/f'failure-{ordinal}';before=len(self.calls)
            kwargs={target:Partial(error)}
            with self.wire(**kwargs):
                with self.assertRaises(type(error)):self.execute(root)
                with self.assertRaises(FileExistsError):self.execute(root)
            self.assertEqual(len(self.calls)-before,1 if target=='tokenization' else 2)
            failure=parse_json((root/'FAILURE.json').read_bytes())
            self.assertEqual(failure['generation_entered'],target=='generation')
            self.assertIsNone(failure['reported_usage']);self.assertFalse(failure['usage_verified'])
            if target=='generation':self.assertEqual((root/'native-failure-body.bin').read_bytes(),b'invented')
            self.assertFalse((root/'RECEIPT.json').exists())

    def test_owner_loss_or_substitution_before_dispatch_never_generates(self):
        self.owner.assert_ready=lambda:(_ for _ in ()).throw(ContractError('not owned'))
        with self.wire(),self.assertRaises(ContractError):self.execute()
        self.assertEqual(self.calls,[])
        self.owner.assert_ready=lambda:None
        changed=encode(self.call);changed['model_provenance']['runtime_sha256']='0'*64
        call,payload=p.make_call(changed['request'],changed['model_provenance'],limits=p.Limits(**changed['limits']))
        with self.wire(),self.assertRaises(ContractError):
            p.execute_once(self.owner,call,payload,output=self.root/'wrong',deadline=time.monotonic()+20,alias='invented-alce',execution_id='wrong')
        self.assertEqual(self.calls,[])

    def test_post_tokenizer_owner_switch_is_failure_without_completion(self):
        class ChangingResponse(Response):
            def close(inner):self.owner.terminal_record['pid']=24681
        with self.wire(tokenization=ChangingResponse(canonical(dict(tokens=list(range(50)))))):
            with self.assertRaises(ContractError):self.execute()
        self.assertEqual([c['path'] for c in self.calls],['/tokenize'])

    def test_complete_http_redirect_or_malformed_body_is_not_success(self):
        for i,response in enumerate([Response(self.body(),302),Response(b'not JSON')]):
            with self.wire(generation=response),self.assertRaises(ContractError):self.execute(self.root/f'http-{i}')
        self.assertEqual(len(self.calls),4)

    def test_capture_and_receipt_write_failures_preserve_attempt_accounting(self):
        original=p.publish_bytes
        for i,name in enumerate(('native-response.bin','RESULT.json','RECEIPT.json')):
            root=self.root/f'write-{i}'
            def fail(path,raw):
                if Path(path).name==name:raise OSError('invented storage failure')
                return original(path,raw)
            with self.wire(),patch.object(p,'publish_bytes',side_effect=fail):
                with self.assertRaises(OSError):self.execute(root)
            failure=parse_json((root/'FAILURE.json').read_bytes())
            self.assertEqual(failure['reported_usage']['input_tokens'],50)
            self.assertEqual(failure['usage_verified'],name!='native-response.bin')
            self.assertFalse((root/'RECEIPT.json').exists())

    def test_failure_journal_and_record_failures_never_replace_primary(self):
        original_append=p.RunJournal.append;original_publish=p.publish_bytes
        def append(journal,event,**details):
            if event=='alce_call_failed':raise OSError('journal persistence')
            return original_append(journal,event,**details)
        def publish(path,raw):
            if Path(path).name=='FAILURE.json':raise PermissionError('record persistence')
            return original_publish(path,raw)
        for i,record_fails in enumerate((False,True)):
            root=self.root/f'persist-{i}';error=TimeoutError('original transport failure')
            with self.wire(generation=Partial(error)),patch.object(p.RunJournal,'append',new=append), \
                 patch.object(p,'publish_bytes',side_effect=publish if record_fails else original_publish):
                with self.assertRaises(TimeoutError) as caught:self.execute(root)
            self.assertIs(caught.exception,error)
            self.assertIn('failure journal: OSError',error.__notes__)
            if record_fails:self.assertIn('failure record: PermissionError',error.__notes__)
            else:self.assertTrue((root/'FAILURE.json').is_file())

    def test_cleanup_error_dominates_complete_transport(self):
        class BadClose(Connection):
            def close(self):raise OSError('invented close failure')
        with self.wire(connection_class=BadClose),self.assertRaises(OSError):self.execute()
        self.assertEqual([c['path'] for c in self.calls],['/tokenize'])
        self.assertTrue((self.root/'attempt/FAILURE.json').is_file())

    def test_wire_replay_external_owner_quote_and_body_substitutions_rejected(self):
        with self.wire():value=self.execute()
        root=Path(value['root']);quote=parse_json((root/'tokenization/result.json').read_bytes());raw=(root/'native-response.bin').read_bytes()
        args=dict(alias='invented-alce',server_spec=self.spec,bindings=self.bindings,owner_pid=24680)
        with self.assertRaises(ContractError):p.verify_response(self.call,self.payload,quote,raw,**dict(args,owner_pid=1))
        wrapper=parse_json(raw);body=parse_json(base64.b64decode(wrapper['body_base64']));body['tokens_predicted']=999
        changed=canonical(body);wrapper.update(body_base64=base64.b64encode(changed).decode(),body_sha256=digest(changed))
        with self.assertRaises(ContractError):p.verify_response(self.call,self.payload,quote,canonical(wrapper),**args)
        with self.assertRaises(ContractError):self.replay(dict(value,receipt_sha256='0'*64))

    def test_resealed_result_journal_clocks_or_terminal_contradictions_rejected(self):
        with self.wire():value=self.execute()
        root=Path(value['root']);original={x:x.read_bytes() for x in root.rglob('*') if x.is_file()}
        def restore():
            for path,raw in original.items():path.write_bytes(raw)
        result=parse_json((root/'RESULT.json').read_bytes());result['reported_usage']['output_tokens']=1
        (root/'RESULT.json').write_bytes(canonical(result))
        with self.assertRaises(ContractError):self.replay(self.reseal(value))
        restore();self.rewrite_chain(root,lambda e:e[2]['details'].update(owner_pid=999))
        with self.assertRaises(ContractError):self.replay(self.reseal(value))
        restore();receipt=parse_json((root/'RECEIPT.json').read_bytes());receipt['seal_elapsed_seconds']=0
        raw=canonical(receipt);(root/'RECEIPT.json').write_bytes(raw)
        with self.assertRaises(ContractError):self.replay(dict(value,receipt_sha256=digest(raw)))
        restore();(root/'orphan').mkdir()
        with self.assertRaises(ContractError):self.replay(value)
        (root/'orphan').rmdir()
        for name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json'):
            (root/name).write_bytes(b'{}')
            with self.assertRaises(ContractError):self.replay(value)
            (root/name).unlink()

    def test_expired_deadline_and_protected_output_have_no_transport(self):
        with self.wire(),self.assertRaises(TimeoutError):
            p.execute_once(self.owner,self.call,self.payload,output=self.root/'expired',deadline=time.monotonic()-1,
                alias='invented-alce',execution_id='expired')
        with self.wire(),self.assertRaises(ContractError):self.execute(self.root/'assets')
        self.assertEqual(self.calls,[])

    def test_final_source_drift_rejected_without_mutating_public_source(self):
        # Add one invented source proof at discovery only. All real native wire,
        # result, source-byte and final revalidation paths still execute.
        dependency=self.root/'invented-dependency.py';dependency.write_bytes(b'original = 1\n')
        proofs=p._sources(time.monotonic()+20)+[p._hash(dependency,time.monotonic()+20)]
        with patch.object(p,'_sources',return_value=proofs):
            with self.wire():value=self.execute()
            original=p.verify_response
            def drift(*args,**kw):
                result=original(*args,**kw)
                dependency.write_bytes(b'original = 2\n')
                return result
            with patch.object(p,'verify_response',side_effect=drift):
                with self.assertRaises(ContractError):self.replay(value)


if __name__=='__main__':unittest.main()
