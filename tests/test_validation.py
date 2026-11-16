"""The validation command must fail when required checks fail or disappear."""
import io
import os
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
from tether_engine.serde import write_json


class ValidationGateTests(unittest.TestCase):
    def test_physical_scratch_root_is_inherited_and_restored_on_failure(self):
        previous = tempfile.tempdir
        environment = {key: os.environ.get(key) for key in ('TEMP', 'TMP', 'TMPDIR')}
        physical = Path(tempfile.gettempdir()).resolve()
        with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
            with validate.canonical_test_temporary_directory() as selected:
                self.assertEqual(selected, str(physical))
                self.assertEqual(tempfile.tempdir, str(physical))
                for key in environment:
                    self.assertEqual(os.environ[key], str(physical))
                raise RuntimeError('fixture failure')
        self.assertEqual(tempfile.tempdir, previous)
        self.assertEqual({key: os.environ.get(key) for key in environment}, environment)

    def test_legacy_inventory_never_imports_original_runtime_tests(self):
        from tests import test_refinement_recovery as selection
        with patch.object(selection, 'legacy_suite', side_effect=AssertionError('Historical import forbidden')):
            scope = validate.legacy_compatibility_scope()
        self.assertEqual(scope['tests'], 16)
        self.assertEqual(len(set(scope['test_ids'])), 16)
        self.assertFalse(scope['current_policy_qualified'])
        self.assertEqual(scope['status'], 'not_executed_by_current_policy_gate')

    def test_legacy_inventory_rejects_changed_declarations_without_import(self):
        from tests import test_refinement_recovery as selection
        with patch.object(Path, 'read_text', return_value='class OriginalTests(unittest.TestCase): pass'):
            with self.assertRaisesRegex(AssertionError, 'inventory changed'):
                selection.legacy_test_inventory()

    @staticmethod
    def passing_probe_report():
        output = Path(sys.argv[sys.argv.index('--output') + 1])
        profile = sys.argv[sys.argv.index('--profile') + 1]
        write_json(output, {'profile': profile, 'probes': {'fixture': {'passed': True}}})
        return 0

    def test_probe_scope_and_details_survive_temporary_directory_cleanup(self):
        result = self.result('passed')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'validation.json'
            with patch.object(validate, 'structural_checks', return_value={}), \
                 patch.object(validate, 'powershell_check', return_value=True), \
                 patch('tools.test_profiles.select_suite', return_value=([], {'profile': 'maintained'})), \
                 patch.object(validate.unittest.TextTestRunner, 'run', return_value=result), \
                 patch.object(validate, 'probe_main', side_effect=self.passing_probe_report), \
                 patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(validate.main(['--mode', 'core', '--profile', 'maintained',
                                                '--report', str(output)]), 0)
            retained = validate.read_json(output)['required_probes']
            self.assertEqual(retained['profile'], 'maintained')
            self.assertTrue(retained['probes']['fixture']['passed'])

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
                 patch.object(validate, 'probe_main', side_effect=self.passing_probe_report), \
                 patch('sys.stdout', new_callable=io.StringIO):
                self.assertEqual(validate.main(['--mode', 'core']), 1)

    def test_empty_suite_and_optional_skip_policy(self):
        self.assertFalse(validate.successful_tests(unittest.TestResult(), 'core'))
        result = self.result('optional')
        self.assertTrue(validate.successful_tests(result, 'core'))
        self.assertFalse(validate.successful_tests(result, 'full'))

    def test_native_windows_skip_is_only_allowed_in_core_mode(self):
        for reason in ('native held-handle test requires Windows', 'Windows Job Object qualification'):
            with self.subTest(reason=reason):
                def native_only():
                    raise unittest.SkipTest(reason)
                result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.FunctionTestCase(native_only))
                self.assertEqual(result.testsRun, 1)
                self.assertEqual(len(result.skipped), 1)
                self.assertTrue(validate.successful_tests(result, 'core'))
                self.assertFalse(validate.successful_tests(result, 'full'))

    def test_parquet_optional_skip_keeps_wrong_arrow_version_rejected(self):
        from tether_engine.ingest import arrow as require_arrow
        def maintained_ingestion_dependency():
            if importlib.util.find_spec('pyarrow') is None:
                raise unittest.SkipTest('install the ingest extra for adapter tests')
            require_arrow()
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
                from tests.test_source_byte_qualification import ByteQualificationTests
                suite = unittest.TestSuite([
                    unittest.FunctionTestCase(maintained_ingestion_dependency),
                    ByteQualificationTests("test_parquet_footers_verified_without_row_decode"),
                    ByteQualificationTests("test_forged_footer_and_schema_fail_even_with_correct_payload_hash"),
                ])
                result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
            self.assertEqual(result.testsRun, 3)
            self.assertEqual(result.failures, [])
            if expected_core:
                self.assertEqual([reason for _, reason in result.skipped], ['install the ingest extra for adapter tests'] * 3)
                self.assertEqual(result.errors, [])
            else:
                self.assertEqual(result.skipped, [])
                self.assertEqual(len(result.errors), 3)
                self.assertIn('requires pyarrow==21.0.0' if kind == 'wrong_version' else 'pyarrow.parquet', result.errors[0][1])
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

    def test_research_fixture_dependencies_are_optional_only_in_core(self):
        from tests import test_research_build, test_research_mapping, test_research_parquet
        for cls in (test_research_build.ResearchBuildTests, test_research_mapping.ResearchMappingTests,
                    test_research_parquet.ResearchParquetTests):
            method = unittest.defaultTestLoader.getTestCaseNames(cls)[0]
            with self.subTest(fixture=cls.__name__), patch.dict(sys.modules, {'pyarrow': None, 'pyarrow.parquet': None}):
                result = unittest.TestResult()
                unittest.TestSuite([cls(method)]).run(result)
                self.assertEqual(result.errors, [])
                self.assertEqual([reason for _, reason in result.skipped], ['install the ingest extra for source-audit tests'])
                self.assertTrue(validate.successful_tests(result, 'core'))
                self.assertFalse(validate.successful_tests(result, 'full'))
