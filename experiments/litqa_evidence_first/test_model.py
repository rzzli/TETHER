"""Model-free regressions; no prospective qualification answers are imported."""
import json
import unittest
from uuid import UUID

from tether_engine.serde import canonical, encode, fingerprint
from experiments.litqa_refinement import contracts as old
from experiments.litqa_refinement import test_contracts as f
from . import contracts as c, model, projection

MODEL = dict(weights_sha256={'fictional.gguf': 'a' * 64}, runtime_sha256='b' * 64)


class MethodTests(unittest.TestCase):
    def pair(self, sources=None):
        return model.make_pair(f.query(), f.prior(), f.context(),
                               f.sources() if sources is None else sources, MODEL)

    def test_evidence_order_survives_canonical_serializer(self):
        pair = self.pair()
        text = pair['repair']['payload']['prompt']
        data = json.loads(text.split('<|im_start|>user\n')[1].split('<|im_end|>')[0])
        self.assertEqual([next(iter(row)) for row in data], list(model.SECTIONS))
        self.assertEqual(data[1]['indexed_options'],
                         [dict(answer_index=i, text=v) for i, v in enumerate(f.query()['choices'])])
        self.assertEqual(data[2]['raw_passages'],
                         [dict(source_id=s['source_id'], text=s['text']) for s in f.sources()])

    def test_whitelist_keeps_relevant_controls_without_wrapper_metadata(self):
        pair = self.pair(); request = pair['repair']['request']
        data = model.model_sections(f.query(), f.prior(), f.context(), f.sources())
        self.assertEqual(set(data[3]['untrusted_prior_candidate']), set(model.CANDIDATE_FIELDS))
        self.assertEqual(set(data[4]['untrusted_critique']['decoded']), set(model.DECODED_FIELDS))
        self.assertNotIn('queries', data[4]['untrusted_critique']['decoded'])
        self.assertIn('queries', request['critique_context']['decoded'])
        self.assertIn('native_call_sha256', request['candidate_context'])
        for task in c.PHASES:
            model.validate_binding(pair[task]['request'], pair[task]['payload'])

    def test_pair_frozen_before_dispatch_and_deeply_immutable(self):
        pair = self.pair()
        self.assertEqual(pair['method_sha256'], fingerprint(model.method_descriptor()))
        for key in ('query', 'candidate_context', 'critique_context', 'model_provenance', 'configuration'):
            self.assertEqual(pair['repair']['request'][key], pair['removal']['request'][key])
        with self.assertRaises(TypeError):
            pair['repair']['request']['candidate_context']['prediction']['answer_index'] = 2
        with self.assertRaises(TypeError):
            pair['repair']['request']['sources'][0]['text'] = 'edited'

    def test_mutated_method_source_and_kind_are_rejected(self):
        member = self.pair()['repair']
        for key, value in [('method_sha256', '0' * 64), ('kind', 'wrong'), ('task', 'removal')]:
            request = encode(member['request']); request[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                model.validate_binding(request, member['payload'])
        request = encode(member['request']); request['sources'][0]['text'] += ' edited'
        with self.assertRaises(ValueError): model.validate_binding(request, member['payload'])

    def test_removal_has_no_raw_sources_or_factual_member(self):
        pair = self.pair()
        value = projection.from_verified_context(f.query(), f.prior(), f.context(), f.sources(), MODEL,
                                                 cutoff='fixed', context={'cutoff': 'fixed'})
        actor = projection.actor_member(value, 'removal')
        self.assertEqual(actor['sources'], ())
        self.assertEqual(actor['prepared_member'], pair['removal'])
        self.assertNotIn('context', actor)
        self.assertNotIn('members', actor)
        with self.assertRaises(ValueError):
            projection.actor_input('removal', f.query(), f.prior(), f.context(), f.sources(),
                                   MODEL, pair['removal'], pair['control_sha256'])

    def test_unsupported_prior_source_cannot_be_cited(self):
        pair = self.pair([])
        for task in c.PHASES:
            with self.assertRaises(ValueError):
                model.decode(pair[task]['request'], canonical(dict(answer_index=0,
                             evidence_ids=[f.sources()[0]['source_id']])))
            self.assertEqual(model.decode(pair[task]['request'], canonical(dict(answer_index=0,
                             evidence_ids=[])))['answer_index'], 0)

    def test_no_option_remapping_and_strict_two_field_decode(self):
        member = self.pair()['repair']
        for index in range(3):
            value = dict(answer_index=index, evidence_ids=[])
            self.assertEqual(encode(model.decode(member['request'], canonical(value))), value)
        with self.assertRaises(ValueError):
            model.decode(member['request'], canonical(dict(answer_index=0, evidence_ids=[], rationale='extra')))

    def test_capacity_never_truncates_and_removal_can_still_fit(self):
        sources = [dict(source_id=f'p{i}', text='é' * 500,
                        sha256=model.codecs.digest(('é' * 500).encode())) for i in range(8)]
        pair = self.pair(sources)
        self.assertEqual(pair['repair'], dict(status='capacity', request=None, payload=None))
        self.assertEqual(pair['removal']['status'], 'ready')

    def test_missing_controls_remain_null(self):
        query = f.query()
        prior = old.candidate(query, None, producer_status='input_unavailable', original_admission_status='not_run',
                              native_call_sha256=None, generated_at_utc=None, offered_ids=[])
        critic = old.critique(query, prior, [], None, native_status='capacity', native_call_sha256=None)
        member = model.make_pair(query, prior, critic, [], MODEL)['removal']
        data = model.model_sections(query, prior, critic, [])
        self.assertIsNone(data[3]['untrusted_prior_candidate']['prediction'])
        self.assertIsNone(data[4]['untrusted_critique']['decoded'])
        model.validate_binding(member['request'], member['payload'])

    def test_full_scope_and_separate_explicit_budgets(self):
        for purpose, count, calls in [('production', 199, 398), ('fictional_qualification', 6, 12)]:
            ids = [str(UUID(int=i + 1)) for i in range(count)]
            self.assertEqual(c.schedule(ids, purpose), tuple(ids))
            with self.assertRaises(ValueError): c.schedule(ids[:-1], purpose)
            limits = c.budgets(purpose)
            self.assertEqual(limits['generation_calls'], calls)
            self.assertEqual(limits['reserved_input_tokens'], calls * 16128)
            self.assertFalse(limits['automatic_retry'])
        self.assertNotEqual(c.identity('a' * 64, 'b' * 64), c.identity('a' * 64, 'c' * 64))


if __name__ == '__main__': unittest.main()
