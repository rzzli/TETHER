"""The validation command must fail when required checks fail or disappear."""
import io
import tempfile
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
