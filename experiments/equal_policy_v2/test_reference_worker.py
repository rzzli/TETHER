"""Qualification and dispatch safeguards with invented installations/records."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.equal_policy_v2 import reference, worker


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[2] / 'data/cache/equal-policy-v2-reference-tests'
        base.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.python = self.root / 'environment/Scripts/python.exe'
        self.python.parent.mkdir(parents=True)
        self.python.write_bytes(b'fictional interpreter')
        self.modules, proofs = {}, []
        for name, version in (('tether_engine', '0.4.0'), ('tether', '0.6.0')):
            package = self.root / 'environment/Lib/site-packages' / name
            package.mkdir(parents=True)
            entry = package / '__init__.py'
            entry.write_text('__version__ = ' + repr(version) + '\n')
            module = ModuleType(name)
            module.__file__, module.__version__ = str(entry), version
            self.modules[name] = module
            wheel = self.root / 'wheels' / (name + '.whl')
            wheel.parent.mkdir(exist_ok=True)
            wheel.write_bytes(b'fictional qualified wheel ' + name.encode())
            proofs.append(dict(path=str(wheel), distribution={'tether_engine': 'tether-target-engine', 'tether': 'tether-target-agents'}[name],
                record_verified=True, sha256=sha(wheel), bytes=wheel.stat().st_size,
                source_sha256={name + '/__init__.py': sha(entry)}))
        presentation = ModuleType('tether._presentation')
        presentation.code_proof = lambda: dict(code={}, method='fictional')
        self.modules['tether._presentation'] = presentation
        self.document = dict(status='PASS', versions={'tether-target-engine': '0.4.0',
            'tether-target-agents': '0.6.0'}, wheel_proofs=proofs)
        self.save()
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules, self.modules).start()
        patch.object(sys, 'executable', str(self.python)).start()

    def save(self):
        (self.root / 'QUALIFICATION.json').write_text(json.dumps(self.document))

    def test_qualified_runtime_captures_versions_and_actual_payload(self):
        observed = reference.trusted_runtime(self.root)
        self.assertEqual(observed['versions'], dict(tether='0.6.0', tether_engine='0.4.0'))
        self.assertEqual(len(observed['wheels']), 2)
        self.assertEqual(observed['qualification']['sha256'], sha(self.root / 'QUALIFICATION.json'))

    def test_previous_runtime_pair_is_not_requalified_by_renaming(self):
        self.modules['tether'].__version__ = '0.5.2'
        self.modules['tether_engine'].__version__ = '0.3.13'
        self.document['versions'] = {'tether-target-engine': '0.3.13', 'tether-target-agents': '0.5.2'}
        self.save()
        with self.assertRaisesRegex(ValueError, 'version pair'):
            reference.trusted_runtime(self.root)

    def test_mixed_or_unsupported_versions_rejected(self):
        self.modules['tether'].__version__ = '0.5.2'
        with self.assertRaisesRegex(ValueError, 'version pair'):
            reference.trusted_runtime(self.root)

    def test_unqualified_installation_rejected(self):
        self.document['status'] = 'FAILED'
        self.save()
        with self.assertRaisesRegex(ValueError, 'qualification'):
            reference.trusted_runtime(self.root)

    def test_wheel_mutation_rejected(self):
        (self.root / 'wheels/tether_engine.whl').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'wheel bytes'):
            reference.trusted_runtime(self.root)

    def test_installed_payload_cannot_requalify_itself(self):
        Path(self.modules['tether_engine'].__file__).write_text('# changed since qualification\n')
        with self.assertRaisesRegex(ValueError, 'payload differs'):
            reference.trusted_runtime(self.root)

    def test_product_outside_requested_installation_rejected(self):
        self.modules['tether_engine'].__file__ = str(self.root / 'elsewhere/tether_engine/__init__.py')
        with self.assertRaisesRegex(ValueError, 'outside'):
            reference.trusted_runtime(self.root)


class WorkerTests(unittest.TestCase):
    def test_explicit_registry_uses_versioned_full_validators_and_original_controls(self):
        expected = dict(tether=('equal_policy_v2.reference', 'validate_bundle'),
            independent=('equal_policy_v2.independent', 'validate_bundle'),
            hash_schema=('equal_policy.controls', 'hash_schema'),
            reject_all=('equal_policy.controls', 'reject_all'))
        self.assertEqual(worker.IMPLEMENTATION_MODULES, expected)
        for name, (module, function) in expected.items():
            sentinel = object()
            with patch.object(worker.importlib, 'import_module',
                              return_value=SimpleNamespace(**{function: sentinel})) as importer:
                _, observed = worker._implementation(name)
                self.assertIs(observed, sentinel)
                importer.assert_called_once_with(module)

    def test_network_and_oracle_access_are_rejected(self):
        for event, args in (('socket.connect', ()), ('socket.getaddrinfo', ()),
                            ('open', ('oracle.json',)), ('open', ('oracle-secret.json',))):
            with self.assertRaises(PermissionError):
                worker.forbid_network(event, args)

    def test_unknown_arm_does_not_default_to_independent(self):
        with self.assertRaises(KeyError):
            worker._implementation('misspelled')


if __name__ == '__main__':
    unittest.main()
