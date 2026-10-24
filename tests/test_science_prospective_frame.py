"""Synthetic offline shapes; real archived schema, never live study data."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from asof.serde import ContractError, fingerprint, read_json, sha256_file, write_json
from tools.science import prospective_frame as frame


REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
VERSION = {'apiVersion': '2.0.5', 'dataTimestamp': '2026-10-23T09:00:04'}


class ProspectiveFrameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        protocol = read_json(REPO / frame.PROTOCOL)
        for relative in [frame.PROTOCOL] + [p['path'] for p in protocol['parents']]:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Small public schema fixtures are tracked; tests never require the
            # ignored local acquisition tree or a network request on clean CI.
            source = (REPO / 'tests/fixtures/prospective-frame-metadata' / Path(relative).name
                      if relative.startswith(frame.METADATA) else REPO / relative)
            shutil.copyfile(source, target)
        self.output = self.root / frame.OUTPUT_ROOT / 'synthetic-build'
        self.raw = self.root / 'synthetic-pages'
        self.raw.mkdir()
        self.clock = patch.object(frame, '_utc_now', return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.counter = 0

    def build(self, **overrides):
        args = dict(expected_protocol_sha256=sha256_file(self.root / frame.PROTOCOL),
                    readiness_date='2026-10-23', interval_start='2026-09-23', interval_end='2026-10-22')
        args.update(overrides)
        return frame.build_frame(self.root, self.output, **args)

    def record(self, number=1):
        # These canonical identifiers are synthetic fixtures, not retrieved trials.
        return {'protocolSection': {
            'identificationModule': {'nctId': f'NCT{number:08d}'},
            'statusModule': {'studyFirstPostDateStruct': {'date': '2026-10-01', 'type': 'ACTUAL'},
                             'lastUpdatePostDateStruct': {'date': '2026-10-22', 'type': 'ACTUAL'}},
            'designModule': {'studyType': 'INTERVENTIONAL', 'phases': ['PHASE2'],
                             'designInfo': {'primaryPurpose': 'TREATMENT'}},
            'armsInterventionsModule': {'interventions': [{'type': 'DRUG'}]}}}

    def page(self, contract, records, *, total=1, token=None, request_token=None, index=0):
        self.counter += 1
        path = self.raw / f'synthetic-{self.counter}.json'
        payload = {'studies': records, 'totalCount': total}
        if token is not None:
            payload['nextPageToken'] = token
        write_json(path, payload)
        request = frame.page_request(contract, request_token)
        return {'request': request, 'final_url': request['url'], 'http_status': 200, 'attempt': 1,
                'started_at_utc': f'2026-10-23T10:{index:02d}:01+00:00',
                'ended_at_utc': f'2026-10-23T10:{index:02d}:02+00:00',
                'body': {'path': path.name, 'bytes': path.stat().st_size, 'sha256': sha256_file(path)}}

    def validate(self, contract, pages, **kwargs):
        options = dict(capture_root=self.raw, version_before=VERSION, version_after=VERSION)
        options.update(kwargs)
        return frame.validate_frame(contract, pages, **options)

    def test_build_pins_actual_schema_and_reserves_non_dispatch_artifacts(self):
        c = self.build()
        self.assertEqual(c, frame.verify_build(self.output))
        self.assertEqual(list(frame.FIELDS), list(c['projection']))
        self.assertEqual('protocolSection.designModule.phases', c['projection']['Phase']['json_path'])
        self.assertFalse(c['source_dispatch_allowed'])
        self.assertFalse(c['transport_qualified'])
        self.assertIsNone(c['clinical_origin_F'])
        self.assertIsNone(c['capture_started_at_utc'])

    def test_request_exact_date_filter_no_clinical_filter_and_only_date_sort(self):
        c = self.build()
        query = parse_qs(urlsplit(c['request']['url']).query)
        self.assertEqual(['AREA[StudyFirstPostDate]RANGE[2026-09-23,2026-10-22]'], query['filter.advanced'])
        self.assertEqual(['StudyFirstPostDate:asc'], query['sort'])
        self.assertEqual([','.join(frame.FIELDS)], query['fields'])
        self.assertEqual({'format', 'filter.advanced', 'fields', 'sort', 'countTotal', 'pageSize'}, set(query))
        self.assertIn('not_live_qualified', c['query_grammar_status'])

    def test_malicious_url_and_query_changes_rejected_even_with_new_self_hash(self):
        c = self.build()
        for mutation in ('url', 'endpoint', 'parameters'):
            bad = copy.deepcopy(c)
            if mutation == 'parameters':
                bad['request'][mutation]['query.outc'] = 'favorable'
            else:
                bad['request'][mutation] = 'https://evil.invalid/api/v2/studies'
            bad['contract_sha256'] = fingerprint({k: v for k, v in bad.items() if k != 'contract_sha256'})
            with self.assertRaises(ContractError):
                frame.page_request(bad)

    def test_opaque_token_is_encoded_without_parameter_injection(self):
        c = self.build()
        token = 'a&query.outc=secret/+?%'
        request = frame.page_request(c, token)
        query = parse_qs(urlsplit(request['url']).query)
        self.assertEqual([token], query['pageToken'])
        self.assertNotIn('query.outc', query)
        for bad in ('', 'x\nheader', 'x' * 2049):
            with self.assertRaises(ContractError):
                frame.page_request(c, bad)

    def test_output_and_parent_path_traversal_fail(self):
        self.output = self.root / frame.OUTPUT_ROOT / 'child' / '..' / 'escape'
        with self.assertRaises(ContractError):
            self.build()
        p = read_json(self.root / frame.PROTOCOL)
        p['parents'][0]['path'] = '../outside'
        write_json(self.root / frame.PROTOCOL, p)
        self.output = self.root / frame.OUTPUT_ROOT / 'clean'
        with self.assertRaises(ContractError):
            self.build()

    def test_future_R_same_day_interval_and_wrong_span_rejected(self):
        for i, changes in enumerate(({'readiness_date': '2026-10-24'},
                                     {'readiness_date': '2026-10-22'},
                                     {'interval_start': '2026-09-24'},
                                     {'interval_start': '2026-09-24', 'interval_end': '2026-10-23'})):
            self.output = self.root / frame.OUTPUT_ROOT / f'invalid-date-{i}'
            with self.assertRaises(ContractError):
                self.build(**changes)

    def test_changed_parent_and_changed_schema_fail_before_request_seal(self):
        p = read_json(self.root / frame.PROTOCOL)
        target = self.root / p['parents'][0]['path']
        target.write_bytes(target.read_bytes() + b'changed')
        with self.assertRaises(ContractError):
            self.build()
        self.assertFalse((self.output / 'request.json').exists())
        target.write_bytes((REPO / p['parents'][0]['path']).read_bytes())
        metadata = self.root / (frame.METADATA + '02-metadata.json')
        metadata.write_bytes(metadata.read_bytes() + b' ')
        self.output = self.root / frame.OUTPUT_ROOT / 'changed-schema'
        with self.assertRaises(ContractError):
            self.build()

    def test_wrong_protocol_digest_and_code_pin_mutation_fail(self):
        with self.assertRaises(ContractError):
            self.build(expected_protocol_sha256='0' * 64)
        self.output = self.root / frame.OUTPUT_ROOT / 'good'
        c = self.build()
        c['code_pins'][0]['sha256'] = '0' * 64
        c['contract_sha256'] = fingerprint({k: v for k, v in c.items() if k != 'contract_sha256'})
        with self.assertRaises(ContractError):
            frame.validate_contract(c)

    def test_concurrent_reservation_allows_one_builder_only(self):
        def attempt(_):
            try:
                self.build()
                return 'built'
            except FileExistsError:
                return 'reserved'
        with ThreadPoolExecutor(max_workers=2) as workers:
            self.assertCountEqual(['built', 'reserved'], list(workers.map(attempt, range(2))))
        frame.verify_build(self.output)

    def test_empty_page_with_token_continues_and_reconciles_total(self):
        c = self.build()
        pages = [self.page(c, [], token='opaque'),
                 self.page(c, [self.record()], request_token='opaque', index=1)]
        result = self.validate(c, pages)
        self.assertEqual(1, result['frame_count'])
        self.assertEqual(['NCT00000001'], result['sample_nct_ids'])
        self.assertFalse(result['transport_qualified'])

    def test_zero_total_complete_empty_frame_and_no_sample(self):
        c = self.build()
        result = self.validate(c, [self.page(c, [], total=0)])
        self.assertEqual([], result['sample_nct_ids'])
        self.assertTrue(result['complete'])

    def test_loop_and_duplicate_ids_stop_without_sample(self):
        c = self.build()
        cases = [[self.page(c, [], total=0, token='loop'),
                  self.page(c, [], total=0, token='loop', request_token='loop', index=1)],
                 [self.page(c, [self.record()], total=2, token='next'),
                  self.page(c, [self.record()], total=2, request_token='next', index=1)]]
        for pages in cases:
            with self.assertRaises(ContractError):
                self.validate(c, pages)

    def test_truncation_count_drift_and_extra_terminal_page_stop(self):
        c = self.build()
        for pages in ([self.page(c, [self.record()], total=2)],
                      [self.page(c, [], total=1, token='more')],
                      [self.page(c, [], total=1, token='more'),
                       self.page(c, [self.record()], total=2, request_token='more', index=1)],
                      [self.page(c, [], total=0), self.page(c, [], total=0, index=1)]):
            with self.assertRaises(ContractError):
                self.validate(c, pages)

    def test_500_cap_is_stop_not_truncation_and_page_size100(self):
        c = self.build()
        for page in (self.page(c, [], total=501),
                     self.page(c, [self.record(i) for i in range(1, 102)], total=101)):
            with self.assertRaises(ContractError):
                self.validate(c, [page])
        pages = [self.page(c, [self.record(i) for i in range(n * 100 + 1, (n + 1) * 100 + 1)],
                           total=500, token=f't{n}' if n < 4 else None,
                           request_token=f't{n-1}' if n else None, index=n) for n in range(5)]
        result = self.validate(c, pages)
        self.assertEqual(500, result['frame_count'])
        self.assertEqual(12, len(result['sample_nct_ids']))

    def test_attempt_and_elapsed_caps_no_retries(self):
        c = self.build()
        page = self.page(c, [], total=0)
        page['attempt'] = 2
        with self.assertRaises(ContractError):
            self.validate(c, [page])
        page['attempt'] = 1
        page['ended_at_utc'] = '2026-10-23T10:10:02+00:00'
        with self.assertRaises(ContractError):
            self.validate(c, [page])
        with self.assertRaises(ContractError):
            self.validate(c, [page] * 11)

    def test_page_byte_cap_and_changed_original_hash_fail(self):
        c = self.build()
        page = self.page(c, [], total=0)
        page['body']['bytes'] = 2097153
        with self.assertRaises(ContractError):
            self.validate(c, [page])
        page = self.page(c, [], total=0)
        (self.raw / page['body']['path']).write_bytes(b'{}')
        with self.assertRaises(ContractError):
            self.validate(c, [page])

    def test_version_drift_and_expired_capture_day_stop(self):
        c = self.build()
        page = self.page(c, [], total=0)
        with self.assertRaises(ContractError):
            self.validate(c, [page], version_after=dict(VERSION, dataTimestamp='changed'))
        page['started_at_utc'] = '2026-10-24T10:00:01Z'
        page['ended_at_utc'] = '2026-10-24T10:00:02Z'
        with self.assertRaises(ContractError):
            self.validate(c, [page])

    def test_hidden_clinical_fields_fail_at_any_depth(self):
        c = self.build()
        for location, key in (('root', 'hasResults'), ('root', 'resultsSection'),
                              ('status', 'whyStopped'), ('design', 'primaryOutcomes'),
                              ('intervention', 'description')):
            row = self.record()
            target = {'root': row, 'status': row['protocolSection']['statusModule'],
                      'design': row['protocolSection']['designModule'],
                      'intervention': row['protocolSection']['armsInterventionsModule']['interventions'][0]}[location]
            target[key] = 'prohibited synthetic content'
            with self.assertRaises(ContractError):
                self.validate(c, [self.page(c, [row])])

    def test_identity_and_first_post_date_integrity_fail(self):
        c = self.build()
        for value in ('nct00000001', 'NCT1', None):
            row = self.record()
            row['protocolSection']['identificationModule']['nctId'] = value
            with self.assertRaises(ContractError):
                self.validate(c, [self.page(c, [row])])
        for value in (None, '2026-09-22', '2026-10-23', '2026-10', '2026-02-30'):
            row = self.record()
            row['protocolSection']['statusModule']['studyFirstPostDateStruct']['date'] = value
            with self.assertRaises(ContractError):
                self.validate(c, [self.page(c, [row])])

    def test_unknown_eligibility_kept_and_known_exclusion_wins(self):
        c = self.build()
        unknown, excluded = self.record(), self.record(2)
        del unknown['protocolSection']['designModule']['designInfo']
        excluded['protocolSection']['designModule']['studyType'] = 'OBSERVATIONAL'
        del excluded['protocolSection']['designModule']['phases']
        result = self.validate(c, [self.page(c, [unknown, excluded], total=2)])
        self.assertEqual(['screen_unknown', 'ineligible'], [x['screen'] for x in result['all_member_ledger']])
        self.assertIn('phase', result['all_member_ledger'][1]['missing_or_conflicting'])
        self.assertEqual(['NCT00000001'], result['sample_nct_ids'])

    def test_phase_combinations_exposures_and_digest_selection(self):
        c = self.build(extra_exposed_ids=['NCT00000001'])
        rows = [self.record(i) for i in range(1, 17)]
        rows[1]['protocolSection']['designModule']['phases'] = ['PHASE3', 'PHASE2']
        rows[2]['protocolSection']['designModule']['phases'] = ['PHASE1', 'PHASE2']
        rows[3]['protocolSection']['designModule']['phases'] = ['PHASE2_PHASE3']
        result = self.validate(c, [self.page(c, rows, total=16)])
        pool = [f'NCT{i:08d}' for i in range(2, 17) if i != 3]
        pool.sort(key=lambda n: (hashlib.sha256((c['protocol']['sha256'] + n).encode()).hexdigest(), n))
        self.assertEqual(pool[:12], result['sample_nct_ids'])
        self.assertTrue(result['all_member_ledger'][0]['exposure_excluded'])
        self.assertEqual('screen_unknown', result['all_member_ledger'][3]['screen'])

    def test_manifest_path_escape_and_response_redirect_rejected(self):
        c = self.build()
        page = self.page(c, [], total=0)
        page['body']['path'] = '../outside.json'
        with self.assertRaises(ContractError):
            self.validate(c, [page])
        page = self.page(c, [], total=0)
        page['final_url'] = 'https://clinicaltrials.gov/api/v2/studies?fields=HasResults'
        with self.assertRaises(ContractError):
            self.validate(c, [page])

    def test_malformed_projection_arrays_and_duplicate_json_keys_fail(self):
        c = self.build()
        row = self.record()
        row['protocolSection']['designModule']['phases'] = 'PHASE2'
        with self.assertRaises(ContractError):
            self.validate(c, [self.page(c, [row])])
        page = self.page(c, [], total=0)
        path = self.raw / page['body']['path']
        path.write_bytes(b'{"studies":[],"totalCount":0,"totalCount":0}')
        page['body'].update(bytes=path.stat().st_size, sha256=sha256_file(path))
        with self.assertRaises(ContractError):
            self.validate(c, [page])

    def test_no_network_dependency_or_live_qualification(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('Network prohibited')):
            c = self.build()
            result = self.validate(c, [self.page(c, [self.record()])])
        self.assertFalse(result['transport_qualified'])
        self.assertFalse(result['clinical_activation'])


if __name__ == '__main__':
    unittest.main()
