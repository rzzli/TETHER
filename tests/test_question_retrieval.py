"""Model-free checks for bounded retrieval over a question and pre-admitted text."""

from dataclasses import replace
from importlib.resources import files
import unittest

from tether_engine.contracts import Case, Category, Citation, GroundedObservation, Observation
from tether_engine.generated_claims import make_generated_request, make_span_catalog
from tether_engine.retrieval import (
    QUESTION_THREE_TERM_OVERLAP, RetrievalPolicy, bounded_question_request, question_terms,
)
from tether_engine.serde import ContractError, canonical, decode, fingerprint, parse_json


class QuestionRetrievalTests(unittest.TestCase):
    def setUp(self):
        demo = files('tether_engine').joinpath('demo/v2')
        self.case = decode(Case, parse_json(demo.joinpath('case.json').read_bytes()))
        self.observation = decode(Observation,
            parse_json(demo.joinpath('evidence.json').read_bytes())['observations'][0])

    def request(self, rows, question='What color is QX-0.9?'):
        citation = Citation('fictional-fixture', 'synthetic', '1', 'a' * 64, 'https://example.invalid')
        observations = tuple(GroundedObservation(
            replace(self.observation, observation_id=identity, statement=body), citation
        ) for identity, body in rows)
        return make_generated_request(self.case, Category.GENETICS, observations, question=question)

    def test_numeric_punctuation_and_unicode_tokens_preserve_distinctions(self):
        self.assertEqual(question_terms('Ω\u2011QX, VQ₄, µ-QX, Cafe\u0301-QX and p.Val600Glu'),
                         ('ω-qx', 'vq4', 'μ-qx', 'café-qx', 'p.val600glu'))
        self.assertEqual(question_terms('QX-03 QX-3 QX-0.9 QX-9 1.07 1.70 HLA-DQB1*06:02'),
                         ('qx-03', 'qx-3', 'qx-0.9', 'qx-9', '1.07', '1.70', 'hla-dqb1*06:02'))

    def test_bm25_selects_the_matching_identifier_and_preserves_literal_offer(self):
        full = self.request((('a', 'The color of QX-9 is pearl.'), ('z', 'The color of QX-0.9 is ébène.')))
        prepared, audit = bounded_question_request(full, RetrievalPolicy(max_records=1))
        self.assertEqual(prepared.sources, (full.sources[1],))
        self.assertEqual(prepared.question, full.question)
        self.assertEqual(audit['selected_ids'], ('z',))
        self.assertEqual(audit['excluded'], [{'observation_id': 'a', 'reason': 'record_count_cap'}])
        self.assertEqual(audit['input_request_sha256'], fingerprint(full))
        self.assertEqual(audit['request_sha256'], fingerprint(prepared))
        self.assertEqual(audit['request_bytes'], len(canonical(prepared)))
        self.assertEqual(make_span_catalog(prepared).offers[0].end_byte, len(full.sources[1].text.encode()))

    def test_both_strategies_apply_same_byte_rule_and_audit_every_source(self):
        full = self.request((('long', 'QX-0.9 color ' * 150), ('small', 'QX-0.9 color.'),
                             ('oversized', 'color ' * 1500), ('blank', '  '), ('no-overlap', 'other.')))
        budget = len(canonical(replace(full, sources=(full.sources[1],))))
        for name in ('question_bm25_v1', QUESTION_THREE_TERM_OVERLAP):
            with self.subTest(name=name):
                selected, proof = bounded_question_request(full, RetrievalPolicy(3, budget), strategy=name)
                self.assertEqual(selected.sources, (full.sources[1],))
                self.assertEqual(proof['request_bytes'], budget)
                self.assertEqual(proof['query_count'], 1)
                self.assertEqual(proof['offerable_records'], 3)
                self.assertEqual({row['observation_id']: row['reason'] for row in proof['excluded']},
                                 {'long': 'whole_record_exceeds_byte_cap', 'oversized': 'not_offerable',
                                  'blank': 'not_offerable', 'no-overlap': 'no_query_overlap'})

    def test_deterministic_ties_and_empty_result(self):
        full = self.request((('b', 'QX-0.9 color.'), ('a', 'QX-0.9 color.'), ('c', 'unrelated.')))
        forward, proof = bounded_question_request(full, RetrievalPolicy())
        backward, _ = bounded_question_request(replace(full, sources=full.sources[::-1]), RetrievalPolicy())
        self.assertEqual(forward, backward)
        self.assertEqual(proof['selected_ids'], ('a', 'b'))
        self.assertEqual(proof['request_bytes'], len(canonical(forward)))
        for request in (replace(full, question='What?'), replace(full, sources=())):
            result, audit = bounded_question_request(request, RetrievalPolicy())
            self.assertEqual(result.sources, ())
            self.assertEqual(audit['request_bytes'], len(canonical(result)))

    def test_rejects_missing_question_forged_sources_and_invalid_strategy(self):
        full = self.request((('x', 'A fictional observation.'),))
        with self.assertRaisesRegex(ContractError, 'requires an explicit question'):
            bounded_question_request(replace(full, schema_version=1, question=None), RetrievalPolicy())
        with self.assertRaisesRegex(ContractError, 'source_text_hash_mismatch'):
            altered = replace(full, sources=(replace(full.sources[0], text='changed'),))
            bounded_question_request(altered, RetrievalPolicy())
        with self.assertRaisesRegex(ContractError, 'Unknown question retrieval strategy'):
            bounded_question_request(full, RetrievalPolicy(), strategy='forged')
