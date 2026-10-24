"""Invented provider-shaped originals; no real biological judgments or inference."""
import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from asof.agents import ExtractiveBackend
from asof.artifacts import write_run
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.journal import read_chain
from asof.serde import ContractError, decode, fingerprint, read_json, sha256_file, write_json
from asof.workflow import run_workflow
from tests import test_v02_ingest as fixtures
from tools.science.run_comparison import pin
from tools.science.t6_claim_audit import HYPOTHESIS_FIELDS
from tools.science.t6_dossier_binding import (audit_bound_claims, bind_manifest,
                                             build_binding, verify_binding, _dossier_bytes)


@unittest.skipUnless(importlib.util.find_spec('pyarrow'), 'install the pinned ingest extra')
class DossierSourceBindingTests(unittest.TestCase):
    setUp = fixtures.IngestTests.setUp
    tearDown = fixtures.IngestTests.tearDown
    save_manifest = fixtures.IngestTests.save_manifest
    receipt = fixtures.IngestTests.receipt
    evidence = fixtures.IngestTests.evidence

    def prepare(self):
        output, report = fixtures.IngestTests.build(self)
        self.case_folder = output / report['cases'][0]['case_id']
        case = decode(Case, read_json(self.case_folder / 'case.json'))
        store = load_snapshot(self.case_folder / 'snapshot.json', case, self.catalog)
        self.run = self.root / 'run'
        result = run_workflow(case, store, ExtractiveBackend())
        self.digest = write_run(self.run, result, store, None)
        self.proof = pin(self.run / 'receipt.json')
        self.output = self.root / 'binding'
        return case

    def bind(self):
        report = build_binding(self.proof, self.output, approved_roots=[self.root])
        self.binding_proof = report['binding']
        self.binding = read_json(Path(self.binding_proof['path']))
        return report

    def inventory(self):
        unit = self.binding['source_units'][0]
        start = unit['quoted_span']['start'] + 2
        end = unit['quoted_span']['end']
        self.inventory_value = dict(schema_version=1, role='evaluation_only',
            dossier_sha256=self.binding['dossier']['sha256'],
            dossier_binding_sha256=fingerprint(self.binding), question=self.binding['question'],
            atomization_status='reviewed_complete', atomizer_id='synthetic-fixture-reviewer',
            claims=[dict(claim_id='atomic-fixture-1', statement=unit['statement'],
                         kind='resource_observation', question_sha256=fingerprint(self.binding['question']),
                         atomicity_attested=True, cited_source_ids=[unit['observation_id']],
                         dossier_spans=[dict(start=start, end=end)])])
        return self.inventory_value

    def test_actual_format_binding_replays_sources_and_preserves_draft_scope(self):
        self.prepare()
        report = self.bind()
        self.assertEqual(report['source_units'], 1)
        self.assertFalse(report['atomic_inventory_complete'])
        self.assertEqual(self.binding['scientific_validity'], 'not_established')
        self.assertEqual(verify_binding(self.binding_proof, approved_roots=[self.root]), self.binding)
        self.assertEqual(set(self.binding['question']), HYPOTHESIS_FIELDS)
        self.assertEqual(read_chain(self.output / 'journal.jsonl')[-1]['event'], 'build_completed')

    def test_multiline_source_quote_preserves_native_line_endings(self):
        path = self.raw / 'disease.parquet'
        rows = self.pq.read_table(path).to_pylist()
        for row in rows:
            if row['id'] == 'EFO_0003060':
                row['name'] += '\nFictional second line'
        self.pq.write_table(self.pa.Table.from_pylist(rows), path)
        self.receipt(self.entries[1])
        self.prepare()
        native = (self.run / 'dossier.md').read_bytes().replace(b'\r\n', b'\n')
        receipt = read_json(self.run / 'receipt.json')
        for name, newline in [('LF', b'\n'), ('CRLF', b'\r\n')]:
            (self.run / 'dossier.md').write_bytes(native.replace(b'\n', newline))
            receipt['outputs']['dossier.md'] = sha256_file(self.run / 'dossier.md')
            write_json(self.run / 'receipt.json', receipt)
            self.proof = pin(self.run / 'receipt.json')
            self.output = self.root / ('binding-' + name)
            self.bind()
            self.assertIn('\n', self.binding['source_units'][0]['statement'])

    def test_utf8_span_cannot_cut_a_character(self):
        path = self.raw / 'disease.parquet'
        rows = self.pq.read_table(path).to_pylist()
        for row in rows:
            if row['id'] == 'EFO_0003060':
                row['name'] += ' \u03b1'
        self.pq.write_table(self.pa.Table.from_pylist(rows), path)
        self.receipt(self.entries[1])
        self.prepare(); self.bind(); manifest = self.inventory()
        offset = (self.run / 'dossier.md').read_bytes().index('\u03b1'.encode('utf-8'))
        manifest['claims'][0].update(statement='x', dossier_spans=[dict(start=offset + 1, end=offset + 2)])
        with self.assertRaisesRegex(ContractError, 'cuts a UTF-8 character'):
            bind_manifest(manifest, self.binding)

    def test_actual_dossier_read_is_bounded_even_if_a_file_grows(self):
        fake = SimpleNamespace(open=lambda _: io.BytesIO(b'x' * 17))
        with patch('tools.science.t6_dossier_binding.MAX_SOURCE_BYTES', 16):
            with self.assertRaisesRegex(ContractError, 'bounded audit input size'):
                _dossier_bytes(fake)

    def test_legacy_receipts_do_not_acquire_v2_scientific_guarantees(self):
        self.prepare()
        receipt = read_json(self.run / 'receipt.json')
        receipt['schema_version'] = 1
        write_json(self.run / 'receipt.json', receipt)
        with self.assertRaisesRegex(ContractError, 'v1 remains archival'):
            build_binding(pin(self.run / 'receipt.json'), self.output, approved_roots=[self.root])

    def test_claim_text_and_question_must_match_actual_dossier_bytes(self):
        self.prepare(); self.bind(); manifest = self.inventory()
        bind_manifest(manifest, self.binding)
        for key, value in [('statement', 'Invented clinical efficacy statement.'),
                           ('dossier_spans', [dict(start=0, end=3)]),
                           ('dossier_spans', [dict(start=True, end=3)])]:
            changed = copy.deepcopy(manifest)
            changed['claims'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                bind_manifest(changed, self.binding)
        changed = copy.deepcopy(manifest)
        changed['question']['intended_action'] = 'activate'
        changed['claims'][0]['question_sha256'] = fingerprint(changed['question'])
        with self.assertRaises(ContractError):
            bind_manifest(changed, self.binding)

    def test_unselected_or_invented_section_citations_fail(self):
        self.prepare(); self.bind(); manifest = self.inventory()
        manifest['claims'][0]['cited_source_ids'] = ['foreign']
        with self.assertRaises(ContractError):
            bind_manifest(manifest, self.binding)
        manifest = self.inventory()
        statement = 'Probability withheld'
        body = (self.run / 'dossier.md').read_bytes()
        start = body.index(statement.encode())
        manifest['claims'][0].update(statement=statement,
            dossier_spans=[dict(start=start, end=start + len(statement))])
        with self.assertRaisesRegex(ContractError, 'differ from this actual dossier section'):
            bind_manifest(manifest, self.binding)
        manifest['claims'][0]['cited_source_ids'] = []
        bind_manifest(manifest, self.binding)  # Uncited text stays in the denominator.
        manifest = self.inventory()
        manifest['claims'][0]['cited_source_ids'] = []
        with self.assertRaisesRegex(ContractError, 'differ from this actual dossier section'):
            bind_manifest(manifest, self.binding)

    def test_noncontiguous_or_duplicate_pieces_cannot_manufacture_a_claim(self):
        self.prepare(); self.bind(); manifest = self.inventory()
        manifest['claims'][0]['dossier_spans'] *= 2
        with self.assertRaises(ContractError):
            bind_manifest(manifest, self.binding)

    def test_changed_binding_cannot_substitute_for_original_replay(self):
        self.prepare(); self.bind()
        changed = copy.deepcopy(self.binding)
        changed['source_units'][0]['source_audit']['projected_original_row']['score'] = 1
        target = self.root / 'forged-binding.json'
        write_json(target, changed)
        with self.assertRaisesRegex(ContractError, 'binding replay differs'):
            verify_binding(pin(target), approved_roots=[self.root])

    def test_changed_original_receipt_and_mapping_are_rejected(self):
        self.prepare(); self.bind()
        evidence = next(p for p in self.binding['source_proofs'] if p['dataset_id'] == 'ot_evidence')
        receipt = Path(evidence['raw_root']) / evidence['receipt_path']
        for path in (receipt, self.case_folder / 'identifier-validation.json'):
            old = path.read_bytes()
            path.write_text('{}', encoding='utf-8')
            with self.subTest(path=path), self.assertRaises((ContractError, KeyError)):
                verify_binding(self.binding_proof, approved_roots=[self.root])
            path.write_bytes(old)

    def test_transport_receipt_rewrite_does_not_replace_archived_parent(self):
        self.prepare(); self.bind()
        (self.raw / 'evidence.parquet.receipt.json').write_text('{}', encoding='utf-8')
        verify_binding(self.binding_proof, approved_roots=[self.root])

    def test_original_parquet_drift_is_rejected(self):
        self.prepare(); self.bind()
        with (self.raw / 'evidence.parquet').open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaises(ContractError):
            verify_binding(self.binding_proof, approved_roots=[self.root])

    def test_output_cannot_modify_sealed_run_inventory(self):
        self.prepare()
        with self.assertRaisesRegex(ContractError, 'outside the sealed run'):
            build_binding(self.proof, self.run / 'new-output', approved_roots=[self.root])
        self.assertFalse((self.run / 'new-output').exists())

    def test_write_failure_keeps_failed_journal_and_no_success_report(self):
        self.prepare()
        with patch('tools.science.t6_dossier_binding.write_json', side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):
                self.bind()
        self.assertEqual(read_chain(self.output / 'journal.jsonl')[-1]['event'], 'build_failed')
        self.assertFalse((self.output / 'report.json').exists())

    def test_resealed_dossier_quote_and_citation_drift_are_detected(self):
        self.prepare()
        receipt = read_json(self.run / 'receipt.json')
        original = (self.run / 'dossier.md').read_bytes()
        for before, after in [(b'Open Targets', b'Invented!!!'), (b' observation ot25:', b' observation fake:')]:
            changed = original.replace(before, after, 1)
            self.assertNotEqual(changed, original)
            (self.run / 'dossier.md').write_bytes(changed)
            receipt['outputs']['dossier.md'] = sha256_file(self.run / 'dossier.md')
            write_json(self.run / 'receipt.json', receipt)
            with self.subTest(before=before), self.assertRaises(ContractError):
                build_binding(pin(self.run / 'receipt.json'), self.root / ('bad-' + str(len(after))),
                              approved_roots=[self.root])

    def test_concurrent_output_reservation_allows_only_one_builder(self):
        self.prepare()
        def attempt():
            try:
                return build_binding(self.proof, self.output, approved_roots=[self.root])['status']
            except FileExistsError:
                return 'already_reserved'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(results, ['source_inclusive_dossier_binding_completed', 'already_reserved'])

    def test_oversized_binding_fails_without_dropping_rows(self):
        self.prepare()
        with patch('tools.science.t6_dossier_binding.canonical', return_value=b'x' * (64 * 1024 * 1024 + 1)):
            with self.assertRaisesRegex(ContractError, 'no rows dropped'):
                self.bind()
        self.assertEqual(read_chain(self.output / 'journal.jsonl')[-1]['event'], 'build_failed')

    def test_changed_dossier_or_receipt_does_not_replay(self):
        self.prepare(); self.bind()
        for path in (self.run / 'dossier.md', self.run / 'receipt.json'):
            old = path.read_bytes()
            path.write_bytes(old + b' ')
            with self.subTest(path=path), self.assertRaises(ContractError):
                verify_binding(self.binding_proof, approved_roots=[self.root])
            path.write_bytes(old)

    def test_approved_roots_apply_before_original_reads(self):
        self.prepare()
        with patch('tools.science.t6_dossier_binding.verify_run') as verify:
            with self.assertRaises(ContractError):
                build_binding(self.proof, self.output, approved_roots=[self.run])
            verify.assert_not_called()
        self.assertEqual(read_chain(self.output / 'journal.jsonl')[-1]['event'], 'build_failed')

    def test_existing_output_cannot_be_overwritten_or_resumed(self):
        self.prepare(); self.bind()
        original = (self.output / 'report.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.bind()
        self.assertEqual(original, (self.output / 'report.json').read_bytes())

    def test_interrupt_preserves_terminal_journal(self):
        self.prepare()
        with patch('tools.science.t6_dossier_binding._collect', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                build_binding(self.proof, self.output, approved_roots=[self.root])
        self.assertEqual(read_chain(self.output / 'journal.jsonl')[-1]['event'], 'build_interrupted')

    def test_bound_review_uses_original_parquet_without_json_extract_substitution(self):
        self.prepare(); self.bind(); manifest = self.inventory()
        sources = [dict(source_id=u['observation_id'], format='verified_opentargets_parquet',
                        source_audit=u['source_audit']) for u in self.binding['source_units']]
        review = dict(schema_version=1, role='evaluation_only', reviewer_id='fixture-reviewer-B',
            review_mode='blinded_source_review', therapeutic_truth='not_established',
            claims_sha256=fingerprint(manifest), sources_sha256=fingerprint(sources),
            claims=[dict(claim_id=manifest['claims'][0]['claim_id'], entailment='supported',
                         applicability='uncertain', citation_status='supported', uncertainty='high',
                         evidence_source_ids=manifest['claims'][0]['cited_source_ids'],
                         reason='Invented fixture annotation only; no efficacy inference.')])
        result = audit_bound_claims(manifest, review, self.binding_proof, approved_roots=[self.root])
        self.assertTrue(result['original_source_replay'])
        self.assertTrue(result['dossier_span_binding'])
        self.assertEqual(result['therapeutic_truth'], 'not_established')
        self.assertEqual(result['entailment']['supported'], 1)


if __name__ == '__main__':
    unittest.main()
