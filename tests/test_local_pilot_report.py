from pathlib import Path
import tempfile
import unittest
import os

from asof.serde import ContractError, sha256_file, write_json
from tools.framework.summarize_local_pilot import verify_seal, summarize


class LocalPilotReportTests(unittest.TestCase):
    def test_relative_roots_and_windows_separator_members_are_portable(self):
        with tempfile.TemporaryDirectory(prefix='asof-report-test-', dir=Path.cwd()) as d:
            root = Path(d); (root / 'case').mkdir()
            for name in ['pilot-report.json', 'pilot-journal.jsonl', 'case/record.json']:
                (root / name).write_bytes(b'{}')
            files = [{'path': n.replace('/', '\\'), 'bytes': 2, 'sha256': sha256_file(root / n)}
                for n in ['pilot-report.json', 'pilot-journal.jsonl', 'case/record.json']]
            seal = root / 'evidence-manifest.json'; write_json(seal, {'files': files})
            relative_root = Path(os.path.relpath(root))
            self.assertIn('case/record.json', verify_seal(relative_root, sha256_file(seal)))
            files.append({**files[-1], 'path': 'case/record.json'})
            write_json(seal, {'files': files})
            with self.assertRaises(ContractError): verify_seal(relative_root, sha256_file(seal))

    def test_changed_duplicate_missing_and_escaped_seal_members_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ['pilot-report.json', 'pilot-journal.jsonl']:
                (root / name).write_bytes(b'{}')
            pins = [{'path': name, 'bytes': 2, 'sha256': sha256_file(root / name)}
                    for name in ['pilot-report.json', 'pilot-journal.jsonl']]
            seal = root / 'evidence-manifest.json'; write_json(seal, {'files': pins})
            self.assertEqual(len(verify_seal(root, sha256_file(seal))), 2)
            (root / 'pilot-report.json').write_bytes(b'[]')
            with self.assertRaises(ContractError): verify_seal(root, sha256_file(seal))
            (root / 'pilot-report.json').write_bytes(b'{}')
            for members in [pins + pins[:1], pins[:1], [{'path': '../escape', 'bytes': 2, 'sha256': 'a' * 64}]]:
                write_json(seal, {'files': members})
                with self.assertRaises(ContractError): verify_seal(root, sha256_file(seal))

    def test_running_failed_partial_or_unstopped_pilot_cannot_be_completed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / 'pilot-journal.jsonl').write_text('', encoding='utf-8')
            for status, stopped, cases in [('running', False, []), ('failed', True, []),
                    ('ten_development_cases_verified', False, [{}] * 10),
                    ('ten_development_cases_verified', True, [{}] * 9)]:
                write_json(root / 'pilot-report.json', {'status': status, 'server_stopped': stopped, 'cases': cases})
                files = [{'path': n, 'bytes': (root / n).stat().st_size, 'sha256': sha256_file(root / n)}
                         for n in ['pilot-report.json', 'pilot-journal.jsonl']]
                seal = root / 'evidence-manifest.json'; write_json(seal, {'files': files})
                with self.assertRaises(ContractError): summarize(root, sha256_file(seal))
