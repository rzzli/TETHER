"""No live roots, inference or network are needed for archive path regressions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.archive.paths import ArchiveResolver, from_envelope, join, logical_key
from asof.serde import ContractError


class ArchivePathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = b'preserved bytes'
        (self.root / 'object').write_bytes(self.data)
        self.bindings = [dict(root_id='code', logical_root='Q:/missing/repo', physical_root=str(self.root))]
        self.files = [dict(logical_path='Q:/missing/repo/src/code.py', root_id='code',
                          relative_path='object', sha256=hashlib.sha256(self.data).hexdigest(), bytes=len(self.data))]

    def test_windows_identity_and_no_original_fallback(self):
        resolver = ArchiveResolver(self.bindings, self.files)
        self.assertEqual(resolver.read_bytes('q:\\MISSING\\repo\\src\\CODE.py'), self.data)
        self.assertEqual(resolver.verify_file(self.files[0]['logical_path']), self.root/'object')
        with self.assertRaises(ContractError):
            resolver.resolve('Q:/missing/repository/src/code.py')
        with self.assertRaises(ContractError):
            resolver.resolve(str(self.root/'object'))

    def test_posix_case_sensitive_and_component_join(self):
        self.assertNotEqual(logical_key('/repo/A'), logical_key('/repo/a'))
        self.assertEqual(join('Q:\\missing\\repo', 'src/file.py'), 'Q:\\missing\\repo/src/file.py')
        self.assertEqual(logical_key('D:/one'), logical_key('d:\\ONE'))

    def test_unsafe_paths(self):
        for value in ['D:relative', 'D:/a/../b', 'D:/a/./b', '//server/share', '\\\\server\\share',
                      'D:/file:stream', '/a//b', '/a/../b', 'D:/a.', 'D:/NUL', 'D:/COM1.txt']:
            with self.subTest(value=value), self.assertRaises(ContractError):
                logical_key(value)
        for value in ['../escape', '/absolute', 'D:/drive', 'a:ads', 'a//b', 'a/.']:
            with self.subTest(value=value), self.assertRaises(ContractError):
                join('D:/repo', value)

    def test_root_collisions(self):
        other = self.root/'second';other.mkdir()
        for logical in ['q:/MISSING/repo', 'Q:/missing/repo/nested', 'Q:/missing']:
            bindings = self.bindings + [dict(root_id='second', logical_root=logical, physical_root=str(other))]
            with self.subTest(logical=logical), self.assertRaises(ContractError):
                ArchiveResolver(bindings, self.files)
        with self.assertRaises(ContractError):
            ArchiveResolver(self.bindings + [dict(root_id='raw', logical_root='E:/raw', physical_root=str(other))], self.files)

    def test_duplicate_logical_and_foreign_roots(self):
        for row in [dict(self.files[0], logical_path='q:/MISSING/repo/src/CODE.py'),
                    dict(self.files[0], logical_path='Q:/missing/elsewhere/code.py'),
                    dict(self.files[0], root_id='unknown')]:
            with self.assertRaises(ContractError):
                ArchiveResolver(self.bindings, self.files + [row])

    def test_hash_size_missing_and_mutable_input_isolation(self):
        resolver = ArchiveResolver(self.bindings, self.files)
        self.files[0]['sha256'] = '0'*64
        self.assertEqual(resolver.read_bytes('Q:/missing/repo/src/code.py'), self.data)
        (self.root/'object').write_bytes(b'changed')
        with self.assertRaises(ContractError):resolver.verify_file('Q:/missing/repo/src/code.py')
        (self.root/'object').unlink()
        with self.assertRaises(FileNotFoundError):resolver.resolve('Q:/missing/repo/src/code.py')

    def test_reparse_denied_without_platform_privileges(self):
        original = Path.lstat
        target = self.root/'object'
        def spoof(path):
            info = original(path)
            if path == target:
                class Reparse:
                    st_mode = info.st_mode
                    st_file_attributes = 0x400
                return Reparse()
            return info
        resolver = ArchiveResolver(self.bindings, self.files)
        with patch.object(Path, 'lstat', spoof), self.assertRaises(ContractError):
            resolver.resolve('Q:/missing/repo/src/code.py')

    def test_envelope_anchor_and_caller_roots(self):
        doc = dict(schema_version=1, resolver_version=1,
                   roots=[dict(root_id='code', logical_root='Q:/missing/repo')],
                   runs=[dict(run_id='old', receipt_sha256='a'*64, files=self.files)])
        path = self.root/'envelope.json'
        path.write_text(json.dumps(doc))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        resolver = from_envelope(path, digest, {'code':self.root}, 'old')
        self.assertEqual(resolver.read_bytes(self.files[0]['logical_path']), self.data)
        with self.assertRaises(ContractError):from_envelope(path,'0'*64,{'code':self.root},'old')
        with self.assertRaises(ContractError):from_envelope(path,digest,{},'old')
        doc['roots'][0]['physical_root'] = str(self.root)
        path.write_text(json.dumps(doc));digest=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ContractError):from_envelope(path,digest,{'code':self.root},'old')

    def test_same_logical_code_different_run_content(self):
        old = ArchiveResolver(self.bindings,self.files)
        data = b'other version';(self.root/'other').write_bytes(data)
        files = [dict(self.files[0],relative_path='other',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())]
        new = ArchiveResolver(self.bindings,files)
        self.assertEqual(old.read_bytes(self.files[0]['logical_path']),self.data)
        self.assertEqual(new.read_bytes(self.files[0]['logical_path']),data)

    def test_concurrent_mutation_is_not_accepted(self):
        resolver = ArchiveResolver(self.bindings,self.files)
        original = __import__('os').fstat
        calls = []
        def changing(fd):
            info = original(fd);calls.append(fd)
            if len(calls) == 2:
                class Changed:
                    st_dev, st_ino, st_size = info.st_dev, info.st_ino, info.st_size
                    st_mtime_ns, st_ctime_ns = info.st_mtime_ns + 1, info.st_ctime_ns
                return Changed()
            return info
        with patch('asof.archive.paths.os.fstat', changing), self.assertRaises(ContractError):
            resolver.read_bytes(self.files[0]['logical_path'])

    def test_conflicting_cas_alias_and_bool_size_denied(self):
        for item in [dict(self.files[0], logical_path='Q:/missing/repo/other.py',sha256='b'*64),
                     dict(self.files[0],logical_path='Q:/missing/repo/other.py',bytes=True),
                     dict(self.files[0],logical_path='Q:/missing/repo/other.py',relative_path='NUL')]:
            with self.assertRaises(ContractError):ArchiveResolver(self.bindings,self.files+[item])

    def test_layout_only_for_root_and_excluded_missing_nodes(self):
        resolver = ArchiveResolver(self.bindings, self.files)
        self.assertEqual(resolver.layout_path('q:/MISSING/repo'), self.root)
        excluded = 'Q:/missing/repo/Future/not-collected.json'
        self.assertEqual(resolver.layout_path(excluded), self.root/'Future/not-collected.json')
        with self.assertRaises(ContractError):resolver.read_bytes(excluded)
        with self.assertRaises(ContractError):resolver.verify_file(excluded)
        with self.assertRaises(ContractError):resolver.layout_path('Q:/missing/repository/file')
        with self.assertRaises(ContractError):resolver.layout_path('Q:/missing/repo/../escape')
        self.assertEqual(resolver.layout_path(self.files[0]['logical_path']), self.root/'object')

    def test_declared_spelling_and_immutable_entries(self):
        resolver = ArchiveResolver(self.bindings, self.files)
        self.assertEqual(resolver.declared_path('q:/MISSING/repo/src/CODE.py'), self.files[0]['logical_path'])
        self.assertEqual(resolver.declared_path('q:/MISSING/repo'), self.bindings[0]['logical_root'])
        with self.assertRaises(ContractError):resolver.declared_path('Q:/missing/repo/unknown')
        with self.assertRaises(TypeError):resolver.file_entries[0]['bytes'] = 0

    def test_layout_reparse_rejected_even_without_registered_file(self):
        resolver = ArchiveResolver(self.bindings, self.files)
        original = Path.lstat
        def spoof(path):
            if path == self.root/'future':
                class Reparse:
                    st_mode = 0
                    st_file_attributes = 0x400
                return Reparse()
            return original(path)
        with patch.object(Path, 'lstat', spoof), self.assertRaises(ContractError):
            resolver.layout_path('Q:/missing/repo/future/absent.json')

    def test_envelope_rejects_unsupported_versions_duplicate_roots_and_runs(self):
        base = dict(schema_version=1, resolver_version=1,
                    roots=[dict(root_id='code',logical_root='Q:/missing/repo')],
                    runs=[dict(run_id='old',receipt_sha256='a'*64,files=self.files)])
        variants = [dict(base,schema_version=True), dict(base,resolver_version=2),
                    dict(base,roots=base['roots']*2),dict(base,runs=base['runs']*2)]
        path = self.root/'envelope.json'
        for doc in variants:
            path.write_text(json.dumps(doc)); digest=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ContractError):from_envelope(path,digest,{'code':self.root},'old')
        path.write_text('{"schema_version":1,"schema_version":1}')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ContractError):from_envelope(path,digest,{},'old')


if __name__ == '__main__':
    unittest.main()
