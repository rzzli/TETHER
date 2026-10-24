"""Independent adversarial synthetic frame checks; never accesses study sources."""
import json
import unittest

from asof.serde import ContractError, sha256_file
from asof.journal import read_chain
from tools.science import prospective_frame as frame
from tests import test_science_prospective_frame as fixtures


class ProspectiveFramePeerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProspectiveFrameTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_single_page_over_request_limit_below_frame_limit_rejected(self):
        f = self.fixture
        contract = f.build()
        page = f.page(contract, [], total=0)
        page['ended_at_utc'] = '2026-10-23T10:02:02Z'
        with self.assertRaises(ContractError):
            f.validate(contract, [page])

    def test_request_limit_boundary_is_accepted_offline_only(self):
        f = self.fixture
        contract = f.build()
        page = f.page(contract, [], total=0)
        page['ended_at_utc'] = '2026-10-23T10:02:01Z'
        result = f.validate(contract, [page])
        self.assertFalse(result['transport_qualified'])
        self.assertFalse(result['clinical_activation'])

    def test_real_raw_byte_limit_counts_json_whitespace(self):
        f = self.fixture
        contract = f.build()
        page = f.page(contract, [], total=0)
        path = f.raw / page['body']['path']
        path.write_bytes(b'{"studies":[],"totalCount":0}' + b' ' * (2 * 1024 * 1024))
        page['body'].update(bytes=path.stat().st_size, sha256=sha256_file(path))
        with self.assertRaises(ContractError):
            f.validate(contract, [page])

    def test_totalcount_required_before_any_sample(self):
        f = self.fixture
        contract = f.build()
        page = f.page(contract, [f.record()])
        path = f.raw / page['body']['path']
        path.write_text(json.dumps({'studies': [f.record()]}), encoding='utf-8')
        page['body'].update(bytes=path.stat().st_size, sha256=sha256_file(path))
        with self.assertRaises(ContractError):
            f.validate(contract, [page])

    def test_array_at_object_or_scalar_location_rejected_as_contract_error(self):
        f = self.fixture
        contract = f.build()
        for key, value in (('designInfo', [{'primaryPurpose': 'TREATMENT'}]),
                           ('studyType', ['INTERVENTIONAL'])):
            with self.subTest(key=key):
                row = f.record()
                row['protocolSection']['designModule'][key] = value
                with self.assertRaises(ContractError):
                    f.validate(contract, [f.page(contract, [row])])

    def test_phase_null_and_missing_purpose_remain_in_sample(self):
        f = self.fixture
        contract = f.build()
        row = f.record()
        row['protocolSection']['designModule']['phases'] = None
        del row['protocolSection']['designModule']['designInfo']
        result = f.validate(contract, [f.page(contract, [row])])
        self.assertEqual(['NCT00000001'], result['sample_nct_ids'])
        self.assertEqual('screen_unknown', result['all_member_ledger'][0]['screen'])

    def test_result_leaf_hidden_inside_allowed_object_is_rejected(self):
        f = self.fixture
        contract = f.build()
        row = f.record()
        row['protocolSection']['designModule']['designInfo']['primaryOutcomes'] = 'synthetic outcome'
        with self.assertRaises(ContractError):
            f.validate(contract, [f.page(contract, [row])])

    def test_nonterminal_last_page_never_yields_partial_sample(self):
        f = self.fixture
        contract = f.build()
        page = f.page(contract, [f.record()], total=1, token='still-more')
        with self.assertRaises(ContractError):
            f.validate(contract, [page])

    def test_failed_build_keeps_reserved_failure_and_cannot_be_reused(self):
        f = self.fixture
        with self.assertRaises(ContractError):
            f.build(readiness_date='2025-01-01')
        events = read_chain(f.output / 'journal.jsonl')
        self.assertEqual('build_reserved', events[0]['event'])
        self.assertEqual('build_failed', events[-1]['event'])
        with self.assertRaises(FileExistsError):
            f.build()

    def test_reserved_request_file_mutation_is_detected(self):
        f = self.fixture
        f.build()
        request = f.output / 'request.json'
        request.write_bytes(request.read_bytes() + b' ')
        with self.assertRaises(ContractError):
            frame.verify_build(f.output)
