"""Retain a post-return exception counterexample on the paused portable core."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'raw_adoption_core_v2.py'
TARGET=HERE/'RAW-ADOPTION-WRAPPER-RETURN-BEFORE-v2.json'
def pin(path):
    b=path.read_bytes();return dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    assert not TARGET.exists();before_pin=pin(SOURCE)
    spec=importlib.util.spec_from_file_location('wrapper_return_before',SOURCE);p=importlib.util.module_from_spec(spec);sys.modules[spec.name]=p;spec.loader.exec_module(p)
    f=p.HarnessFactory();refs={k:f.ref(t) for k,t in zip(p.Context.__dataclass_fields__,p.CONTEXT_KINDS)};refs['early_context']=None;o=f.owner(p.Context(**refs))
    o.declare_slot('file','original_file',handle=101,closer='CloseHandle',identity_ref=f.ref('file_identity'));buf=f.ref('buffer');o.declare_buffer(buf,3,b'abc')
    call=o.reserve(0,'ReadFile','file',3,buf);o.invoke(call);o.store_scalar(call,1);o.store_count(call,3);o.wrapper_return(call)
    first=o.snapshot().to_dict();error=RuntimeError('later publication failed');o.raise_exception(call,error,'cleanup_publication');last=o.snapshot().to_dict()
    assert first['counters']['portable_wrapper_returns']==1 and last['counters']['portable_wrapper_returns']==0
    result=dict(schema_version=1,status='KNOWN_WRAPPER_RETURN_COUNTER_DECREASE_REPRODUCED',recorded_at_utc=datetime.now(timezone.utc).isoformat(),source=before_pin,probe=pin(Path(__file__)),
        before=dict(counters=first['counters'],records=first['records'],known_read_bytes=first['known_read_bytes']),after=dict(counters=last['counters'],records=last['records'],known_read_bytes=last['known_read_bytes']),
        required='A later error must not erase a previously observed wrapper return: either reject the post-return wrapper-outcome rewrite before mutation, or preserve its known return axis and separately record the later stop.',
        original_exception_identity_preserved=o.primary is error,source_unchanged=pin(SOURCE)==before_pin,scope='One new synthetic call/clock/bytes only; no frozen fixture modified, no actual FFI, native API or old archive/source operation.',actual_API_calls=0,profile_qualified=False,runtime_authorized=False)
    with TARGET.open('x',encoding='utf-8') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(pin(TARGET)))
if __name__=='__main__':main()
