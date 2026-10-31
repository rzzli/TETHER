"""Independent role-aware adapter of the frozen synthetic cohort driver.

Only FileSpec role tags, schema2 packet transport and genuine snapshot projection
are adapted. Frozen histories/expectations, actual identity assertions, ordinary
read-only ref checks, strict snapshot validator and fault/cutoff monitors persist.

Fixture labels/expected values remain only in this harness. Subject sources
receive individual generic calls, exact bytes/refs and original exceptions.
"""
import builtins
import copy
import encodings.utf_16_le
import hashlib
import json
import math
import re
import struct
from pathlib import Path
import sys
import time
import types

HERE=Path(__file__).resolve().parent
LITERALS_DIR=HERE.parent/'recovery-step9-shared-owner-20261029'
TEST_DEADLINE=None
SUBJECT_FILENAMES=set()
PROJECTOR_OBSERVATIONS=[]
ACTIVE=[False]
AUDIT_DENIALS=[]
FIXTURE_SHA='e12d6485d0bc38b38c5b4bf33edcab22c1471da15858718185f18f1b5179eee2'
SCHEMA_SHA='34c3df0519df387e31439096b8c76e39fc3ce74437e1281346da58ab3a33952e'
VALIDATOR_SHA='afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc'
API=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')

class HarnessError(RuntimeError):pass

def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')
def same(a,b):
 if type(a) is not type(b):return False
 if type(a) is dict:return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
 if type(a) is list:return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
 return a==b
def invoke(function,*args,**kwargs):
 previous=ACTIVE[0];ACTIVE[0]=True
 try:return function(*args,**kwargs)
 finally:ACTIVE[0]=previous
def audit(event,args):
 dangerous=(event=='open' or event=='import' or event.startswith(('ctypes.','subprocess.','socket.','os.')))
 if not dangerous:return
 active=ACTIVE[0]
 frame=sys._getframe()
 for _ in range(512):
  if frame is None:break
  if frame.f_code.co_filename in SUBJECT_FILENAMES:active=True;break
  frame=frame.f_back
 if active:
  AUDIT_DENIALS.append(event);raise HarnessError('unexpected_IO_or_import_during_subject')
sys.addaudithook(audit)

def literals():
 paths=[('SHARED-OWNER-INTEGRATION-FIXTURES-v3.json',FIXTURE_SHA),('SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json',SCHEMA_SHA),('SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6'),('SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8')]
 out=[]
 for name,digest in paths:
  raw=(LITERALS_DIR/name).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=digest:raise HarnessError('literal_pin')
  out.append(json.loads(raw))
 return out

def load_exact_modules(source_pins):
 """Compile the SAME freshly pinned bytes; closed imports, no cached fallback."""
 import dataclasses
 stdlib={'dataclasses':dataclasses,'hashlib':hashlib,'json':json,'math':math,'types':types,'struct':struct,'re':re}
 modules={};source_bytes={}
 for name,expected in source_pins.items():
  raw=Path(expected['path']).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=expected['sha256'] or len(raw)!=expected['bytes']:raise HarnessError('source_pin')
  if name in sys.modules:raise HarnessError('fresh_module_name_already_cached')
  source_bytes[name]=raw
  SUBJECT_FILENAMES.add(str(Path(expected['path'])))
 def importer(name,globals=None,locals=None,fromlist=(),level=0):
  if level!=0:raise ImportError('relative subject import not declared')
  if name in modules:return modules[name]
  if name in stdlib:return stdlib[name]
  raise ImportError('closed new-source map: '+name)
 for name in source_pins:
  module=types.ModuleType(name);module.__file__=source_pins[name]['path'];module.__package__=''
  module.__dict__['__builtins__']=dict(vars(builtins),__import__=importer)
  modules[name]=module;sys.modules[name]=module # Fresh exact bytes only; dataclass lookup.
  invoke(exec,compile(source_bytes[name],module.__file__,'exec'),module.__dict__)
 return modules


def subject_role(legacy):
 if legacy=='software':return 'captured_software'
 if legacy in ('owner_metadata','artifact'):return 'captured_metadata'
 raise HarnessError('undeclared legacy input role')

def projected_snapshot(world,issued):
 # Diagnostic projection is an immutable observation, including after the
 # synthetic owner's hard cutoff. Its cancellation uses the ONE externally
 # established real suite deadline, never a renewed owner or a no-op callback.
 if type(issued) is not world.S.ProducerSnapshot:raise HarnessError('nongenuine producer snapshot')
 def check():
  if TEST_DEADLINE is None:raise HarnessError('external test deadline not installed')
  if time.monotonic()>=TEST_DEADLINE:raise TimeoutError('original independent suite deadline')
 projected=invoke(world.S.project_legacy,issued,check=check)
 PROJECTOR_OBSERVATIONS.append(dict(actual_producer_snapshot=True,actual_projector=True,
     same_owner_token_resolution_external=True,owner_clock_resampled=False))
 return projected

class Clock:
 def __init__(self,start=100):self.value=start;self.calls=0
 def __call__(self):self.calls+=1;return self.value
 def set(self,value):
  if type(value) not in (int,float) or isinstance(value,bool) or not math.isfinite(value) or value<self.value:raise HarnessError('invalid scripted clock')
  self.value=value

class SinkSpy:
 def __init__(self,run):self.run=run;self.records=[];self.kind_counts={k:0 for k in ('candidate','cleanup','failure','receipt','seal')};self.journal_consumed=False;self.seal_attempted=False;self.owned=False
 def _call(self,target,ack,hard_end,payload=None,kind=None):
  r=self.run;record=dict(target=target,kind=kind,clock=r.clock.value,payload_hex=None if payload is None else payload.hex(),returned=False,acknowledged=False)
  self.records.append(record) # Never hide an unexpected callback as zero.
  if hard_end!=400:r.violate('foreign/reset sink hard deadline')
  if r.clock.value>=400:r.violate('sink callback after original hard cutoff')
  if target!='reserve' and not self.owned:r.violate('callback into unowned/unknown output')
  if target=='reserve' and sum(x['target']=='reserve' for x in self.records)>1:r.violate('duplicate output reservation')
  if target=='append' and self.journal_consumed:r.violate('append after consumed journal close')
  if target=='close_journal':
   if self.journal_consumed:r.violate('duplicate journal close')
   self.journal_consumed=True
  if self.seal_attempted and target!='publish_seal':r.violate('sink callback after seal')
  if kind is not None:
   self.kind_counts[kind]+=1
   if self.kind_counts[kind]>1:r.violate('publication kind attempted twice')
   if kind in ('receipt','seal') and not self.journal_consumed:r.violate('receipt/seal before journal close')
   if kind=='seal':self.seal_attempted=True
  if payload is not None:
   if type(payload) is not bytes:r.violate('mutable/nonbytes sink payload')
   if len(payload)>(1024 if target=='append' else 8192):r.violate('oversized sink payload')
   decoded=json.loads(payload)
   keys=r.public['serialized_journal_row']['exact_keys'] if target=='append' else ('schema_version','kind','scope','status','elapsed','totals','gates','ledger_refs','links','diagnostic_counts','qualification')
   if type(decoded) is not dict or set(decoded)!=set(keys):r.violate('wrong sink payload keys')
   if canonical(decoded)+b'\n'!=payload:r.violate('noncanonical captured sink payload')
   if target!='append':
    qnames=('originals','real_entry','real_FFI','physical_IO','new84_runtime','resource_fit','scientific')
    if decoded['schema_version']!=2 or type(decoded['schema_version']) is not int or decoded['scope']!='role_aware_producer_format_v1':r.violate('wrong new packet version/scope')
    if decoded['kind']!=kind+'.json' or decoded['status'] not in ('OBSERVED_COMPLETE','OBSERVED_NEGATIVE','INCOMPLETE'):r.violate('wrong new packet kind/status')
    if type(decoded['qualification']) is not dict or set(decoded['qualification'])!=set(qnames) or any(x is not False for x in decoded['qualification'].values()):r.violate('new packet qualification changed')
  action_result=r.callback_actions(target)
  result=object() if action_result=='foreign' else ack
  record['returned']=True;record['acknowledged']=result is ack
  if target=='reserve':self.owned=result is ack
  return result
 def reserve(self,key,ack,hard_end):
  if key!=self.run.fixture['common']['output_key']:self.run.violate('output key changed')
  return self._call('reserve',ack,hard_end)
 def append(self,payload,ack,hard_end):return self._call('append',ack,hard_end,payload)
 def publish(self,kind,payload,ack,hard_end):return self._call('publish_'+kind,ack,hard_end,payload,kind)
 def close_journal(self,ack,hard_end):return self._call('close_journal',ack,hard_end)

class BindingSpy:
 def __init__(self,run):
  self.run=run;self.records=[];self.actual_refs=[];self.occ={};self.literal_read_counts={0:[],1:[],2:[]};self.stopped=False;self.close_counts={};self.known_handles=set()
 def invoke(self,call_ref,arguments,hooks):
  r=self.run;api=call_ref.api;file_id=call_ref.file_ref.id
  key=(api,file_id);self.occ[key]=self.occ.get(key,0)+1;occurrence=self.occ[key]
  record=dict(api=api,file_id=file_id,occurrence=occurrence,arguments=copy.deepcopy(arguments),wrapper_returned=False,exception=None)
  self.records.append(record)
  self.actual_refs.append(call_ref)
  if type(file_id) is not int or not 0<=file_id<3:r.violate('invalid actual file ordinal')
  if type(call_ref.ordinal) is not int or not 0<=call_ref.ordinal<69:r.violate('invalid actual call ordinal')
  if api not in API:r.violate('inactive API dispatched')
  if r.clock.value>=400:r.violate('original binding after hard cutoff')
  if self.stopped and api!='CloseHandle':r.violate('fresh original work after failed/stopped prefix')
  if call_ref.file_ref is not r.owner.file_ref(r.blobs[file_id]['path']):r.violate('foreign/noncanonical file ref')
  base=next(x for x in r.fixture['baseline_binding_inputs'] if x['api']==api and r.aliases[x['file_id']]==file_id)
  expected=copy.deepcopy(base['arguments'])
  if api=='ReadFile':expected['requested']=min(65536,r.blobs[file_id]['bytes']-sum(self.literal_read_counts[file_id]))
  if not same(arguments,expected):r.violate('binding arguments differ from independent frozen expectation')
  if api=='ReadFile' and call_ref.requested!=expected['requested']:r.violate('CallRef requested differs from independent argument')
  if api=='ReadFile' and occurrence>17:r.violate('18th read beyond per-file admitted quota')
  if api=='CloseHandle':
   self.close_counts[file_id]=self.close_counts.get(file_id,0)+1
   if self.close_counts[file_id]>1:r.violate('duplicate original close invocation')
   if arguments['handle'] not in self.known_handles:r.violate('guessed closer for unknown/unowned raw handle')
  override=next((x for x in r.script['binding_overrides'] if (x['api'],x['file_id'],x['occurrence'])==(api,file_id,occurrence)),None)
  actions=copy.deepcopy(override['actions'] if override else base['actions'])
  scalar='UNOBSERVED';count='UNOBSERVED';original=None
  try:
   for a in actions:
    kind=a['hook']
    if kind=='buffer_write':
     frame=a.get('frame',a.get('frame_id'));data=r.frames[frame]
     if call_ref.buffer_ref is None or call_ref.buffer_ref.capacity<len(data):r.violate('unreserved/undersized current buffer')
     hooks.buffer_write(call_ref,call_ref.buffer_ref,call_ref.buffer_generation,data)
    elif kind=='store_scalar':
     scalar=a['value']
     if api=='CreateFileW' and type(scalar) is int and scalar not in (0,2**64-1):self.known_handles.add(scalar)
     hooks.store_scalar(call_ref,scalar)
    elif kind=='store_count':count=a['value'];hooks.store_count(call_ref,count)
    elif kind=='store_error':hooks.store_error(call_ref,a['value'],a['defined'])
    elif kind=='aux':hooks.aux(call_ref,a['field'])
    elif kind=='clock_set':r.clock.set(a['value']);self.stopped=True
    elif kind=='raise_exception':
     original=r.errors[a['exception']];hooks.raise_exception(call_ref,original,a['phase']);self.stopped=True
    elif kind=='throw':original=r.errors[a['exception']];raise original
    else:r.violate('unclosed binding action')
   if override and override['return']=='throw_original':
    if original is None:r.violate('throw_original lacks actual exception')
    raise original
   record['wrapper_returned']=True
   if api=='CreateFileW' and (scalar=='UNOBSERVED' or scalar is None or scalar in (0,2**64-1)):self.stopped=True
   if api=='ReadFile':
    if type(scalar) is int and scalar!=0 and type(count) is int and 0<=count<=expected['requested']:
     self.literal_read_counts[file_id].append(count)
     if count==0 or occurrence==17:self.stopped=True
    else:self.stopped=True
   return None
  except BaseException as error:
   record['exception']=r.exception_label(error);self.stopped=True;raise

class Runtime:
 """Source-facing harness world: contains NO case IDs or expected checks."""
 def __init__(self,modules,fixture,public,cohort,script):
  self.S=modules['shared_owner_v1'];self.P=modules['shared_file_ports_v1'];self.C=modules['continue_verification_v1']
  self.fixture={'baseline_binding_inputs':copy.deepcopy(fixture['baseline_binding_inputs']),'common':{'output_key':fixture['common']['output_key']}}
  self.script=copy.deepcopy(script);self.public=public;self.blobs=cohort['blobs'];self.aliases={b['id']:i for i,b in enumerate(self.blobs)}
  self.frames={k:bytes.fromhex(v) for k,v in fixture['frames_hex'].items()}
  self.clock=Clock();self.owner=None;self.view=None;self.sink=None;self.binding=None;self.specs=None;self.rules=None
  self.errors={};self.violations=[];self.callback_counts={};self.compiler_inputs=[];self.marker_execs=[];self.marker_calls=[];self.peer=None;self.caught=[];self.checker_inputs=[]
  for label,description in fixture['exception_inputs'].items():
   cls=self.S.SharedOwnerError if description['type']=='SharedOwnerError' else getattr(builtins,description['type'])
   self.errors[label]=cls(description.get('code',description.get('message')))
 def violate(self,message):
  self.violations.append(message);raise HarnessError(message)
 def exception_label(self,error):
  return next((label for label,value in self.errors.items() if error is value),'source:'+type(error).__name__)
 def setup(self,owner):
  self.owner=owner
  self.specs=tuple(self.S.FileSpec(b['path'],subject_role(b['role']),b['bytes'],b['sha256'],b['capture'],legacy_role=b['role']) for b in self.blobs)
  self.rules=(self.S.ModuleRule('cohort_leaf',self.blobs[0]['path'],(),False),self.S.ModuleRule('cohort_entry',self.blobs[1]['path'],('cohort_leaf',),False))
  self.binding=BindingSpy(self);self.view=self.P.FilePortView(owner,self.binding);self.sink=SinkSpy(self)
  owner.bind_ports(self.view,self.sink)
  owner.bind_test_hooks(self.S.TestHooks(owner,self.hook))
  owner.bind_test_compiler(self.compiler,stdlib=())
  return owner
 def callback_actions(self,target,call_ref=None):
  self.callback_counts[target]=self.callback_counts.get(target,0)+1;occurrence=self.callback_counts[target]
  rule=next((r for r in self.script['callback_rules'] if r['target']==target and r['occurrence']==occurrence),None)
  if rule is None:return None
  for a in rule['actions']:
   action=a['action']
   if action=='return_foreign_ack':return 'foreign'
   if action=='throw_original':
    if self.binding is not None:self.binding.stopped=True
    raise self.errors[a['exception']]
   if action=='clock_set':
    self.clock.set(a['value'])
    if a['value']>=395 and self.binding is not None:self.binding.stopped=True
   elif action=='emit_forbidden':self.owner.emit(a['event'],a['details'],cleanup=a['cleanup'])
   elif action=='resolve_undeclared':return ('resolve',a['module'])
   elif action=='return_foreign_context':return 'foreign_context'
   else:self.violate('unclosed callback action')
  return None
 def hook(self,point,owner,call_ref):
  if owner is not self.owner:self.violate('testhook foreign owner')
  if point not in ('hash_update','copy_bytes','before_final_ack'):self.violate('unknown testhook point')
  return self.callback_actions(point,call_ref)
 def compiler(self,fullname,captured_bytes,resolver):
  if fullname not in ('cohort_leaf','cohort_entry'):self.violate('unknown compiled ownmodule')
  blob=next(b for b in self.blobs if b['id']==fullname)
  if type(captured_bytes) is not bytes or captured_bytes!=bytes.fromhex(blob['utf8_hex']):self.violate('compiler bytes differ from exact input')
  context=self.owner.early_context
  if context is None or captured_bytes is not context.bytes_for(blob['path']):self.violate('compiler did not reuse same captured early blob')
  self.compiler_inputs.append(dict(module=fullname,bytes=len(captured_bytes),sha256=hashlib.sha256(captured_bytes).hexdigest()))
  action=self.callback_actions('compiler_entry') if fullname=='cohort_entry' else None
  if isinstance(action,tuple):
   result=resolver(action[1]);self.violate('undeclared resolver unexpectedly returned')
  module=types.ModuleType(fullname);module.__file__='<synthetic captured '+fullname+'>'
  def closed_import(name,globals=None,locals=None,fromlist=(),level=0):
   if name!='cohort_leaf' or fullname!='cohort_entry' or level!=0:self.violate('ordinary import fallback attempted')
   return resolver(name)
  module.__dict__['__builtins__']={'__import__':closed_import}
  exec(compile(captured_bytes,module.__file__,'exec'),module.__dict__)
  self.marker_execs.append(fullname)
  return module
 def make_peer(self):
  if self.peer is not None:return self.peer
  empty={'baseline_binding_inputs':self.fixture['baseline_binding_inputs'],'common':self.fixture['common'],'frames_hex':{k:v.hex() for k,v in self.frames.items()},'exception_inputs':{'err0':dict(type='RuntimeError',message='peer diagnostic')}}
  peer=Runtime({'shared_owner_v1':self.S,'shared_file_ports_v1':self.P,'continue_verification_v1':self.C},empty,self.public,{'blobs':self.blobs},{'binding_overrides':[],'callback_rules':[]})
  self.S.start_injected(peer.clock,peer.setup)
  peer.owner.admit_plan(peer.specs,tuple(b['path'] for b in self.blobs[:2]),peer.rules)
  self.peer=peer;return peer
 def factories(self,variant,verdict):
  ids=tuple((stage,'toy_'+stage) for stage in ('archive','journal','resources','core'))
  authority_owner=self.owner;factory_owner=self.owner;files=self.specs
  if variant in ('foreign_factory_owner','foreign_authority_owner'):
   peer=self.make_peer();authority_owner=peer.owner
   if variant=='foreign_factory_owner':factory_owner=peer.owner
  if variant in ('role_changed','capture_changed','hash_changed'):
   b=self.blobs[0];files=list(files)
   files[0]=self.S.FileSpec(b['path'],'captured_metadata' if variant=='role_changed' else subject_role(b['role']),b['bytes'],'0'*64 if variant=='hash_changed' else b['sha256'],False if variant=='capture_changed' else True,legacy_role='owner_metadata' if variant=='role_changed' else b['role'])
   files=tuple(files)
  def authority():return self.C.TestAuthority(authority_owner,files,ids)
  def checker_ports():
   if variant=='unbranded':return {'ids':ids,'handlers':()}
   handlers=[]
   for stage in ('archive','journal','resources','core'):
    def handler(context,stage=stage):
     self.checker_inputs.append(dict(stage=stage,current_context=context is self.owner.evidence_context))
     if context is not self.owner.evidence_context:self.violate('checker called with foreign current context')
     if stage=='archive':self.callback_actions('checker_archive')
     reported=self.owner.early_context if variant=='foreign_context' else context
     return self.C.TestObservation(reported,stage,'negative' if stage=='core' and verdict=='negative' else 'consistent',(self.blobs[2]['path'],),'synthetic only')
    handlers.append(handler)
   return self.C.TestCheckerPorts(self.owner,ids,tuple(handlers))
  return self.C.test_factories(factory_owner,authority,checker_ports)

class FrozenRun:
 def __init__(self,modules,validator,fixture,schema,public,cohort,case):
  self.modules=modules;self.validator=validator;self.fixture=fixture;self.schema=schema;self.public=public;self.cohort=cohort;self.case=copy.deepcopy(case)
  script={k:copy.deepcopy(case[k]) for k in ('binding_overrides','callback_rules')}
  self.world=Runtime(modules,fixture,public,cohort,script)
  self.saved={};self.snapshots=[];self.events=[];self.differences=[];self.protocol_errors=[];self.token_labels=[];self.original_refs={};self.file_refs={};self.early_blobs={};self.token=None;self.continuation=None;self.result=None
 def label(self,error):return self.world.exception_label(error)
 def check_token(self,token):
  owner=self.world.owner;original=owner.exception_for_token(token)
  if not isinstance(original,BaseException):return False
  return original is owner.primary or any(original is x for x in owner.secondary)
 def normalize(self,raw):
  value=copy.deepcopy(raw)
  # deepcopy would clone opaque tokens: replace from actual raw values first.
  for index,diag in enumerate(([raw['errors']['primary']] if raw['errors']['primary'] is not None else [])+raw['errors']['secondary']):
   original=self.world.owner.exception_for_token(diag['identity'])
   label=next((label for known,label in self.token_labels if original is known),None)
   if label is None:
    label=self.label(original)
    if label.startswith('source:'):label+=':'+str(len(self.token_labels))
    self.token_labels.append((original,label))
   if raw['errors']['primary'] is not None and index==0:value['errors']['primary']['identity']=label
   else:
    secondary_index=index-(1 if raw['errors']['primary'] is not None else 0)
    value['errors']['secondary'][secondary_index]['identity']=label
  return value
 def capture(self,name=None):
  w=self.world
  if w.owner is None:return None
  calls=w.clock.calls
  issued=invoke(w.owner.snapshot)
  if not hasattr(issued,'to_dict'):raise HarnessError('subject snapshot lacks immutable issued view')
  legacy=projected_snapshot(w,issued)
  raw=invoke(legacy.to_dict)
  if w.clock.calls!=calls:raise HarnessError('snapshot/to_dict sampled the owner clock')
  # This MUST precede label normalization or ANY expected comparison.
  invoke(self.validator.validate_snapshot,raw,diagnostic_identity_check=self.check_token)
  data=self.normalize(raw)
  if raw['finalized'] and not raw['pure_seam_complete'] and raw['status'] not in ('REFUSED','INCOMPLETE'):raise HarnessError('final noncomplete status not closed')
  self.check_identity(raw)
  self.snapshots.append(dict(point=name or 'observation',data=data))
  if name is not None:self.saved[name]=data
  return issued,data
 def check_identity(self,raw):
  w=self.world;o=w.owner
  if w.view.owner is not o:raise HarnessError('view replaced actual owner')
  if self.continuation is not None and self.continuation.owner is not o:raise HarnessError('Continuation replaced owner')
  for key in ('origin','nonce','registry','port','sink','loader','journal'):
   current=getattr(o,key)
   if key not in self.original_refs:self.original_refs[key]=current
   elif current is not self.original_refs[key]:raise HarnessError('owner identity replaced: '+key)
  if o.origin.start!=100 or o.origin.work_end!=395 or o.origin.hard_end!=400:raise HarnessError('owner time renewed/reset')
  # Before finalization file_ref is a non-owning lookup, never a new lease.
  if raw['plan'] is not None and not o.finalized:
   for i,b in enumerate(w.blobs):
    ref=o.file_ref(b['path'])
    if i in self.file_refs and ref is not self.file_refs[i]:raise HarnessError('canonical file ref copied/reset')
    self.file_refs[i]=ref
  early=o.early_context
  if early is not None:
   if 'early_context' in self.original_refs and early is not self.original_refs['early_context']:raise HarnessError('early source context replaced')
   self.original_refs['early_context']=early
   for b in w.blobs[:2]:
    blob=early.blobs[b['path']]
    if b['path'] in self.early_blobs and blob is not self.early_blobs[b['path']]:raise HarnessError('early byte object replaced')
    self.early_blobs[b['path']]=blob
  full=o.evidence_context
  if full is not None:
   if full.early_context is not early:raise HarnessError('full context lost exact early context')
   for path,blob in self.early_blobs.items():
    if full.blobs[path] is not blob:raise HarnessError('full context recopied/rehash early bytes')
  for field,value in raw['qualification'].items():
   if value is not False:raise HarnessError('real qualification flag lifted: '+field)
 def _spec_variant(self,variant):
  w=self.world
  if variant=='exact':return w.specs,tuple(b['path'] for b in w.blobs[:2]),w.rules
  if variant=='canonical_alias':
   s=w.specs[0];alias=w.S.FileSpec(s.path.replace('\\','/').upper(),s.role,s.size,s.sha256,s.capture,legacy_role=s.legacy_role)
   return w.specs+(alias,),tuple(b['path'] for b in w.blobs[:2]),w.rules
  if variant=='N5_B3_M3_invalid':return w.specs+(w.specs[0],w.specs[1]),tuple(b['path'] for b in w.blobs),w.rules+(w.rules[0],)
  raise HarnessError('unclosed spec variant')
 def _foreign(self,control):
  w=self.world;o=w.owner;peer=w.make_peer()
  if control=='other_registry_file_ref':return w.view.inspect(peer.owner.file_ref(w.blobs[0]['path']))
  if control=='other_owner_port':return o.bind_ports(peer.view,w.sink)
  if control=='copied_dict_continuation':
   factories=w.factories('exact','consistent')
   return w.C.continue_once(dict(owner=o,origin=o.origin,ready=True),w.C.Request(self.fixture['common']['output_key'],w.specs),*factories)
  if control=='second_claim':return self.token.claim()
  raise HarnessError('unclosed foreign control')
 def dispatch(self,step):
  w=self.world;op=step['op'];o=w.owner
  if op=='setup':return w.S.start_injected(w.clock,w.setup)
  if op=='admit':return o.admit_plan(*self._spec_variant(step['spec_variant']))
  if op=='reserve':return o.reserve_output(self.fixture['common']['output_key'])
  if op=='capture_early':return o.capture_early()
  if op=='issue':self.token=o.issue_continuation();return self.token
  if op=='claim':self.continuation=self.token.claim();return self.continuation
  if op=='load':
   loaded=o.load_source(step['module'])
   o.check();actual=loaded.run();o.check()
   w.marker_calls.append(list(actual))
   if actual!=('cohort-entry-v1','cohort-leaf-v1'):raise HarnessError('actual captured helper functions returned wrong marker')
   return loaded
  if op=='probe_load_refused':
   try:o.load_source(step['module'])
   except w.S.SharedOwnerError:raise
   else:raise HarnessError('failed/closed compile retried or cached despite liveness')
  if op=='probe_claim_refused':
   try:self.token.claim()
   except w.S.SharedOwnerError:raise
   else:raise HarnessError('dead early context claim accepted')
  if op=='continue':
   self.result=w.C.continue_once(self.continuation,w.C.Request(self.fixture['common']['output_key'],w.specs),*w.factories(step['factory_variant'],step['verdict']))
   return self.result
  if op=='finalize_incomplete':self.result=o.finalize('incomplete');return self.result
  if op=='close':return w.view.close(o.file_ref(w.blobs[step['file_id']]['path']))
  if op=='clock_set':return w.clock.set(step['value'])
  if op=='foreign_control':return self._foreign(step['control'])
  if op=='emit':return o.emit(step['event'],step['details'],cleanup=step['cleanup'])
  if op=='probe_forbidden_claimed_keyword':
   return o.admit_plan(w.specs,tuple(b['path'] for b in w.blobs[:2]),w.rules,**{step['keyword']:step['value']})
  if op=='snapshot':return None
  if op=='mutate_issued':
   issued=projected_snapshot(w,invoke(o.snapshot));before=invoke(issued.to_dict)
   self.validator.validate_snapshot(before,diagnostic_identity_check=self.check_token)
   original=o.primary
   if original is not w.errors['err0']:raise HarnessError('immutable mutation control missing original error')
   original.args=('changed original exception AFTER issuance',)
   changed=issued.to_dict();changed['qualification']['runtime_authorized']=True;changed['files'].clear();changed['errors']['primary']['message']='mutated caller report'
   after=issued.to_dict()
   # Normalize each via original raw tokens; no shallow exception masking.
   if not same(self.normalize(before),self.normalize(after)):raise HarnessError('issued diagnostic/container mutated')
   if o.primary is not original:raise HarnessError('exception getter lost original object')
   return None
  if op=='diagnostic_foreign_control':
   peer=w.make_peer()
   try:peer.owner.admit_plan({},(),())
   except BaseException:pass
   foreign=invoke(projected_snapshot(peer,invoke(peer.owner.snapshot)).to_dict)['errors']['primary']['identity']
   try:o.exception_for_token(foreign)
   except w.S.SharedOwnerError:pass
   else:raise HarnessError('foreign diagnostic token accepted')
   try:w.view.close(self.continuation)
   except w.S.SharedOwnerError:pass
   else:raise HarnessError('nonowning/finalized misuse accepted')
   return None
  raise HarnessError('unclosed driver op')
 def project(self,data,path):
  if path=='$snapshot':return data
  if path.startswith('$binding.'):
   _,api,file_id,occurrence,_,field=path.split('.')
   rows=[r for r in self.world.binding.records if (r['api'],r['file_id'],r['occurrence'])==(api,int(file_id),int(occurrence))]
   if len(rows)!=1:raise HarnessError('binding projection missing/duplicate actual invocation')
   return rows[0]['arguments'][field]
  value=data
  for p in path.split('.'):
   value=value[int(p)] if type(value) is list else value[p]
  return value
 def compare(self):
  for check in self.case['checks']:
   try:
    data=self.saved[check['at']];actual=self.project(data,check['path']);relation=check['relation'];expected=check['value']
    if relation=='eq':ok=(type(actual) in (int,float) and not isinstance(actual,bool) and actual==expected) if check['path'].startswith('origin.') else same(actual,expected)
    elif relation=='one_of':ok=any(same(actual,x) for x in expected)
    elif relation=='len':ok=type(actual) is list and len(actual)==expected
    elif relation=='le':ok=actual<=expected
    elif relation=='ge':ok=actual>=expected
    elif relation=='unchanged_since':ok=same(actual,self.saved[expected])
    elif relation=='original_exception_is':ok=self.world.owner.primary is self.world.errors[expected]
    else:raise HarnessError('unimplemented frozen relation '+relation)
    if not ok:self.differences.append(dict(check=check,actual=actual))
   except BaseException as error:self.differences.append(dict(check=check,error=type(error).__name__,message=str(error)[:512]))
 def run(self):
  stopped=False;interrupt=False
  for index,step in enumerate(self.case['steps']):
   op=step['op']
   allowed_after_stop=op in ('snapshot','finalize_incomplete','probe_load_refused','probe_claim_refused','foreign_control','mutate_issued','diagnostic_foreign_control')
   if stopped and not allowed_after_stop:
    self.events.append(dict(step=index,op=op,skipped_due_to_failed_prefix=True));continue
   if interrupt and op not in ('snapshot','finalize_incomplete','mutate_issued','diagnostic_foreign_control'):
    self.events.append(dict(step=index,op=op,skipped_due_to_interruption=True));continue
   try:invoke(self.dispatch,step)
   except BaseException as error:
    self.world.caught.append(error);self.events.append(dict(step=index,op=op,exception=self.label(error),error_class=type(error).__name__,message=str(error)[:512]))
    stopped=True;interrupt=interrupt or isinstance(error,(KeyboardInterrupt,SystemExit))
    if isinstance(error,HarnessError):self.protocol_errors.append(str(error))
    if op=='foreign_control':
     try:self.capture('after_rejected_control')
     except BaseException as capture_error:self.protocol_errors.append('rejected-control snapshot:'+type(capture_error).__name__+':'+str(capture_error))
   try:self.capture(step['name'] if op=='snapshot' else 'step_'+str(index))
   except BaseException as error:
    self.protocol_errors.append('actual_snapshot:'+type(error).__name__+':'+str(error));stopped=True
  try:self.capture('final')
  except BaseException as error:self.protocol_errors.append('final_snapshot:'+type(error).__name__+':'+str(error))
  if self.world.peer is not None:
   if self.world.peer.binding.records or self.world.peer.sink.records:self.protocol_errors.append('metadata-only peer dispatched original/sink callbacks')
  # Ordinary read-only facade checks; setters may not change even to samevalue.
  refs=[(ref,('id','spec')) for ref in self.file_refs.values()]
  if self.world.binding is not None:
   refs += [(ref,('ordinal','api','file_ref','requested','buffer_ref','buffer_generation')) for ref in self.world.binding.actual_refs]
   refs += [(ref.buffer_ref,('capacity',)) for ref in self.world.binding.actual_refs if ref.buffer_ref is not None]
  for ref,fields in refs:
   for field in fields:
    before=getattr(ref,field)
    try:invoke(setattr,ref,field,before)
    except (TypeError,AttributeError):pass
    except BaseException as error:self.protocol_errors.append('readonly_ref_wrong_exception:'+type(error).__name__)
    else:self.protocol_errors.append('readonly_ref_setter_accepted:'+field)
  self.compare()
  return dict(id=self.case['id'],matched=not self.differences and not self.protocol_errors and not self.world.violations,differences=self.differences,protocol_errors=self.protocol_errors,violations=self.world.violations,events=self.events,snapshots=self.snapshots,binding_records=[] if self.world.binding is None else self.world.binding.records,sink_records=[] if self.world.sink is None else self.world.sink.records,compiler_inputs=self.world.compiler_inputs,marker_module_execs=self.world.marker_execs,marker_function_calls=self.world.marker_calls,checker_inputs=self.world.checker_inputs,clock_calls=self.world.clock.calls,original_exception_getters_checked=True,scope='Actual new pure source execution against frozen synthetic inputs only; no FFI/real source/production/profile qualification')


