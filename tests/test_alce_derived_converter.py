"""Small invented converter controls; real Windows locks/Torch format are separately qualified."""
from contextlib import nullcontext
import hashlib
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from experiments.alce import derived_converter as c
from tether_engine.serde import ContractError


def proof(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class FakeStorage:
    def __init__(self,raw):self.raw=raw
    def clone(self):return FakeStorage(bytes(self.raw))
    def view(self,dtype):return self
    def as_strided(self,shape,stride,offset):
        return SimpleNamespace(storage=self,shape=shape,stride=stride,offset=offset,requires_grad_=lambda flag:None)


class ConverterControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.scratch=self.root/'scratch';self.scratch.mkdir()
        self.end=time.monotonic()+60
        self.lock=patch.object(c,'stable_files',side_effect=lambda *a,**kw:nullcontext())
        self.lock.start();self.addCleanup(self.lock.stop)

    def test_verified_spool_retains_original_bytes(self):
        source=self.root/'source.bin';source.write_bytes(b'original\0raw'*1000)
        before=proof(source)
        result=c.spool_original(before,self.scratch,deadline=self.end,maximum=100000)
        self.assertEqual(Path(result['path']).read_bytes(),source.read_bytes())
        self.assertEqual(result,dict(before,path=str(self.scratch/source.name)))
        self.assertEqual(proof(source),before)
        c.stable_files.assert_called_once_with([source],deadline=self.end)

    def test_wrong_source_hash_preserves_failed_spool(self):
        source=self.root/'source.bin';source.write_bytes(b'preserve failed bytes')
        bad=dict(proof(source),sha256='0'*64)
        with self.assertRaisesRegex(ContractError,'SHA256'):
            c.spool_original(bad,self.scratch,deadline=self.end,maximum=100)
        self.assertEqual((self.scratch/source.name).read_bytes(),source.read_bytes())

    def test_existing_spool_and_oversized_source_reject_before_copy(self):
        source=self.root/'source.bin';source.write_bytes(b'raw')
        with self.assertRaisesRegex(ContractError,'spool bound'):
            c.spool_original(proof(source),self.scratch,deadline=self.end,maximum=2)
        self.assertEqual(list(self.scratch.iterdir()),[])
        (self.scratch/'prior').write_bytes(b'keep')
        with self.assertRaisesRegex(ContractError,'Empty owned'):
            c.spool_original(proof(source),self.scratch,deadline=self.end,maximum=100)
        self.assertEqual((self.scratch/'prior').read_bytes(),b'keep')

    def pack(self,save=None):
        # Includes negative zero, a NaN payload, a subnormal and an ordinary float.
        raw=bytes.fromhex('000000800100c07f010000000000803f')
        spool=self.root/'spool.bin';spool.write_bytes(b'header'+raw)
        rows=[dict(key=k,dtype='torch.float32',contiguous=True,storage_offset=0,
                   shape=[4],stride=[1],requires_grad=False) for k in ('shared','alias')]
        original=dict(groups=[dict(id=0,offset=6,bytes=16,tensor_ordinals=[0,1])],
                      tensors=rows,state_dict_metadata=None)
        packed=dict(name='packed.bin',group_ids=[0],storage_bytes=16)
        observed={}
        def record(state,stream,**options):
            observed.update(keys=list(state),same_storage=state['shared'].storage is state['alias'].storage,
                raw=state['shared'].storage.raw,options=options,metadata=getattr(state,'_metadata',None))
            if save is not None:return save(state,stream,**options)
            stream.write(b'invented-stock-writer-boundary')
        torch=SimpleNamespace(uint8='uint8',float32='float32',frombuffer=lambda b,**kw:FakeStorage(b),save=record)
        return raw,spool,original,packed,torch,observed

    def test_pack_preserves_order_storage_alias_and_bits(self):
        raw,spool,original,packed,torch,observed=self.pack()
        target=self.root/'packed.bin'
        p=c.write_pack(torch,spool,original,packed,target,deadline=self.end,file_limit=1024)
        self.assertEqual(observed['keys'],['shared','alias'])
        self.assertTrue(observed['same_storage']);self.assertEqual(observed['raw'],raw)
        self.assertEqual(observed['options'],dict(pickle_protocol=2,_use_new_zipfile_serialization=True))
        self.assertEqual(p,proof(target))

    def test_serializer_error_preserves_partial_and_no_retry(self):
        def fail(state,stream,**kw):stream.write(b'partial');raise RuntimeError('stock failure')
        _,spool,original,packed,torch,_=self.pack(fail);target=self.root/'packed.bin'
        with self.assertRaisesRegex(RuntimeError,'stock failure'):
            c.write_pack(torch,spool,original,packed,target,deadline=self.end,file_limit=100)
        self.assertEqual(target.read_bytes(),b'partial')
        with self.assertRaisesRegex(ContractError,'retried'):
            c.write_pack(torch,spool,original,packed,target,deadline=self.end,file_limit=100)

    def test_layout_and_serialized_size_rejection(self):
        _,spool,original,packed,torch,_=self.pack();target=self.root/'packed.bin'
        original['tensors'][0]['contiguous']=False
        with self.assertRaisesRegex(ContractError,'contiguous'):
            c.write_pack(torch,spool,original,packed,target,deadline=self.end,file_limit=100)
        self.assertFalse(target.exists())
        original['tensors'][0]['contiguous']=True
        with self.assertRaisesRegex(ContractError,'serialized'):
            c.write_pack(torch,spool,original,packed,target,deadline=self.end,file_limit=1)
        self.assertTrue(target.exists())

    def test_resource_guards_are_separate_and_strict(self):
        limits=dict(cache_bytes=100,spool_bytes=50)
        good=dict(rss_bytes=1,available_host_bytes=4*c.GIB,cache_bytes=0,spool_bytes=0)
        self.assertEqual(c.ResourceGuard(self.root,limits,lambda:good).capture()['rss_bytes'],1)
        for field,value in [('rss_bytes',4*c.GIB+1),('available_host_bytes',4*c.GIB-1),
                            ('cache_bytes',101),('spool_bytes',51),('rss_bytes',True),('cache_bytes',None)]:
            with self.subTest(field=field,value=value),self.assertRaises(ContractError):
                c.ResourceGuard(self.root,limits,lambda:dict(good,**{field:value})).capture()

    def test_primary_exception_survives_resource_finalization(self):
        samples=iter([dict(rss_bytes=1,available_host_bytes=4*c.GIB,cache_bytes=0,spool_bytes=0),
                      dict(rss_bytes=4*c.GIB+1,available_host_bytes=4*c.GIB,cache_bytes=0,spool_bytes=0)])
        primary=RuntimeError('primary')
        with self.assertRaises(RuntimeError) as caught:
            with c.ResourceGuard(self.root,dict(cache_bytes=100,spool_bytes=50),lambda:next(samples)):
                raise primary
        self.assertIs(caught.exception,primary)
        self.assertTrue(any('Resource finalization' in n for n in primary.__notes__))

    def test_foreign_import_origin_rejects_before_loader(self):
        trusted=self.root/'trusted.py';trusted.write_bytes(b'# trusted execution source\n')
        foreign=self.root/'foreign.py';foreign.write_bytes(trusted.read_bytes())
        with patch.object(c.importlib.util,'find_spec',return_value=SimpleNamespace(origin=str(foreign))):
            with self.assertRaisesRegex(ContractError,'import origin'):
                c.check_import_origin('invented_torch',proof(trusted),self.end)
        with patch.object(c.importlib.util,'find_spec',return_value=SimpleNamespace(origin=str(trusted))):
            c.check_import_origin('invented_torch',proof(trusted),self.end)


if __name__=='__main__':unittest.main()
