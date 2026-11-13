"""Legacy receipts authenticate declared bytes, never current derivations."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tether_engine.artifacts import RUN_FILES, receipt_policy, verify_run
from tether_engine.archive.core import verify_core_archive
from tether_engine.archive.paths import ArchiveResolver
from tether_engine.serde import ContractError, canonical, fingerprint, read_json, write_json


class LegacyDerivationVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'run'
        self.output.mkdir()
        self.raw = self.root / 'source.json'
        self.raw.write_bytes(b'{"unverified_old_content":true}')
        # Deliberately not a current contract: byte verification must not decode
        # these fields or lend a forged computation a semantic guarantee.
        inputs = {'case': {'legacy_fixture': True}, 'configuration': {}}
        for name in RUN_FILES:
            (self.output / name).write_bytes(b'{}')
        write_json(self.output / 'inputs.json', inputs)
        event = {'sequence': 0, 'previous_sha256': None, 'event': 'legacy_fixture', 'details': {}}
        event['sha256'] = fingerprint(event)
        trace = canonical(event) + b'\n'
        for name in ('trace.jsonl', 'journal.jsonl'):
            (self.output / name).write_bytes(trace)
        self.code = self.root / 'code'
        self.code.mkdir()
        names = ('__init__.py', '__main__.py', 'agents.py', 'artifacts.py', 'chrono.py', 'cli.py',
                 'contracts.py', 'evaluation.py', 'features.py', 'ledger.py', 'scorer.py',
                 'serde.py', 'workflow.py', 'journal.py', 'provenance.py', 'semantics.py')
        for name in names:
            (self.code / name).write_bytes(b'# synthetic original code bytes; never executed\n')
        self.receipt = dict(schema_version=2, software_version='0.4.0',
            outputs={name: self.sha(self.output / name) for name in RUN_FILES},
            input_fingerprint=fingerprint(inputs),
            sources=[dict(artifact_id='declared-source', path=str(self.raw), sha256=self.sha(self.raw))],
            code={name: self.sha(self.code / name) for name in names})
        self.seal()

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def seal(self):
        write_json(self.output / 'receipt.json', self.receipt)
        self.anchor = self.sha(self.output / 'receipt.json')

    def resolver(self):
        files = [dict(logical_path=str(p), root_id='fixture', relative_path=p.relative_to(self.root).as_posix(),
                      sha256=self.sha(p), bytes=p.stat().st_size)
                 for p in self.root.rglob('*') if p.is_file()]
        return ArchiveResolver([dict(root_id='fixture', logical_root=str(self.root), physical_root=str(self.root))], files)

    def test_legacy_never_calls_current_admission_or_semantics(self):
        with (patch('tether_engine.artifacts.admit_snapshot', side_effect=AssertionError('current admission')),
             patch('tether_engine.artifacts.check_semantics', side_effect=AssertionError('current semantics')),
             patch('tether_engine.artifacts.decode', side_effect=AssertionError('current decoder'))):
            result = verify_run(self.output, self.anchor)
        self.assertEqual(result['semantic_consistency'], 'unavailable_legacy_v2_derivation')
        self.assertEqual(result['derivation_verification'], 'unavailable_legacy_v2_derivation')
        self.assertEqual(result['source_inventory_completeness'], 'not_replayed')
        self.assertEqual(result['source_binding'], 'declared_original_bytes_verified')
        self.assertEqual(self.sha(self.output / 'receipt.json'), self.anchor)

    def test_legacy_declared_source_and_output_tampering_fail(self):
        self.raw.write_bytes(b'changed')
        with self.assertRaisesRegex(ContractError, 'Source integrity'):
            verify_run(self.output, self.anchor)
        (self.output / 'prediction.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ContractError, 'output integrity'):
            verify_run(self.output, self.anchor, verify_sources=False)

    def test_receipt_anchor_and_unknown_policy_fail(self):
        with self.assertRaisesRegex(ContractError, 'anchored receipt'):
            verify_run(self.output, '0' * 64)
        for patch_fields in ({'software_version': '0.5.0'}, {'admission_policy': 'tether.derivation.v1'},
                             {'software_version': '99.0.0'}, {'schema_version': 3}):
            with self.subTest(fields=patch_fields), self.assertRaises(ContractError):
                receipt_policy(dict(self.receipt, **patch_fields))

    def test_missing_declared_parent_does_not_claim_complete_inventory(self):
        self.receipt['sources'] = []
        self.seal()
        result = verify_run(self.output, self.anchor)
        self.assertEqual(result['source_artifacts_checked'], 0)
        self.assertEqual(result['source_inventory_completeness'], 'not_replayed')
        self.assertNotEqual(result['semantic_consistency'], 'verified')

    def test_archive_bytes_do_not_require_current_frozen_dependencies(self):
        with (patch('tether_engine.archive.core.ensure_supported_semantics', side_effect=AssertionError('old semantics')),
             patch('tether_engine.archive.core.decode', side_effect=AssertionError('live decoder'))):
            result = verify_core_archive(str(self.output), self.resolver(), self.anchor, code_root=str(self.code))
        self.assertEqual(result['semantic_consistency'], 'unavailable_legacy_v2_derivation')
        self.assertEqual(result['code_archive_integrity'], 'verified_original_pins')
        self.assertEqual(result['source_inventory_completeness'], 'not_replayed')
        self.assertFalse(result['archived_code_executed'])


if __name__ == '__main__':
    unittest.main()
