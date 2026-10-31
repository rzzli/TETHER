import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from asof.archive.restore import materialize, stable_copy, verify
from asof.serde import ContractError

class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
    def write(self,name,doc):
        path=self.base/name
        path.write_text(json.dumps(doc),encoding='utf-8')
        return path,hashlib.sha256(path.read_bytes()).hexdigest()
    def inputs(self):
        payload=b'{}'
        digest=hashlib.sha256(payload).hexdigest()
        (self.base/'objects').mkdir()
        (self.base/'objects'/digest).write_bytes(payload)
        entry=dict(logical_path='D:/project/runs/demo/receipt.json',sha256=digest,bytes=2,object='objects/'+digest,role='run',run='core_v2')
        cp,ch=self.write('checkpoint.json',dict(schema_version=1,kind='recovery_checkpoint',repository_logical_root='D:/project',raw_logical_root='E:/raw',entries=[entry],runs=[dict(kind='core_v2',logical_root='D:/project/runs/demo',receipt_sha256=digest)]))
        rec,rh=self.write('recovery.json',dict(checkpoint_sha256=ch,requirements=[]))
        sup,sh=self.write('supplement.json',dict(prior_recovery_sha256=rh,recovered=[]))
        return [cp,ch,rec,rh,sup,sh]
    def test_materialization_preserves_sealed_bytes_and_no_overwrite(self):
        args=self.inputs(); dest=self.base/'restored'
        result=materialize(*args,dest)
        self.assertEqual((dest/'runs/core_v2/project/runs/demo/receipt.json').read_bytes(),b'{}')
        doc=json.loads(Path(result['envelope']).read_text())
        self.assertNotIn('physical_root',doc['roots'][0])
        with self.assertRaises(FileExistsError): materialize(*args,dest)
    def test_historical_overlay_uses_pinned_supplement(self):
        args=self.inputs()
        old=b'old code'; new=b'new code'
        oldhash=hashlib.sha256(old).hexdigest(); newhash=hashlib.sha256(new).hexdigest()
        for digest,payload in [(oldhash,old),(newhash,new)]:
            (self.base/'objects'/digest).write_bytes(payload)
        cp=json.loads(args[0].read_text())
        cp['entries'].append(dict(logical_path='D:/project/src/test.py',sha256=newhash,bytes=len(new),object='objects/'+newhash,role='repository',run=None))
        args[0].write_text(json.dumps(cp)); args[1]=hashlib.sha256(args[0].read_bytes()).hexdigest()
        rec=dict(checkpoint_sha256=args[1],requirements=[dict(run='core_v2',logical_path='D:/project/src/test.py',sha256=oldhash,status='unavailable',origin='receipt.code')])
        args[2].write_text(json.dumps(rec)); args[3]=hashlib.sha256(args[2].read_bytes()).hexdigest()
        sup=dict(prior_recovery_sha256=args[3],recovered=[dict(sha256=oldhash,bytes=len(old),object='objects/'+oldhash)])
        args[4].write_text(json.dumps(sup)); args[5]=hashlib.sha256(args[4].read_bytes()).hexdigest()
        result=materialize(*args,self.base/'restored')
        self.assertEqual((self.base/'restored/runs/core_v2/project/src/test.py').read_bytes(),old)
        run=json.loads(Path(result['envelope']).read_text())['runs'][0]
        self.assertEqual(run['original_code_pins'][0]['sha256'],oldhash)
        self.assertEqual(run['supplemental_checkpoint_sources'],[])

    def test_concurrent_reservation_allows_one_writer(self):
        from concurrent.futures import ThreadPoolExecutor
        args=self.inputs(); dest=self.base/'restored'
        def work():
            try:
                materialize(*args,dest)
                return 'created'
            except FileExistsError:
                return 'exists'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:work(),range(2)))
        self.assertCountEqual(results,['created','exists'])

    def test_cli_dispatch_requires_explicit_roots(self):
        from asof.archive.__main__ import main
        from contextlib import redirect_stderr
        from io import StringIO
        with redirect_stderr(StringIO()),self.assertRaises(SystemExit):
            main(['verify','--envelope','x','--envelope-sha256','0'*64,'--run-id','core_v2'])

    def test_external_anchor_before_reservation(self):
        args=self.inputs(); args[1]='0'*64
        with self.assertRaises(ContractError): materialize(*args,self.base/'restored')
        self.assertFalse((self.base/'restored').exists())
    def test_hash_failure_retained(self):
        args=self.inputs(); next((self.base/'objects').iterdir()).write_bytes(b'xx')
        with self.assertRaises(ContractError): materialize(*args,self.base/'restored')
        self.assertTrue((self.base/'restored/failure.json').is_file())
    def test_object_traversal_rejected(self):
        with self.assertRaises(ContractError):
            stable_copy(self.base,dict(object='../outside',sha256='0'*64,bytes=0),self.base/'copy')
    def test_receipt_requires_independent_anchor(self):
        result=materialize(*self.inputs(),self.base/'restored')
        with self.assertRaisesRegex(ContractError,'External receipt'):
            verify(result['envelope'],result['envelope_sha256'],'core_v2',result['approved_root_candidates']['core_v2'])
    def test_shared_raw_conflicts_rejected(self):
        args=self.inputs(); cp=json.loads(args[0].read_text())
        cp['entries'].append(dict(cp['entries'][0],logical_path='C:/outside/file'))
        args[0].write_text(json.dumps(cp));args[1]=hashlib.sha256(args[0].read_bytes()).hexdigest()
        rec=json.loads(args[2].read_text());rec['checkpoint_sha256']=args[1];args[2].write_text(json.dumps(rec));args[3]=hashlib.sha256(args[2].read_bytes()).hexdigest()
        sup=json.loads(args[4].read_text());sup['prior_recovery_sha256']=args[3];args[4].write_text(json.dumps(sup));args[5]=hashlib.sha256(args[4].read_bytes()).hexdigest()
        with self.assertRaisesRegex(ContractError,'outside declared roots'): materialize(*args,self.base/'restored')

if __name__=='__main__': unittest.main()
