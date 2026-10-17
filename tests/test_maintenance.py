import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from asof.maintenance import acquisition_report, update_catalog, write_new_json
from asof.serde import ContractError, read_json, sha256_file, write_json
from tools.framework.prepare_v02_inputs import prepare
from tools.review.probe_framework import required_probes_passed

ROOT = Path(__file__).resolve().parents[1]


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public = self.root/'data/manifests/public'
        self.public.mkdir(parents=True)
        self.catalog = self.root/'catalog.json'
        shutil.copyfile(ROOT/'data/catalog/sources.json',self.catalog)
        self.original = read_json(self.catalog)
        self.anchor = sha256_file(self.catalog)
        self.raw = self.root/'raw'
        (self.raw/'manifests/receipts').mkdir(parents=True)
        (self.raw/'target.parquet').write_bytes(b'fictional bytes; not used as Parquet')
        self.queue = self.root/'queue.json'
        write_json(self.queue, {'batch_id':'fixture-batch','files':[{'dataset_id':'ot_target','release_id':'25.09',
            'relative_path':'target.parquet','receipt_id':'fixture-target'}]})
        self.receipt = self.raw/'manifests/receipts/fixture-target.json'
        write_json(self.receipt,{'status':'completed','dataset_id':'ot_target','release_id':'25.09',
            'relative_path':'target.parquet','bytes':(self.raw/'target.parquet').stat().st_size,
            'sha256':sha256_file(self.raw/'target.parquet')})
        self.report = self.public/'report.json'
        write_new_json(self.report,acquisition_report(self.root,self.raw,[self.queue],self.catalog))

    def test_transport_update_preserves_policy_and_scientific_fields(self):
        update_catalog(self.root,self.catalog,self.report,self.anchor)
        after = read_json(self.catalog)
        self.assertEqual(after['scope'],self.original['scope'])
        for before,row in zip(self.original['datasets'],after['datasets']):
            for key in before:
                if key not in ('collection_status','acquisition_snapshot'):
                    self.assertEqual(before[key],row[key],(row['dataset_id'],key))
        with self.assertRaisesRegex(ContractError,'Stale'):
            update_catalog(self.root,self.catalog,self.report,self.anchor)

    def test_concurrent_updates_have_one_winner_without_lost_changes(self):
        def update():
            try:
                update_catalog(self.root,self.catalog,self.report,self.anchor)
                return 'ok'
            except ContractError:
                return 'denied'
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _:update(),range(2))),['denied','ok'])
        self.assertEqual(read_json(self.catalog)['last_maintenance_update']['report_sha256'],sha256_file(self.report))
        self.assertFalse(self.catalog.with_name('catalog.json.lock').exists())

    def test_forbidden_fields_and_write_failure_leave_catalog_unchanged(self):
        report = read_json(self.report)
        report['datasets'][0]['roles']=['evaluation_only']
        write_json(self.report,report)
        with self.assertRaises(ContractError):
            update_catalog(self.root,self.catalog,self.report,self.anchor)
        self.assertEqual(sha256_file(self.catalog),self.anchor)
        report['datasets'][0].pop('roles')
        write_json(self.report,report)
        with patch('asof.maintenance.write_json',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                update_catalog(self.root,self.catalog,self.report,self.anchor)
        self.assertEqual(sha256_file(self.catalog),self.anchor)
        self.assertFalse(self.catalog.with_name('catalog.json.lock').exists())

    def test_no_clobber_and_readonly_manifest_preparation(self):
        output = self.root/'inputs.json'
        prepare(self.raw,[self.queue],self.catalog,output)
        original = output.read_bytes()
        with self.assertRaises(ContractError):
            prepare(self.raw,[self.queue],self.catalog,output)
        with self.assertRaises(FileExistsError):
            write_new_json(output,{'overwrite':True})
        self.assertEqual(output.read_bytes(),original)
        self.assertEqual(sha256_file(self.catalog),self.anchor)
        self.assertEqual(len(read_json(output)['files']),1)

    def test_acquisition_does_not_promote_bad_receipts(self):
        (self.raw/'target.parquet').write_bytes(b'changed')
        with self.assertRaisesRegex(ContractError,'receipt'):
            acquisition_report(self.root,self.raw,[self.queue],self.catalog)

    def test_complete_normalization_clears_only_missing_input_blocker(self):
        report = {'schema_version':1,'kind':'normalization','created_at_utc':'2026-10-17T00:00:00Z',
                  'build_report':{},'pilot_report':{},'source_review':{}}
        write_json(self.report,report)
        build = {'inspection':{'missing_inputs':[]},'cases':[{'packet_bytes':123}],
                 'snapshot_id':'fixture-complete'}
        with patch('asof.maintenance.checked_product_reports',return_value=(build,{},{})):
            update_catalog(self.root,self.catalog,self.report,self.anchor)
        row = next(r for r in read_json(self.catalog)['datasets'] if r['dataset_id']=='asof_normalized_packets')
        self.assertEqual(row['blockers'],['Independent scientific validation not run'])
        self.assertEqual(row['validation_status'],'not_run')
        self.assertNotIn('resolve selected-subset missing inputs',row['verification']['next_acquisition_check'])

    def test_missing_demo_inputs_do_not_leave_output(self):
        output = self.root/'demo'
        result = subprocess.run([sys.executable,str(ROOT/'tools/framework/build_demo_v2.py'),
            '--input',str(self.root/'missing'),'--output',str(output)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Missing preserved v1 inputs',result.stderr)
        self.assertFalse(output.exists())

    def correction_report(self):
        proof = self.public/'technical-evidence.json'
        write_new_json(proof, {'fixture':'synthetic technical evidence, not scientific validation'})
        row = next(r for r in self.original['datasets'] if r['dataset_id']=='aact_snapshots')
        return {'schema_version':1,'kind':'status_correction','created_at_utc':'2026-10-17T00:00:00Z',
            'scope':'Fixture metadata correction only',
            'evidence':[{'path':'data/manifests/public/technical-evidence.json','sha256':sha256_file(proof)}],
            'datasets':[{'dataset_id':'aact_snapshots','collection_status':row['collection_status'],
                'verification':{'level':'sample_inspected','checked_at':'2026-10-17',
                    'evidence':[{'result':'Fixture restoration metadata inspected'}],
                    'next_acquisition_check':'Scientific qualification remains open'},
                'blockers':['No independent scientific validation']} ]}

    def test_status_correction_preserves_acquisition_policy_and_scientific_status(self):
        report=self.correction_report();write_json(self.report,report)
        update_catalog(self.root,self.catalog,self.report,self.anchor)
        after=read_json(self.catalog)
        for before,row in zip(self.original['datasets'],after['datasets']):
            for key in before:
                if row['dataset_id']!='aact_snapshots' or key not in {'collection_status','verification','blockers'}:
                    self.assertEqual(before[key],row[key],(row['dataset_id'],key))
        self.assertEqual(next(r for r in after['datasets'] if r['dataset_id']=='aact_snapshots')['validation_status'],'not_run')

    def test_correction_rejects_tampering_and_scientific_or_collection_promotion(self):
        report=self.correction_report()
        for field,value in [('parse_status','parsed'),('validation_status','validated'),('roles',['agent_evidence'])]:
            bad=copy.deepcopy(report);bad['datasets'][0][field]=value;write_json(self.report,bad)
            with self.assertRaises(ContractError):update_catalog(self.root,self.catalog,self.report,self.anchor)
            self.assertEqual(sha256_file(self.catalog),self.anchor)
        # A correction cannot turn an uncollected product into a collected one.
        bad=copy.deepcopy(report);bad['datasets'][0]['dataset_id']='chembl_molecules'
        bad['datasets'][0]['collection_status']='collected';write_json(self.report,bad)
        with self.assertRaises(ContractError):update_catalog(self.root,self.catalog,self.report,self.anchor)
        write_json(self.report,report)
        (self.public/'technical-evidence.json').write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ContractError,'evidence changed'):
            update_catalog(self.root,self.catalog,self.report,self.anchor)
        self.assertEqual(sha256_file(self.catalog),self.anchor)

    def test_required_probe_none_and_empty_cannot_succeed(self):
        for result in ({},{'legacy':{'passed':None}},{'legacy':{'passed':False}}):
            self.assertFalse(required_probes_passed(result))
        self.assertTrue(required_probes_passed({'legacy':{'passed':True}}))

    @unittest.skipUnless(shutil.which('pwsh'),'PowerShell 7 required for utility integration')
    def test_powershell_overwrite_and_queue_identity_without_monitor_start(self):
        result = subprocess.run(['pwsh','-NoProfile','-File',str(ROOT/'tools/data/Measure-SourceInventory.ps1'),
            '-OutputPath',str(self.report)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Inventory report exists',result.stderr)
        result = subprocess.run(['pwsh','-NoProfile','-File',str(ROOT/'tools/data/Watch-DownloadBatch.ps1'),
            '-QueuePath',str(self.queue),'-DataRoot',str(self.raw),'-ValidateOnly'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('fixture-batch',result.stdout)
        self.assertIn('false',result.stdout)
        self.assertFalse(any((self.raw/'manifests').glob('*monitor*')))
