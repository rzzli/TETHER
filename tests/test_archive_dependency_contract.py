"""Current builds remain usable without admitting unreviewed semantic code."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.archive import core
from tether_engine.serde import ContractError


class ArchiveDependencyContractTests(unittest.TestCase):
    def test_current_build_has_a_matching_dependency_declaration(self):
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
        self.assertEqual(mismatches, ('ingest.py',))
        with patch.object(core, '_DEPENDENCY_MISMATCHES', mismatches):
            with self.assertRaisesRegex(ContractError, 'Unsupported executing semantic dependencies: ingest.py'):
                core.ensure_supported_semantics()


if __name__ == '__main__':
    unittest.main()
