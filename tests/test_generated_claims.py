"""Fictional proposal and span controls. No transport, outcomes, or external data."""

import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tether_engine.agents import ExtractiveBackend, make_request
from tether_engine.contracts import Case, Category, Citation, GroundedObservation, Observation
from tether_engine.generated_claims import (
    MAX_RESPONSE_BYTES, ClaimProposal, GeneratedResponse, QuoteSpan, Support, SupportReview,
    Uncertainty, archive_assessment, assess_generated_response, assess_span_selection,
    make_generated_request, make_span_catalog,
)
from tether_engine.serde import ContractError, canonical, decode, encode, fingerprint


DEMO = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class GeneratedClaimsTests(unittest.TestCase):
    def setUp(self):
        self.case = decode(Case, json.loads((DEMO / 'case.json').read_bytes()))
        observation = decode(Observation, json.loads((DEMO / 'evidence.json').read_bytes())['observations'][0])
        observation = replace(observation, statement='Café 🧬 and cafe\u0301 were recorded; the outcome is unknown.')
        self.grounded = GroundedObservation(observation, Citation('fixture', 'demo', '1', 'a'*64, 'https://example.invalid'))
        self.request = make_generated_request(self.case, Category.GENETICS, (self.grounded,))
        source = self.request.sources[0]
        span = QuoteSpan(source.observation_id, source.text_sha256, 0, len('Café 🧬'.encode()), 'Café 🧬')
        self.claim = ClaimProposal('claim-1', 'The fictional record mentions Café 🧬.', self.case.hypothesis.key,
                                   Uncertainty.HIGH, (span,))

    def response(self, *proposals):
        return canonical(GeneratedResponse(1, fingerprint(self.request), proposals))

    def review(self, proposal, verdict=Support.SUPPORTED):
        return SupportReview(fingerprint(self.request), fingerprint(proposal), 'synthetic fixture', verdict)

    def selection(self, *claims):
        catalog = make_span_catalog(self.request)
        return dict(schema_version=2, request_sha256=catalog.request_sha256,
                    offer_sha256=fingerprint(catalog), claims=claims)

    def selected(self, **changes):
        return dict(claim_id=self.claim.claim_id, text=self.claim.text,
                    hypothesis_sha256=self.claim.hypothesis_sha256, uncertainty='high',
                    span_ids=['s001']) | changes

    def test_span_selection_resolves_exact_multibyte_bytes_without_credit(self):
        raw = canonical(self.selection(self.selected()))
        result = assess_span_selection(self.request, raw)
        self.assertEqual(result.raw_response, raw)
        self.assertEqual(result.schema_version, 2)
        item = result.proposals[0]
        source = self.request.sources[0]
        self.assertEqual(item.proposal.quotes[0], QuoteSpan(source.observation_id, source.text_sha256,
                        0, len(source.text.encode('utf-8')), source.text))
        self.assertEqual((item.quote_status, item.disposition, result.accepted), ('valid', 'pending_review', ()))
        reviewed = assess_span_selection(self.request, raw, reviews=(self.review(item.proposal),))
        self.assertEqual(reviewed.accepted, (item.proposal,))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'assessment.json'
            archive_assessment(path, self.request, result)
            record = json.loads(path.read_bytes())
            self.assertEqual(record['span_catalog'], encode(make_span_catalog(self.request)))
            self.assertEqual(base64.b64decode(record['raw_response_base64']), raw)

    def test_bad_span_selection_is_retained_alongside_valid_sibling(self):
        for changes, status, reason in (
            ({'span_ids': ['s256']}, 'invalid', 'unknown_span_id'),
            ({'span_ids': ['s001', 's001']}, 'invalid', 'duplicate_quote_span'),
            ({'span_ids': []}, 'invalid', 'invalid_quote_count'),
            ({'span_ids': ['s001'] * 9}, 'invalid', 'invalid_quote_count'),
            ({'hypothesis_sha256': 'f' * 64}, 'not_checked', 'hypothesis_scope_mismatch'),
            ({'start_byte': 0}, 'not_checked', 'start_byte'),
            ({'support': 'supported'}, 'not_checked', 'support'),
        ):
            with self.subTest(changes=changes):
                raw = canonical(self.selection(self.selected(**changes), self.selected(claim_id='sibling')))
                result = assess_span_selection(self.request, raw)
                self.assertEqual(result.raw_response, raw)
                self.assertEqual([item.index for item in result.proposals], [0, 1])
                self.assertEqual(result.proposals[0].quote_status, status)
                self.assertIn(reason, result.proposals[0].reason)
                self.assertEqual(result.proposals[1].quote_status, 'valid')
                self.assertFalse(result.accepted)

    def test_span_selection_keeps_offers_bound_to_admitted_request_and_wire(self):
        raw = canonical(self.selection(self.selected()))
        legacy = self.response(self.claim)
        self.assertEqual(assess_generated_response(self.request, raw).envelope_error, 'invalid_response_fields')
        self.assertEqual(assess_span_selection(self.request, legacy).envelope_error, 'invalid_response_fields')
        stale = self.selection(self.selected()) | {'offer_sha256': '0' * 64}
        self.assertEqual(assess_span_selection(self.request, canonical(stale)).envelope_error, 'response_offer_mismatch')
        other_request = replace(self.request, case=replace(self.case, case_id='other-fixture'))
        self.assertEqual(assess_span_selection(other_request, raw).envelope_error, 'response_request_mismatch')

    def test_blank_oversize_and_empty_sources_have_no_offers(self):
        observations = tuple(replace(self.grounded, observation=replace(self.grounded.observation,
                             observation_id=f'fictional-{i}', statement=statement))
                             for i, statement in enumerate(('  ', 'é' * 4097)))
        self.request = make_generated_request(self.case, Category.GENETICS, observations)
        self.assertEqual(make_span_catalog(self.request).offers, ())
        result = assess_span_selection(self.request, canonical(self.selection()))
        self.assertIsNone(result.envelope_error)
        self.assertEqual(result.proposals, ())
        result = assess_span_selection(self.request, canonical(self.selection(self.selected())))
        self.assertEqual(result.proposals[0].reason, 'unknown_span_id')

    def test_orders_multiple_spans_and_does_not_reassign_skipped_source_ids(self):
        observations = tuple(replace(self.grounded, observation=replace(self.grounded.observation,
                             observation_id=f'fictional-{i}', statement=statement))
                             for i, statement in enumerate(('First quote.', '   ', 'Café 🧬.')))
        self.request = make_generated_request(self.case, Category.GENETICS, observations)
        catalog = make_span_catalog(self.request)
        self.assertEqual([(offer.span_id, offer.source_index) for offer in catalog.offers],
                         [('s001', 0), ('s003', 2)])
        result = assess_span_selection(self.request, canonical(self.selection(
            self.selected(span_ids=['s003', 's001']))))
        self.assertEqual([quote.quote for quote in result.proposals[0].proposal.quotes],
                         ['Café 🧬.', 'First quote.'])
        self.assertEqual(result.proposals[0].quote_status, 'valid')

    def test_exact_unicode_quote_requires_separate_support_record(self):
        raw = self.response(self.claim)
        result = assess_generated_response(self.request, raw)
        self.assertEqual((result.proposals[0].quote_status, result.proposals[0].support), ('valid', Support.NOT_ASSESSED))
        self.assertEqual(result.proposals[0].disposition, 'pending_review')
        self.assertEqual(result.accepted, ())
        supported = assess_generated_response(self.request, raw, reviews=(self.review(self.claim),))
        self.assertEqual(supported.accepted, (self.claim,))

    def test_utf8_boundaries_and_normalization_must_be_literal(self):
        quote = self.claim.quotes[0]
        for change in ({'end_byte': quote.end_byte - 1}, {'end_byte': len(quote.quote)},
                       {'quote': 'Cafe\u0301 🧬'}, {'start_byte': 1}, {'quote': 'Invented'}):
            with self.subTest(change=change):
                claim = replace(self.claim, quotes=(replace(quote, **change),))
                result = assess_generated_response(self.request, self.response(claim), reviews=(self.review(claim),))
                self.assertEqual(result.proposals[0].reason, 'quote_text_mismatch')
                self.assertEqual(result.accepted, ())

    def test_missing_source_hash_and_span_checks(self):
        span = self.claim.quotes[0]
        cases = ((replace(span, observation_id='outside'), 'unknown_evidence_id'),
                 (replace(span, source_sha256='b'*64), 'quote_source_hash_mismatch'),
                 (replace(span, start_byte=-1), 'quote_offset_out_of_range'))
        for changed, expected in cases:
            with self.subTest(expected=expected):
                proposal = replace(self.claim, quotes=(changed,))
                result = assess_generated_response(self.request, self.response(proposal))
                self.assertEqual(result.proposals[0].reason, expected)
                self.assertEqual(result.proposals[0].quote_status, 'invalid')
        duplicate = replace(self.claim, quotes=(span, span))
        self.assertEqual(assess_generated_response(self.request, self.response(duplicate)).proposals[0].reason,
                         'duplicate_quote_span')

    def test_action_modality_and_tissue_scope_cannot_be_substituted(self):
        for change in ({'intended_action': 'activate'}, {'modality': 'antibody'}, {'tissue': 'different site'}):
            with self.subTest(change=change):
                alternative = replace(self.case.hypothesis, **change)
                changed = replace(self.claim, hypothesis_sha256=alternative.key)
                result = assess_generated_response(self.request, self.response(changed), reviews=(self.review(changed),))
                self.assertEqual(result.proposals[0].support, Support.INCOMPATIBLE_SCOPE)
                self.assertEqual(result.proposals[0].quote_status, 'not_checked')
                self.assertEqual(result.accepted, ())

    def test_mixed_sentences_do_not_inherit_support_from_a_quoted_fragment(self):
        mixed = replace(self.claim, claim_id='claim-2', text=self.claim.text + ' This proves a clinical outcome.')
        result = assess_generated_response(self.request, self.response(self.claim, mixed),
                                          reviews=(self.review(self.claim), self.review(mixed, Support.MIXED)))
        self.assertEqual(result.accepted, (self.claim,))
        self.assertEqual((result.proposals[1].support, result.proposals[1].quote_status), (Support.MIXED, 'valid'))
        for verdict in (Support.INSUFFICIENT, Support.CONTRADICTED, Support.INCOMPATIBLE_SCOPE):
            result = assess_generated_response(self.request, self.response(mixed), reviews=(self.review(mixed, verdict),))
            self.assertEqual(result.proposals[0].support, verdict)
            self.assertEqual(result.accepted, ())

    def test_review_cannot_be_transferred_to_different_proposal_or_request(self):
        edited = replace(self.claim, text='The fixture proves something else.')
        result = assess_generated_response(self.request, self.response(edited), reviews=(self.review(self.claim),))
        self.assertEqual(result.proposals[0].disposition, 'pending_review')
        other_request = replace(self.request, case=replace(self.case, case_id='other-fixture'))
        result = assess_generated_response(other_request, self.response(self.claim))
        self.assertEqual(result.envelope_error, 'response_request_mismatch')
        with self.assertRaisesRegex(ContractError, 'invalid_support_review'):
            assess_generated_response(other_request, self.response(self.claim), reviews=(self.review(self.claim),))

    def test_malformed_proposals_and_duplicate_ids_never_receive_credit(self):
        malformed = encode(replace(self.claim, claim_id='claim-2')) | {'support': 'supported'}
        raw = canonical({'schema_version': 1, 'request_sha256': fingerprint(self.request),
                         'claims': [self.claim, self.claim, malformed, 3]})
        result = assess_generated_response(self.request, raw, reviews=(self.review(self.claim),))
        self.assertEqual([row.index for row in result.proposals], [0, 1, 2, 3])
        self.assertEqual(result.proposals[0].reason, 'duplicate_claim_id')
        self.assertIn('unknown fields', result.proposals[2].reason)
        self.assertEqual(result.accepted, ())
        self.assertEqual(result.raw_response, raw)

    def test_archive_keeps_raw_bytes_and_distinct_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'assessment.json'
            invalid = replace(self.claim, claim_id='claim-2', quotes=(replace(self.claim.quotes[0], quote='Invented'),))
            raw = self.response(self.claim, invalid) + b'\n'
            result = assess_generated_response(self.request, raw, reviews=(self.review(self.claim),))
            archive_assessment(record, self.request, result)
            stored = json.loads(record.read_bytes())
            self.assertEqual(base64.b64decode(stored['raw_response_base64']), raw)
            self.assertEqual(stored['raw_response_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(stored['accepted_claim_ids'], ['claim-1'])
            self.assertEqual(stored['proposals'][1]['reason'], 'quote_text_mismatch')
            self.assertEqual(stored['scientific_validation'], 'not_established')
            self.assertEqual(fingerprint(stored['request']), stored['request_sha256'])
            mismatch = replace(self.request, case=replace(self.case, case_id='mismatched-case'))
            with self.assertRaisesRegex(ContractError, 'assessment_request_mismatch'):
                archive_assessment(Path(directory) / 'wrong.json', mismatch, result)
            with self.assertRaises(FileExistsError):
                archive_assessment(record, self.request, result)

    def test_invalid_envelopes_retained_and_oversize_response_declined(self):
        for raw in (b'not JSON', b'{"a":1,"a":1}', b'\xff',
                    canonical(GeneratedResponse(True, fingerprint(self.request), ())),
                    canonical(GeneratedResponse(2, fingerprint(self.request), ()))):
            with self.subTest(raw=raw):
                result = assess_generated_response(self.request, raw)
                self.assertIsNotNone(result.envelope_error)
                self.assertEqual(result.raw_response, raw)
                self.assertEqual(result.accepted, ())
        with self.assertRaisesRegex(ContractError, 'oversize'):
            assess_generated_response(self.request, b' '* (MAX_RESPONSE_BYTES+1))

    def test_source_bindings_and_selection_contract_stay_separate(self):
        with self.assertRaisesRegex(ContractError, 'source_outside_specialist_scope'):
            make_generated_request(self.case, Category.MODALITY, (self.grounded,))
        changed_source = replace(self.request.sources[0], text='another source body')
        with self.assertRaisesRegex(ContractError, 'source_text_hash_mismatch'):
            assess_generated_response(replace(self.request, sources=(changed_source,)), self.response(self.claim))
        selection_request = make_request(self.case, Category.GENETICS, (self.grounded,))
        selected = ExtractiveBackend().select(selection_request)
        self.assertEqual(selected.observation_ids, (self.request.sources[0].observation_id,))
        result = assess_generated_response(self.request, canonical(selected))
        self.assertEqual(result.envelope_error, 'invalid_response_fields')
