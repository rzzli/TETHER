"""Author controls for frozen three-file pure seam; fictional ports only."""
import builtins
import dataclasses
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time
import types

HERE=Path(__file__).resolve().parent
SOURCE_NAMES=('shared_owner_v1','shared_file_ports_v1','continue_verification_v1')
SOURCE_SHA=('76384e02282b1ce2437b9ff342913297f58ea0858752308724bef912b9e2643b','d80f980c771e11ba0116aa3a1a8e526015ce43cafeacc6cf8bc2890f86b4c900','7f52397a8293ae133f019ede1da78881814eb547b026768f072a34e4a4cf8eb2')
TRUSTED={n:sys.modules[n] for n in ('dataclasses','hashlib','json','math','types','struct')}
def pinned_module_map():
    loaded={}
    def only_import(name,globals=None,locals=None,fromlist=(),level=0):
        if level or name not in loaded and name not in TRUSTED:raise ImportError(name)
        return loaded[name] if name in loaded else TRUSTED[name]
    for name,digest in zip(SOURCE_NAMES,SOURCE_SHA):
        data=(HERE/(name+'.py')).read_bytes();assert hashlib.sha256(data).hexdigest()==digest
        module=types.ModuleType(name);module.__builtins__=dict(vars(builtins),__import__=only_import);sys.modules[name]=module;loaded[name]=module
        exec(compile(data,'<captured:'+name+'>','exec'),module.__dict__)
    return tuple(loaded[n] for n in SOURCE_NAMES)
S,P,C=pinned_module_map()
COHORT=json.loads((HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json').read_text(encoding='utf-8'))
BYTES={x['path']:bytes.fromhex(x['utf8_hex']) for x in COHORT['blobs']}
SPECS=tuple(S.FileSpec(x['path'],x['role'],x['bytes'],x['sha256'],True) for x in COHORT['blobs'])
EARLY=tuple(x['path'] for x in COHORT['blobs'] if x['phase']=='early_source')
RULES=tuple(S.ModuleRule(x['fullname'],COHORT['blobs'][i]['path'],tuple(x['dependencies'])) for i,x in enumerate(COHORT['closed_modules']))

class Clock:
    def __init__(self):self.now=100
    def __call__(self):return self.now
class Sink:
    def __init__(self):self.calls=[];self.rows=[];self.packets={};self.closed=False
    def reserve(self,key,ack,end):self.calls.append(('reserve',key));return ack
    def append(self,data,ack,end):assert not self.closed;self.calls.append(('append',len(data)));self.rows.append(data);return ack
    def publish(self,kind,data,ack,end):assert kind not in self.packets and len(data)<=8192;self.calls.append(('publish',kind));self.packets[kind]=data;return ack
    def close_journal(self,ack,end):assert not self.closed;self.closed=True;self.calls.append(('close_journal',None));return ack
class Binding:
    def __init__(self,clock,modify=None):self.clock=clock;self.modify=modify;self.calls=[]
    def invoke(self,ref,args,h):
        self.calls.append((ref.api,dict(args),ref))
        if self.modify is not None and self.modify(ref,args,h):return
        f=ref.file_ref;spec=f.spec;api=ref.api
        if api=='CreateFileW':h.store_scalar(ref,101+f.id)
        elif api=='GetFileType':h.store_scalar(ref,1)
        elif api=='GetFileInformationByHandleEx':h.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,struct.pack('<II',128,0));h.store_scalar(ref,1)
        elif api=='GetFinalPathNameByHandleW':
            text='\\\\?\\'+spec.path;data=(text+'\0').encode('utf-16-le');h.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,data+b'\0'*(8202-len(data)));h.store_scalar(ref,len(text))
        elif api=='GetFileSizeEx':h.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,struct.pack('<q',spec.size));h.store_scalar(ref,1)
        elif api=='ReadFile':
            data=BYTES[spec.path][-args['requested']:];h.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,data);h.store_scalar(ref,1);h.store_count(ref,len(data))
        elif api=='CloseHandle':h.store_scalar(ref,1)
        else:raise AssertionError(api)
        h.aux(ref,'scalar_aux_ack')
        if api=='ReadFile':h.aux(ref,'count_aux_ack')
        if api=='CreateFileW':h.aux(ref,'right_transfer_ack')
def compiler(name,data,resolver):
    def closed(name,globals=None,locals=None,fromlist=(),level=0):return resolver(name,level)
    env={'__builtins__':{'__import__':closed},'__name__':name};exec(compile(data,'<fictional-captured:'+name+'>','exec'),env);return types.SimpleNamespace(**{k:v for k,v in env.items() if not k.startswith('__')})
def create(modify=None,hook=None):
    clock=Clock();sink=Sink();binding=Binding(clock,modify)
    def setup(o):
        view=P.FilePortView(o,binding);o.bind_ports(view,sink);o.bind_test_compiler(compiler)
        if hook is not None:o.bind_test_hooks(S.TestHooks(o,hook))
        return o
    return S.start_injected(clock,setup),clock,sink,binding
def begin(o):o.admit_plan(SPECS,EARLY,RULES);o.reserve_output('fictional-cohort')
def early(o):begin(o);o.capture_early();return o.issue_continuation().claim()
def finish(o,token,verdict='consistent',handlers=None):
    ids=S.CHECKS
    if handlers is None:handlers=tuple((lambda ctx,stage=stage:C.TestObservation(ctx,stage,verdict if stage=='core' else 'consistent',(SPECS[0].path,))) for stage in ids)
    a,k=C.test_factories(o,lambda:C.TestAuthority(o,SPECS,ids),lambda:C.TestCheckerPorts(o,ids,handlers))
    return C.continue_once(token,C.Request('fictional-cohort',SPECS),a,k)
def raises(fn,kind=BaseException):
    try:fn()
    except kind as e:return e
    raise AssertionError('expected refusal')

def t01_descriptor_domains():
    for size in (True,-1,4097,10**1000):
        o,clock,sink,b=create();bad=(dataclasses.replace(SPECS[0],size=size),*SPECS[1:]);raises(lambda:o.admit_plan(bad,EARLY,RULES));assert not b.calls and not sink.calls
def t02_raw_numeric_domains():
    for value in (True,2**31,-2**31-1):
        def bad(ref,args,h):
            if ref.api=='ReadFile':h.store_scalar(ref,value);return True
            return False
        o,clock,sink,b=create(bad);begin(o);raises(o.capture_early);assert len(b.calls)==6;assert o.snapshot().to_dict()['files'][0]['read_count_unknown'];o.finalize()
def t03_invalid_backward_clock():
    for value in (False,float('nan'),float('inf'),99):
        o,clock,sink,b=create();begin(o);clock.now=value;raises(o.capture_early);assert not b.calls;assert o.snapshot().to_dict()['origin']['now']==100
def t04_firstfacts_wrapper_later_stop():
    error=RuntimeError('after first fact')
    def bad(ref,args,h):
        if ref.api=='ReadFile':
            h.buffer_write(ref,ref.buffer_ref,ref.buffer_generation,b'abc');h.store_scalar(ref,1);h.store_count(ref,3);h.raise_exception(ref,error,'after_count_before_aux');return True
        return False
    o,clock,sink,b=create(bad);begin(o);assert raises(o.capture_early) is error;d=o.snapshot().to_dict();assert o.primary is error and d['byte_totals']['known_read_bytes']==3 and d['byte_totals']['hashed_bytes']==0;assert d['calls'][-1]['wrapper_return_observed'] and d['calls'][-1]['wrapper_state']=='returned' and d['calls'][-1]['stopped'];o.finalize()
def t05_original_error_and_formatting():
    class Bad(S.SharedOwnerError):
        def __str__(self):raise RuntimeError('formatter')
    e=Bad('INVALID_INPUT')
    def hook(point,o,call):
        if point=='hash_update':raise e
    o,clock,sink,b=create(hook=hook);begin(o);assert raises(o.capture_early) is e;d=o.snapshot().to_dict();assert o.primary is e and d['errors']['primary']['format_failed'] and len(o.secondary)==1;assert o.exception_for_token(d['errors']['primary']['identity']) is e;o.finalize()
def t06_detached_snapshots_and_refs():
    o,clock,sink,b=create();early(o);d=o.snapshot().to_dict();d['files'][0]['spec']['size']=0;d['loader']['records'].append({});assert o.snapshot().to_dict()['files'][0]['spec']['size']==58;assert not o.snapshot().to_dict()['loader']['records'];ref=o.file_ref(SPECS[0].path);raises(lambda:setattr(ref,'id',99),TypeError);raises(lambda:setattr(ref.spec,'size',0),dataclasses.FrozenInstanceError);o.finalize()
def t07_inflight_and_postfinal():
    def hook(point,o,call):
        if point=='before_final_ack':o.emit('stage_reserved',{'stage':'core'})
    o,clock,sink,b=create(hook=hook);token=early(o);o.load_source('cohort_entry');r=finish(o,token);d=r.to_dict();assert d['terminal']['seal_acknowledged'] and not d['pure_seam_complete'];n=len(sink.calls);same=o.snapshot().to_dict();raises(lambda:o.finalize());raises(lambda:o.port.close(o.file_ref(SPECS[0].path)));assert len(sink.calls)==n and o.snapshot().to_dict()==same
def t08_one_buffer_and_capacity():
    o,clock,sink,b=create();token=early(o);o.load_source('cohort_entry');finish(o,token);refs=[r for api,a,r in b.calls if api=='ReadFile'];assert len({id(r.buffer_ref) for r in refs})==1;assert [r.buffer_generation for r in refs]==[0,1,2];d=o.snapshot().to_dict();assert d['plan']['raw_storage_peak']<=131072 and d['plan']['read_generation']==3
def t09_actual_inmemory_loader():
    o,clock,sink,b=create();token=early(o);m=o.load_source('cohort_entry');assert m.run()==('cohort-entry-v1','cohort-leaf-v1');assert o.loader.attempted==['cohort_entry','cohort_leaf'] and o.loader.returned==['cohort_leaf','cohort_entry'];assert o.load_source('cohort_entry') is m;assert len(b.calls)==12;finish(o,token)
def t10_canonical_owner_and_closers():
    o,clock,sink,b=create();origin,nonce,registry,loader,journal=o.origin,o.nonce,o.registry,o.loader,o.journal;token=early(o);ctx=o.early_context;refs=tuple(o.file_ref(s.path) for s in SPECS);o.load_source('cohort_entry');r=finish(o,token);assert r.to_dict()['pure_seam_complete'];assert token.owner is o and o.origin is origin and o.nonce is nonce and o.registry is registry and o.loader is loader and o.journal is journal and o.evidence_context.early_context is ctx
    for p in EARLY:assert o.evidence_context.bytes_for(p) is ctx.bytes_for(p)
    assert all(o.file_ref(s.path) is r for s,r in zip(SPECS,refs));assert [a['handle'] for api,a,r in b.calls if api=='CloseHandle']==[103,102,101]
def t11_branded_checkers_and_negative():
    o,clock,sink,b=create();token=early(o);o.load_source('cohort_entry');result=finish(o,token,'negative').to_dict();assert result['status']=='PURE_SEAM_COMPLETE_NEGATIVE' and result['gates']==list(S.GATES) and all(v is False for v in result['qualification'].values())
    o,clock,sink,b=create();token=early(o);o.load_source('cohort_entry');ctx=o.early_context
    handlers=(lambda c:C.TestObservation(ctx,'archive','consistent',(SPECS[0].path,)),)*(4)
    result=finish(o,token,handlers=handlers).to_dict();assert not result['pure_seam_complete'] and result['refusal_code']=='CHECKER_CONTEXT_REFUSED'
def t12_publication_structural_and_rows():
    o,clock,sink,b=create();token=early(o);o.load_source('cohort_entry');d=finish(o,token).to_dict();assert d['plan']['calls_used']==21 and d['plan']['events_used']==53
    assert set(sink.packets)=={'candidate','cleanup','receipt','seal'};assert all(len(v)<=8192 for v in sink.packets.values());assert all(len(row)<=1024 and row.endswith(b'\n') for row in sink.rows)
    assert all(set(json.loads(row))=={'sequence','event','stage','kind','file_id','module','elapsed'} for row in sink.rows)
    for kind,payload in sink.packets.items():
        cb=d['outputs']['publications'][kind];assert cb['prepared_bytes']==len(payload) and cb['prepared_sha256']==hashlib.sha256(payload).hexdigest();assert len(json.loads(payload))==11
    assert d['journal']['tip']=={'bytes':sum(map(len,sink.rows)),'sha256':hashlib.sha256(b''.join(sink.rows)).hexdigest()}

def main():
    started=time.monotonic();results=[]
    for name,fn in tuple(globals().items()):
        if name.startswith('t') and len(name)>3 and name[1:3].isdigit():
            try:fn();results.append(dict(method=name,passed=True))
            except BaseException as error:results.append(dict(method=name,passed=False,error_class=type(error).__name__,error=str(error)[:500]))
    proof=dict(schema_version=1,status='PASS' if all(r['passed'] for r in results) else 'FAIL_PRESERVED_FIRST_AUTHOR_RUN',source_pins=[dict(name=n+'.py',sha256=h) for n,h in zip(SOURCE_NAMES,SOURCE_SHA)],checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),methods=len(results),results=results,elapsed=time.monotonic()-started,actual_API_calls=0,persisted_complete_pack=False,qualification_all_false=True,scope='pure_shared_owner_author_controls_not_production_or_profile')
    out=HERE/'SHARED-OWNER-AUTHOR-CONTROLS-PURE-PROOF-v1.json'
    with out.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print(json.dumps(proof,indent=2));print('PROOF_SHA256',hashlib.sha256(out.read_bytes()).hexdigest());return 0 if proof['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
