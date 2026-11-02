"""Validation prerequisite failures must remain inspectable without running tests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import validate


class ValidationFailureReportTests(unittest.TestCase):
    def test_structural_error_retains_failed_report(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'validation.json'
            with patch.object(validate, 'structural_checks', side_effect=ValueError('invented invalid catalog')), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = validate.main(['--mode', 'core', '--report', str(report)])
            self.assertEqual(result, 1)
            payload = json.loads(report.read_text())
            self.assertEqual(payload['status'], 'failed')
            self.assertEqual(payload['stage'], 'structural')
            self.assertEqual(payload['error']['type'], 'ValueError')
            self.assertNotIn('tests', payload)

    def test_interrupt_retains_stage_and_is_unsuccessful(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'validation.json'
            with patch.object(validate, 'structural_checks', return_value={}), \
                 patch.object(validate, 'powershell_check', side_effect=KeyboardInterrupt), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = validate.main(['--mode', 'core', '--report', str(report)])
            self.assertEqual(result, 130)
            payload = json.loads(report.read_text())
            self.assertEqual(payload['status'], 'interrupted')
            self.assertEqual(payload['stage'], 'powershell_syntax')

    def test_existing_report_rejected_before_expensive_work(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'validation.json'
            original = b'{"preserve":"original"}\n'
            report.write_bytes(original)
            with patch.object(validate, 'structural_checks') as structural, \
                 patch.object(validate, 'powershell_check', side_effect=RuntimeError('unexpected work after existing report')):
                with self.assertRaises(FileExistsError):
                    validate.main(['--mode', 'core', '--report', str(report)])
                structural.assert_not_called()
            self.assertEqual(report.read_bytes(), original)
