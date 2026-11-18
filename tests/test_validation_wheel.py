"""Invented wheel inventories prevent stale build-cache namespace leakage."""
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from tether_engine import __version__
from tether_engine.serde import ContractError
from tools.validate import validate_engine_wheel, validate_wrapper_wheel


class WheelNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'invented.whl'
        self.metadata = 'tether_target_engine-'+__version__+'.dist-info'
        self.names = ['tether_engine/demo/v2/case.json', 'tether_engine/demo/case.json',
                      'tether_engine/schemas/native-receipt-v2.json',
                      'tether_engine/schemas/journal-envelope-v1.json',
                      'tether_engine/schemas/generated-claim-response-v1.json',
                      'tether_engine/schemas/generated-span-selection-v2.json',
                      'tether_engine/schemas/portable-bundle-v1.json',
                      self.metadata+'/METADATA', self.metadata+'/WHEEL', self.metadata+'/RECORD']
        self.names += ['tether_engine/study/'+name for name in ('__init__.py', 'proofs.py', 'stable_read.py')]

    def write(self, names):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.path, 'w') as archive:
                for name in names:
                    info = zipfile.ZipInfo(name)
                    info.filename = name  # Preserve adversarial separators on Windows.
                    archive.writestr(info, b'invented unit payload')

    def test_only_current_runtime_and_matching_metadata_are_accepted(self):
        self.write(self.names+['tether_engine/__init__.py'])
        self.assertEqual(validate_engine_wheel(self.path)['members'], len(self.names) + 1)

    def test_unexpected_namespace_and_stale_metadata_are_rejected(self):
        for name in ('old_engine/__init__.py', 'tests/test_secret.py', 'tether/__init__.py',
                     'tether_target_engine-0.0.0.dist-info/METADATA'):
            with self.subTest(name=name):
                self.write(self.names+[name])
                with self.assertRaises(ContractError):
                    validate_engine_wheel(self.path)

    def test_unsafe_and_duplicate_members_are_rejected(self):
        for name in ('tether_engine/../unexpected.py', '/tether_engine/x.py',
                     'tether_engine\\x.py', 'tether_engine//x.py', self.names[0]):
            with self.subTest(name=name):
                self.write(self.names+[name])
                with self.assertRaises(ContractError):
                    validate_engine_wheel(self.path)

    def test_missing_required_package_members_are_rejected(self):
        for name in self.names:
            with self.subTest(name=name):
                self.write([member for member in self.names if member != name])
                with self.assertRaises(ContractError):
                    validate_engine_wheel(self.path)

    def test_stale_research_drivers_and_resources_cannot_enter_core_wheel(self):
        for member in ('tether_engine/study/session.py', 'tether_engine/study/__main__.py',
                       'tether_engine/study/resources/answers.json'):
            with self.subTest(member=member):
                self.write(self.names+[member])
                with self.assertRaisesRegex(ContractError, 'study'):
                    validate_engine_wheel(self.path)

    def test_missing_compatibility_shims_cannot_be_a_valid_slim_wheel(self):
        self.write([name for name in self.names if not name.startswith('tether_engine/study/')])
        with self.assertRaisesRegex(ContractError, 'missing'):
            validate_engine_wheel(self.path)

    def test_wrapper_inventory_requires_entrypoints_and_excludes_legacy_launchers(self):
        from tether import __version__ as wrapper_version
        metadata = 'tether_target_agents-'+wrapper_version+'.dist-info'
        names = ['tether/'+name+'.py' for name in ('__init__', '__main__', '_cli', '_aliases',
                                                   '_presentation', '_catalog_binding', 'api')]
        names.append('tether/py.typed')
        names += [metadata+'/'+name for name in ('METADATA', 'WHEEL', 'RECORD')]
        self.write(names)
        self.assertEqual(validate_wrapper_wheel(self.path)['members'], len(names))
        for member in ('tether/study/__main__.py', 'tether/study/native_diagnostic.py'):
            self.write(names+[member])
            with self.assertRaisesRegex(ContractError, 'study'):
                validate_wrapper_wheel(self.path)
        self.write([name for name in names if name != 'tether/_cli.py'])
        with self.assertRaisesRegex(ContractError, 'missing'):
            validate_wrapper_wheel(self.path)
