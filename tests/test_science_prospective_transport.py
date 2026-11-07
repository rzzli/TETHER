"""Offline synthetic clients only; never contact the public source in tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import queue
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, fingerprint, read_json, sha256_file, write_json
from tools.science import prospective_frame as frame
from tests.prospective_fixtures import restore_protocol_inputs, archived_json
from tools.science import prospective_transport as transport

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
VERSION = {'apiVersion': '2.0.5', 'dataTimestamp': '2026-10-23T09:00:04'}


class SyntheticClient:
    evidence_kind = 'synthetic'

    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def stream(self, request, *, deadline):
        self.requests.append(copy.deepcopy(request))
        value = next(self.responses)
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, dict):
            value = [('headers', {'status': 200, 'final_url': request['url'],
                                  'headers': {'Content-Type': 'application/json'}}),
                     ('body', json.dumps(value).encode())]
        for kind, item in value:
            if isinstance(item, BaseException):
                raise item
            yield kind, item


class ProspectiveTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_bytes = restore_protocol_inputs(self.root)
        for module, name in ((frame, '_utc_now'), (transport, '_now')):
            clock = patch.object(module, name, return_value=NOW)
            clock.start()
            self.addCleanup(clock.stop)
        self.build = self.root / frame.OUTPUT_ROOT / 'synthetic-proposal'
        self.contract = frame.build_frame(self.root, self.build,
            expected_protocol_sha256=sha256_file(self.root / frame.PROTOCOL),
            readiness_date='2026-10-23', interval_start='2026-09-23', interval_end='2026-10-22')
        inventory_output = self.root / frame.OUTPUT_ROOT / 'inventory'
        j = RunJournal(inventory_output)
        write_json(inventory_output / 'inventory.json', {'nct_ids': self.contract['exposed_ids']})
        write_json(inventory_output / 'report.json', {'synthetic': True})
        j.append('inventory_completed')
        j.close()
        pin = frame._pin
        receipt_path = self.root / 'inventory-receipt.json'
        inventory_receipt = {key: pin(inventory_output / (key + ('.jsonl' if key == 'journal' else '.json')))
                             for key in ('inventory', 'report', 'journal')}
        inventory_receipt['distinct_exposed_nct_ids'] = len(self.contract['exposed_ids'])
        write_json(receipt_path, inventory_receipt)
        self.bound_path = self.root / transport.BOUND_REQUEST
        self.bound_path.parent.mkdir(parents=True, exist_ok=True)
        bound = {'status': 'named_origin_inventory_bound_before_source_dispatch',
                 'source_dispatch_allowed': False, 'clinical_activation': False,
                 'contract': pin(self.build / 'contract.json'), 'request': pin(self.build / 'request.json'),
                 'journal': pin(self.build / 'journal.jsonl'), 'inventory_receipt': pin(receipt_path),
                 'inventory': inventory_receipt['inventory'],
                 'named_source_inventory_ids': len(self.contract['exposed_ids'])}
        bound.update({key: self.contract[key] for key in ('readiness_date_R', 'interval_start', 'interval_end')})
        write_json(self.bound_path, bound)
        self.output = self.root / frame.OUTPUT_ROOT / 'synthetic-execution'

    def prepare(self, output=None):
        return transport.prepare_execution(self.root, output or self.output,
                                           expected_bound_sha256=sha256_file(self.bound_path))

    def run_capture(self, responses, *, prepare=True, output=None):
        target = output or self.output
        if prepare:
            self.prepare(target)
        client = SyntheticClient(responses)
        self.client = client
        result = transport.execute(target, expected_manifest_sha256=sha256_file(target / 'execution.json'), client=client)
        return result

    def record(self, number=1):
        return {'protocolSection': {'identificationModule': {'nctId': f'NCT{number:08d}'},
                'statusModule': {'studyFirstPostDateStruct': {'date': '2026-10-01', 'type': 'ACTUAL'},
                                 'lastUpdatePostDateStruct': {'date': '2026-10-22', 'type': 'ACTUAL'}},
                'designModule': {'studyType': 'INTERVENTIONAL', 'phases': ['PHASE2'],
                                 'designInfo': {'primaryPurpose': 'TREATMENT'}},
                'armsInterventionsModule': {'interventions': [{'type': 'DRUG'}]}}}

    def page(self, count=1):
        return {'totalCount': count, 'studies': [self.record()]}

    def failed(self, responses, calls):
        with self.assertRaises((ContractError, TimeoutError, KeyboardInterrupt, OSError)):
            self.run_capture(responses)
        self.assertEqual(calls, len(self.client.requests))
        inspected = transport.inspect_execution(self.output)
        self.assertEqual([], inspected['unresolved_attempts'])
        self.assertIn(inspected['last_event'], ('run_failed', 'run_interrupted'))
        self.assertFalse(inspected['receipt_present'])
        self.assertIn('never redispatch', inspected['recovery'])
        return read_chain(self.output / 'journal.jsonl')

    def test_preparation_archives_and_keeps_original_non_dispatch(self):
        before = sha256_file(self.build / 'contract.json')
        manifest = self.prepare()
        self.assertTrue(manifest['source_dispatch_allowed'])
        self.assertFalse(manifest['clinical_activation'])
        self.assertEqual(before, sha256_file(self.build / 'contract.json'))
        self.assertFalse(read_json(self.build / 'contract.json')['source_dispatch_allowed'])
        self.assertGreater(len(manifest['archives']), 10)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_complete_capture_exact_requests_and_quarantines_selection(self):
        result = self.run_capture([VERSION, self.page(), VERSION])
        self.assertEqual(1, result['frame_count'])
        self.assertEqual(0, result['selected_members'])
        self.assertFalse(result['clinical_activation'])
        self.assertFalse(result['transport_qualified'])
        self.assertFalse(result['atomic_snapshot'])
        self.assertEqual([transport.VERSION_REQUEST, frame.page_request(self.contract), transport.VERSION_REQUEST],
                         self.client.requests)
        self.assertNotIn('sample_nct_ids', read_json(self.output / 'quarantined-frame-validation.json'))
        self.assertEqual('execution_completed', transport.inspect_execution(self.output)['last_event'])
        with self.assertRaises(FileExistsError):
            self.run_capture([], prepare=False)

    def test_opaque_server_token_is_only_query_change(self):
        first = {'totalCount': 101, 'studies': [self.record(n) for n in range(1, 101)],
                 'nextPageToken': 'opaque +/&?token'}
        second = {'totalCount': 101, 'studies': [self.record(101)]}
        self.run_capture([VERSION, first, second, VERSION])
        self.assertEqual(frame.page_request(self.contract, 'opaque +/&?token'), self.client.requests[2])

    def test_missing_count_stops_before_another_page(self):
        page = self.page()
        del page['totalCount']
        self.failed([VERSION, page], 2)

    def test_capacity_is_explicit_gate_before_pagination(self):
        page = {'totalCount': 501, 'studies': [], 'nextPageToken': 'would-fetch'}
        with self.assertRaisesRegex(ContractError, 'capacity gate'):
            self.run_capture([VERSION, page])
        self.assertEqual(2, len(self.client.requests))
        self.assertEqual('run_failed', transport.inspect_execution(self.output)['last_event'])

    def test_extra_results_field_stops_early(self):
        page = self.page()
        page['studies'][0]['resultsSection'] = {}
        self.failed([VERSION, page], 2)

    def test_future_update_stops_early(self):
        page = self.page()
        page['studies'][0]['protocolSection']['statusModule']['lastUpdatePostDateStruct']['date'] = '2026-10-24'
        self.failed([VERSION, page], 2)

    def test_duplicate_ids_stops_early(self):
        page = {'totalCount': 2, 'studies': [self.record(), self.record()]}
        self.failed([VERSION, page], 2)

    def test_short_nonterminal_page_continues_to_terminal(self):
        page = self.page(2)
        page['nextPageToken'] = 'next'
        second = {'studies': [self.record(2)]}
        receipt = self.run_capture([VERSION, page, second, VERSION])
        self.assertEqual(2, receipt['frame_count'])

    def test_empty_nonterminal_page_continues_even_after_count_reached(self):
        page = self.page()
        page['nextPageToken'] = 'empty-terminal'
        receipt = self.run_capture([VERSION, page, {'studies': []}, VERSION])
        self.assertEqual(1, receipt['frame_count'])

    def test_later_count_drift_fails(self):
        page = self.page(2)
        page['nextPageToken'] = 'next'
        self.failed([VERSION, page, {'studies': [self.record(2)], 'totalCount': 3}], 3)

    def test_capacity_not_reported_before_date_validation(self):
        page = self.page(501)
        page['studies'][0]['protocolSection']['statusModule']['studyFirstPostDateStruct']['date'] = '2026-01-01'
        with self.assertRaisesRegex(ContractError, 'First posting date'):
            self.run_capture([VERSION, page])

    def test_partial_terminal_page_stops_early(self):
        self.failed([VERSION, self.page(2)], 2)

    def test_token_loop_stops_without_repeating_call(self):
        first = {'totalCount': 201, 'studies': [self.record(n) for n in range(1, 101)], 'nextPageToken': 'same'}
        second = {'totalCount': 201, 'studies': [self.record(n) for n in range(101, 201)], 'nextPageToken': 'same'}
        self.failed([VERSION, first, second], 3)

    def test_timeout_is_accounted_and_never_retried(self):
        events = self.failed([TimeoutError('synthetic')], 1)
        terminal = [e for e in events if e['event'] == 'attempt_terminal'][0]
        self.assertEqual('TimeoutError', terminal['details']['error_class'])
        self.assertEqual(0, terminal['details']['retained_body']['bytes'])

    def test_interrupt_retains_bytes_and_terminal(self):
        request = transport.VERSION_REQUEST
        events = self.failed([[('headers', {'status': 200, 'final_url': request['url'], 'headers': {}}),
                               ('body', b'partial'), ('body', KeyboardInterrupt())]], 1)
        self.assertEqual(b'partial', (self.output / '00-response.bin').read_bytes())
        self.assertEqual('run_interrupted', events[-1]['event'])

    def test_oversize_retains_only_bounded_prefix(self):
        response = [('headers', {'status': 200, 'final_url': transport.VERSION_URL, 'headers': {}}),
                    ('body', b'x' * (2 * 1024 * 1024 + 1))]
        self.failed([response], 1)
        self.assertEqual(2 * 1024 * 1024, (self.output / '00-response.bin').stat().st_size)

    def test_error_body_and_safe_headers_retained(self):
        response = [('headers', {'status': 503, 'final_url': transport.VERSION_URL,
                                 'headers': {'Set-Cookie': 'private', 'Date': 'a\nb'}}),
                    ('body', b'synthetic error')]
        events = self.failed([response], 1)
        headers = [e for e in events if e['event'] == 'attempt_response_headers'][0]['details']['headers']
        self.assertEqual({'date': 'ab'}, dict(headers))
        self.assertEqual(b'synthetic error', (self.output / '00-response.bin').read_bytes())

    def test_redirect_is_error_with_body_never_followed(self):
        response = [('headers', {'status': 302, 'final_url': transport.VERSION_URL,
                                 'headers': {'Location': 'https://untrusted.invalid/?secret'}}),
                    ('body', b'redirect body')]
        self.failed([response], 1)

    def test_unexpected_final_url_rejected(self):
        response = [('headers', {'status': 200, 'final_url': transport.VERSION_URL + '/changed', 'headers': {}}),
                    ('body', json.dumps(VERSION).encode())]
        self.failed([response], 1)

    def test_version_drift_fails_after_retained_final_receipt(self):
        changed = dict(VERSION, dataTimestamp='different')
        self.failed([VERSION, self.page(), changed], 3)

    def test_unknown_version_schema_stops_before_study_call(self):
        self.failed([dict(VERSION, unexpected=True)], 1)

    def test_metadata_api_version_mismatch_stops_before_study_call(self):
        self.failed([dict(VERSION, apiVersion='999')], 1)

    def test_manifest_tamper_and_pin_tamper_do_not_dispatch(self):
        self.prepare()
        expected = sha256_file(self.output / 'execution.json')
        with (self.output / 'execution.json').open('ab') as stream:
            stream.write(b' ')
        client = SyntheticClient([])
        with self.assertRaises(ContractError):
            transport.execute(self.output, expected_manifest_sha256=expected, client=client)
        self.assertEqual([], client.requests)

    def test_request_artifact_tamper_does_not_dispatch(self):
        self.prepare()
        request = read_json(self.build / 'request.json')
        request['parameters']['pageSize'] = '500'
        write_json(self.build / 'request.json', request)
        client = SyntheticClient([])
        with self.assertRaises(ContractError):
            transport.execute(self.output, expected_manifest_sha256=sha256_file(self.output / 'execution.json'), client=client)
        self.assertEqual([], client.requests)

    def test_output_escape_and_expired_R_rejected(self):
        with self.assertRaises(ContractError):
            self.prepare(self.root / 'escaped')
        with patch.object(transport, '_now', return_value=datetime(2026, 10, 24, tzinfo=timezone.utc)):
            with self.assertRaisesRegex(ContractError, 'Expired R'):
                self.prepare()

    def test_copied_manifest_outside_root_cannot_write_execution_marker(self):
        self.prepare()
        outside = self.root / 'outside-evidence-root'
        shutil.copytree(self.output, outside)
        journal_hash = sha256_file(outside / 'journal.jsonl')
        client = SyntheticClient([])
        for change_path in (False, True):
            manifest = read_json(outside / 'execution.json')
            if change_path:
                manifest['output'] = str(outside.resolve())
                manifest.pop('manifest_sha256')
                manifest['manifest_sha256'] = fingerprint(manifest)
                write_json(outside / 'execution.json', manifest)
            with self.assertRaises(ContractError):
                transport.execute(outside, expected_manifest_sha256=sha256_file(outside / 'execution.json'), client=client)
            self.assertFalse((outside / 'execution-claimed.json').exists())
            self.assertEqual(journal_hash, sha256_file(outside / 'journal.jsonl'))
        self.assertEqual([], client.requests)

    def test_execution_traversal_fails_before_any_marker(self):
        self.prepare()
        journal_hash = sha256_file(self.output / 'journal.jsonl')
        traversal = self.output / '..' / self.output.name
        client = SyntheticClient([])
        with self.assertRaisesRegex(ContractError, 'traversal'):
            transport.execute(traversal, expected_manifest_sha256=sha256_file(self.output / 'execution.json'), client=client)
        self.assertFalse((self.output / 'execution-claimed.json').exists())
        self.assertEqual(journal_hash, sha256_file(self.output / 'journal.jsonl'))
        self.assertEqual([], client.requests)

    def test_inventory_must_equal_exposed_ids(self):
        inventory = read_json(self.bound_path)['inventory']
        write_json(Path(inventory['path']), {'nct_ids': []})
        with self.assertRaises(ContractError):
            self.prepare()

    def test_concurrent_execute_consumes_single_claim(self):
        self.prepare()
        expected = sha256_file(self.output / 'execution.json')
        client = SyntheticClient([VERSION, self.page(), VERSION])
        def run():
            try:
                transport.execute(self.output, expected_manifest_sha256=expected, client=client)
                return 'complete'
            except FileExistsError:
                return 'claimed'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(['claimed', 'complete'], sorted(pool.map(lambda _: run(), range(2))))
        self.assertEqual(3, len(client.requests))

    def test_another_manifest_cannot_retry_failed_proposal(self):
        self.failed([TimeoutError('synthetic')], 1)
        other = self.root / frame.OUTPUT_ROOT / 'another-execution'
        self.prepare(other)
        client = SyntheticClient([])
        with self.assertRaises(FileExistsError):
            transport.execute(other, expected_manifest_sha256=sha256_file(other / 'execution.json'), client=client)
        self.assertEqual([], client.requests)

    def test_hard_elapsed_guard_fails_durable(self):
        self.prepare()
        # Parent verifies elapsed time independently of a cooperative client.
        clock = iter([0, 0, 0, 121, 121])
        with patch.object(transport.time, 'monotonic', side_effect=lambda: next(clock, 121)):
            client = SyntheticClient([VERSION])
            with self.assertRaises(ContractError):
                transport.execute(self.output, expected_manifest_sha256=sha256_file(self.output / 'execution.json'), client=client)
        self.assertEqual([], transport.inspect_execution(self.output)['unresolved_attempts'])

    def test_actual_worker_redirect_handler_disables_follow(self):
        self.assertIsNone(transport._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid'))

    def test_stdlib_worker_sends_no_auth_or_proxy_and_streams_offline(self):
        class Response:
            status = 200
            headers = {'Content-Type': 'application/json'}
            def __enter__(self):
                self.chunks = iter([b'first', b'second', b''])
                return self
            def __exit__(self, *args):
                pass
            def geturl(self):
                return transport.VERSION_URL
            def read1(self, size):
                self_test.assertEqual(65536, size)
                return next(self.chunks)
        self_test = self
        events = queue.Queue()
        with patch.object(transport.urllib.request, 'build_opener') as build:
            build.return_value.open.return_value = Response()
            transport._http_worker(transport.VERSION_REQUEST, events)
            handlers = build.call_args.args
            self.assertEqual({}, handlers[0].proxies)
            self.assertIsInstance(handlers[1], transport._NoRedirect)
            req = build.return_value.open.call_args.args[0]
            self.assertEqual(transport.VERSION_URL, req.full_url)
            self.assertEqual('GET', req.method)
            self.assertEqual({'accept', 'accept-encoding', 'user-agent'},
                             {key.lower() for key, _ in req.header_items()})
            self.assertEqual(40, build.return_value.open.call_args.kwargs['timeout'])
        captured = []
        while not events.empty():
            captured.append(events.get_nowait())
        self.assertEqual(['headers', 'body', 'body', 'done'], [kind for kind, _ in captured])

    def test_close_error_cannot_suppress_terminal_timeout_accounting(self):
        self.prepare()
        class Client:
            evidence_kind = 'synthetic'
            def stream(self, request, *, deadline):
                try:
                    yield 'headers', {'status': 200, 'final_url': request['url'], 'headers': {}}
                    yield 'body', b'partial'
                finally:
                    raise RuntimeError('synthetic cleanup failure')
        # Timeout immediately after receiving headers; generator.close also fails.
        clock = iter([0, 0, 0, 121, 121])
        with patch.object(transport.time, 'monotonic', side_effect=lambda: next(clock, 121)):
            with self.assertRaisesRegex(ContractError, 'elapsed cap'):
                transport.execute(self.output, expected_manifest_sha256=sha256_file(self.output / 'execution.json'),
                                  client=Client())
        events = read_chain(self.output / 'journal.jsonl')
        terminal = [e for e in events if e['event'] == 'attempt_terminal']
        self.assertEqual(1, len(terminal))
        self.assertEqual('ContractError', terminal[0]['details']['error_class'])

    def test_expired_frame_budget_prevents_new_attempt(self):
        self.prepare()
        clock = iter([0, 601])
        client = SyntheticClient([])
        with patch.object(transport.time, 'monotonic', side_effect=lambda: next(clock, 601)):
            with self.assertRaisesRegex(ContractError, 'before dispatch'):
                transport.execute(self.output, expected_manifest_sha256=sha256_file(self.output / 'execution.json'),
                                  client=client)
        self.assertEqual([], client.requests)
        self.assertEqual([], transport.inspect_execution(self.output)['attempts_started'])


if __name__ == '__main__':
    unittest.main()
