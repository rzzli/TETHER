"""Independent capacity-profile regressions; all sources are synthetic."""
from datetime import datetime, timezone
import hashlib
from unittest.mock import patch
import unittest

from tether_engine.serde import ContractError, read_json, sha256_file, write_json
from tools.science import prospective_capacity as capacity
from tools.science import prospective_transport as transport
from tools.science import prospective_frame as frame
from tests import test_science_prospective_capacity as fixture


class CapacityPeerTests(unittest.TestCase):
    setUp = fixture.ProspectiveCapacityTests.setUp
    record = fixture.ProspectiveCapacityTests.record
    prepare = fixture.ProspectiveCapacityTests.prepare
    capture = fixture.ProspectiveCapacityTests.capture
    page = fixture.ProspectiveCapacityTests.page
    audit = fixture.ProspectiveCapacityTests.audit

    def test_completed_capture_remains_replayable_after_R(self):
        self.capture([self.page()])
        later = datetime(2026, 10, 25, tzinfo=timezone.utc)
        with patch.object(transport, '_now', return_value=later):
            self.assertEqual(1, self.audit()['frame_count'])

    def test_expired_execution_is_rejected_without_source_attempt(self):
        digest = self.prepare()
        client = fixture.SyntheticClient([])
        later = datetime(2026, 10, 25, tzinfo=timezone.utc)
        with patch.object(transport, '_now', return_value=later):
            with self.assertRaises(ContractError):
                capacity.execute(self.output, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)
        self.assertFalse((self.output / 'execution-claimed.json').exists())

    def test_prose_reseal_cannot_retry_same_capacity_workload(self):
        self.capture([self.page()])
        amendment = read_json(self.amendment_path)
        amendment['rationale']['decision'] += ' No semantic change.'
        write_json(self.amendment_path, amendment)
        other = self.root / frame.OUTPUT_ROOT / 'same-semantic-profile'
        digest = self.prepare(other)
        client = fixture.SyntheticClient([])
        with self.assertRaises(FileExistsError):
            capacity.execute(other, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)

    def test_extra_nested_capacity_override_rejected(self):
        amendment = read_json(self.amendment_path)
        amendment['capacity_patch']['sample_max_records'] = 13
        write_json(self.amendment_path, amendment)
        with self.assertRaises(ContractError):
            self.prepare()

    def test_changed_scientific_dates_rejected(self):
        amendment = read_json(self.amendment_path)
        amendment['preserved_interval_start'] = '2026-09-25'
        write_json(self.amendment_path, amendment)
        with self.assertRaises(ContractError):
            self.prepare()

    def test_full_member_ledger_retains_exclusion_and_unknown(self):
        exposed = self.record(1)
        exposed['protocolSection']['identificationModule']['nctId'] = self.contract['exposed_ids'][0]
        unknown = self.record(2)
        del unknown['protocolSection']['designModule']['phases']
        bad = self.record(3)
        bad['protocolSection']['designModule']['phases'] = ['PHASE3']
        self.capture([self.page([exposed, unknown, bad], 3)])
        result = self.audit()
        ledger = {r['nct_id']: r for r in result['all_member_ledger']}
        self.assertEqual(3, len(ledger))
        self.assertTrue(ledger[self.contract['exposed_ids'][0]]['exposure_excluded'])
        self.assertEqual('screen_unknown', ledger['NCT00000002']['screen'])
        self.assertEqual('ineligible', ledger['NCT00000003']['screen'])
        self.assertEqual(['NCT00000002'], result['candidate_nct_ids'])
        self.assertEqual(0, result['selected_members'])

    def test_candidate_order_independent_of_transport_page_order(self):
        rows = [self.record(n) for n in range(1, 25)]
        self.capture([self.page(list(reversed(rows[12:])), 24, 'next'), self.page(rows[:12], 24)])
        expected = sorted([f'NCT{n:08d}' for n in range(1, 25)],
                          key=lambda n: (hashlib.sha256((capacity.SEED + n).encode()).hexdigest(), n))[:12]
        self.assertEqual(expected, self.audit()['candidate_nct_ids'])

    def test_empty_complete_frame_has_no_candidates(self):
        self.capture([self.page([], 0)])
        result = self.audit()
        self.assertEqual([], result['candidate_nct_ids'])
        self.assertEqual([], result['all_member_ledger'])


if __name__ == '__main__':
    unittest.main()
