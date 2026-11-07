import unittest
import contextlib
import io
import json
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
from tools.feasibility.restore_intermediate_aact import safe_members, dump_date, execute
from tools.feasibility.retain_public_sources import is_challenge
from tools.feasibility.verify_intermediate_aact import verify_journal, verify_seal


class IntermediateArchiveTests(unittest.TestCase):
    def test_restore_seals_reject_changed_bytes_and_escaped_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / 'audit.json'; artifact.write_bytes(b'{}')
            proof = root / 'manifest.json'
            digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            entry = {'path': 'audit.json', 'bytes': 2, 'sha256': digest(artifact)}
            proof.write_text(json.dumps({'files': [entry]}))
            self.assertEqual(verify_seal(proof, digest(proof)), {artifact.resolve()})
            artifact.write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError, 'Sealed evidence changed'):
                verify_seal(proof, digest(proof))
            proof.write_text(json.dumps({'files': [{**entry, 'path': '../outside.json'}]}))
            with self.assertRaisesRegex(ValueError, 'Unsafe or duplicate'):
                verify_seal(proof, digest(proof))

    def test_restore_journal_requires_chain_and_completed_terminal(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'journal.jsonl'
            row = {'stage': 'batch_terminal', 'status': 'completed', 'previous_sha256': None}
            digest = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            path.write_text(json.dumps({**row, 'sha256': digest}) + '\n')
            self.assertEqual(verify_journal(path), [row])
            path.write_text(json.dumps({**row, 'status': 'failed', 'sha256': digest}) + '\n')
            with self.assertRaisesRegex(ValueError, 'Broken restore journal'):
                verify_journal(path)
            row['status'] = 'running'
            digest = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            path.write_text(json.dumps({**row, 'sha256': digest}) + '\n')
            with self.assertRaisesRegex(ValueError, 'not complete'):
                verify_journal(path)

    def test_bad_archive_leaves_failure_and_existing_output_is_not_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'bad.zip'; archive.write_bytes(b'not a zip')
            out = root / 'run'
            plan = {'pg_bin': str(root), 'template_restore': str(root), 'first_port': 55439,
                    'snapshots': [{'requested_date': '2024-01-01', 'archive': str(archive)}]}
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(Exception):
                execute(plan, out)
            saved = (out / 'result.json').read_bytes()
            result = json.loads(saved)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['snapshots'][0]['status'], 'failed')
            self.assertEqual(json.loads((out / 'journal.jsonl').read_text().splitlines()[-1])['stage'], 'batch_terminal')
            with self.assertRaises(FileExistsError):
                execute(plan, out)
            self.assertEqual((out / 'result.json').read_bytes(), saved)

    def test_http_success_is_not_article_content(self):
        self.assertTrue(is_challenge(b'<title>pubmed.ncbi.nlm.nih.gov</title><script>const challengeId = "x";</script>'))
        self.assertTrue(is_challenge(b'<title>Checking your browser - reCAPTCHA</title>'))
        self.assertFalse(is_challenge(b'<title>A trial report</title><p>Abstract of the trial</p>'))

    def test_pmc_download_interstitial_is_not_a_workbook(self):
        self.assertTrue(is_challenge(b'<title>Preparing to download ...</title><script>const POW_CHALLENGE = "test";</script>'))
        self.assertFalse(is_challenge(b'PK\x03\x04xl/workbook.xml'))

    def test_flat_zip_member_contract(self):
        safe_members([SimpleNamespace(filename=x) for x in ['postgres.dmp', 'schema.png']])
        for names in [['../postgres.dmp'], ['C:postgres.dmp'], ['postgres.dmp', 'POSTGRES.DMP'],
                      ['postgres.dmp', 'nested/file'], ['schema.png']]:
            with self.assertRaises(ValueError):
                safe_members([SimpleNamespace(filename=x) for x in names])

    def test_actual_release_lag_is_preserved(self):
        self.assertEqual(dump_date('; Archive created at 2023-07-02 04:00:00\n', '2023-07-01'), '2023-07-02')
        self.assertEqual(dump_date('; Archive created at 2024-01-01 04:00:00\n', '2024-01-01'), '2024-01-01')
        for header in ['; Archive created at 2024-02-01 04:00:00\n', 'bad header']:
            with self.assertRaises(ValueError):
                dump_date(header, '2024-01-01')


if __name__ == '__main__':
    unittest.main()
