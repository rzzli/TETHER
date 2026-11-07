"""Invented HTTP lifecycle controls; no model, source query or benchmark keys.

Both tokenizer and generation execute their real owned-transport code against
in-memory HTTP objects. Only process ownership and the socket watchdog are
invented. Failure injection targets persistence and the actual transport read.
"""
import base64
from contextlib import contextmanager
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import canonical, encode, parse_json
from experiments.labbench.tests import test_model as http_fixtures
from . import cells, model, native_evaluation, transport
from . import test_native_evaluation as native_fixtures


class PartialFailureResponse(http_fixtures.Response):
    def __init__(self, error):
        super().__init__(b'partial-native-body')
        self.error = error
        self.first = True

    def read1(self, limit):
        if self.first:
            self.first = False
            return super().read1(min(limit, 7))
        raise self.error


class CellLifecycleTests(unittest.TestCase):
    def setUp(self):
        native_fixtures.NativeTests.setUp(self)
        self.pair = model.make_pair(self.q, self.prior, self.critic, self.sources, self.f.f.model)
        self.member = self.pair['repair']
        self.f.f.request, self.f.f.payload = self.member['request'], self.member['payload']

    def responses(self, *, generation=None, tokenization=None):
        if tokenization is None:
            tokenization = http_fixtures.Response(canonical(dict(tokens=list(range(50)))))
        if generation is None:
            generation = http_fixtures.Response(self.f.f.native_body(
                content=canonical(dict(answer_index=0, evidence_ids=['fixture:p1'])).decode()))
        return [tokenization, generation]

    @contextmanager
    def wire(self, responses, *, connection_factory=None):
        pending = list(responses)

        def connect(*args, **kwargs):
            self.assertTrue(pending, 'Unexpected additional transport attempt')
            response = pending.pop(0)
            return (connection_factory or http_fixtures.Connection)(response, self.f.f.calls)

        with patch.object(transport.native, '_check_owner', return_value=12345), \
             patch.object(transport.native, '_watchdog', return_value=http_fixtures.Timer()), \
             patch.object(transport.native.http.client, 'HTTPConnection', side_effect=connect):
            yield pending

    def call(self, root, *, deadline=None, member=None):
        return cells.call_pair_member(
            self.q, self.prior, self.critic, self.sources, self.f.f.model,
            self.member if member is None else member, 'repair', owner=self.f.f.owner,
            output=root, deadline=time.monotonic()+15 if deadline is None else deadline,
            alias=self.f.alias, execution_id='invented-repair', control_sha256=self.pair['control_sha256'])

    def independently_read(self, root):
        return native_evaluation.reconstruct_cell(
            root, parse_json((root/'INPUT.json').read_bytes()), execution_id='invented-repair',
            model_provenance=self.f.f.model, alias=self.f.alias, owner_pid=12345,
            endpoint=f'http://127.0.0.1:{self.f.f.spec.port}', method_proof=self.method)

    def assert_reserved_no_repeat(self, root, *, expected_calls):
        events = read_chain(root/'journal.jsonl')
        self.assertEqual(events[0]['event'], 'build_reserved')
        self.assertEqual(sum(event['event'] == 'refinement_generation_attempt' for event in events),
                         1 if expected_calls == 2 else 0)
        before = len(self.f.f.calls)
        with self.assertRaises(FileExistsError):
            self.call(root)
        self.assertEqual(len(self.f.f.calls), before)

    def test_real_tokenizer_and_generation_wire_reconstruct_once(self):
        root = self.f.root/'complete'
        with self.wire(self.responses()) as pending:
            result = self.call(root)
            self.assertFalse(pending)
            self.assert_reserved_no_repeat(root, expected_calls=2)
        self.assertEqual([row['path'] for row in self.f.f.calls], ['/tokenize', '/completion'])
        checked = self.independently_read(root)
        self.assertEqual(checked['summary'], encode(result['summary']))
        self.assertEqual(checked['summary']['usage'], dict(input_tokens=50, output_tokens=12, cost_usd=0))

    def test_timeout_and_interruption_keep_partial_bytes_and_attempt_without_retry(self):
        for index, error in enumerate((TimeoutError('invented read timeout'), KeyboardInterrupt('invented interruption'))):
            with self.subTest(error=type(error).__name__):
                root = self.f.root/f'partial-{index}'
                before = len(self.f.f.calls)
                with self.wire(self.responses(generation=PartialFailureResponse(error))):
                    with self.assertRaises(type(error)):
                        self.call(root)
                    self.assert_reserved_no_repeat(root, expected_calls=2)
                self.assertEqual(len(self.f.f.calls)-before, 2)
                state = parse_json((root/'native/failure.json').read_bytes())
                self.assertEqual(state['stage'], 'generation')
                self.assertEqual(state['status'], 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed')
                self.assertTrue(state['generation_entered'])
                self.assertIsNone(state['measured_usage'])
                wrapper = parse_json((root/'native/native-failure-wrapper.json').read_bytes())
                self.assertFalse(wrapper['complete'])
                self.assertEqual(wrapper['error_class'], type(error).__name__)
                self.assertEqual(base64.b64decode(wrapper['body_base64']), b'partial')
                self.assertEqual((root/'native/native-failure-body.bin').read_bytes(), b'partial')
                self.assertTrue((root/'FAILURE.json').is_file())
                self.assertFalse((root/'SUMMARY.json').exists())
                self.assertFalse((root/'native/native-response.bin').exists())
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.independently_read(root)

    def test_tokenizer_failure_retains_partial_quote_and_never_enters_generation(self):
        root = self.f.root/'tokenizer-failed'
        with self.wire(self.responses(tokenization=PartialFailureResponse(TimeoutError('invented quote timeout')))) as pending:
            with self.assertRaises(TimeoutError):
                self.call(root)
            self.assertEqual(len(pending), 1)
            self.assert_reserved_no_repeat(root, expected_calls=1)
        state = parse_json((root/'native/failure.json').read_bytes())
        quote = parse_json((root/'native/tokenization/result.json').read_bytes())
        self.assertEqual(state['stage'], 'tokenization')
        self.assertFalse(state['generation_entered'])
        self.assertIsNone(state['measured_usage'])
        self.assertEqual(quote['error_class'], 'TimeoutError')
        self.assertFalse(quote['complete'])
        self.assertEqual((root/'native/tokenization/body.bin').read_bytes(), b'partial')
        self.assertEqual([row['path'] for row in self.f.f.calls], ['/tokenize'])

    def test_capture_write_failure_preserves_unverified_reported_usage(self):
        root = self.f.root/'capture-failed'
        publish = transport.publish_bytes

        def fail_body(path, raw):
            if Path(path).name == 'native-response.bin':
                raise PermissionError('invented raw-capture failure')
            return publish(path, raw)

        with self.wire(self.responses()), patch.object(transport, 'publish_bytes', side_effect=fail_body):
            with self.assertRaises(PermissionError):
                self.call(root)
            self.assert_reserved_no_repeat(root, expected_calls=2)
        state = parse_json((root/'native/failure.json').read_bytes())
        self.assertEqual(state['stage'], 'capture')
        self.assertEqual(state['measured_usage'], dict(input_tokens=50, output_tokens=12, cost_usd=0))
        self.assertFalse(state['usage_verified'])
        self.assertTrue(state['generation_entered'])
        self.assertFalse((root/'native/native-response.bin').exists())
        self.assertFalse((root/'native/result.json').exists())
        self.assertFalse((root/'SUMMARY.json').exists())
        self.assertTrue((root/'FAILURE.json').is_file())

    def test_summary_write_failure_preserves_native_result_but_is_not_success(self):
        root = self.f.root/'summary-failed'
        publish = cells.publish_bytes

        def fail_summary(path, raw):
            if Path(path).name == 'SUMMARY.json':
                raise OSError('invented summary persistence failure')
            return publish(path, raw)

        with self.wire(self.responses()), patch.object(cells, 'publish_bytes', side_effect=fail_summary):
            with self.assertRaises(OSError):
                self.call(root)
            self.assert_reserved_no_repeat(root, expected_calls=2)
        self.assertTrue(parse_json((root/'native/result.json').read_bytes())['usage_verified'])
        self.assertTrue((root/'native/native-response.bin').is_file())
        self.assertTrue((root/'FAILURE.json').is_file())
        self.assertFalse((root/'SUMMARY.json').exists())
        self.assertEqual(read_chain(root/'journal.jsonl')[-1]['event'], 'build_failed')
        with self.assertRaises((ValueError, FileNotFoundError)):
            self.independently_read(root)

    def test_late_journal_failures_dominate_existing_native_result_or_summary(self):
        append = cells.RunJournal.append
        for index, failed_event in enumerate(('refinement_call_completed', 'refinement_cell_completed')):
            with self.subTest(event=failed_event):
                root = self.f.root/f'journal-failed-{index}'

                def fail_terminal(journal, event, **details):
                    if event == failed_event:
                        raise OSError('invented terminal journal failure')
                    return append(journal, event, **details)

                with self.wire(self.responses()), patch.object(cells.RunJournal, 'append', new=fail_terminal):
                    with self.assertRaises(OSError):
                        self.call(root)
                    self.assert_reserved_no_repeat(root, expected_calls=2)
                self.assertTrue((root/'native/result.json').is_file())
                self.assertTrue((root/'FAILURE.json').is_file())
                self.assertEqual((root/'SUMMARY.json').exists(), failed_event == 'refinement_cell_completed')
                if failed_event == 'refinement_call_completed':
                    state = parse_json((root/'native/failure.json').read_bytes())
                    self.assertEqual(state['stage'], 'finalization')
                    self.assertTrue(state['usage_verified'])
                    self.assertEqual(state['measured_usage']['output_tokens'], 12)
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.independently_read(root)

    def test_expired_and_invalid_deadlines_fail_before_any_http(self):
        for index, deadline in enumerate((time.monotonic()-1, True, float('nan'), float('inf'))):
            with self.subTest(deadline=deadline):
                root = self.f.root/f'deadline-{index}'
                with self.wire(self.responses()) as pending:
                    with self.assertRaises((ValueError, TimeoutError)):
                        self.call(root, deadline=deadline)
                    self.assertEqual(len(pending), 2)
                    self.assert_reserved_no_repeat(root, expected_calls=0)
                state = parse_json((root/'native/failure.json').read_bytes())
                self.assertFalse(state['generation_entered'])
                self.assertEqual(state['stage'], 'reservation')
        self.assertFalse(self.f.f.calls)

    def test_substituted_prepared_payload_fails_before_tokenization(self):
        member = encode(self.member)
        member['payload']['prompt'] += 'invented substitution'
        root = self.f.root/'substitution'
        with self.wire(self.responses()) as pending:
            with self.assertRaisesRegex(ValueError, 'Pre-generation member differs'):
                self.call(root, member=member)
            self.assertEqual(len(pending), 2)
            self.assert_reserved_no_repeat(root, expected_calls=0)
        self.assertFalse((root/'native').exists())
        self.assertTrue((root/'FAILURE.json').is_file())
        self.assertFalse(self.f.f.calls)

    def test_usage_integrity_failure_cannot_become_recoverable_codec_failure(self):
        root = self.f.root/'usage-mismatch'
        response = http_fixtures.Response(self.f.f.native_body(tokens_evaluated=51,
            content=canonical(dict(answer_index=0, evidence_ids=['fixture:p1'])).decode()))
        with self.wire(self.responses(generation=response)):
            with self.assertRaisesRegex(ValueError, 'exact token quote'):
                self.call(root)
            self.assert_reserved_no_repeat(root, expected_calls=2)
        state = parse_json((root/'native/failure.json').read_bytes())
        self.assertEqual(state['stage'], 'verification')
        self.assertNotEqual(state['error_type'], 'OutputCodecError')
        self.assertFalse(state['usage_verified'])
        self.assertEqual(state['measured_usage']['input_tokens'], 51)
        self.assertTrue((root/'native/native-response.bin').is_file())
        self.assertFalse((root/'SUMMARY.json').exists())

    def test_input_write_failure_retains_zero_call_failure_and_exclusive_reservation(self):
        root = self.f.root/'input-failed'
        publish = cells.publish_bytes

        def fail_input(path, raw):
            if Path(path).name == 'INPUT.json':
                raise PermissionError('invented input persistence failure')
            return publish(path, raw)

        with self.wire(self.responses()) as pending, patch.object(cells, 'publish_bytes', side_effect=fail_input):
            with self.assertRaises(PermissionError):
                self.call(root)
            self.assertEqual(len(pending), 2)
            self.assert_reserved_no_repeat(root, expected_calls=0)
        self.assertFalse((root/'INPUT.json').exists())
        self.assertTrue((root/'FAILURE.json').is_file())
        self.assertEqual([row['event'] for row in read_chain(root/'journal.jsonl')],
                         ['build_reserved', 'build_failed'])

    def test_same_directory_cannot_dispatch_concurrently(self):
        root = self.f.root/'concurrent'
        entered, release = threading.Event(), threading.Event()
        outcome = []

        class HeldConnection(http_fixtures.Connection):
            def request(connection, method, path, **kwargs):
                connection.is_generation = path == '/completion'
                super().request(method, path, **kwargs)

            def getresponse(connection):
                if connection.is_generation:
                    entered.set()
                    if not release.wait(5):
                        raise TimeoutError('invented test release was not signalled')
                return super().getresponse()

        def first():
            try:
                outcome.append(self.call(root))
            except BaseException as error:
                outcome.append(error)

        with self.wire(self.responses(), connection_factory=HeldConnection):
            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(entered.wait(5), 'First attempt did not enter the invented completion')
                with self.assertRaises(FileExistsError):
                    self.call(root)
                self.assertEqual([row['path'] for row in self.f.f.calls], ['/tokenize', '/completion'])
            finally:
                release.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcome), 1)
        if isinstance(outcome[0], BaseException):
            raise outcome[0]
        self.assertEqual(self.independently_read(root)['summary']['status'], 'completed')

    def test_secondary_failure_persistence_error_keeps_primary_and_native_partial_capture(self):
        root = self.f.root/'secondary-failure'
        publish = transport.publish_bytes

        def fail_failure_record(path, raw):
            if Path(path).name == 'failure.json':
                raise PermissionError('invented native terminal failure write error')
            return publish(path, raw)

        with self.wire(self.responses(generation=PartialFailureResponse(TimeoutError('primary timeout')))), \
             patch.object(transport, 'publish_bytes', side_effect=fail_failure_record):
            with self.assertRaisesRegex(TimeoutError, 'primary timeout') as caught:
                self.call(root)
            self.assert_reserved_no_repeat(root, expected_calls=2)
        self.assertIn('Failure persistence: PermissionError', caught.exception.__notes__)
        self.assertTrue((root/'native/native-failure-wrapper.json').is_file())
        self.assertEqual((root/'native/native-failure-body.bin').read_bytes(), b'partial')
        self.assertTrue((root/'FAILURE.json').is_file())
        self.assertFalse((root/'SUMMARY.json').exists())


if __name__ == '__main__':
    unittest.main()
