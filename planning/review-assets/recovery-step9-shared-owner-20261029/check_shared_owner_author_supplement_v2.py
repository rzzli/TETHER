"""Isolated unknown/late/diagnostic controls, same frozen v1 subject bytes."""
import hashlib
import json
from pathlib import Path
import sys
import types
HERE=Path(__file__).resolve().parent
INPUT=HERE/'check_shared_owner_author_controls_v2.py'
assert hashlib.sha256(INPUT.read_bytes()).hexdigest()=='34e506bf24274ab19fded2322bd5aed4696b62a22d0d7155148ceff91f8fb56b'
H=types.ModuleType('author_harness_for_supplement');H.__file__=str(INPUT);sys.modules[H.__name__]=H;exec(compile(INPUT.read_bytes(),str(INPUT),'exec'),H.__dict__)

def diagnostic_capture():
    error=RuntimeError('captured immutable message')
    def hook(point,owner,ref):
        if point=='hash_update':raise error
    owner,clock,sink,binding=H.create(hook=hook);H.begin(owner);assert H.raises(owner.capture_early) is error
    snapshot=owner.snapshot();before=snapshot.to_dict();error.args=('mutated afterward',);after=snapshot.to_dict();assert after==before and owner.primary is error;assert after['errors']['primary']['message']=='captured immutable message';owner.finalize()

def unreturned_read_unknown():
    error=KeyboardInterrupt('entered wrapper did not return')
    def modify(ref,args,hooks):
        if ref.api=='ReadFile':raise error
        return False
    owner,clock,sink,binding=H.create(modify);H.begin(owner);assert H.raises(owner.capture_early) is error
    d=owner.snapshot().to_dict();assert d['byte_totals']['read_count_unknown'] and d['byte_totals']['known_read_bytes']==0;assert d['calls'][-1]['wrapper_return_observed'] is False;owner.finalize();assert owner.primary is error

def returned_count_before_late_clock():
    holder={}
    def modify(ref,args,hooks):
        if ref.api=='ReadFile':
            hooks.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,b'abc');hooks.store_scalar(ref,1);hooks.store_count(ref,3);holder['clock'].now=395;return True
        return False
    owner,clock,sink,binding=H.create(modify);holder['clock']=clock;H.begin(owner);H.raises(owner.capture_early)
    d=owner.snapshot().to_dict();assert d['byte_totals']['known_read_bytes']==3 and d['byte_totals']['hashed_bytes']==0 and d['byte_totals']['captured_bytes']==0;assert d['calls'][-1]['wrapper_return_observed'];owner.finalize();d=owner.snapshot().to_dict();assert not d['pure_seam_complete'];assert [api for api,args,ref in binding.calls].count('ReadFile')==1

def returned_checker_before_late_clock():
    owner,clock,sink,binding=H.create();token=H.early(owner);owner.load_source('cohort_entry')
    def handler(context):clock.now=395;return H.C.TestObservation(context,'archive','consistent',(H.SPECS[0].path,))
    d=H.finish(owner,token,handlers=(handler,handler,handler,handler)).to_dict();row=d['stages'][-1]
    assert row['name']=='archive' and row['return_observed'] and not row['accepted'] and row['verdict']=='consistent';assert not d['pure_seam_complete'] and d['gates']==['admission','hashes'];assert d['terminal']['original_closures_complete']

def main():
    results=[]
    for fn in (diagnostic_capture,unreturned_read_unknown,returned_count_before_late_clock,returned_checker_before_late_clock):
        try:fn();results.append(dict(method=fn.__name__,passed=True))
        except BaseException as error:results.append(dict(method=fn.__name__,passed=False,error_class=type(error).__name__,error=str(error)[:500]))
    proof=dict(schema_version=1,status='PASS' if all(r['passed'] for r in results) else 'FAIL_PRESERVED',source_pins=[dict(name=n+'.py',sha256=h) for n,h in zip(H.SOURCE_NAMES,H.SOURCE_SHA)],checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),methods=len(results),results=results,actual_API_calls=0,scope='pure supplemental control evidence, not full48 or production/profile')
    out=HERE/'SHARED-OWNER-AUTHOR-SUPPLEMENT-PURE-PROOF-v2.json'
    with out.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print(json.dumps(proof,indent=2));print(hashlib.sha256(out.read_bytes()).hexdigest());return int(proof['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
