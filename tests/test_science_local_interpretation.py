"""Local transport/translation fixtures; no native model or scientific claims."""
from pathlib import Path
import copy
import base64
import hashlib
import io
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch
import shutil

from tether_engine.agents import Usage
from tether_engine.contracts import Case
from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint, read_json, write_json
from tools.science.bounded_interpretation import prepare_input,run_interpretation,verify_interpretation
from tools.science.local_interpretation import (compact_request,expand_request,materialize,
                                               LocalInterpreter,payload_for,parse_native,verify_execution)

ROOT=Path(__file__).resolve().parents[1]


class LocalInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        inputs=self.root/'inputs';shutil.copytree(ROOT/'src/tether_engine/demo/v2',inputs);self.inputs=inputs
        case=replace(decode(Case,read_json(inputs/'case.json')),task='T6',endpoint=None)
        write_json(inputs/'case.json',encode(case))
        full=prepare_input(inputs/'case.json',inputs/'snapshot.json')
        self.ids=[full.request['evidence'][0]['observation_id']]
        self.request=prepare_input(inputs/'case.json',inputs/'snapshot.json',observation_ids=self.ids).request
        self.config=dict(schema_version=1,endpoint='http://127.0.0.1:55589',model_id='fictional-pinned-model',
            model_provenance={'weights_sha256':{'fixture.gguf':'0'*64},'runtime_sha256':'1'*64},
            max_prompt_bytes=12288,max_output_tokens=2048,timeout_seconds=30,seed=42)
        self.config_path=self.root/'config.json';write_json(self.config_path,self.config)
        self.prop=dict(subject='fixture source',predicate='supports',object='only its reported association',
            negation=False,modal='possible',population=None,tissue=None,intervention=None,comparator=None,
            outcome=None,timing=None,orientation=None)
        self.wire=dict(claims=[dict(claim_id='C1',kind='caution',text='This fixture does not establish a drug effect.',
            proposition=self.prop,quote_refs=[{'source':'E0','pointer':'/statement'}],
            limitations=['No scientific validation is performed by this fixture.'],applicability='uncertain')],
            abstention_reason=None)

    def native(self,wire=None,**changes):
        payload=payload_for(self.request,self.config)
        value=dict(content=canonical(wire or self.wire).decode('utf-8'),tokens_evaluated=20,tokens_predicted=40,
                   truncated=False,stopped_limit=False,prompt=payload['prompt'],model='fixture-owned-model',
                   generation_settings={k:payload[k] for k in ['seed','temperature','n_predict','stop','stream']})
        value.update(changes);return value

    def backend(self,native=None,error=None):
        backend=LocalInterpreter(self.config_path)
        class Opener:
            calls=0
            def open(self,request,timeout):
                self.calls+=1
                if error:raise error
                return io.BytesIO(canonical(native or self.outer.native()))
        opener=Opener();opener.outer=self;backend.opener=opener
        return backend

    def run_job(self,backend):
        return run_interpretation(self.inputs/'case.json',self.inputs/'snapshot.json',self.root/'output',
                                 backend,observation_ids=self.ids)

    def test_lossless_compaction_round_trip(self):
        self.assertEqual(fingerprint(expand_request(compact_request(self.request))),fingerprint(self.request))

    def test_common_null_is_not_an_absent_field(self):
        request=encode(self.request);other=copy.deepcopy(request['evidence'][0])
        request['evidence'].append(other);request['evidence'][0]['scientific_record']['source_metrics']['only_one']=None
        self.assertEqual(expand_request(compact_request(request)),request)

    def test_bool_int_and_float_scientific_values_remain_distinct(self):
        request=encode(self.request);request['evidence']=[copy.deepcopy(request['evidence'][0]) for _ in range(3)]
        for row,value in zip(request['evidence'],[True,1,1.0]):row['scientific_record']['source_metrics']['typed']=value
        self.assertEqual(fingerprint(expand_request(compact_request(request))),fingerprint(request))

    def test_delimiters_are_escaped_without_mutating_source(self):
        request=encode(self.request);request['instructions']+='<|im_start|>bad'
        before=fingerprint(request);payload=payload_for(request,self.config)
        self.assertNotIn('<|im_start|>bad',payload['prompt']);self.assertEqual(fingerprint(request),before)

    def test_exact_original_quote_materialized(self):
        result=materialize(self.request,self.wire);quote=result['claims'][0]['quotes'][0]
        self.assertEqual(quote['text'],self.request['evidence'][0]['statement'])
        self.assertEqual(quote['span']['end'],len(quote['text'].encode('utf-8')))

    def test_foreign_quote_cannot_be_materialized(self):
        for ref in [{'source':'E99','pointer':'/statement'},{'source':'E0','pointer':'/features'}]:
            wire=copy.deepcopy(self.wire);wire['claims'][0]['quote_refs']=[ref]
            with self.assertRaises(ContractError):materialize(self.request,wire)

    def test_truncated_or_token_limited_native_rejected(self):
        for field in ['truncated','stopped_limit']:
            with self.assertRaises(ContractError):parse_native(self.request,self.native(**{field:True}))

    def test_missing_completeness_flag_rejected(self):
        native=self.native();native.pop('stopped_limit')
        with self.assertRaises(ContractError):parse_native(self.request,native)

    def test_pinned_runtime_modern_eos_completeness_supported(self):
        native=self.native(stop=True,stop_type='eos');native.pop('stopped_limit')
        response,usage=parse_native(self.request,native)
        self.assertEqual(response['claims'][0]['claim_id'],'C1');self.assertEqual(usage.output_tokens,40)

    def test_modern_stop_word_must_match_requested_stop(self):
        native=self.native(stop=True,stop_type='word',stopping_word='<|im_end|>');native.pop('stopped_limit')
        parse_native(self.request,native)
        native['stopping_word']='unexpected'
        with self.assertRaises(ContractError):parse_native(self.request,native)

    def test_limit_unknown_or_conflicting_completion_causes_fail(self):
        for changes in [{'stop':True,'stop_type':'limit'}, {'stop':False,'stop_type':'eos'},
                        {'stop':True,'stop_type':'unknown'}, {'stop':True,'stop_type':'eos','stopped_limit':True}]:
            with self.assertRaises(ContractError):parse_native(self.request,self.native(**changes))

    def test_remote_and_credential_endpoints_denied(self):
        for endpoint in ['https://example.com','http://127.0.0.1.evil.test:80','http://u:p@127.0.0.1:80',
                         'http://127.0.0.1:bad','http://127.0.0.1:0']:
            config=dict(self.config,endpoint=endpoint);write_json(self.config_path,config)
            with self.assertRaises(ContractError):LocalInterpreter(self.config_path)

    def test_context_bound_includes_generation_headroom(self):
        write_json(self.config_path,dict(self.config,max_prompt_bytes=14000,max_output_tokens=2048))
        LocalInterpreter(self.config_path)
        write_json(self.config_path,dict(self.config,max_prompt_bytes=14336))
        with self.assertRaises(ContractError):LocalInterpreter(self.config_path)

    def test_prompt_excess_fails_before_native_call(self):
        backend=self.backend();request=encode(self.request);request['instructions']+='x'*15000
        with self.assertRaises(ContractError):backend.quote(request)
        self.assertEqual(backend.opener.calls,0)

    def test_success_archives_native_and_semantically_replays(self):
        backend=self.backend();self.run_job(backend)
        self.assertTrue(verify_interpretation(self.root/'output')['source_inputs_replayed'])
        self.assertEqual(backend.opener.calls,1)
        self.assertTrue((self.root/'output/backend-execution.json').exists())

    def test_bad_native_keeps_measured_usage_and_original_body(self):
        backend=self.backend(self.native(content='{broken'))
        with self.assertRaises(ContractError):self.run_job(backend)
        events=read_chain(self.root/'output/journal.jsonl')
        account=next(e for e in events if e['event']=='interpretation_accounted')
        self.assertEqual(account['details']['basis'],'adapter_reported')
        self.assertEqual(account['details']['usage']['output_tokens'],40)
        document=read_json(self.root/'output/backend-execution.json')
        self.assertIn('response_base64',document['attempts'][0])

    def test_timeout_no_native_retry(self):
        backend=self.backend(error=TimeoutError('fixture timeout'))
        with self.assertRaises(TimeoutError):self.run_job(backend)
        self.assertEqual(backend.opener.calls,1)
        events=read_chain(self.root/'output/journal.jsonl')
        self.assertEqual(events[-1]['event'],'build_failed')
        account=next(e for e in events if e['event']=='interpretation_accounted')
        self.assertEqual(account['details']['basis'],'conservative_quote')

    def test_native_stale_prompt_is_rejected_with_measured_usage(self):
        backend=self.backend(self.native(prompt='stale other request'))
        with self.assertRaises(ContractError):self.run_job(backend)
        row=read_json(self.root/'output/backend-execution.json')['attempts'][0]
        self.assertEqual(row['status'],'rejected_native_response')
        self.assertEqual(row['measured_usage']['output_tokens'],40)

    def test_peer_modern_stop_causes_must_agree(self):
        for changes in [dict(stopped_eos=False),dict(stopped_word=True),
                        dict(stopping_word='unexpected'),dict(stopped_eos=1)]:
            with self.assertRaises(ContractError):
                parse_native(self.request,self.native(stop=True,stop_type='eos',**changes))

    def test_peer_legacy_stop_causes_must_agree(self):
        for changes in [dict(stopped_eos=True,stopped_word=True),
                        dict(stopped_eos=True,stopping_word='unexpected'),dict(stopped_word=1)]:
            with self.assertRaises(ContractError):parse_native(self.request,self.native(**changes))

    def test_peer_native_settings_preserve_exact_json_types(self):
        for key,value in [('stream',0),('seed',42.0),('temperature',False)]:
            native=self.native();native['generation_settings'][key]=value
            backend=self.backend(native)
            with self.assertRaises(ContractError):
                run_interpretation(self.inputs/'case.json',self.inputs/'snapshot.json',self.root/('output-'+key),
                                   backend,observation_ids=self.ids)
            self.assertEqual(backend.opener.calls,1)
            self.assertEqual(backend.execution_document()['attempts'][0]['measured_usage']['output_tokens'],40)

    def test_actual_runtime_echo_uses_float_temperature(self):
        native=self.native(stop=True,stop_type='eos',stopping_word='')
        native.pop('stopped_limit');native['generation_settings']['temperature']=0.0
        backend=self.backend(native)
        self.run_job(backend)
        self.assertTrue(verify_interpretation(self.root/'output')['source_inputs_replayed'])
        self.assertIs(type(payload_for(self.request,self.config)['temperature']),float)

    def test_verify_execution_rechecks_endpoint_policy(self):
        backend=self.backend();generated=backend.generate(self.request,30)
        provenance=encode(backend.provenance);provenance['config']['endpoint']='http://example.com:80'
        raw=canonical(provenance['config']);provenance.update(config_original_utf8=raw.decode(),config_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ContractError):
            verify_execution(self.request,backend.execution_document(),provenance,
                             read_json_text(generated.content_json),encode(generated.usage))

    def test_verify_execution_rechecks_native_generation_cap(self):
        backend=self.backend();generated=backend.generate(self.request,30);document=backend.execution_document()
        row=document['attempts'][0];row['native_response']['tokens_predicted']=2100;body=canonical(row['native_response'])
        row.update(response_base64=base64.b64encode(body).decode(),response_bytes=len(body),
                   response_sha256=hashlib.sha256(body).hexdigest(),measured_usage=encode(Usage(20,2100,0)))
        with self.assertRaises(ContractError):
            verify_execution(self.request,document,encode(backend.provenance),
                             read_json_text(generated.content_json),encode(Usage(20,2100,0)))

    def test_peer_native_text_and_limitations_bounds_enforced(self):
        for update in [{'text':'x'*1801},{'limitations':['limit']*5}]:
            wire=copy.deepcopy(self.wire);wire['claims'][0].update(update)
            with self.assertRaises(ContractError):parse_native(self.request,self.native(wire))

    def test_peer_archive_failure_does_not_mask_timeout_or_terminal_journal(self):
        import tools.science.bounded_interpretation as module
        original=module.write_json;backend=self.backend(error=TimeoutError('native timeout'))
        def fail(path,value):
            if path.name=='backend-execution.json':raise OSError('archive fixture failure')
            return original(path,value)
        with patch.object(module,'write_json',side_effect=fail):
            with self.assertRaises(TimeoutError):self.run_job(backend)
        events=read_chain(self.root/'output/journal.jsonl')
        self.assertEqual(events[-1]['event'],'build_failed')
        self.assertEqual(events[-1]['details']['error_class'],'TimeoutError')
        self.assertEqual(backend.opener.calls,1)


def read_json_text(text):
    from tether_engine.serde import parse_json
    return parse_json(text)


if __name__=='__main__':unittest.main()
