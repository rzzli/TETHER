"""Diagnostic output does not change failure accounting or permit partial success."""
import io
import unittest
from tools import validate


class LiveValidationTests(unittest.TestCase):
    def test_error_trace_is_available_before_final_print_errors(self):
        stream = io.StringIO()
        result = validate.LiveErrorResult(stream, True, 0)
        class Broken(unittest.TestCase):
            def runTest(self):
                raise RuntimeError('invented fixture error')
        Broken().run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIn('RuntimeError: invented fixture error', stream.getvalue())
        self.assertFalse(validate.successful_tests(result, 'core'))
        self.assertFalse(validate.successful_tests(result, 'full'))

    def test_failfast_stops_next_test_and_partial_result_remains_failed(self):
        events = []
        class Broken(unittest.TestCase):
            def runTest(self):
                events.append('failed')
                self.fail('invented assertion')
        class Later(unittest.TestCase):
            def runTest(self):
                events.append('later')
        stream = io.StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=0, failfast=True, resultclass=validate.LiveErrorResult)
        result = runner.run(unittest.TestSuite([Broken(), Later()]))
        self.assertEqual(events, ['failed'])
        self.assertEqual(result.testsRun, 1)
        self.assertEqual(len(result.failures), 1)
        self.assertIn('Captured assertion failure:', stream.getvalue())
        self.assertFalse(validate.successful_tests(result, 'full'))


if __name__ == '__main__':
    unittest.main()
