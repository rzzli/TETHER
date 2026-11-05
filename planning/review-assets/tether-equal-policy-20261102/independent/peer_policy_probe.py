"""Read-only peer probes against policy code; never score the frozen corpus."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.equal_policy import independent_policy as policy
from experiments.equal_policy.independent import PolicyError
from experiments.equal_policy.test_independent_policy import IndependentOuterUnits


class PeerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = IndependentOuterUnits()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.assertTrue(self.root.resolve().is_relative_to((ROOT / 'data/cache').resolve()))

    def test_read_rechecks_links_after_closing_stream(self):
        path = self.root / 'bytes.bin'
        path.write_bytes(b'unit')
        actual = policy.no_links
        calls = []
        def boundary(value):
            calls.append(value)
            if len(calls) == 2:
                raise PolicyError('EP-IO-01', 'Injected post-read path alias')
            return actual(value)
        with patch.object(policy, 'no_links', side_effect=boundary):
            with self.assertRaisesRegex(PolicyError, 'post-read'):
                policy.stable(path, time.monotonic() + 10)
        self.assertEqual(len(calls), 2)

    def test_read_rechecks_deadline_after_final_read(self):
        path = self.root / 'bytes.bin'
        path.write_bytes(b'unit')
        with patch.object(policy.time, 'monotonic', side_effect=[0.0, 0.0, 2.0]):
            with self.assertRaisesRegex(PolicyError, 'after read'):
                policy.stable(path, 1.0)

    def test_outer_all_inventory_and_strict_size_bind_before_inner(self):
        output, manifest, trusted = self.fixture.outer()
        inner = dict(semantic_consistency='verified', code_matches_current=True, status='completed')
        with patch.object(policy, 'verify_core', return_value=inner) as verify:
            policy.verify_outer(output, None, trusted)
            self.assertEqual(verify.call_count, 1)
            verify.reset_mock()
            manifest['artifacts']['engine-stderr.txt']['bytes'] = 0.0
            self.fixture.seal_outer(output, manifest, inventory=False)
            with self.assertRaises(PolicyError):
                policy.verify_outer(output, None, trusted)
            verify.assert_not_called()
            self.fixture.seal_outer(output, manifest)
            (output / 'unlisted-empty').mkdir()
            with self.assertRaises(PolicyError):
                policy.verify_outer(output, None, trusted)
            verify.assert_not_called()

    def test_outer_current_code_and_trust_schema_fail_closed(self):
        output, _, trusted = self.fixture.outer()
        good = dict(semantic_consistency='verified', code_matches_current=True, status='completed')
        for trusted_change, inner_change in (({'schema_version': True}, {}), ({}, {'code_matches_current': False}),
                ({}, {'semantic_consistency': 'unavailable'}), ({}, {'status': 'partial'})):
            with self.subTest(trusted_change=trusted_change, inner_change=inner_change):
                with patch.object(policy, 'verify_core', return_value=good | inner_change):
                    with self.assertRaises(PolicyError):
                        policy.verify_outer(output, None, trusted | trusted_change)

    def test_supervision_fields_and_bounds_never_coerce(self):
        _, manifest, _ = self.fixture.outer()
        report, limits = manifest['supervision'], manifest['process_limits']
        for key, value in (('process_reaped', 1), ('process_started', 'true'), ('observed_stderr_bytes', False),
                ('observed_stdout_bytes', 2.0), ('execution_elapsed_seconds', True),
                ('execution_elapsed_seconds', 10.0), ('total_elapsed_seconds', 0.5), ('cleanup_errors', ['failure'])):
            with self.subTest(key=key, value=value), self.assertRaises(PolicyError):
                policy.supervision(report | {key: value}, limits, 2, 0)
        with self.assertRaises(PolicyError):
            policy.supervision(report | {'extra': 'unsupported'}, limits, 2, 0)

    def test_missing_policy_code_cannot_fall_back_to_schema1(self):
        output, manifest, trusted = self.fixture.outer()
        manifest['artifact_policy'] = {'path': 'missing', 'bytes': 0, 'sha256': '0' * 64}
        self.fixture.seal_outer(output, manifest)
        inner = dict(semantic_consistency='verified', code_matches_current=True, status='completed')
        with patch.object(policy, 'verify_core', return_value=inner):
            with self.assertRaises(PolicyError):
                policy.verify_outer(output, None, trusted)


def main():
    target = Path(__file__).resolve().parent
    phase = sys.argv[1]
    log, record = target / (phase + '.log'), target / (phase + '.json')
    if log.exists() or record.exists():
        raise SystemExit('Refusing to overwrite peer evidence')
    files = [Path(policy.__file__), Path(__file__), ROOT / 'experiments/equal_policy/test_independent_policy.py',
             ROOT / 'experiments/equal_policy/independent_runtime.py',
             ROOT / 'experiments/equal_policy/independent.py', ROOT / 'tests/test_equal_policy_independent.py']
    hashes = lambda: {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    before = hashes()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PeerPolicyTests))
    with log.open('x', encoding='utf-8') as output:
        output.write(stream.getvalue())
    after = hashes()
    summary = dict(status='PASS' if result.wasSuccessful() and before == after else 'FAIL', tests_run=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped), source_sha256=before,
        source_unchanged=before == after, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        scope='Independent fictional peer controls; inner verifier stubbed only for outer-envelope isolation; no corpus scoring',
        limitations=['Post-read alias/deadline probes inject boundary failures; no native race exploit is asserted',
                    'This record does not replace complete source-inclusive native integration'])
    with record.open('x', encoding='utf-8') as output:
        json.dump(summary, output, indent=2)
        output.write('\n')
    print(json.dumps(summary))
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
