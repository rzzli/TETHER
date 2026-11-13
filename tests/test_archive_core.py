"""Relocated byte/source/semantic verification; all data and calls are synthetic."""
import copy
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend
from tether_engine.archive.core import verify_core_archive
from tether_engine.archive.paths import ArchiveResolver
from tether_engine.artifacts import write_run, verify_run
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, decode, read_json, write_json
from tether_engine.workflow import run_workflow

ROOT = Path(__file__).resolve().parents[1]


class ArchiveCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.original = self.base / 'original'
        self.sources = self.original / 'inputs'
        shutil.copytree(ROOT / 'src/tether_engine/demo/v2', self.sources)
        self.case = decode(Case, read_json(self.sources / 'case.json'))
        store = load_snapshot(self.sources / 'snapshot.json', self.case)
        self.output = self.original / 'run'
        journal = RunJournal(self.output)
        try:
            result = run_workflow(self.case, store, ExtractiveBackend(), journal=journal)
            write_run(self.output, result, store, None, journal)
        finally:
            journal.close()

    def relocate(self, legacy=False, current_policy=False):
        receipt = read_json(self.output / 'receipt.json')
        # Synthetic format conversion exercises byte-only legacy compatibility;
        # it is never represented as a historical producer execution.
        if not current_policy:
            receipt.pop('admission_policy', None)
            receipt['software_version'] = '0.1.0' if legacy else '0.4.0'
        if legacy:
            receipt['schema_version'] = 1
            del receipt['outputs']['journal.jsonl']
        write_json(self.output / 'receipt.json', receipt)
        self.anchor = hashlib.sha256((self.output / 'receipt.json').read_bytes()).hexdigest()
        physical = self.base / 'restored'
        project = physical / 'project'
        fixture = physical / 'fixture'
        shutil.copytree(self.original, fixture)
        pairs = []
        for name in receipt['code']:
            old = ROOT / 'src/tether_engine' / name
            new = project / old.relative_to(ROOT)
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(old, new)
            pairs.append((old, new, 'project', new.relative_to(project)))
        if self.original.is_relative_to(ROOT):
            relocated = project / self.original.relative_to(ROOT)
            shutil.copytree(fixture, relocated)
            for old in self.original.rglob('*'):
                if old.is_file():
                    new = relocated / old.relative_to(self.original)
                    pairs.append((old, new, 'project', new.relative_to(project)))
            self.bindings = [dict(root_id='project', logical_root=str(ROOT), physical_root=str(project))]
        else:
            for old in self.original.rglob('*'):
                if old.is_file():
                    new = fixture / old.relative_to(self.original)
                    pairs.append((old, new, 'fixture', new.relative_to(fixture)))
            self.bindings = [dict(root_id='project', logical_root=str(ROOT), physical_root=str(project)),
                             dict(root_id='fixture', logical_root=str(self.original), physical_root=str(fixture))]
        self.files = [dict(logical_path=str(old), root_id=rid, relative_path=relative.as_posix(),
                           sha256=hashlib.sha256(new.read_bytes()).hexdigest(), bytes=new.stat().st_size)
                      for old, new, rid, relative in pairs]
        self.resolver = ArchiveResolver(self.bindings, self.files)
        self.original.rename(self.base / 'unavailable-original')

    def verify(self, resolver=None, anchor=None):
        if not hasattr(self, 'resolver'):
            return verify_run(self.output, anchor)
        return verify_core_archive(str(self.output), resolver or self.resolver,
                                   self.anchor if anchor is None else anchor, code_root=str(ROOT / 'src/tether_engine'))

    def test_legacy_v2_checks_declared_bytes_after_relocation(self):
        self.relocate()
        result = self.verify()
        self.assertEqual(result['semantic_consistency'], 'unavailable_legacy_v2_derivation')
        self.assertEqual(result['source_inventory_completeness'], 'not_replayed')
        self.assertEqual(result['code_archive_integrity'], 'verified_original_pins')
        self.assertFalse(result['archived_code_executed'])
        self.assertEqual(result['scientific_validity'], 'not_established')

    def test_legacy_keeps_unavailable_semantics(self):
        self.relocate(legacy=True)
        self.assertEqual(self.verify()['semantic_consistency'], 'unavailable_legacy_v1')

    def test_receipt_and_code_anchors_are_required(self):
        self.relocate()
        with self.assertRaisesRegex(ContractError, 'anchor'):
            self.verify(anchor='0'*64)
        files = [f for f in self.files if not f['logical_path'].endswith('contracts.py')]
        with self.assertRaises(ContractError):
            self.verify(ArchiveResolver(self.bindings, files))

    def test_missing_packet_or_ancestor_cannot_fall_back(self):
        self.relocate()
        snapshot = read_json(self.base / 'unavailable-original/inputs/snapshot.json')
        for relative in [snapshot['artifacts'][0]['path'], snapshot['sources'][0]['path']]:
            logical = str(self.sources / relative)
            files = [f for f in self.files if self.resolver.logical_key(f['logical_path']) != self.resolver.logical_key(logical)]
            with self.assertRaises(ContractError):
                self.verify(ArchiveResolver(self.bindings, files))

    def test_current_resealed_features_still_fail_semantics(self):
        path = self.output / 'features.json'
        feature = read_json(path)
        feature['values']['genetic_support']['value'] = 0.2
        write_json(path, feature)
        receipt_path = self.output / 'receipt.json'
        receipt = read_json(receipt_path)
        receipt['outputs']['features.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_json(receipt_path, receipt)
        self.anchor = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ContractError, 'feature'):
            verify_run(self.output, self.anchor)

    def test_current_relocated_semantics_are_explicitly_unsupported(self):
        self.relocate(current_policy=True)
        with self.assertRaisesRegex(ContractError, 'Relocated derivation-policy semantic replay is unavailable'):
            self.verify()

    def test_original_files_are_not_opened_by_verifier(self):
        self.relocate()
        actual_open = Path.open

        def guarded(path, *args, **kwargs):
            if path.is_relative_to(self.original) or path.is_relative_to(ROOT / 'src'):
                raise AssertionError('Attempted original-root read: ' + str(path))
            return actual_open(path, *args, **kwargs)

        with patch.object(Path, 'open', guarded):
            self.assertEqual(self.verify()['semantic_consistency'], 'unavailable_legacy_v2_derivation')


if __name__ == '__main__':
    unittest.main()
