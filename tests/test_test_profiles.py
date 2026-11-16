"""Scope routing cannot turn missing, stale or historical checks into passes."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.test_inventory import source_inventory
from tools.test_profiles import classify, select_suite


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tests').mkdir()
        (self.root / 'tests/test_a.py').write_text(
            'class A:\n    def test_one(self): pass\n    def test_two(self): pass\n')
        self.cases = [dict(id='tests.test_a.A.' + method, path='tests/test_a.py',
                           owner='A', method=method) for method in ('test_one', 'test_two')]
        self.census = dict(status='collection_complete_not_execution',
                           sources=source_inventory(self.root),
                           modules=[dict(cases=self.cases)])
        self.policy = dict(schema_version=1, authority='invented unit-test policy',
                           profiles={'maintained': 'current', 'historical': 'old runtime'},
                           files={'tests/test_a.py': 'maintained'},
                           overrides={'tests/test_a.py::A.test_two': 'historical'})

    def test_method_override_is_visible_and_not_a_test_pass(self):
        result = classify(self.root, self.census, self.policy)
        self.assertEqual(result['counts'], dict(maintained=1, historical=1))
        self.assertEqual(result['unique_cases'], 2)
        self.assertEqual(result['status'], 'scope_reconciled_not_execution')
        self.assertTrue(all(row['execution_status'] == 'not_established_by_census'
                            for row in result['methods']))

    def test_duplicate_collectors_do_not_double_count(self):
        self.census['modules'].append(copy.deepcopy(self.census['modules'][0]))
        self.assertEqual(classify(self.root, self.census, self.policy)['unique_cases'], 2)

    def test_stale_source_or_added_test_file_fails(self):
        path = self.root / 'tests/test_a.py'
        path.write_text(path.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            classify(self.root, self.census, self.policy)
        self.census['sources'] = source_inventory(self.root)
        (self.root / 'tests/test_new.py').write_text('')
        with self.assertRaisesRegex(ValueError, 'stale'):
            classify(self.root, self.census, self.policy)

    def test_missing_or_extra_classification_fails(self):
        for files in ({}, dict(self.policy['files'], **{'tests/test_gone.py': 'historical'})):
            with self.subTest(files=files), self.assertRaisesRegex(ValueError, 'Every test file'):
                classify(self.root, self.census, dict(self.policy, files=files))

    def test_unknown_scope_and_unused_override_fail(self):
        for edits, reason in ((dict(files={'tests/test_a.py': 'new'}), 'Unknown'),
                              (dict(overrides={'tests/test_a.py::A.test_missing': 'historical'}), 'Stale')):
            with self.subTest(edits=edits), self.assertRaisesRegex(ValueError, reason):
                classify(self.root, self.census, dict(self.policy, **edits))

    def test_conflicting_identity_fails(self):
        self.census['modules'].append(dict(cases=[dict(self.cases[0], method='different')]))
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            classify(self.root, self.census, self.policy)

    def test_incomplete_census_is_not_scope_acceptance(self):
        with self.assertRaisesRegex(ValueError, 'complete isolated census'):
            classify(self.root, dict(self.census, status='collection_failed'), self.policy)

    def test_unclassified_method_source_fails(self):
        self.cases.append(dict(id='unknown.A.test_extra', path='tests/test_unknown.py',
                               owner='A', method='test_extra'))
        with self.assertRaisesRegex(ValueError, 'unclassified source'):
            classify(self.root, self.census, self.policy)

    def test_claimed_complete_census_cannot_omit_declared_method(self):
        self.cases.pop()
        with self.assertRaisesRegex(ValueError, 'omits declared'):
            classify(self.root, self.census, self.policy)

    def fixture_module(self):
        path = self.root / 'tests/test_a.py'
        path.write_text('import unittest\nclass A(unittest.TestCase):\n'
                        '    def test_one(self): pass\n    def test_two(self): pass\n')
        spec = importlib.util.spec_from_file_location('invented_scope_control', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_selected_gate_excludes_original_bytes_without_importing_other_groups(self):
        module = self.fixture_module()
        (self.root / 'tests/test_old.py').write_text('raise AssertionError("Do not import")\n')
        self.policy['files']['tests/test_old.py'] = 'historical'
        with patch.object(unittest.TestLoader, 'loadTestsFromName',
                          return_value=unittest.defaultTestLoader.loadTestsFromModule(module)) as load:
            suite, report = select_suite(self.root, self.policy)
        load.assert_called_once_with('tests.test_a')
        result = unittest.TestResult(); suite.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(report['excluded_from_mixed_modules'],
                         [dict(id='invented_scope_control.A.test_two', profile='historical')])

    def test_platform_skip_keeps_original_source_scope_and_skip_accounting(self):
        module = self.fixture_module()
        module.A.test_one = unittest.skip("invented platform restriction")(module.A.test_one)
        with patch.object(unittest.TestLoader, "loadTestsFromName",
                          return_value=unittest.defaultTestLoader.loadTestsFromModule(module)):
            suite, report = select_suite(self.root, self.policy)
        self.assertEqual(report["selected"], 1)
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(result.skipped[0][1], "invented platform restriction")

    def test_reverse_selection_preserves_all_selected_ids(self):
        module = self.fixture_module()
        self.policy['overrides'] = {}
        with patch.object(unittest.TestLoader, 'loadTestsFromName',
                          side_effect=lambda name: unittest.defaultTestLoader.loadTestsFromModule(module)):
            _, forward = select_suite(self.root, self.policy)
            _, reverse = select_suite(self.root, self.policy, reverse=True)
        self.assertEqual(reverse['test_ids'], forward['test_ids'][::-1])
        self.assertEqual(reverse['selected'], 2)

    def test_unknown_scope_and_missing_classification_fail_before_import(self):
        with patch.object(unittest.TestLoader, 'loadTestsFromName') as load:
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                select_suite(self.root, self.policy, profile='invented')
            with self.assertRaisesRegex(ValueError, 'Every test file'):
                select_suite(self.root, dict(self.policy, files={}))
            load.assert_not_called()

    def test_stale_override_cannot_disappear_from_current_gate(self):
        self.policy['overrides']['tests/test_a.py::A.test_gone'] = 'historical'
        with patch.object(unittest.TestLoader, 'loadTestsFromName') as load:
            with self.assertRaisesRegex(ValueError, 'Stale'):
                select_suite(self.root, self.policy)
            load.assert_not_called()
