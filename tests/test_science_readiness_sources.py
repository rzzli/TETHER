"""Offline fixed-member source acquisition, with independent synthetic origins."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_science_prospective_capacity as fixtures
from tests.prospective_fixtures import archived_json
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, canonical, fingerprint, read_json, sha256_file, write_json
from tools.science import prospective_capacity as capacity
from tools.science import prospective_frame as frame
from tools.science import prospective_transport as transport
from tools.science import readiness_sources as sources

PDF = b'%PDF-1.7\nsynthetic original\n%%EOF\n'


class ReadinessSourcesTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ProspectiveCapacityTests('test_missing_first_count')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.root = fixture, fixture.root
        self.clock = patch.object(sources, '_now', return_value=fixtures.NOW)
        self.clock.start(); self.addCleanup(self.clock.stop)
        no_live = patch.object(transport.StdlibClient, 'stream', side_effect=AssertionError('actual HTTP forbidden'))
        no_live.start(); self.addCleanup(no_live.stop)
        rows = [fixture.record(n) for n in range(1, 13)]
        del rows[-1]['protocolSection']['designModule']['phases']
        pages = [fixture.page(rows[i:i+1], 12, str(i+1)) for i in range(8)]
        pages.append(fixture.page(rows[8:], 12))
        receipt = fixture.capture(pages)
        audit = fixture.audit()
        self.prior_output = fixture.output
        pin = frame._pin
        proof = self.root / 'source-membership'
        journal = RunJournal(proof, kind='build')
        members, origins = [], []
        for order, nct in enumerate(audit['candidate_nct_ids'], 1):
            for part in receipt['pages']:
                raw = fixture.output / part['body']['path']
                studies = json.loads(raw.read_bytes())['studies']
                found = [(i, row) for i, row in enumerate(studies) if row['protocolSection']['identificationModule']['nctId'] == nct]
                if found:
                    index, row = found[0]
                    locator = {'raw_body': pin(raw), 'json_pointer': '/studies/'+str(index), 'row_sha256': fingerprint(row)}
                    screen = next(r for r in audit['all_member_ledger'] if r['nct_id'] == nct)
                    members.append({'order': order, 'nct_id': nct, 'screen': screen, 'source_locator': locator})
                    origins.append({'nct_id': nct, 'source_locator': locator, 'record': row})
                    break
        self.members, self.origins = members, origins
        review = self.root / 'independent-review.json'
        write_json(review, {'status': 'passed_independent_raw_reconstruction_before_membership', 'synthetic': True})
        frame_audit = self.root / 'frame-audit.json'
        write_json(frame_audit, {'execution_manifest': pin(fixture.output / 'execution.json'),
            'capture_receipt': pin(fixture.output / 'receipt.json'), 'capture_journal': pin(fixture.output / 'journal.jsonl')})
        membership = dict(sources.BOUNDARIES, status='readiness_membership_sealed', members=members,
            sampling_seed_sha256=capacity.SEED, tether_cases_created=0,
            frame_audit=pin(frame_audit), capture_receipt=pin(fixture.output / 'receipt.json'), independent_review=pin(review))
        write_json(proof / 'membership.json', membership)
        write_json(proof / 'origin-metadata.json', {'role': 'evaluation_only', 'records': origins})
        journal.append('build_completed', membership=pin(proof / 'membership.json'),
            origin_metadata=pin(proof / 'origin-metadata.json'), source_rule_queries=0)
        journal.close()
        freeze = {'schema_version': 1, 'status': 'fixed_twelve_readiness_members_sealed_before_source_rule_queries',
            'membership': pin(proof / 'membership.json'), 'origin_metadata': pin(proof / 'origin-metadata.json'),
            'journal': pin(proof / 'journal.jsonl'), 'independent_review': pin(review), 'members': 12,
            'source_rule_queries': 0, 'clinical_activation': False, 'model_calls': 0}
        self.freeze_path = self.root / sources.MEMBERSHIP_FREEZE
        self.freeze_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.freeze_path, freeze)
        self.protocol_path = self.root / sources.PROTOCOL
        protocol = archived_json(sources.PROTOCOL)
        protocol['base_protocol'] = dict(pin(self.root / frame.PROTOCOL), path=frame.PROTOCOL)
        protocol['membership_freeze'] = dict(pin(self.freeze_path), path=sources.MEMBERSHIP_FREEZE)
        write_json(self.protocol_path, protocol)
        self.output = self.root / frame.OUTPUT_ROOT / 'readiness-sources'
        self.fields = read_json(self.root / frame.PROTOCOL)['request_contract']['exact_post_membership_projection']
        self.projection = read_json(self.root / frame.PROTOCOL)['request_contract']['frozen_schema_verified_post_membership_projection']

    def listing(self, index, docs=None):
        nct = self.members[index]['nct_id']
        result = {'protocolSection': {'identificationModule': {'nctId': nct},
            'designModule': {'phases': self.origins[index]['record']['protocolSection']['designModule'].get('phases')}}}
        if docs is not None:
            result['documentSection'] = {'largeDocumentModule': {'largeDocs': docs}}
        return result

    def doc(self, filename='Prot_SAP_001.pdf', **extra):
        return dict({'filename': filename, 'hasProtocol': True, 'hasSap': True, 'hasIcf': False,
                     'typeAbbrev': 'Prot_SAP', 'size': len(PDF)}, **extra)

    def responses(self):
        return [self.listing(i) for i in range(12)]

    def prepare(self, output=None):
        output = output or self.output
        sources.prepare_execution(self.root, output, expected_protocol_sha256=sha256_file(self.protocol_path))
        return sha256_file(output / 'execution.json')

    def capture(self, responses=None):
        self.digest = self.prepare()
        self.client = fixtures.SyntheticClient(responses if responses is not None else self.responses())
        return sources.execute(self.output, expected_manifest_sha256=self.digest, client=self.client)

    def audit(self):
        return sources.audit_packets(self.output, expected_manifest_sha256=self.digest)

    def binary(self, request, raw=PDF, status=200, headers=None, url=None):
        return [('headers', {'status': status, 'final_url': url or request['url'], 'headers': headers or {}}), ('body', raw)]

    def test_fixed12_no_replacement_including_unknown(self):
        result = self.capture()
        self.assertEqual([m['nct_id'] for m in self.members], [p['nct_id'] for p in result['packets']])
        self.assertEqual(1, sum(p['screen']['screen'] == 'screen_unknown' for p in result['packets']))
        self.assertEqual(23, result['amended_package_source_attempts'])
        self.assertEqual(12, self.audit()['source_attempts'])
        self.assertFalse(result['boundaries']['agent_visible'])
        self.assertEqual('unknown', self.audit()['scientific_readiness'])

    def test_combined_original_candidate_and_steward_pending(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc()])
        responses.insert(1, self.binary(sources.pdf_request(self.members[0]['nct_id'], 'Prot_SAP_001.pdf')))
        result = self.capture(responses)
        packet = result['packets'][0]
        self.assertEqual('retained_candidate_pending_steward_review', packet['pdfs'][0]['status'])
        self.assertFalse(packet['pdfs'][0]['authenticity_qualified'])
        self.assertEqual('pending', packet['steward_review'])
        self.assertEqual(13, self.audit()['source_attempts'])

    def test_free_text_is_evaluation_only(self):
        responses = self.responses(); responses[0]['protocolSection']['eligibilityModule'] = {'eligibilityCriteria': 'Clinical narrative pending review'}
        result = self.capture(responses)
        self.assertIn('Clinical narrative', json.dumps(result['packets'][0]['metadata_evaluation_only']))
        self.assertFalse(result['packets'][0]['agent_visible'])
        self.assertEqual('pending', result['packets'][0]['steward_review'])
        self.audit()

    def test_http404_continues_fixed_others(self):
        responses = self.responses(); responses[0] = self.binary(sources.listing_request(self.members[0]['nct_id'], self.fields), b'not found', 404)
        result = self.capture(responses)
        self.assertEqual('access_failed', result['packets'][0]['status'])
        self.assertEqual(12, len(self.client.requests)); self.audit()

    def test_missing_identity_case_hold(self):
        responses = self.responses(); del responses[0]['protocolSection']['identificationModule']['nctId']
        result = self.capture(responses)
        self.assertEqual('identity_hold', result['packets'][0]['status']); self.audit()

    def test_alias_cannot_replace_fixed_member(self):
        responses = self.responses(); responses[0]['protocolSection']['identificationModule']['nctId'] = 'NCT99999999'
        result = self.capture(responses)
        self.assertEqual('identity_hold', result['packets'][0]['status']); self.audit()

    def test_phase_drift_hold(self):
        responses = self.responses(); responses[0]['protocolSection']['designModule']['phases'] = ['PHASE4']
        result = self.capture(responses)
        self.assertEqual('phase_drift_hold', result['packets'][0]['status']); self.audit()

    def test_result_branch_global_quarantine_and_unattempted(self):
        responses = self.responses(); responses[0]['resultsSection'] = {'outcomeMeasuresModule': {}}
        with self.assertRaises(ContractError): self.capture(responses)
        self.assertEqual(1, len(self.client.requests))
        partial = read_json(self.output / 'partial-packets.json')
        self.assertEqual([m['nct_id'] for m in self.members[1:]], partial['unattempted_members'])
        self.assertFalse(sources.inspect_execution(self.output)['complete_packets_present'])

    def test_unrequested_status_global_quarantine(self):
        responses = self.responses(); responses[0]['protocolSection']['statusModule'] = {'overallStatus': 'COMPLETED'}
        with self.assertRaises(ContractError): self.capture(responses)

    def test_boolean_type_strict(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc(hasProtocol='true')])
        with self.assertRaises(ContractError): self.capture(responses)

    def test_boolean_nct_not_identifier(self):
        responses = self.responses(); responses[0]['protocolSection']['identificationModule']['nctId'] = True
        with self.assertRaises(ContractError): self.capture(responses)

    def test_null_missing_leaves_allowed(self):
        responses = self.responses(); responses[0]['protocolSection']['conditionsModule'] = {'conditions': None}
        responses[1]['protocolSection']['conditionsModule'] = {'conditions': []}
        self.capture(responses); self.audit()

    def test_text_and_object_arrays_strict(self):
        for branch in ({'conditionsModule': {'conditions': [1]}}, {'armsInterventionsModule': {'armGroups': ['bad']}}):
            value = self.listing(0); value['protocolSection'].update(branch)
            with self.assertRaises(ContractError): sources.validate_listing(value, self.projection)

    def test_document_long_rejects_bool(self):
        value = self.listing(0, [self.doc(size=True)])
        with self.assertRaises(ContractError): sources.validate_listing(value, self.projection)

    def test_pdf_route_rejects_unsafe_filenames(self):
        for filename in ('../x.pdf', 'x.pdf?url=evil', 'https://evil.test/a.pdf', 'x%2F.pdf', 'x\\bad.pdf'):
            with self.assertRaises(ContractError): sources.pdf_request(self.members[0]['nct_id'], filename)

    def test_product_flags_type_tokens_and_filename_not_proof(self):
        nct = self.members[0]['nct_id']
        docs = [self.doc(hasProtocol=None, hasSap=None, typeAbbrev='Prot_SAP')]
        self.assertEqual(1, len(sources.select_documents(self.listing(0, docs), nct)['selected']))
        docs = [{'filename': 'Prot_SAP.pdf', 'label': 'protocol SAP', 'hasIcf': True, 'typeAbbrev': 'ICF'}]
        self.assertEqual([], sources.select_documents(self.listing(0, docs), nct)['selected'])

    def test_explicit_flag_type_conflict_no_pdf(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc(hasProtocol=False)])
        result = self.capture(responses)
        self.assertEqual('insufficient_under_cap_or_metadata', result['packets'][0]['status'])
        self.assertEqual(12, len(self.client.requests)); self.audit()

    def test_more_than_two_versions_no_arbitrary_latest(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc('Prot_SAP_'+str(i)+'.pdf') for i in range(3)])
        result = self.capture(responses)
        self.assertEqual([], result['packets'][0]['pdfs']); self.audit()

    def test_duplicate_identical_dedup_conflicting_hold(self):
        nct = self.members[0]['nct_id']; doc = self.doc()
        self.assertEqual(1, len(sources.select_documents(self.listing(0, [doc, copy.deepcopy(doc)]), nct)['selected']))
        self.assertEqual([], sources.select_documents(self.listing(0, [doc, dict(doc, size=1)]), nct)['selected'])

    def test_two_originals_protocol_before_sap(self):
        nct = self.members[0]['nct_id']
        docs = [self.doc('Sap.pdf', hasProtocol=False, typeAbbrev='SAP'), self.doc('Prot.pdf', hasSap=False, typeAbbrev='Prot')]
        selected = sources.select_documents(self.listing(0, docs), nct)['selected']
        self.assertEqual(['Prot.pdf', 'Sap.pdf'], [r['filename'] for r in selected])

    def test_pdf_signature_qc_hold(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc()])
        responses.insert(1, self.binary(sources.pdf_request(self.members[0]['nct_id'], 'Prot_SAP_001.pdf'), b'<html>not PDF</html>'))
        result = self.capture(responses)
        self.assertEqual('pdf_qc_hold', result['packets'][0]['pdfs'][0]['status']); self.audit()

    def test_reported_oversize_no_download(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc(size=17*1024*1024)])
        result = self.capture(responses)
        self.assertEqual('oversize_reported_not_requested', result['packets'][0]['pdfs'][0]['status'])
        self.assertEqual(12, len(self.client.requests)); self.audit()

    def test_redirect_not_followed(self):
        responses = self.responses(); request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        responses[0] = self.binary(request, b'', 302, {'Location': 'https://evil.invalid/'})
        self.capture(responses)
        self.assertEqual(12, len(self.client.requests)); self.audit()

    def test_final_url_mismatch_case_hold(self):
        responses = self.responses(); request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        responses[0] = self.binary(request, b'{}', url='https://evil.invalid/')
        result = self.capture(responses)
        self.assertEqual('access_failed', result['packets'][0]['status']); self.audit()

    def test_timeout_case_hold_no_retry(self):
        responses = self.responses(); responses[0] = TimeoutError()
        self.capture(responses); self.assertEqual(12, len(self.client.requests)); self.audit()

    def test_interrupt_stops_durable(self):
        responses = self.responses(); responses[0] = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.capture(responses)
        self.assertEqual([], sources.inspect_execution(self.output)['unresolved_attempts'])
        self.assertEqual(1, len(self.client.requests))

    def test_semantic_cross_manifest_no_retry(self):
        self.capture()
        other = self.root / frame.OUTPUT_ROOT / 'duplicate-source-job'
        digest = self.prepare(other); client = fixtures.SyntheticClient([])
        with self.assertRaises(FileExistsError): sources.execute(other, expected_manifest_sha256=digest, client=client)
        self.assertEqual([], client.requests)

    def test_output_escape_before_writes(self):
        target = self.root / 'escape'
        with self.assertRaises(ContractError): self.prepare(target)
        self.assertFalse(target.exists())

    def test_raw_body_mutation_audit_denied(self):
        self.capture(); (self.output / '00-response.bin').write_bytes(b'{}')
        with self.assertRaises(ContractError): self.audit()

    def test_manifest_external_digest_denied(self):
        digest = self.prepare(); path = self.output / 'execution.json'
        value = read_json(path); value['members'].reverse(); write_json(path, value)
        with self.assertRaises(ContractError): sources.execute(self.output, expected_manifest_sha256=digest, client=fixtures.SyntheticClient([]))
        self.assertFalse((self.output / 'execution-claimed.json').exists())

    def test_archive_omission_resealed_denied(self):
        self.prepare(); path = self.output / 'execution.json'; value = read_json(path)
        value['archives'].pop(); value.pop('manifest_sha256'); value['manifest_sha256'] = fingerprint(value); write_json(path, value)
        with self.assertRaises(ContractError): sources.execute(self.output, expected_manifest_sha256=sha256_file(path), client=fixtures.SyntheticClient([]))
        self.assertFalse((self.output / 'execution-claimed.json').exists())

    def test_protocol_scope_override_denied(self):
        value = read_json(self.protocol_path); value['technical_scope']['outcome_queries'] = 1; write_json(self.protocol_path, value)
        with self.assertRaises(ContractError): self.prepare()

    def test_partial_content_length_hold(self):
        responses = self.responses(); request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        responses[0] = self.binary(request, b'{', headers={'Content-Length': '100'})
        self.capture(responses); self.audit()

    def test_listing_oversize_retained_and_case_hold(self):
        responses = self.responses(); request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        responses[0] = self.binary(request, b'x' * (sources.CAPS['max_bytes_per_listing'] + 1))
        result = self.capture(responses)
        self.assertEqual('oversize', result['packets'][0]['listing']['hold_reason'])
        self.assertEqual(2*1024*1024, (self.output / '00-response.bin').stat().st_size)
        self.audit()

    def test_pdf_stream_16MiB_cap(self):
        responses = self.responses(); responses[0] = self.listing(0, [self.doc(size=None)])
        responses.insert(1, self.binary(sources.pdf_request(self.members[0]['nct_id'], 'Prot_SAP_001.pdf'),
            b'%PDF-' + b'x' * sources.CAPS['max_bytes_per_pdf']))
        result = self.capture(responses)
        self.assertEqual('oversize', result['packets'][0]['pdfs'][0]['status'])
        self.assertEqual(16*1024*1024, (self.output / '01-response.bin').stat().st_size)
        self.audit()

    def test_global_byte_cap_durable_attempt(self):
        output = self.root / frame.OUTPUT_ROOT / 'direct-global-budget'
        journal = RunJournal(output); self.addCleanup(journal.close)
        request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        client = fixtures.SyntheticClient([self.binary(request, b'xxx')])
        with self.assertRaises(ContractError): sources._attempt(journal, output, request, client, 0, float('inf'), [2])
        events = read_chain(output / 'journal.jsonl')
        self.assertEqual('global_byte_cap', events[-1]['details']['hold_reason'])
        self.assertEqual(2, (output / '00-response.bin').stat().st_size)

    def test_total_request_cap_before_dispatch(self):
        output = self.root / frame.OUTPUT_ROOT / 'direct-request-cap'
        journal = RunJournal(output); self.addCleanup(journal.close)
        client = fixtures.SyntheticClient([])
        request = sources.listing_request(self.members[0]['nct_id'], self.fields)
        with self.assertRaises(ContractError): sources._attempt(journal, output, request, client, 37, float('inf'), [100])
        self.assertEqual([], client.requests)

    def test_hard_elapsed_timeout_and_global_deadline(self):
        for deadline in (1000, 10):
            output = self.root / frame.OUTPUT_ROOT / ('direct-elapsed-'+str(deadline))
            journal = RunJournal(output); self.addCleanup(journal.close)
            tick = [0]
            request = sources.listing_request(self.members[0]['nct_id'], self.fields)
            class Delayed:
                evidence_kind = 'synthetic'
                def stream(self, request, *, deadline):
                    tick[0] = 121
                    yield 'headers', {'status': 200, 'final_url': request['url'], 'headers': {}}
            with patch.object(sources.time, 'monotonic', side_effect=lambda: tick[0]):
                if deadline == 10:
                    with self.assertRaises(ContractError): sources._attempt(journal, output, request, Delayed(), 0, deadline, [100])
                else:
                    result = sources._attempt(journal, output, request, Delayed(), 0, deadline, [100])
                    self.assertEqual('timeout', result['hold_reason'])
            self.assertEqual('attempt_terminal', read_chain(output / 'journal.jsonl')[-1]['event'])

    def test_concurrent_one_job_only(self):
        from concurrent.futures import ThreadPoolExecutor
        digest = self.prepare()
        clients = [fixtures.SyntheticClient(self.responses()) for _ in range(2)]
        def run(client):
            try:
                return sources.execute(self.output, expected_manifest_sha256=digest, client=client)
            except (ContractError, FileExistsError):
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, clients))
        self.assertEqual(1, sum(r is not None for r in results))
        self.assertEqual(12, sum(len(c.requests) for c in clients))
        self.digest = digest; self.audit()

    def test_expired_R_no_claim_and_later_offline_replay(self):
        from datetime import timedelta
        self.capture()
        with patch.object(sources, '_now', return_value=fixtures.NOW+timedelta(days=1)):
            self.audit()
        other = self.root / frame.OUTPUT_ROOT / 'expired-dispatch'
        digest = self.prepare(other)
        with patch.object(sources, '_now', return_value=fixtures.NOW+timedelta(days=1)):
            with self.assertRaises(ContractError):
                sources.execute(other, expected_manifest_sha256=digest, client=fixtures.SyntheticClient([]))
        self.assertFalse((other / 'execution-claimed.json').exists())

    def test_missing_product_metadata_unknown_not_absence(self):
        responses = self.responses(); responses[0] = self.listing(0, [{'filename': 'Prot_SAP.pdf'}])
        result = self.capture(responses)
        self.assertEqual('insufficient_under_cap_or_metadata', result['packets'][0]['status'])
        self.assertEqual([], result['packets'][0]['pdfs']); self.audit()


if __name__ == '__main__':
    unittest.main()
