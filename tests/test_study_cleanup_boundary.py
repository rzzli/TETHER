"""Parent cleanup must not depend on an unrelated caller exception context."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.study import authority_four_arm as authority
from tether_engine.study import fixed_evidence_smoke as fixed
from tether_engine.study import tokenization as tok
from tests import test_study_authority_four_arm as authority_fixtures
from tests import test_study_tokenization as token_fixtures


class ParentCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The new gate must not depend on another suite creating data/cache.
        with patch.object(token_fixtures, 'TEMP_ROOT', Path(tempfile.gettempdir())):
            token_fixtures.TokenizationArtifactTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        token_fixtures.TokenizationArtifactTests.tearDownClass()

    def authority_run(self, output):
        child = tok._run_child
        with patch.object(tok, '_run_child', side_effect=lambda *args:
                          child(*args, process_factory=authority_fixtures.HundredTokenChild)):
            return authority.smoke(output, token_fixtures.TokenizationArtifactTests.authority,
                                   token_fixtures.TokenizationArtifactTests.roots)

    def assert_close_failure(self, execute):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'parent'
            original = RunJournal.close
            secondary = OSError('parent close fixture')

            def broken(journal):
                original(journal)
                if journal.output == output:
                    raise secondary

            try:
                raise LookupError('unrelated caller exception')
            except LookupError as unrelated:
                with patch.object(RunJournal, 'close', new=broken), \
                        self.assertRaises(OSError) as caught:
                    execute(output)
                self.assertIs(caught.exception, secondary)
                self.assertFalse(hasattr(unrelated, '__notes__'))
            self.assertTrue((output/'receipt.json').is_file())
            self.assertFalse((output/'failure.json').exists())

    def test_fixed_close_error_is_not_attached_to_callers_exception(self):
        self.assert_close_failure(fixed.smoke)

    def test_authority_close_error_is_not_attached_to_callers_exception(self):
        self.assert_close_failure(self.authority_run)

    def test_source_cleanup_failure_still_closes_parent_journal(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'parent'
            source, server = ExitStack(), ExitStack()
            stacks = iter((source, server))
            real_close, journal_close = source.close, RunJournal.close
            calls, closed = [], []
            failure = OSError('late source cleanup fixture')

            def close_source():
                calls.append(True)
                real_close()
                if len(calls) == 2:
                    raise failure

            def close_journal(journal):
                journal_close(journal)
                if journal.output == output:
                    closed.append(True)

            try:
                with patch.object(authority, 'ExitStack', side_effect=lambda: next(stacks, None) or ExitStack()), \
                        patch.object(source, 'close', side_effect=close_source), \
                        patch.object(RunJournal, 'close', new=close_journal), \
                        self.assertRaises(OSError) as caught:
                    self.authority_run(output)
                self.assertIs(caught.exception, failure)
                self.assertEqual(closed, [True])
                self.assertTrue((output/'receipt.json').is_file())
                self.assertFalse((output/'failure.json').exists())
            finally:
                source.close()
                server.close()


if __name__ == '__main__':
    unittest.main()
