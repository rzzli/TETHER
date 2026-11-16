"""A clean source ZIP must not borrow parent Git history or mutate its files."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError
from tools import validate


class ExportValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        for name in ('.gitignore', 'data/.gitignore', 'data/catalog/sources.json', 'data/catalog/policy-v2.json'):
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(validate.ROOT/name, target)
        self.enterContext(patch.object(validate, 'ROOT', self.root))

    def test_real_ignore_and_catalog_checks_need_no_source_git_or_writes(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        result = validate.structural_export_checks()
        self.assertEqual(result['layout'], 'export')
        self.assertFalse(result['source_git_metadata_created'])
        self.assertEqual(result['tracked_scope_files'], 4)
        self.assertFalse((self.root/'.git').exists())
        after = {p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_private_file_in_export_is_rejected(self):
        (self.root/'memory.md').write_text('invented private record')
        with self.assertRaisesRegex(ContractError, 'Internal working record'):
            validate.structural_export_checks()

    def test_missing_ignore_rule_cannot_use_parent_checkout_configuration(self):
        (self.root/'.gitignore').write_text('')
        with self.assertRaisesRegex(ContractError, 'Required ignore missing'):
            validate.structural_export_checks()

    def test_existing_git_metadata_is_rejected_before_enumerating_source(self):
        (self.root/'.git').mkdir()
        with patch.object(Path, 'rglob', side_effect=AssertionError('Source enumerated')):
            with self.assertRaisesRegex(ContractError, 'Git metadata'):
                validate.structural_export_checks()
