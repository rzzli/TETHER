"""Chat conformance against a fictional numeric-loopback server and recordings."""

from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
from threading import Thread
import time
import unittest
from unittest.mock import patch

from tether_engine.contracts import Case, Category, Citation, GroundedObservation, Observation
from tether_engine.generated_chat import ChatCapabilities, ChatLimits, LocalGeneratedChat, archive_chat, replay_chat
from tether_engine.generated_claims import make_generated_request
from tether_engine.serde import ContractError, canonical, decode


DEMO = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, result=None, *, models=('fictional-model',)):
        super().__init__(('127.0.0.1', 0), Handler)
        self.models = models
        self.result = result or self.completed
        self.requests = []

    @staticmethod
    def completed(request):
        prompt = json.loads(request['messages'][1]['content'])
        source = prompt['sources'][0]
        quote = dict(observation_id=source['observation_id'], source_sha256=source['text_sha256'],
                     start_byte=0, end_byte=len(source['text'].encode('utf-8')), quote=source['text'])
        claim = dict(claim_id='fictional-claim', text='The fixture records a fictional result.',
                     hypothesis_sha256=prompt['hypothesis_sha256'], uncertainty='high', quotes=[quote])
        proposal = dict(schema_version=1, request_sha256=prompt['request_sha256'], claims=[claim])
        envelope = dict(choices=[dict(finish_reason='stop', message=dict(role='assistant', content=canonical(proposal).decode()))],
                        usage=dict(prompt_tokens=100, completion_tokens=20, total_tokens=120))
        return 200, 'application/json', canonical(envelope), None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send(self, code, media, payload, length):
        self.send_response(code)
        self.send_header('Content-Type', media)
        self.send_header('Content-Length', str(len(payload) if length is None else length))
        if code == 302:
            self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/elsewhere')
        self.end_headers()
        try:
            self.wfile.write(payload)
        except ConnectionError:
            pass

    def do_GET(self):
        self.server.requests.append((self.command, self.path, None))
        self._send(200, 'application/json', canonical(dict(data=[dict(id=x) for x in self.server.models])), None)

    def do_POST(self):
        raw = self.rfile.read(int(self.headers['Content-Length']))
        request = json.loads(raw)
        self.server.requests.append((self.command, self.path, request))
        self._send(*self.server.result(request))


class GeneratedChatTests(unittest.TestCase):
    def setUp(self):
        case = decode(Case, json.loads((DEMO / 'case.json').read_bytes()))
        observation = decode(Observation, json.loads((DEMO / 'evidence.json').read_bytes())['observations'][0])
        grounded = GroundedObservation(observation, Citation('fixture', 'demo', '1', 'a'*64, 'https://example.invalid'))
        self.request = make_generated_request(case, Category.GENETICS, (grounded,))

    def server(self, result=None, **options):
        server = Server(result, **options)
        thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.02}, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        return server

    def test_local_completion_and_recorded_replay_match(self):
        server = self.server()
        backend = LocalGeneratedChat(server.server_port, 'fictional-model')
        capabilities = backend.negotiate()
        result = backend.run(self.request, capabilities)
        self.assertEqual(result.disposition, 'proposal_assessed')
        self.assertEqual(result.accounted_usage.input_tokens, 100)
        self.assertEqual(result.usage_basis, 'adapter_reported')
        self.assertEqual(result.assessment.accepted, ())
        self.assertEqual(len(result.assessment.proposals), 1)
        self.assertEqual(result.assessment.proposals[0].quote_status, 'valid')
        self.assertEqual(result.assessment.proposals[0].disposition, 'pending_review')
        self.assertEqual([r[:2] for r in server.requests], [('GET', '/v1/models'), ('POST', '/v1/chat/completions')])
        sent = server.requests[-1][2]
        self.assertEqual(sent['response_format'], {'type': 'json_object'})
        self.assertFalse(sent['stream'])
        self.assertNotIn('https://example.invalid', sent['messages'][1]['content'])
        with tempfile.TemporaryDirectory() as temp, patch('tether_engine.generated_chat._http') as transport:
            path = Path(temp) / 'chat.json'
            archive_chat(path, result)
            self.assertEqual(replay_chat(path, self.request, capabilities), result)
            transport.assert_not_called()
            changed = replace(self.request, case=replace(self.request.case, case_id='other-case'))
            with self.assertRaisesRegex(ContractError, 'request_mismatch'):
                replay_chat(path, changed, capabilities)
            record = json.loads(path.read_bytes())
            record['usage']['input_tokens'] = 1
            path.write_bytes(canonical(record))
            with self.assertRaisesRegex(ContractError, 'accounting_mismatch'):
                replay_chat(path, self.request, capabilities)
            record['response_sha256'] = 'f'*64
            path.write_bytes(canonical(record))
            with self.assertRaisesRegex(ContractError, 'response_mismatch'):
                replay_chat(path, self.request, capabilities)

    def test_capability_probe_requires_unique_model_before_dispatch(self):
        server = self.server(models=('other',))
        backend = LocalGeneratedChat(server.server_port, 'fictional-model')
        with self.assertRaisesRegex(ContractError, 'model_not_unique'):
            backend.negotiate()
        with self.assertRaisesRegex(ContractError, 'capabilities_mismatch'):
            backend.run(self.request, ChatCapabilities(server.server_port, 'fictional-model', 'f'*64))
        self.assertEqual([r[0] for r in server.requests], ['GET'])

    def test_streaming_http_errors_partial_responses_and_limits_are_distinct(self):
        for code, media, raw, length, disposition in (
            (200, 'text/event-stream', b'data: {}\n\n', None, 'streaming_response'),
            (503, 'application/json', b'{}', None, 'http_error'),
            (302, 'application/json', b'{}', None, 'http_error'),
            (200, 'application/json', b'{', 30, 'partial_response'),
            (200, 'application/json', b'x'*2048, None, 'response_byte_limit'),
            (200, 'text/plain', b'{}', None, 'unsupported_response_media'),
            (200, 'application/json', b'not JSON', None, 'malformed_chat_response'),
        ):
            with self.subTest(disposition=disposition, code=code):
                server = self.server(lambda _request: (code, media, raw, length))
                limits = ChatLimits(max_response_bytes=1024)
                backend = LocalGeneratedChat(server.server_port, 'fictional-model', limits)
                result = backend.run(self.request, backend.negotiate())
                self.assertEqual(result.disposition, disposition)
                self.assertEqual(result.usage_basis, 'configured_reservation_not_measured')
                self.assertEqual(result.accounted_usage, limits.reservation)
                self.assertLessEqual(len(result.response.raw), limits.max_response_bytes)
                self.assertEqual(len(server.requests), 2)

    def test_preserves_valid_usage_on_incomplete_and_malformed_completions(self):
        for form, disposition in (('length', 'incomplete_chat_completion'), ('tool', 'malformed_chat_response'),
                                  ('mismatch', 'invalid_generated_response'), ('overrun', 'usage_reservation_exceeded'),
                                  ('missing_usage', 'usage_unavailable')):
            with self.subTest(form=form):
                def payload(request):
                    code, media, raw, length = Server.completed(request)
                    decoded = json.loads(raw)
                    choice = decoded['choices'][0]
                    if form == 'length':
                        choice['finish_reason'] = 'length'
                    elif form == 'tool':
                        choice['message']['tool_calls'] = [dict(id='fictional')]
                    elif form == 'mismatch':
                        body = json.loads(choice['message']['content'])
                        body['request_sha256'] = 'b'*64
                        choice['message']['content'] = canonical(body).decode()
                    elif form == 'overrun':
                        decoded['usage'].update(completion_tokens=1025, total_tokens=1125)
                    else:
                        decoded.pop('usage')
                    return code, media, canonical(decoded), length
                server = self.server(payload)
                backend = LocalGeneratedChat(server.server_port, 'fictional-model')
                result = backend.run(self.request, backend.negotiate())
                self.assertEqual(result.disposition, disposition)
                expected_basis = 'configured_reservation_not_measured' if form == 'missing_usage' else 'adapter_reported'
                self.assertEqual(result.usage_basis, expected_basis)
                self.assertEqual(len(server.requests), 2)

    def test_deadline_and_request_budget_stop_without_retry(self):
        def delayed(request):
            time.sleep(0.4)
            return Server.completed(request)
        server = self.server(delayed)
        backend = LocalGeneratedChat(server.server_port, 'fictional-model', ChatLimits(timeout_seconds=0.15))
        capabilities = backend.negotiate()
        result = backend.run(self.request, capabilities)
        self.assertEqual(result.disposition, 'timeout')
        self.assertEqual(len(server.requests), 2)
        too_small = LocalGeneratedChat(server.server_port, 'fictional-model', ChatLimits(max_request_bytes=1))
        with self.assertRaisesRegex(ContractError, 'request_byte_limit'):
            too_small.run(self.request, too_small.negotiate())
        self.assertEqual([request[0] for request in server.requests], ['GET', 'POST', 'GET'])
