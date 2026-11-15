"""Current fictional source controls, independently reconstructed by the auditor."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from tether_engine.serde import read_json
from tools.science import audit_source_validation_experiment as auditor
from tools.science import run_source_validation_experiment as producer


class SourceAuditSupportTests(unittest.TestCase):
    def test_direct_auditor_help_works_without_pythonpath(self):
        script = Path(auditor.__file__).resolve()
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, '-I', str(script), '--help'],
                                    cwd=temporary, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertIn(b'--seal-sha256', result.stdout)

    def test_auditor_import_does_not_execute_private_archive_code(self):
        code = '''
import importlib.util
def forbidden(*args, **kwargs):
    raise AssertionError("Private dynamic loader used")
importlib.util.spec_from_file_location = forbidden
from tools.science import audit_source_validation_experiment
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_all_current_fixtures_have_independent_stage_and_decision_agreement(self):
        cache = Path(__file__).resolve().parents[1] / 'data/cache'
        cache.mkdir(parents=True, exist_ok=True)
        first = {'F01': 'G0', 'F02': 'G1', 'F03': 'G2', 'F04': 'G2', 'F09': 'G3'}
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            root = Path(temporary) / 'fixtures'
            producer.author_fictional_fixtures(root)
            for key in producer.SCENARIOS:
                with self.subTest(scenario=key):
                    scenario = read_json(root / key / 'scenario.json')
                    packet = read_json(root / key / 'packet.json')
                    raw_root = root / key / 'originals'
                    names = [node['path'][:-5] for node in scenario['snapshot']['sources']]
                    originals = {name: (raw_root / (name + '.json')).read_bytes() for name in names}
                    receipts = {name: (raw_root / (name + '.receipt.json')).read_bytes() for name in names}
                    raw = producer.fictional_candidate(packet, key)
                    independent = auditor.fixture_evidence(scenario, packet, originals, receipts, raw, fixture_root=root)
                    bounds = producer.Bounds(root)
                    observed = producer.evaluate_fictional(scenario, packet, raw, bounds, approved_fixture_root=root)
                    valid = key.startswith('C')
                    full = independent['decisions']['FULL']
                    self.assertEqual(full['verdict'], 'admitted' if valid else 'rejected')
                    self.assertEqual(full['first_failure_stage'], None if valid else first.get(key, 'G4'))
                    for decision in observed['decisions']:
                        expected = independent['decisions'][decision['policy']]
                        self.assertEqual(decision['verdict'], expected['verdict'])
                        self.assertEqual(decision['first_failure_stage'], expected['first_failure_stage'])
                    if key == 'F02':
                        self.assertIn('role denied', observed['stages']['G1']['reason'])

    def test_current_helper_code_is_in_execution_pin_inventory(self):
        for name in ('__init__', 'registry', 'inputs', 'references'):
            self.assertIn('tools/science/audit_support/' + name + '.py', producer.EXTRA_CODE)


if __name__ == '__main__':
    unittest.main()
