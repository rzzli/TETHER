"""Invented release/mapping and temporal-view fixtures, without TestCase imports."""
import hashlib
from pathlib import Path
import tempfile

from tether_engine.serde import canonical, fingerprint
from tools.science.historical_inputs import BASE, NOTICE
from tools.science.research_mapping import build_index
from tools.science.research_views import build_views


class ResearchMappingFixture:
    def prepare(self, add_cleanup):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.tmp = tempfile.TemporaryDirectory(); add_cleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files, products, listing = [], [], []
        for kind, label in (('targets', 'approvedSymbol'), ('diseases', 'name')):
            path = self.root/(kind+'.parquet')
            pq.write_table(pa.Table.from_pylist([dict(id=kind+'-1', **{label: 'fictional label'}, clinicalPhase=4),
                                                dict(id=kind+'-2', **{label: None}, clinicalPhase=3)]), path, row_group_size=1)
            relative = 'output/etl/parquet/'+kind+'/part-0.parquet'
            item = self.item(path, BASE+relative)
            item['publisher_sha1'] = hashlib.sha1(path.read_bytes()).hexdigest()
            self.files.append(item)
            products.append(dict(product=kind, parents=[relative], rows=2))
            listing.append(item['publisher_sha1']+'  '+relative+'\n')
        notice = self.root/'notice.json'
        notice.write_bytes(canonical({'post_stream': {'posts': [{'created_at': '2024-09-18T13:36:32.754Z', 'cooked': 'Released 24.09'}]}}))
        integrity = self.root/'integrity'; integrity.write_text(''.join(listing), encoding='utf-8')
        checksum = self.root/'integrity.sha1'; checksum.write_text(hashlib.sha1(integrity.read_bytes()).hexdigest()+'  release_data_integrity\n', encoding='utf-8')
        self.manifest = dict(release_id='24.09', future_fallback=False, available_by='2024-09-19T00:00:00Z',
                             files=self.files, products=products,
                             metadata=[self.item(notice, NOTICE), self.item(integrity, BASE+'release_data_integrity'),
                                       self.item(checksum, BASE+'release_data_integrity.sha1')])
        self.path = self.root/'manifest.json'; self.output = self.root/'output'; self.pin()

    def item(self, path, url):
        payload = path.read_bytes()
        receipt = dict(status='completed', source_url=url, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                       http_status=200, retrieval_started_at='2026-10-18T12:00:00Z', retrieval_completed_at='2026-10-18T12:01:00Z')
        rp = self.root/(path.name+'.receipt.json'); rp.write_bytes(canonical(receipt))
        return dict(path=str(path), receipt_path=str(rp), receipt_sha256=hashlib.sha256(rp.read_bytes()).hexdigest(),
                    source_url=url, bytes=len(payload), sha256=receipt['sha256'])

    def pin(self):
        raw = canonical(self.manifest); self.path.write_bytes(raw); self.anchor = hashlib.sha256(raw).hexdigest()

    def run_build(self, **kwargs):
        return build_index(self.path, self.anchor, self.output, source_roots=(self.root,), **kwargs)


class ResearchViewFixture:
    def setUp(self):
        self.case = dict(case_id='case', target_id='ENSG-fixture', indication_id='EFO-fixture',
                         target_namespace_version='old', indication_namespace_version='old',
                         intended_action='inhibit', modality='antibody', tissue=None)
        def source(key, release, purpose, when, parents=()):
            return dict(artifact_id=key, sha256=fingerprint(key), release=release,
                        role='reference', purpose=purpose, available_by=when, parents=list(parents),
                        datasource='gene_burden' if purpose == 'nonclinical_evidence' else None)
        self.frame = dict(schema_version=1, view_policy_id='fixture.v1',
                          decision_origin='2025-01-01T00:00:00Z', hypotheses=[self.case],
                          method_sha256=fingerprint('fixture-fixed-method'),
                          sources=[source('old', '24.09', 'nonclinical_evidence', '2024-09-19T00:00:00Z', ['mapping']),
                                   source('new', '25.09', 'nonclinical_evidence', '2025-09-30T00:00:00Z', ['mapping']),
                                   source('mapping', '24.09', 'identifier_mapping', '2024-09-19T00:00:00Z')],
                          views={'archived': ['old'], 'current_filtered': ['new'], 'current_unfiltered': ['new']},
                          filter_field='publicationDate', max_rows=100, max_selected_rows=100)

    def row(self, source='new', date='2024-06-01', identity='r1', **values):
        return dict(source_id=source, row_group=0, row_index=0,
                    values=dict(id=identity, datasourceId='gene_burden', datatypeId='genetic_association',
                                targetId='ENSG-fixture', diseaseId='EFO-fixture', publicationDate=date, **values))

    def run_views(self, rows=()):
        return build_views(self.frame, rows, expected_frame_sha256=fingerprint(self.frame))
