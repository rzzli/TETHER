"""Check attribution development vectors without a service or a model."""

from dataclasses import replace
from importlib.resources import files
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from tether_engine.contracts import Case, Category, Citation, GroundedObservation, Observation
from tether_engine.generated_chat import HTTPResult, LocalGeneratedChat
from tether_engine.generated_claims import make_generated_request
from tether_engine.serde import canonical, decode, parse_json


FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'generated-attribution-development'
DEMO = files('tether_engine').joinpath('demo/v2')
RECORD = re.compile(r'Record (R[0-9]+) reports (marker|size) as ([a-z]+)\.')
INERT_MARKER = 'SAMPLE_INERT_MARKER'


def content_reference(facts, quotes):
    """Interpret just the deliberately finite fictional fixture language."""
    recorded = []
    for quote in quotes:
        sentence = quote.quote.splitlines()[0]
        recorded.append(RECORD.fullmatch(sentence).groups())
    verdicts = set()
    for record, attribute, value in facts:
        values = {result for subject, key, result in recorded if (subject, key) == (record, attribute)}
        if value in values:
            verdicts.add('supported')
        if values - {value}:
            verdicts.add('contradicted')
        if not values:
            verdicts.add('insufficient')
    if len(verdicts) > 1:
        return 'mixed'
    return next(iter(verdicts), 'insufficient')


class GeneratedAttributionFixtureTests(unittest.TestCase):
    def test_scripted_v2_exchanges_keep_literal_alignment_separate_from_support(self):
        actor = parse_json((FIXTURES / 'actor.json').read_bytes())
        evaluator = parse_json((FIXTURES / 'reference.json').read_bytes())
        self.assertEqual(set(actor), {'schema_version', 'purpose', 'sources', 'scenarios'})
        self.assertEqual(set(evaluator), {'schema_version', 'purpose', 'evaluator_canary', 'references'})
        self.assertEqual(actor['schema_version'], 1)
        self.assertEqual(evaluator['schema_version'], 1)
        self.assertEqual(evaluator['purpose'], 'evaluation_only')
        self.assertEqual(actor['purpose'], 'synthetic_actor_and_recorded_response_inputs')
        reference = {item['id']: item for item in evaluator['references']}
        self.assertEqual(len(actor['scenarios']), 16)
        self.assertEqual(len(reference), len(evaluator['references']))
        self.assertEqual({item['id'] for item in actor['scenarios']}, set(reference))
        base = decode(Case, parse_json(DEMO.joinpath('case.json').read_bytes()))
        observation = decode(Observation, parse_json(DEMO.joinpath('evidence.json').read_bytes())['observations'][0])
        citation = Citation('fictional-fixture', 'synthetic', '1', 'a' * 64, 'https://example.invalid')

        for index, scenario in enumerate(actor['scenarios'], 1):
            with self.subTest(scenario=scenario['id']):
                expected = reference[scenario['id']]
                case = replace(base, case_id=f'fixture-attribution-{index:02}')
                texts = [actor['sources'][key] for key in scenario['sources']]
                sources = tuple(GroundedObservation(replace(observation, observation_id=f'fixture-{i}',
                                statement=text), citation) for i, text in enumerate(texts))
                request = make_generated_request(case, Category.GENETICS, sources)
                calls, original_responses = [], []

                def exchange(port, method, path, payload, *_limits):
                    self.assertEqual(port, 53804)
                    calls.append((method, path))
                    if method == 'GET':
                        self.assertIsNone(payload)
                        return HTTPResult(200, 'application/json',
                                          canonical({'data': [{'id': 'fixture-response'}]}))
                    self.assertNotIn(evaluator['evaluator_canary'].encode(), payload)
                    self.assertNotIn(scenario['id'].encode(), payload)
                    sent = parse_json(payload)
                    content = parse_json(sent['messages'][1]['content'].encode())
                    self.assertEqual(set(content), {'case', 'category', 'request_sha256', 'hypothesis_sha256',
                                                    'offer_sha256', 'spans'})
                    self.assertEqual([item['text'] for item in content['spans']], texts)
                    propositions = []
                    if scenario['span_ids']:
                        text = ' '.join(f'Record {row} reports {key} as {value}.'
                                        for row, key, value in scenario['facts'])
                        propositions.append(dict(claim_id='fixture-claim', text=text, uncertainty='high',
                            hypothesis_sha256=content['hypothesis_sha256'], span_ids=scenario['span_ids'])
                            | scenario.get('response_overrides', {}))
                    original = canonical(dict(schema_version=2, request_sha256=content['request_sha256'],
                                               offer_sha256=content['offer_sha256'], claims=propositions))
                    original_responses.append(original)
                    response = dict(choices=[dict(finish_reason='stop', message=dict(role='assistant',
                                    content=original.decode()))], usage=dict(prompt_tokens=100, completion_tokens=32))
                    return HTTPResult(200, 'application/json', canonical(response))

                backend = LocalGeneratedChat(53804, 'fixture-response', select_spans=True)
                with patch('tether_engine.generated_chat._http', side_effect=exchange):
                    attempt = backend.run(request, backend.negotiate())
                self.assertEqual(calls, [('GET', '/v1/models'), ('POST', '/v1/chat/completions')])
                self.assertEqual(attempt.disposition, 'proposal_assessed')
                assessment = attempt.assessment
                self.assertEqual(assessment.raw_response, original_responses[0])
                self.assertEqual(assessment.accepted, ())
                if expected['quote_status'] is None:
                    self.assertEqual(assessment.proposals, ())
                    continue
                item, = assessment.proposals
                self.assertEqual(item.quote_status, expected['quote_status'])
                if item.quote_status == 'valid':
                    self.assertEqual(item.support, 'not_assessed')
                    self.assertEqual(item.disposition, 'pending_review')
                    self.assertEqual(content_reference(scenario['facts'], item.proposal.quotes),
                                     expected['content_status'])
                    self.assertEqual(INERT_MARKER in item.proposal.text, expected.get('inert_marker_echoed', False))
                else:
                    self.assertEqual(item.disposition, 'rejected')
                    self.assertIn(expected['reason'], item.reason)
                    self.assertEqual(item.support, expected['content_status'])
