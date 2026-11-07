"""Invented wheel inventories prevent stale build-cache namespace leakage."""
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from tether_engine import __version__
from tether_engine.serde import ContractError
from tools.validate import validate_engine_wheel


class WheelNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'invented.whl'
        self.metadata = 'tether_target_engine-'+__version__+'.dist-info'
        self.names = ['tether_engine/demo/v2/case.json', 'tether_engine/demo/case.json',
                      self.metadata+'/METADATA', self.metadata+'/WHEEL', self.metadata+'/RECORD']

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
        self.assertEqual(validate_engine_wheel(self.path)['members'], 6)

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

    def test_missing_demo_or_distribution_metadata_is_rejected(self):
        for name in self.names:
            with self.subTest(name=name):
                self.write([member for member in self.names if member != name])
                with self.assertRaises(ContractError):
                    validate_engine_wheel(self.path)
