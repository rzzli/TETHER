"""End-to-end source grants, receipts, mappings and durable three-view builds."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain, inspect_run
from tether_engine.serde import ContractError, canonical, fingerprint, read_json
from tools.science.research_build import build, pipeline_code
from tools.science.temporal_inventory import _schema_fields
from tests.research_fixtures import ResearchMappingFixture


class ResearchBuildTests(unittest.TestCase):
    def setUp(self):
        if importlib.util.find_spec('pyarrow') is None:
            self.skipTest('install the ingest extra for source-audit tests')
        import pyarrow as pa
        import pyarrow.parquet as pq
        mapping = ResearchMappingFixture(); mapping.prepare(self.addCleanup)
        self.root = mapping.root; self.mapping = mapping
        self.files = []; metadata = []
        for release, dates in (('24.09', ['2024-06-01']), ('25.09', ['2024-06-01', '2026-01-01'])):
            rows = [dict(id='row-'+str(i), targetId='targets-1', diseaseId='diseases-1',
                         datasourceId='gene_burden', datatypeId='genetic_association', publicationDate=date,
                         score=1.0, clinicalPhase=4) for i, date in enumerate(dates)]
            path = self.root/('evidence-'+release+'.parquet')
            pq.write_table(pa.Table.from_pylist(rows), path)
            raw = path.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
            directory = 'output/etl/parquet/evidence/' if release == '24.09' else 'output/evidence/'
            url = 'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/'+release+'/'+directory+'sourceId=gene_burden/part-fixture.parquet'
            relative = release+'/'+directory+'sourceId=gene_burden/part-fixture.parquet'
            receipt = dict(status='completed', receipt_id='receipt-'+release, dataset_id='ot_evidence',
                           release_id=release, relative_path=relative, url=url, sha256=digest, bytes=len(raw),
                           completed_at_utc='2026-11-01T00:00:00Z', role='evaluation_only' if release == '24.09' else None)
            rp = self.root/('receipt-'+release+'.json'); rp.write_bytes(canonical(receipt))
            item = dict(path=str(path), sha256=digest, bytes=len(raw), release=release, source='gene_burden',
                        receipt_path=str(rp), receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),
                        receipt_role=receipt['role'], url=url, relative_path=relative,
                        publisher_algorithm='sha256', publisher_digest=digest,
                        receipt_id=receipt['receipt_id'], dataset_id='ot_evidence',
                        schema_sha256=fingerprint(_schema_fields(pa.Table.from_pylist(rows).schema)),
                        footer_rows=len(rows), footer_row_groups=1)
            self.files.append(item)
            metadata.append(dict(path=str(rp), sha256=item['receipt_sha256'], bytes=rp.stat().st_size))
        screen = self.save('screen.json', dict(files=self.files, metadata_pins=metadata))
        catalog = self.save('catalog.json', dict(schema_version=1, datasets=[dict(dataset_id=key, roles=['reference'])
                             for key in ('ot_evidence', 'ot_target', 'ot_disease', 'ot_release_inputs')]))
        self.grant = dict(schema_version=1, status='approved', permission_applied=True,
                          requested_input_role='reference', production_admission_changes=False, new_downloads=False,
                          provider_spend_usd=0, approval=dict(answer='Approve this isolated research use'),
                          decision_origin='2025-01-01T00:00:00Z', source_screen_sha256=screen['sha256'],
                          mapping_manifest_sha256=mapping.anchor,
                          evidence_originals=[{k:r.get(k) for k in ('path','sha256','bytes','release','source','receipt_path','receipt_sha256','receipt_role','url')} for r in self.files],
                          mapping_originals=[dict(dataset_id=kind, **{k:r[k] for k in ('path','sha256','bytes','receipt_path','receipt_sha256','source_url')})
                                             for kind,r in zip(('ot_target','ot_disease'),mapping.files)])
        self.grant_ref = self.save('grant.json', self.grant)
        self.case = dict(case_id='fixture', target_id='targets-1', indication_id='diseases-1',
                         target_namespace_version='OpenTargets:24.09:targets',
                         indication_namespace_version='OpenTargets:24.09:diseases',
                         intended_action='inhibit', modality='antibody', tissue=None)
        self.request = dict(schema_version=1, kind='tether_development_three_views',
                            decision_origin='2025-01-01T00:00:00Z', grant=self.grant_ref,
                            catalog=catalog, source_screen=screen,
                            mapping_manifest=dict(path=str(mapping.path),sha256=mapping.anchor),
                            hypotheses=[self.case], pipeline_sha256=fingerprint(pipeline_code()))
        self.request_ref = self.save('request.json',self.request)
        self.output = self.root/'build'

    def save(self, name, value):
        path = self.root/name; raw=canonical(value)+b'\n'; path.write_bytes(raw)
        return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())

    def run_build(self):
        return build(Path(self.request_ref['path']),self.request_ref['sha256'],self.output,
                     expected_grant_sha256=self.grant_ref['sha256'],source_roots=(self.root,))

    def repin(self):
        self.request_ref=self.save('request.json',self.request)

    def test_complete_build_preserves_old_roles_and_truthful_current_verdict(self):
        before={row['receipt_path']:Path(row['receipt_path']).read_bytes() for row in self.files}
        report=self.run_build()
        self.assertEqual([report['coverage'][v]['accepted_rows'] for v in ('archived','current_filtered','current_unfiltered')],[1,1,2])
        self.assertEqual(report['temporal_verdicts']['archived'],'eligible_by_declared_lineage')
        self.assertEqual(report['temporal_verdicts']['current_filtered'],'later_information')
        self.assertEqual(report['preserved_collection_roles'], {'evaluation_only':1,'None':1})
        for path,raw in before.items(): self.assertEqual(Path(path).read_bytes(),raw)
        seal=read_json(self.output/'terminal-seal.json')
        self.assertEqual(seal['report_sha256'],hashlib.sha256((self.output/'report.json').read_bytes()).hexdigest())
        self.assertEqual(seal['journal_head'],read_chain(self.output/'journal.jsonl')[-1]['sha256'])
        for name,entry in report['outputs'].items():
            self.assertEqual(hashlib.sha256((self.output/name).read_bytes()).hexdigest(),entry['sha256'])
        inspection = inspect_run(self.output)
        self.assertEqual(inspection['stage'], 'publication')
        self.assertEqual(inspection['build_report_files'], ['report.json'])
        self.assertTrue(inspection['build_report_present'])

    def test_unapproved_grant_fails_before_original_source_inspection(self):
        self.grant['status']='proposed'; self.grant_ref=self.save('grant.json',self.grant)
        self.request['grant']=self.grant_ref; self.repin()
        with patch('tools.science.research_build.qualify',side_effect=AssertionError('unapproved dispatch')):
            with self.assertRaisesRegex(ContractError,'approval required'): self.run_build()
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'],'build_failed')

    def test_request_cannot_replace_independently_selected_grant(self):
        self.request['grant']['sha256']='0'*64; self.repin()
        with self.assertRaisesRegex(ContractError,'independent caller anchor'):
            build(Path(self.request_ref['path']),self.request_ref['sha256'],self.output,
                  expected_grant_sha256='f'*64,source_roots=(self.root,))

    def test_changed_granted_original_or_clinical_partition_cannot_be_selected(self):
        doc=read_json(Path(self.request['source_screen']['path'])); doc['files'][0]['source']='chembl'
        screen=self.save('screen.json',doc); self.request['source_screen']=screen
        self.grant['source_screen_sha256']=screen['sha256']; self.grant_ref=self.save('grant.json',self.grant)
        self.request['grant']=self.grant_ref; self.repin()
        with self.assertRaisesRegex(ContractError,'Granted evidence identity differs'): self.run_build()

    def test_evaluator_catalog_product_is_denied_even_with_a_use_grant(self):
        doc=read_json(Path(self.request['catalog']['path'])); doc['datasets'][0]['roles'].append('evaluation_only')
        self.request['catalog']=self.save('catalog.json',doc); self.repin()
        with self.assertRaisesRegex(ContractError,'Catalog denies'): self.run_build()

    def test_missing_case_identifier_fails_without_silent_replacement(self):
        self.case['target_id']='absent'; self.repin()
        with self.assertRaisesRegex(ContractError,'canonical identifier missing'): self.run_build()
        self.assertFalse((self.output/'terminal-seal.json').exists())

    def test_nested_stage_interruption_retains_parent_failure(self):
        with patch('tools.science.research_build.build_index',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.run_build()
        events=read_chain(self.output/'journal.jsonl')
        self.assertEqual(events[-1]['event'],'build_interrupted')
        self.assertEqual(events[-1]['details']['stage'],'mapping_membership')
        self.assertTrue((self.output/'source-inspection/terminal-seal.json').exists())

    def test_output_reservation_prevents_duplicate_concurrent_execution(self):
        def worker():
            try: return self.run_build()['status']
            except FileExistsError: return 'exclusive_output_denied'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:worker(),range(2)))
        self.assertCountEqual(results,['development_three_view_build_complete','exclusive_output_denied'])
        self.assertEqual(sum(e['event']=='build_reserved' for e in read_chain(self.output/'journal.jsonl')),1)

    def test_packet_size_failure_remains_unsealed(self):
        with patch('tools.science.research_build.MAX_VIEW_BYTES',1):
            with self.assertRaisesRegex(ContractError,'64 MiB'): self.run_build()
        self.assertFalse((self.output/'terminal-seal.json').exists())
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['details']['stage'],'publication')

    def test_iterator_cleanup_failure_preserves_primary_failure(self):
        class Broken:
            def __iter__(self): return self
            def __next__(self): raise TimeoutError('primary')
            def close(self): raise OSError('secondary')
        with patch('tools.science.research_build.stream_rows',return_value=Broken()):
            with self.assertRaisesRegex(TimeoutError,'primary'): self.run_build()
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['details']['error_class'],'TimeoutError')

    def test_child_report_tampering_is_detected_before_parent_seal(self):
        from tools.science.research_parquet import stream_rows
        def corrupt(*args, **kwargs):
            yield from stream_rows(*args, **kwargs)
            path=self.output/'source-inspection/report.json'
            value=read_json(path); value['actor_input_qualification']='forged'
            path.write_bytes(canonical(value))
        with patch('tools.science.research_build.stream_rows',side_effect=corrupt):
            with self.assertRaisesRegex(ContractError,'Child build seal'): self.run_build()
        self.assertFalse((self.output/'terminal-seal.json').exists())

    def test_final_view_write_failure_leaves_readable_parent_progress(self):
        from tether_engine.atomic import publish_bytes
        def failing(path, raw, **kwargs):
            if path.name=='archived.json': raise OSError('fictional disk full')
            return publish_bytes(path, raw, **kwargs)
        with patch('tools.science.research_build.publish_bytes',side_effect=failing):
            with self.assertRaisesRegex(OSError,'disk full'): self.run_build()
        inspection=inspect_run(self.output)
        self.assertEqual(inspection['stage'],'publication')
        self.assertEqual(inspection['failure']['error_class'],'OSError')
        self.assertFalse((self.output/'terminal-seal.json').exists())

    def test_undeclared_control_fields_are_rejected_before_source_inspection(self):
        self.request['hidden_outcome']='fictional unexpected control'; self.repin()
        with patch('tools.science.research_build.qualify',side_effect=AssertionError('unsupported controls')):
            with self.assertRaisesRegex(ContractError,'Unsupported research build request'): self.run_build()

    def test_actual_receipt_precision_has_a_conservative_view_bound(self):
        row=self.files[1]; path=Path(row['receipt_path']); receipt=read_json(path)
        receipt['completed_at_utc']='2026-10-11T02:11:32.3798602+00:00'; path.write_bytes(canonical(receipt))
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        screen=read_json(Path(self.request['source_screen']['path']))
        screen['files'][1]['receipt_sha256']=digest
        next(p for p in screen['metadata_pins'] if p['path']==str(path)).update(sha256=digest,bytes=path.stat().st_size)
        self.request['source_screen']=self.save('screen.json',screen)
        self.grant['source_screen_sha256']=self.request['source_screen']['sha256']
        self.grant['evidence_originals'][1]['receipt_sha256']=digest
        self.grant_ref=self.save('grant.json',self.grant); self.request['grant']=self.grant_ref; self.repin()
        report=self.run_build()
        self.assertEqual(report['status'],'development_three_view_build_complete')
        frame=read_json(self.output/'frame.json')
        current=next(s for s in frame['sources'] if s['release']=='25.09')
        self.assertEqual(current['available_by'],'2026-10-11T02:11:32.379861Z')
        proofs=read_json(self.output/'source-provenance.json')
        self.assertEqual(next(p for p in proofs if p['release']=='25.09')['retrieved_at'],receipt['completed_at_utc'])


if __name__ == '__main__': unittest.main()
