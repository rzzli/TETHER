"""Current builds remain usable without admitting unreviewed semantic code."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.archive import core
from tether_engine.serde import ContractError


class ArchiveDependencyContractTests(unittest.TestCase):
    def test_old_semantic_policy_requires_its_original_implementation(self):
        # RP02 deliberately preserves the old resource, instead of changing its
        # hashes to bless a new admission policy under the old identity.
        self.assertEqual(core.POLICY, 'tether-engine-0.4.0-20261106')
        with self.assertRaisesRegex(ContractError, 'Unsupported executing semantic dependencies'):
            core.ensure_supported_semantics()

    def test_stale_module_pin_still_prevents_semantic_verification(self):
        resource = Path(core.__file__).with_name('semantic_dependencies.json')
        declared = json.loads(resource.read_bytes())
        declared['modules']['ingest.py'] = '0' * 64
        captured = json.dumps(declared).encode('utf-8')
        original = Path.read_bytes

        def read(path):
            return captured if path == resource else original(path)

        with patch.object(Path, 'read_bytes', read):
            _, mismatches, _ = core._load_dependency_guard()
        self.assertIn('ingest.py', mismatches)
        with patch.object(core, '_DEPENDENCY_MISMATCHES', ('ingest.py',)):
            with self.assertRaisesRegex(ContractError, 'Unsupported executing semantic dependencies: ingest.py'):
                core.ensure_supported_semantics()


if __name__ == '__main__':
    unittest.main()
