"""Absolute-deadline checks against finite local fixture HTTP, never a model."""
from contextlib import contextmanager
import socket
import threading
import time
import unittest
from unittest.mock import Mock, patch

from tether_engine.serde import canonical
from tether_engine.study.source_fact_transport import TypedReportingClient


@contextmanager
def fixture_server(slow, *, redirect=False):
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    listener.settimeout(2)
    stop, calls, faults = threading.Event(), [], []
    port = listener.getsockname()[1]
    body = canonical(dict(content='{}', tokens_evaluated=2, tokens_predicted=1,
        truncated=False, prompt='prompt', model='fixture',
        generation_settings=dict(seed=0, temperature=0.0, n_predict=2048,
                                 stop=['<|im_end|>'], stream=False)))
    header = b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\nConnection: close\r\n\r\n'
    if redirect:
        header = b'HTTP/1.1 302 Found\r\nLocation: http://example.invalid/\r\nContent-Length: 0\r\n\r\n'
        body = b''
    def serve():
        try:
            with listener.accept()[0] as peer:
                peer.settimeout(2)
                request = b''
                while b'\r\n\r\n' not in request:
                    request += peer.recv(65536)
                head, rest = request.split(b'\r\n\r\n', 1)
                length = next(int(line.split(b':', 1)[1]) for line in head.split(b'\r\n')
                              if line.lower().startswith(b'content-length:'))
                while len(rest) < length:
                    rest += peer.recv(65536)
                calls.append(request)
                for phase, payload in (('header', header), ('body', body)):
                    if slow == phase:
                        for value in payload:
                            if stop.wait(0.005): return
                            peer.sendall(bytes([value]))
                    else:
                        peer.sendall(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Expected when the client closes its owned fixture connection.
        except BaseException as error:
            faults.append(error)
    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{port}', calls
    finally:
        stop.set()
        worker.join(3)
        listener.close()
        if worker.is_alive(): raise AssertionError('Fixture worker did not stop')
        if faults: raise faults[0]


class SourceFactDeadlineTests(unittest.TestCase):
    def test_normal_fixture_succeeds_and_is_not_retried(self):
        with fixture_server(None) as (endpoint, calls), patch.dict('os.environ', {
            'HTTP_PROXY': 'http://127.0.0.1:1', 'http_proxy': 'http://127.0.0.1:1',
            'NO_PROXY': '', 'no_proxy': ''}):
            result = TypedReportingClient(endpoint, expected_pid=1,
                ownership_check=lambda *args: True).execute('prompt', timeout_seconds=2)
        self.assertEqual(result.status, 'returned')
        self.assertEqual(len(calls), 1)

    def test_trickled_headers_and_body_cannot_reset_deadline(self):
        for phase in ('header', 'body'):
            with self.subTest(phase=phase):
                with fixture_server(phase) as (endpoint, calls):
                    events = []
                    start = time.monotonic()
                    result = TypedReportingClient(endpoint, expected_pid=1,
                        ownership_check=lambda *args: True, retain=events.append).execute(
                            'prompt', timeout_seconds=0.15)
                    elapsed = time.monotonic() - start
                self.assertEqual(result.status, 'timeout')
                self.assertTrue(result.dispatched)
                self.assertLess(elapsed, 1.0)
                self.assertEqual(len(calls), 1)
                self.assertEqual([event['event'] for event in events], ['attempt', 'terminal'])

    def test_default_transport_rejects_redirect_without_following(self):
        with fixture_server(None, redirect=True) as (endpoint, calls), \
                patch('urllib.request.build_opener', side_effect=AssertionError('No URL opener')):
            result = TypedReportingClient(endpoint, expected_pid=1,
                ownership_check=lambda *args: True).execute('prompt', timeout_seconds=2)
        self.assertEqual(result.status, 'failed')
        self.assertIn('Unexpected completion HTTP status', result.error)
        self.assertEqual(len(calls), 1)

    def test_expiry_in_ownership_prevents_dispatch(self):
        now = [0.0]
        def owner(*args):
            now[0] = 2.0
            return True
        opener, events = Mock(), []
        with patch('time.monotonic', side_effect=lambda: now[0]):
            with self.assertRaisesRegex(TimeoutError, 'deadline'):
                TypedReportingClient('http://127.0.0.1:55591', expected_pid=1,
                    ownership_check=owner, opener=opener, retain=events.append).execute(
                        'prompt', timeout_seconds=1)
        opener.open.assert_not_called()
        self.assertFalse(events[-1]['result'].dispatched)


if __name__ == '__main__':
    unittest.main()
