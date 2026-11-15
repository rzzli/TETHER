"""Caller roots, rather than serialized receipts, authorize source verification."""
import shutil
import os
import copy
import subprocess
import stat
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case
from tether_engine.serde import ContractError, decode, read_json, write_json, sha256_file
from tether_engine.workflow import run_workflow
from tether_engine.source_access import SourceAccess, local_path, selected_root

DEMO = Path(__file__).resolve().parents[1] / 'src/tether_engine/demo/v2'


class SourceAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        shutil.copytree(DEMO, self.source)
        self.output = self.root / 'run'
        self.build(self.source, self.output)

    def build(self, source, output):
        case = decode(Case, read_json(source / 'case.json'))
        store = load_snapshot(source / 'snapshot.json', case)
        write_run(output, run_workflow(case, store, ExtractiveBackend()), store, None)

    def test_external_sources_require_authority_before_admission(self):
        with patch('tether_engine.artifacts.admit_snapshot', side_effect=AssertionError('unauthorized source read')):
            with self.assertRaisesRegex(ContractError, 'source.root|Source root'):
                verify_run(self.output)

    def test_linked_receipt_is_denied_before_read(self):
        receipt = self.output / 'receipt.json'
        original_stat, original_open = Path.lstat, Path.open
        def linked(path, *args, **kwargs):
            if path == receipt:
                return SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
            return original_stat(path, *args, **kwargs)
        def guarded(path, *args, **kwargs):
            if path == receipt:
                raise AssertionError('linked receipt was opened')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'lstat', new=linked), patch.object(Path, 'open', new=guarded):
            with self.assertRaisesRegex(ContractError, 'Linked source descendant'):
                verify_run(self.output, source_roots=(self.source,))

    def test_explicit_root_permits_source_inclusive_semantics(self):
        answer = verify_run(self.output, source_roots=(self.source,))
        self.assertEqual(answer['assurance'], 'source_inclusive_semantics')

    def test_sibling_prefix_does_not_authorize_originals(self):
        wrong = self.root / 'sour'
        wrong.mkdir()
        with self.assertRaisesRegex(ContractError, 'source.root|Source root'):
            verify_run(self.output, source_roots=(wrong,))

    def test_outputs_only_never_reopens_originals(self):
        shutil.rmtree(self.source)
        answer = verify_run(self.output, verify_sources=False)
        self.assertEqual(answer['source_artifacts_checked'], 0)

    def test_fixed_bundled_demo_still_works_without_grant(self):
        import tether_engine
        output = self.root / 'builtin'
        self.build(Path(tether_engine.__file__).parent / 'demo' / 'v2', output)
        self.assertEqual(verify_run(output)['source_binding'], 'current_originals')

    def test_all_grants_checked_before_first_source_stat(self):
        access = SourceAccess.for_run(self.output, (self.source,))
        with patch.object(Path, 'lstat', side_effect=AssertionError('source stat before complete authority')):
            with self.assertRaisesRegex(ContractError, 'source-root'):
                access.prepare([self.source / 'evidence.json', self.root / 'denied' / 'secret.json'])

    def test_network_device_drive_relative_and_traversal_rejected_without_stat(self):
        with patch.object(Path, 'lstat', side_effect=AssertionError('unsafe path stat')):
            for value in ('\\\\server\\share\\secret', '//server/share/secret', '\\\\?\\C:\\secret',
                          'C:secret', str(self.source / '..' / 'secret'), str(self.source / 'file:stream')):
                with self.subTest(path=value), self.assertRaises(ContractError):
                    local_path(value)

    def test_changed_file_rejected_even_with_identical_bytes(self):
        path = self.source / 'evidence.json'
        files = SourceAccess.for_run(self.output, (self.source,)).prepare([path])
        replacement = self.source / 'replacement.json'
        replacement.write_bytes(path.read_bytes())
        os.replace(replacement, path)
        with self.assertRaisesRegex(ContractError, 'changed after authorization'):
            files.read(path, 64 * 1024 * 1024)

    def test_only_preflighted_paths_are_readable(self):
        files = SourceAccess.for_run(self.output, (self.source,)).prepare([self.source / 'evidence.json'])
        with self.assertRaisesRegex(ContractError, 'preflighted inventory'):
            files.read(self.source / 'case.json', 100000)

    def test_approved_hardlink_source_is_hash_checked(self):
        original = self.source / 'evidence.json'
        link = self.source / 'hardlink.json'
        os.link(original, link)
        files = SourceAccess.for_run(self.output, (self.source,)).prepare([link])
        self.assertEqual(files.read(link, 64 * 1024 * 1024), original.read_bytes())

    def directory_link(self, link, target):
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.addCleanup(os.rmdir, link)
        else:
            link.symlink_to(target, target_is_directory=True)
            self.addCleanup(link.unlink)

    def test_selected_root_junction_is_supported(self):
        link = self.root / 'selected-link'
        self.directory_link(link, self.source)
        self.assertEqual(selected_root(link)[1], self.source)
        answer = verify_run(self.output, source_roots=(link,))
        self.assertEqual(answer['assurance'], 'source_inclusive_semantics')

    def test_descendant_junction_never_grants_access(self):
        link = self.source / 'descendant-link'
        self.directory_link(link, self.root / 'run')
        with self.assertRaisesRegex(ContractError, 'Linked source descendant'):
            SourceAccess.for_run(self.output, (self.source,)).prepare([link / 'inputs.json'])

    def test_caller_selected_run_ancestor_link_is_supported(self):
        link = self.root / 'run-link'
        self.directory_link(link, self.output)
        self.assertEqual(verify_run(link, source_roots=(self.source,))['semantic_consistency'], 'verified')

    def test_raw_parent_and_receipt_need_separate_grant(self):
        raw = self.root / 'raw'
        shutil.copytree(self.source, raw)
        snapshot = read_json(self.source / 'snapshot.json')
        snapshot['raw_root'] = str(raw)
        node = snapshot['sources'][0]
        receipt_path = raw / 'download-receipt.json'
        write_json(receipt_path, dict(status='completed', sha256=node['sha256'], dataset_id=node['dataset_id'],
                                     release_id=node['release_id'], relative_path=node['path'],
                                     bytes=(raw / node['path']).stat().st_size))
        node.update(receipt_path=receipt_path.name, receipt_sha256=sha256_file(receipt_path))
        write_json(self.source / 'snapshot.json', snapshot)
        output = self.root / 'separate-raw-run'
        self.build(self.source, output)
        with patch('tether_engine.artifacts.admit_snapshot', side_effect=AssertionError('source read')):
            with self.assertRaisesRegex(ContractError, 'source-root'):
                verify_run(output, source_roots=(self.source,))
        self.assertEqual(verify_run(output, source_roots=(self.source, raw))['source_binding'], 'current_originals')

    def test_computed_assets_outside_root_cannot_bypass_preflight(self):
        from tests.derivation_fixtures import qualify_projection
        qualify_projection(self.source)
        raw = self.root / 'computed-originals'
        shutil.copytree(self.source, raw)
        snapshot = read_json(self.source / 'snapshot.json')
        snapshot['raw_root'] = str(raw)
        inputs, assets = raw / 'allowed-inputs', raw / 'method-assets'
        inputs.mkdir()
        assets.mkdir()
        original = snapshot['sources'][0]
        shutil.copyfile(raw / original['path'], inputs / 'original.json')
        original['path'] = 'allowed-inputs/original.json'
        asset = copy.deepcopy(original)
        asset_path = assets / 'parameters.json'
        write_json(asset_path, {'fixed': 'fictional registered method asset'})
        asset.update(source_id='method-asset', path='method-assets/parameters.json',
                     sha256=sha256_file(asset_path), role='reference')
        snapshot['sources'].append(asset)
        packet = read_json(self.source / 'evidence.json')
        observation = packet['observations'][0]
        observation['input_refs'].append('method-asset')
        observation['derivation']['assets'] = {'method-asset': asset['sha256']}
        snapshot['artifacts'][0]['input_refs'].append('method-asset')
        write_json(self.source / 'evidence.json', packet)
        snapshot['artifacts'][0]['sha256'] = sha256_file(self.source / 'evidence.json')
        write_json(self.source / 'snapshot.json', snapshot)
        output = self.root / 'computed-run'
        self.build(self.source, output)
        with self.assertRaisesRegex(ContractError, 'source-root'):
            verify_run(output, source_roots=(self.source, inputs))
        self.assertEqual(verify_run(output, source_roots=(self.source, inputs, assets))['derivation_verification'], 'verified')

    def test_legacy_sources_do_not_get_implicit_external_grants(self):
        receipt = read_json(self.output / 'receipt.json')
        receipt['software_version'] = '0.4.0'
        receipt.pop('admission_policy')
        write_json(self.output / 'receipt.json', receipt)
        with self.assertRaisesRegex(ContractError, 'source-root'):
            verify_run(self.output, allow_legacy=True)
        result = verify_run(self.output, allow_legacy=True, source_roots=(self.source,))
        self.assertEqual(result['assurance'], 'byte_integrity')

    def test_expired_hash_deadline_stops_before_open(self):
        files = SourceAccess.for_run(self.output, (self.source,)).prepare([self.source / 'evidence.json'])
        with patch('tether_engine.source_access.read_local', side_effect=AssertionError('read after deadline')):
            with self.assertRaisesRegex(TimeoutError, 'deadline expired'):
                files.digest_size(self.source / 'evidence.json', deadline=0)


if __name__ == '__main__':
    unittest.main()
