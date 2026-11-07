"""Stable bounded reads: avoid ceiling-sized allocations without weaker checks."""
from pathlib import Path
import os
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from . import native_records as native


class BoundedReadTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path=Path(temp.name).resolve()/'invented.bin'
        self.path.write_bytes(b'invented')

    def test_empty_small_and_exact_limit_preserve_bytes(self):
        for data in (b'',b'x',b'x'*16384):
            self.path.write_bytes(data)
            self.assertEqual(native.read(self.path),data)
            self.assertEqual(native.read(self.path,len(data)),data)

    def test_read_request_is_bounded_by_verified_file_size(self):
        opened=Path.open;requests=[]
        class Wrapper:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def read(self,size):requests.append(size);return self.stream.read(size)
        with patch.object(Path,'open',lambda path,*args,**kwargs:Wrapper(opened(path,*args,**kwargs))):
            self.assertEqual(native.read(self.path),b'invented')
        self.assertEqual(requests,[len(b'invented')+1])

    def test_oversized_and_nonregular_inputs_rejected(self):
        with self.assertRaises(ValueError):native.read(self.path,1)
        with self.assertRaises(ValueError):native.read(self.path.parent)

    def test_ceiling_must_be_a_nonnegative_integer(self):
        self.path.write_bytes(b'')
        for limit in (float('inf'),float('-inf'),float('nan'),1.0,True,False,-1,'12',None):
            with self.subTest(limit=limit),self.assertRaises(ValueError):native.read(self.path,limit)

    def test_short_read_rejected_even_with_stable_identity(self):
        opened=Path.open
        class Wrapper:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def read(self,size):return self.stream.read(size)[:-1]
        with patch.object(Path,'open',lambda path,*args,**kwargs:Wrapper(opened(path,*args,**kwargs))):
            with self.assertRaises(ValueError):native.read(self.path)

    def test_growth_during_read_rejected(self):
        opened=Path.open;target=self.path
        class Wrapper:
            def __init__(self,stream):self.stream=stream
            def __enter__(self):return self
            def __exit__(self,*args):self.stream.close()
            def fileno(self):return self.stream.fileno()
            def read(self,size):
                with opened(target,'ab') as writer:writer.write(b'growth')
                return self.stream.read(size)
        with patch.object(Path,'open',lambda path,*args,**kwargs:Wrapper(opened(path,*args,**kwargs))):
            with self.assertRaisesRegex(ValueError,'changed during read'):native.read(self.path)

    def test_growth_before_open_rejected(self):
        opened=Path.open
        def changed(path,*args,**kwargs):
            if path==self.path:
                with opened(path,'ab') as writer:writer.write(b'growth-before-open')
            return opened(path,*args,**kwargs)
        with patch.object(Path,'open',changed):
            with self.assertRaisesRegex(ValueError,'before read'):native.read(self.path)

    def test_identity_change_on_second_fstat_rejected(self):
        original=os.fstat;calls=[]
        def changed(fd):
            value=original(fd);calls.append(fd)
            if len(calls)==2:
                return SimpleNamespace(st_dev=value.st_dev,st_ino=value.st_ino,st_size=value.st_size,
                    st_mtime_ns=value.st_mtime_ns,st_ctime_ns=value.st_ctime_ns+1)
            return value
        with patch.object(os,'fstat',changed):
            with self.assertRaisesRegex(ValueError,'changed during read'):native.read(self.path)

    def test_reparse_leaf_and_ancestor_rejected(self):
        original=Path.lstat
        for altered in (self.path,self.path.parent):
            def changed(path,*args,**kwargs):
                value=original(path,*args,**kwargs)
                return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=0x400) if path==altered else value
            with self.subTest(path=altered),patch.object(Path,'lstat',changed):
                with self.assertRaisesRegex(ValueError,'Linked/reparse'):native.read(self.path)


if __name__=='__main__':unittest.main()
