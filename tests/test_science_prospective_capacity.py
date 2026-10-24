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

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, fingerprint, read_json, sha256_file, write_json
from tools.science import prospective_frame as frame
from tools.science import prospective_transport as transport

REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 24, 10, tzinfo=timezone.utc)
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


from tools.science import prospective_capacity as capacity

class ProspectiveCapacityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        protocol = read_json(REPO / frame.PROTOCOL)
        for relative in [frame.PROTOCOL] + [p['path'] for p in protocol['parents']]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            source = (REPO / 'tests/fixtures/prospective-frame-metadata' / Path(relative).name
                      if relative.startswith(frame.METADATA) else REPO / relative)
            shutil.copyfile(source, target)
        for module, name in ((frame, '_utc_now'), (transport, '_now')):
            clock = patch.object(module, name, return_value=NOW)
            clock.start()
            self.addCleanup(clock.stop)
        self.build = self.root / frame.OUTPUT_ROOT / 'synthetic-proposal'
        self.contract = frame.build_frame(self.root, self.build,
            expected_protocol_sha256=sha256_file(self.root / frame.PROTOCOL),
            readiness_date='2026-10-24', interval_start='2026-09-24', interval_end='2026-10-23')
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

        # Retain a real synthetic old failure, including its independent claim.
        old = self.root / frame.OUTPUT_ROOT / 'stopped-v01'
        transport.prepare_execution(self.root, old, expected_bound_sha256=sha256_file(self.bound_path))
        with self.assertRaises(ContractError):
            transport.execute(old, expected_manifest_sha256=sha256_file(old / 'execution.json'),
                              client=SyntheticClient([VERSION, {'totalCount': 4277, 'studies': []}]))
        stop_path = self.root / 'source-stop.json'
        write_json(stop_path, {'status': 'cold_source_attempt_audited_stopped_at_frozen_capacity_gate',
            'declared_query_count': 4277, 'completed_frame': False, 'clinical_activation': False,
            'selected_members': 0, 'automatic_retries': 0, 'unresolved_attempts': [],
            'execution_manifest': pin(old / 'execution.json'), 'journal': pin(old / 'journal.jsonl'),
            'raw_bodies': [pin(old / '00-response.bin'), pin(old / '01-response.bin')]})
        self.amendment_path = self.root / capacity.AMENDMENT
        amendment = read_json(REPO / capacity.AMENDMENT)
        for key, path in [('base_protocol', self.root / frame.PROTOCOL),
                          ('base_bound_request', self.bound_path), ('stopped_attempt', stop_path)]:
            amendment[key] = dict(pin(path), path=path.relative_to(self.root).as_posix())
        write_json(self.amendment_path, amendment)
        self.old_output = old
        self.old_hash = sha256_file(old / 'journal.jsonl')

    def record(self, number=1):
        return {'protocolSection': {'identificationModule': {'nctId': f'NCT{number:08d}'},
                'statusModule': {'studyFirstPostDateStruct': {'date': '2026-10-01', 'type': 'ACTUAL'},
                                 'lastUpdatePostDateStruct': {'date': '2026-10-22', 'type': 'ACTUAL'}},
                'designModule': {'studyType': 'INTERVENTIONAL', 'phases': ['PHASE2'],
                                 'designInfo': {'primaryPurpose': 'TREATMENT'}},
                'armsInterventionsModule': {'interventions': [{'type': 'DRUG'}]}}}

    def prepare(self, output=None):
        target = output or self.output
        capacity.prepare_execution(self.root, target, expected_amendment_sha256=sha256_file(self.amendment_path))
        return sha256_file(target / 'execution.json')

    def capture(self, pages, *, before=VERSION, after=VERSION):
        self.digest = self.prepare()
        self.client = SyntheticClient([before, *pages, after])
        return capacity.execute(self.output, expected_manifest_sha256=self.digest, client=self.client)

    def audit(self):
        return capacity.audit_capture(self.output, expected_manifest_sha256=self.digest)

    def page(self, records=None, count=1, token=None):
        result = {'totalCount': count, 'studies': records if records is not None else [self.record()]}
        if token is not None:
            result['nextPageToken'] = token
        return result

    def test_4277_records_nine_pages_original_seed(self):
        rows = [self.record(n) for n in range(1, 4278)]
        pages = [self.page(rows[i:i+500], 4277, str(i+500) if i+500 < 4277 else None)
                 for i in range(0, 4277, 500)]
        result = self.capture(pages)
        audit = self.audit()
        self.assertEqual((4277, 9, 0), (result['frame_count'], result['study_queries'], result['selected_members']))
        expected = sorted([r['protocolSection']['identificationModule']['nctId'] for r in rows],
            key=lambda n: (__import__('hashlib').sha256((capacity.SEED+n).encode()).hexdigest(), n))[:12]
        self.assertEqual(expected, audit['candidate_nct_ids'])
        self.assertFalse(audit['transport_qualified'])
        self.assertFalse(audit['clinical_activation'])
        self.assertEqual(self.old_hash, sha256_file(self.old_output / 'journal.jsonl'))
        self.assertNotIn('candidate_nct_ids', json.dumps(read_json(self.output / 'receipt.json')))

    def test_501_per_page_rejected(self):
        with self.assertRaises(ContractError):
            self.capture([self.page([self.record(n) for n in range(1, 502)], 501)])
        self.assertEqual(2, len(self.client.requests))

    def test_5001_total_rejected(self):
        with self.assertRaises(ContractError): self.capture([self.page(count=5001)])

    def test_missing_first_count(self):
        with self.assertRaises(ContractError): self.capture([{'studies': []}])

    def test_later_count_optional_and_empty_short_pages(self):
        self.capture([self.page([], 1, 'opaque/+'), {'studies': [self.record()]}])
        self.assertEqual(1, self.audit()['frame_count'])
        self.assertIn('pageToken=opaque%2F%2B', self.client.requests[2]['url'])

    def test_count_drift(self):
        with self.assertRaises(ContractError): self.capture([self.page([], 1, 'next'), self.page(count=2)])

    def test_token_loop(self):
        with self.assertRaises(ContractError): self.capture([self.page([], 1, 'next'), self.page([], 1, 'next')])

    def test_terminal_truncation(self):
        with self.assertRaises(ContractError): self.capture([self.page([], 1)])

    def test_page_attempt_cap(self):
        with self.assertRaises(ContractError): self.capture([self.page([], 1, str(i)) for i in range(11)])
        self.assertEqual(11, len(self.client.requests))

    def test_duplicate_identity(self):
        with self.assertRaises(ContractError): self.capture([self.page([self.record(), self.record()], 2)])

    def test_unprojected_fields(self):
        row = self.record(); row['resultsSection'] = {}
        with self.assertRaises(ContractError): self.capture([self.page([row])])

    def test_screen_unknown_and_disqualified(self):
        unknown, excluded = self.record(1), self.record(2)
        del unknown['protocolSection']['designModule']['phases']
        excluded['protocolSection']['designModule']['studyType'] = 'OBSERVATIONAL'
        self.capture([self.page([unknown, excluded], 2)])
        audit = self.audit()
        self.assertEqual(['screen_unknown', 'ineligible'], [r['screen'] for r in audit['all_member_ledger']])
        self.assertEqual(['NCT00000001'], audit['candidate_nct_ids'])

    def test_profile_scientific_override_rejected(self):
        amendment = read_json(self.amendment_path); amendment['eligibility'] = {'phase': 'PHASE3'}
        write_json(self.amendment_path, amendment)
        with self.assertRaises(ContractError): self.prepare()

    def test_profile_wrong_cap(self):
        amendment = read_json(self.amendment_path); amendment['capacity_patch']['page_size'] = 1000
        write_json(self.amendment_path, amendment)
        with self.assertRaises(ContractError): self.prepare()

    def test_profile_wrong_seed(self):
        amendment = read_json(self.amendment_path); amendment['sampling_seed_sha256'] = '0'*64
        write_json(self.amendment_path, amendment)
        with self.assertRaises(ContractError): self.prepare()

    def test_version_drift(self):
        with self.assertRaises(ContractError): self.capture([self.page()], after=dict(VERSION, dataTimestamp='changed'))

    def test_api_schema_version_drift(self):
        with self.assertRaises(ContractError): self.capture([self.page()], before=dict(VERSION, apiVersion='new'))
        self.assertEqual(1, len(self.client.requests))

    def test_timeout_durable_no_retry(self):
        with self.assertRaises(TimeoutError): self.capture([TimeoutError()])
        self.assertEqual([], capacity.inspect_execution(self.output)['unresolved_attempts'])
        with self.assertRaises(ContractError): capacity.execute(self.output, expected_manifest_sha256=self.digest, client=self.client)

    def test_interrupt_durable(self):
        with self.assertRaises(KeyboardInterrupt): self.capture([KeyboardInterrupt()])
        self.assertEqual([], capacity.inspect_execution(self.output)['unresolved_attempts'])

    def test_partial_stream_bytes_retained(self):
        digest = self.prepare()
        client = SyntheticClient([VERSION, [('headers', {'status': 200, 'final_url': capacity.page_request(self.contract)['url'],
            'headers': {'Content-Length': '100'}}), ('body', b'{')]])
        with self.assertRaises(ContractError): capacity.execute(self.output, expected_manifest_sha256=digest, client=client)
        self.assertEqual(b'{', (self.output / '01-response.bin').read_bytes())

    def test_cross_manifest_claim_no_retry(self):
        self.capture([self.page()])
        other = self.root / frame.OUTPUT_ROOT / 'another-capacity'
        digest = self.prepare(other); client = SyntheticClient([])
        with self.assertRaises(FileExistsError): capacity.execute(other, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)

    def test_output_escape(self):
        outside = self.root / 'escaped'
        with self.assertRaises(ContractError): self.prepare(outside)
        self.assertFalse(outside.exists())

    def test_external_manifest_digest(self):
        digest = self.prepare(); path = self.output / 'execution.json'
        value = read_json(path); value['request']['parameters']['pageSize'] = '1'; write_json(path, value)
        with self.assertRaises(ContractError): capacity.execute(self.output, expected_manifest_sha256=digest, client=SyntheticClient([]))
        self.assertFalse((self.output / 'execution-claimed.json').exists())

    def test_resealed_omitted_archive(self):
        self.prepare(); path = self.output / 'execution.json'
        value = read_json(path); value['archives'].pop(); value.pop('manifest_sha256'); value['manifest_sha256'] = fingerprint(value)
        write_json(path, value)
        with self.assertRaises(ContractError): capacity.execute(self.output, expected_manifest_sha256=sha256_file(path), client=SyntheticClient([]))
        self.assertFalse((self.output / 'execution-claimed.json').exists())

    def test_raw_mutation_audit(self):
        self.capture([self.page()]); (self.output / '01-response.bin').write_bytes(b'{}')
        with self.assertRaises(ContractError): self.audit()

    def test_receipt_mutation_audit(self):
        self.capture([self.page()]); value = read_json(self.output / 'receipt.json'); value['frame_count'] = 2
        write_json(self.output / 'receipt.json', value)
        with self.assertRaises(ContractError): self.audit()

    def test_metadata_drift_before_dispatch(self):
        digest = self.prepare(); path = self.root / (frame.METADATA + '04-version.json'); path.write_text('{}')
        client = SyntheticClient([])
        with self.assertRaises(ContractError): capacity.execute(self.output, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)

    def reseal_events(self, mutate):
        # Recompute the whole public hash chain, so semantic audit must catch it.
        from asof.serde import canonical
        events = [json.loads(line) for line in (self.output / 'journal.jsonl').read_text().splitlines()]
        mutate(events)
        previous = None
        for index, event in enumerate(events):
            event['sequence'], event['previous_sha256'] = index, previous
            event.pop('sha256', None); event['sha256'] = fingerprint(event); previous = event['sha256']
        (self.output / 'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))

    def test_resealed_journal_request_mismatch(self):
        self.capture([self.page()])
        self.reseal_events(lambda events: events[6]['details']['request'].update(url='https://example.invalid/'))
        with self.assertRaises(ContractError): self.audit()

    def test_resealed_journal_event_order(self):
        self.capture([self.page()])
        def reorder(events): events[3], events[4] = events[4], events[3]
        self.reseal_events(reorder)
        with self.assertRaises(ContractError): self.audit()

    def test_resealed_journal_elapsed_mismatch(self):
        self.capture([self.page()])
        self.reseal_events(lambda events: events[5]['details'].update(elapsed_seconds=121))
        with self.assertRaises(ContractError): self.audit()

    def test_offline_audit_after_R(self):
        self.capture([self.page()])
        with patch.object(transport, '_now', return_value=datetime(2026, 10, 25, tzinfo=timezone.utc)):
            self.assertTrue(self.audit()['complete'])

    def test_prose_only_reseal_does_not_grant_new_attempt(self):
        self.capture([self.page()])
        value = read_json(self.amendment_path); value['exposure_disclosure'] += ' Unchanged scope.'
        write_json(self.amendment_path, value)
        other = self.root / frame.OUTPUT_ROOT / 'new-prose'
        digest = self.prepare(other); client = SyntheticClient([])
        with self.assertRaises(FileExistsError):
            capacity.execute(other, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)


if __name__ == '__main__':
    unittest.main()

