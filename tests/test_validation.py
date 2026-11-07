"""The validation command must fail when required checks fail or disappear."""
import io
import importlib.util
from importlib.machinery import ModuleSpec
import runpy
import sys
import tempfile
from types import ModuleType
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import validate


class ValidationGateTests(unittest.TestCase):
    def result(self, outcome):
        def fixture():
            if outcome == 'failure':
                raise AssertionError('intentional failing CI fixture')
            if outcome == 'skip':
                raise unittest.SkipTest('unexpected missing prerequisite')
            if outcome == 'optional':
                raise unittest.SkipTest('install the ingest extra for adapter tests')
        return unittest.TextTestRunner(stream=io.StringIO()).run(unittest.FunctionTestCase(fixture))

    def test_required_failure_and_unexpected_skip_return_nonzero(self):
        for outcome in ('failure', 'skip'):
            result = self.result(outcome)
            with patch.object(validate, 'structural_checks', return_value={}), \
                 patch.object(validate, 'powershell_check', return_value=True), \
                 patch.object(validate.unittest.defaultTestLoader, 'discover', return_value=[]), \
                 patch.object(validate.unittest.TextTestRunner, 'run', return_value=result), \
                 patch.object(validate, 'probe_main', return_value=0), \
                 patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(validate.main(['--mode', 'core']), 1)

    def test_empty_suite_and_optional_skip_policy(self):
        self.assertFalse(validate.successful_tests(unittest.TestResult(), 'core'))
        result = self.result('optional')
        self.assertTrue(validate.successful_tests(result, 'core'))
        self.assertFalse(validate.successful_tests(result, 'full'))

    def test_native_windows_skip_is_only_allowed_in_core_mode(self):
        def native_only():
            raise unittest.SkipTest('native held-handle test requires Windows')
        result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.FunctionTestCase(native_only))
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.skipped), 1)
        self.assertTrue(validate.successful_tests(result, 'core'))
        self.assertFalse(validate.successful_tests(result, 'full'))

    def test_parquet_optional_skip_keeps_wrong_arrow_version_rejected(self):
        from tests.test_study_source_fact_sources import SourceFactSourceTests
        wrong_arrow = ModuleType('pyarrow')
        wrong_arrow.__spec__ = ModuleSpec('pyarrow', loader=None, is_package=True)
        wrong_arrow.__path__ = []
        wrong_arrow.__version__ = '24.0.0'
        wrong_arrow.parquet = ModuleType('pyarrow.parquet')
        wrong_arrow.parquet.__spec__ = ModuleSpec('pyarrow.parquet', loader=None)
        broken_arrow = ModuleType('pyarrow')
        broken_arrow.__spec__ = ModuleSpec('pyarrow', loader=None, is_package=True)
        broken_arrow.__path__ = []
        broken_arrow.__version__ = '21.0.0'
        for kind, arrow, parquet, expected_core in (
            ('absent', None, None, True),
            ('wrong_version', wrong_arrow, wrong_arrow.parquet, False),
            ('broken_import', broken_arrow, None, False),
        ):
            with self.subTest(kind=kind), patch.dict(
                sys.modules, {'pyarrow': arrow, 'pyarrow.parquet': parquet}
            ):
                suite = unittest.TestSuite([SourceFactSourceTests(
                    'test_fictional_parquet_selected_row_and_absent_schema')])
                result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
            self.assertEqual(result.testsRun, 1)
            self.assertEqual(result.failures, [])
            if expected_core:
                self.assertEqual([reason for _, reason in result.skipped], ['install the ingest extra for source-audit tests'])
                self.assertEqual(result.errors, [])
            else:
                self.assertEqual(result.skipped, [])
                self.assertEqual(len(result.errors), 1)
                self.assertIn('requires pyarrow 21.0.0' if kind == 'wrong_version' else 'pyarrow.parquet', result.errors[0][1])
            self.assertEqual(validate.successful_tests(result, 'core'), expected_core)
            self.assertFalse(validate.successful_tests(result, 'full'))

    def test_source_audit_optional_skips_pass_core_and_fail_full(self):
        """Exercise the actual optional classes without running source fixtures."""
        root = Path(__file__).resolve().parents[1]
        original_find_spec = importlib.util.find_spec
        def without_arrow(name, *args, **kwargs):
            return None if name == 'pyarrow' else original_find_spec(name, *args, **kwargs)
        suite = unittest.TestSuite()
        for filename, class_name in (
            ('test_science_t6_contextual_audit.py', 'ContextualOriginalIntegrationTests'),
            ('test_science_t6_dossier_binding.py', 'DossierSourceBindingTests'),
        ):
            with patch('importlib.util.find_spec', side_effect=without_arrow):
                namespace = runpy.run_path(str(root / 'tests' / filename))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(namespace[class_name]))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        self.assertEqual(result.testsRun, 28)
        self.assertEqual(len(result.skipped), 28)
        self.assertTrue(validate.successful_tests(result, 'core'))
        self.assertFalse(validate.successful_tests(result, 'full'))
