"""Independent source-product boundary regressions; synthetic transport only."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_science_readiness_sources as fixture
from asof.serde import ContractError, canonical, fingerprint, read_json, sha256_file, write_json
from tools.science import readiness_sources as sources
from tools.science import prospective_frame as frame


class SourceSelectionPeerTests(unittest.TestCase):
    nct = 'NCT12345678'

    def select(self, docs):
        return sources.select_documents({'documentSection': {'largeDocumentModule': {'largeDocs': docs}}}, self.nct)

    def test_filename_only_product_is_unknown_hold(self):
        result = self.select([{'filename': 'Prot_SAP.pdf'}])
        self.assertEqual('insufficient_under_cap_or_metadata', result['status'])
        self.assertEqual([], result['selected'])

    def test_unknown_product_blocks_other_easier_original(self):
        result = self.select([{'filename': 'Prot.pdf', 'hasProtocol': True}, {'filename': 'Other.pdf'}])
        self.assertEqual('insufficient_under_cap_or_metadata', result['status'])
        self.assertEqual([], result['selected'])
        self.assertEqual(2, len(result['listing']))

    def test_explicit_icf_only_does_not_block_protocol(self):
        result = self.select([{'filename': 'ICF.pdf', 'typeAbbrev': 'ICF', 'hasIcf': True},
                              {'filename': 'Prot.pdf', 'hasProtocol': True}])
        self.assertEqual(['Prot.pdf'], [r['filename'] for r in result['selected']])

    def test_combined_and_protocol_both_retained(self):
        result = self.select([{'filename': 'A.pdf', 'typeAbbrev': 'Prot'},
                              {'filename': 'Z.pdf', 'typeAbbrev': 'Prot_SAP'}])
        self.assertEqual(['Z.pdf', 'A.pdf'], [r['filename'] for r in result['selected']])

    def test_three_originals_hold_independent_of_dates(self):
        result = self.select([{'filename': f'Prot{i}.pdf', 'typeAbbrev': 'Prot', 'uploadDate': f'2026-10-{i+1:02d}T12:00'} for i in range(3)])
        self.assertEqual([], result['selected'])
        self.assertEqual('insufficient_under_cap_or_metadata', result['status'])

    def test_unrecognized_type_stays_unknown(self):
        result = self.select([{'filename': 'Unknown.pdf', 'typeAbbrev': 'UNRECOGNIZED'}])
        self.assertEqual('insufficient_under_cap_or_metadata', result['status'])


class SourceRuntimePeerTests(unittest.TestCase):
    setUp = fixture.ReadinessSourcesTests.setUp
    listing = fixture.ReadinessSourcesTests.listing
    doc = fixture.ReadinessSourcesTests.doc
    responses = fixture.ReadinessSourcesTests.responses
    prepare = fixture.ReadinessSourcesTests.prepare
    capture = fixture.ReadinessSourcesTests.capture
    audit = fixture.ReadinessSourcesTests.audit
    binary = fixture.ReadinessSourcesTests.binary

    def test_expired_R_denied_before_any_client_request(self):
        digest = self.prepare()
        client = fixture.fixtures.SyntheticClient([])
        with patch.object(sources, '_now', return_value=datetime(2026, 10, 25, tzinfo=timezone.utc)):
            with self.assertRaises(ContractError):
                sources.execute(self.output, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)
        self.assertFalse((self.output / 'execution-claimed.json').exists())

    def test_completed_source_packets_replay_after_R(self):
        self.capture()
        with patch.object(sources, '_now', return_value=datetime(2026, 10, 25, tzinfo=timezone.utc)):
            self.assertEqual(12, self.audit()['source_attempts'])

    def test_phase_array_order_does_not_create_drift(self):
        responses = self.responses()
        # Origin equality is checked separately; exercise packet planning with a
        # valid order-insensitive origin and listing phase pair directly.
        member = self.members[0]
        origin = {'protocolSection': {'designModule': {'phases': ['PHASE2', 'PHASE3']}}}
        responses[0]['protocolSection']['designModule']['phases'] = ['PHASE3', 'PHASE2']
        path = self.root / 'reversed-phases.json'
        write_json(path, responses[0])
        receipt = {'outcome': 'received', 'body': frame._pin(path)}
        packets = []
        sources._packets([member], [origin], self.projection, self.fields,
                         lambda request: receipt, self.root, packets)
        self.assertEqual('matched', packets[0]['phase_comparison'])

    def test_prose_change_cannot_grant_same_members_new_attempt(self):
        self.capture()
        value = read_json(self.protocol_path)
        value['rationale']['source_truth'] += ' Informational update only.'
        write_json(self.protocol_path, value)
        other = self.root / frame.OUTPUT_ROOT / 'same-source-job'
        digest = self.prepare(other)
        client = fixture.fixtures.SyntheticClient([])
        with self.assertRaises(FileExistsError):
            sources.execute(other, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)

    def reseal(self, result, mutate):
        write_json(self.output / 'packets.json', result)
        events = [json.loads(line) for line in (self.output / 'journal.jsonl').read_text().splitlines()]
        mutate(events)
        events[-1]['details']['packets'] = frame._pin(self.output / 'packets.json')
        previous = None
        for index, event in enumerate(events):
            event['sequence'], event['previous_sha256'] = index, previous
            event.pop('sha256', None)
            event['sha256'] = fingerprint(event)
            previous = event['sha256']
        (self.output / 'journal.jsonl').write_bytes(b''.join(canonical(e) + b'\n' for e in events))

    def test_failed_HTTP_reason_cannot_contradict_success_headers(self):
        responses = self.responses()
        request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        responses[0] = self.binary(request, b'not found', status=404)
        result = self.capture(responses)
        result['packets'][0]['listing']['response']['status'] = 200
        def mutate(events):
            events[4]['details']['status'] = 200
            events[5]['details']['response']['status'] = 200
        self.reseal(result, mutate)
        with self.assertRaises(ContractError):
            self.audit()

    def test_job_elapsed_cannot_hide_recorded_wall_span(self):
        result = self.capture()
        result['active_job_elapsed_seconds'] = 0
        start = datetime.fromisoformat(result['active_job_started_at_utc'])
        result['active_job_ended_at_utc'] = (start + timedelta(seconds=10)).isoformat()
        self.reseal(result, lambda events: None)
        with self.assertRaises(ContractError):
            self.audit()


if __name__ == '__main__':
    unittest.main()
