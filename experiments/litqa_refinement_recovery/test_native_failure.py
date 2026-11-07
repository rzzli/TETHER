"""Invented, source-bound token-limit captures; no actual HTTP or model calls."""
import base64
from copy import deepcopy
import http.client
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode, fingerprint, freeze
from tether_engine.study import native
from experiments.labbench.tests import test_model as fixtures
from experiments.litqa_refinement import cells, contracts, model, transport
from experiments.litqa_refinement_recovery import native_failure as failure


class NativeLimitFailureTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ModelTests('runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root.resolve() / 'captured-cell'
        self.execution_id = '11111111-1111-4111-8111-111111111111-repair-0184'
        prior = contracts.candidate(self.f.query, dict(answer_index=0, evidence_ids=['fixture:p0001']),
            producer_status='produced', original_admission_status='accepted', native_call_sha256='a'*64,
            generated_at_utc='2026-11-06T00:00:00Z', offered_ids=['fixture:p0001'])
        critic = contracts.critique(self.f.query, prior, self.f.sources,
            dict(support='supported', evidence_ids=['fixture:p0001'], criticism='An invented source supports it.',
                 queries=[['orb'], ['color']]), native_status='completed', native_call_sha256='b'*64)
        pair = model.make_repair_pair(self.f.query, prior, critic, self.f.sources, self.f.model)
        self.request, self.payload = map(encode, (pair['repair']['request'], pair['repair']['payload']))
        self.f.request, self.f.payload = self.request, self.payload
        self.inputs = encode(dict(task='repair', query=self.f.query, candidate_context=prior,
            critique_context=critic, sources=self.f.sources, model_provenance=self.f.model,
            prepared_member=pair['repair'], control_sha256=pair['control_sha256']))
        raw = json.loads(self.f.native_body(content='INCOMPLETE OUTPUT MUST NEVER BE TASK-DECODED',
            tokens_predicted=256, stop_type='limit'))
        for key in ('stopped_limit', 'stopped_eos', 'stopped_word'):
            raw.pop(key)
        self.body = raw

        def tokenize(owner, payload, *, output, journal, deadline):
            output.mkdir()
            quote = self.f.quote()
            quote['elapsed_seconds'] = 0.0
            encoded = canonical(quote['tokenizer_request'])
            (output/'request.json').write_bytes(encoded)
            (output/'body.bin').write_bytes(base64.b64decode(quote['body_base64']))
            (output/'result.json').write_bytes(canonical(quote))
            journal.append('mcq_tokenize_attempt', payload_sha256=fingerprint(payload),
                request_sha256=failure.records.digest(encoded), owner_pid=12345)
            journal.append('mcq_tokenize_terminal', proof_sha256=fingerprint(quote), token_count=quote['token_count'],
                error_class=None, elapsed_seconds=quote['elapsed_seconds'])
            return freeze(quote)

        with patch.object(transport.mcq, 'tokenize_once', side_effect=tokenize), \
             patch.object(native, '_check_owner', return_value=12345), \
             patch.object(native, '_watchdog', return_value=fixtures.Timer()), \
             self.f.transport(fixtures.Response(canonical(raw))), \
             patch.object(model, 'decode', side_effect=AssertionError('Partial answer must not be decoded')):
            with self.assertRaisesRegex(ContractError, 'Unqualified native completion cause'):
                cells.call_pair_member(self.f.query, prior, critic, self.f.sources, self.f.model, pair['repair'],
                    'repair', control_sha256=pair['control_sha256'], owner=self.f.owner,
                    output=self.root, deadline=time.monotonic()+20, alias='fictional-mcq', execution_id=self.execution_id)
        self.assertEqual(len(self.f.calls), 1)
        self.original = {name: (self.root/name).read_bytes() for name in failure.FILES}
        self.files = self.proofs()

    def proofs(self):
        return {name: dict(path=str(self.root/name), bytes=(self.root/name).stat().st_size,
                sha256=failure.records.digest((self.root/name).read_bytes())) for name in failure.FILES}

    def reset(self):
        for name, raw in self.original.items():
            (self.root/name).write_bytes(raw)
        self.files = self.proofs()

    def write(self, name, value):
        (self.root/name).write_bytes(canonical(value))
        self.files = self.proofs()

    def native_change(self, **changes):
        wrapper = json.loads((self.root/'native/native-response.bin').read_bytes())
        body = json.loads(base64.b64decode(wrapper['body_base64']))
        body.update(changes)
        raw = canonical(body)
        wrapper.update(body_base64=base64.b64encode(raw).decode(), body_sha256=failure.records.digest(raw))
        self.write('native/native-response.bin', wrapper)

    def journal_change(self, operation):
        events = [json.loads(line) for line in (self.root/'journal.jsonl').read_bytes().splitlines()]
        operation(events)
        previous = None
        for number, event in enumerate(events):
            event.update(sequence=number, previous_sha256=previous)
            event['sha256'] = fingerprint({k: v for k, v in event.items() if k != 'sha256'})
            previous = event['sha256']
        (self.root/'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))
        self.files = self.proofs()

    def verify(self, **changes):
        args = dict(files=self.files, expected_inputs=self.inputs, expected_request=self.request,
            expected_payload=self.payload, execution_id=self.execution_id, owner_pid=12345,
            alias='fictional-mcq', server_spec=self.f.spec, bindings=self.f.bindings)
        args.update(changes)
        with patch.object(http.client, 'HTTPConnection', side_effect=AssertionError('Verifier cannot dispatch')), \
             patch.object(model, 'decode', side_effect=AssertionError('Verifier cannot decode partial answer')):
            return failure.verify_cell_limit_failure(self.root, **args)

    def test_original_limit_without_legacy_boolean_is_failure_never_prediction(self):
        result = self.verify()
        self.assertEqual(result['kind'], failure.KIND)
        self.assertEqual(result['status'], 'authenticated_limit_failure')
        self.assertEqual((result['producer_status'], result['check_status']), ('error', 'not_run'))
        self.assertIsNone(result['prediction'])
        self.assertIsNone(result['qualified_usage'])
        self.assertFalse(result['original_usage_verified'])
        self.assertTrue(result['raw_usage_checked'])
        self.assertEqual(result['raw_reported_usage']['output_tokens'], 256)
        self.assertEqual(result['raw_reported_usage']['input_tokens'], 50)
        self.assertEqual(result['conservative_reservation']['output_tokens'], 256)
        self.assertFalse(result['automatic_retry'])
        with self.assertRaises(TypeError):
            result['raw_reported_usage']['output_tokens'] = 0
        with self.assertRaises(ContractError):
            native._complete(self.body)
        self.assertEqual({name: (self.root/name).read_bytes() for name in failure.FILES}, self.original)
        self.assertEqual(len(self.f.calls), 1)

    def test_optional_consistent_legacy_limit_flags_require_original_message(self):
        self.native_change(stopped_limit=True, stopped_eos=False, stopped_word=False)
        with self.assertRaises(ValueError):
            self.verify()
        self.journal_change(lambda e: e[-1]['details'].update(message='Native output hit token limit'))
        self.assertIsNone(self.verify()['prediction'])

    def test_complete_looking_partial_answer_is_still_never_promoted(self):
        self.native_change(content='{"answer_index":0,"evidence_ids":["fixture:p0001"]}')
        result=self.verify()
        self.assertIsNone(result['prediction'])
        self.assertEqual(result['check_status'],'not_run')
        self.assertNotIn('content',result)

    def test_unknown_inconsistent_or_nonpositive_stop_cannot_be_recovered(self):
        variants = ({'stop_type':'eos'}, {'stop_type':'unknown'}, {'stop_type':None}, {'stop':False},
            {'stop':1}, {'stopped_limit':False}, {'stopped_limit':1}, {'stopped_eos':True},
            {'stopped_word':True}, {'stopping_word':'<|im_end|>'}, {'truncated':True})
        for change in variants:
            with self.subTest(change=change):
                self.reset(); self.native_change(**change)
                with self.assertRaises(ValueError): self.verify()

    def test_wrong_prompt_model_settings_and_usage_are_not_limit_dispositions(self):
        variants = ({'prompt':'substituted'}, {'model':'other-model'}, {'tokens_evaluated':51},
            {'tokens_evaluated':True}, {'tokens_predicted':255}, {'tokens_predicted':257},
            {'tokens_predicted':True}, {'generation_settings':dict(self.payload, n_predict=512)},
            {'generation_settings':dict(self.payload, seed=True)}, {'content':{'answer_index':0}})
        for change in variants:
            with self.subTest(change=change):
                self.reset(); self.native_change(**change)
                with self.assertRaises(ValueError): self.verify()

    def test_wrapper_hash_owner_transport_and_duration_substitutions_rejected(self):
        variants = ({'body_sha256':'0'*64}, {'owner_pid':999}, {'owner_pid':True},
            {'request_sha256':'0'*64}, {'payload_sha256':'0'*64}, {'complete':False}, {'http_status':500},
            {'elapsed_seconds':120}, {'error_class':'TimeoutError'})
        for change in variants:
            with self.subTest(change=change):
                self.reset()
                value=json.loads((self.root/'native/native-response.bin').read_bytes()); value.update(change)
                self.write('native/native-response.bin', value)
                with self.assertRaises(ValueError): self.verify()

    def test_token_quote_original_request_and_captured_body_are_bound(self):
        for name, key, replacement in (
            ('native/tokenization/result.json','token_count',51),
            ('native/tokenization/result.json','owner_pid',999),
            ('native/tokenization/result.json','payload_sha256','0'*64),
            ('native/tokenization/request.json','parse_special',False)):
            with self.subTest(name=name,key=key):
                self.reset(); value=json.loads((self.root/name).read_bytes()); value[key]=replacement; self.write(name,value)
                with self.assertRaises(ValueError): self.verify()
        self.reset(); (self.root/'native/tokenization/body.bin').write_bytes(b'{"tokens":[9]}');self.files=self.proofs()
        with self.assertRaises(ValueError):self.verify()

    def test_failed_call_and_journal_accounting_remain_exact(self):
        for change in ({'usage_verified':True}, {'status':'completed'}, {'generation_entered':False},
                       {'wall_seconds':120}, {'wall_seconds':0}, {'measured_usage':None},
                       {'conservative_reserved_output_tokens':512}):
            with self.subTest(change=change):
                self.reset();value=json.loads((self.root/'native/failure.json').read_bytes());value.update(change)
                self.write('native/failure.json',value)
                with self.assertRaises(ValueError):self.verify()
        self.reset();self.journal_change(lambda e:e[5]['details']['reservation'].update(output_tokens=512))
        with self.assertRaises(ValueError):self.verify()

    def test_absent_duplicate_or_contradictory_attempt_and_tail_rejected(self):
        operations=(lambda e:e.pop(5),lambda e:e.insert(5,deepcopy(e[5])),
            lambda e:e[-1].update(event='build_interrupted'),
            lambda e:e[6]['details'].update(generation_entered=False))
        for operation in operations:
            self.reset();self.journal_change(operation)
            with self.assertRaises(ValueError):self.verify()
        self.reset();(self.root/'journal.jsonl').write_bytes((self.root/'journal.jsonl').read_bytes().rstrip(b'\n'))
        self.files=self.proofs()
        with self.assertRaises(ValueError):self.verify()

    def test_missing_response_extra_product_or_unanchored_members_fail_closed(self):
        bad=deepcopy(self.files);bad.pop('native/native-response.bin')
        with self.assertRaises(ValueError):self.verify(files=bad)
        (self.root/'SUMMARY.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):self.verify()
        (self.root/'SUMMARY.json').unlink()
        (self.root/'native/native-response.bin').unlink()
        with self.assertRaises(ValueError):self.verify()

    def test_source_input_member_and_model_bindings_cannot_be_substituted(self):
        changed=deepcopy(self.inputs);changed['sources'][0]['text']='different source'
        with self.assertRaises(ValueError):self.verify(expected_inputs=changed)
        changed=deepcopy(self.request);changed['query']['question']='different question'
        with self.assertRaises(ValueError):self.verify(expected_request=changed)
        with self.assertRaises(ValueError):self.verify(owner_pid=999)
        with self.assertRaises(ValueError):self.verify(alias='other-model')
        with self.assertRaises(ValueError):self.verify(execution_id='different-execution')
        spec=encode(self.f.spec);spec['executable']['sha256']='0'*64
        with self.assertRaises(ValueError):self.verify(server_spec=spec)

    def test_resealed_input_context_and_prepared_member_must_join_request(self):
        for mutate in (lambda value:value['sources'][0].update(text='different captured source',sha256='c'*64),
                       lambda value:value['prepared_member'].update(status='capacity'),
                       lambda value:value.update(control_sha256='c'*64),
                       lambda value:value.update(extra_context='unqualified')):
            with self.subTest(mutate=mutate):
                self.reset();changed=deepcopy(self.inputs);mutate(changed);self.write('INPUT.json',changed)
                self.journal_change(lambda e:e[1]['details'].update(input_sha256=fingerprint(changed)))
                with self.assertRaises(ValueError):self.verify(expected_inputs=changed)

    def test_changed_file_during_verification_and_aliased_proof_rejected(self):
        original=failure.records.read
        counts={}
        def changed(path,limit=32*1024**2):
            data=original(path,limit=limit);key=str(path);counts[key]=counts.get(key,0)+1
            if Path(path).name=='failure.json' and counts[key]==2:return data+b' '
            return data
        with patch.object(failure.records,'read',side_effect=changed),self.assertRaises(ValueError):self.verify()
        bad=deepcopy(self.files);bad['INPUT.json']['path']=str(self.root/'native'/'..'/'INPUT.json')
        with self.assertRaises(ValueError):self.verify(files=bad)

    def test_invalid_deadline_never_reads_or_dispatches(self):
        for end in (True,float('nan'),float('inf'),time.monotonic()-1,time.monotonic()+1000):
            with self.subTest(deadline=end),patch.object(failure.records,'read',side_effect=AssertionError('No input reads')):
                with self.assertRaises(ValueError):self.verify(deadline=end)

    def test_unbounded_or_mistyped_file_proofs_rejected(self):
        for value in (True,-1,failure.MAX_FILE_BYTES+1):
            with self.subTest(bytes=value):
                bad=deepcopy(self.files);bad['INPUT.json']['bytes']=value
                with self.assertRaises(ValueError):self.verify(files=bad)


if __name__ == '__main__':
    unittest.main()
