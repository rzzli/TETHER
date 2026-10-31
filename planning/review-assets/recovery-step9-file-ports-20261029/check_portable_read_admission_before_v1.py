"""Preserve candidate and reproduce no-dispatch read accounting; fictional only."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'portable_file_ports_v2.py'
SNAPSHOT=HERE/'portable_file_ports_v2_pre_read_accounting.py'
PROOF=HERE/'PORTABLE-FILE-PORTS-READ-ADMISSION-BEFORE-v1.json'
def pin(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    assert not PROOF.exists() and not SNAPSHOT.exists()
    with SNAPSHOT.open('xb') as f:f.write(SOURCE.read_bytes())
    s=importlib.util.spec_from_file_location('ports_read_before',SNAPSHOT);p=importlib.util.module_from_spec(s);sys.modules[s.name]=p;s.loader.exec_module(p)
    calls=[];times=iter((0,295,295,295));spec=p.FileSpec(r'D:\Fixture\input.bin',3,hashlib.sha256(b'abc').hexdigest())
    def api(name,args):calls.append(name);return p.RawReturn(1,0,False,None,False,b'',False)
    def build(origin):
        owner=p.PortableOwner(origin,api,lambda name:None,files=(spec,),output=r'D:\Fixture\output')
        owner.seed_for_tests(namespace_owned=True,reservation_ready=True,slots=(('o0','original_file',101,spec),));owner.assume_seed_identity_for_tests('o0')
        return owner.run(lambda o:o.hash_capture('o0')).to_dict()
    result=p.begin_injected(lambda:next(times),build)
    assert result['api_attempts']['ReadFile']==0 and result['read_count_unknown'] is True and calls==['CloseHandle']
    record=dict(schema_version=1,status='SOURCE_COUNTEREXAMPLE_NO_READ_DISPATCH_BUT_UNKNOWN_COUNT',source=pin(SNAPSHOT),unchanged_candidate=pin(SOURCE),checker=pin(Path(__file__)),recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        required=dict(read_count_unknown=False,ReadFile_attempts=0),observed=result,calls=calls,
        scope='Constant/finite fictional clock, source-issued harness seed assumption and injected Python API only. This is not an original file or platform call.',profile_qualified=False,runtime_authorized=False,actual_API_calls=0)
    with PROOF.open('x',encoding='utf-8') as f:json.dump(record,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),snapshot=pin(SNAPSHOT))))
if __name__=='__main__':main()
