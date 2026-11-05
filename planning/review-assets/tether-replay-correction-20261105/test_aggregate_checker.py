"""Invented-file adversarial self-audit; never reads or executes the real gate.

The checker author wrote these probes. They are not an independent reviewer or
new release tests, and their counts must not be added to product-test evidence.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).parent
PROJECT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location('aggregate_under_test', HERE / 'check_release_aggregate.py')
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def save(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


class FullGateProofTests(unittest.TestCase):
    def setUp(self):
        base = PROJECT / 'data/cache/aggregate-checker-invented-tests'
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.here = self.root / 'review'
        self.addCleanup(patch.stopall)
        patch.object(CHECKER, 'ROOT', self.root).start()
        patch.object(CHECKER, 'HERE', self.here).start()
        # Rebind only the helper's captured root to private invented files; its
        # real hashing/size checks remain in use, with no decision helper mocked.
        patch.object(CHECKER.assert_hashes, '__defaults__', (self.root,)).start()
        for name in ('src/asof/__init__.py', 'tests/test_fiction.py', 'tools/validate.py',
            'pyproject.toml', 'uv.lock', 'packages/tether/pyproject.toml', 'packages/tether/uv.lock',
            'paper/release/build-constraints.txt', 'data/catalog/sources.json', 'data/catalog/policy-v2.json',
            'planning/review-assets/tether-ce-fixes-20261102/integration/run_gate.py'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# Invented file; never executed\n', encoding='utf-8')
        self.stem = self.here / 'integration/tether052-full-gate-03'
        self.started_path = self.stem.with_suffix('.started.json')
        self.before_path = self.stem.with_suffix('.source-before.json')
        self.report_path = self.stem.with_suffix('.json')
        self.bracket_path = self.stem.with_suffix('.source-bracket.json')
        self.log_path = self.stem.with_suffix('.log')
        self.before = dict(schema_version=1, sources=CHECKER.gate_inventory())
        save(self.before_path, self.before)
        self.started = dict(schema_version=1, status='started', pid=123, cwd=str(self.root),
            started_at_utc='2026-01-01T00:00:00+00:00', before_path=str(self.before_path),
            before_sha256=CHECKER.sha(self.before_path),
            argv=[str(self.root / 'fictional-python.exe'), '-B', str(self.root / 'tools/validate.py'),
                  '--mode', 'full', '--package', '--failfast', '--report', str(self.report_path)])
        save(self.started_path, self.started)
        self.report = dict(mode='full', status='passed', stage='complete',
            tests=dict(run=2, failures=0, errors=0, skipped=[]), required_probes_exit_code=0,
            packaging=dict(dependency_free_demo='passed', package_network_policy='offline',
                build_constraints_sha256=CHECKER.sha(self.root / 'paper/release/build-constraints.txt')))
        self.log_path.write_text('Invented log, not executed tests\nRan 2 tests in 0.1s\n\nOK\n', encoding='utf-8')
        self.bracket = dict(self.started, status='PASS', exit_code=0,
            finished_at_utc='2026-01-01T00:00:01+00:00', changed_sources=[], after_sources=self.before['sources'],
            report_path=str(self.report_path), log_path=str(self.log_path))
        self.reseal()

    def reseal(self):
        save(self.report_path, self.report)
        self.bracket.update(report_sha256=CHECKER.sha(self.report_path), log_sha256=CHECKER.sha(self.log_path))
        save(self.bracket_path, self.bracket)

    def test_complete_consistent_invented_proof_reaches_pass(self):
        self.assertEqual(CHECKER.full_gate()['status'], 'PASS')

    def test_missing_terminal_report_is_pending_even_with_claimed_pass_bracket(self):
        self.report_path.unlink()
        self.assertEqual(CHECKER.full_gate()['status'], 'PENDING')

    def test_missing_terminal_bracket_is_pending_even_with_passed_report(self):
        self.bracket_path.unlink()
        self.assertEqual(CHECKER.full_gate()['status'], 'PENDING')

    def test_resealed_passed_report_cannot_hide_log_test_count_mismatch(self):
        self.report['tests']['run'] = 3
        self.reseal()
        with self.assertRaises(AssertionError):
            CHECKER.full_gate()

    def test_resealed_passed_report_cannot_hide_skipped_tests(self):
        self.report['tests']['skipped'] = [['fictional-test', 'skipped']]
        self.reseal()
        with self.assertRaises(AssertionError):
            CHECKER.full_gate()

    def test_failed_final_log_summary_cannot_be_overridden_by_resealed_pass(self):
        self.log_path.write_text('Ran 1 test in 0.1s\n\nOK\nNested output\nRan 2 tests in 0.2s\n\nFAILED (failures=1)\n', encoding='utf-8')
        self.reseal()
        with self.assertRaises(AssertionError):
            CHECKER.full_gate()

    def test_nested_negative_summary_does_not_override_successful_final_suite(self):
        self.log_path.write_text('Nested negative fixture\nRan 1 test in 0.1s\n\nFAILED (errors=1)\nOuter suite\nRan 2 tests in 0.2s\n\nOK\n', encoding='utf-8')
        self.reseal()
        self.assertEqual(CHECKER.full_gate()['status'], 'PASS')

    def test_log_skips_rejected_even_if_report_claims_none(self):
        self.log_path.write_text('Ran 2 tests in 0.2s\n\nOK (skipped=1)\n', encoding='utf-8')
        self.reseal()
        with self.assertRaises(AssertionError):
            CHECKER.full_gate()

    def test_focused_record_cannot_use_an_earlier_ok_for_failed_final_suite(self):
        self.log_path.write_text('Ran 1 test in 0.1s\n\nOK\nRan 2 tests in 0.2s\n\nFAILED (failures=1)\n', encoding='utf-8')
        path = self.here / 'fictional-focused.json'
        save(path, dict(status='PASS', tests=2, failures=0, errors=0, skipped=0, log_sha256=CHECKER.sha(self.log_path)))
        with self.assertRaises(AssertionError):
            CHECKER.test_record(path, self.log_path, 2)

    def test_focused_record_accepts_final_ok_despite_nested_negative_fixture(self):
        self.log_path.write_text('Ran 1 test in 0.1s\n\nFAILED (errors=1)\nRan 2 tests in 0.2s\n\nOK\n', encoding='utf-8')
        path = self.here / 'fictional-focused.json'
        save(path, dict(status='PASS', tests=2, failures=0, errors=0, skipped=0, log_sha256=CHECKER.sha(self.log_path)))
        self.assertEqual(CHECKER.test_record(path, self.log_path, 2)[1]['parsed_test_count'], 2)

    def test_consistently_resealed_missing_source_inventory_member_rejected(self):
        self.before['sources'].pop('tests/test_fiction.py')
        save(self.before_path, self.before)
        self.started['before_sha256'] = CHECKER.sha(self.before_path)
        save(self.started_path, self.started)
        self.bracket.update(before_sha256=self.started['before_sha256'], after_sources=self.before['sources'])
        self.reseal()
        with self.assertRaisesRegex(AssertionError, 'inventory'):
            CHECKER.full_gate()

    def test_passed_words_do_not_replace_successful_terminal_exit(self):
        self.bracket['exit_code'] = 1
        self.reseal()
        with self.assertRaises(AssertionError):
            CHECKER.full_gate()

    def test_resealed_bracket_cannot_bind_a_different_started_invocation(self):
        self.bracket['pid'] = 987
        self.reseal()
        with self.assertRaises(AssertionError):
            CHECKER.full_gate()


class PreviousProofPreservationTests(unittest.TestCase):
    def setUp(self):
        base = PROJECT / 'data/cache/aggregate-checker-invented-tests'
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.versions = {'asof-target-agents': 'fictional', 'tether-target-agents': 'fictional'}
        self.qual = dict(status='PASS', versions=self.versions, commands=[],
            source_manifest=dict(sources={}), installed=dict(isolated=1,
                executable=str(self.base / 'environment/Scripts/python.exe'), packages={}), wheel_proofs=[])
        for namespace, distribution in (('asof', 'asof-target-agents'), ('tether', 'tether-target-agents')):
            package = self.base / 'environment/Lib/site-packages' / namespace
            package.mkdir(parents=True)
            payload = b'# Fictional package, not imported\n'
            (package / '__init__.py').write_bytes(payload)
            members = {namespace + '/__init__.py': hashlib.sha256(payload).hexdigest()}
            wheel = self.base / (namespace + '.whl')
            with zipfile.ZipFile(wheel, 'x') as archive:
                archive.writestr(namespace + '/__init__.py', payload)
            self.qual['source_manifest']['sources'][namespace] = members
            self.qual['installed']['packages'][namespace] = dict(root=str(package), source_sha256=members)
            self.qual['wheel_proofs'].append(dict(distribution=distribution, path=str(wheel),
                sha256=CHECKER.sha(wheel), source_sha256=members))
        (self.base / 'journal.jsonl').write_text('Fictional previously anchored journal\n', encoding='utf-8')
        self.qual['journal_sha256'] = CHECKER.sha(self.base / 'journal.jsonl')
        copied = self.base / 'captured.txt'
        copied.write_text('Fictional captured input\n', encoding='utf-8')
        build = self.base / 'build-context-proof.json'
        save(build, dict(inputs={'captured.txt': dict(copied=str(copied), sha256=CHECKER.sha(copied))}))
        self.qual['build_context'] = dict(proof_sha256=CHECKER.sha(build))
        self.path = self.base / 'QUALIFICATION.json'
        save(self.path, self.qual)
        self.anchor = CHECKER.sha(self.path)

    def test_unchanged_invented_prior_proof_and_payloads_accepted(self):
        result = CHECKER.installed(self.base, self.anchor, self.versions, False)
        self.assertTrue(result['installed_payload_unchanged'])

    def test_previous_qualification_bytes_changed_after_anchor_rejected(self):
        self.path.write_bytes(self.path.read_bytes() + b' ')
        with self.assertRaises(AssertionError):
            CHECKER.installed(self.base, self.anchor, self.versions, False)

    def test_previous_wheel_bytes_changed_rejected(self):
        (self.base / 'asof.whl').write_bytes(b'Changed fictional wheel')
        with self.assertRaises(AssertionError):
            CHECKER.installed(self.base, self.anchor, self.versions, False)

    def test_previous_installed_payload_changed_rejected(self):
        (self.base / 'environment/Lib/site-packages/asof/__init__.py').write_bytes(b'# Altered fictional package')
        with self.assertRaises(AssertionError):
            CHECKER.installed(self.base, self.anchor, self.versions, False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    before = CHECKER.sha(HERE / 'check_release_aggregate.py')
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    log = HERE / ('aggregate-checker-' + args.tag + '.log')
    with log.open('x', encoding='utf-8') as output:
        output.write(stream.getvalue())
    record = dict(schema_version=1, status='PASS' if result.wasSuccessful() else 'FAIL',
        scope='Invented-file adversarial self-audit by checker author; no real full gate read or execution',
        checked_at_utc=datetime.now(timezone.utc).isoformat(), tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        checker_sha256=before, checker_unchanged=before == CHECKER.sha(HERE / 'check_release_aggregate.py'),
        test_sha256=CHECKER.sha(Path(__file__)), log_sha256=CHECKER.sha(log),
        product_test_count_addition=0, provider_calls=0)
    with (HERE / ('AGGREGATE-CHECKER-' + args.tag.upper() + '.json')).open('x', encoding='utf-8') as output:
        json.dump(record, output, indent=2)
        output.write('\n')
    print(stream.getvalue())
    print(json.dumps(record, indent=2))
    return 0 if result.wasSuccessful() and record['checker_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
