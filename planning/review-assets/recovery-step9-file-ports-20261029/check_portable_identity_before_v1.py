"""Source-pinned portable counterexamples; only fictional injected Python calls."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'portable_file_ports_v1.py'
PROOF=HERE/'PORTABLE-FILE-PORTS-IDENTITY-WRITE-BEFORE-v1.json'

def pin(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

def load():
    s=importlib.util.spec_from_file_location('identity_before_ports',SOURCE);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m

def main():
    assert not PROOF.exists()
    p=load();rows=[]
    for kind in ('caught_original_identity','caught_output_identity','unreturned_write'):
        calls=[];ownerbox=[];raised=RuntimeError('synthetic_unreturned_write')
        def raw(value,count=None,buffer=b'',defined=False):return p.RawReturn(value,0,False,count,count is not None,buffer,defined)
        def api(name,args):
            calls.append(dict(name=name,arguments=args))
            if name=='CreateFileW':return raw(101)
            if name=='GetFileType':return raw(3) # owned PIPE, not the required DISK
            if name=='ReadFile':return raw(1,3,b'abc',True)
            if name=='WriteFile':
                if kind=='unreturned_write':raise raised
                return raw(1,len(bytes.fromhex(args['data_hex'])))
            if name in ('FlushFileBuffers','CloseHandle'):return raw(1)
            raise AssertionError(name)
        spec=p.FileSpec(r'D:\Fixture\input.bin',3,hashlib.sha256(b'abc').hexdigest())
        def build(origin):
            o=p.PortableOwner(origin,api,lambda name:None,files=(spec,),output=r'D:\Fixture\output');ownerbox.append(o)
            o.seed_for_tests(namespace_owned=True,reservation_ready=True,slots=(('w0','output_file',101,None),) if kind=='unreturned_write' else ())
            def act(owner):
                if kind=='unreturned_write':owner.write_record('w0',b'ABCD');return
                try:
                    if kind=='caught_original_identity':owner.open_original(spec)
                    else:owner.open_output('receipt.json','w0')
                except p.PortError as error:
                    assert error.code=='identity'
                if kind=='caught_original_identity':owner.hash_capture('o0')
                else:owner.write_record('w0',b'ABCD')
            return o.run(act).to_dict()
        result=p.begin_injected(lambda:0,build);o=ownerbox[0]
        if kind=='unreturned_write':
            expected=result['write_count_unknown'] is True
            details=dict(expected_write_count_unknown=True,observed=result['write_count_unknown'],original_exception_preserved=o._primary_object is raised)
        else:
            target='ReadFile' if kind=='caught_original_identity' else 'WriteFile'
            expected=not any(c['name']==target for c in calls)
            details=dict(required_content_attempts=0,observed_content_attempts=sum(c['name']==target for c in calls),identity_ok=o.slots[0].identity_ok)
        rows.append(dict(id=kind,required_invariant_passed=expected,details=details,calls=calls,observation=result))
    assert all(not r['required_invariant_passed'] for r in rows)
    record=dict(schema_version=1,status='THREE_SOURCE_COUNTEREXAMPLES_REPRODUCED_BEFORE_CORRECTION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),source=pin(SOURCE),checker=pin(Path(__file__)),rows=rows,
        chronology='Executed after the first 84-case portable behavioral batch and after the peer identified the identity gate; source v1 remains unchanged.',
        scope='Fictional Python APIs/constant clock only. These are actual portable-source counterexamples, not real FFI/file/native observations.',actual_API_calls=0,profile_qualified=False,runtime_authorized=False)
    with PROOF.open('x',encoding='utf-8') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),counterexamples=len(rows))))

if __name__=='__main__':main()
