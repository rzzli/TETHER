"""Collection must account for missing tests without leaking import side effects."""
import json
import os
from pathlib import Path
import sys
import time
import tempfile
import unittest
from unittest.mock import patch

from tools import test_inventory as inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tests').mkdir()
        (self.root / 'tests/__init__.py').write_text('', encoding='utf-8')

    def source(self, name, body):
        (self.root / 'tests' / (name + '.py')).write_text(body, encoding='utf-8')

    def test_separate_processes_ignore_parent_path_and_global_import_mutation(self):
        self.source('test_a', "import os, sys, unittest\nos.environ['TETHER_CENSUS_MARKER']='leaked'\n"
                    "sys.path.clear()\nclass A(unittest.TestCase):\n def test_a(self): raise AssertionError('must not execute')\n")
        self.source('test_b', "import os, unittest\nassert 'TETHER_CENSUS_MARKER' not in os.environ\n"
                    "class B(unittest.TestCase):\n def test_b(self): raise AssertionError('must not execute')\n")
        with patch.dict(os.environ, {'PYTHONPATH': 'nonexistent-parent-path'}):
            result = inventory.collect(self.root, self.root / 'output')
        self.assertEqual(result['status'], 'collection_complete_not_execution')
        self.assertEqual(result['counts']['unique_test_ids'], 2)
        self.assertEqual(result['tests_executed'], 0)
        self.assertNotIn('TETHER_CENSUS_MARKER', os.environ)
        self.assertFalse(list((self.root / 'tests').rglob('__pycache__')))

    def test_platform_skip_retains_its_declared_method_in_census(self):
        self.source("test_skipped", 'import unittest\nclass A(unittest.TestCase):\n'
                    ' @unittest.skip("invented platform restriction")\n'
                    ' def test_control(self): raise AssertionError("must not execute")\n')
        result = inventory.collect(self.root, self.root / "output")
        self.assertEqual(result["status"], "collection_complete_not_execution")
        self.assertEqual(result["counts"]["uncollected_declarations"], 0)
        self.assertEqual(result["counts"]["unique_test_ids"], 1)
        self.assertEqual(result["tests_executed"], 0)

    def test_missing_import_retains_declared_methods_and_failure(self):
        self.source('test_bad', 'import missing_tether_fixture_dependency\nimport unittest\n'
                    'class Bad(unittest.TestCase):\n def test_missing(self): pass\n')
        result = inventory.collect(self.root, self.root / 'output')
        self.assertEqual(result['status'], 'collection_incomplete')
        self.assertEqual(result['counts']['uncollected_declarations'], 1)
        self.assertEqual(result['failed_modules'], ['tests.test_bad'])
        self.assertIn('missing_tether_fixture_dependency', str(result['modules'][0]['errors']))

    def test_loader_cannot_silently_drop_a_declared_method(self):
        self.source('test_dropped', 'import unittest\nclass A(unittest.TestCase):\n def test_a(self): pass\n'
                    'def load_tests(loader, tests, pattern): return unittest.TestSuite()\n')
        result = inventory.collect(self.root, self.root / 'output')
        self.assertEqual(result['status'], 'collection_incomplete')
        self.assertEqual(result['uncollected_declarations'][0]['method'], 'test_a')

    def test_timeout_and_missing_interpreter_are_not_empty_success(self):
        self.source('test_slow', 'import time\ntime.sleep(2)\n')
        result = inventory.collect(self.root, self.root / 'timed', timeout=0.05)
        self.assertEqual(result['modules'][0]['status'], 'collection_timeout')
        result = inventory.collect(self.root, self.root / 'missing', environments={'tests': self.root / 'missing-python'})
        self.assertEqual(result['status'], 'collection_incomplete')
        self.assertEqual(result['modules'][0]['status'], 'collection_failed')

    def test_stale_destination_preserves_previous_result(self):
        output = self.root / 'output'; output.mkdir()
        marker = output / 'inventory.json'; marker.write_text('original', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            inventory.collect(self.root, output)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'original')

    def test_longest_environment_prefix_and_path_boundary(self):
        env = {'experiments/x': '/one', 'experiments/x/tests': '/two'}
        self.assertEqual(inventory.interpreter_for('experiments/x/tests/test_a.py', env), str(Path('/two').resolve()))
        self.assertEqual(inventory.interpreter_for('experiments/xyz/test_a.py', env), sys.executable)

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object qualification')
    def test_timeout_stops_a_descendant_of_the_interpreter_launcher(self):
        marker = self.root / 'descendant-survived.txt'
        ready = self.root / 'descendant-started.txt'
        child = "import time;from pathlib import Path;time.sleep(2);Path(%r).write_text('survived')" % str(marker)
        self.source('test_child',
                    "import subprocess,sys,time;from pathlib import Path\n"
                    "subprocess.Popen([sys.executable,'-I','-S','-c',%r])\n"
                    "Path(%r).write_text('started')\ntime.sleep(10)\n" % (child, str(ready)))
        result = inventory.collect(self.root, self.root / 'output', timeout=1)
        self.assertTrue(ready.is_file(), 'Control must reach descendant launch before timeout')
        self.assertEqual(result['modules'][0]['status'], 'collection_timeout')
        time.sleep(2)
        self.assertFalse(marker.exists(), 'Timed-out collector left a writable descendant alive')

    def test_empty_source_tree_cannot_report_success(self):
        with self.assertRaisesRegex(ValueError, 'No test sources'):
            inventory.collect(self.root, self.root / 'output')

    def test_explicitly_loadable_nonprefixed_module_is_in_the_census(self):
        self.source('compatibility_checks',
                    'import unittest\nclass Controls(unittest.TestCase):\n'
                    '    def test_compatible(self): pass\n')
        report = inventory.collect(self.root, self.root / 'output')
        self.assertEqual(report['status'], 'collection_complete_not_execution')
        self.assertEqual(report['counts']['declared_methods'], 1)
        self.assertEqual(report['sources'][0]['path'], 'tests/compatibility_checks.py')

    def test_empty_module_and_self_modified_module_cannot_complete_inventory(self):
        self.source('test_empty', '# no tests\n')
        result = inventory.collect(self.root, self.root / 'empty')
        self.assertEqual(result['status'], 'collection_incomplete')
        self.source('test_change', "from pathlib import Path\nPath(__file__).write_text('# replaced')\n")
        result = inventory.collect(self.root, self.root / 'changed')
        self.assertIn('source_changed_during_collection', [m['status'] for m in result['modules']])


if __name__ == '__main__':
    unittest.main()
