"""Independent reader controls built exclusively from invented native fixtures."""
import base64
import copy
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from experiments.litqa_comparison.tests import test_replay as replay_fixtures
from experiments.labbench.tests import test_model as model_fixtures
from . import cells, contracts, native_evaluation as e, model, transport


def tokenize(fixture, owner, payload, *, output, journal, deadline):
    """Invented zero-duration quote, coherent with the actual enclosing timer."""
    fixture.f.payload = payload; quote = fixture.f.quote(); quote['elapsed_seconds'] = 0.0
    quote['endpoint'] = f'http://{owner.spec.host}:{owner.spec.port}'
    output = Path(output); output.mkdir()
    request = quote['tokenizer_request']; body = base64.b64decode(quote['body_base64'])
    (output/'request.json').write_bytes(canonical(request)); (output/'body.bin').write_bytes(body)
    (output/'result.json').write_bytes(canonical(quote))
    journal.append('mcq_tokenize_attempt', payload_sha256=e.fingerprint(payload),
                   request_sha256=e.fingerprint(request), owner_pid=12345)
    journal.append('mcq_tokenize_terminal', proof_sha256=e.fingerprint(quote), token_count=50,
                   error_class=None, elapsed_seconds=0.0)
    return quote


class NativeEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.f = replay_fixtures.ReplayTests('runTest')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.q = dict(self.f.q, choices=['(A) Increased', '(B) Insufficient information to answer the question', '(C) Reduced'])
        text = 'An invented paragraph reports increased transport.'
        self.sources = [dict(source_id='fixture:p1', text=text, sha256=e.n.digest(text.encode()))]
        self.prior = contracts.candidate(self.q, dict(answer_index=0, evidence_ids=['fixture:p1']),
            producer_status='produced', original_admission_status='accepted', native_call_sha256='a'*64,
            generated_at_utc=None, offered_ids=['fixture:p1'])
        self.answer = dict(support='supported', evidence_ids=['fixture:p1'], criticism='The raw passage reports an increase.',
                           queries=[['transport'], ['protein uptake']])
        self.critic = contracts.critique(self.q, self.prior, self.sources, self.answer,
            native_status='completed', native_call_sha256='b'*64)
        self.code = e.proof(Path(model.__file__))

    def cell(self, task='critic', raw=None, sources=None):
        root = self.f.root/task
        sources = self.sources if sources is None and task != 'removal' else ([] if sources is None else sources)
        if task == 'critic':
            request, payload = model.make_critic_request(self.q, self.prior, sources, self.f.f.model)
            decoded = self.answer
        else:
            member = model.make_repair_pair(self.q, self.prior, self.critic, sources, self.f.f.model)[task]
            request, payload = member['request'], member['payload']
            decoded = dict(answer_index=0, evidence_ids=['fixture:p1'] if sources else [])
        self.f.f.payload = payload
        body = self.f.f.native_body(content=canonical(decoded).decode() if raw is None else raw)
        with patch.object(transport.native, '_check_owner', return_value=12345), \
             patch.object(transport.native, '_watchdog', return_value=model_fixtures.Timer()), \
             patch.object(transport.mcq, 'tokenize_once', side_effect=lambda *a, **k: tokenize(self.f, *a, **k)), \
             self.f.f.transport(model_fixtures.Response(body)):
            common = dict(owner=self.f.f.owner, output=root, deadline=time.monotonic()+15,
                          alias=self.f.alias, execution_id='invented-'+task)
            if task == 'critic':
                cells.call_critic(self.q, self.prior, sources, self.f.f.model, **common)
            else:
                cells.call_pair_member(self.q, self.prior, self.critic, sources, self.f.f.model, member, task,
                    control_sha256=e.fingerprint(dict(query=self.q, candidate=self.prior, critique=self.critic)), **common)
        return root, e.n.load(root/'INPUT.json')

    def read(self, root, inputs):
        return e.reconstruct_cell(root, inputs, execution_id='invented-'+inputs['task'],
            model_provenance=self.f.f.model, alias=self.f.alias, owner_pid=12345,
            endpoint='http://127.0.0.1:'+str(self.f.f.spec.port), code_proof=self.code)

    def events(self, root, mutate):
        events = e.n.journal(root/'journal.jsonl'); mutate(events); previous = None
        for row in events:
            row.pop('sha256'); row['previous_sha256'] = previous
            row['sha256'] = e.fingerprint(row); previous = row['sha256']
        (root/'journal.jsonl').write_bytes(b''.join(canonical(r)+b'\n' for r in events))

    def test_all_three_request_kinds_original_native_bytes_and_usage(self):
        for task in ('critic', 'repair', 'removal'):
            root, inputs = self.cell(task)
            got = self.read(root, inputs)
            self.assertEqual(got['summary']['status'], 'completed')
            self.assertEqual(got['summary']['usage'], dict(input_tokens=50, output_tokens=12, cost_usd=0))
            self.assertFalse(got['source_lineage_checked'])
            self.assertEqual(got['sources'], [] if task == 'removal' else self.sources)

    def test_malformed_complete_output_remains_codec_failure(self):
        root, inputs = self.cell(raw='malformed')
        got = self.read(root, inputs)
        self.assertEqual(got['summary']['status'], 'codec_failure')
        self.assertIsNone(got['summary']['decoded'])
        self.assertEqual(got['summary']['usage']['output_tokens'], 12)

    def test_capacity_reconstructed_without_transport(self):
        self.q['question'] = 'α'*5000
        self.prior = contracts.candidate(self.q, None, producer_status='input_unavailable',
            original_admission_status='not_run', native_call_sha256=None, generated_at_utc=None, offered_ids=[])
        root = self.f.root/'capacity'
        cells.call_critic(self.q, self.prior, [], self.f.f.model, owner=None, output=root,
            deadline=time.monotonic()+10, alias=self.f.alias, execution_id='invented-critic')
        got = self.read(root, e.n.load(root/'INPUT.json'))
        self.assertEqual(got['summary']['status'], 'capacity')
        self.assertIsNone(got['native_call_sha256'])
        self.assertFalse((root/'native').exists())

    def test_paired_prompts_and_grammar_match_producer_without_importing_it_at_replay(self):
        for task in ('critic', 'repair', 'removal'):
            sources = [] if task == 'removal' else self.sources
            got = e.prepare_member(task, self.q, self.prior, None if task == 'critic' else self.critic,
                                   sources, self.f.f.model, self.code)
            if task == 'critic':
                req, payload = model.make_critic_request(self.q, self.prior, sources, self.f.f.model)
                expected = dict(status='ready', request=req, payload=payload)
            else:
                expected = model.make_repair_pair(self.q, self.prior, self.critic, self.sources, self.f.f.model)[task]
            self.assertEqual(canonical(got), canonical(expected))

    def test_explicit_candidate_and_indexed_choices_are_rebuilt_including_null(self):
        for index in (2, None):
            prior = contracts.candidate(self.q, None if index is None else dict(answer_index=index, evidence_ids=[]),
                producer_status='input_unavailable' if index is None else 'produced',
                original_admission_status='not_run' if index is None else 'rejected',
                native_call_sha256=None if index is None else 'a'*64, generated_at_utc=None, offered_ids=[])
            got = e.prepare_member('critic', self.q, prior, None, self.sources, self.f.f.model, self.code)
            request, payload = model.make_critic_request(self.q, prior, self.sources, self.f.f.model)
            self.assertEqual(canonical(got), canonical(dict(status='ready', request=request, payload=payload)))
            data = json.loads(got['payload']['prompt'].split('<|im_start|>user\n')[1].split('<|im_end|>')[0])
            self.assertEqual(data['candidate_answer'], None if index is None else dict(answer_index=index, text=self.q['choices'][index]))
            self.assertEqual(data['indexed_options'], [dict(answer_index=i, text=t) for i, t in enumerate(self.q['choices'])])

    def test_original_projection_is_data_only_and_unknown_layout_rejected(self):
        path = self.f.root/'pinned-producer.py'
        # Never import this file: it deliberately raises if executed.
        source = "raise RuntimeError('archived source must never execute')\ndef critic_payload(query, prior, sources):\n    return codecs._payload('Invented original prompt.', dict(task=query, candidate_context=prior, passages=[]), None)\n"
        path.write_text(source, encoding='utf8')
        got = e.prepare_member('critic', self.q, self.prior, None, self.sources, self.f.f.model, e.proof(path))
        data = json.loads(got['payload']['prompt'].split('<|im_start|>user\n')[1].split('<|im_end|>')[0])
        self.assertEqual(set(data), {'task', 'candidate_context', 'passages'})
        self.assertEqual(data['passages'], [dict(source_id=s['source_id'], text=s['text']) for s in self.sources])
        path.write_text(source.replace('task=query,', 'unexpected=query,'), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'projection layout'):
            e.prepare_member('critic', self.q, self.prior, None, self.sources, self.f.f.model, e.proof(path))

    def test_critic_strict_safety_and_null_prior_constraints(self):
        for change in ('duplicate_key', 'term_identifier', 'term_repeat', 'citation', 'assertion', 'long_unicode', 'null_prior'):
            row = copy.deepcopy(self.answer); prior = encode(self.prior)
            if change == 'term_identifier': row['queries'][0] = ['PMID123']
            if change == 'term_repeat': row['queries'][1] = ['TRANSPORT']
            if change == 'citation': row['evidence_ids'] = ['other']
            if change == 'assertion': row['evidence_ids'] = []
            if change == 'long_unicode': row['criticism'] = 'é'*81
            if change == 'null_prior': prior['prediction'] = None
            raw = canonical(row)
            if change == 'duplicate_key': raw = b'{"support":"supported","support":"insufficient"}'
            with self.subTest(change=change), self.assertRaises(ValueError): e.critic_decode(raw, self.q, prior, self.sources)

    def test_summary_usage_and_resealed_journal_reservation_rejected(self):
        root, inputs = self.cell()
        path = root/'SUMMARY.json'; original = path.read_bytes(); summary = e.n.load(path)
        summary['usage']['input_tokens'] = 49; path.write_bytes(canonical(summary))
        with self.assertRaisesRegex(ValueError, 'summary'): self.read(root, inputs)
        path.write_bytes(original)
        self.events(root, lambda rows: rows[2]['details'].update(generation_entered=True))
        with self.assertRaisesRegex(ValueError, 'reservation event'): self.read(root, inputs)

    def test_actor_projection_and_other_pair_member_cannot_be_substituted(self):
        root, inputs = self.cell('removal')
        bad = copy.deepcopy(inputs); bad['sources'] = self.sources
        with self.assertRaisesRegex(ValueError, 'projected actor'): self.read(root, bad)
        bad = copy.deepcopy(inputs); bad['prepared_member']['request']['candidate_context']['prediction']['answer_index'] = 2
        (root/'INPUT.json').write_bytes(canonical(bad))
        with self.assertRaisesRegex(ValueError, 'paired member'): self.read(root, bad)

    def test_extra_native_file_and_failure_marker_rejected(self):
        root, inputs = self.cell()
        for name in ('FAILURE.json', 'native/extra.json'):
            path = root/name; path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'inventory'): self.read(root, inputs)
            path.unlink()

    def test_native_settings_owner_or_token_quote_substitution_rejected(self):
        root, inputs = self.cell()
        path = root/'native/native-response.bin'; original = path.read_bytes()
        for kind in ('owner', 'grammar', 'stop'):
            wrapper = e.n.decode(original)
            if kind == 'owner': wrapper['owner_pid'] = 999
            else:
                response = e.n.decode(base64.b64decode(wrapper['body_base64']))
                if kind == 'grammar': response['generation_settings']['grammar'] = 'root ::= "other"'
                else: response['stopped_limit'] = True
                raw = canonical(response)
                wrapper.update(body_base64=base64.b64encode(raw).decode(), body_sha256=e.n.digest(raw))
            path.write_bytes(canonical(wrapper))
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.read(root, inputs)

    def test_native_generation_must_fit_fixed_call_seconds(self):
        root, inputs = self.cell()
        for relative, field in (('native/native-response.bin', 'elapsed_seconds'),
                                ('native/tokenization/result.json', 'elapsed_seconds'),
                                ('native/result.json', 'wall_seconds')):
            path = root/relative; original = path.read_bytes()
            for duration in (120.0, 121.0):
                value = e.n.decode(original); value[field] = duration; path.write_bytes(canonical(value))
                with self.subTest(path=relative, duration=duration), self.assertRaisesRegex(ValueError, 'call time|duration'):
                    self.read(root, inputs)
            path.write_bytes(original)
        path = root/'native/native-response.bin'; value = e.n.load(path)
        value['elapsed_seconds'] = 1.0; path.write_bytes(canonical(value))
        with self.assertRaisesRegex(ValueError, 'component durations'): self.read(root, inputs)


if __name__ == '__main__':
    unittest.main()
