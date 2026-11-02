"""Offline Windows transport verifier identity regressions; no real sources."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell 7 required for utility integration')
class ReceiptIdentityTests(unittest.TestCase):
    def run_fixture(self, changed, queued_changes=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'raw').mkdir()
            (root / 'manifests/receipts').mkdir(parents=True)
            payload = b'PAR1fictionalPAR1'
            (root / 'raw/example.parquet').write_bytes(payload)
            queued = {'receipt_id': 'receipt-example', 'dataset_id': 'ot_target',
                      'release_id': '25.09', 'relative_path': 'raw/example.parquet',
                      'url': 'https://ftp.ebi.ac.uk/fictional.parquet',
                      'expected_bytes': len(payload), 'planning_upper_bytes': 100,
                      'format': 'parquet'}
            queued.update(queued_changes or {})
            receipt = {**queued, 'status': 'completed', 'bytes': len(payload),
                       'sha256': hashlib.sha256(payload).hexdigest(), **changed}
            (root / 'queue.json').write_text(json.dumps({'batch_id': 'fictional', 'files': [queued]}))
            original_receipt = json.dumps(receipt).encode()
            receipt_path = root / 'manifests/receipts/receipt-example.json'
            receipt_path.write_bytes(original_receipt)
            result = subprocess.run([
                'pwsh', '-NoProfile', '-File', str(ROOT / 'tools/data/Test-DownloadBatch.ps1'),
                '-QueuePath', str(root / 'queue.json'), '-DataRoot', str(root),
                '-OutputPath', str(root / 'report.json')], capture_output=True, text=True, timeout=30)
            report = json.loads((root / 'report.json').read_text(encoding='utf-8-sig'))
            self.assertEqual(receipt_path.read_bytes(), original_receipt)
            self.assertEqual((root / 'raw/example.parquet').read_bytes(), payload)
            return result.returncode, report

    def test_valid_receipt_passes_without_rewriting_originals(self):
        code, report = self.run_fixture({})
        self.assertEqual(code, 0)
        self.assertTrue(report['complete'])
        self.assertEqual(report['verified_files'], 1)

    def assert_rejected(self, changed, queued_changes=None):
        code, report = self.run_fixture(changed, queued_changes)
        self.assertEqual(code, 2)
        self.assertFalse(report['complete'])
        self.assertEqual(report['verified_files'], 0)
        self.assertEqual(report['failed_files'], 1)

    def test_wrong_dataset_rejected(self):
        self.assert_rejected({'dataset_id': 'ot_disease'})

    def test_wrong_release_rejected(self):
        self.assert_rejected({'release_id': '99.99'})

    def test_wrong_receipt_identity_rejected(self):
        self.assert_rejected({'receipt_id': 'different-receipt'})

    def test_missing_identity_rejected(self):
        for key in ('receipt_id', 'dataset_id', 'release_id'):
            with self.subTest(key=key):
                self.assert_rejected({key: None})

    def test_case_only_source_identity_changes_are_rejected(self):
        for changed, queued in [
            ({'receipt_id': 'Receipt-example'}, {}),
            ({'dataset_id': 'OT_target'}, {}),
            ({'release_id': 'release-25.09'}, {'release_id': 'Release-25.09'}),
            ({'url': 'https://ftp.ebi.ac.uk/Fictional.parquet'}, {}),
            ({'relative_path': 'raw/Example.parquet'}, {}),
        ]:
            with self.subTest(changed=changed):
                self.assert_rejected(changed, queued)


if __name__ == '__main__':
    scratch = ROOT / 'data/cache/full-review-data-tests'
    scratch.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(scratch)
    unittest.main()
