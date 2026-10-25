"""Boundary/lifecycle fixtures, not biological accuracy or a model evaluation."""
import copy
from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from asof.agents import Usage
from asof.contracts import Case
from asof.journal import read_chain
from asof.serde import ContractError, canonical, decode, encode, fingerprint, read_json, write_json
from tools.science.run_comparison import pin
from asof.workflow import Budget
from tools.science.bounded_interpretation import (
    Generated, RecordedInterpreter, prepare_input, validate_response,
    run_interpretation, verify_interpretation)

ROOT = Path(__file__).resolve().parents[1]


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        shutil.copytree(ROOT / 'src/asof/demo/v2', self.inputs)
        self.case = replace(decode(Case, read_json(self.inputs/'case.json')), task='T6', endpoint=None)
        write_json(self.inputs/'case.json', encode(self.case))
        self.prepared = self.prepare()

    def prepare(self, **kwargs):
        return prepare_input(self.inputs/'case.json', self.inputs/'snapshot.json', **kwargs)

    def response(self, request=None):
        request = request or self.prepared.request
        row = request['evidence'][0]
        quote = dict(observation_id=row['observation_id'], pointer='/statement',
                     span=dict(start=0, end=len(row['statement'].encode('utf-8'))), text=row['statement'])
        proposition = dict(subject='Fixture source', predicate='reports', object='an association',
            negation=False, modal='asserted', population=None, tissue=None, intervention=None,
            comparator=None, outcome=None, timing=None, orientation=None)
        return dict(schema_version=1, kind='generated_interpretation',
            request_sha256=fingerprint(request), hypothesis_key=request['hypothesis_key'],
            claims=[dict(claim_id='I1', kind='source_report', text=row['statement'],
                proposition=proposition, premise_ids=[row['observation_id']], quotes=[quote],
                limitations=['Invented fixture, not biological truth.'], applicability='uncertain')],
            abstention_reason=None, features={}, clinical_probability=None)

    def backend(self, response=None, usage=Usage(0, 0, 0), error=None):
        outer = self
        class Fake:
            backend_id = 'fixture-interpreter'
            calls = 0
            def quote(self, request): return usage
            def generate(self, request, timeout_seconds):
                self.calls += 1
                if error: raise error
                from asof.serde import canonical
                return Generated(canonical(response or outer.response(request)).decode(), usage)
        return Fake()

    def run_job(self, backend, **kwargs):
        return run_interpretation(self.inputs/'case.json', self.inputs/'snapshot.json',
            self.root/'output', backend, **kwargs)

    def test_request_is_immutable_and_prediction_features_hidden(self):
        with self.assertRaises(TypeError): self.prepared.request['coverage']['absence_claim'] = True
        self.assertTrue(all(not r['scientific_record']['features'] for r in self.prepared.request['evidence']))
        self.assertFalse(self.prepared.request['coverage']['absence_claim'])

    def test_binding_covers_opposite_action_and_modality(self):
        response = self.response()
        changed = replace(self.case, hypothesis=replace(self.case.hypothesis, intended_action='activate'))
        write_json(self.inputs/'case.json', encode(changed))
        with self.assertRaises(ContractError): validate_response(self.prepare().request, response)

    def test_evaluator_parent_rejected_before_calls(self):
        snapshot = read_json(self.inputs/'snapshot.json'); snapshot['sources'][0]['role'] = 'evaluation_only'
        write_json(self.inputs/'snapshot.json', snapshot)
        backend = self.backend()
        with self.assertRaises(ContractError): self.run_job(backend)
        self.assertEqual(backend.calls, 0)
        self.assertEqual(read_chain(self.root/'output/journal.jsonl')[-1]['event'], 'build_failed')

    def test_t1_is_outside_interpretation_scope(self):
        write_json(self.inputs/'case.json', encode(replace(self.case, task='T1')))
        with self.assertRaises(ContractError): self.prepare()

    def test_exact_quote_and_foreign_premise_rejected(self):
        for mutate in [lambda r: r['claims'][0]['quotes'][0].update(text='invented'),
                       lambda r: r['claims'][0].update(premise_ids=['foreign'])]:
            response = self.response(); mutate(response)
            with self.assertRaises(ContractError): validate_response(self.prepared.request, response)

    def test_source_report_cannot_be_paraphrase(self):
        response = self.response(); response['claims'][0]['text'] = 'Inference disguised as source quotation.'
        with self.assertRaises(ContractError): validate_response(self.prepared.request, response)

    def test_inference_requires_explicit_limits(self):
        response = self.response(); response['claims'][0].update(kind='scientific_inference', limitations=[])
        with self.assertRaises(ContractError): validate_response(self.prepared.request, response)

    def test_no_structured_probability_or_features(self):
        for key, value in [('features', {'risk': 1}), ('clinical_probability', .8), ('score', 1)]:
            response = self.response(); response[key] = value
            with self.assertRaises(ContractError): validate_response(self.prepared.request, response)

    def test_empty_response_needs_abstention_reason(self):
        response = self.response(); response['claims'] = []
        with self.assertRaises(ContractError): validate_response(self.prepared.request, response)
        response['abstention_reason'] = 'No qualified premises.'
        validate_response(self.prepared.request, response)

    def test_bounds_fail_instead_of_truncating(self):
        with self.assertRaises(ContractError): self.prepare(max_observations=0)
        response = self.response(); response['claims'] *= 20
        with self.assertRaises(ContractError): validate_response(self.prepared.request, response)

    def test_success_is_separate_from_ledger_and_verifiable(self):
        report = self.run_job(self.backend())
        self.assertEqual(report['status'], 'interpretation_contract_completed_not_scientific_validation')
        self.assertFalse((self.root/'output/ledger.json').exists())
        self.assertTrue(verify_interpretation(self.root/'output')['source_inputs_replayed'])

    def test_malformed_response_keeps_measured_accounting(self):
        backend = self.backend(usage=Usage(7,3,0))
        backend.generate = lambda request, timeout_seconds: Generated('{broken', Usage(7, 3, 0))
        with self.assertRaises(ContractError): self.run_job(backend)
        events = read_chain(self.root/'output/journal.jsonl')
        accounting = [e for e in events if e['event']=='interpretation_accounted']
        self.assertEqual(accounting[0]['details']['basis'], 'adapter_reported')
        self.assertEqual(accounting[0]['details']['usage']['input_tokens'], 7)
        self.assertTrue((self.root/'output/raw-response.txt').exists())

    def test_over_quote_retains_actual_usage_and_fails(self):
        backend=self.backend()
        backend.generate=lambda request,timeout_seconds: Generated(canonical(self.response(request)).decode(),Usage(4,2,0))
        with self.assertRaisesRegex(ContractError,'reserved quote'):self.run_job(backend)
        event=next(e for e in read_chain(self.root/'output/journal.jsonl') if e['event']=='interpretation_accounted')
        self.assertEqual(event['details']['usage']['input_tokens'],4)

    def test_timeout_and_interruption_are_retained_without_retry(self):
        for name, error in [('timeout', TimeoutError()), ('interrupt', KeyboardInterrupt())]:
            with self.subTest(name=name):
                backend = self.backend(error=error)
                out = self.root/name
                with self.assertRaises(type(error)):
                    run_interpretation(self.inputs/'case.json', self.inputs/'snapshot.json', out, backend)
                events = read_chain(out/'journal.jsonl')
                self.assertEqual(backend.calls, 1)
                account = next(e for e in events if e['event']=='interpretation_accounted')
                self.assertEqual(account['details']['basis'], 'conservative_quote')
                self.assertTrue(events[-1]['event'] in {'build_failed','build_interrupted'})

    def test_budget_stops_before_dispatch(self):
        backend = self.backend(usage=Usage(1, 1, 1))
        report = self.run_job(backend)
        self.assertEqual(backend.calls, 0)
        self.assertEqual(report['status'], 'abstained_budget')
        self.assertTrue(verify_interpretation(self.root/'output')['source_inputs_replayed'])

    def test_existing_output_never_dispatches_twice(self):
        backend = self.backend(); self.run_job(backend)
        with self.assertRaises(FileExistsError): self.run_job(backend)
        self.assertEqual(backend.calls, 1)

    def test_request_tamper_is_detected(self):
        self.run_job(self.backend())
        request = read_json(self.root/'output/request.json'); request['hypothesis_key']='changed'
        write_json(self.root/'output/request.json', request)
        with self.assertRaises(ContractError): verify_interpretation(self.root/'output')

    def test_recorded_backend_binds_request_and_has_no_retry(self):
        path=self.root/'replay.json'
        write_json(path, dict(schema_version=1, request_sha256=fingerprint(self.prepared.request),
            response=self.response(), usage=encode(Usage(0, 0, 0))))
        backend=RecordedInterpreter(path); self.run_job(backend)
        with self.assertRaises(ContractError): backend.generate(self.prepared.request, 1)

    def reseal(self, mutate_events=None):
        out=self.root/'output';receipt=read_json(out/'receipt.json')
        receipt['outputs']={name:pin(out/name) for name in receipt['outputs']}
        write_json(out/'receipt.json',receipt)
        events=[encode(e) for e in read_chain(out/'journal.jsonl')]
        if mutate_events:mutate_events(events)
        events[-1]['details']['receipt']=pin(out/'receipt.json')
        previous=None
        for e in events:
            e.pop('sha256');e['previous_sha256']=previous;e['sha256']=fingerprint(e);previous=e['sha256']
        (out/'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))

    def test_resealed_zero_call_budget_cannot_validate_a_dispatch(self):
        self.run_job(self.backend());p=self.root/'output/configuration.json';config=read_json(p)
        config['budget']['max_calls']=0;write_json(p,config);self.reseal()
        with self.assertRaises(ContractError):verify_interpretation(self.root/'output')

    def test_resealed_science_validation_claim_rejected(self):
        self.run_job(self.backend());p=self.root/'output/report.json';report=read_json(p)
        report['scientific_validation']='passed';write_json(p,report);self.reseal()
        with self.assertRaises(ContractError):verify_interpretation(self.root/'output')

    def test_resealed_retry_policy_rejected(self):
        self.run_job(self.backend());p=self.root/'output/configuration.json';config=read_json(p)
        config['automatic_retries']=True;write_json(p,config);self.reseal()
        with self.assertRaises(ContractError):verify_interpretation(self.root/'output')

    def test_future_program_fails_before_dispatch(self):
        case=read_json(self.inputs/'case.json')
        case['program']['availability']['annotation_public_at']='2024-01-01'
        write_json(self.inputs/'case.json',case);backend=self.backend()
        with self.assertRaises(ContractError):self.run_job(backend)
        self.assertEqual(backend.calls,0)

    def test_nested_utf8_quote_uses_decoded_byte_coordinates(self):
        request=encode(self.prepared.request)
        request['evidence'][0]['scientific_record']['source_metrics']={'text':'β effect'}
        response=self.response(request);claim=response['claims'][0]
        claim['text']='β';claim['quotes'][0].update(pointer='/source_metrics/text',text='β',span={'start':0,'end':2})
        validate_response(request,response)
        claim['quotes'][0]['span']['end']=1
        with self.assertRaises(ContractError):validate_response(request,response)

    def test_two_concurrent_outputs_dispatch_once(self):
        backend=self.backend()
        def execute():
            try:self.run_job(backend);return 'completed'
            except FileExistsError:return 'reserved'
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(lambda _:execute(),range(2)))
        self.assertCountEqual(outcomes,['completed','reserved']);self.assertEqual(backend.calls,1)

    def test_write_failure_after_call_preserves_accounting(self):
        import tools.science.bounded_interpretation as module
        original=module.write_json
        def fail(path,value):
            if path.name=='response.json':raise OSError('fixture disk failure')
            return original(path,value)
        backend=self.backend()
        with patch.object(module,'write_json',side_effect=fail):
            with self.assertRaises(OSError):self.run_job(backend)
        events=read_chain(self.root/'output/journal.jsonl')
        self.assertEqual(backend.calls,1);self.assertEqual(events[-1]['event'],'build_failed')
        self.assertEqual(sum(e['event']=='interpretation_accounted' for e in events),1)

    def test_forged_quote_budget_abstention_rejected(self):
        self.run_job(self.backend(usage=Usage(1,1,1)))
        p=self.root/'output/response.json';response=read_json(p)
        response['abstention_reason']=None;write_json(p,response);self.reseal()
        with self.assertRaises(ContractError):verify_interpretation(self.root/'output')

    def test_peer_negative_measured_usage_rejected_even_when_resealed(self):
        self.run_job(self.backend());p=self.root/'output/report.json';report=read_json(p)
        report['measured_usage']['input_tokens']=-3;write_json(p,report)
        def mutate(events):
            next(e for e in events if e['event']=='interpretation_accounted')['details']['usage']['input_tokens']=-3
        self.reseal(mutate)
        with self.assertRaises(ContractError):verify_interpretation(self.root/'output')

    def test_peer_code_manifest_cannot_substitute_unrelated_file(self):
        self.run_job(self.backend());p=self.root/'output/configuration.json';config=read_json(p)
        config['code']=pin(self.inputs/'case.json');config['dependency_code']=[];write_json(p,config)
        def mutate(events):
            next(e for e in events if e['event']=='interpretation_quote')['details']['configuration_sha256']=fingerprint(config)
        self.reseal(mutate)
        with self.assertRaises(ContractError):verify_interpretation(self.root/'output')


if __name__=='__main__': unittest.main()
