"""Invented ALCE rows only; no released dataset or reference payloads are read."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.alce import data_views as d
from tether_engine.serde import ContractError, canonical


def put(path, value):
    path.write_bytes(canonical(value)+b'\n')
    return proof(path)


def proof(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def invented(family, ordinal):
    row = dict(id=f'{family}-{ordinal}', question=f'Invented {family} question {ordinal}?',
        docs=[dict(title=f'Title{i}', text=f'Invented passage{i}', answers_found=[i == 6],
                   oracle_rank=7-i, id={'forbidden_nested':'REF_SECRET'}) for i in range(7)],
        annotations=[dict(long_answer='REF_SECRET_A'),dict(long_answer='REF_SECRET_B')],
        answer='REF_SECRET', qa_pairs=[dict(question='REF_SECRET_Q',short_answers=['REF_SECRET_A'])],
        claims=['REF_SECRET_C'], answers=[['REF_SECRET_A']], arbitrary_reference='REF_SECRET_X')
    return row


class ViewsTests(unittest.TestCase):
    def test_hardlinked_source_requires_independent_copy(self):
        source=self.root/'installed-source.py';alias=self.root/'cache-alias.py'
        source.write_bytes(b'VALUE = 1\n');os.link(source,alias)
        self.assertGreater(source.stat().st_nlink,1)
        with self.assertRaisesRegex(ContractError,'Single regular source file'):
            d._hash(source,time.monotonic()+10)
        alias.unlink()
        self.assertEqual(d._hash(source,time.monotonic()+10),proof(source))

    def setUp(self):
        workspace = Path(__file__).resolve().parents[1] / 'data/cache'
        workspace.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=workspace.resolve(), prefix='alce-invented-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.raw = {f:canonical([invented(f,i) for i in range(2)]) for f in d.FAMILIES}
        self.archive = self.root/'original.tar'
        self.tar()
        self.sources = {n:put(self.root/n,dict(invented_source=n)) for n in ('run.py','eval.py')}
        self.bind()

    def tar(self, extra=()):
        with tarfile.open(self.archive,'w',format=tarfile.USTAR_FORMAT) as archive:
            for f in d.FAMILIES:
                info=tarfile.TarInfo(d.MEMBERS[f]);info.size=len(self.raw[f])
                archive.addfile(info,io.BytesIO(self.raw[f]))
            for info,raw in extra:
                info.size=len(raw);archive.addfile(info,io.BytesIO(raw))

    def bind(self):
        self.ap=proof(self.archive)
        asset=dict(id='archive',destination='ALCE-data.tar',expected_bytes=self.ap['bytes'],
            digest=dict(algorithm='sha256',kind='content',value=self.ap['sha256']),
            revision=dict(kind='git_commit',value='1'*40),metadata_proof=self.sources['run.py'],rights_reference='invented')
        manifest=put(self.root/'ACQUISITION-MANIFEST.json',dict(kind='alce_acquisition_manifest_v1',assets=[asset],limits=dict(total_seconds=30)))
        entry=dict(asset,path=self.ap['path'],bytes=self.ap['bytes'],sha256=self.ap['sha256'],status='completed',attempts=1)
        worker=put(self.root/'ACQUISITION-WORKER.json',dict(kind='alce_acquisition_worker_receipt_v1',
            status='completed',manifest=manifest,files=[entry],hard_parent_supervision=True))
        (self.root/'stdout.bin').write_bytes(b'');(self.root/'stderr.bin').write_bytes(b'')
        process=put(self.root/'PROCESS.json',dict(returncode=0,supervision=dict(
            schema_version=1,method='tether.process_envelope.v1',limits=dict(timeout_seconds=29,max_output_bytes=4*d.BLOCK),
            termination_reason='exited',execution_elapsed_seconds=.1,total_elapsed_seconds=.2,
            retained_stdout_bytes=0,retained_stderr_bytes=0,observed_stdout_bytes=0,observed_stderr_bytes=0,
            observed_counts_are_lower_bounds=False,pipe_eof=dict(stdout=True,stderr=True),
            process_started=True,process_reaped=True,cleanup_errors=[])))
        self.receipt=put(self.root/'ACQUISITION-RECEIPT.json',dict(kind='alce_acquisition_receipt_v1',status='verified',
            manifest=manifest,worker_receipt=worker,process=process,automatic_retries=0,range_resume=False,payload_hashes_rechecked=True))

    def prepare(self, **kw):
        return d.prepare(self.ap,self.receipt,'archive',self.root/'prepared',
            identity_fields={f:'id' for f in d.FAMILIES},source_proofs=self.sources,**kw)

    def test_complete_projection_is_original_order_and_reconstructs(self):
        value=self.prepare();result=d.verify_preparation(value['root'],value['receipt_sha256'])
        self.assertEqual(dict(result['counts']),dict(asqa=2,qampari=2,eli5=2))
        for family in d.FAMILIES:
            p=self.root/'prepared'/f'generation/{family}.json'
            rows=d.load_generation(proof(p))
            self.assertEqual(len(rows),2)
            self.assertNotIn(b'REF_SECRET',p.read_bytes())
            self.assertEqual([x['text'] for x in rows[0]['docs']],[f'Invented passage{i}' for i in range(5)])
            self.assertEqual([x['citation_position'] for x in rows[0]['docs']],[1,2,3,4,5])
            self.assertEqual((self.root/'prepared'/f'evaluation/{family}.json').read_bytes(),self.raw[family])
            with self.assertRaises(TypeError):rows[0]['question']='mutated'

    def test_generation_reader_opens_no_evaluator_archive_or_coordinator_file(self):
        self.prepare();allowed=self.root/'prepared/generation/asqa.json';p=proof(allowed)
        original=Path.open;opened=[]
        def guarded(path,*args,**kwargs):
            self.assertEqual(path,allowed);opened.append(path)
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):rows=d.load_generation(p)
        self.assertEqual(len(rows),2);self.assertEqual(opened,[allowed])

    def test_resealed_projection_substitution_rejected_against_original(self):
        self.prepare();root=self.root/'prepared';p=root/'generation/asqa.json'
        rows=json.loads(p.read_bytes());rows[0]['docs'][0]['text']='fabricated source'
        changed=put(p,rows);receipt=json.loads((root/'RECEIPT.json').read_bytes())
        receipt['files']['generation/asqa.json']=changed
        rp=put(root/'RECEIPT.json',receipt)
        with self.assertRaisesRegex(ContractError,'projection differs'):
            d.verify_preparation(root,rp['sha256'])

    def test_generation_allowlist_rejects_nested_reference_field(self):
        self.prepare();p=self.root/'prepared/generation/asqa.json'
        rows=json.loads(p.read_bytes());rows[0]['docs'][0]['answers_found']=[True]
        with self.assertRaisesRegex(ContractError,'allowlist'):d.load_generation(put(p,rows))

    def test_identity_absence_is_explicit_and_null_or_conflicts_reject(self):
        row=invented('asqa',0);row.pop('id')
        def run(v,field=None):
            return d.project(canonical([v]),family='asqa',member=d.MEMBERS['asqa'],archive_sha256='a'*64,identity_field=field)
        a=run(row);self.assertEqual(a['schedule'][0]['identity']['kind'],'question_sha256_fallback')
        for value in (None,False,{},'present'):
            with self.subTest(value=value),self.assertRaises(ContractError):run(dict(row,id=value))
        with self.assertRaises(ContractError):run(dict(row,id='a',qid='b'),'id')

    def test_duplicate_ids_questions_and_malformed_reference_shapes_reject(self):
        for mutation in ('id','question','qa_pairs','annotations'):
            rows=[invented('asqa',i) for i in range(2)]
            if mutation in ('id','question'):rows[1][mutation]=rows[0][mutation]
            else:rows[0][mutation]=[]
            with self.subTest(mutation=mutation),self.assertRaises(ContractError):
                d.project(canonical(rows),family='asqa',member=d.MEMBERS['asqa'],archive_sha256='a'*64,identity_field='id')

    def test_empty_and_short_document_lists_preserve_all_cases(self):
        rows=[invented('eli5',i) for i in range(2)];rows[0]['docs']=[];rows[1]['docs']=rows[1]['docs'][:2]
        value=d.project(canonical(rows),family='eli5',member=d.MEMBERS['eli5'],archive_sha256='b'*64,identity_field='id')
        self.assertEqual([len(x['docs']) for x in value['generation']],[0,2])

    def test_malformed_and_partial_archive_keep_failure_no_receipt(self):
        self.raw['asqa']=b'[{"question":"a","question":"b"}]';self.tar();self.bind()
        with self.assertRaises(ContractError):self.prepare()
        self.assertTrue((self.root/'prepared/FAILURE.json').is_file())
        self.assertFalse((self.root/'prepared/RECEIPT.json').exists())

    def test_tar_links_sparse_extensions_traversal_aliases_and_duplicates_reject(self):
        cases=[]
        for typ in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.GNUTYPE_SPARSE,tarfile.XHDTYPE):
            info=tarfile.TarInfo('bad');info.type=typ;info.linkname='other' if typ in (tarfile.SYMTYPE,tarfile.LNKTYPE) else ''
            cases.append((info,b''))
        for name in ('../escape','/absolute','a/../b','data/NUL.txt','data/alias.','data\\alias',d.MEMBERS['asqa']):
            cases.append((tarfile.TarInfo(name),b'{}'))
        for index,extra in enumerate(cases):
            with self.subTest(index=index):
                self.tar([extra]);self.bind()
                with self.assertRaises((ContractError,tarfile.TarError)):
                    d._scan(self.ap,d.MEMBERS,d.Limits(),time.monotonic()+30,lambda f,c,s:list(c))

    def test_case_collision_in_implicit_parent_is_rejected(self):
        self.tar([(tarfile.TarInfo('Data/other.json'),b'{}')]);self.bind()
        with self.assertRaisesRegex(ContractError,'collid|alias'):
            d._scan(self.ap,d.MEMBERS,d.Limits(),time.monotonic()+30,lambda f,c,s:list(c))

    def test_missing_family_or_altered_acquisition_binding_rejected(self):
        with self.assertRaises(ContractError):self.prepare(members={f:d.MEMBERS[f] for f in ('asqa','qampari')})
        receipt=json.loads((self.root/'ACQUISITION-RECEIPT.json').read_bytes());receipt['status']='failed'
        self.receipt=put(self.root/'ACQUISITION-RECEIPT.json',receipt)
        with self.assertRaises(ContractError):self.prepare()

    def test_transport_failure_markers_dominate_verified_receipt(self):
        for name in ('FAILED.json','SUPERVISOR-FAILED.json','STALLED.json'):
            path=self.root/name;path.write_bytes(b'{}')
            try:
                with self.subTest(name=name),self.assertRaises(ContractError):
                    d._acquisition(self.ap,self.receipt,'archive',time.monotonic()+30)
            finally:path.unlink()

    def test_transport_process_must_be_bound_successful_reaped_and_closed(self):
        original=json.loads((self.root/'PROCESS.json').read_bytes())
        for field in ('returncode','process_reaped','pipe_eof','timeout_seconds'):
            value=copy.deepcopy(original)
            if field=='returncode':value[field]=1
            elif field=='pipe_eof':value['supervision'][field]['stdout']=False
            elif field=='timeout_seconds':value['supervision']['limits'][field]=31
            else:value['supervision'][field]=False
            pp=put(self.root/'PROCESS.json',value)
            rp=json.loads((self.root/'ACQUISITION-RECEIPT.json').read_bytes());rp['process']=pp
            anchor=put(self.root/'ACQUISITION-RECEIPT.json',rp)
            with self.subTest(field=field),self.assertRaises(ContractError):
                d._acquisition(self.ap,anchor,'archive',time.monotonic()+30)

    def test_verification_preflight_time_is_not_reset_after_request(self):
        value=self.prepare(limits=d.Limits(seconds=30));now=[100.0];original=d._read
        def delayed(p,maximum,end):
            raw=original(p,maximum,end)
            if Path(p['path']).name=='REQUEST.json':now[0]=132.0
            return raw
        with patch.object(d.time,'monotonic',lambda:now[0]),patch.object(d,'_read',delayed),self.assertRaises(TimeoutError):
            d.verify_preparation(value['root'],value['receipt_sha256'])

    def test_late_same_size_acquisition_stream_change_prevents_sealing(self):
        (self.root/'stdout.bin').write_bytes(b'ok!\n')
        process=json.loads((self.root/'PROCESS.json').read_bytes())
        for key in ('retained_stdout_bytes','observed_stdout_bytes'):process['supervision'][key]=4
        rp=json.loads((self.root/'ACQUISITION-RECEIPT.json').read_bytes())
        rp['process']=put(self.root/'PROCESS.json',process)
        self.receipt=put(self.root/'ACQUISITION-RECEIPT.json',rp)
        original=d._scan
        def change(*args,**kwargs):
            value=original(*args,**kwargs);(self.root/'stdout.bin').write_bytes(b'bad\n');return value
        with patch.object(d,'_scan',change),self.assertRaises(ContractError):self.prepare()
        self.assertFalse((self.root/'prepared/RECEIPT.json').exists())

    def test_overwrite_protection_and_source_mutation(self):
        value=self.prepare();before=proof(self.root/'prepared/RECEIPT.json')
        with self.assertRaises(ContractError):self.prepare()
        self.assertEqual(proof(self.root/'prepared/RECEIPT.json'),before)
        (self.root/'run.py').write_bytes(b'changed')
        with self.assertRaises(ContractError):d.verify_preparation(value['root'],value['receipt_sha256'])

    def test_output_budget_failure_is_retained(self):
        with self.assertRaises(ContractError):self.prepare(limits=d.Limits(output_bytes=4000))
        self.assertTrue((self.root/'prepared/FAILURE.json').is_file())
        self.assertFalse((self.root/'prepared/RECEIPT.json').exists())

    def test_concurrent_output_claim_has_one_owner_and_no_overwrite(self):
        def attempt():
            try:return self.prepare()
            except (ContractError,FileExistsError):return None
        with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(lambda _:attempt(),range(2)))
        self.assertEqual(sum(v is not None for v in values),1)
        success=next(v for v in values if v is not None)
        self.assertEqual(d.verify_preparation(success['root'],success['receipt_sha256'])['status'],'source_projection_verified')

    def test_late_unlisted_output_is_rejected_on_final_revalidation(self):
        value=self.prepare();root=Path(value['root']);original=d._hash
        receipt_calls=0
        def changed(path,end):
            nonlocal receipt_calls
            result=original(path,end)
            if Path(path)==root/'RECEIPT.json':
                receipt_calls+=1
                if receipt_calls==2:(root/'orphan.json').write_bytes(b'{}')
            return result
        with patch.object(d,'_hash',changed),self.assertRaises(ContractError):
            d.verify_preparation(root,value['receipt_sha256'])

    def test_unknown_nonfinite_metadata_and_invalid_limits_reject(self):
        raw=self.raw['asqa'].replace(b'"arbitrary_reference":"REF_SECRET_X"',b'"arbitrary_reference":1e999')
        with self.assertRaises(ContractError):
            d.project(raw,family='asqa',member=d.MEMBERS['asqa'],archive_sha256='a'*64,identity_field='id')
        for value in (False,-1,float('inf'),1.5):
            with self.subTest(value=value),self.assertRaises(ContractError):d.Limits(member_bytes=value)

    def test_large_nonselected_member_streams_beyond_packet_limit(self):
        class Zeros:
            def read(self,n):return b'\0'*n
        with tarfile.open(self.archive,'w',format=tarfile.USTAR_FORMAT) as archive:
            for family in d.FAMILIES:
                info=tarfile.TarInfo(d.MEMBERS[family]);info.size=len(self.raw[family]);archive.addfile(info,io.BytesIO(self.raw[family]))
            info=tarfile.TarInfo('other.bin');info.size=65*1024**2;archive.addfile(info,Zeros())
        self.bind();sizes=[]
        original=Path.open
        class Checked:
            def __init__(self,file):self.file=file
            def read(self,n=-1):
                self_check.assertGreater(n,0);self_check.assertLessEqual(n,d.BLOCK);sizes.append(n);return self.file.read(n)
            def __getattr__(self,name):return getattr(self.file,name)
            def __enter__(self):return self
            def __exit__(self,*args):return self.file.__exit__(*args)
        self_check=self
        def opened(path,*args,**kwargs):
            value=original(path,*args,**kwargs)
            return Checked(value) if path==self.archive and args==('rb',) else value
        with patch.object(Path,'open',opened):
            inv=d._scan(self.ap,d.MEMBERS,d.Limits(),time.monotonic()+30,lambda f,c,s:list(c))
        self.assertGreater(inv['expanded_file_bytes'],64*1024**2);self.assertTrue(sizes)


if __name__ == '__main__':
    unittest.main()
