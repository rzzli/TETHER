"""Text/AST-only source adaptation; never imports/executes subject modules."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
S=H.parent/'recovery-step9-role-aware-source-20261029'
source=S/'role_owner_v4.py'
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='16f63faee01182d06bcec83e2c2178afcdecb02cca443e9afac4d7447b736acb'
text=raw.decode('utf-8');tree=ast.parse(text)
owner=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='SharedOwner')
names=('match_full_roster','hash_remaining','_packet','_publish','_make_report','_close','finalize','_finish','_context_report','_wire_call','_wire_source','_consume_ledger','freeze_generated','generated_bytes','generated_artifact','_install_generated','check_generated','_snapshot')
methods=[]
for name in names:
    node=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name==name)
    body=ast.get_source_segment(text,node)
    if name=='hash_remaining':
        body=body.replace("CapturedContext(self,self.nonce,self._specs,{f.spec.path:f.blob for f in self.registry._files if f.spec.capture},{f.spec.path:f.actual_sha for f in self.registry._files},self.early_context,_issuer=_MINT)","self.make_context(self._specs,{f.spec.path:f.blob for f in self.registry._files if f.spec.capture},{f.spec.path:f.actual_sha for f in self.registry._files},early_context=self.early_context)")
    if name in ('_packet','_wire_source'):
        first,rest=body.split('\n',1);body=first+'\n        self.require_role1_representable()\n'+rest
    if name=='_snapshot':
        body=body.replace("return ProducerSnapshot(_MINT,self,dict(","return self._issue_snapshot(dict(")
        body=body.replace("scope='role_aware_producer_seam'","scope='entry_kernel_producer_seam'")
        assert body.endswith('))')
        body=body[:-2]+'),finalized=finalized)'
    methods.append('    '+body+'\n')

header='''"""Captured, non-owning late operations over the canonical entry kernel.

No Owner/Origin/Registry constructor, native access or ordinary import fallback.
Source4 algorithms are explicit lineage; every method's self is KernelState.
The accepted Source4 files remain unchanged. Initial factories are synthetic.
"""
from dataclasses import dataclass
from types import MappingProxyType, MethodType
import hashlib
import json
import preflight_entry_kernel_v1 as K
import role_ledger_codec_v4 as codec

UNOBSERVED=K.UNOBSERVED
INVALID=K.INVALID
PROFILE_N4=K.PROFILE_N4
PROFILE_ORIGINAL7_1M=K.PROFILE_ORIGINAL7_1M
CapturedContext=K.CapturedContext
KernelSnapshot=K.KernelSnapshot
uint=K.uint
signed_bool=K.signed_bool
usable=K.usable
sha=K.sha
freeze=K.freeze
thaw=K.thaw
atom=K.atom
_Rows=K._Rows
_same_typed=K._same_typed
_utf8_prefix=K._utf8_prefix
_clock_atom=K._clock_atom
CHECKS=('archive','journal','resources','core')
GATES=('admission','hashes',*CHECKS,'consistency','leases_closed','sealed','final_clock')
KINDS=('candidate','cleanup','failure','receipt','seal')
QUALIFICATION=dict(FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,real_checkers_bound=False,verification_complete=False,profile_qualified=False,runtime_authorized=False)
ARTIFACT_CAPS=K.ARTIFACT_CAPS
_MINT=object()
_OPS_MINT=object()

def need(ok,code='INVALID_INPUT'):
    if not ok:raise K.KernelRefusal(code)

@dataclass(frozen=True,slots=True)
class GeneratedArtifactBytes:
    _mint:object
    owner:object
    origin:object
    nonce:object
    registry:object
    kind:str
    phase:str
    raw:bytes
    sha256:str
    def __post_init__(self):
        need(self._mint is _MINT and type(self.owner)is K.KernelState and type(self.raw)is bytes)

@dataclass(frozen=True,slots=True)
class LegacySnapshot:
    _data:object
    def to_dict(self):return thaw(self._data)

class _LateAlgorithms:
'''

footer='''
_LATE_TABLE=MappingProxyType({name:getattr(_LateAlgorithms,name) for name in (
    'match_full_roster','hash_remaining','_packet','_publish','_make_report','_close',
    'finalize','_finish','_context_report','_wire_call','_wire_source','_consume_ledger',
    'freeze_generated','generated_bytes','generated_artifact','_install_generated',
    'check_generated','_snapshot')})

class OwnerOps:
    __slots__=('_view','_state')
    def __init__(self,mint,view):
        need(mint is _OPS_MINT and type(view)is K.StateView,'FOREIGN_STATE')
        object.__setattr__(self,'_view',view);object.__setattr__(self,'_state',view.state)
    def __setattr__(self,name,value):raise TypeError('non-owning operations are read-only')
    @property
    def view(self):return self._view
    @property
    def state(self):return self._state
    @property
    def origin(self):return self._state.origin
    @property
    def nonce(self):return self._state.nonce
    @property
    def registry(self):return self._state.registry
    @property
    def raw_store(self):return self._state.raw_store
    @property
    def port(self):return self._state.port
    @property
    def sink(self):return self._state.sink
    @property
    def journal(self):return self._state.journal
    @property
    def loader(self):return self._state.loader
    @property
    def early_context(self):return self._state.early_context
    @property
    def evidence_context(self):return self._state.evidence_context
    @property
    def profile(self):return self._state.profile
    @property
    def primary(self):return self._state.primary
    @property
    def secondary(self):return self._state.secondary
    @property
    def finalized(self):return self._state.finalized
    def snapshot(self):return self._state.snapshot()
    def __getattr__(self,name):
        if name in _LATE_TABLE:return MethodType(_LATE_TABLE[name],self._state)
        raise AttributeError(name)
    def continue_once(self,request,authority_factory,checker_factory):
        return continue_once(self._view,request,authority_factory,checker_factory)

def attach(capsule):
    need(type(capsule)is K.KernelContinuation,'FOREIGN_STATE')
    view=capsule.claim_operations(attach)
    ops=OwnerOps(_OPS_MINT,view)
    view.state.install_owner_ops(view,ops,_LATE_TABLE)
    return ops

@dataclass(frozen=True,slots=True)
class Request:
    output_key:str
    files:tuple
@dataclass(frozen=True,slots=True)
class TestAuthority:
    owner:object
    files:tuple
    checker_ids:tuple
@dataclass(frozen=True,slots=True)
class TestCheckerPorts:
    owner:object
    ids:tuple
    handlers:tuple
@dataclass(frozen=True,slots=True)
class TestObservation:
    context:object
    stage:str
    verdict:str
    evidence_paths:tuple
    detail:str=''
@dataclass(frozen=True,slots=True)
class TestAuthorityFactory:
    owner:object
    callback:object
    scope:str='SYNTHETIC_ONLY'
    def __call__(self):return self.callback()
@dataclass(frozen=True,slots=True)
class TestCheckerFactory:
    owner:object
    callback:object
    scope:str='SYNTHETIC_ONLY'
    def __call__(self):return self.callback()

def test_factories(state,authority_callback,checker_callback):
    need(type(state)is K.KernelState and callable(authority_callback) and callable(checker_callback))
    return TestAuthorityFactory(state,authority_callback),TestCheckerFactory(state,checker_callback)

def continue_once(claimed_view,request,test_authority_factory,test_checker_factory):
    need(type(claimed_view)is K.StateView,'FOREIGN_STATE')
    state=claimed_view.state
    state._active();state.require(state._claimed and not state._engine_entered,'CONTINUATION_REPEATED')
    state._engine_entered=True;state._phase='CONTINUATION'
    try:
        state.check();state._live_early();state.require(type(request)is Request,'INVALID_INPUT')
        state.require(type(test_authority_factory)is TestAuthorityFactory and type(test_checker_factory)is TestCheckerFactory and test_authority_factory.owner is state and test_checker_factory.owner is state and test_authority_factory.scope=='SYNTHETIC_ONLY' and test_checker_factory.scope=='SYNTHETIC_ONLY','FOREIGN_STATE')
        def valid_authority(value):state.require(type(value)is TestAuthority and value.owner is state,'FOREIGN_STATE')
        authority=state.stage('authority_factory',test_authority_factory,valid_authority)
        def valid_checkers(value):
            state.require(type(value)is TestCheckerPorts and value.owner is state and type(value.ids)is tuple and value.ids==authority.checker_ids and type(value.handlers)is tuple and len(value.handlers)==4 and all(callable(h)for h in value.handlers),'CHECKER_BINDING_REFUSED')
            order=tuple(x[0]if type(x)is tuple and len(x)==2 else x for x in value.ids)
            state.require(order==CHECKS,'CHECKER_BINDING_REFUSED')
        checkers=state.stage('checker_factory',test_checker_factory,valid_checkers)
        state.stage('admit_reconcile',lambda:state.match_full_roster(request,authority))
        state.stage('hash_remaining',state.hash_remaining)
        for stage,handler in zip(CHECKS,checkers.handlers):
            state._phase='CHECKERS'
            def validate(observation,stage=stage):
                state.require(type(observation)is TestObservation and observation.context is state.evidence_context and type(observation.context)is K.CapturedContext and observation.context.owner is state and observation.stage==stage,'CHECKER_CONTEXT_REFUSED')
                state.require(observation.verdict in('consistent','negative') and(observation.verdict!='negative'or stage=='core')and type(observation.detail)is str and len(observation.detail)<=4096,'CHECKER_BINDING_REFUSED')
                state.require(type(observation.evidence_paths)is tuple and 0<len(observation.evidence_paths)<=state.profile.Nmax and len(set(observation.evidence_paths))==len(observation.evidence_paths)and all(p in state.evidence_context.blobs for p in observation.evidence_paths),'CHECKER_CONTEXT_REFUSED')
                state._negative=state._negative or observation.verdict=='negative';state.proof(stage)
            state.stage(stage,lambda handler=handler:handler(state.evidence_context),validate)
        state.stage('consistency',lambda:state.proof('consistency'))
    except BaseException as error:state.record_error(error,'continue_once')
    return state._finish(state.primary is None and tuple(state._gates)==GATES[:7])

def project_legacy(snapshot,*,check):
    need(callable(check));check()
    need(type(snapshot)is K.KernelSnapshot,'LEGACY_NOT_REPRESENTABLE')
    snapshot.require_role1_representable()
    if snapshot._profile is not PROFILE_N4:raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    state=snapshot.owner_state;data=snapshot.to_dict()
    if data['calls']is None or any(not f['spec']['capture']for f in data['files']):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    for diagnostic in(data['errors']['primary'],*data['errors']['secondary']):
        if diagnostic is not None and diagnostic['phase']not in LEGACY_PHASES:raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    # No fallback role guess, prefix stripping or new-phase normalization.
    for f in data['files']:
        spec=state._specs[f['id']]
        if spec.legacy_role not in('software','owner_metadata','artifact'):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    data.pop('schema_version');data.pop('generated');data.pop('assembly_live');data.pop('assembly_peak');data['scope']='pure_shared_owner_seam'
    for f in data['files']:
        for key in('capture_state','hash_unknown','copy_unknown','read_generation'):f.pop(key,None)
        f['spec']['role']=state._specs[f['id']].legacy_role
        if f['handle_fact']['tag']=='UNENCODABLE_RAW':raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    for c in data['calls']:
        if any(c[k]['tag']=='UNENCODABLE_RAW'for k in('raw_scalar','raw_count','raw_error')):raise codec.FormatError('LEGACY_NOT_REPRESENTABLE')
    result=LegacySnapshot(freeze(data));check();return result

LEGACY_PHASES=('binding_invoke','pre_dispatch','after_scalar_before_aux','after_scalar_before_right_transfer','error_copy','RawReturn_allocation','after_count_before_aux','buffer_copy','hash_update','post_call_clock','identity_query','handoff','close_wrapper','cleanup_publication','entry','bind_ports','bind_test_hooks','bind_test_compiler','admit_plan','reserve_output','capture_early','issue_continuation','claim_continuation','load_source','continue_once','finalize','journal_append','journal_close','publish_candidate','publish_cleanup','publish_failure','publish_receipt','publish_seal','original_close','diagnostic_format','final_clock','authority_factory','checker_factory','admit_reconcile','hash_remaining','archive','journal','resources','core','consistency','copy_bytes','before_final_ack')
'''

out=header+'\n'.join(methods)+footer
ast.parse(out)
target=H/'preflight_owner_ops_v1.py'
if target.exists():raise RuntimeError('first generated source already exists; preserve before correction')
target.write_text(out,encoding='utf-8',newline='\n')
record=dict(source4_sha256=hashlib.sha256(raw).hexdigest(),new_source_sha256=hashlib.sha256(out.encode()).hexdigest(),new_source_bytes=len(out.encode()),methods=list(names),authoring='AST/text only; no source import/exec/test',adaptations=['same KernelState receiver via fixed late table','kernel context/snapshot mint','ROLE1 representability guards','local continuation over StateView','no owner/Origin/Registry construction','strict legacy role/phase projection'])
(H/'OWNEROPS-TEXT-AUTHORING-v1.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record))
