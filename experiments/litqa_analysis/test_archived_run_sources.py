"""Exact archived producer sources support verification, never execution."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.litqa_analysis import envelopes as e, reconstruct_run as r
from experiments.litqa_analysis.invented_run_fixtures import InventedRuns


class ArchivedRunSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = InventedRuns()
        cls.addClassCleanup(cls.fixtures.close)
        cls.frame = e.load(cls.fixtures.primary_path / 'FRAME.json')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        files = {}
        for index, name in enumerate(self.frame['code_pins']):
            target = self.root / f'{index:03d}.py'
            target.write_bytes((e.REPO / name).read_bytes())
            files[name] = e.proof(target)
        self.manifest = dict(schema_version=1, kind='sc04_executed_source_archive_v1',
            original_repository_root=str(e.REPO), files=files)
        self.descriptor = self.publish()

    def publish(self):
        target = self.root / 'MANIFEST.json'
        target.write_bytes(e.canonical(self.manifest) + b'\n')
        return dict(path=str(target), sha256=e.digest(target.read_bytes()))

    def verified(self):
        return e.verify_run(self.fixtures.primary_path, self.fixtures.primary_sha,
                            source_archive=self.descriptor)

    def test_explicit_archive_reconstructs_without_current_producer_sources(self):
        baseline = r.reconstruct(self.fixtures.primary_path, self.fixtures.primary_sha)
        original = e.proof
        forbidden = {e.REPO / name for name in self.frame['code_pins']}
        def archive_only(path):
            if Path(path) in forbidden:
                raise FileNotFoundError('Invented retired working-tree source')
            return original(path)
        with patch.object(e, 'proof', side_effect=archive_only):
            value = r.reconstruct(self.fixtures.primary_path, self.fixtures.primary_sha,
                                  source_archive=self.descriptor)
        self.assertEqual(value['records'], baseline['records'])
        self.assertEqual(value['source_cases'], baseline['source_cases'])
        self.assertEqual(value['executed_source_archive']['sha256'], self.descriptor['sha256'])
        self.assertEqual(value['executed_source_archive']['original_repository_root'], str(e.REPO))

    def test_archive_is_never_an_implicit_fallback(self):
        original = e.proof
        absent = e.REPO / next(iter(self.frame['code_pins']))
        def missing(path):
            if Path(path) == absent:
                raise FileNotFoundError('Invented absent producer')
            return original(path)
        with patch.object(e, 'proof', side_effect=missing), self.assertRaises(FileNotFoundError):
            e.verify_run(self.fixtures.primary_path, self.fixtures.primary_sha)

    def test_omitted_archived_source_cannot_use_matching_working_copy(self):
        self.manifest['files'].pop(next(iter(self.manifest['files'])))
        self.descriptor = self.publish()
        with self.assertRaises(ValueError):
            self.verified()

    def test_archive_rejects_a_different_execution_root(self):
        self.manifest['original_repository_root'] = str(self.root)
        self.descriptor = self.publish()
        with self.assertRaises(ValueError):
            self.verified()

    def test_changed_archive_after_envelope_verification_is_rejected(self):
        envelope = self.verified()
        path = Path(self.manifest['files']['experiments/litqa_comparison/codecs.py']['path'])
        path.write_bytes(path.read_bytes() + b'\n# Invented post-verification mutation\n')
        with self.assertRaises(ValueError):
            r.primary_verified(envelope)

    def test_default_source_bindings_cannot_be_substituted(self):
        envelope = e.verify_run(self.fixtures.primary_path, self.fixtures.primary_sha)
        value = deepcopy(envelope)
        value['executed_source_proofs']['experiments/litqa_comparison/codecs.py']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            r.primary_verified(value)

    def test_same_byte_source_copy_requires_explicit_archive(self):
        envelope = e.verify_run(self.fixtures.primary_path, self.fixtures.primary_sha)
        name = 'experiments/litqa_comparison/codecs.py'
        copied = self.root / 'same-bytes.py'
        copied.write_bytes((e.REPO / name).read_bytes())
        envelope['executed_source_proofs'][name] = e.proof(copied)
        with self.assertRaises(ValueError):
            r.code_proof(envelope, name)


class CatalogSourceRoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo_patch = patch.object(r, 'REPO', self.root)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)

    def envelope(self, source):
        admission = self.root / 'experiments/litqa_comparison/admission.py'
        admission.parent.mkdir(parents=True, exist_ok=True)
        admission.write_text(source, encoding='utf-8')
        adapter = self.root / 'experiments/labbench/retired_adapter.py'
        adapter.parent.mkdir(parents=True, exist_ok=True)
        adapter.write_bytes(b'raise AssertionError("Archived sources must never execute")\n')
        proofs = {'experiments/litqa_comparison/admission.py': e.proof(admission),
                  'experiments/labbench/retired_adapter.py': e.proof(adapter)}
        return dict(kind='primary',frame=dict(code_pins={name: value['sha256'] for name, value in proofs.items()}),
                    executed_source_proofs=proofs)

    def test_supplied_catalog_comes_from_its_own_pinned_admission(self):
        envelope = self.envelope('from experiments.labbench.retired_adapter import DEFAULT_CATALOG\n')
        other = self.root / 'experiments/labbench/supplied_adapter.py'
        other.write_text('# Different supplied catalog fixture\n', encoding='utf-8')
        supplied = self.root / 'experiments/litqa_supplied/admission.py'
        supplied.parent.mkdir(parents=True)
        supplied.write_text('from experiments.labbench.supplied_adapter import DEFAULT_CATALOG\n', encoding='utf-8')
        for name, path in (('experiments/litqa_supplied/admission.py', supplied),
                           ('experiments/labbench/supplied_adapter.py', other)):
            envelope['executed_source_proofs'][name] = e.proof(path)
            envelope['frame']['code_pins'][name] = e.proof(path)['sha256']
        envelope['kind'] = 'supplied'
        self.assertEqual(r.catalog_code_proof(envelope), e.proof(other))

    def test_catalog_role_comes_from_pinned_import_without_importing_module(self):
        envelope = self.envelope('from experiments.labbench.retired_adapter import DEFAULT_CATALOG\n')
        value = r.catalog_code_proof(envelope)
        self.assertEqual(value, envelope['executed_source_proofs']['experiments/labbench/retired_adapter.py'])

    def test_ambiguous_or_unpinned_catalog_import_is_rejected(self):
        for source in (
            'from experiments.labbench.missing_adapter import DEFAULT_CATALOG\n',
            'from outside.retired_adapter import DEFAULT_CATALOG\n',
            'from experiments.labbench.retired_adapter import DEFAULT_CATALOG\n' * 2,
            'from experiments.labbench.retired_adapter import DEFAULT_CATALOG as REPLACEMENT\n',
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                r.catalog_code_proof(self.envelope(source))


if __name__ == '__main__':
    unittest.main()
