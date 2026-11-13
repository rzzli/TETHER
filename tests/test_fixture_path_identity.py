"""Fixtures canonicalize temporary-root aliases before binding original paths."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_archive_core as core
from tests import test_archive_interpretation as interpretation
from tests import test_science_t6_challenge as challenge
from tests import test_study_source_fact_peer as source_fact


class FixturePathIdentityTests(unittest.TestCase):
    def run_with_aliased_temp(self, case):
        original = tempfile.TemporaryDirectory
        aliases = []

        class AliasedTemporaryDirectory:
            def __init__(self, *args, **kwargs):
                self.owner = original(*args, **kwargs)
                real = Path(self.owner.name)
                self.name = str(real / '..' / real.name)
                # The supplied spelling names exactly the same owned directory.
                if Path(self.name).resolve() != real.resolve():
                    self.owner.cleanup()
                    raise AssertionError('Invented temporary alias changed identity')
                aliases.append(self.name)

            def __enter__(self):
                return self.name

            def __exit__(self, *args):
                return self.owner.__exit__(*args)

            def cleanup(self):
                self.owner.cleanup()

        result = unittest.TestResult()
        with patch.object(tempfile, 'TemporaryDirectory', AliasedTemporaryDirectory):
            case.run(result)
        self.assertTrue(aliases, 'Control did not use an aliased temporary root')
        self.assertEqual(result.skipped, [])
        self.assertEqual(result.errors, [], result.errors)
        self.assertEqual(result.failures, [], result.failures)

    def test_core_archive_checks_legacy_bytes_with_aliased_temp_root(self):
        self.run_with_aliased_temp(core.ArchiveCoreTests(
            'test_legacy_v2_checks_declared_bytes_after_relocation'))

    def test_interpretation_checkpoint_gate_with_aliased_temp_root(self):
        self.run_with_aliased_temp(interpretation.ArchiveInterpretationTests(
            'test_recorded_question_requires_original_semantic_checkpoint'))

    def test_challenge_reference_gate_uses_canonical_fixture_root(self):
        self.run_with_aliased_temp(challenge.TopOneTaskTests(
            'test_reference_gate_only_opens_metadata_and_hashes_children'))

    def test_fictional_lock_scope_uses_canonical_fixture_root(self):
        self.run_with_aliased_temp(source_fact.SourceFactPeerBoundaryTests(
            'test_fictional_lock_scope_rejects_files_outside_its_fixture'))

    def test_posix_fixture_replay_uses_canonical_fixture_root(self):
        self.run_with_aliased_temp(source_fact.SourceFactPeerBoundaryTests(
            'test_posix_fixture_replay_preserves_native_fail_closed_boundary'))


if __name__ == '__main__':
    unittest.main()
