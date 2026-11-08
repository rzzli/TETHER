"""Invented stock-format FP32 files; no Torch imports, models, or real assets."""
from contextlib import nullcontext
import copy
import copyreg
import hashlib
import io
import json
from pathlib import Path
import pickle
import shutil
import struct
import tempfile
import time
import unittest
from unittest.mock import patch,Mock
import zipfile

from experiments.alce import derived_checkpoint as d
from tether_engine.serde import ContractError,canonical,encode


def proof(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(encode(value))+b'\n');return proof(path)


def atom(value):
    if type(value)is str:
        raw=value.encode();return b'X'+struct.pack('<I',len(raw))+raw
    if type(value)is int:return b'J'+struct.pack('<i',value)
    if type(value)is bool:return b'\x88' if value else b'\x89'
    if type(value)is tuple:return b'('+b''.join(atom(x) for x in value)+b't'
    raise AssertionError(value)


def checkpoint(path,rows,storages,*,payload=None,prefix='archive'):
    # Explicit restricted protocol2 grammar, independent of the reader.
    raw=b'\x80\x02ccollections\nOrderedDict\n)R('
    for key,storage,shape,stride in rows:
        persistent=b'('+atom('storage')+b'ctorch\nFloatStorage\n'+atom(storage)+atom('cpu')+atom(len(storages[storage])//4)+b'tQ'
        tensor=b'ctorch._utils\n_rebuild_tensor_v2\n('+persistent+atom(0)+atom(tuple(shape))+atom(tuple(stride))+atom(False)+b'ccollections\nOrderedDict\n)RtR'
        raw+=atom(key)+tensor
    raw+=b'u.'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr(prefix+'/data.pkl',raw if payload is None else payload)
        z.writestr(prefix+'/byteorder',b'little');z.writestr(prefix+'/version',b'3\n')
        for name,value in storages.items():z.writestr(prefix+'/data/'+name,value)
    return proof(path)


def original_rows(path,end):
    metadata=d.checkpoint_metadata(path,deadline=end);rows=[]
    for r in metadata['tensors']:
        rows.append(dict(key=r['key'],shard=path.name,**{k:r[k] for k in d.TENSOR_FIELDS},
            checkpoint_offset=r['offset'],zip_storage=dict(name='archive/data/'+r['storage_key'],offset=r['offset'],bytes=r['bytes']),
            tensor_bytes=r['bytes'],view_start_bytes=0,view_span_bytes=r['bytes'],contiguous=True))
    return rows,metadata


def minimal_plan(root,end):
    source=root/'source.bin';bits=bytes.fromhex('000000800100c07f0000807f01000000')
    checkpoint(source,[('shared','0',[4],[1]),('alias','0',[4],[1]),('last','1',[1],[1])],{'0':bits,'1':b'\0'*4})
    rows,meta=original_rows(source,end)
    groups=[dict(id=i,offset=meta['storages'][str(i)]['offset'],bytes=meta['storages'][str(i)]['bytes'],
                 tensor_ordinals=[0,1] if i==0 else [2]) for i in range(2)]
    outputs=[dict(name=f'pytorch_model-{i+1:05}-of-00002.bin',group_ids=[i],storage_bytes=g['bytes']) for i,g in enumerate(groups)]
    return dict(kind=d.PLAN_KIND,limits=d.LIMITS,original_shards=[dict(name=source.name,proof=proof(source),
                tensors=rows,groups=groups,outputs=outputs,state_dict_metadata=None)]),source,bits


def completed_fixture(root,end):
    """Genuine public lineage/layout/bit checks; only OS/installed runtime metadata is invented."""
    from tests.alce_derived_fixtures import parent_fixture
    from experiments.alce import derived_converter as converter
    from experiments.scifact_multivers_transport.download import Journal
    parent=parent_fixture(root,end);plan=parent['plan'];out=root/'derived';out.mkdir()
    for name in ('checkpoint','audits','scratch'):(out/name).mkdir()
    local=put(out/'PLAN.json',plan);sources=converter.source_pins(end)
    placeholder=put(parent['inputs']/'INVENTED-RUNTIME.json',dict(invented=True,no_optional_import=True))
    runtime=put(parent['inputs']/'RUNTIME.json',dict(interpreter=proof(Path(__import__('sys').executable).resolve()),
        sources=sources,records={'invented':placeholder},torch_sources={k:placeholder for k in ('torch','torch.serialization','torch._utils')},
        psutil_source=placeholder))
    put(out/'REQUEST.json',dict(kind='alce_true_fp32_conversion_request_v1',at_utc='2026-11-07T00:00:00Z',plan=parent['plan_proof'],
        local_plan=local,runtime=runtime,output=str(out),process_limits=converter.PROCESS_LIMITS,automatic_retries=0,inference=False))
    journal=Journal(out/'journal.jsonl');journal.append('conversion_reserved',plan=local,output=str(out));audits=[]
    for ordinal,shard in enumerate(plan['original_shards']):
        journal.append('original_copy_entered',ordinal=ordinal,source=shard['proof'])
        spool=out/'scratch'/shard['name'];shutil.copyfile(shard['proof']['path'],spool);sp=proof(spool)
        journal.append('original_copy_verified',ordinal=ordinal,spool=sp);paths={}
        for packed in shard['outputs']:
            rows=[];storages={}
            for storage_id,gid in enumerate(packed['group_ids']):
                group=shard['groups'][gid]
                with spool.open('rb') as f:f.seek(group['offset']);storages[str(storage_id)]=f.read(group['bytes'])
                for i in group['tensor_ordinals']:
                    tensor=shard['tensors'][i];rows.append((tensor['key'],str(storage_id),tensor['shape'],tensor['stride']))
            target=out/'checkpoint'/packed['name'];paths[packed['name']]=target
            checkpoint(target,rows,storages);journal.append('packed_file_written',ordinal=ordinal,file=proof(target))
        audited=d.verify_spooled_original(plan,shard['name'],spool,paths,deadline=end)
        ap=put(out/'audits'/f'{ordinal:05}.json',audited);audits.append(ap)
        journal.append('original_independently_audited',ordinal=ordinal,audit=ap)
        spool.unlink();journal.append('owned_spool_removed',ordinal=ordinal,path=str(spool))
    for name,p in plan['metadata_files'].items():shutil.copyfile(p['path'],out/'checkpoint'/name)
    put(out/'checkpoint/pytorch_model.bin.index.json',plan['derived_index'])
    sample=dict(rss_bytes=100,available_host_bytes=8*d.GIB,cache_bytes=10000,spool_bytes=0)
    resources=put(out/'RESOURCES.json',dict(process_limits=converter.PROCESS_LIMITS,storage_limits=plan['limits'],
        samples=[sample,sample],wall_seconds=1,scope='Invented observations only'))
    complete=put(out/'COMPLETE.json',dict(kind='alce_true_fp32_conversion_terminal_v1',status='verified_lossless_fp32',plan=local,
        original_audits=audits,originals=len(plan['original_shards']),shards=sum(len(s['outputs']) for s in plan['original_shards']),
        inference=False,automatic_retries=0))
    journal.append('conversion_completed',complete=complete)
    rp=put(out/'RECEIPT.json',dict(kind=d.RECEIPT_KIND,status='verified_lossless_fp32',plan=local,cache_root=str(out/'checkpoint'),
        files={p.relative_to(out).as_posix():proof(p) for p in sorted(out.rglob('*')) if p.is_file()},
        original_audits=audits,resources=resources,source_proofs=sources))
    return dict(parent=parent,root=out,receipt=rp,plan=local)


class CheckpointControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.end=time.monotonic()+120

    def test_restricted_stock_metadata_preserves_key_order_alias_layout(self):
        plan,source,bits=minimal_plan(self.root,self.end);got=d.checkpoint_metadata(source,deadline=self.end)
        self.assertEqual([r['key'] for r in got['tensors']],['shared','alias','last'])
        self.assertEqual(got['tensors'][0]['storage_key'],got['tensors'][1]['storage_key'])
        self.assertEqual(len(got['storages']),2)
        self.assertEqual(d._span_hash(source,got['tensors'][0]['offset'],16,self.end),hashlib.sha256(bits).hexdigest())

    def test_pickle_globals_trailing_metadata_and_nonfloat_rejected(self):
        for i,payload in enumerate((b'\x80\x02cos\nsystem\nX\x04\x00\x00\x00nope\x85R.',
                                   pickle.dumps({},2)+b'ignored',b'\x80\x02ctorch\nDoubleStorage\n.')):
            p=self.root/f'bad{i}.bin';checkpoint(p,[],{},payload=payload)
            with self.subTest(i=i),self.assertRaises((ContractError,pickle.UnpicklingError)):
                d.checkpoint_metadata(p,deadline=self.end)

    def test_cached_pickle_extensions_cannot_bypass_global_allowlist(self):
        callback=Mock(return_value={});key=37;missing=object();prior=copyreg._extension_cache.get(key,missing)
        copyreg._extension_cache[key]=callback
        try:
            for code in (b'\x82'+bytes([key]),b'\x83'+struct.pack('<H',key),b'\x84'+struct.pack('<I',key)):
                callback.reset_mock();path=self.root/'extension.bin';checkpoint(path,[],{},payload=b'\x80\x02'+code+b')R.')
                with self.subTest(opcode=code.hex()):
                    with self.assertRaisesRegex(ContractError,'extension'):d.checkpoint_metadata(path,deadline=self.end)
                    callback.assert_not_called()
        finally:
            if prior is missing:copyreg._extension_cache.pop(key,None)
            else:copyreg._extension_cache[key]=prior

    def test_noncontiguous_view_unreferenced_and_compressed_storages_reject(self):
        p=self.root/'bad.bin';checkpoint(p,[('x','0',[2],[2])],{'0':b'\0'*8})
        with self.assertRaises(ContractError):d.checkpoint_metadata(p,deadline=self.end)
        checkpoint(p,[('x','0',[2],[1])],{'0':b'\0'*8,'1':b'\0'*4})
        with self.assertRaisesRegex(ContractError,'Unreferenced'):d.checkpoint_metadata(p,deadline=self.end)
        with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('archive/data.pkl',b'anything')
        with self.assertRaisesRegex(ContractError,'Stored'):d.checkpoint_metadata(p,deadline=self.end)

    def test_numeric_local_zip_header_must_match_central_directory(self):
        p=self.root/'header.bin';checkpoint(p,[('x','0',[2],[1])],{'0':b'\0'*8});original=p.read_bytes()
        with zipfile.ZipFile(p) as archive:info=archive.getinfo('archive/data/0')
        variants={'name':(info.header_offset+30+len('archive/data/'),ord('1')),
                  'method':(info.header_offset+8,8),'flags':(info.header_offset+6,1),
                  'crc':(info.header_offset+14,original[info.header_offset+14]^1),
                  'size':(info.header_offset+22,original[info.header_offset+22]^1)}
        for name,(offset,byte) in variants.items():
            raw=bytearray(original);raw[offset]=byte;p.write_bytes(raw)
            with self.subTest(field=name),self.assertRaises(ContractError):d.checkpoint_metadata(p,deadline=self.end)

    def test_stock_descriptor_and_zip64_conventions_remain_explicit(self):
        original=self.root/'original.bin';checkpoint(original,[('x','0',[2],[1])],{'0':b'\0'*8})
        with zipfile.ZipFile(original) as archive:members=[(i.filename,archive.read(i)) for i in archive.infolist()]
        class Nonseekable(io.BytesIO):
            def seek(self,*args):raise OSError('Invented nonseekable stock writer')
        for descriptor in (False,True):
            for zip64 in (False,True):
                buffer=Nonseekable() if descriptor else io.BytesIO()
                with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
                    for name,raw in members:
                        with archive.open(name,'w',force_zip64=zip64) as stream:stream.write(raw)
                target=self.root/f'format-{descriptor}-{zip64}.bin';target.write_bytes(buffer.getvalue())
                with self.subTest(descriptor=descriptor,zip64=zip64):
                    got=d.checkpoint_metadata(target,deadline=self.end);self.assertEqual(got['tensors'][0]['key'],'x')
                if descriptor:
                    changed=bytearray(target.read_bytes());row=got['tensors'][0];changed[row['offset']+row['bytes']+4]^=1
                    target.write_bytes(changed)
                    with self.assertRaisesRegex(ContractError,'descriptor'):d.checkpoint_metadata(target,deadline=self.end)

    def packed(self):
        plan,source,bits=minimal_plan(self.root,self.end);spool=self.root/'spool.bin';shutil.copyfile(source,spool)
        paths={};shard=plan['original_shards'][0]
        for i,output in enumerate(shard['outputs']):
            path=self.root/output['name'];paths[output['name']]=path
            rows=[('shared','0',[4],[1]),('alias','0',[4],[1])] if i==0 else [('last','0',[1],[1])]
            checkpoint(path,rows,{'0':bits if i==0 else b'\0'*4})
        return plan,source,spool,paths,bits

    def test_independent_raw_bits_alias_and_spool_binding(self):
        plan,source,spool,paths,bits=self.packed()
        # Portable controls substitute only the explicitly Win32 sharing boundary.
        with patch.object(d,'stable_files',side_effect=lambda *a,**k:nullcontext()) as locked:
            got=d.verify_spooled_original(plan,source.name,spool,paths,deadline=self.end)
            locked.assert_called_once();self.assertEqual(got['outputs'][0]['storages'][0]['sha256'],hashlib.sha256(bits).hexdigest())
        self.assertEqual(proof(source),plan['original_shards'][0]['proof'])

    def test_raw_bit_alias_order_and_spliced_original_mutations_reject(self):
        plan,source,spool,paths,bits=self.packed();p=next(iter(paths.values()));saved=p.read_bytes()
        variations=[([('shared','0',[4],[1]),('alias','0',[4],[1])],{'0':bytes([bits[0]^1])+bits[1:]}),
                    ([('shared','0',[4],[1]),('alias','1',[4],[1])],{'0':bits,'1':bits}),
                    ([('alias','0',[4],[1]),('shared','0',[4],[1])],{'0':bits})]
        with patch.object(d,'stable_files',side_effect=lambda *a,**k:nullcontext()):
            for rows,storages in variations:
                checkpoint(p,rows,storages)
                with self.subTest(keys=[r[0] for r in rows]),self.assertRaises(ContractError):
                    d.verify_spooled_original(plan,source.name,spool,paths,deadline=self.end)
            p.write_bytes(saved);spool.write_bytes(spool.read_bytes()+b'extra')
            with self.assertRaisesRegex(ContractError,'Spool differs'):
                d.verify_spooled_original(plan,source.name,spool,paths,deadline=self.end)


class NativeV2Controls(unittest.TestCase):
    def setUp(self):
        from tests.test_alce_native_worker import WorkerTests
        fixture=WorkerTests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fixture=fixture;self.root=fixture.root;self.job=copy.deepcopy(fixture.job)

    def test_explicit_v2_null_preserves_original_route(self):
        from experiments.alce import native_worker as w
        from tests.test_alce_native_worker import invented_execute
        self.job.update(schema_version=2,kind='alce_native_job_v2',derived_checkpoint=None)
        jp=put(self.root/'V2.json',self.job);got=w.load_job(jp)
        self.assertEqual(got[0]['derived_checkpoint'],None)
        receipt=invented_execute(jp)
        self.assertEqual(w.verify_worker(Path(self.job['output']),jp,self.job,self.fixture.rows,time.monotonic()+15),receipt)

    def test_replay_exact_job_identity_and_proof_rejects_resealed_legacy_or_extra(self):
        from experiments.alce import native_worker as w
        from tests.test_alce_native_worker import invented_execute
        receipt=invented_execute(self.fixture.jp)
        for change in (dict(kind='unknown'),dict(extra=True),dict(schema_version=True)):
            changed=dict(self.job,**change)
            with self.subTest(change=change),self.assertRaises(ContractError):
                w.verify_worker(Path(self.job['output']),self.fixture.jp,changed,self.fixture.rows,time.monotonic()+15)

    def test_derived_route_cannot_use_other_product_or_overlap_root(self):
        from experiments.alce import native_worker as w
        derived=self.root/'derived';derived.mkdir();dp=put(derived/'RECEIPT.json',dict(kind='invented'))
        self.job.update(schema_version=2,kind='alce_native_job_v2',derived_checkpoint=dp,operation='qa')
        jp=put(self.root/'V2.json',self.job)
        with self.assertRaises(ContractError):w.load_job(jp)
        self.assertFalse(Path(self.job['output']).exists())

    def test_derived_native_route_uses_genuine_authority_and_preserves_raw_runtime(self):
        from experiments.alce import native_worker as w
        from tests.test_alce_native_worker import invented_modules,sample
        fixture_root=self.root/'cache-fixture';fixture_root.mkdir();end=time.monotonic()+120
        with patch.object(d,'stable_files',side_effect=lambda *a,**kw:nullcontext()):
            cache=completed_fixture(fixture_root,end)
            self.job.update(schema_version=2,kind='alce_native_job_v2',derived_checkpoint=cache['receipt'],
                            acquisition_receipt=cache['parent']['acquisition'])
            self.job['limits']['seconds']=60;jp=put(self.root/'V2.json',self.job)
            modules=invented_modules(self.fixture.module);original=Mock(side_effect=AssertionError('Original weights route entered'))
            result=w.execute(jp,module_loader=lambda **kw:modules,asset_loader=original,resource_sampler=sample)
            original.assert_not_called()
            self.assertEqual(w.verify_worker(Path(self.job['output']),jp,self.job,self.fixture.rows,end),result)
            config=modules['transformers'].AutoModelForSeq2SeqLM.from_pretrained.call_args
            self.assertEqual(config.args,(str(cache['root']/'checkpoint'),))
            self.assertEqual(config.kwargs['dtype'],'bf16');self.assertFalse(config.kwargs['use_safetensors'])
            self.assertTrue(config.kwargs['local_files_only']);self.assertFalse(config.kwargs['trust_remote_code'])


class CacheAuthorityControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.end=time.monotonic()+120
        lock=patch.object(d,'stable_files',side_effect=lambda *a,**kw:nullcontext());lock.start();self.addCleanup(lock.stop)
        self.fixture=completed_fixture(self.root,self.end)

    def test_complete_derived_authority_uses_no_original_numeric_reads(self):
        f=self.fixture;originals={Path(s['proof']['path']) for s in f['parent']['plan']['original_shards']}
        open_original=Path.open
        def no_original(path,*a,**kw):
            self.assertNotIn(path,originals,'Original numerical source must not be reread at native admission')
            return open_original(path,*a,**kw)
        with patch.object(Path,'open',no_original):
            value=d.verify_cache(f['plan'],f['receipt'],deadline=self.end)
            asset=d.DerivedModelAssets(f['parent']['acquisition'],'true_nli',derived_checkpoint=f['receipt'],deadline=self.end)
            asset.revalidate(self.end);asset.revalidate(self.end,full=True)
            d.verify_asset_provenance(f['parent']['acquisition'],f['receipt'],asset.provenance(),deadline=self.end)
        self.assertEqual(len(value['files']),12);self.assertFalse(list((f['root']/'scratch').iterdir()))

    def test_nonfull_runtime_checks_do_not_decode_or_hash_payloads_again(self):
        f=self.fixture;asset=d.DerivedModelAssets(f['parent']['acquisition'],'true_nli',derived_checkpoint=f['receipt'],deadline=self.end)
        with patch.object(d,'checkpoint_metadata',side_effect=AssertionError('Repeated pickle decode')),\
             patch.object(d,'_hash_and_spans',side_effect=AssertionError('Repeated payload hashing')),\
             patch.object(d,'prepare_plan',side_effect=AssertionError('Repeated ancestry replay')):
            asset.revalidate(self.end)
            put(Path(f['parent']['acquisition']['path']).parent/'FAILED.json',dict(failed=True))
            with self.assertRaisesRegex(ContractError,'Late acquisition'):asset.revalidate(self.end)

    def test_model_root_revision_receipt_or_parent_substitution_rejected(self):
        f=self.fixture;model=encode(d.verify_cache(f['plan'],f['receipt'],deadline=self.end)['provenance'])
        for change in ('root','revision','receipt','parent','omitted_parent'):
            changed=copy.deepcopy(model)
            if change=='root':changed['local_checkpoint']=str(self.root)
            if change=='revision':changed['revision']='0'*40
            if change=='receipt':changed['derived_checkpoint']['receipt']['sha256']='0'*64
            if change=='parent':changed['derived_checkpoint']['original_files'].pop(next(iter(changed['derived_checkpoint']['original_files'])))
            if change=='omitted_parent':changed.pop('acquisition')
            with self.subTest(change=change),self.assertRaises(ContractError):
                d.verify_asset_provenance(f['parent']['acquisition'],f['receipt'],changed,deadline=self.end)

    def test_late_numeric_mutation_missing_audit_and_extra_empty_directory_reject(self):
        f=self.fixture;asset=d.DerivedModelAssets(f['parent']['acquisition'],'true_nli',derived_checkpoint=f['receipt'],deadline=self.end)
        extra=f['root']/'extra';extra.mkdir()
        with self.assertRaises(ContractError):asset.revalidate(self.end)
        extra.rmdir();audit=f['root']/'audits/00000.json';saved=audit.read_bytes();audit.write_bytes(saved+b' ')
        with self.assertRaises(ContractError):asset.revalidate(self.end)
        audit.write_bytes(saved);path=next((f['root']/'checkpoint').glob('*.bin'));raw=bytearray(path.read_bytes())
        metadata=d.checkpoint_metadata(path,deadline=self.end);raw[metadata['tensors'][0]['offset']]^=1;path.write_bytes(raw)
        with self.assertRaises(ContractError):d.verify_cache(f['plan'],f['receipt'],deadline=self.end)

    def test_parent_manifest_revision_change_fails_before_model_modules(self):
        f=self.fixture;manifest=Path(f['parent']['plan']['source_controls']['manifest']['path'])
        raw=json.loads(manifest.read_bytes());raw['assets'][0]['revision']['value']='0'*40;put(manifest,raw)
        with self.assertRaises(ContractError):d.derived_admission(f['parent']['acquisition'],f['receipt'],deadline=self.end)

    def test_resealed_storage_digest_must_match_current_derived_bits(self):
        from experiments.scifact_multivers_transport.download import Journal
        f=self.fixture;root=f['root'];audit=json.loads((root/'audits/00000.json').read_bytes())
        audit['outputs'][0]['storages'][0]['sha256']='0'*64
        ap=put(root/'audits/00000.json',audit)
        complete=json.loads((root/'COMPLETE.json').read_bytes());complete['original_audits'][0]=ap
        cp=put(root/'COMPLETE.json',complete)
        events=[json.loads(line) for line in (root/'journal.jsonl').read_bytes().splitlines()]
        (root/'journal.jsonl').unlink();journal=Journal(root/'journal.jsonl')
        for row in events:
            details=row['details']
            if row['event']=='original_independently_audited' and details['ordinal']==0:details['audit']=ap
            if row['event']=='conversion_completed':details['complete']=cp
            journal.append(row['event'],**details)
        receipt=json.loads((root/'RECEIPT.json').read_bytes());receipt['original_audits'][0]=ap
        receipt['files']={p.relative_to(root).as_posix():proof(p) for p in root.rglob('*') if p.is_file() and p!=root/'RECEIPT.json'}
        rp=put(root/'RECEIPT.json',receipt)
        with self.assertRaisesRegex(ContractError,'storage|bits'):
            d.verify_cache(f['plan'],rp,deadline=self.end)


if __name__=='__main__':unittest.main()
